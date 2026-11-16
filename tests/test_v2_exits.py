"""Literal synthetic exit and state tests; no historical execution."""
from dataclasses import replace
from decimal import Decimal
import unittest

from research.access import Window
from research.stage0b.engine import Engine
from research.stage0b.model import Plan, IntegrityError, size_steps
from research.v2_exits.engine import ExitExperiment, A, B
from research.v2_exits.metrics import metrics
from research.funding_attribution.accounting import prepare_path, observations, attribute
from research.funding_lifecycle.accounting import Scenario
from tests.test_stage0b import config, setup, bar
from tests.test_funding_attribution import data


class ExitTests(unittest.TestCase):
    def engine(self, arm=A):
        w=Window.annual(2023,'15');e=ExitExperiment('C01',w,config(),'fixture',arm=arm);e.reset_day(w.start);return e

    def queued(self, arm=A, direction='Long', steps=1000):
        e=self.engine(arm);sign=1 if direction=='Long' else -1;t=e.window.start
        p=Plan(f'fixture:Research:C01:2023:{t-e.window.step}:{direction}',direction,t,t-e.window.step,
               235,230,100.,100-sign*2,100+sign*3,100+sign*5,steps,steps//2,steps-steps//2,10000.,25.,2.)
        e.queue(p);e._gate('G',direction);e.process_open(bar(t));return e

    def exits(self,e):return [x for x in e._ledger if x['event']=='EXIT_LEG']

    def test_only_registered_exit_arms(self):
        with self.assertRaises(IntegrityError):self.engine('OTHER')

    def test_initial_stop_unchanged_before_tp1(self):
        e=self.queued();e.process_intrabar(bar(e.window.start,h=102,l=99,c=101))
        self.assertEqual(e.current_stop(),98);self.assertEqual(e.be_stops,{})
        e.process_open(bar(e.window.start+900000,o=97,h=99,l=96,c=98))
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[97,97])

    def test_conservative_long_and_short_rounding_after_actual_tp1(self):
        for direction,opening in [('Long',104),('Short',96)]:
            e=self.queued(direction=direction);e.process_open(bar(e.window.start+900000,o=opening,h=opening+1,l=opening-1,c=opening))
            self.assertEqual(e.current_stop(),100);self.assertEqual(len(e.activations),1)
            self.assertEqual(e.position.remaining,[0,500]);self.assertEqual(e.position.plan.sl,98 if direction=='Long' else 102)

    def test_initial_sl_and_tp1_same_bar_never_activates_be(self):
        e=self.queued();e.process_intrabar(bar(e.window.start,h=106,l=97,c=100))
        self.assertEqual([x['kind'] for x in self.exits(e)],['STOP','STOP'])
        self.assertEqual(e.activations,[]);self.assertEqual(e.quality['UNCERTAIN_INTRABAR_ORDER'],1)

    def test_tp1_new_be_and_tp2_same_bar_conservative_ambiguity(self):
        e=self.queued();e.process_intrabar(bar(e.window.start,h=106,l=99,c=104))
        self.assertEqual([(x['kind'],x['raw_market_price']) for x in self.exits(e)],[('TP',103),('STOP',100)])
        self.assertEqual(e.quality['BE_ACTIVATION_INTRABAR_AMBIGUOUS'],1)
        self.assertIsNone(e.position)

    def test_tp1_without_new_stop_touch_allows_tp2(self):
        e=self.queued();t=e.window.start+900000;b=bar(t,o=101,h=106,l=100.5,c=105)
        e.process_open(b);e.process_intrabar(b)
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[103,105])

    def test_known_open_tp1_new_stop_active_for_remaining_bar(self):
        e=self.queued();t=e.window.start+900000;e.process_open(bar(t,o=104,h=106,l=99,c=105));e.process_intrabar(bar(t,o=104,h=106,l=99,c=105))
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[103,100])
        self.assertEqual(e.quality['BE_ACTIVATION_INTRABAR_AMBIGUOUS'],0)

    def test_be_gap_uses_actual_open_and_adverse_friction(self):
        e=self.queued();t=e.window.start+900000;e.process_open(bar(t,o=104,h=104.5,l=103.5,c=104))
        e.process_open(bar(t+900000,o=99,h=100,l=98,c=99))
        last=self.exits(e)[-1];self.assertEqual(last['raw_market_price'],99)
        self.assertAlmostEqual(last['fill'],99*(1-.0002));self.assertNotEqual(last['fill'],100.02)
        self.assertEqual(last['phase'],'OPEN');self.assertGreater(last['exit_fee'],0)

    def test_short_be_gap_uses_actual_open(self):
        e=self.queued(direction='Short');t=e.window.start+900000;e.process_open(bar(t,o=96,h=97,l=95,c=96))
        e.process_open(bar(t+900000,o=101,h=102,l=100,c=101))
        self.assertEqual(self.exits(e)[-1]['raw_market_price'],101)
        self.assertAlmostEqual(self.exits(e)[-1]['fill'],101*1.0002)

    def test_new_be_beyond_tp1_touch_uses_known_market_not_unvisited_stop(self):
        e=self.engine();t=e.window.start
        p=Plan(f'fixture:Research:C01:2023:{t-900000}:Long','Long',t,t-900000,
               235,230,10000.,9800.,10300.,10500.,1000,500,500,10000.,25.,200.)
        e.queue(p);e._gate('G','Long')
        b=bar(t,o=10299.99,h=10300.5,l=10299.,c=10300.)
        e.process_open(b);e.process_intrabar(b)
        self.assertGreater(e.be_stops[p.entry_id],10300.5)
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[10300.,10300.])
        self.assertEqual(e.quality['BE_IMMEDIATE_INTRABAR_EXIT'],1)

    def test_odd_quantity_conserved_after_be(self):
        e=self.queued(steps=3);e.process_intrabar(bar(e.window.start,h=104,l=99,c=103))
        self.assertEqual([x['quantity_steps'] for x in self.exits(e)],[1,2]);e.assert_integrity()

    def test_full_tp1_closes_whole_position_at_tp1(self):
        e=self.queued(B);e.process_intrabar(bar(e.window.start,h=104,l=99,c=103))
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[103,103])
        self.assertEqual(sum(x['quantity_steps'] for x in self.exits(e)),1000)
        self.assertEqual(e.completed,1);self.assertIsNone(e.position);self.assertEqual(e.activations,[])

    def test_full_tp1_gap_keeps_frozen_target_not_better_open(self):
        e=self.queued(B);e.process_open(bar(e.window.start+900000,o=110,h=111,l=109,c=110))
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[103,103])

    def test_full_tp1_stop_first_on_dual_touch(self):
        e=self.queued(B);e.process_intrabar(bar(e.window.start,h=106,l=97,c=100))
        self.assertEqual([x['kind'] for x in self.exits(e)],['STOP','STOP'])

    def test_full_tp1_short_conservation(self):
        e=self.queued(B,direction='Short',steps=3);e.process_intrabar(bar(e.window.start,h=101,l=96,c=97))
        self.assertEqual([x['raw_market_price'] for x in self.exits(e)],[97,97]);e.assert_integrity()

    def test_partial_does_not_settle_and_full_exit_does(self):
        a,b=self.queued(A),self.queued(B);t=a.window.start+900000
        a.process_open(bar(t,o=104,h=104.5,l=103.5,c=104));b.process_open(bar(t,o=104,h=104.5,l=103.5,c=104))
        self.assertEqual(a._settled,10000);self.assertNotEqual(b._settled,10000)
        self.assertIsNotNone(a.position);self.assertIsNone(b.position)
        self.assertNotEqual(size_steps(setup(),a._settled,a.config)[0],size_steps(setup(),b._settled,b.config)[0])

    def test_duration_changes_subsequent_accepted_signals(self):
        a,b=self.queued(A),self.queued(B);t=a.window.start+900000
        a.process_open(bar(t,o=104,h=104.5,l=103.5,c=104));b.process_open(bar(t,o=104,h=104.5,l=103.5,c=104))
        a.offer(setup(pullback=999),t);b.offer(setup(pullback=999),t)
        self.assertIsNone(a.pending);self.assertIsNotNone(b.pending)

    def test_daily_stop_recomputed_after_different_full_closures(self):
        a,b=self.queued(A,steps=100000),self.queued(B,steps=100000);t=a.window.start+900000
        a.process_open(bar(t,o=104,h=104.5,l=103.5,c=104));b.process_open(bar(t,o=104,h=104.5,l=103.5,c=104))
        a.process_open(bar(t+900000,o=90,h=91,l=89,c=90))
        self.assertTrue(a.daily_stop);self.assertFalse(b.daily_stop)

    def test_funding_on_remaining_old_be_position_before_open_exit(self):
        e=self.queued(A);t=e.window.start+8*3600000
        e.process_intrabar(bar(t-900000,o=101,h=104,l=100.5,c=103))
        e.process_open(bar(t,o=99,h=100,l=98,c=99));e.finish()
        p=prepare_path(e.private_payload(),'fixture');o=observations(2023,*data());r=attribute(p,o,Scenario())
        self.assertEqual(r['records'][0]['quantity_steps'],500)
        self.assertEqual(r['records'][0]['cashflow'],Decimal('-.5'));self.assertTrue(r['records'][0]['tie'])

    def test_funding_exempt_after_full_tp1_previous_bar(self):
        e=self.queued(B);t=e.window.start+8*3600000;e.process_intrabar(bar(t-900000,o=101,h=104,l=99,c=103));e.finish()
        r=attribute(prepare_path(e.private_payload(),'fixture'),observations(2023,*data()),Scenario())
        self.assertEqual(r['records'],[])

    def test_censor_no_funding_at_exclusive_annual_end(self):
        e=self.queued();e.finish();r=attribute(prepare_path(e.private_payload(),'fixture'),observations(2023,*data()),Scenario())
        self.assertEqual(r['trades'][0]['state'],'CENSORED');self.assertIsNone(r['trades'][0]['trade_R_net'])
        self.assertTrue(all(x['settlement_ms']<e.window.end for x in r['records']))

    def test_deterministic_exit_ledger(self):
        a,b=self.queued(),self.queued()
        for e in (a,b):e.process_intrabar(bar(e.window.start,h=106,l=99,c=104));e.finish()
        self.assertEqual(a.private_payload(),b.private_payload())

    def test_reference_engine_not_modified(self):
        e=self.queued();v=Engine('C01',e.window,e.config,'fixture');v.reset_day(e.window.start)
        p=next(x['plan'] for x in e._ledger if x['event']=='SIGNAL_AND_BRACKETS_QUEUED');v.queue(Plan(**p));v._gate('G','Long');v.process_open(bar(v.window.start));v.process_intrabar(bar(v.window.start,h=104,l=99,c=103))
        self.assertIsNotNone(v.position);self.assertEqual(v.position.remaining,[0,500]);self.assertEqual(v.position.plan.sl,98)

    def test_metrics_use_closure_order_not_dictionary_order(self):
        payload={'ledger':[{'event':'POSITION_CLOSED','entry_id':k} for k in ['b','a','c']]}
        rows=[dict(entry_id=k,state='COMPLETED',net_after_funding=Decimal(n),trade_R_net=Decimal(r),attributed_funding=Decimal('0'))
              for k,n,r in [('a','-10','-1'),('b','20','2'),('c','-30','-3')]]
        result=metrics(payload,{'trades':rows})
        self.assertEqual(result['net_usdt'],Decimal('-20'))
        self.assertEqual(result['profit_factor'],Decimal('.5'))
        self.assertEqual(result['max_realized_drawdown_R'],Decimal('4'))

    def test_metrics_exclude_censored_financial_rows(self):
        rows=[dict(entry_id='censored',state='CENSORED',trade_R_net=None,attributed_funding=Decimal('5'))]
        result=metrics({'ledger':[]},{'trades':rows})
        self.assertEqual(result['completed'],0);self.assertEqual(result['censored'],1)
        self.assertIsNone(result['win_rate']);self.assertIsNone(result['mean_R'])
        self.assertEqual(result['funding_censored'],Decimal('5'));self.assertEqual(result['net_usdt'],0)
