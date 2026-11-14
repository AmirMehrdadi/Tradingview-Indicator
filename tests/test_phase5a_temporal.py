"""Independent synthetic temporal fixtures; no Pine compilation/runtime claim."""
import json
import re
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from research.indicators import ema, rma
from tests.phase5a_reference import ANCHOR, START, END, STEP, HOUR, Reference, consumed_hour, eligible


class ForbiddenValues:
    def __len__(self):
        raise AssertionError('Unauthorized numerical input touched')


class TemporalTests(unittest.TestCase):
    def data(self, count=288, step=STEP):
        r = Reference(step)
        states = []
        for i in range(count):
            states.append(r.feed(ANCHOR+i*step, (100+i, 102+i, 99+i, 101+i)))
        return r, states

    def hours(self):
        return {ANCHOR+i*HOUR: (float(i), float(i+100), i) for i in range(1, 100)}

    def test_A_initial_15m_anchor_and_first_tr(self):
        r, s = self.data(1)
        self.assertEqual(s[0], (101, 101, None, 3, 1))

    def test_B_initial_hour_anchor(self):
        r, s = self.data(1, HOUR)
        self.assertEqual(r.last, ANCHOR+HOUR)
        self.assertEqual(s[0][0], 101)

    def test_C_ema_and_wilder_seeds_match_frozen_independent_functions(self):
        r, s = self.data(30)
        self.assertEqual([v[0] for v in s], ema(list(range(101, 131)), 20))
        self.assertEqual([v[1] for v in s], ema(list(range(101, 131)), 50))
        self.assertEqual([v[2] for v in s], rma([3.0]*30, 14))
        self.assertEqual(s[13][2], 3)
        self.assertEqual(s[1][0], (2/21)*102+(1-2/21)*101)

    def test_tr_uses_only_previous_authorized_close_after_anchor(self):
        r = Reference()
        r.feed(ANCHOR, (100, 102, 99, 101))
        self.assertEqual(r.feed(ANCHOR+STEP, (110, 113, 109, 112))[3], 12)

    def test_invalid_ohlc_and_nonfinite_input_permanently_quarantine(self):
        for values in ((100, 98, 99, 101), (100, 102, 0, 101), (100, float('nan'), 99, 101)):
            r = Reference()
            self.assertIsNone(r.feed(ANCHOR, values))
            self.assertIsNone(r.feed(ANCHOR+STEP, (100, 102, 99, 101)))

    def test_hourly_ema50_has_independent_first_close_seed(self):
        r, s = self.data(75, HOUR)
        self.assertEqual([v[1] for v in s], ema(list(range(101, 176)), 50))

    def test_nonconstant_wilder_seed_and_recurrence(self):
        r = Reference()
        actual = [r.feed(ANCHOR+i*STEP, (100, 101+i, 100, 100))[2] for i in range(16)]
        self.assertEqual(actual, rma(list(range(1, 17)), 14))
        self.assertEqual(actual[13], 7.5)
        self.assertEqual(actual[14], (1/14)*15+(1-1/14)*7.5)

    def test_D_na_until_fourteen_valid_observations(self):
        r, s = self.data(14)
        self.assertEqual([v[2] for v in s[:13]], [None]*13)
        self.assertIsNotNone(s[13][2])

    def test_E_first_tr_cannot_consume_pre_anchor_close(self):
        r = Reference()
        self.assertIsNone(r.feed(ANCHOR-STEP, ForbiddenValues()))
        self.assertEqual(r.feed(ANCHOR, (100, 110, 95, 104))[3], 15)

    def test_F_hour_ending_11_only_consumed_by_1100_execution_interval(self):
        h = self.hours()
        t = START+11*HOUR
        before = consumed_hour(t-STEP, h)
        after = consumed_hour(t, h)
        self.assertEqual(before[3], t-HOUR)
        self.assertEqual(after[3], t)
        self.assertEqual(after[1], h[t-3*HOUR][0])
        self.assertEqual(t+STEP, START+11*HOUR+15*60000)

    def test_G_warmup_has_no_diagnostic_eligibility(self):
        r = Reference()
        for t in range(ANCHOR, START-STEP, STEP):
            s = r.feed(t, (100, 102, 99, 101))
            self.assertFalse(eligible(t, s, consumed_hour(t, self.hours())))

    def test_H_first_permitted_signal_close_boundary(self):
        r, s = self.data(288)
        self.assertTrue(eligible(START-STEP, s[-1], consumed_hour(START-STEP, self.hours())))
        self.assertFalse(eligible(START-2*STEP, s[-2], consumed_hour(START-2*STEP, self.hours())))

    def test_I_trade_start_does_not_reset_state(self):
        r, s = self.data(289)
        self.assertEqual(s[287][4], 288)
        self.assertEqual(s[288][4], 289)
        self.assertNotEqual(s[288][0], 389)

    def test_J_end_excludes_new_eligibility_and_input(self):
        s = (1, 1, 1, 1, 999)
        self.assertFalse(eligible(END-STEP, s, (1,)))
        self.assertFalse(eligible(END, s, (1,)))
        self.assertTrue(eligible(END-2*STEP, s, (1,)))
        self.assertIsNone(Reference().feed(END, ForbiddenValues()))

    def test_K_pre_anchor_values_cannot_change_numerical_state(self):
        a, b = Reference(), Reference()
        for t in range(ANCHOR-10*STEP, ANCHOR, STEP):
            a.feed(t, ForbiddenValues())
        for t in range(ANCHOR, ANCHOR+30*STEP, STEP):
            self.assertEqual(a.feed(t, (100, 104, 99, 102)), b.feed(t, (100, 104, 99, 102)))

    def test_L_source_review_has_no_implicit_indicator_fallback(self):
        # Source inspection is deliberately not named a compiler test.
        s = (Path(__file__).resolve().parents[1]/'pine/Phase5A_Temporal_Probe_UNVALIDATED.pine').read_text()
        for token in ('ta.', 'nz(', 'varip ', 'strategy(', 'strategy.', 'alert(', 'alertcondition('):
            self.assertIsNone(re.search(r'(?<![A-Za-z0-9_])'+re.escape(token), s))
        self.assertIn('output[1], output[4]', s)
        self.assertIn('lookahead = barmerge.lookahead_on', s)
        self.assertIn('barstate.isconfirmed and window', s)

    def test_M_missing_values_quarantine_instead_of_zero_or_skipping(self):
        r = Reference()
        self.assertIsNone(r.feed(ANCHOR, (100, None, 99, 101)))
        self.assertIsNone(r.feed(ANCHOR+STEP, (100, 102, 99, 101)))
        self.assertEqual(r.n, 0)

    def test_N_deterministic_replay(self):
        self.assertEqual(json.dumps(self.data(300)[1]), json.dumps(self.data(300)[1]))

    def test_O_no_io_and_unauthorized_values_denied_before_access(self):
        with patch('builtins.open', side_effect=AssertionError('No files')), patch.object(socket, 'create_connection', side_effect=AssertionError('No network')):
            r = Reference()
            self.assertIsNone(r.feed(ANCHOR-STEP, ForbiddenValues()))
            self.assertIsNotNone(r.feed(ANCHOR, (100, 102, 99, 101)))

    def test_missing_anchor_or_gap_poison_both_timeframes(self):
        for step in (STEP, HOUR):
            r = Reference(step)
            self.assertIsNone(r.feed(ANCHOR+step, (100, 102, 99, 101)))
            r = Reference(step)
            r.feed(ANCHOR, (100, 102, 99, 101))
            self.assertIsNone(r.feed(ANCHOR+2*step, (100, 102, 99, 101)))
            self.assertIsNone(r.feed(ANCHOR+3*step, (100, 102, 99, 101)))

    def test_unconfirmed_execution_never_changes_chart_state(self):
        r = Reference()
        self.assertIsNone(r.feed(ANCHOR, ForbiddenValues(), False))
        self.assertEqual(r.n, 0)
        self.assertFalse(eligible(START, (1,1,1,1,300), (1,), False))

    def test_missing_hour_not_forward_filled_and_60_observation_minimum(self):
        h = self.hours()
        self.assertIsNone(consumed_hour(ANCHOR+59*HOUR, h))
        self.assertIsNotNone(consumed_hour(ANCHOR+60*HOUR, h))
        del h[START]
        self.assertIsNone(consumed_hour(START+STEP, h))

    def test_future_hour_changes_cannot_change_prior_observation(self):
        h = self.hours()
        before = consumed_hour(START, h)
        h[START+HOUR] = (1e99, 1e99, 999)
        self.assertEqual(consumed_hour(START, h), before)
