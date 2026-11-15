"""Synthetic filter/candidate vectors, not Pine compilation or historical research."""
import ast
import hashlib
import json
import math
from pathlib import Path
import re
import unittest
from unittest.mock import patch
from dataclasses import replace
from research.stage0b.features import adx14, rsi14, regime_pass, volume_pass, momentum_pass, quality_pass
from tests.phase5b1_reference import Bar, Context, State, decide, accept, confirmed_pivot
from tests import test_phase5b1_c01 as baseline_fixtures
from tests.phase5b2_reference import (REGISTRY,BITS,Wilder,oscillator_series,regime,relative_volume,momentum,higher,quality,Hours,selected,Diagnostic,flags_for,ANCHOR,START,END,STEP,HOUR)


class Forbidden:
    def __len__(self):raise AssertionError('Unauthorized values touched')


class FilterTests(unittest.TestCase):
    def fixture(self):return baseline_fixtures.C01Tests().fixture()
    def plan(self):return decide(*self.fixture(),Context())[0]
    def hours(self):
        h=Hours()
        for i in range(90):h.feed(ANCHOR+i*HOUR,(100+i,102+i,99+i,101+i))
        return h

    def test_registry_exact_literal_and_frozen_config(self):
        expected={'C01':(),'C02':('R',),'C03':('H',),'C04':('V',),'C05':('M',),'C06':('Q',),'C07':('R','H'),'C08':('R','V'),'C09':('R','M'),'C10':('H','V'),'C11':('R','H','Q'),'C12':('R','H','V','M','Q')}
        self.assertEqual(REGISTRY,expected)
        config=json.loads((Path(__file__).resolve().parents[1]/'configs/research_v0.2.2.json').read_text())
        self.assertEqual({k:('B',)+v for k,v in REGISTRY.items()},{k:tuple(v) for k,v in config['candidate_combinations'].items()})

    def test_unknown_candidate_rejected(self):
        for cid in ('C00','C13','C1','',None):
            with self.assertRaises(ValueError):Diagnostic(cid)

    def test_all_twelve_pass_with_all_flags_and_exact_id_bits(self):
        expected=[0,1,2,4,8,16,3,5,9,6,19,31]
        for cid,bits in zip(REGISTRY,expected):
            ctx=Context();result=selected(self.plan(),dict.fromkeys(BITS,True),cid,ctx,True)
            self.assertEqual(result['candidate'],cid);self.assertEqual(result['filter_bits'],bits)
            self.assertIn(':'+cid+':',result['decision_id'])
            self.assertEqual(ctx.consumed,{(cid,1,result['pullback_id'])})

    def test_all_filters_computed_from_same_complete_synthetic_fixture(self):
        b,f,s,a=self.fixture();b[-11]=replace(b[-11],high=130.)
        volumes=[10.]*288;volumes[-1]=12.
        plan,error=decide(b,f,s,a,Context());self.assertIsNone(error)
        flags=flags_for(b,f,s,a,volumes,self.hours(),plan)
        self.assertEqual(flags,{'R':True,'H':True,'V':True,'M':True,'Q':True})
        for cid in REGISTRY:
            self.assertIsNotNone(selected(plan,flags,cid,Context(),True))

    def test_each_active_filter_blocks_each_affected_candidate_only(self):
        for cid,required in REGISTRY.items():
            for name in BITS:
                flags=dict.fromkeys(BITS,True);flags[name]=False
                ctx=Context();result=selected(self.plan(),flags,cid,ctx,True)
                self.assertEqual(result is None,name in required)
                if name in required:self.assertEqual(ctx.consumed,set())

    def test_null_flags_only_block_active_filters(self):
        for cid in REGISTRY:
            ctx=Context();result=selected(self.plan(),{},cid,ctx,True)
            self.assertEqual(result is not None,cid=='C01')

    def test_c01_plan_fields_unchanged(self):
        p=self.plan();result=selected(p,{},'C01',Context(),True)
        self.assertEqual({k:result[k] for k in p},p)
        self.assertEqual(p['steps'],(4498,2249,2249))

    def test_candidate_consumption_is_independent(self):
        a,b=Diagnostic('C01',enabled=True),Diagnostic('C02',enabled=True)
        flags=dict.fromkeys(BITS,True)
        self.assertIsNotNone(selected(self.plan(),flags,a.candidate,a.context,True))
        self.assertEqual(b.context.consumed,set())
        self.assertIsNotNone(selected(self.plan(),flags,b.candidate,b.context,True))
        self.assertIsNone(selected(self.plan(),flags,a.candidate,a.context,True))

    def test_candidate_namespacing_even_with_shared_fixture_context(self):
        ctx=Context();flags=dict.fromkeys(BITS,True)
        for cid in REGISTRY:
            self.assertIsNotNone(selected(self.plan(),flags,cid,ctx,True))
        self.assertEqual(len(ctx.consumed),12)
        self.assertIsNone(selected(self.plan(),flags,'C01',ctx,True))

    def test_future_hour_values_and_quarantine_do_not_rewrite_past(self):
        h=self.hours();before=h.at(START)
        h.feed(ANCHOR+90*HOUR,(1e8,1e8+2,1e8-1,1e8+1))
        self.assertEqual(h.at(START),before)
        h.feed(ANCHOR+91*HOUR,(1,None,1,1))
        self.assertEqual(h.at(START),before)
        self.assertIsNone(h.at(ANCHOR+92*HOUR))

    def test_disabled_busy_daily_missing_rejection_do_not_consume(self):
        for ctx,enabled,flags in [(Context(),False,dict.fromkeys(BITS,True)),(Context(busy=True),True,dict.fromkeys(BITS,True)),(Context(daily_stop=True),True,dict.fromkeys(BITS,True)),(Context(),True,{})]:
            self.assertIsNone(selected(self.plan(),flags,'C12',ctx,enabled));self.assertEqual(ctx.consumed,set())

    def test_wilder_literal_nonconstant_seed_and_recurrence(self):
        r=Wilder();values=[r.feed(x) for x in range(1,16)]
        self.assertEqual(values[:13],[None]*13);self.assertEqual(values[13],7.5)
        self.assertEqual(values[14],(1/14)*15+(1-1/14)*7.5)
        before=r.value;self.assertIsNone(r.feed(None));self.assertEqual(r.value,before)

    def test_dm_first_na_and_strict_ties(self):
        b=[Bar(ANCHOR+i*STEP,100,101+i,99-i,100) for i in range(40)]
        a,r,m=oscillator_series(b,[2.+2*i for i in range(40)])
        self.assertEqual(m[0],(None,None));self.assertEqual(m[1:],[(0.,0.)]*39)
        self.assertEqual(a[:27],[None]*27);self.assertEqual(a[27],0.)

    def test_adx_rising_literal_seed_and_reference(self):
        b=[Bar(ANCHOR+i*STEP,100+i,102+i,99+i,101+i) for i in range(50)]
        a,r,m=oscillator_series(b,[3.]*50)
        self.assertEqual(a[:27],[None]*27);self.assertEqual(a[27],100.)
        self.assertEqual(a,adx14(b,[3.]*50))
        self.assertEqual(r,rsi14([x.close for x in b]))

    def test_adx_nonconstant_vectors_match_preserved_helper(self):
        b=[Bar(ANCHOR+i*STEP,100,103+(i%7),97-(i%3),100+math.sin(i)) for i in range(90)]
        atr=[float(x.high-x.low) for x in b]
        a,r,m=oscillator_series(b,atr)
        self.assertEqual(a,adx14(b,atr));self.assertEqual(r,rsi14([x.close for x in b]))

    def test_zero_tr_dm_defined_without_zero_division(self):
        b=[Bar(ANCHOR+i*STEP,100,100,100,100) for i in range(40)]
        a,r,m=oscillator_series(b,[0.]*40)
        self.assertEqual(a[27],0.);self.assertEqual(r[14],50.)

    def test_regime_thresholds_inclusive(self):
        self.assertTrue(regime(20,101,100,4,[2.]*96))
        for args in [(19.999,101,100,4,[2.]*96),(20,100.999,100,4,[2.]*96),(20,101,100,4.001,[2.]*96)]:self.assertFalse(regime(*args))
        self.assertEqual(regime(20,101,100,4,[2.]*96),regime_pass(20,101,100,4,[2.]*96))

    def test_regime_even_median_and_missing_history(self):
        values=[1.]*48+[3.]*48
        self.assertTrue(regime(20,101,100,4,values))
        self.assertFalse(regime(20,101.1,100,4.01,values))
        for v in ([2.]*95,[2.]*97,[2.]*95+[None]):self.assertFalse(regime(20,101,100,4,v))

    def test_prior96_atr_ownership_excludes_current(self):
        b,f,s,a=self.fixture();a[-1]=5.;a[-97:-1]=[1.]*48+[3.]*48
        plan=self.plan()
        with patch('tests.phase5b2_reference.oscillator_series',return_value=([20.]*288,[50.]*288,[])):
            flags=flags_for(b,f,s,a,[10.]*288,None,plan)
        self.assertFalse(flags['R'])
        self.assertTrue(regime(20,f[-1],s[-1],5.,a[-96:]))
        self.assertEqual((sorted(a[-97:-1])[47]+sorted(a[-97:-1])[48])/2,2.)

    def test_hour_exact_anchor_and_first_close_ema_seed(self):
        h=Hours();x=h.feed(ANCHOR,(100,102,99,101))
        self.assertEqual(x[1],101);self.assertEqual(h.values[ANCHOR+HOUR],(101,101,1))

    def test_hour_first_pre_anchor_close_is_never_read(self):
        h=Hours();self.assertIsNone(h.feed(ANCHOR-HOUR,Forbidden()))
        self.assertEqual(h.feed(ANCHOR,(100,102,99,101))[1],101)

    def test_hour_1045_and_1100_ownership_and_slope(self):
        h=self.hours();t=START+11*HOUR
        before=h.at(t-STEP);after=h.at(t)
        self.assertEqual(before[3],t-HOUR);self.assertEqual(after[3],t)
        self.assertEqual(after[0],h.values[t][0]);self.assertEqual(after[1],h.values[t-3*HOUR][0])
        self.assertTrue(higher(after,1));self.assertFalse(higher(after,-1))

    def test_hour_sixty_minimum_and_stale_hour(self):
        h=self.hours();self.assertIsNone(h.at(ANCHOR+59*HOUR));self.assertIsNotNone(h.at(ANCHOR+60*HOUR))
        del h.values[START];self.assertIsNone(h.at(START+STEP))

    def test_hour_missing_anchor_gap_invalid_quarantine(self):
        h=Hours();self.assertIsNone(h.feed(ANCHOR+HOUR,Forbidden()));self.assertIsNone(h.at(START))
        h=Hours();h.feed(ANCHOR,(100,102,99,101));h.feed(ANCHOR+2*HOUR,Forbidden());self.assertTrue(h.numeric.poisoned)
        h=Hours();h.feed(ANCHOR,(100,None,99,101));self.assertTrue(h.numeric.poisoned)

    def test_higher_strict_equalities_short_mirror(self):
        self.assertTrue(higher((99,100,98,START,60),-1))
        for h in [(100,99,100,START,60),(100,100,101,START,60),None]:self.assertFalse(higher(h,1))

    def test_non_h_candidates_ignore_unready_hour(self):
        for cid,filters in REGISTRY.items():
            flags=dict.fromkeys(BITS,True);flags['H']=None
            result=selected(self.plan(),flags,cid,Context(),True)
            self.assertEqual(result is not None,'H' not in filters)

    def test_volume_exact_previous_twenty_and_equality(self):
        self.assertTrue(relative_volume(12,[10.]*20));self.assertFalse(relative_volume(11.999,[10.]*20))
        self.assertFalse(relative_volume(12,[10.]*19));self.assertFalse(relative_volume(12,[10.]*21))
        self.assertEqual(relative_volume(12,[10.]*20),volume_pass(12,[10.]*20))

    def test_volume_zero_and_invalid(self):
        self.assertTrue(relative_volume(0,[0.]*20))
        for v in (None,-1,float('nan'),float('inf')):
            self.assertFalse(relative_volume(v,[10.]*20));self.assertFalse(relative_volume(12,[10.]*19+[v]))

    def test_volume_current_excluded_nonconstant_history(self):
        b,f,s,a=self.fixture();v=[10.]*288;v[-21:-1]=list(range(1,21));v[-1]=12.6
        self.assertTrue(flags_for(b,f,s,a,v,None,self.plan())['V'])
        v[-1]=12.59;self.assertFalse(flags_for(b,f,s,a,v,None,self.plan())['V'])

    def test_bad_volume_does_not_poison_c01_ohlc_state(self):
        d=Diagnostic('C01',enabled=True)
        for i in range(300):d.feed(ANCHOR+i*STEP,(100,102,99,101),None)
        self.assertFalse(d.baseline.numeric.poisoned);self.assertEqual(d.baseline.numeric.n,300)
        self.assertIsNotNone(selected(self.plan(),{'V':False},'C01',Context(),True))

    def test_rsi_literal_first_change_and_zero_special_cases(self):
        for closes,want in [([100.]*40,50.),(list(range(100,140)),100.),(list(range(140,100,-1)),0.)]:
            b=[Bar(ANCHOR+i*STEP,c,c+1,c-1,c) for i,c in enumerate(closes)]
            _,r,_=oscillator_series(b,[2.]*40)
            self.assertEqual(r[:14],[None]*14);self.assertEqual(r[14],want)

    def test_momentum_thresholds(self):
        for r,d,wanted in [(55,1,True),(54.999,1,False),(45,-1,True),(45.001,-1,False),(None,1,False)]:
            self.assertEqual(momentum(r,d),wanted)
            self.assertEqual(momentum(r,d),momentum_pass(r,'Long' if d==1 else 'Short'))

    def test_quality_nearest_opposing_not_farthest(self):
        self.assertFalse(quality(1,2,2,2,[110,102],100,1))
        self.assertTrue(quality(1,2,2,2,[110,103],100,1))
        self.assertTrue(quality(1,2,2,2,[90,97],100,-1))
        self.assertFalse(quality(1,2,2,2,[90,98],100,-1))

    def test_quality_body_span_room_boundaries_and_no_tp2_rule(self):
        self.assertTrue(quality(2.4,3.6,2,2,[103],100,1))
        self.assertFalse(quality(2.4001,3.6,2,2,[103],100,1))
        self.assertFalse(quality(2.4,3.6001,2,2,[103],100,1))
        self.assertFalse(quality(2.4,3.6,2,2,[102.999],100,1))
        self.assertTrue(quality_pass(2.4,3.6,2,2,[3]))
        self.assertLess(3,2.5*2) # Frozen Q does not require TP2 room.

    def test_quality_missing_wrong_side_and_unavailable_values(self):
        for levels in ([],[99,100],[None]):self.assertFalse(quality(1,2,2,2,levels,100,1))
        self.assertFalse(quality(1,2,None,2,[110],100,1))

    def test_opposing_pivot_confirmed_strict_ties(self):
        b=[Bar(ANCHOR+i*STEP,100,102,99,100) for i in range(9)];b[3]=replace(b[3],high=105)
        self.assertIsNone(confirmed_pivot(b,5,-1));self.assertEqual(confirmed_pivot(b,6,-1),3)
        b[4]=replace(b[4],high=105);self.assertIsNone(confirmed_pivot(b,6,-1))

    def test_q_builder_excludes_recent_unconfirmed_and_expired_pivots(self):
        b,f,s,a=self.fixture();plan=self.plan()
        b[-2]=replace(b[-2],high=200)
        self.assertFalse(flags_for(b,f,s,a,[10.]*288,None,plan)['Q'])
        b[100]=replace(b[100],high=200)
        self.assertFalse(flags_for(b,f,s,a,[10.]*288,None,plan)['Q'])
        b[-11]=replace(b[-11],high=130)
        self.assertTrue(flags_for(b,f,s,a,[10.]*288,None,plan)['Q'])

    def test_null_ohlc_and_gap_quarantine_all_candidates(self):
        for cid in REGISTRY:
            d=Diagnostic(cid);d.feed(ANCHOR,(100,None,99,101),None)
            self.assertTrue(d.baseline.numeric.poisoned)
            self.assertIsNone(d.feed(ANCHOR+STEP,(100,102,99,101),10))

    def test_utc_boundary_c01_regression_and_no_reset(self):
        b,f,s,a=self.fixture();p,e=decide(b,f,s,a,Context());self.assertIsNone(e);self.assertEqual(p['signal_close'],START)
        for t in (START-STEP,END,END+STEP):
            bb=list(b);bb[-1]=replace(bb[-1],time=t-STEP)
            self.assertEqual(decide(bb,f,s,a,Context())[1],'WINDOW')
        d=Diagnostic()
        for i in range(289):d.feed(ANCHOR+i*STEP,(100,102,99,101),10)
        self.assertEqual(d.baseline.numeric.n,289)

    def test_prefix_independence_and_denial_before_data_touch(self):
        a,b=Diagnostic(),Diagnostic()
        self.assertIsNone(a.feed(ANCHOR-STEP,Forbidden(),Forbidden()))
        for i in range(300):
            args=(ANCHOR+i*STEP,(100,102,99,101),None)
            self.assertEqual(a.feed(*args),b.feed(*args))
        self.assertEqual(a.baseline.fast,b.baseline.fast)

    def test_deterministic_replay_all_candidates(self):
        for cid in REGISTRY:
            rows=[]
            for repeat in range(2):
                ctx=Context();p=selected(self.plan(),dict.fromkeys(BITS,True),cid,ctx,True)
                rows.append(json.dumps(p,sort_keys=True))
            self.assertEqual(rows[0],rows[1])

    def test_guard_classifies_data_and_network_before_access(self):
        from tests.run_phase4c_regression import OfflineGuard,ProhibitedAccess,ROOT
        g=OfflineGuard()
        with self.assertRaises(ProhibitedAccess):g.audit('open',(str(ROOT/'data/stage0a/forbidden'),'r',0))
        with self.assertRaises(ProhibitedAccess):g.audit('socket.connect',(None,('example.invalid',443)))

    def test_pine_registry_scope_and_offsets_not_compiler_proof(self):
        p=Path(__file__).resolve().parents[1]/'pine/Phase5B2_Selected_Candidate_Probe_UNVALIDATED.pine';text=p.read_text()
        options=re.search(r'options = (\[[^\n]+\])',text).group(1)
        self.assertEqual(ast.literal_eval(options),list(REGISTRY))
        for token in ('strategy.', 'alert(', 'alertcondition(', 'ta.ema(', 'ta.rma(', 'ta.rsi(', 'ta.pivot','nz('):self.assertNotIn(token,text)
        self.assertIn('output[1], output[4]',text);self.assertIn('lookahead = barmerge.lookahead_on',text)
        self.assertIn('for age = 1 to 96',text);self.assertIn('for age = 1 to 20',text)
        self.assertIn('not useH or passH',text)
        self.assertIn('room >= 1.5 * risk',text)

    def test_pine_global_constant_declarations_are_unique(self):
        # Narrow source regression, not a Pine compiler or full language parser.
        source = (Path(__file__).resolve().parents[1]/'pine/Phase5B2_Selected_Candidate_Probe_UNVALIDATED.pine').read_text()
        declarations = re.findall(r'^const[ \t]+[A-Za-z_][A-Za-z0-9_<>]*[ \t]+([A-Za-z_][A-Za-z0-9_]*)[ \t]*=', source, re.MULTILINE)
        self.assertGreater(len(declarations), 0, 'Static scan must find global constants')
        duplicates = sorted({name for name in declarations if declarations.count(name) > 1})
        self.assertEqual(duplicates, [], 'Repeated global constant declarations: '+', '.join(duplicates))

    def test_no_io_in_pure_candidate_decision(self):
        p=self.plan()
        with patch('builtins.open',side_effect=AssertionError('NO_IO')):
            self.assertIsNotNone(selected(p,{},'C01',Context(),True))
