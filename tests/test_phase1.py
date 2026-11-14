"""All prices here are SYNTHETIC UNIT FIXTURES, never research evidence."""
import io
import json
import math
import tempfile
import unittest
import urllib.error
import urllib.parse
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

from research.access import AccessDenied, Window, timestamp, iso, authorize_request
from research.loader import (Candle, DataError, RetrievalError, PublicClient, validate_rows, parse_candle, fetch_candles,
                             fetch_instrument, canonical, sha256, candle_csv, save_dataset, read_dataset)
from research.indicators import ema, rma, atr14, confirmed_pivot, round_stop
from research.stage0a import baseline, risk_cost, describe, percentiles
from research.workflow import EXPECTED_CONFIG, provenance, run_directory, _stable_output
from research import workflow

NOW = timestamp("2026-11-14T00:00:00Z")


def row(t, o="100", h="102", low="98", c="101", v="3", turnover="300"):
    return [str(t), o, h, low, c, v, turnover]


def response(rows, category="linear", symbol="BTCUSDT", code=0):
    return canonical({"retCode": code, "result": {"category": category, "symbol": symbol, "list": rows}})


class AccessTests(unittest.TestCase):
    def test_annual_warmup_and_leap_year(self):
        a, b = Window.annual(2023, "15"), Window.annual(2024, "15")
        self.assertEqual(iso(a.anchor), "2022-12-29T12:00:00.000Z")
        self.assertEqual(iso(b.anchor), "2023-12-29T12:00:00.000Z")
        self.assertEqual((a.end-a.anchor)//a.step, 35280)
        self.assertEqual((b.end-b.anchor)//b.step, 35376)
        self.assertEqual((Window.annual(2024, "60").start-Window.annual(2024, "60").anchor)//3_600_000, 60)

    def test_utc_required(self):
        for bad in ("2023-01-01T00:00:00", "2023-01-01T00:00:00+03:30"):
            with self.assertRaises(AccessDenied):
                timestamp(bad)

    def test_unauthorized_years_and_timeframes(self):
        for year in (2022, 2025, 2026, True):
            with self.assertRaises(AccessDenied):
                Window.annual(year, "15")
        with self.assertRaises(AccessDenied):
            Window.annual(2023, "5")

    def test_exact_end_exclusive_and_alignment(self):
        w = Window.annual(2024, "15")
        w.authorize_bar(w.end-w.step)
        for t in (w.anchor-1, w.end, w.start+1, timestamp("2026-05-01T00:00:00Z")):
            with self.assertRaises(AccessDenied):
                w.authorize_bar(t)

    def test_forged_window_rejected(self):
        good = Window.annual(2024, "15")
        bad = Window(2024, "15", good.start, timestamp("2027-01-01T00:00:00Z"), good.anchor)
        with self.assertRaises(AccessDenied):
            bad.authorize(good.start, good.start+good.step)

    def test_only_public_authorized_paths(self):
        client = PublicClient(transport=lambda _: self.fail("Unauthorized request reached network"), sleep=lambda _: None)
        for path in ("/v5/market/funding/history", "/v5/market/mark-price-kline", "/v5/order/create", "/v5/account/wallet-balance"):
            with self.assertRaises(AccessDenied):
                client.get(path, {"category": "linear", "symbol": "BTCUSDT"})
        self.assertEqual(client.calls, [])

    def test_holdout_request_blocked_before_network(self):
        client = PublicClient(transport=lambda _: self.fail("Holdout request sent"))
        for date in ("2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z", "2026-11-01T00:00:00Z"):
            start = timestamp(date)
            with self.assertRaises(AccessDenied):
                client.get("/v5/market/kline", {"category": "linear", "symbol": "BTCUSDT", "interval": "15", "start": start, "end": start+899999, "limit": 1})

    def test_cache_path_traversal_and_symlink(self):
        for name in ("../2026", "/tmp/future", "20260101"):
            with self.assertRaises(AccessDenied):
                run_directory(name)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/"link.json").symlink_to(root/"missing.json")
            with self.assertRaises(AccessDenied):
                read_dataset(root, root/"link.json", Window.annual(2023, "15"))

    def test_cache_future_manifest_denied_before_price_read(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            metadata = {"window": {"year": 2026}, "category": "linear", "symbol": "BTCUSDT", "phase": "stage0a-development-only"}
            (root/"manifest.json").write_bytes(canonical(metadata))
            with patch.object(Path, "read_bytes", side_effect=AssertionError("Price cache was read")):
                with self.assertRaises(AccessDenied):
                    read_dataset(root, root/"manifest.json", Window.annual(2023, "15"))

    def test_unauthorized_response_bar_denied_before_ohlc_parse(self):
        future = row(timestamp("2025-01-01T00:00:00Z"), o="NOT_PARSED")
        with self.assertRaises(AccessDenied):
            parse_candle(future, Window.annual(2024, "15"), NOW)


class LoaderTests(unittest.TestCase):
    def test_pagination_explicit_limits_reverse_order_and_coverage(self):
        w = Window.annual(2023, "60")
        params_seen = []
        def transport(url):
            p = urllib.parse.parse_qs(urllib.parse.urlsplit(url).query)
            a, b = int(p["start"][0]), int(p["end"][0])+1
            params_seen.append((a, b))
            self.assertLessEqual((b-a)//w.step, 1000)
            return response([row(t) for t in reversed(range(a, b, w.step))])
        client = PublicClient(transport=transport, sleep=lambda _: None)
        bars, quality = fetch_candles(client, w, NOW)
        self.assertEqual(len(params_seen), 9)
        self.assertEqual(params_seen[0][0], w.anchor)
        self.assertEqual(params_seen[-1][1], w.end)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(params_seen, params_seen[1:])))
        self.assertEqual(quality["status"], "VALID")
        self.assertEqual(len(bars), 8820)
        self.assertEqual(bars, sorted(bars, key=lambda b: b.open_time))

    def test_duplicate_removal_and_conflict_quarantine(self):
        w = Window.annual(2023, "60")
        bars, q = validate_rows([row(w.anchor), row(w.anchor)], w, NOW)
        self.assertEqual(len(bars), 1)
        self.assertEqual(q["duplicate_rows"], 1)
        bars, q = validate_rows([row(w.anchor), row(w.anchor, c="100")], w, NOW)
        self.assertEqual(bars, [])
        self.assertEqual(q["conflicting_timestamps"], [w.anchor])
        self.assertEqual(q["status"], "QUARANTINED")

    def test_missing_invalid_and_incomplete_no_interpolation(self):
        w = Window.annual(2023, "60")
        bars, q = validate_rows([row(w.anchor, h="99"), row(w.anchor+w.step)], w, w.anchor+2*w.step-1)
        self.assertEqual(bars, [])
        self.assertEqual(len(q["invalid_rows"]), 1)
        self.assertEqual(len(q["incomplete_rows"]), 1)
        self.assertEqual(q["missing_open_times"][0], w.anchor+2*w.step)
        self.assertEqual(q["status"], "QUARANTINED")

    def test_ohlc_and_numeric_schema(self):
        w = Window.annual(2023, "15")
        for bad in (row(w.anchor, low="101"), row(w.anchor, h="100"), row(w.anchor, c="103"), row(w.anchor, o="0"), row(w.anchor, v="-1"), row(w.anchor, c="nan"), row(w.anchor, turnover="inf"), row(w.anchor, c="bad")):
            with self.assertRaises(DataError):
                parse_candle(bad, w, NOW)

    def test_schema_and_nonzero_api_code_fail_closed(self):
        for body in (b"not json", canonical({"retCode": "0"}), response([], category="spot"), response([], code=10001)):
            c = PublicClient(transport=lambda _, body=body: body, sleep=lambda _: None)
            with self.assertRaises(DataError):
                c.get("/v5/market/instruments-info", {"category": "linear", "symbol": "BTCUSDT"})
            self.assertEqual(len(c.calls), 1)

    def test_wrong_symbol_and_invalid_page_limit(self):
        w = Window.annual(2023,"15")
        c = PublicClient(transport=lambda _: response([],symbol="ETHUSDT"), sleep=lambda _: None)
        with self.assertRaisesRegex(DataError,"symbol"):
            fetch_candles(c,w,NOW)
        with self.assertRaises(ValueError):
            fetch_candles(c,w,NOW,limit=1001)

    def test_retry_backoff_and_global_budget(self):
        waits = []
        c = PublicClient(transport=lambda _: response([], code=10006), sleep=waits.append, max_requests=2)
        with self.assertRaises(RetrievalError):
            c.get("/v5/market/instruments-info", {"category": "linear", "symbol": "BTCUSDT"})
        self.assertEqual(len(c.calls), 2)
        self.assertIn(0.5, waits)

    def test_403_is_terminal_without_retry_or_bypass(self):
        def denied(url):
            raise urllib.error.HTTPError(url, 403, "Forbidden", {}, io.BytesIO(b"denied"))
        c = PublicClient(transport=denied, sleep=lambda _: None)
        with self.assertRaisesRegex(RetrievalError, "HTTP 403"):
            fetch_instrument(c)
        self.assertEqual(len(c.calls), 1)

    def test_server_out_of_page_row_refused(self):
        w = Window.annual(2023, "60")
        c = PublicClient(transport=lambda _: response([row(w.end-w.step)]), sleep=lambda _: None)
        with self.assertRaisesRegex(DataError, "page window"):
            fetch_candles(c, w, NOW)

    def test_current_metadata_constraints_and_assumption(self):
        item = {"symbol": "BTCUSDT", "contractType": "LinearPerpetual", "settleCoin": "USDT", "priceFilter": {"tickSize": "0.1"},
                "lotSizeFilter": {"qtyStep": "0.001", "minOrderQty": "0.001", "minNotionalValue": "5", "maxMktOrderQty": "100", "maxOrderQty": "100"}}
        c = PublicClient(transport=lambda _: response([item]), sleep=lambda _: None)
        m = fetch_instrument(c)
        self.assertEqual(m["constraints"]["tick_size"], "0.1")
        self.assertEqual(m["historical_assumption"], "HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION")
        self.assertEqual(m["historical_effective_dates"], "UNVERIFIED")

    def test_missing_metadata_not_guessed(self):
        c = PublicClient(transport=lambda _: response([{"symbol": "BTCUSDT", "contractType": "LinearPerpetual", "settleCoin": "USDT"}]), sleep=lambda _: None)
        with self.assertRaises(DataError):
            fetch_instrument(c)

    def test_deterministic_csv_and_sha(self):
        w = Window.annual(2023, "15")
        bars = [parse_candle(row(w.anchor), w, NOW)]
        self.assertEqual(candle_csv(bars, w.step), candle_csv(list(bars), w.step))
        self.assertEqual(sha256(candle_csv(bars, w.step)), sha256(candle_csv(list(bars), w.step)))

    def test_cache_roundtrip_hash_and_synthetic_guard(self):
        w = Window.annual(2023, "60")
        bars, q = validate_rows([row(t) for t in range(w.anchor, w.end, w.step)], w, NOW)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            m = save_dataset(root, bars, q, w, [], synthetic=True)
            path = root/(m["csv"]+".manifest.json")
            with self.assertRaisesRegex(DataError, "Synthetic"):
                read_dataset(root, path, w)
            loaded, _ = read_dataset(root, path, w, allow_synthetic=True)
            self.assertEqual(loaded, bars)
            with (root/m["csv"]).open("ab") as f:
                f.write(b"tamper")
            with self.assertRaisesRegex(DataError, "SHA-256"):
                read_dataset(root, path, w, allow_synthetic=True)


class NumericalTests(unittest.TestCase):
    def test_ema_first_value_seed(self):
        self.assertEqual(ema([10.0, 13.0, 16.0], 2), [10.0, 12.0, 44.0/3.0])

    def test_wilder_sma_seed_then_recursion(self):
        result = rma([float(i) for i in range(1, 16)], 14)
        self.assertEqual(result[:13], [None]*13)
        self.assertEqual(result[13], 7.5)
        self.assertAlmostEqual(result[14], (7.5*13+15)/14)

    def test_na_not_converted_to_zero(self):
        self.assertEqual(rma([None, 2.0, 4.0, 6.0], 2), [None, None, 3.0, 4.5])

    def test_atr_first_tr_and_gap(self):
        bars = [Candle(0,10,11,9,10,1,1)] + [Candle(i*900000,15,16,14,15,1,1) for i in range(1,14)]
        values = atr14(bars)
        self.assertEqual(values[:13], [None]*13)
        self.assertAlmostEqual(values[13], (2+6+12*2)/14)

    def test_strict_pivot_first_available_three_right_bars_later(self):
        bars = [Candle(i*900000,10,12,low,10,1,1) for i, low in enumerate([7,6,5,1,5,6,7])]
        self.assertIsNone(confirmed_pivot(bars, 5, "Long"))
        self.assertEqual(confirmed_pivot(bars, 6, "Long"), (3, 1))
        bars[2] = Candle(1800000,10,12,1,10,1,1)
        self.assertIsNone(confirmed_pivot(bars, 6, "Long"))

    def test_strict_high_pivot_and_tie(self):
        bars = [Candle(i*900000,10,high,9,10,1,1) for i, high in enumerate([11,12,13,19,13,12,11])]
        self.assertEqual(confirmed_pivot(bars, 6, "Short"), (3,19))
        bars[4] = Candle(3600000,10,19,9,10,1,1)
        self.assertIsNone(confirmed_pivot(bars, 6, "Short"))

    def test_stop_rounding_and_cost_proxy(self):
        self.assertEqual(round_stop(98.07, "0.1", "Long"), (980, 98.0))
        self.assertEqual(round_stop(98.07, "0.1", "Short"), (981, 98.1))
        risk, cost, ratio = risk_cost(100,98)
        self.assertEqual(risk,2)
        self.assertAlmostEqual(cost,0.1485)
        self.assertAlmostEqual(ratio,2/0.1485)

    def test_descriptive_percentiles(self):
        self.assertEqual(percentiles(list(range(101))), {str(p): float(p) for p in (5,10,25,50,75,90,95)})
        self.assertEqual(percentiles([])["50"], None)


class BaselineTests(unittest.TestCase):
    def fixture(self):
        bars = [Candle(i*900000,101.2,102,100,101.5,1,1) for i in range(11)]
        bars[10] = Candle(9000000,102.5,104.2,102,104,1,1)
        return bars, [101.0]*11, [99.0]*11, [4.0]*11

    def test_latest_pullback_and_closed_trigger(self):
        bars,f,s,a = self.fixture()
        self.assertEqual(baseline(bars,10,f,s,a), ("Long",8,None))

    def test_one_right_bar_touch_not_eligible(self):
        bars,f,s,a = self.fixture()
        for i in range(5,9):
            bars[i] = Candle(i*900000,103,104,102,103,1,1)
        self.assertEqual(baseline(bars,10,f,s,a)[2], "NO_ELIGIBLE_PULLBACK")

    def test_trigger_equality_and_ema50_sequence_rejected(self):
        bars,f,s,a = self.fixture()
        bars[10] = Candle(9000000,101.5,103,101,102,1,1)
        self.assertEqual(baseline(bars,10,f,s,a)[2], "TRIGGER_NOT_MET")
        bars,f,s,a = self.fixture()
        s[8] = bars[8].close
        self.assertEqual(baseline(bars,10,f,s,a)[2], "EMA50_SEQUENCE_VIOLATION")

    def test_short_is_exact_mirror(self):
        bars,f,s,a = self.fixture()
        mirrored = [Candle(b.open_time,200-b.open,200-b.low,200-b.high,200-b.close,b.volume,b.turnover) for b in bars]
        self.assertEqual(baseline(mirrored,10,[200-x for x in f],[200-x for x in s],a), ("Short",8,None))

    def test_prefix_causality_determinism_and_annual_signal_boundaries(self):
        w = Window.annual(2023, "15")
        bars, previous = [], 100.0
        for i in range(1000):
            close = 100+0.02*i+math.sin(i/7)+(1.8 if i%13==0 else 0)
            bars.append(Candle(w.anchor+i*w.step,previous,max(previous,close)+0.8+0.01*(i%4),min(previous,close)-0.8-0.01*(i%3),close,1,100))
            previous = close
        summary, full = describe(bars,w,"0.1",EXPECTED_CONFIG)
        self.assertGreater(len(full),0, "Non-vacuous causal fixture must have raw opportunities")
        self.assertGreater(summary["groups"]["All"]["confirmed_pivot_survivors"],0)
        self.assertGreater(summary["groups"]["All"]["stop_range_survivors"],0)
        prefix = bars[:650]
        _, partial = describe(prefix,w,"0.1",EXPECTED_CONFIG)
        self.assertEqual(partial, [x for x in full if x["signal_close_utc"] <= iso(prefix[-1].open_time+w.step)])
        self.assertTrue(all(w.start <= timestamp(x["signal_close_utc"]) < w.end for x in full))
        self.assertTrue(all(x["pivot_confirmed_at_utc"] is None or x["pivot_confirmed_at_utc"] <= x["signal_close_utc"] for x in full))
        self.assertEqual(canonical(summary),canonical(describe(bars,w,"0.1",EXPECTED_CONFIG)[0]))
        self.assertEqual(summary["K_cost_stop"],"UNSET")
        self.assertEqual(summary["evaluated_signal_bars"], len(bars)-239)

    def test_analysis_rejects_future_input_and_wrong_profile_or_k(self):
        w=Window.annual(2023,"15")
        with self.assertRaises(AccessDenied):
            describe([Candle(timestamp("2026-01-01T00:00:00Z"),1,2,1,2,1,1)],w,"0.1",EXPECTED_CONFIG)
        with self.assertRaises(AccessDenied):
            describe([],Window.annual(2023,"60"),"0.1",EXPECTED_CONFIG)
        with self.assertRaises(AccessDenied):
            describe([],w,"0.1",dict(EXPECTED_CONFIG,K_cost_stop=10))


class ProvenanceTests(unittest.TestCase):
    def test_spec_and_tag_unchanged_and_config_unset(self):
        config, source = provenance()
        self.assertEqual(config["K_cost_stop"], "UNSET")
        self.assertEqual(source["design_commit"], "ac8fc4bb9b66a59c7224aaec1630a594b41d7e80")
        self.assertEqual(source["research_parameter_freeze"], "OPEN")

    def test_report_overwrite_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"report.json"
            _stable_output(path,b"same")
            _stable_output(path,b"same")
            with self.assertRaises(DataError):
                _stable_output(path,b"different")

    def test_network_block_produces_honest_not_run_reports(self):
        def denied(url):
            raise urllib.error.HTTPError(url,403,"Fixture denial",{},io.BytesIO(b"fixture"))
        client=PublicClient(transport=denied,sleep=lambda _:None)
        origin={"design_commit":"unit-fixture", "spec_sha256":"unit-fixture", "config_sha256":"unit-fixture"}
        with tempfile.TemporaryDirectory() as temp:
            with patch.object(workflow,"ROOT",Path(temp)), patch.object(workflow,"provenance",return_value=(EXPECTED_CONFIG,origin)), patch.object(workflow,"PublicClient",return_value=client):
                result=workflow.run_fetch()
                self.assertEqual(result["years"],{"2023":"NOT_RUN","2024":"NOT_RUN"})
                self.assertEqual(len(client.calls),1)
                self.assertEqual(list(Path(temp).rglob("*.csv")),[])
                summary=json.loads((Path(result["report"]).parent/"2023.json").read_text())
                self.assertIsNone(summary["descriptive_statistics"])
