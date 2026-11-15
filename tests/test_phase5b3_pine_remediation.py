"""Independent literal fixture expectations and source-only remediation checks."""
from copy import deepcopy
from dataclasses import replace
from pathlib import Path
import re,subprocess,unittest
from research.fixture_state_v1.state import Lifecycle,FixtureError,START,END,STEP,DAY
from research.fixture_state_v1.integration import CandidatePath,REGISTRY
from tests import test_phase5b3_state as f
from tests.test_phase5b3_integration import synthetic_bars
from tests.test_phase5b3_pine import declaration_scan
from tests.phase5b3_pine_audit_reference import AuditedLifecycle,canonical_id,BAR_RESERVE

ROOT=Path(__file__).resolve().parents[1]
PINE='pine/Phase5B3_Integrated_Research_Probe_UNVALIDATED.pine'
ORIGINAL='ae2dc03734d660ba79d85b7965cc2892e51129de'
SOURCE_OVERRIDE=None


def require_identity(source):
    assert 'runId + "/Research/" + cid + "/November2026/" + str.tostring(barOpen) + "/" + str.tostring(direction)' in source,'INCOMPLETE_SIX_COMPONENT_ID'
    assert 'this.entryId := f_canonicalResearchId(this.runId, cid, barOpen, direction)' in source,'CANONICAL_ENTRY_NOT_BOUND'


def require_audit(source):
    assert 'type ResearchAuditRow' in source and 'array<ResearchAuditRow> audit' in source,'MISSING_APPEND_ONLY_ECONOMIC_AUDIT'
    for token in ('"ENTRY"','"EXIT"','"FULL_FLAT_SETTLEMENT"','"ENTRY_REJECTED_MARGIN"','"PARTITION_CENSORED"'):
        assert 'this.appendResearchAudit('+token in source,'MISSING_AUDIT_EVENT_'+token


class AuditReferenceTests(unittest.TestCase):
    def ready(self,t=START,side=1,steps=1001,run='review-A'):
        e=AuditedLifecycle(run_id=run);e.process(f.bar(t-STEP));e.queue(f.decision(t,side,steps));return e
    def fills(self,e):return [r for r in e.tape if r['kind'] in ('ENTRY','EXIT')]

    def test_six_component_identity_literal_and_distinct_runs(self):
        self.assertEqual(canonical_id('review-A','C01',1793749500000,1),'review-A/Research/C01/November2026/1793749500000/1')
        self.assertNotEqual(self.ready(run='review-A').trade_id,self.ready(run='review-B').trade_id)
        self.assertEqual(self.ready().trade_id,self.ready().trade_id) # Deterministic, no automatic uniqueness claim.

    def test_reject_ambiguous_or_empty_run_names(self):
        for run in ('','a/b','a:b','a b','a\nb','x'*65):
            with self.assertRaises(FixtureError):canonical_id(run,'C01',START-STEP,1)

    def test_queue_is_busy_without_fee_or_fill(self):
        e=self.ready();r=e.tape[-1]
        self.assertEqual(r['kind'],'PLAN_QUEUED');self.assertEqual(r['fill_count'],0);self.assertEqual(r['reservations'],[500,501])
        self.assertEqual(r['steps'],0);self.assertEqual(r['remaining'],[0,0]);self.assertTrue(r['occupied'])
        self.assertIsNone(r['fee']);self.assertIsNone(r['price']);self.assertIsNone(r['release_time'])

    def test_literal_entry_and_two_target_fees_and_fill_counts(self):
        e=self.ready();e.process(f.bar(h=106));rows=self.fills(e)
        self.assertEqual([r['steps'] for r in rows],[1001,500,501]);self.assertEqual([r['fill_count'] for r in rows],[1,2,3])
        for r,price,fee in zip(rows,[100.02,102.9794,104.979],[.055066011,.028319335,.02892696345]):
            self.assertAlmostEqual(r['price'],price,places=10);self.assertAlmostEqual(r['fee'],fee,places=12)
            self.assertTrue(r['fill_id'].startswith(e.trade_id+'/'))
        self.assertAlmostEqual(e.cash,10003.85184669055,places=8)
        self.assertEqual([r['remaining'] for r in rows],[[500,501],[0,501],[0,0]])

    def test_partial_then_full_release_timing_and_settlement(self):
        e=self.ready();e.process(f.bar(h=104));r=self.fills(e)[-1]
        self.assertEqual((r['time'],r['phase']),(START+STEP,'PRIOR_BAR'));self.assertEqual(r['settled'],10000)
        self.assertTrue(r['occupied']);self.assertIsNone(r['release_time']);self.assertEqual(r['remaining'],[0,501])
        self.assertFalse(any(r['kind']=='FULL_FLAT_SETTLEMENT' for r in e.tape))
        e.process(f.bar(START+STEP,h=106));r=e.tape[-1]
        self.assertEqual(r['kind'],'FULL_FLAT_SETTLEMENT');self.assertEqual(r['release_time'],START+2*STEP)
        self.assertEqual(r['phase'],'PRIOR_BAR');self.assertFalse(r['occupied']);self.assertEqual(r['settled'],e.cash)
        self.assertEqual(r['fill_count'],3);self.assertIsNone(r['fee'])

    def test_stop_first_audit_both_directions(self):
        for side in (1,-1):
            e=self.ready(side=side);e.process(f.bar(h=110,l=90));fills=self.fills(e)
            self.assertEqual([r['classification'] for r in fills[1:]],['STOP','STOP'])
            self.assertTrue(any(r['classification']=='UNCERTAIN_INTRABAR_ORDER' for r in e.tape))
            self.assertEqual(sum(r['steps'] for r in fills[1:]),1001)

    def test_tp1_then_stop_and_exact_residual(self):
        e=self.ready();e.process(f.bar(h=104));e.process(f.bar(START+STEP,l=97));rows=self.fills(e)
        self.assertEqual([(r['classification'],r['steps']) for r in rows[1:]],[('TP',500),('STOP',501)])
        self.assertEqual(rows[-1]['remaining'],[0,0]);self.assertEqual(e.tape[-1]['kind'],'FULL_FLAT_SETTLEMENT')

    def test_margin_rejection_has_no_fictitious_fill_or_fee(self):
        e=self.ready();e.process(f.bar(o=30000,h=30001,l=29999,c=30000));r=e.tape[-1]
        self.assertEqual(r['kind'],'ENTRY_REJECTED_MARGIN');self.assertEqual(self.fills(e),[])
        self.assertEqual(r['fill_id'],'');self.assertEqual(r['steps'],0);self.assertEqual(r['fill_count'],0)
        self.assertIsNone(r['fee']);self.assertIsNone(r['price']);self.assertEqual(r['release_time'],START)
        self.assertFalse(r['occupied']);self.assertEqual(e.cash,10000);self.assertEqual(len(e.consumed),1)

    def test_censor_keeps_exposure_without_exit_or_release(self):
        e=self.ready(t=END-STEP);e.process(f.bar(END-STEP,h=104));r=e.tape[-1]
        self.assertEqual((r['kind'],r['time'],r['phase']),('PARTITION_CENSORED',END,'PARTITION_END'))
        self.assertEqual(r['remaining'],[0,501]);self.assertTrue(r['occupied']);self.assertIsNone(r['release_time'])
        self.assertIsNone(r['fee']);self.assertIsNone(r['price']);self.assertEqual(r['fill_count'],2)
        self.assertEqual(len(self.fills(e)),2);self.assertEqual(e.settled,10000)

    def test_entry_stop_and_gap_economic_price(self):
        e=self.ready();e.process(f.bar(o=97,h=99,l=96,c=97));rows=self.fills(e)
        self.assertAlmostEqual(rows[0]['price'],97.0194);self.assertAlmostEqual(rows[-1]['price'],96.9806)
        self.assertTrue(any(r['classification']=='ENTRY_AT_OR_BEYOND_SL' for r in e.tape))
        e=self.ready();e.process(f.bar());e.process(f.bar(START+STEP,o=95,h=96,l=94,c=95))
        self.assertAlmostEqual(self.fills(e)[-1]['price'],94.981)

    def test_open_targets_and_no_later_margin_classification(self):
        e=self.ready();e.process(f.bar(o=110,h=120,l=1,c=100));rows=self.fills(e)
        self.assertEqual([r['phase'] for r in rows],['OPEN','OPEN','OPEN'])
        self.assertNotIn('MARGIN_MODEL_EVENT',[r['classification'] for r in e.tape])
        self.assertEqual(e.tape[-1]['release_time'],START)

    def test_quantity_conservation_and_unique_fill_derivations(self):
        for steps in (1000,1001):
            e=self.ready(steps=steps);e.process(f.bar(h=106));rows=self.fills(e)
            self.assertEqual([r['fill_id'] for r in rows],[e.trade_id+'/ENTRY',e.trade_id+'/L1',e.trade_id+'/L2'])
            self.assertEqual(len(set(r['fill_id'] for r in rows)),3)
            self.assertEqual(sum(r['steps'] for r in rows[1:]),steps)
            for r in rows:self.assertEqual(r['exited']+sum(r['remaining']),steps)
            before=deepcopy(e.tape)
            with self.assertRaises(FixtureError):e.exit_leg(1,105,START+STEP,'PRIOR_BAR','TP')
            self.assertEqual(e.tape,before)

    def test_no_change_to_preserved_economic_results_literal_scenarios(self):
        scenarios=[(1,[f.bar()]),(1,[f.bar(h=106)]),(1,[f.bar(h=104),f.bar(START+STEP,l=97)]),
                   (-1,[f.bar(l=94)]),(1,[f.bar(h=110,l=90)]),(1,[f.bar(o=30000,h=30001,l=29999,c=30000)]),
                   (1,[f.bar(o=102.99,h=102.99,l=102.9,c=102.99)])]
        for side,bars in scenarios:
            a=Lifecycle(fixture_id='fixture:combined');b=AuditedLifecycle()
            for e in (a,b):e.process(f.bar(START-STEP));e.queue(f.decision(side=side))
            for bar in bars:
                a.process(bar);b.process(bar);self.assertEqual(a.serialized(),b.serialized())

    def test_candidatepath_economics_identical_with_observer(self):
        for cid in REGISTRY:
            a=CandidatePath(cid,enabled=True);b=CandidatePath(cid,enabled=True);b.model=AuditedLifecycle(cid)
            for bar in synthetic_bars():
                self.assertEqual(a.feed(bar,volume=100),b.feed(bar,volume=100))
                self.assertEqual(a.model.serialized(),b.model.serialized())

    def test_all_audit_rows_conserve_actual_entered_steps(self):
        for t,b in [(START,f.bar(h=106)),(START,f.bar(o=30000,h=30001,l=29999,c=30000)),(END-STEP,f.bar(END-STEP,h=104))]:
            e=self.ready(t=t);e.process(b)
            for r in e.tape:self.assertEqual(r['exited']+sum(r['remaining']),r['entered'])

    def test_exposure_notional_is_remaining_quantity_at_observed_raw_price(self):
        e=self.ready();e.process(f.bar(h=104));rows=self.fills(e)
        self.assertAlmostEqual(rows[0]['exposure_notional'],100.1)
        self.assertAlmostEqual(rows[1]['exposure_notional'],51.603)
        self.assertAlmostEqual(rows[1]['cash'],10001.396314654,places=8)

    def test_new_trade_resets_audit_quality_and_has_distinct_fill_ids(self):
        e=self.ready();e.process(f.bar(o=110,h=120,l=99,c=100))
        first_id=e.trade_id;self.assertIn('ENTRY_DEVIATION',e.audit_quality)
        e.queue(f.decision(START+STEP));self.assertEqual(e.audit_quality,set())
        self.assertNotEqual(first_id,e.trade_id)
        e.process(f.bar(START+STEP,h=106))
        ids=[r['fill_id'] for r in self.fills(e)];self.assertEqual(len(ids),6);self.assertEqual(len(set(ids)),6)
        self.assertNotIn('ENTRY_DEVIATION',e.audit_quality)

    def test_queue_capacity_failure_does_not_consume_or_freeze_plan(self):
        e=AuditedLifecycle();e.process(f.bar(START-STEP));e.capacity=0
        with self.assertRaisesRegex(FixtureError,'AUDIT_CAPACITY_EXHAUSTED'):e.queue(f.decision())
        self.assertEqual(e.consumed,set());self.assertIsNone(e.pending);self.assertEqual(e.tape,[])
        self.assertEqual(e.cash,10000);self.assertTrue(e.quarantined)

    def test_immutable_prior_record_values(self):
        e=self.ready();e.process(f.bar());before=deepcopy(e.tape)
        e.process(f.bar(START+STEP,h=104));self.assertEqual(e.tape[:len(before)],before)

    def test_capacity_exhaustion_stops_before_economic_mutation(self):
        e=self.ready();e.capacity=len(e.tape)+BAR_RESERVE-1;before=e.serialized();tape=deepcopy(e.tape)
        with self.assertRaisesRegex(FixtureError,'AUDIT_CAPACITY_EXHAUSTED'):e.process(f.bar(h=106))
        self.assertTrue(e.audit_blocked and e.quarantined);self.assertEqual(e.tape,tape)
        # Only the deliberate fail-closed quarantine bit changes.
        e.quarantined=False;self.assertEqual(e.serialized(),before)

    def test_midnight_release_precedes_new_day_snapshot(self):
        e=self.ready(t=START+DAY-STEP);e.process(f.bar(START+DAY-STEP,h=106));r=e.tape[-1]
        self.assertEqual(r['release_time'],START+DAY);self.assertEqual(r['day'],START//DAY)
        self.assertEqual(e.day,(START+DAY)//DAY);self.assertEqual(e.day_start,e.settled)


class RemediationSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.source=SOURCE_OVERRIDE if SOURCE_OVERRIDE is not None else (ROOT/PINE).read_text()

    def test_six_component_identity_contract(self):require_identity(self.source)
    def test_complete_audit_contract(self):require_audit(self.source)

    def test_original_source_fails_both_contracts(self):
        original=subprocess.check_output(['git','show',ORIGINAL+':'+PINE]).decode()
        with self.assertRaisesRegex(AssertionError,'INCOMPLETE_SIX_COMPONENT_ID'):require_identity(original)
        with self.assertRaisesRegex(AssertionError,'MISSING_APPEND_ONLY'):require_audit(original)

    def test_explicit_namespace_and_all_derivations(self):
        s=self.source
        self.assertIn('input.string("phase5b3-pine-v1",',s);self.assertIn('f_validResearchRunId(this.runId)',s)
        for name,suffix in [('leg1Id','L1'),('leg2Id','L2'),('oca1Id','OCA1'),('oca2Id','OCA2')]:
            self.assertIn('this.'+name+' := this.entryId + "/'+suffix+'"',s)
        self.assertIn('this.entryId + "/ENTRY"',s)

    def test_audit_has_required_fields_and_append_only_operations(self):
        s=self.source;row=s[s.index('type ResearchAuditRow'):s.index('type ResearchBook')]
        for field in ('tradeId','fillId','clock','economicPhase','steps','price','fee','remaining1','remaining2','fillCount','releasedAt','quality','classification','exposureNotional','occupied','cash','settled','entered'):
            self.assertRegex(row,r'\b'+field+r'\b')
        self.assertIn('array.push(this.audit, row)',s)
        self.assertIsNone(re.search(r'array\.(?:set|clear|pop|shift|remove)\(this\.audit',s))
        self.assertIsNone(re.search(r'\brow\.\w+\s*:=',s))

    def test_capacity_preflight_precedes_all_bar_mutations(self):
        s=self.source;body=s[s.index('method advanceResearchBar'):s.index('method researchQualityCode')]
        self.assertLess(body.index('this.reserveResearchAudit(16)'),body.index('this.resetResearchDay(barOpen)'))
        self.assertIn('const int AUDIT_CAPACITY = 20000',s)
        self.assertIn('this.auditBlocked := true',s)
        queue=s[s.index('method queueResearchPlan'):s.index('method advanceResearchBar')]
        self.assertLess(queue.index('this.reserveResearchAudit(1)'),queue.index('this.phase := 1'))

    def test_fees_capture_fill_values_not_reconstructed_grid_prices(self):
        s=self.source
        self.assertIn('this.appendResearchAudit("ENTRY", fid, -1, this.total, o, fill, fee, "ENTRY_FILLED", false)',s)
        self.assertIn('this.appendResearchAudit("EXIT", fid, leg, steps, raw, fill, fee,',s)
        for event in ('ENTRY_REJECTED_MARGIN','PARTITION_CENSORED','FULL_FLAT_SETTLEMENT'):
            self.assertRegex(s,r'this\.appendResearchAudit\("'+event+r'", "", -1, 0, [^,]+, na, na,')

    def test_economic_core_and_all_plots_preserved(self):
        old=subprocess.check_output(['git','show',ORIGINAL+':'+PINE]).decode();s=self.source
        for start,end in [('f_valid() =>','// Frozen research assumptions'),('f_ticks(float','bool window ='),('if active and window','// Data Window observations')]:
            self.assertEqual(s[s.index(start):s.index(end)],old[old.index(start):old.index(end)])
        self.assertEqual([l for l in s.splitlines() if l.startswith('plot(')],[l for l in old.splitlines() if l.startswith('plot(')])
        # Identity/audit instrumentation may not add a second cash update or alter existing arithmetic.
        def economic_lines(text):
            text=text[text.index('method assertResearchQuantity'):]
            patterns=('this.cash','this.settled :=','this.dailyStop :=','float fill =','float fee =','float anticipated =','float plannedRisk =','float actualRisk =')
            return [l.strip() for l in text.splitlines() if any(l.strip().startswith(p) for p in patterns)]
        self.assertEqual(economic_lines(s),economic_lines(old))

    def test_global_and_type_declarations_unique_with_new_udt(self):
        s=re.sub(r'(?m)^(\s*)(ResearchAuditRow)(\s+\w+\s*=)',r'\1ResearchBook\3',self.source)
        self.assertEqual(declaration_scan(s)['duplicates'],[])
