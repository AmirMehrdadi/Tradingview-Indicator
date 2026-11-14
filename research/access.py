"""Fail-closed Phase-1 access policy, independent of user configuration."""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
STEP_MS = {"15": 900_000, "60": 3_600_000}


class AccessDenied(ValueError):
    pass


def timestamp(value: str) -> int:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
        raise AccessDenied("An explicit UTC timestamp is required")
    return int(dt.timestamp() * 1000)


def iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class Window:
    year: int
    interval: str
    start: int
    end: int
    anchor: int

    @property
    def step(self) -> int:
        return STEP_MS[self.interval]

    @classmethod
    def annual(cls, year: int, interval: str):
        if type(year) is not int or year not in (2023, 2024) or interval not in STEP_MS:
            raise AccessDenied("Phase 1 permits only annual 2023/2024 and intervals 15/60")
        start = timestamp(f"{year}-01-01T00:00:00Z")
        return cls(year, interval, start, timestamp(f"{year+1}-01-01T00:00:00Z"), start - 60 * 3_600_000)

    def validate(self):
        if self != Window.annual(self.year, self.interval):
            raise AccessDenied("Window differs from the authorized annual partition and 60-hour warm-up")

    def authorize(self, start: int, end: int):
        self.validate()
        if type(start) is not int or type(end) is not int or not self.anchor <= start < end <= self.end:
            raise AccessDenied("Range is outside Phase-1 development/warm-up allowlist")
        if start % self.step or end % self.step:
            raise AccessDenied("Candle windows must align to UTC interval boundaries")

    def authorize_bar(self, open_time: int):
        self.authorize(open_time, open_time + self.step)


def authorize_request(path: str, params: dict):
    if params.get("category") != "linear" or params.get("symbol") != "BTCUSDT":
        raise AccessDenied("Only public BTCUSDT linear data is authorized")
    if path == "/v5/market/instruments-info":
        if set(params) != {"category", "symbol"}:
            raise AccessDenied("Unexpected instrument request parameters")
        return  # Explicitly authorized current metadata, never price history.
    if path != "/v5/market/kline" or set(params) != {"category", "symbol", "interval", "start", "end", "limit"}:
        raise AccessDenied("Endpoint/parameters not authorized in Phase 1")
    if type(params["limit"]) is not int or not 1 <= params["limit"] <= 1000:
        raise AccessDenied("API limit must be 1..1000")
    if type(params["start"]) is not int or type(params["end"]) is not int:
        raise AccessDenied("Integer millisecond boundaries required")
    # Bybit end is inclusive; the local contract is exclusive.
    for year in (2023, 2024):
        try:
            Window.annual(year, params["interval"]).authorize(params["start"], params["end"] + 1)
            return
        except AccessDenied:
            pass
    raise AccessDenied("Unauthorized history, including all 2025+ and Holdout data")
