"""Separate allowlist: exactly two public endpoints and Development settlements."""
from dataclasses import dataclass, asdict

from research.access import AccessDenied, timestamp, iso

MINUTE = 60000
EXECUTION_STEP = 15*MINUTE
DEVELOPMENT_START = timestamp("2023-01-01T00:00:00Z")
DEVELOPMENT_END = timestamp("2025-01-01T00:00:00Z")
FUNDING = "/v5/market/funding/history"
MARK = "/v5/market/mark-price-kline"


@dataclass(frozen=True)
class Period:
    year: int
    start: int
    end: int

    @classmethod
    def annual(cls, year):
        if type(year) is not int or year not in (2023, 2024):
            raise AccessDenied("DEVELOPMENT_YEARS_ONLY")
        return cls(year, timestamp(f"{year}-01-01T00:00:00Z"), timestamp(f"{year+1}-01-01T00:00:00Z"))

    def validate(self):
        if self != Period.annual(self.year):
            raise AccessDenied("ALTERED_ANNUAL_PERIOD")

    def settlement(self, t):
        self.validate()
        if type(t) is not int or not self.start <= t < self.end:
            raise AccessDenied("SETTLEMENT_OUTSIDE_AUTHORIZED_YEAR")

    def mark_minute(self, t):
        self.settlement(t)
        if t % MINUTE:
            raise AccessDenied("SETTLEMENT_NOT_MINUTE_ALIGNED")
        if t-MINUTE < DEVELOPMENT_START or t > DEVELOPMENT_END:
            raise AccessDenied("PRE_DEVELOPMENT_MARK_MINUTE_NOT_AUTHORIZED")
        return t-MINUTE

    def public(self):
        self.validate()
        return {**asdict(self), "start_utc": iso(self.start), "exclusive_end_utc": iso(self.end)}


def authorize_request(period, path, params, settlements=()):
    period.validate()
    if params.get("category") != "linear" or params.get("symbol") != "BTCUSDT":
        raise AccessDenied("ONLY_LINEAR_BTCUSDT")
    if type(params.get("limit")) is not int:
        raise AccessDenied("INTEGER_PAGE_LIMIT_REQUIRED")
    if path == FUNDING:
        if set(params) != {"category", "symbol", "startTime", "endTime", "limit"} or not 1 <= params["limit"] <= 200:
            raise AccessDenied("INVALID_FUNDING_REQUEST_SCHEMA_OR_LIMIT")
        lo, hi = params["startTime"], params["endTime"]
        if type(lo) is not int or type(hi) is not int or not period.start <= lo <= hi < period.end:
            raise AccessDenied("FUNDING_REQUEST_OUTSIDE_YEAR")
    elif path == MARK:
        if set(params) != {"category", "symbol", "interval", "start", "end", "limit"} or params["interval"] != "1" or not 1 <= params["limit"] <= 1000:
            raise AccessDenied("INVALID_MARK_REQUEST_SCHEMA_OR_LIMIT")
        lo, hi = params["start"], params["end"]
        if type(lo) is not int or type(hi) is not int or lo % MINUTE or (hi+1) % MINUTE or not DEVELOPMENT_START <= lo <= hi < DEVELOPMENT_END:
            raise AccessDenied("MARK_REQUEST_OUTSIDE_DEVELOPMENT_OR_UNALIGNED")
        expected = set()
        for t in settlements:
            expected.add(period.mark_minute(t))
        requested = set(range(lo, hi+1, MINUTE))
        if not requested or not requested <= expected or len(requested) > params["limit"]:
            raise AccessDenied("UNLINKED_OR_UNRELATED_MARK_MINUTES")
    else:
        raise AccessDenied("ENDPOINT_NOT_AUTHORIZED_FOR_PHASE4A")


def response_timestamp(row, path):
    value = row.get("fundingRateTimestamp") if path == FUNDING and isinstance(row, dict) else row[0] if path == MARK and isinstance(row, list) and row else None
    if not isinstance(value, str) or not value.isascii() or not value.isdigit():
        raise ValueError("INVALID_RESPONSE_TIMESTAMP")
    return int(value)


def authorize_response(period, path, params, rows, settlements=()):
    authorize_request(period, path, params, settlements)
    if not isinstance(rows, list) or len(rows) > params["limit"]:
        raise ValueError("INVALID_OR_OVERSIZED_PAGE")
    for row in rows:
        t = response_timestamp(row, path)
        if path == FUNDING:
            period.settlement(t)  # Before reading a rate value.
            if not params["startTime"] <= t <= params["endTime"]:
                raise AccessDenied("FUNDING_RESPONSE_OUTSIDE_EXPLICIT_PAGE")
            if row.get("symbol") != "BTCUSDT":
                raise AccessDenied("FUNDING_RESPONSE_SYMBOL_MISMATCH")
        else:
            period.mark_minute(t+MINUTE)  # Before reading prices or persisting a response body.
            if t not in {period.mark_minute(s) for s in settlements} or not params["start"] <= t <= params["end"] or t % MINUTE:
                raise AccessDenied("MARK_RESPONSE_NOT_LINKED_TO_AUTHORIZED_SETTLEMENT")
