"""Deterministic synthetic lifecycle tests; never expose real accounting values."""
import json
import math
import socket
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from research.access import AccessDenied, Window
from research.indicators import atr14, confirmed_pivot
from research.loader import Candle, canonical, sha256
from research.stage0b.engine import Engine
from research.stage0b.features import Features, Setup, adx14, build_features, confirmed_hour_index, regime_pass, rsi14, volume_pass, momentum_pass, quality_pass
from research.stage0b.guard import ROOT, preflight, _same_frozen_file
from research.stage0b.model import FundingEvidence, FundingMissingError, IntegrityError, Plan, size_steps
from research.stage0b.output import no_financial_outputs, restricted_directory, validate_path_summary, write_private, write_public_summary
from research.stage0b.runner import frequency_diagnostic, offline_only
from research.stage0b.audit import check_summary


def config():
    return json.loads((ROOT / "configs/research_v0.2.2.json").read_text())


def setup(index=239, pullback=235, R=True, **changes):
    values = dict(index=index, direction="Long", pullback=pullback, pivot_index=index-5, entry_ref=100., atr=1., sl=98.,
                  sl_ticks=980, tp1=103., tp2=105., risk=2., cost=.1485, stop_valid=True, cost_valid=True,
                  levels_valid=True, filters=tuple(zip("RHVMQ", (R, True, True, True, True))))
    values.update(changes)
    return Setup(**values)


def bar(t, o=100., h=101., l=99., c=100.):
    return Candle(t, o, h, l, c, 10., 1000.)


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.w = Window.annual(2023, "15")
        self.c = config()
        self.e = Engine("C01", self.w, self.c, "synthetic")
        self.e.reset_day(self.w.start)

    def queue(self, steps=1000, direction="Long", **changes):
        sign = 1 if direction == "Long" else -1
        values = dict(entry_id="synthetic-entry", direction=direction, signal_time=self.w.start,
                      signal_bar_open=self.w.start-self.w.step, pullback=235, pivot_index=230,
                      entry_ref=100., sl=100-sign*2, tp1=100+sign*3, tp2=100+sign*5,
                      total_steps=steps, tp1_steps=steps//2, tp2_steps=steps-steps//2,
                      signal_balance=10000., risk_budget=25., planned_risk=2.)
        values.update(changes)
        p = Plan(**values)
        self.e.queue(p)
        self.e._gate("G", direction)
        return p

    def exits(self):
        return [v for v in self.e._ledger if v["event"] == "EXIT_LEG"]

    def test_same_entry_bar_stop_first_both_directions(self):
        for direction in ("Long", "Short"):
            with self.subTest(direction=direction):
                self.setUp()
                self.queue(direction=direction)
                b = bar(self.w.start, h=106., l=94.)
                self.e.process_open(b)
                self.e.process_intrabar(b)
                self.assertEqual([x["kind"] for x in self.exits()], ["STOP", "STOP"])
                self.assertEqual(self.e.completed, 1)
                self.assertEqual(self.e.quality["UNCERTAIN_INTRABAR_ORDER"], 1)
                self.e.finish()

    def test_gap_through_stop_uses_open_not_stop(self):
        self.queue()
        self.e.process_open(bar(self.w.start))
        self.e.process_open(bar(self.w.start+self.w.step, o=95., h=96., l=94., c=95.))
        self.assertTrue(all(x["fill"] == 95.*.9998 for x in self.exits()))
        self.assertEqual(self.e.completed, 1)

    def test_entry_beyond_stop_records_entry_and_immediate_exits(self):
        self.queue()
        self.e.process_open(bar(self.w.start, o=97., h=99., l=96., c=97.))
        self.assertEqual((self.e.filled, self.e.completed), (1, 1))
        self.assertEqual(self.e.quality["ENTRY_AT_OR_BEYOND_SL"], 1)
        self.assertEqual(self.e.quality["EXECUTION_ANOMALY"], 1)

    def test_entry_exact_stop_raw_is_anomaly_even_friction_above_stop(self):
        self.queue()
        self.e.process_open(bar(self.w.start, o=98., h=99., l=97., c=98.))
        self.assertEqual(self.e.quality["EXECUTION_ANOMALY"], 1)

    def test_open_both_targets_are_frozen_no_open_improvement(self):
        self.queue()
        b = bar(self.w.start, o=110., h=120., l=1., c=100.)
        self.e.process_open(b)
        self.e.process_intrabar(b)
        self.assertEqual([x["fill"] for x in self.exits()], [103.*.9998, 105.*.9998])
        self.assertEqual(self.e.quality["MARGIN_MODEL_EVENT"], 0)

    def test_open_partial_then_remaining_stop(self):
        self.queue(steps=1001)
        b = bar(self.w.start, o=104., h=106., l=97., c=100.)
        self.e.process_open(b)
        self.assertEqual(self.e.position.remaining, [0, 501])
        self.assertEqual(self.e._settled, 10000.)
        self.e.process_intrabar(b)
        self.assertEqual([(x["kind"], x["quantity_steps"]) for x in self.exits()], [("TP", 500), ("STOP", 501)])
        self.e.finish()

    def test_friction_crossing_is_not_raw_tp_trigger(self):
        self.queue(tp1=100.01, tp2=101.)
        b = bar(self.w.start, h=100.005, l=99.9)
        self.e.process_open(b)
        self.e.process_intrabar(b)
        self.assertEqual(len(self.exits()), 0)
        self.assertEqual(self.e.quality["FILL_FRICTION_CROSSED_TP"], 1)
        self.assertEqual(self.e.quality["EXECUTION_ANOMALY"], 1)

    def test_margin_rejection_no_fee_no_retry_pullback_stays_consumed(self):
        p = self.queue(steps=150000)
        self.e.process_open(bar(self.w.start, o=200., h=201., l=199., c=200.))
        self.assertEqual((self.e.filled, self.e.rejected_margin, self.e._cash), (0, 1, 10000.))
        self.assertIn((p.direction, p.pullback), self.e.consumed)
        self.assertIsNone(self.e.pending)
        self.e.finish()

    def test_no_margin_extremum_after_definitive_stop(self):
        self.queue(steps=150000)
        b = bar(self.w.start, h=106., l=1.)
        self.e.process_open(b)
        self.e.process_intrabar(b)
        self.assertEqual(self.e.quality["MARGIN_MODEL_EVENT"], 0)
        self.assertEqual(self.e.completed, 1)

    def test_real_gap_margin_event_invalidates_without_dropping_trade(self):
        self.queue(steps=150000)
        self.e.process_open(bar(self.w.start))
        self.e.process_open(bar(self.w.start+self.w.step, o=1., h=2., l=.5, c=1.))
        self.e.finish()
        self.assertEqual(self.e.quality["MARGIN_MODEL_EVENT"], 1)
        self.assertEqual(self.e.completed, 1)
        self.assertEqual(self.e.public_summary()["execution_model_validity"], "INVALID_MARGIN_MODEL_EVENT")

    def test_remaining_margin_uses_partial_quantity_and_updated_cash(self):
        self.queue(steps=150000, sl=1., planned_risk=99.)
        self.e.process_open(bar(self.w.start, o=104., h=104., l=100., c=104.))
        self.assertEqual(sum(self.e.position.remaining), 75000)
        self.e._margin(50., self.w.start, "TEST")
        self.assertEqual(self.e.quality["MARGIN_MODEL_EVENT"], 0)

    def test_no_duplicate_exit_or_overlapping_entry(self):
        p = self.queue()
        with self.assertRaises(IntegrityError):
            self.e.queue(p)
        self.e.process_open(bar(self.w.start, o=104., h=104., l=100.))
        with self.assertRaises(IntegrityError):
            self.e._exit_leg(0, 103., self.w.start, "TEST", "TP")
        self.e.assert_integrity()

    def test_busy_diagnostics_do_not_consume_or_resize(self):
        self.queue()
        self.e.process_open(bar(self.w.start))
        original = self.e.position.plan
        self.e.offer(setup(index=243, pullback=240), self.w.start+3*self.w.step)
        self.assertEqual(self.e.after["F"], 1)
        self.assertEqual(self.e.rejections["G:POSITION_BUSY"], 1)
        self.assertNotIn(("Long", 240), self.e.consumed)
        self.assertEqual(self.e.position.plan, original)

    def test_repeated_pullback_rejected_after_full_exit(self):
        self.queue()
        self.e.process_open(bar(self.w.start, o=110., h=110., l=109.))
        self.e.offer(setup(), self.w.start+self.w.step)
        self.assertEqual(self.e.rejections["G:CONSUMED_PULLBACK"], 1)

    def test_partial_does_not_settle_or_trip_daily_stop(self):
        self.queue(steps=100000)
        self.e.process_open(bar(self.w.start, o=104., h=104., l=100.))
        self.assertEqual(self.e._settled, 10000.)
        self.assertFalse(self.e.daily_stop)
        self.e.reset_day(self.w.start+86400000)
        self.assertEqual(self.e._day_start, 10000.)

    def test_full_settlement_daily_stop_and_utc_reset(self):
        self.queue(steps=100000)
        b = bar(self.w.start, h=101., l=97.)
        self.e.process_open(b)
        self.e.process_intrabar(b)
        self.assertTrue(self.e.daily_stop)
        self.e.offer(setup(index=243, pullback=240), self.w.start+3*self.w.step)
        self.assertEqual(self.e.daily_blocked, 1)
        prior_settled = self.e._settled
        self.e.reset_day(self.w.start+86400000)
        self.assertFalse(self.e.daily_stop)
        self.assertEqual(self.e._day_start, prior_settled)

    def test_midnight_prior_bar_exit_precedes_new_day(self):
        t = self.w.start+86400000-self.w.step
        self.queue(steps=100000, signal_time=t, signal_bar_open=t-self.w.step)
        b = bar(t, h=101., l=97.)
        self.e.process_open(b)
        self.e.process_intrabar(b)
        self.assertTrue(self.e.daily_stop)
        self.e.reset_day(t+self.w.step)
        self.assertFalse(self.e.daily_stop)
        events = [x["event"] for x in self.e._ledger]
        self.assertLess(events.index("POSITION_CLOSED"), len(events)-1)
        self.assertEqual(events[-1], "UTC_DAY_RESET")

    def test_censor_keeps_exposure_and_annual_reset_is_independent(self):
        self.queue()
        self.e.process_open(bar(self.w.start))
        self.e.finish()
        self.assertEqual((self.e.completed, self.e.censored), (0, 1))
        self.assertIsNotNone(self.e.position)
        new = Engine("C01", Window.annual(2024, "15"), self.c, "new-year")
        self.assertEqual(new._cash, 10000.)
        self.assertEqual(new.consumed, set())
        self.assertEqual(new._ledger, [])
        with self.assertRaises(IntegrityError):
            self.e.process_open(bar(self.w.start))

    def test_entry_must_be_next_open(self):
        self.queue()
        with self.assertRaises(IntegrityError):
            self.e.process_open(bar(self.w.start+self.w.step))

    def test_count_conservation_fails_closed(self):
        self.e.filled = 1
        with self.assertRaises(IntegrityError):
            self.e.assert_integrity()


class FeatureAndGuardTests(unittest.TestCase):
    def test_rsi_seed_and_zero_special_cases(self):
        for closes, expected in (([10.]*30, 50.), (list(range(30)), 100.), (list(range(30, 0, -1)), 0.)):
            result = rsi14(closes)
            self.assertTrue(all(x is None for x in result[:14]))
            self.assertEqual(result[14], expected)

    def test_adx_wilder_seed_and_strict_dm_ties(self):
        bars = [bar(i*900000, h=101.+i, l=99.-i) for i in range(40)]
        result = adx14(bars, atr14(bars))
        self.assertTrue(all(x is None for x in result[:27]))
        self.assertEqual(result[27], 0.)

    def test_regime_inclusive_boundaries_and_96_prior_only(self):
        self.assertTrue(regime_pass(20., 101., 100., 4., [2.]*96))
        self.assertFalse(regime_pass(19.99, 101., 100., 4., [2.]*96))
        self.assertFalse(regime_pass(20., 101., 100., 4., [2.]*95))
        self.assertFalse(regime_pass(20., 101., 100., 4.01, [2.]*96))

    def test_htf_uses_execution_bar_open_not_signal_close(self):
        ends = [3600000, 7200000, 10800000]
        self.assertEqual(confirmed_hour_index(ends, 6300000), 0)
        self.assertEqual(confirmed_hour_index(ends, 7200000), 1)
        self.assertEqual(confirmed_hour_index(ends, 0), -1)

    def test_volume_momentum_quality_inclusive_thresholds(self):
        self.assertTrue(volume_pass(12., [10.]*20))
        self.assertFalse(volume_pass(11.999, [10.]*20))
        self.assertTrue(volume_pass(0., [0.]*20))
        self.assertFalse(volume_pass(float("nan"), [10.]*20))
        self.assertFalse(volume_pass(12., [10.]*19))
        for direction, boundary, rejected in (("Long", 55., 54.999), ("Short", 45., 45.001)):
            self.assertTrue(momentum_pass(boundary, direction))
            self.assertFalse(momentum_pass(rejected, direction))
            self.assertFalse(momentum_pass(None, direction))
        self.assertTrue(quality_pass(1.2, 1.8, 1., 2., [3., 5.]))
        self.assertFalse(quality_pass(1.2, 1.8, 1., 2., []))
        self.assertFalse(quality_pass(1.2, 1.8, 1., 2., [2.999, 5.]))
        self.assertFalse(quality_pass(1.201, 1.8, 1., 2., [3.]))
        self.assertFalse(quality_pass(1.2, 1.801, 1., 2., [3.]))

    def test_pivot_only_after_three_right_bars_and_strict(self):
        bars = [bar(i*900000, l=(95. if i == 3 else 99.)) for i in range(10)]
        self.assertIsNone(confirmed_pivot(bars, 5, "Long"))
        self.assertEqual(confirmed_pivot(bars, 6, "Long"), (3, 95.))
        changed = list(bars)
        changed[5] = replace(changed[5], low=95.)
        self.assertIsNone(confirmed_pivot(changed, 6, "Long"))

    def fixture(self, count=900):
        w = Window.annual(2023, "15")
        bars = []
        for i in range(count):
            prev = 100.+.02*(i-1)+math.sin((i-1)/6)
            close = 100.+.02*i+math.sin(i/6)+(1.8 if i % 13 == 0 else 0.)
            bars.append(bar(w.anchor+i*w.step, prev, max(prev, close)+.8+.01*(i % 4), min(prev, close)-.8-.01*(i % 3), close))
        hourly = [bar(w.anchor+i*3600000, 100.+i*.08, 102.+i*.08, 98.+i*.08, 100.+i*.08) for i in range((count+3)//4)]
        return w, bars, hourly

    def test_future_append_cannot_change_prior_setup_or_htf(self):
        w, bars, hourly = self.fixture()
        all_features = build_features(bars, hourly, w, config())
        prefix = build_features(bars[:700], hourly[:175], w, config())
        self.assertEqual(all_features.setups[:700], prefix.setups)
        self.assertGreater(sum(s is not None for s in prefix.setups), 0)
        altered = list(hourly)
        for i in range(175, len(hourly)):
            altered[i] = replace(altered[i], close=100000.)
        changed = build_features(bars, altered, w, config())
        self.assertEqual(changed.setups[:700], all_features.setups[:700])
        for s in all_features.setups:
            if s and s.pivot_index is not None:
                self.assertTrue(3 <= s.pivot_age <= 80)

    def test_two_valid_partial_quantities_and_invalid_partial_rejects_all(self):
        s = setup(entry_ref=20000., sl=19900., tp1=20150., tp2=20250., risk=100., cost=29.925)
        c = config()
        self.assertEqual(size_steps(s, 200., c), ((3, 1, 2), None))
        c["instrument_assumption"]["min_order_qty"] = ".002"
        self.assertEqual(size_steps(s, 200., c)[1], "INVALID_PARTIAL_QUANTITY")

    def test_closing_minimum_notional_exempt_entry_notional_enforced(self):
        c = config()
        s = setup(entry_ref=2000., sl=1900., tp1=2150., tp2=2250., risk=100., cost=2.925)
        self.assertEqual(size_steps(s, 125., c), ((3, 1, 2), None))
        self.assertEqual(size_steps(s, 90., c)[1], "ENTRY_MINIMUM")

    def test_missing_funding_never_zero_or_net_valid(self):
        f = FundingEvidence()
        self.assertFalse(f.public()["zero_substitution"])
        self.assertEqual(f.public()["funding_adjusted_result"], "NOT_EVALUABLE")
        with self.assertRaises(FundingMissingError):
            f.require_net_research()

    def test_network_offline_and_future_windows_denied(self):
        with offline_only(), self.assertRaises(AccessDenied):
            socket.create_connection(("example.invalid", 443))
        for year in (2025, 2026):
            with self.assertRaises(AccessDenied):
                Window.annual(year, "15")
        w, bars, hourly = self.fixture(300)
        bars[250] = replace(bars[250], open_time=Window.annual(2024, "15").end)
        with self.assertRaises(AccessDenied):
            build_features(bars, hourly, w, config())

    def test_frozen_config_tamper_rejected_before_price_processing(self):
        import research.stage0b.guard as guard
        original = guard._same_frozen_file
        def reject_config(name):
            if name == "configs/research_v0.2.2.json":
                raise AccessDenied("FROZEN_FILE_CHANGED")
            original(name)
        with patch.object(guard, "_same_frozen_file", side_effect=reject_config), patch.object(guard, "read_dataset") as reader:
            with self.assertRaises(AccessDenied):
                preflight()
            reader.assert_not_called()

    def test_all_data_hashes_checked_before_any_price_parsing(self):
        import research.stage0b.guard as guard
        original = guard.sha256
        # A manifest mismatch is also rejected before the parser; force every late CSV digest invalid.
        with patch.object(guard, "sha256", side_effect=lambda value: "0"*64 if len(value) > 100000 else original(value)), patch.object(guard, "read_dataset") as reader:
            with self.assertRaises(AccessDenied):
                preflight()
            reader.assert_not_called()

    def test_public_financial_field_and_future_export_rejected_before_write(self):
        for field in ("net_pnl", "returns", "win_rate", "profit_factor", "drawdown", "cash", "settled_balance"):
            with self.subTest(field=field), self.assertRaises(AccessDenied):
                no_financial_outputs({"nested": {field: 1}})
        with tempfile.TemporaryDirectory() as name:
            with self.assertRaises(AccessDenied):
                write_public_summary(Path(name), {"year": 2025, "candidate": "C01"})
            self.assertEqual(list(Path(name).iterdir()), [])

    def test_private_storage_permissions_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as name:
            directory = Path(name)/"restricted"
            restricted_directory(directory)
            target = directory/"fixture.json"
            write_private(target, b"{}")
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                write_private(target, b"{}")

    def test_frequency_diagnostic_strict_below_150_and_no_elimination(self):
        paths = [{"candidate": "C01", "year": y, "N_completed": 150} for y in (2023, 2024)]
        self.assertEqual(frequency_diagnostic(paths)["status"], "NO_LOW_SIGNAL_FREQUENCY_FLAG")
        paths[0]["N_completed"] = 149
        d = frequency_diagnostic(paths)
        self.assertEqual(d["status"], "LOW_SIGNAL_FREQUENCY")
        self.assertFalse(d["candidate_elimination"])


class IndependentPathTests(unittest.TestCase):
    def test_optional_rejection_frees_later_entry_independent_of_c01(self):
        w = Window.annual(2023, "15")
        candles = tuple(bar(t, h=100.4, l=99.6) for t in range(w.anchor, w.end, w.step))
        candles = list(candles)
        candles[250] = bar(candles[250].open_time, h=101.5, l=99.6)
        setups = [None]*len(candles)
        setups[239] = setup(R=False)
        setups[243] = setup(index=243, pullback=240, sl=99.5, tp1=100.75, tp2=101.25, risk=.5)
        f = Features(w, tuple(candles), tuple(setups))
        c = config()
        first = Engine("C01", w, c, "independent")
        a = first.run(f)
        second = Engine("C02", w, c, "independent")
        b = second.run(f)
        replay = Engine("C02", w, c, "independent")
        self.assertEqual(replay.run(f), b)
        self.assertEqual(sha256(canonical(second.private_payload())), sha256(canonical(replay.private_payload())))
        self.assertEqual((a["N_completed"], a["N_censored"]), (0, 1))
        self.assertEqual((b["N_completed"], b["N_censored"]), (1, 0))
        self.assertEqual(a["rejection_reasons"]["G:POSITION_BUSY"], 1)
        self.assertEqual(b["rejection_reasons"]["F:FILTER_R"], 1)
        validate_path_summary(a)
        validate_path_summary(b)
        check_summary(a)
        check_summary(b)
        corrupted = dict(b, N_completed=b["N_completed"]+1)
        with self.assertRaises(IntegrityError):
            check_summary(corrupted)
        self.assertEqual(second._settled, second._cash)
        self.assertEqual(len(first.consumed), 1)

    def test_final_bar_exit_completes_before_boundary_and_no_end_signal(self):
        w = Window.annual(2023, "15")
        candles = [bar(t, h=100.4, l=99.6) for t in range(w.anchor, w.end, w.step)]
        setups = [None]*len(candles)
        i = len(candles)-2
        setups[i] = setup(index=i, pullback=i-4)
        setups[-1] = setup(index=i+1, pullback=i-3)
        candles[-1] = bar(candles[-1].open_time, h=106., l=99.)
        e = Engine("C01", w, config(), "boundary")
        summary = e.run(Features(w, tuple(candles), tuple(setups)))
        self.assertEqual((summary["N_signals"], summary["N_completed"], summary["N_censored"]), (1, 1, 0))
        self.assertIsNone(e.pending)
        self.assertEqual(e._ledger[-1]["phase"], "PRIOR_BAR")
        with self.assertRaises(IntegrityError):
            Engine("C01", w, config(), "bad").run(Features(w, tuple(candles[:-1]), tuple(setups[:-1])))


if __name__ == "__main__":
    unittest.main()
