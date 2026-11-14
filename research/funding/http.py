"""Unauthenticated bounded HTTP; no redirects, fallback hosts or credentials."""
import json
import socket
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

from research.access import AccessDenied, UTC
from research.loader import canonical, sha256
from .policy import MARK, authorize_request, authorize_response

BASE_URL = "https://api.bybit.com"


class AcquisitionError(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise AcquisitionError("REDIRECT_REFUSED")


class Client:
    def __init__(self, transport=None, sleep=time.sleep, monotonic=time.monotonic, retries=3, max_requests=8192, interval=.15):
        if type(retries) is not int or not 1 <= retries <= 3 or type(max_requests) is not int or not 1 <= max_requests <= 8192 or interval < .15:
            raise ValueError("NETWORK_BOUNDS_EXCEEDED")
        self.transport = transport or self._http
        self.sleep, self.monotonic = sleep, monotonic
        self.retries, self.max_requests, self.interval = retries, max_requests, interval
        self.calls, self.bodies = [], {}
        self.lock, self.next_request, self.forbidden = threading.Lock(), 0., False

    @staticmethod
    def _http(url):
        opener = urllib.request.build_opener(NoRedirect())
        req = urllib.request.Request(url, headers={"User-Agent": "BTC-Research-Phase4A/1", "Accept": "application/json"}, method="GET")
        with opener.open(req, timeout=15) as response:
            body = response.read(4*1024*1024+1)
            if len(body) > 4*1024*1024:
                raise AcquisitionError("RESPONSE_SIZE_LIMIT")
            return body

    def get(self, period, path, params, settlements=()):
        for attempt in range(1, self.retries+1):
            authorize_request(period, path, params, settlements)  # Every attempt, including injected transports.
            with self.lock:
                if self.forbidden:
                    raise AcquisitionError("HTTP_403_CIRCUIT_OPEN_NO_BYPASS")
                if len(self.calls) >= self.max_requests:
                    raise AcquisitionError("GLOBAL_REQUEST_BUDGET_EXHAUSTED")
                delay = max(0., self.next_request-self.monotonic())
                if delay:
                    self.sleep(delay)
                self.next_request = self.monotonic()+self.interval
                record = {"request_id": len(self.calls)+1, "actor": "phase4a-public-data-loader", "purpose": "DEVELOPMENT_FUNDING_MARK_EVIDENCE",
                          "period": period.public(), "path": path, "params": dict(params), "attempt": attempt,
                          "retrieved_at_utc": datetime.now(UTC).isoformat(), "status": "PENDING"}
                self.calls.append(record)
            url = BASE_URL+path+"?"+urllib.parse.urlencode(sorted(params.items()))
            try:
                body = self.transport(url)
                if not isinstance(body, bytes) or len(body) > 4*1024*1024:
                    raise AcquisitionError("INVALID_OR_OVERSIZED_BODY")
                record.update(response_sha256=sha256(body), response_bytes=len(body))
                payload = json.loads(body)
                if not isinstance(payload, dict) or type(payload.get("retCode")) is not int:
                    raise ValueError("INVALID_BYBIT_ENVELOPE")
                record["retCode"] = payload["retCode"]
                if payload["retCode"] in (10006, 10016):
                    raise AcquisitionError("RETRYABLE_API_CODE")
                if payload["retCode"] != 0:
                    raise ValueError("API_NONZERO_RETCODE")
                result = payload.get("result")
                if not isinstance(result, dict) or result.get("category") != "linear" or not isinstance(result.get("list"), list):
                    raise ValueError("INVALID_RESULT_CATEGORY_OR_LIST")
                if path == MARK and result.get("symbol") != "BTCUSDT":
                    raise ValueError("INVALID_MARK_SYMBOL")
                authorize_response(period, path, params, result["list"], settlements)
                # Unauthorized bodies are never cached/exported, including on HTTP 200.
                with self.lock:
                    self.bodies[record["request_id"]] = body
                record["status"] = "OK"
                return result["list"]
            except urllib.error.HTTPError as exc:
                record.update(status="HTTP_ERROR", http_status=exc.code, reason="PUBLIC_ENDPOINT_HTTP_ERROR")
                if exc.fp is not None:
                    error_body=exc.read(4*1024*1024)
                    record.update(response_sha256=sha256(error_body),response_bytes=len(error_body),error_body_retained=False)
                if exc.code == 403:
                    with self.lock:
                        self.forbidden = True
                    raise AcquisitionError("HTTP_403_PUBLIC_ACCESS_FORBIDDEN_NO_BYPASS") from None
                if exc.code not in (429, 500, 502, 503, 504):
                    raise AcquisitionError("TERMINAL_HTTP_ERROR") from None
            except AccessDenied:
                record.update(status="ACCESS_DENIED_RESPONSE", reason="RESPONSE_OUTSIDE_ALLOWLIST_NOT_CACHED")
                raise
            except (ValueError, TypeError, KeyError, UnicodeError):
                record.update(status="SCHEMA_OR_API_ERROR", reason="INVALID_PUBLIC_RESPONSE")
                raise AcquisitionError("INVALID_PUBLIC_RESPONSE") from None
            except (urllib.error.URLError, TimeoutError, socket.timeout, OSError, AcquisitionError) as exc:
                code = str(exc) if isinstance(exc, AcquisitionError) else type(exc).__name__
                record.update(status="NETWORK_ERROR", reason=code)
                if code == "REDIRECT_REFUSED":
                    raise AcquisitionError(code) from None
            if attempt < self.retries:
                self.sleep(min(2., .5*2**(attempt-1)))
        raise AcquisitionError("BOUNDED_RETRIES_EXHAUSTED")
