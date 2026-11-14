"""Bounded public HTTP loader. No keys, arbitrary endpoints, or redirects."""
import csv
import hashlib
import io
import json
import math
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path

from .access import AccessDenied, Window, UTC, iso, authorize_request

BASE_URL = "https://api.bybit.com"


class DataError(ValueError):
    pass


class RetrievalError(RuntimeError):
    pass


def canonical(value) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False, indent=2) + "\n").encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_new(path: Path, data: bytes):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RetrievalError("HTTP redirect refused; endpoint allowlist cannot be bypassed")


class PublicClient:
    def __init__(self, transport=None, sleep=time.sleep, max_requests=256, retries=3, timeout=15):
        if not 1 <= max_requests <= 256 or not 1 <= retries <= 3 or not 0 < timeout <= 15:
            raise ValueError("Network bounds exceeded")
        self.transport = transport or self._http
        self.sleep, self.max_requests, self.retries, self.timeout = sleep, max_requests, retries, timeout
        self.calls = []
        self.opener = urllib.request.build_opener(NoRedirect())

    def _http(self, url):
        req = urllib.request.Request(url, headers={"User-Agent": "BTC-Research-Phase1/0.1", "Accept": "application/json"}, method="GET")
        with self.opener.open(req, timeout=self.timeout) as response:
            body = response.read(8 * 1024 * 1024 + 1)
            if len(body) > 8 * 1024 * 1024:
                raise RetrievalError("Response exceeds 8 MiB limit")
            return body

    def get(self, path: str, params: dict):
        authorize_request(path, params)  # Before every network request, including injected transports.
        url = BASE_URL + path + "?" + urllib.parse.urlencode(sorted(params.items()))
        for attempt in range(self.retries):
            if len(self.calls) >= self.max_requests:
                raise RetrievalError("Global HTTP request budget exhausted")
            record = {"url": url, "retrieved_at": datetime.now(UTC).isoformat(), "attempt": attempt + 1}
            self.calls.append(record)
            if len(self.calls) > 1:
                self.sleep(0.2)
            try:
                body = self.transport(url)
                record["response_sha256"] = sha256(body)
                payload = json.loads(body)
                if not isinstance(payload, dict) or type(payload.get("retCode")) is not int:
                    raise DataError("Invalid Bybit envelope/retCode")
                record["retCode"] = payload["retCode"]
                if payload["retCode"] in (10006, 10016):
                    raise RetrievalError("Retryable Bybit response code " + str(payload["retCode"]))
                if payload["retCode"] != 0:
                    raise DataError("Bybit API rejected request; retCode=" + str(payload["retCode"]))
                result = payload.get("result")
                if not isinstance(result, dict) or result.get("category") != "linear" or not isinstance(result.get("list"), list):
                    raise DataError("Invalid Bybit result/category/list")
                if path.endswith("/kline") and result.get("symbol") != "BTCUSDT":
                    raise DataError("Unexpected response symbol")
                record["status"] = "OK"
                return result
            except urllib.error.HTTPError as exc:
                record.update(status="HTTP_ERROR", http_status=exc.code)
                if exc.code not in (429, 500, 502, 503, 504):
                    raise RetrievalError(f"HTTP {exc.code}: public Bybit endpoint unavailable; no bypass attempted") from exc
                error = f"HTTP {exc.code}"
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, RetrievalError) as exc:
                record.update(status="NETWORK_ERROR", error=str(exc))
                error = str(exc)
            except (json.JSONDecodeError, UnicodeDecodeError, DataError) as exc:
                record.update(status="SCHEMA_OR_API_ERROR", error=str(exc))
                raise DataError(str(exc)) from exc
            if attempt + 1 < self.retries:
                self.sleep(min(0.5 * 2 ** attempt, 2.0))
        raise RetrievalError(f"Request failed after {self.retries} bounded attempts: {error}")


@dataclass(frozen=True)
class Candle:
    open_time: int
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float

    def row(self, step):
        return [str(self.open_time), iso(self.open_time), iso(self.open_time + step)] + [repr(x) for x in (self.open, self.high, self.low, self.close, self.volume, self.turnover)]


def row_timestamp(row):
    if not isinstance(row, list) or len(row) != 7 or not isinstance(row[0], str) or not row[0].isdigit():
        raise DataError("Kline row must have seven string fields and integer timestamp")
    return int(row[0])


def parse_candle(row, window: Window, now_ms: int):
    ts = row_timestamp(row)
    window.authorize_bar(ts)  # Validate timestamp before consuming OHLC values.
    if any(not isinstance(v, str) for v in row):
        raise DataError("Bybit decimal fields must be strings")
    try:
        numbers = [float(v) for v in row[1:]]
    except (ValueError, OverflowError) as exc:
        raise DataError("Non-numeric kline field") from exc
    if not all(math.isfinite(v) for v in numbers):
        raise DataError("Non-finite kline value")
    o, h, low, c, volume, turnover = numbers
    if min(o, h, low, c) <= 0 or not low <= o <= h or not low <= c <= h or volume < 0 or turnover < 0:
        raise DataError("Invalid OHLC/volume/turnover")
    if ts + window.step > now_ms:
        raise DataError("INCOMPLETE_CANDLE")
    return Candle(ts, *numbers)


def validate_rows(rows, window: Window, now_ms: int):
    window.validate()
    found, signatures, conflicted = {}, {}, set()
    quality = {"received_rows": len(rows), "duplicate_rows": 0, "conflicting_timestamps": [], "invalid_rows": [], "incomplete_rows": []}
    for index, row in enumerate(rows):
        ts = row_timestamp(row)  # Invalid schema is a protocol error, not a repairable price.
        window.authorize_bar(ts)
        sig = tuple(row)
        if ts in signatures:
            quality["duplicate_rows"] += 1
            if sig != signatures[ts]:
                conflicted.add(ts)
        else:
            signatures[ts] = sig
        try:
            bar = parse_candle(row, window, now_ms)
        except DataError as exc:
            key = "incomplete_rows" if str(exc) == "INCOMPLETE_CANDLE" else "invalid_rows"
            quality[key].append({"row_index": index, "open_time": ts, "reason": str(exc)})
            continue
        found.setdefault(ts, bar)
    for ts in conflicted:
        found.pop(ts, None)
    quality["conflicting_timestamps"] = sorted(conflicted)
    quality["unique_received_rows"] = len(signatures)
    quality["missing_open_times"] = [t for t in range(window.anchor, window.end, window.step) if t not in signatures]
    quality["expected_rows"] = (window.end - window.anchor) // window.step
    quality["valid_rows"] = len(found)
    quality["valid_development_rows"] = sum(window.start <= t < window.end for t in found)
    quality["valid_warmup_rows"] = sum(t < window.start for t in found)
    quality["status"] = "VALID" if not any(quality[k] for k in ("conflicting_timestamps", "invalid_rows", "incomplete_rows", "missing_open_times")) else "QUARANTINED"
    return [found[t] for t in sorted(found)], quality


def fetch_candles(client: PublicClient, window: Window, now_ms: int, limit=1000):
    window.validate()
    if type(limit) is not int or not 1 <= limit <= 1000:
        raise ValueError("Invalid page limit")
    rows = []
    cursor = window.anchor
    while cursor < window.end:
        stop = min(cursor + limit * window.step, window.end)
        params = {"category": "linear", "symbol": "BTCUSDT", "interval": window.interval, "start": cursor, "end": stop - 1, "limit": limit}
        result = client.get("/v5/market/kline", params)
        page = result["list"]
        if len(page) > limit:
            raise DataError("API page exceeds requested limit")
        for row in page:
            ts = row_timestamp(row)
            window.authorize_bar(ts)
            if not cursor <= ts < stop:
                raise DataError("API returned candle outside explicit page window")
        rows.extend(page)
        cursor = stop  # Explicit disjoint windows; never infer missing candles or fetch beyond end.
    return validate_rows(rows, window, now_ms)


def fetch_instrument(client: PublicClient):
    result = client.get("/v5/market/instruments-info", {"category": "linear", "symbol": "BTCUSDT"})
    matches = [x for x in result["list"] if isinstance(x, dict) and x.get("symbol") == "BTCUSDT"]
    if len(matches) != 1:
        raise DataError("Expected exactly one BTCUSDT instrument")
    item = matches[0]
    if item.get("contractType") != "LinearPerpetual" or item.get("settleCoin") != "USDT":
        raise DataError("Instrument is not a linear USDT perpetual")
    try:
        values = {"tick_size": item["priceFilter"]["tickSize"], **{k: item["lotSizeFilter"][v] for k, v in {
            "qty_step": "qtyStep", "min_qty": "minOrderQty", "min_notional": "minNotionalValue", "max_market_qty": "maxMktOrderQty", "max_limit_qty": "maxOrderQty"}.items()}}
        if any(not isinstance(v, str) or not math.isfinite(float(v)) or float(v) <= 0 for v in values.values()):
            raise ValueError("Nonpositive/nonfinite metadata")
    except (KeyError, ValueError, TypeError) as exc:
        raise DataError("Missing/invalid instrument constraints") from exc
    return {"instrument": item, "constraints": values, "retrieved_at": client.calls[-1]["retrieved_at"], "source_url": client.calls[-1]["url"],
            "historical_assumption": "HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION", "historical_effective_dates": "UNVERIFIED",
            "minimum_applicability_on_reduce_only_exits": "UNVERIFIED_NOT_USED_IN_STAGE0A", "applies_to_scenario_years": [2023, 2024]}


CSV_FIELDS = ["open_time_ms", "open_time_utc", "end_time_utc", "open", "high", "low", "close", "volume", "turnover"]


def candle_csv(candles, step):
    output = io.StringIO(newline="")
    writer = csv.writer(output, lineterminator="\n")
    writer.writerow(CSV_FIELDS)
    for bar in candles:
        writer.writerow(bar.row(step))
    return output.getvalue().encode("utf-8")


def save_dataset(directory: Path, candles, quality: dict, window: Window, requests: list, synthetic=False):
    window.validate()
    data = candle_csv(candles, window.step)
    name = f"BTCUSDT_{window.year}_{window.interval}.csv"
    manifest = {"schema_version": 1, "phase": "stage0a-development-only", "category": "linear", "symbol": "BTCUSDT", "window": asdict(window),
                "interval_minutes": int(window.interval), "start_utc": iso(window.anchor), "exclusive_end_utc": iso(window.end),
                "csv": name, "csv_sha256": sha256(data), "quality": quality, "requests": requests, "synthetic": synthetic}
    write_new(directory / name, data)
    write_new(directory / (name + ".manifest.json"), canonical(manifest))
    return manifest


def read_dataset(directory: Path, manifest_path: Path, expected: Window, allow_synthetic=False):
    expected.validate()  # Before opening a cache, reject unauthorized requested year/window.
    root = directory.resolve()
    if manifest_path.is_symlink() or manifest_path.resolve().parent != root:
        raise AccessDenied("Cache manifest must be an ordinary direct child of the authorized directory")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("window") != asdict(expected) or manifest.get("category") != "linear" or manifest.get("symbol") != "BTCUSDT" or manifest.get("phase") != "stage0a-development-only":
        raise AccessDenied("Cache range/identity/phase not authorized")
    if (manifest.get("synthetic") is not False and not (allow_synthetic and manifest.get("synthetic") is True)) or manifest.get("quality", {}).get("status") != "VALID":
        raise DataError("Synthetic or quarantined cache cannot produce real Stage-0A results")
    expected_name = f"BTCUSDT_{expected.year}_{expected.interval}.csv"
    if manifest.get("csv") != expected_name:
        raise AccessDenied("Unexpected cache filename")
    path = root / expected_name
    if path.is_symlink() or path.resolve().parent != root:
        raise AccessDenied("Cache data path escapes authorized directory")
    data = path.read_bytes()
    if sha256(data) != manifest.get("csv_sha256"):
        raise DataError("Cache SHA-256 mismatch")
    reader = csv.DictReader(io.StringIO(data.decode("utf-8")))
    if reader.fieldnames != CSV_FIELDS:
        raise DataError("Invalid cache CSV schema")
    rows = []
    for row in reader:
        ts = int(row["open_time_ms"])
        expected.authorize_bar(ts)
        if row["open_time_utc"] != iso(ts) or row["end_time_utc"] != iso(ts + expected.step):
            raise DataError("Cache UTC labels disagree with timestamp")
        rows.append([str(ts)] + [row[k] for k in CSV_FIELDS[3:]])
    candles, quality = validate_rows(rows, expected, int(datetime.now(UTC).timestamp() * 1000))
    if quality["status"] != "VALID":
        raise DataError("Cache no longer passes data quality validation")
    return candles, manifest
