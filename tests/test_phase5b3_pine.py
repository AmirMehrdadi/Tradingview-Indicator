"""Synthetic Python reference and Pine static-contract checks, never Pine execution."""
from dataclasses import replace
from pathlib import Path
import hashlib
import json
import re
import unittest
from research.fixture_state_v1.state import Lifecycle, Candle, FixtureError, ANCHOR,START,END,STEP,DAY
from research.fixture_state_v1.integration import CandidatePath,REGISTRY
from tests.phase5b3_pine_reference import Book
from tests import test_phase5b3_state as fixtures
from tests.test_phase5b3_integration import synthetic_bars

ROOT=Path(__file__).resolve().parents[1]
PINE=ROOT/'pine/Phase5B3_Integrated_Research_Probe_UNVALIDATED.pine'
OLD=ROOT/'pine/Phase5B2_Selected_Candidate_Probe_UNVALIDATED.pine'


def declaration_scan(source):
    """Small indentation-aware declaration scanner, not a Pine grammar/compiler.

    Global, type-field and block-local namespaces are checked separately. Branch
    siblings own distinct scopes; assignments (:=) are not declarations.
    """
    scopes=[(-1,'global',{})];duplicates=[];inventory=[];previous=None
    typed=re.compile(r'(?:(?:var|varip|const)\s+)?(?:int|float|bool|string|color|ResearchBook|array<[^>]+>)\s+(\w+)\s*(?:=|$)')
    for line_no,line in enumerate(source.splitlines(),1):
        code=line.split('//',1)[0].rstrip()
        if not code.strip():continue
        indent=len(code)-len(code.lstrip());s=code.strip()
        while len(scopes)>1 and indent<=scopes[-1][0]:scopes.pop()
        if previous and indent>previous[0]:scopes.append((previous[0],f'block:{previous[1]}',{}))
        names=[]
        m=re.match(r'(?:method\s+)?(\w+)\(.*=>$',s)
        if m:names=[m.group(1)]
        elif s.startswith('type '):names=[s.split()[1]]
        elif s.startswith('[') and '] =' in s:names=[x.strip() for x in s[1:s.index(']')].split(',')]
        else:
            m=typed.match(s)
            if m:names=[m.group(1)]
        scope=scopes[-1]
        for name in names:
            if name in scope[2]:duplicates.append((name,scope[2][name],line_no,scope[1]))
            scope[2][name]=line_no;inventory.append((name,line_no,scope[1]))
        previous=(indent,line_no)
    return {'duplicates':duplicates,'declarations':inventory,'kind':'STATIC_SCANNER_NOT_COMPILER'}


class PythonReferenceTests(unittest.TestCase):
    def pair(self,t=START,side=1,steps=1001):
        x=Lifecycle(fixture_id='fixture:combined');y=Book()
        for e in (x,y):e.process(fixtures.bar(t-STEP));e.queue(fixtures.decision(t,side,steps))
        return x,y

    def same(self,x,y):
        self.assertEqual(x.state,y.state)
        for attr in ('cash','settled','day_start'):self.assertAlmostEqual(getattr(x,attr),getattr(y,attr),places=9)
        self.assertEqual(x.daily_stop,y.daily_stop);self.assertEqual(x.quality,y.quality)
        self.assertEqual(x.consumed,y.consumed);self.assertEqual(x.fill_ids,y.ids)
        self.assertEqual(len(x.completed),len(y.completed));self.assertEqual(len(x.censored),len(y.censored))
        if x.position:self.assertEqual(x.position.remaining,y.left)
        if x.censored:self.assertEqual(x.censored[-1].remaining,y.left)

    def feed(self,pair,b):
        for e in pair:e.process(b)
        self.same(*pair)

    def test_pending_is_not_filled_and_exact_next_open(self):
        x,y=self.pair();self.assertEqual(y.phase,1);self.assertEqual(y.ids,set())
        self.assertEqual(y.cash,10000);self.assertEqual(y.left,[0,0]);self.assertEqual(y.events[-1][0],'QUEUED')
        self.feed((x,y),fixtures.bar());self.assertEqual(y.phase,2);self.assertEqual(y.left,[500,501])
        self.assertEqual(y.fill,100.02);self.assertAlmostEqual(y.cash,10000-1.001*100.02*.00055)

    def test_margin_rejection_no_fee_preserves_consumption(self):
        pair=self.pair();self.feed(pair,fixtures.bar(o=30000,h=30001,l=29999,c=30000));y=pair[1]
        self.assertEqual((y.phase,y.cash,y.settled),(0,10000,10000));self.assertEqual(len(y.consumed),1)
        self.assertEqual(y.ids,set());self.assertEqual(y.events[-1][0],'ENTRY_REJECTED_MARGIN')

    def test_entry_bar_stop_literal_fees_both_sides(self):
        for side in (1,-1):
            pair=self.pair(side=side);self.feed(pair,fixtures.bar(h=103,l=97));y=pair[1]
            raw=98 if side==1 else 102;entry=100*(1+side*.0002);exit=raw*(1-side*.0002)
            expected=10000-1.001*entry*.00055+side*1.001*(exit-entry)-1.001*exit*.00055
            self.assertAlmostEqual(y.cash,expected);self.assertEqual(y.left,[0,0]);self.assertEqual(y.exited,1001)
            self.assertEqual([e[5] for e in y.events if e[0]=='EXIT'],['STOP','STOP'])

    def test_entry_bar_tp1_then_tp2_and_partial_cash(self):
        pair=self.pair();self.feed(pair,fixtures.bar(h=104));y=pair[1]
        self.assertEqual(y.left,[0,501]);self.assertEqual(y.settled,10000);self.assertNotEqual(y.cash,y.settled)
        self.feed(pair,fixtures.bar(START+STEP,h=106));self.assertEqual(y.phase,0);self.assertEqual(y.settled,y.cash)
        self.assertEqual(y.exited,1001)

    def test_tp1_then_remaining_stop(self):
        pair=self.pair();self.feed(pair,fixtures.bar(h=104));self.feed(pair,fixtures.bar(START+STEP,l=97))
        self.assertEqual([(e[4],e[5]) for e in pair[1].events if e[0]=='EXIT'],[(500,'TP'),(501,'STOP')])

    def test_both_targets_open_skip_later_extremum(self):
        pair=self.pair();self.feed(pair,fixtures.bar(o=110,h=120,l=1,c=100));y=pair[1]
        self.assertEqual([e[6] for e in y.events if e[0]=='EXIT'],[103*.9998,105*.9998])
        self.assertNotIn('MARGIN_MODEL_EVENT',y.quality);self.assertEqual(y.left,[0,0])

    def test_short_targets_and_integer_conservation(self):
        for steps in (1000,1001):
            pair=self.pair(side=-1,steps=steps);self.feed(pair,fixtures.bar(l=96));y=pair[1]
            self.assertEqual(y.left,[0,steps-steps//2]);self.feed(pair,fixtures.bar(START+STEP,l=94))
            self.assertEqual(y.exited,steps);self.assertEqual(y.left,[0,0])

    def test_stop_first_ambiguity_keeps_unfavorable_fill(self):
        for side in (1,-1):
            pair=self.pair(side=side);self.feed(pair,fixtures.bar(h=110,l=90));y=pair[1]
            self.assertIn('UNCERTAIN_INTRABAR_ORDER',y.quality)
            self.assertEqual([e[5] for e in y.events if e[0]=='EXIT'],['STOP','STOP'])

    def test_gap_stop_raw_open_not_stop_level(self):
        pair=self.pair();self.feed(pair,fixtures.bar());self.feed(pair,fixtures.bar(START+STEP,o=95,h=96,l=94,c=95))
        self.assertEqual([e[6] for e in pair[1].events if e[0]=='EXIT'],[95*.9998]*2)

    def test_entry_at_stop_retained_and_anomalous(self):
        pair=self.pair();self.feed(pair,fixtures.bar(o=97,h=99,l=96,c=97))
        self.assertIn('ENTRY_AT_OR_BEYOND_SL',pair[1].quality);self.assertEqual(len(pair[1].completed),1)

    def test_friction_crosses_tp_without_raw_marketability(self):
        pair=self.pair();self.feed(pair,fixtures.bar(o=102.99,h=102.99,l=102.9,c=102.99));y=pair[1]
        self.assertIn('FILL_FRICTION_CROSSED_TP',y.quality);self.assertEqual(y.left,[500,501])

    def test_duplicate_exit_and_replay_rejected(self):
        x,y=self.pair();self.feed((x,y),fixtures.bar(h=104))
        with self.assertRaises(FixtureError):y.close_leg(0,103,START+STEP,'PRIOR_BAR','TP')
        before=y.cash
        with self.assertRaises(FixtureError):y.process(fixtures.bar())
        self.assertTrue(y.quarantined);self.assertEqual(y.cash,before)

    def test_invalid_ohlc_validate_before_mutation(self):
        x,y=self.pair();before=y.snapshot()
        with self.assertRaises(FixtureError):y.process(fixtures.bar(h=99))
        self.assertEqual(y.snapshot(),before);self.assertTrue(y.quarantined)

    def test_midnight_prior_bar_settlement_before_day_reset(self):
        t=(START//DAY+1)*DAY-STEP;pair=self.pair(t=t)
        self.feed(pair,fixtures.bar(t,h=106));y=pair[1]
        self.assertEqual(y.day,(t+STEP)//DAY);self.assertEqual(y.day_start,y.settled);self.assertFalse(y.daily_stop)
        exits=[i for i,e in enumerate(y.events) if e[0]=='EXIT'];reset=[i for i,e in enumerate(y.events) if e[0]=='UTC_DAY_RESET']
        self.assertLess(max(exits),max(reset))

    def test_daily_stop_full_settlement_and_reset(self):
        pair=self.pair(steps=10000);self.feed(pair,fixtures.bar())
        self.feed(pair,fixtures.bar(START+STEP,o=80,h=81,l=79,c=80));x,y=pair
        self.assertTrue(y.daily_stop)
        d=replace(fixtures.decision(START+2*STEP),entry_ref=80.,sl_ticks=780,tp1_ticks=830,tp2_ticks=850,steps=1000)
        self.assertFalse(y.queue(d))
        for e in pair:e.reset_day(START+DAY)
        self.same(*pair);self.assertFalse(y.daily_stop);self.assertEqual(y.day_start,y.settled)

    def test_three_step_reservations_and_no_orphan(self):
        x,y=Lifecycle(fixture_id='fixture:combined'),Book()
        for e in (x,y):
            e.process(fixtures.bar(START-STEP,o=2000,h=2001,l=1999,c=2000))
            e.queue(replace(fixtures.decision(steps=3),entry_ref=2000.,sl_ticks=19000,tp1_ticks=21500,tp2_ticks=22500))
        self.feed((x,y),fixtures.bar(o=2000,h=2200,l=1950,c=2100));self.assertEqual(y.left,[0,2]);self.assertEqual(y.exited,1)
        self.feed((x,y),fixtures.bar(START+STEP,o=2100,h=2300,l=2000,c=2200));self.assertEqual(y.left,[0,0]);self.assertEqual(y.exited,3)

    def test_final_prior_bar_complete_is_not_censored(self):
        pair=self.pair(t=END-STEP);self.feed(pair,fixtures.bar(END-STEP,h=106));y=pair[1]
        self.assertEqual(y.phase,3);self.assertEqual(y.censored,[]);self.assertEqual(len(y.completed),1)

    def test_invalid_reservations_and_fill_inputs_leave_quantities_unchanged(self):
        y=Book();y.process(fixtures.bar(START-STEP))
        for d in (replace(fixtures.decision(),steps=True),replace(fixtures.decision(),pullback_id=ANCHOR-STEP),replace(fixtures.decision(),tp2_ticks=20000000)):
            with self.assertRaises(FixtureError):y.queue(d)
        self.assertEqual(y.consumed,set());self.assertTrue(y.queue(fixtures.decision()));y.process(fixtures.bar())
        before=y.snapshot()
        with self.assertRaises(FixtureError):y.close_leg(0,float('nan'),START+STEP,'PRIOR_BAR','TP')
        self.assertEqual(y.snapshot(),before)

    def test_busy_daily_and_candidate_consumption(self):
        x,y=self.pair();before=set(y.consumed)
        self.assertFalse(y.queue(replace(fixtures.decision(),pullback_id=START-4*STEP)));self.assertEqual(y.consumed,before)
        z=Book('C02');z.process(fixtures.bar(START-STEP));self.assertEqual(z.consumed,set())
        self.assertTrue(z.queue(fixtures.decision(candidate='C02')))
        self.assertNotEqual(z.eid,y.eid)

    def test_exclusive_end_prior_effects_then_censor_without_fill(self):
        pair=self.pair(t=END-STEP);self.feed(pair,fixtures.bar(END-STEP,h=104));y=pair[1]
        self.assertEqual(y.phase,4);self.assertEqual(y.left,[0,501]);self.assertEqual(y.settled,10000)
        with self.assertRaises(FixtureError):y.process(fixtures.bar(END))
        z=Book();z.process(fixtures.bar(END-STEP))
        with self.assertRaises(FixtureError):z.queue(fixtures.decision(END))

    def test_anchor_and_first_signal_with_candidatepath(self):
        p=CandidatePath(enabled=True);p.model=Book()
        with self.assertRaises(FixtureError):p.feed(fixtures.bar(ANCHOR+STEP))
        y=Book();y.process(fixtures.bar(START-2*STEP))
        with self.assertRaises(FixtureError):y.queue(fixtures.decision(START-STEP))
        y.process(fixtures.bar(START-STEP));self.assertTrue(y.queue(fixtures.decision(START)))

    def test_all_twelve_combined_streams_match_preserved_candidatepath(self):
        total=0
        for cid in REGISTRY:
            x=CandidatePath(cid,enabled=True);y=CandidatePath(cid,enabled=True);y.model=Book(cid)
            bars=synthetic_bars()
            for i,b in enumerate(bars):
                hour=None
                if i%4==3:
                    group=bars[i-3:i+1];hour=Candle(group[0].time,group[0].open,max(z.high for z in group),min(z.low for z in group),b.close)
                volume=150 if i%7==0 else 100
                self.assertEqual(x.feed(b,volume=volume,hour=hour),y.feed(b,volume=volume,hour=hour));self.same(x.model,y.model)
            self.assertEqual(x.decisions,y.decisions);total+=len(y.decisions)
        self.assertGreater(total,0)

    def test_source_and_reference_have_no_io_adapter(self):
        source=(ROOT/'tests/phase5b3_pine_reference.py').read_text()
        self.assertIsNone(re.search(r'\b(?:open|read_text|read_bytes|urlopen|requests|socket|subprocess)\s*\(',source))
        runner=(ROOT/'tests/run_phase5b3_pine_checks.py').read_text()
        self.assertIn('sys.addaudithook(guard.audit)',runner)
        self.assertNotIn('discover(',runner)

    def test_guard_denies_network_and_protected_cache_paths(self):
        from tests.run_phase5b3_checks import FixtureGuard
        from tests.run_phase4c_regression import ProhibitedAccess
        for action in ('cache','network','export'):
            guard=FixtureGuard()
            with self.assertRaises(ProhibitedAccess):
                if action=='network':guard.audit('socket.connect',())
                else:guard.check_path(ROOT/'data/forbidden_probe',writing=action=='export')
            self.assertEqual(len(guard.blocked),1)
        # Direct policy probes do not open a file or initiate a socket.

    def test_deterministic_reference_replay(self):
        hashes=[]
        for _ in range(2):
            p=CandidatePath(enabled=True);p.model=Book()
            for b in synthetic_bars():p.feed(b,volume=100)
            hashes.append(hashlib.sha256(json.dumps(p.model.snapshot(),sort_keys=True).encode()).hexdigest())
        self.assertEqual(hashes[0],hashes[1])


class PineStaticContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=PINE.read_text();cls.old=OLD.read_text()

    def test_global_type_and_local_declarations_unique(self):
        self.assertEqual(declaration_scan(self.source)['duplicates'],[])

    def test_scanner_detects_duplicate_global_constants_and_fields(self):
        self.assertTrue(declaration_scan(self.source.replace('const int HOUR = 3600000','const int HOUR = 3600000\nconst int HOUR = 3600000'))['duplicates'])
        self.assertTrue(declaration_scan('type X\n    int a = 0\n    int a = 1')['duplicates'])
        self.assertFalse(declaration_scan('f() =>\n    if true\n        int a = 0\n    else\n        int a = 1')['duplicates'])

    def test_exact_candidate_selectors_preserved(self):
        a=self.source[self.source.index('string candidate ='):self.source.index('// Hypothetical Research state')]
        b=self.old[self.old.index('string candidate ='):self.old.index('bool fixtureEnabled')]
        self.assertEqual(a,b)
        self.assertEqual(list(REGISTRY),['C%02d'%n for n in range(1,13)])

    def test_numerical_pivot_filter_core_byte_preserved(self):
        for start,end in [('f_valid() =>','// Frozen research assumptions'),('f_ticks(float','bool window =')]:
            self.assertEqual(self.source[self.source.index(start):self.source.index(end)],self.old[self.old.index(start):self.old.index(end)])

    def test_decision_changes_only_evolving_state_and_queue(self):
        def decision_core(s):return s[s.index('if active and window'):s.index('// Data Window observations')]
        old=decision_core(self.old).replace('fixtureBalance','researchSettled').replace('fixtureBusy','researchBusy').replace('fixtureDailyStop','researchDailyStop').replace('fixtureEnabled','diagnosticEnabled')
        new=decision_core(self.source)
        # Frozen calculation and gate prefix through successful queue point.
        self.assertEqual(new[:new.index('                        bool queued')],old[:old.index('                        accepted := true')])
        self.assertIn('if queued\n                            accepted := true\n                            array.push(used, pullbackId)',new)

    def test_disabled_by_default_no_static_account_inputs(self):
        self.assertIn('input.bool(false, "Enable hypothetical Research diagnostic',self.source)
        for name in ('fixtureBalance','fixtureBusy','fixtureDailyStop'):self.assertNotIn(name,self.source)
        self.assertIn('float researchSettled = book.settled',self.source)

    def test_confirmed_anchor_continuity_and_exclusive_mask(self):
        for token in ('barOpen == DATA_START','barOpen == this.lastBar + STEP','time_close < TRADE_END','sigClose < TRADE_END','barEnd == TRADE_END','this.phase := 4'):
            self.assertIn(token,self.source)
        self.assertIn('if diagnosticEnabled and barstate.isconfirmed and time >= DATA_START and time < TRADE_END',self.source)
        plots=[l for l in self.source.splitlines() if l.startswith('plot(')]
        self.assertTrue(all(('accepted ?' in l or 'stateVisible ?' in l) and 'display.data_window' in l and 'offset = 1' in l for l in plots))
        self.assertFalse(any('book.cash' in l or 'book.settled' in l for l in plots))

    def test_confirmed_hour_ownership_contract(self):
        self.assertIn('[output[1], output[4], sourceClose[1], outputEnd[1], outputCount[1]]',self.source)
        self.assertIn('lookahead = barmerge.lookahead_on',self.source)
        self.assertIn('hEnd == time - time % HOUR',self.source)
        self.assertIn('hCount >= 60',self.source)

    def test_no_order_alert_or_graphical_apis(self):
        code='\n'.join(l.split('//')[0] for l in self.source.splitlines())
        self.assertIsNone(re.search(r'\b(?:strategy\.(?:entry|exit|order|close)|alert|alertcondition|label\.new|line\.new)\s*\(',code))
        self.assertNotIn('strategy(',code)

    def test_frozen_costs_grid_priority_and_settlement_source(self):
        for token in ('const float K_COST_STOP = 2.5','const float FEE = 0.00055','const float FRICTION = 0.0002','const float QSTEP = 0.001','const float TICK = 0.10'):
            self.assertIn(token,self.source)
        self.assertLess(self.source.index('this.stopResearchLegs(o'),self.source.index('bool stopHit'))
        self.assertLess(self.source.index('if stopHit'),self.source.index('this.markResearchMargin(this.side == 1 ? l : h)'))
        self.assertIn('if this.left1 + this.left2 == 0\n            this.phase := 0\n            this.settled := this.cash',self.source)
        self.assertIn('this.exited + this.left1 + this.left2 == this.total',self.source)

    def test_midnight_end_and_margin_after_exit_source_guards(self):
        body=self.source[self.source.index('method advanceResearchBar'):self.source.index('method researchQualityCode')]
        self.assertLess(body.index('this.stopResearchLegs(sl'),body.index('this.resetResearchDay(barEnd)'))
        self.assertIn('if this.phase == 2 and not this.quarantined\n                    this.markResearchMargin(this.side == 1 ? l : h)',body)
        self.assertIn('this.fillResearchLeg(leg, target, o, barOpen, 1)',body)
        self.assertNotIn('this.cash :=',body)
