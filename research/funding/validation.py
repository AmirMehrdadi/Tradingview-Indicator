"""Historical timestamp diagnostics and linked Mark proxy validation; no PnL."""
import math
from collections import Counter
from decimal import Decimal, InvalidOperation

from research.access import AccessDenied, iso
from .policy import MINUTE, EXECUTION_STEP, FUNDING, MARK, response_timestamp


def decimal_string(value):
    if not isinstance(value, str) or len(value)>128:
        raise ValueError("DECIMAL_STRING_REQUIRED")
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise ValueError("INVALID_DECIMAL") from None
    if not number.is_finite() or not math.isfinite(float(number)) or abs(number.adjusted())>1000:
        raise ValueError("NONFINITE_DECIMAL")
    text = format(number,'f')
    return "0" if number==0 else text.rstrip('0').rstrip('.') if '.' in text else text


def funding_rows(rows, period):
    period.validate()
    found, invalid, conflicts, seen = {}, [], set(), {}
    duplicates = 0
    for row in rows:
        t = response_timestamp(row, FUNDING)
        period.settlement(t)
        if row.get("symbol") != "BTCUSDT":
            raise AccessDenied("FUNDING_SYMBOL_MISMATCH")
        try:
            rate = decimal_string(row.get("fundingRate"))
        except ValueError as exc:
            invalid.append({"settlement_ms": t, "reason": str(exc)})
            conflicts.add(t)  # A bad copy must not be hidden by a valid duplicate.
            continue
        if t in seen:
            if Decimal(seen[t]) != Decimal(rate):
                conflicts.add(t)
            else:
                duplicates += 1
        seen[t] = rate
        found.setdefault(t, {"settlement_ms": t, "settlement_utc": iso(t), "funding_rate": rate})
    for t in conflicts:
        found.pop(t, None)
    return [found[t] for t in sorted(found)], {"received": len(rows), "valid_unique": len(found), "identical_duplicates": duplicates,
                                            "conflicting_settlements_ms": sorted(conflicts), "invalid_records": invalid}


def calendar_diagnostics(records, period, scan_complete, verification_matches):
    period.validate()
    times = []
    for record in records:
        period.settlement(record["settlement_ms"])
        times.append(record["settlement_ms"])
    if times != sorted(set(times)):
        raise ValueError("CALENDAR_REQUIRES_SORTED_UNIQUE_SETTLEMENTS")
    gaps = Counter(b-a for a,b in zip(times,times[1:]))
    modal = None if not gaps else min(gaps, key=lambda d:(-gaps[d],d))
    suspected = []
    suspected_count = 0
    if modal and modal > 0:
        for a,b in zip(times,times[1:]):
            if (b-a) % modal == 0 and b-a > modal:
                suspected_count += (b-a)//modal-1
                suspected.extend(range(a+modal,b,modal)[:max(0,16384-len(suspected))])
    irregular = [{"previous_ms":a,"next_ms":b,"interval_ms":b-a} for a,b in zip(times,times[1:]) if modal and b-a != modal]
    return {"observed_settlements":len(times), "first_observed_utc":iso(times[0]) if times else None,
            "last_observed_utc":iso(times[-1]) if times else None, "observed_interval_counts_ms":{str(k):v for k,v in sorted(gaps.items())},
            "modal_observed_interval_ms":modal, "suspected_internal_missing_ms":suspected,
            "suspected_internal_missing_count":suspected_count, "suspected_timestamp_list_truncated":suspected_count>len(suspected), "irregular_intervals":irregular,
            "annual_api_scan_complete":bool(scan_complete), "independent_window_requery_matches":bool(verification_matches),
            "historical_calendar_status":"UNVERIFIED_NO_DATED_INTERVAL_CHANGE_OR_COMPLETE_CALENDAR_EVIDENCE",
            "missing_settlement_count":None, "missing_count_reason":"Cannot distinguish missing API rows from historical schedule changes using these observations alone; empty responses never establish zero settlements.",
            "schedule_basis":"HISTORICAL_API_TIMESTAMPS_ONLY_NOT_CURRENT_INSTRUMENT_METADATA",
            "coverage_verdict":"OBSERVED_DATA_ONLY_HISTORICAL_CALENDAR_UNPROVEN" if times else "NO_SETTLEMENT_COVERAGE_ESTABLISHED"}


def classify_settlement(t, period):
    period.settlement(t)
    if t % EXECUTION_STEP:
        return {"settlement_ms":t,"alignment":"FUNDING_ALIGNMENT_UNRESOLVED", "intrabar_order":"NOT_INFERRED"}
    return {"settlement_ms":t, "alignment":"ALIGNED_15M", "phase_order":["PRIOR_BAR","PARTITION_END_IF_APPLICABLE","UTC_DAY_RESET_IF_APPLICABLE","FUNDING","SIGNAL_CLOSE","OPEN"],
            "new_entry_at_same_open":"EXEMPT", "old_open_exit_base":"AFTER_FUNDING", "old_open_exit_sensitivity":"BEFORE_FUNDING",
            "partition_start":t==period.start, "partition_start_carried_exposure":"NONE_ANNUAL_RESET" if t==period.start else "NOT_APPLICABLE"}


def classify_fill_event(event_ms,phase,kind,settlement_ms,period):
    """Timestamp/phase classification only; never calculates quantities or cashflows."""
    period.settlement(settlement_ms)
    period.settlement(event_ms)
    if phase not in ('PRIOR_BAR','OPEN') or kind not in ('ENTRY','EXIT') or (kind=='ENTRY' and phase!='OPEN'):
        raise ValueError('INVALID_FILL_PHASE_OR_KIND')
    if settlement_ms % EXECUTION_STEP:
        return {'classification':'FUNDING_ALIGNMENT_UNRESOLVED','ordering':'NOT_INFERRED'}
    if event_ms!=settlement_ms:
        return {'classification':'BEFORE_FUNDING' if event_ms<settlement_ms else 'AFTER_FUNDING'}
    if phase=='PRIOR_BAR':
        return {'classification':'BEFORE_FUNDING','quantity_effect':'EXIT_ALREADY_REDUCED_OLD_EXPOSURE'}
    if kind=='ENTRY':
        return {'classification':'AFTER_FUNDING','same_open_entry':'EXEMPT'}
    return {'classification':'FUNDING_TIE','base_exit_order':'AFTER_FUNDING','sensitivity_exit_order':'BEFORE_FUNDING'}


def mark_rows(rows, settlements, period, now_ms):
    period.validate()
    required, unavailable = {}, []
    for t in settlements:
        period.settlement(t)
        try:
            required[period.mark_minute(t)] = t
        except AccessDenied as exc:
            unavailable.append({"settlement_ms":t,"reason":str(exc)})
    seen, valid, conflicts, invalid = {}, {}, set(), []
    duplicates = 0
    for row in rows:
        t = response_timestamp(row, MARK)
        period.mark_minute(t+MINUTE)
        if t not in required or t % MINUTE:
            raise AccessDenied("MARK_NOT_LINKED_TO_REQUIRED_SETTLEMENT")
        try:
            if len(row) != 5:
                raise ValueError("MARK_REQUIRES_FIVE_STRING_FIELDS")
            values = [decimal_string(v) for v in row[1:]]
            o,h,l,c = [Decimal(v) for v in values]
            if min(o,h,l,c) <= 0 or not l <= o <= h or not l <= c <= h:
                raise ValueError("INVALID_MARK_OHLC_GEOMETRY_OR_PRICE")
            if t+MINUTE > now_ms:
                raise ValueError("INCOMPLETE_MARK_MINUTE")
        except ValueError as exc:
            invalid.append({"minute_open_ms":t,"reason":str(exc)})
            conflicts.add(t)
            continue
        signature = tuple(Decimal(v) for v in values)
        if t in seen:
            duplicates += 1
            if seen[t] != signature:
                conflicts.add(t)
        seen[t] = signature
        valid.setdefault(t, {"settlement_ms":required[t],"settlement_utc":iso(required[t]),"minute_open_ms":t,"minute_open_utc":iso(t),
                             "minute_end_ms":t+MINUTE,"open":values[0],"high":values[1],"low":values[2],"close":values[3],
                             "proxy_classification":"APPROXIMATE_MARK_PREVIOUS_1M_CLOSE","settlement_price_proxy":values[3],
                             "low_sensitivity":values[2],"high_sensitivity":values[1],"exact_tick":False,"guaranteed_settlement_bounds":False})
    for t in conflicts:
        valid.pop(t,None)
    missing = [{"settlement_ms":s,"minute_open_ms":t,"reason":"REQUIRED_MARK_MINUTE_MISSING_OR_INVALID"} for t,s in sorted(required.items()) if t not in valid]
    return [valid[t] for t in sorted(valid)], {"required_settlements":len(settlements),"requestable_minutes":len(required),"valid_linked_minutes":len(valid),
                                            "duplicate_rows":duplicates,"conflicting_minutes_ms":sorted(conflicts),"invalid_minutes":invalid,
                                            "unavailable_minutes":unavailable,"missing_minutes":missing,
                                            "status":"COMPLETE_FOR_OBSERVED_SETTLEMENTS" if not missing and not unavailable and not invalid else "INCOMPLETE"}
