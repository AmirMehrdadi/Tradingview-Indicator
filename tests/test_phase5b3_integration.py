"""Stage B synthetic integration and preserved-source static checks."""
from pathlib import Path
from dataclasses import replace
import hashlib
import json
import math
import re
import unittest
from research.fixture_state_v1.state import Lifecycle, Candle, Decision, FixtureError, ANCHOR,START,END,STEP,DAY
from research.fixture_state_v1.integration import CandidatePath, REGISTRY
from tests import test_phase5b3_state as a


def synthetic_bars(count=500):
    out=[]
    for i in range(count):
        previous=100.+.02*(i-1)+math.sin((i-1)/6)
        close=100.+.02*i+math.sin(i/6)+(1.8 if i%13==0 else 0.)
        out.append(Candle(ANCHOR+i*STEP,previous,max(previous,close)+.8+.01*(i%4),min(previous,close)-.8-.01*(i%3),close))
    return out


class IntegrationTests(unittest.TestCase):
    def ready(self,cid='C01',enabled=True):
        p=CandidatePath(cid,enabled=enabled);p.model.process(a.bar(START-STEP));return p

    def test_registry_exact_twelve_and_invalid_candidate(self):
        self.assertEqual(list(REGISTRY),['C%02d'%n for n in range(1,13)])
        with self.assertRaises(FixtureError):CandidatePath('C13')

    def test_all_candidates_queue_on_matching_prevalidated_decision_and_bits(self):
        for cid,filters in REGISTRY.items():
            p=self.ready(cid);self.assertTrue(p.offer_decision(a.decision(candidate=cid),dict.fromkeys('RHVMQ',True)))
            self.assertEqual(p.model.state,'PENDING_ENTRY');self.assertEqual(p.decisions[-1]['classification'],'QUEUED_NOT_FILLED')
            self.assertIn(':'+cid+':',p.decisions[-1]['entry_id'])
            self.assertEqual(p.decisions[-1]['filter_bits'],sum({'R':1,'H':2,'V':4,'M':8,'Q':16}[x] for x in filters))

    def test_each_active_optional_rejection_does_not_consume(self):
        for cid,filters in REGISTRY.items():
            for f in filters:
                p=self.ready(cid);flags=dict.fromkeys('RHVMQ',True);flags[f]=False
                self.assertFalse(p.offer_decision(a.decision(candidate=cid),flags));self.assertEqual(p.model.consumed,set())

    def test_non_h_and_inactive_filters_do_not_require_hour_or_volume(self):
        p=self.ready();self.assertTrue(p.offer_decision(a.decision(),{}))
        p=self.ready('C03');self.assertFalse(p.offer_decision(a.decision(candidate='C03'),{}))

    def test_disabled_busy_and_daily_block_without_consuming(self):
        p=self.ready(enabled=False);self.assertFalse(p.offer_decision(a.decision(),{}));self.assertEqual(p.model.consumed,set())
        p=self.ready();p.model.daily_stop=True;self.assertFalse(p.offer_decision(a.decision(),{}));self.assertEqual(p.model.consumed,set())
        p=self.ready();p.offer_decision(a.decision(),{});before=set(p.model.consumed)
        self.assertFalse(p.offer_decision(replace(a.decision(),pullback_id=START-4*STEP),{}));self.assertEqual(p.model.consumed,before)
        p.model.process(a.bar());self.assertFalse(p.offer_decision(replace(a.decision(START+STEP),pullback_id=START-5*STEP),{}))
        self.assertEqual(p.model.consumed,before)

    def test_cross_candidate_no_consumption_or_position_contamination(self):
        x,y=self.ready('C01'),self.ready('C02')
        self.assertTrue(x.offer_decision(a.decision(),{}))
        self.assertFalse(y.offer_decision(a.decision(candidate='C02'),{'R':False}))
        self.assertEqual(y.model.state,'FLAT');self.assertEqual(y.model.consumed,set())
        self.assertTrue(y.offer_decision(a.decision(candidate='C02'),{'R':True}))
        x.model.process(a.bar(h=106,l=99));self.assertEqual(x.model.state,'FLAT');self.assertEqual(y.model.state,'PENDING_ENTRY')

    def test_rejected_entry_keeps_consumed_pullback_and_order_identity(self):
        p=self.ready();p.offer_decision(a.decision(),{});eid=p.decisions[0]['entry_id']
        p.model.process(a.bar(o=30000,h=30001,l=29999,c=30000))
        self.assertEqual(p.model.state,'FLAT');self.assertEqual(len(p.model.consumed),1)
        self.assertTrue(any(e.get('entry_id')==eid and e['name']=='ENTRY_REJECTED_MARGIN' for e in p.model.events))

    def test_dynamic_balance_is_read_from_own_full_settled_snapshot(self):
        p=self.ready();p.offer_decision(a.decision(),{});p.model.process(a.bar(h=104,l=99))
        self.assertEqual(p.model.settled,10000.)
        p.model.process(a.bar(START+STEP,h=106,l=99));self.assertNotEqual(p.model.settled,10000.)
        untouched=CandidatePath('C02');self.assertEqual(untouched.model.settled,10000.)

    def test_actual_synthetic_stream_has_causal_decisions_and_fills(self):
        p=CandidatePath(enabled=True)
        for b in synthetic_bars():p.feed(b,None)
        self.assertGreater(len(p.decisions),0)
        self.assertTrue(any(e['name']=='ENTRY' for e in p.model.events))
        for e in p.model.events:
            if e['name']=='ENTRY':
                d=next(d for d in p.decisions if d['entry_id']==e['entry_id'])
                self.assertEqual(e['time'],d['signal_close'])
        p.model.invariants()

    def test_raw_synthetic_stream_all_paths_have_independent_histories(self):
        paths=[CandidatePath(cid,enabled=True) for cid in REGISTRY]
        for b in synthetic_bars():
            for p in paths:p.feed(b,None)
        self.assertTrue(all(p.history.numeric.n==500 for p in paths))
        self.assertTrue(all(p.model.candidate==p.candidate for p in paths))
        self.assertTrue(all(p.model.consumed is not q.model.consumed for i,p in enumerate(paths) for q in paths[i+1:]))
        for p in paths:
            self.assertTrue(all(e['candidate']==p.candidate for e in p.model.events));p.model.invariants()
        self.assertGreater(len(paths[0].decisions),0)
        self.assertEqual(paths[3].decisions,[]) # Missing V, not missing OHLC.

    def test_hourly_completed_input_cannot_arrive_from_future(self):
        p=CandidatePath();b=a.bar(ANCHOR)
        p.feed(b)
        with self.assertRaisesRegex(FixtureError,'FUTURE_HOUR'):p.add_hour(a.bar(ANCHOR))
        for k in range(1,4):p.feed(a.bar(ANCHOR+k*STEP))
        self.assertIsNotNone(p.add_hour(a.bar(ANCHOR)))
        self.assertEqual(p.hours.values[ANCHOR+3600000][2],1)

    def test_future_hour_on_feed_is_rejected_before_execution_mutation(self):
        p=CandidatePath();before=p.model.serialized()
        with self.assertRaisesRegex(FixtureError,'FUTURE_HOUR'):p.feed(a.bar(ANCHOR),hour=a.bar(ANCHOR))
        self.assertEqual(p.model.serialized(),before)
        self.assertEqual(p.history.numeric.n,0)

    def test_missing_hour_quarantines_h_only(self):
        p=CandidatePath();p.feed(a.bar(ANCHOR))
        for k in range(1,8):p.feed(a.bar(ANCHOR+k*STEP))
        self.assertIsNone(p.add_hour(a.bar(ANCHOR+3600000)))
        self.assertTrue(p.hours.numeric.poisoned);self.assertFalse(p.model.quarantined)
        self.assertEqual(p.history.numeric.n,8)

    def test_prefix_independence_unconfirmed_and_invalid_origin(self):
        p=CandidatePath();before=p.model.serialized()
        with self.assertRaises(FixtureError):p.feed(a.bar(ANCHOR-STEP))
        self.assertEqual(p.model.serialized(),before)
        self.assertIsNone(p.feed(a.bar(ANCHOR),confirmed=False));self.assertEqual(p.history.numeric.n,0)
        with self.assertRaises(FixtureError):p.feed(replace(a.bar(ANCHOR),provenance='HISTORICAL'))

    def test_missing_anchor_and_invalid_ohlc_quarantine(self):
        p=CandidatePath()
        with self.assertRaises(FixtureError):p.feed(a.bar(ANCHOR+STEP))
        self.assertTrue(p.model.quarantined)
        p=CandidatePath()
        with self.assertRaises(FixtureError):p.feed(a.bar(ANCHOR,h=None))
        self.assertTrue(p.model.quarantined)

    def test_warmup_and_trade_start_keep_numerical_history(self):
        p=CandidatePath(enabled=True)
        for b in synthetic_bars(288):p.feed(b)
        self.assertEqual(p.history.numeric.n,288)
        self.assertTrue(all(START<=d['signal_close']<END for d in p.decisions))
        p.feed(synthetic_bars(289)[-1]);self.assertEqual(p.history.numeric.n,289)

    def test_explicit_end_rejection_without_protective_cancellation(self):
        p=self.ready();d=replace(a.decision(),signal_close=END)
        with self.assertRaises(FixtureError):p.offer_decision(d,{})
        p=self.ready();p.offer_decision(a.decision(),{})
        before=p.model.pending
        with self.assertRaises(FixtureError):p.feed(a.bar(END))
        self.assertEqual(p.model.pending,before)

    def test_no_future_close_can_mutate_an_already_queued_decision(self):
        a1,a2=self.ready(),self.ready();a1.offer_decision(a.decision(),{});a2.offer_decision(a.decision(),{})
        self.assertEqual(a1.decisions,a2.decisions)
        a1.model.process(a.bar(h=101,l=99));a2.model.process(a.bar(h=110,l=90))
        self.assertEqual(a1.decisions,a2.decisions)

    def test_preserved_pine_sources_no_duplicate_global_declarations(self):
        root=Path(__file__).resolve().parents[1]
        for p in sorted((root/'pine').glob('*.pine')):
            names=[]
            for line in p.read_text().splitlines():
                if not line or line[0].isspace() or line.startswith('//'):continue
                m=re.match(r'^(?:const |var |varip )?(?:int|float|bool|string|array<[^>]+>)\s+(\w+)\s*=',line)
                if m:names.append(m[1])
                m=re.match(r'^\[([^]]+)\]\s*=',line)
                if m:names += [s.strip() for s in m[1].split(',')]
            self.assertEqual(len(names),len(set(names)),str(p))

    def test_deterministic_combined_replay_and_guard_denial(self):
        hashes=[]
        for _ in range(2):
            p=CandidatePath(enabled=True)
            for b in synthetic_bars():p.feed(b,None)
            hashes.append(hashlib.sha256(p.model.serialized()).hexdigest())
        self.assertEqual(hashes[0],hashes[1])
        from tests.run_phase4c_regression import OfflineGuard,ProhibitedAccess,ROOT
        guard=OfflineGuard()
        with self.assertRaises(ProhibitedAccess):guard.audit('open',(str(ROOT/'data/stage0b_private/forbidden'),'r',0))
        with self.assertRaises(ProhibitedAccess):guard.audit('socket.connect',(None,('example.invalid',443)))
