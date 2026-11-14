"""Independent synthetic C01 decisions; not Pine compilation or market replay."""
from dataclasses import replace
from types import SimpleNamespace
from pathlib import Path
import json
import math
import unittest
from unittest.mock import patch
from research.indicators import confirmed_pivot as old_pivot, round_stop, ema, atr14
from research.stage0a import baseline as old_baseline
from research.stage0b.model import size_steps
from tests.phase5b1_reference import *


class Untouchable:
    def __len__(self):
        raise AssertionError('Unauthorized values accessed')


class C01Tests(unittest.TestCase):
    def fixture(self):
        bars = [Bar(ANCHOR+k*STEP, 104., 106., 104., 105.) for k in range(288)]
        fast, slow, atr = [103.]*288, [100.]*288, [2.5]*288
        bars[-11] = replace(bars[-11], low=103.)
        bars[-3] = replace(bars[-3], low=102.5)
        bars[-1] = replace(bars[-1], open=107., high=109., low=107., close=108.)
        fast[-1] = 106.
        return bars, fast, slow, atr

    def plan(self, context=None):
        return decide(*self.fixture(), context or Context())

    def test_positive_complete_fixture_has_literal_levels_and_ids(self):
        p,e = self.plan()
        self.assertIsNone(e)
        self.assertEqual((p['sl_ticks'],p['tp1_ticks'],p['tp2_ticks']),(1026,1161,1215))
        self.assertEqual((p['pullback_id'],p['pivot_id'],p['signal_close']),(START-3*STEP,START-11*STEP,START))
        self.assertEqual(p['steps'][1]+p['steps'][2],p['steps'][0])

    def test_strict_direction_and_equalities(self):
        for args,wanted in [((108,106,100),1),((92,94,100),-1),((108,100,100),0),((100,106,100),0),((100,94,100),0)]:
            self.assertEqual(direction(*args),wanted)

    def test_pullback_touch_equality(self):
        b,f,s,a = self.fixture();b[-3]=replace(b[-3],low=f[-3])
        self.assertEqual(pullback(b,f,s,a,287),(285,1,None))

    def test_pullback_age_two_and_five_inclusive(self):
        for age in (2,5):
            b,f,s,a=self.fixture();b[-3]=replace(b[-3],low=104.)
            j=287-age;b[j]=replace(b[j],low=102.5)
            self.assertEqual(pullback(b,f,s,a,287)[0],j)

    def test_pullback_age_one_six_excluded(self):
        for age in (1,6):
            b,f,s,a=self.fixture();b[-3]=replace(b[-3],low=104.)
            b[287-age]=replace(b[287-age],low=102.5)
            self.assertEqual(pullback(b,f,s,a,287)[2],'PULLBACK')

    def test_latest_touch_chosen_without_older_fallback_after_sequence_failure(self):
        b,f,s,a=self.fixture();b[-6]=replace(b[-6],low=102.5)
        s[-2]=105.
        self.assertEqual(pullback(b,f,s,a,287),(285,1,'SEQUENCE'))

    def test_trigger_all_strict_boundaries(self):
        for changes in ({'open':108.},{'close':106.}):
            b,f,s,a=self.fixture();b[-1]=replace(b[-1],**changes)
            self.assertEqual(pullback(b,f,s,a,287)[2],'TRIGGER')

    def test_depth_equality_and_just_over(self):
        b,f,s,a=self.fixture();b[-3]=replace(b[-3],low=101.125)
        self.assertIsNone(pullback(b,f,s,a,287)[2])
        b[-3]=replace(b[-3],low=101.124)
        self.assertEqual(pullback(b,f,s,a,287)[2],'PULLBACK')

    def test_short_is_exact_mirror_of_long(self):
        b,f,s,a=self.fixture()
        b=[Bar(x.time,210-x.open,210-x.low,210-x.high,210-x.close) for x in b]
        f,s=[210-x for x in f],[210-x for x in s]
        self.assertEqual(pullback(b,f,s,a,287),(285,-1,None))
        p,e=decide(b,f,s,a,Context());self.assertIsNone(e);self.assertEqual(p['direction'],-1)
        self.assertGreater(p['sl_ticks']/10,p['entry_ref'])

    def test_pivot_three_right_bar_delay_and_ties(self):
        b=[Bar(ANCHOR+k*STEP,100,102,99,100) for k in range(8)]
        b[3]=replace(b[3],low=95,high=105)
        self.assertIsNone(confirmed_pivot(b,5,1))
        for d in (1,-1):self.assertEqual(confirmed_pivot(b,6,d),3)
        for d,field,value in [(1,'low',95),(-1,'high',105)]:
            tied=list(b);tied[2]=replace(tied[2],**{field:value})
            self.assertIsNone(confirmed_pivot(tied,6,d))
            tied=list(b);tied[4]=replace(tied[4],**{field:value})
            self.assertIsNone(confirmed_pivot(tied,6,d))

    def test_pivots_match_preserved_helper_on_synthetic_bars(self):
        b,_,_,_=self.fixture()
        for i in range(288):
            for d in (1,-1):
                expected=old_pivot(b,i,'Long' if d==1 else 'Short')
                self.assertEqual(confirmed_pivot(b,i,d),None if expected is None else expected[0])

    def test_pivot_age_eighty_inclusive_eighty_one_excluded(self):
        for age, wanted in ((80, None), (81, 'PIVOT')):
            b,f,s,a=self.fixture();b[-11]=replace(b[-11],low=104.)
            j=287-age;b[j]=replace(b[j],low=103.)
            self.assertEqual(decide(b,f,s,a,Context())[1],wanted)

    def test_latest_confirmed_suitable_pivot_selected(self):
        b,f,s,a=self.fixture();b[-7]=replace(b[-7],low=103.5)
        plan,error=decide(b,f,s,a,Context())
        self.assertIsNone(error)
        self.assertEqual(plan['pivot_id'],b[-7].time)

    def test_stop_side_invalid_pivot_and_nonpositive_stop(self):
        self.assertEqual(levels(100,101,2,1)[1],'PIVOT_SIDE')
        self.assertEqual(levels(100,99,2,-1)[1],'PIVOT_SIDE')
        self.assertEqual(levels(.1,.05,1,1)[1],'STOP_SIDE')

    def test_stop_distance_boundaries_exact(self):
        for r,ok in [(1.5,True),(5.,True),(math.nextafter(1.5,0),False),(math.nextafter(5.,6),False)]:
            self.assertEqual(stop_range(r,2),ok)

    def test_tick_rounding_both_directions_and_no_epsilon(self):
        self.assertEqual(ticks(102.69,1),1026)
        self.assertEqual(ticks(102.61,-1),1027)
        for raw in (102.69,102.61,.3,12345.67):
            for d in (1,-1):
                n,value=round_stop(raw,'0.10','Long' if d==1 else 'Short')
                self.assertEqual(ticks(raw,d),n)
                self.assertEqual(n/10.,value)

    def test_cost_floor_inclusive_boundary(self):
        self.assertTrue(cost_gate(10,4))
        self.assertFalse(cost_gate(10,math.nextafter(4,5)))
        for c in (None,0,-1,float('nan')):self.assertFalse(cost_gate(10,c))

    def test_research_cost_assumptions_and_frozen_sizing_match(self):
        from tools.verify_research_freeze import load, ROOT
        config=load(ROOT/'configs/research_v0.2.2.json')
        p,e=self.plan();self.assertIsNone(e)
        self.assertEqual(p['cost'],(108+102.6)*(.00055+.0002))
        st=SimpleNamespace(levels_valid=True,risk=p['risk'],cost=p['cost'],entry_ref=108,tp1=116.1,tp2=121.5)
        self.assertEqual(size_steps(st,10000.,config),(p['steps'],None))
        self.assertEqual(config['K_cost_stop'],2.5)

    def test_total_and_split_integer_steps(self):
        self.assertEqual(split(3),(3,1,2))
        self.assertEqual(split(4),(4,2,2))
        for n in (0,1,-1,True,3.0):self.assertIsNone(split(n))

    def test_entry_minimum_notional_and_single_leg_failure(self):
        self.assertEqual(size(2000,100,2.925,125),((3,1,2),None))
        self.assertEqual(size(2000,100,2.925,90)[1],'ENTRY_MINIMUM')
        self.assertEqual(size(10000,100,10,50)[1],'PARTIAL_QUANTITY')

    def test_entry_maximum_and_balance_invalid(self):
        self.assertEqual(size(100,1,1,10000000)[1],'ENTRY_MAXIMUM')
        for v in (None,0,-1,float('inf')):self.assertEqual(size(100,1,1,v)[1],'BUDGET')

    def test_no_exit_minimum_notional_is_invented(self):
        result,error=size(2000,100,2.925,125)
        self.assertIsNone(error);self.assertLess(result[1]/1000*2150,5)

    def test_tp_rounding_geometry_without_extra_rr_cutoff(self):
        p,e=levels(108.03,103,2.5,1);self.assertIsNone(e)
        self.assertLess(p['rr1'],1.5)
        self.assertGreater(p['tp2_ticks'],p['tp1_ticks'])
        self.assertGreater(p['tp1_ticks']/10,p['entry_ref'])

    def test_consumption_only_on_explicit_diagnostic_acceptance(self):
        c=Context();p,e=self.plan(c);self.assertIsNone(e);self.assertEqual(c.consumed,set())
        accept(p,c);self.assertEqual(self.plan(c)[1],'CONSUMED')
        with self.assertRaisesRegex(ValueError,'CONSUMED'):accept(p,c)
        c.consumed={( -1,p['pullback_id'])};self.assertIsNone(self.plan(c)[1])

    def test_busy_and_daily_stop_do_not_consume(self):
        for c in (Context(busy=True),Context(daily_stop=True)):
            self.assertIn(self.plan(c)[1],('BUSY','DAILY_STOP'));self.assertEqual(c.consumed,set())

    def test_frozen_baseline_helper_matches_new_predicate_fixture(self):
        b,f,s,a=self.fixture()
        self.assertEqual(old_baseline(b,287,f,s,a),('Long',285,None))
        self.assertEqual(pullback(b,f,s,a,287),(285,1,None))

    def test_missing_feature_or_invalid_prices_rejected(self):
        for v in (None,float('nan'),float('inf')):
            self.assertEqual(direction(v,100,99),0)
            self.assertEqual(levels(108,103,v,1)[1],'INVALID_LEVEL_INPUT')
        st=State();self.assertEqual(st.feed(ANCHOR,(100,None,99,101),Context())[1],'UNAVAILABLE')
        self.assertEqual(st.feed(ANCHOR+STEP,(100,102,99,101),Context())[1],'UNAVAILABLE')

    def test_windows_and_no_trade_start_reset(self):
        b,f,s,a=self.fixture();self.assertIsNone(decide(b,f,s,a,Context())[1])
        for close in (START-STEP,END,END+STEP):
            changed=list(b);changed[-1]=replace(changed[-1],time=close-STEP)
            self.assertEqual(decide(changed,f,s,a,Context())[1],'WINDOW')
        state=State()
        for i in range(289):state.feed(ANCHOR+i*STEP,(100,102,99,101),Context())
        self.assertEqual(state.numeric.n,289)

    def test_pre_anchor_protected_values_never_touched(self):
        a,b=State(),State()
        self.assertEqual(a.feed(ANCHOR-STEP,Untouchable(),Context())[1],'UNAVAILABLE')
        for i in range(300):
            self.assertEqual(a.feed(ANCHOR+i*STEP,(100,102,99,101),Context()),b.feed(ANCHOR+i*STEP,(100,102,99,101),Context()))

    def test_no_forward_input_access_or_unconfirmed_changes(self):
        s=State();s.feed(ANCHOR,Untouchable(),Context(),False);self.assertEqual(s.numeric.n,0)
        b,f,slow,a=self.fixture();original=pullback(b,f,slow,a,287)
        b.append(Bar(END,1e9,2e9,1,1e9));f.append(1e9);slow.append(1e9);a.append(1e9)
        self.assertEqual(pullback(b,f,slow,a,287),original)

    def test_gap_and_missing_anchor_quarantine(self):
        s=State();self.assertEqual(s.feed(ANCHOR+STEP,Untouchable(),Context())[1],'UNAVAILABLE')
        s=State();s.feed(ANCHOR,(100,102,99,101),Context())
        self.assertEqual(s.feed(ANCHOR+2*STEP,Untouchable(),Context())[1],'UNAVAILABLE')

    def test_numerical_state_matches_frozen_helpers(self):
        s=State()
        bars=[]
        for i in range(300):
            v=(100+i*.02,102+i*.02,99+i*.02,101+i*.02)
            s.feed(ANCHOR+i*STEP,v,Context());bars.append(Bar(ANCHOR+i*STEP,*v))
        self.assertEqual(s.fast,ema([b.close for b in bars],20))
        self.assertEqual(s.slow,ema([b.close for b in bars],50))
        self.assertEqual(s.atr,atr14(bars))

    def test_replay_is_deterministic_with_identical_ids_and_integer_outputs(self):
        a,b=self.plan()[0],self.plan()[0]
        self.assertEqual(json.dumps(a,sort_keys=True),json.dumps(b,sort_keys=True))
        for k in ('sl_ticks','tp1_ticks','tp2_ticks','pullback_id','pivot_id'):self.assertIs(type(a[k]),int)

    def test_source_only_safety_review_not_compiler_validation(self):
        text=(Path(__file__).resolve().parents[1]/'pine/Phase5B1_C01_Decision_Probe_UNVALIDATED.pine').read_text()
        for token in ('request.security','strategy.', 'alertcondition(', 'alert(', 'ta.ema(', 'ta.rma(', 'ta.pivot'):
            self.assertNotIn(token,text)
        self.assertIn('K_COST_STOP = 2.5',text)
        self.assertIn('totalSteps - firstSteps',text)
        self.assertIn('input.bool(false',text)

    def test_reference_has_no_io_dependency(self):
        with patch('builtins.open',side_effect=AssertionError('NO FILE ACCESS')):
            self.assertIsNone(self.plan()[1])
