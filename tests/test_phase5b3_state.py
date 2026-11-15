"""Stage A: independent synthetic Research lifecycle assertions; no real ledgers."""
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from research.fixture_state_v1.state import (Lifecycle,Decision,Candle,FixtureError,ANCHOR,START,END,STEP,DAY)


def bar(t=START,o=100,h=101,l=99,c=100):return Candle(t,o,h,l,c)


def decision(t=START,side=1,steps=1001,candidate='C01'):
    return Decision(candidate,t,t-3*STEP,side,100.,980 if side==1 else 1020,1030 if side==1 else 970,1050 if side==1 else 950,steps)


def ready(t=START,candidate='C01'):
    e=Lifecycle(candidate);e.process(bar(t-STEP));return e


class StateTests(unittest.TestCase):
    def exits(self,e):return [v for v in e.events if v['name']=='EXIT']

    def test_flat_pending_open_next_open(self):
        e=ready();self.assertEqual(e.state,'FLAT');self.assertTrue(e.queue(decision()));self.assertEqual(e.state,'PENDING_ENTRY')
        self.assertFalse(any(v['name']=='ENTRY' for v in e.events))
        e.process(bar());self.assertEqual(e.state,'OPEN');self.assertEqual(e.events[-1]['name'],'ENTRY')
        p=e.position;self.assertEqual(p.remaining,[500,501]);self.assertEqual(p.fill,100*1.0002)

    def test_long_and_short_tp1_then_tp2(self):
        for side in (1,-1):
            e=ready();e.queue(decision(side=side));e.process(bar())
            e.process(bar(START+STEP,h=104,l=99) if side==1 else bar(START+STEP,h=101,l=96))
            self.assertEqual(e.position.remaining,[0,501]);self.assertEqual(e.settled,10000.)
            e.process(bar(START+2*STEP,h=106,l=99) if side==1 else bar(START+2*STEP,h=101,l=94))
            self.assertEqual(e.state,'FLAT');self.assertEqual([v['kind'] for v in self.exits(e)],['TP','TP'])
            self.assertEqual(sum(v['steps'] for v in self.exits(e)),1001)
            self.assertEqual(e.settled,e.cash)

    def test_tp1_then_remaining_stop_no_premature_settlement(self):
        e=ready();e.queue(decision());e.process(bar(h=104,l=99));self.assertEqual(e.settled,10000.)
        e.process(bar(START+STEP,h=101,l=97));self.assertEqual([(v['kind'],v['steps']) for v in self.exits(e)],[('TP',500),('STOP',501)])
        self.assertEqual(e.settled,e.cash)

    def test_stop_before_tp1_both_legs(self):
        e=ready();e.queue(decision());e.process(bar(h=101,l=97))
        self.assertEqual([(v['kind'],v['steps']) for v in self.exits(e)],[('STOP',500),('STOP',501)])
        self.assertEqual(e.state,'FLAT')

    def test_stop_first_ambiguity_both_sides(self):
        for side in (1,-1):
            e=ready();e.queue(decision(side=side));e.process(bar(h=110,l=90))
            self.assertEqual([x['kind'] for x in self.exits(e)],['STOP','STOP'])
            self.assertIn('UNCERTAIN_INTRABAR_ORDER',e.quality)

    def test_known_open_targets_not_cancelled_by_later_extreme(self):
        e=ready();e.queue(decision());e.process(bar(o=110,h=120,l=1,c=100))
        self.assertEqual([x['raw'] for x in self.exits(e)],[103.,105.])
        self.assertNotIn('MARGIN_MODEL_EVENT',e.quality)

    def test_gap_through_stop_uses_raw_open(self):
        e=ready();e.queue(decision());e.process(bar());e.process(bar(START+STEP,o=95,h=96,l=94,c=95))
        self.assertEqual([x['fill'] for x in self.exits(e)],[95*.9998]*2)

    def test_entry_at_or_beyond_stop_is_retained_then_closed(self):
        e=ready();e.queue(decision());e.process(bar(o=97,h=99,l=96,c=97))
        self.assertEqual(sum(v['name']=='ENTRY' for v in e.events),1)
        self.assertEqual(len(e.completed),1);self.assertIn('ENTRY_AT_OR_BEYOND_SL',e.quality)

    def test_adverse_gap_records_quality_without_resizing(self):
        e=ready();e.queue(decision());e.process(bar(o=101,h=102,l=100,c=101))
        self.assertIn('ENTRY_DEVIATION',e.quality);self.assertEqual(e.position.remaining,[500,501])

    def test_rejected_margin_no_fees_retains_consumed_identity(self):
        e=ready();d=decision();e.queue(d);e.process(bar(o=30000,h=30001,l=29999,c=30000))
        self.assertEqual(e.state,'FLAT');self.assertEqual(e.cash,10000.)
        self.assertIn(('C01',1,d.pullback_id),e.consumed)
        self.assertTrue(any(v['name']=='ENTRY_REJECTED_MARGIN' for v in e.events))
        self.assertFalse(any(v['name']=='ENTRY' for v in e.events))

    def test_even_and_odd_reservation_and_conservation(self):
        for steps in (1000,1001,3):
            e=ready();e.queue(decision(steps=steps if steps>=50 else 50))
            # Entry minimum notional correctly disallows a 3-step BTC order at 100.
            reservations=e.events[-1]['reservations'];self.assertEqual(sum(reservations),max(steps,50))
            e.process(bar(h=106,l=99));e.invariants()
            self.assertEqual(e.completed[-1].exited,max(steps,50))

    def test_odd_three_steps_with_sufficient_entry_notional(self):
        e=Lifecycle();e.process(bar(START-STEP,o=2000,h=2001,l=1999,c=2000));d=Decision('C01',START,START-3*STEP,1,2000.,19000,21500,22500,3)
        self.assertTrue(e.queue(d));e.process(bar(o=2000,h=2200,l=1950,c=2100))
        self.assertEqual(e.position.remaining,[0,2]);self.assertEqual(e.position.exited,1)

    def test_duplicate_or_over_or_under_fill_cannot_mutate_quantity(self):
        e=ready();e.queue(decision());e.process(bar(h=104,l=99));before=e.serialized()
        with self.assertRaises(FixtureError):e.exit_leg(0,103,START+STEP,'PRIOR_BAR','TP')
        with self.assertRaises(FixtureError):e.exit_leg(1,105,START+STEP,'PRIOR_BAR','TP',steps=502)
        with self.assertRaises(FixtureError):e.exit_leg(1,105,START+STEP,'PRIOR_BAR','TP',steps=500)
        self.assertEqual(e.serialized(),before)

    def test_busy_pending_open_and_consumed_rejection(self):
        e=ready();d=decision();self.assertTrue(e.queue(d));self.assertFalse(e.queue(d))
        e.process(bar());self.assertFalse(e.queue(replace(d,signal_close=START+STEP)))
        e.process(bar(START+STEP,h=106,l=99));self.assertFalse(e.queue(replace(d,signal_close=START+2*STEP)))

    def test_risk_budget_notional_and_minimum_order_checks(self):
        e=ready()
        for d in [decision(steps=1),decision(steps=150001),decision(steps=20000),decision(steps=True),replace(decision(),sl_ticks=1000)]:
            with self.assertRaises(FixtureError):e.queue(d)
        self.assertEqual(e.consumed,set());self.assertEqual(e.state,'FLAT')

    def test_nonintegral_prices_quantities_and_foreign_candidates_denied(self):
        e=ready()
        for d in [replace(decision(),sl_ticks=980.),replace(decision(),candidate='C02'),replace(decision(),provenance='HISTORICAL')]:
            with self.assertRaises(FixtureError):e.queue(d)

    def test_next_open_missing_or_duplicate_bar_quarantine(self):
        e=ready();e.queue(decision());before=e.cash
        with self.assertRaises(FixtureError):e.process(bar(START+STEP))
        self.assertTrue(e.quarantined);self.assertEqual(e.cash,before);self.assertEqual(e.state,'PENDING_ENTRY')

    def test_utc_midnight_prior_full_close_then_reset(self):
        t=START+DAY
        e=ready(t-STEP);e.queue(decision(t-STEP,steps=10000));e.process(bar(t-STEP,h=101,l=97))
        self.assertEqual(e.day_start,e.settled);self.assertFalse(e.daily_stop)
        names=[x['name'] for x in e.events if x['time']==t]
        self.assertLess(names.index('FULL_FLAT_SETTLEMENT'),names.index('UTC_DAY_RESET'))

    def test_daily_stop_activation_and_next_day_reset(self):
        e=ready();e.queue(decision(steps=10000));e.process(bar())
        e.process(bar(START+STEP,o=80,h=81,l=79,c=80))
        self.assertTrue(e.daily_stop)
        # A fresh valid decision remains blocked; no inferred position reopening.
        self.assertFalse(e.queue(replace(decision(START+2*STEP),entry_ref=80.,sl_ticks=780,tp1_ticks=830,tp2_ticks=850,steps=1000)))
        e.reset_day(START+DAY);self.assertFalse(e.daily_stop);self.assertEqual(e.day_start,e.settled)

    def test_partial_midnight_retains_last_full_settled_snapshot(self):
        t=START+DAY;e=ready(t-STEP);e.queue(decision(t-STEP));e.process(bar(t-STEP,h=104,l=99))
        self.assertEqual(e.position.remaining,[0,501]);self.assertEqual((e.settled,e.day_start),(10000.,10000.))

    def test_end_censors_after_last_bar_without_forced_exit(self):
        e=ready(END-STEP);e.queue(decision(END-STEP));e.process(bar(END-STEP))
        self.assertTrue(e.ended);self.assertEqual(len(e.completed),0);self.assertEqual(len(e.censored),1)
        self.assertEqual(e.censored[0].remaining,[500,501]);self.assertEqual(e.censored[0].state,'CENSORED')
        with self.assertRaises(FixtureError):e.process(bar(END))

    def test_final_prior_bar_exit_is_complete_not_censored(self):
        e=ready(END-STEP);e.queue(decision(END-STEP));e.process(bar(END-STEP,h=106,l=99))
        self.assertEqual(len(e.completed),1);self.assertEqual(e.censored,[])
        with self.assertRaises(FixtureError):e.queue(decision(END))

    def test_invalid_missing_future_and_provenance_data_fail_before_effects(self):
        for b in [bar(h=None),bar(l=0),bar(h=float('nan')),bar(END),replace(bar(),provenance='HISTORICAL')]:
            e=ready();e.queue(decision())
            with self.assertRaises(FixtureError):e.process(b)
            self.assertEqual(e.cash,10000.);self.assertEqual(e.fill_ids,set());self.assertTrue(e.quarantined)

    def test_friction_fee_accounting_independent_synthetic_expectation(self):
        e=ready();e.queue(decision(steps=1000));e.process(bar(h=106,l=99))
        cash=10000.-(100*1.0002)*.00055
        for raw in (103,105):
            fill=raw*.9998;cash+=.5*(fill-100*1.0002)-.5*fill*.00055
        self.assertEqual(e.cash,cash);self.assertEqual(e.settled,cash)

    def test_margin_never_uses_later_extremum_after_full_close(self):
        e=ready();e.queue(decision());e.process(bar(o=110,h=111,l=.1,c=110))
        self.assertNotIn('MARGIN_MODEL_EVENT',e.quality)

    def test_signal_reference_must_equal_observed_close(self):
        e=ready()
        with self.assertRaisesRegex(FixtureError,'ENTRY_REF_NOT_SIGNAL_CLOSE'):e.queue(replace(decision(),entry_ref=101.))
        self.assertEqual(e.consumed,set())

    def test_invalid_fill_values_fail_before_cash_or_quantity_changes(self):
        e=ready();e.queue(decision());e.process(bar());before=e.serialized()
        with self.assertRaises(FixtureError):e.exit_leg(0,float('nan'),START+STEP,'PRIOR_BAR','TP')
        with self.assertRaises(FixtureError):e.exit_leg(True,103,START+STEP,'PRIOR_BAR','TP')
        self.assertEqual(e.serialized(),before)

    def test_adverse_fill_risk_overrun_is_recorded_without_resizing(self):
        e=ready();e.queue(decision(steps=10000));e.process(bar(o=100.4,h=101,l=100,c=100.4))
        self.assertIn('RISK_OVERRUN',e.quality)
        self.assertEqual(e.position.remaining,[5000,5000])

    def test_independent_lifecycle_matches_preserved_engine_on_synthetic_legs(self):
        from research.stage0b.engine import Engine
        from research.stage0b.model import Plan
        from research.access import Window
        from research.loader import Candle as ResearchCandle
        root=Path(__file__).resolve().parents[1]
        config=json.loads((root/'configs/research_v0.2.2.json').read_text())
        for side in (1,-1):
            window=Window.annual(2023,'15')
            old=Engine('C01',window,config,'fixture:comparison');old.reset_day(window.start)
            old.queue(Plan('fixture:entry','Long' if side==1 else 'Short',window.start,window.start-STEP,1,0,
                           100.,98. if side==1 else 102.,103. if side==1 else 97.,105. if side==1 else 95.,
                           1001,500,501,10000.,25.,2.))
            new=ready();new.queue(decision(side=side))
            vectors=[(100,104,99,100),(100,101,97,100)] if side==1 else [(100,101,96,100),(100,103,99,100)]
            for i,(o,h,l,c) in enumerate(vectors):
                oldbar=ResearchCandle(window.start+i*STEP,o,h,l,c,1.,1.)
                old.process_open(oldbar);old.process_intrabar(oldbar)
                new.process(bar(START+i*STEP,o,h,l,c))
            self.assertEqual(new.cash,old._cash)
            self.assertEqual(new.settled,old._settled)
            oldlegs=[(e['kind'],e['quantity_steps'],e['fill']) for e in old._ledger if e['event']=='EXIT_LEG']
            newlegs=[(e['kind'],e['steps'],e['fill']) for e in self.exits(new)]
            self.assertEqual(newlegs,oldlegs)

    def test_conservation_failure_is_detected(self):
        e=ready();e.queue(decision());e.process(bar());e.position.remaining[0]+=1
        with self.assertRaisesRegex(FixtureError,'CONSERVATION'):e.invariants()

    def test_deterministic_fixture_replay_and_no_io(self):
        hashes=[]
        with patch('builtins.open',side_effect=AssertionError('NO_IO')):
            for _ in range(2):
                e=ready();e.queue(decision());e.process(bar(h=104,l=99));e.process(bar(START+STEP,h=101,l=97))
                hashes.append(hashlib.sha256(e.serialized()).hexdigest())
        self.assertEqual(hashes[0],hashes[1])
