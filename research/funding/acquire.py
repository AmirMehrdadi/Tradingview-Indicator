"""Bounded scans and observed-settlement-only Mark requests."""
from concurrent.futures import ThreadPoolExecutor

from research.access import AccessDenied
from research.loader import canonical, sha256
from .http import AcquisitionError
from .policy import FUNDING, MARK, MINUTE
from .validation import funding_rows


def funding_scan(client, period, start=None, end=None, limit=200):
    period.validate()
    lo = period.start if start is None else start
    hi = period.end-1 if end is None else end
    if type(lo) is not int or type(hi) is not int or not period.start <= lo <= hi < period.end:
        raise AccessDenied("SCAN_OUTSIDE_ANNUAL_PERIOD")
    if type(limit) is not int or not 1 <= limit <= 200:
        raise AccessDenied("FUNDING_LIMIT_1_TO_200_REQUIRED")
    rows, pages = [], 0
    cursor = hi
    while cursor >= lo:
        params = {"category":"linear","symbol":"BTCUSDT","startTime":lo,"endTime":cursor,"limit":limit}
        try:
            page = client.get(period,FUNDING,params)
        except (AcquisitionError, AccessDenied) as exc:
            return rows, {"scan_complete":False,"pages":pages,"reason":str(exc)}
        pages += 1
        rows.extend(page)
        if len(rows) > 20000:
            return rows, {"scan_complete":False,"pages":pages,"reason":"SETTLEMENT_RESOURCE_LIMIT_20000_PER_SCAN"}
        if not page:
            return rows, {"scan_complete":True,"pages":pages,"reason":"EXPLICIT_RANGE_PAGINATION_EXHAUSTED_NOT_CALENDAR_PROOF"}
        oldest = min(int(row["fundingRateTimestamp"]) for row in page)
        if oldest > cursor:
            raise AcquisitionError("PAGINATION_NO_BACKWARD_PROGRESS")
        cursor = oldest-1  # Inclusive remote end; move one millisecond back, never beyond the year.
    return rows, {"scan_complete":True,"pages":pages,"reason":"REACHED_ANNUAL_START_NOT_CALENDAR_PROOF"}


def verify_disjoint_windows(client, period, records):
    """Independent 14-day re-queries detect pagination loss; not a historical calendar."""
    period.validate()
    other = []
    for start in range(period.start,period.end,14*86400000):
        rows, status = funding_scan(client,period,start,min(start+14*86400000,period.end)-1)
        other.extend(rows)
        if not status["scan_complete"]:
            return {"status":"INCOMPLETE","reason":status["reason"],"matches":False}
    normalized, quality = funding_rows(other,period)
    matches = canonical(normalized)==canonical(records) and not quality["invalid_records"] and not quality["conflicting_settlements_ms"]
    return {"status":"MATCH" if matches else "MISMATCH","matches":matches,"observed_timestamp_rate_sha256":sha256(canonical(normalized)),
            "basis":"INDEPENDENT_DISJOINT_14_DAY_PUBLIC_QUERIES_NOT_INDEPENDENT_CALENDAR"}


def mark_batches(settlements,period):
    period.validate()
    starts=[]
    for t in settlements:
        period.settlement(t)
        try:
            starts.append(period.mark_minute(t))
        except AccessDenied:
            continue  # Explicitly reported as unavailable by mark_rows, never silently repaired.
    batches=[]
    for t in sorted(set(starts)):
        if batches and t==batches[-1][-1]+MINUTE and len(batches[-1])<1000:
            batches[-1].append(t)
        else:
            batches.append([t])
    return batches


def fetch_marks(client,period,settlements,workers=6,progress=None):
    period.validate()
    if type(workers) is not int or not 1<=workers<=6:
        raise ValueError("MARK_WORKERS_1_TO_6")
    batches=mark_batches(settlements,period)
    def retrieve(batch):
        linked=tuple(t+MINUTE for t in batch)
        params={"category":"linear","symbol":"BTCUSDT","interval":"1","start":batch[0],"end":batch[-1]+MINUTE-1,"limit":len(batch)}
        try:
            return client.get(period,MARK,params,linked),None
        except (AcquisitionError,AccessDenied) as exc:
            return [],{"settlements_ms":list(linked),"reason":str(exc)}
    # executor.map preserves deterministic batch order; Client serializes request starts and shares a 403 circuit.
    with ThreadPoolExecutor(max_workers=workers) as pool:
        results=[]
        for i,result in enumerate(pool.map(retrieve,batches),1):
            results.append(result)
            if progress and (i%100==0 or i==len(batches)):
                progress(i,len(batches))
    return [row for rows,_ in results for row in rows],[error for _,error in results if error]
