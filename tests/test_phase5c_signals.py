"""Synthetic presentation expectations and static Pine contracts, never chart execution."""
from copy import deepcopy
from dataclasses import replace,asdict
import hashlib,itertools,json,re,subprocess,unittest
from pathlib import Path
from research.fixture_state_v1.state import Lifecycle,FixtureError,ANCHOR,START,END,STEP
from research.fixture_state_v1.integration import CandidatePath,REGISTRY
from tests import test_phase5b3_state as f
from tests.test_phase5b3_integration import synthetic_bars
from tests.phase5b3_pine_audit_reference import canonical_id
from tests.phase5c_reference import Settings,Snapshot,Presentation,snapshot
from tests.test_phase5b3_pine import declaration_scan

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'pine/Trading_Signals.pine'
PROBE=ROOT/'pine/Phase5B3_Integrated_Research_Probe_UNVALIDATED.pine'
BOUNDARY='// PHASE 5C PRESENTATION BOUNDARY'


def duplicate_table_cell_named_arguments(source):
    """Limited lexical check of direct table.cell calls, not a Pine compiler.

    Mask quoted strings/comments, then split only top-level call arguments.
    No type/signature checking, alias resolution or general Pine parsing.
    """
    masked=re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|//[^\n]*|/\*[\s\S]*?\*/''',
                  lambda m:re.sub(r'[^\n]',' ',m.group()),source)
    duplicates=[]
    for call in re.finditer(r'\btable\s*\.\s*cell\s*\(',masked):
        stack=['('];start=call.end();arguments=[]
        for index in range(start,len(masked)):
            char=masked[index]
            if char in '([{':stack.append(char)
            elif char in ')]}':
                if not stack or stack[-1]!={')':'(',']':'[','}':'{'}[char]:
                    raise ValueError('Unbalanced table.cell delimiters')
                stack.pop()
                if not stack:
                    arguments.append(masked[start:index]);break
            elif char==',' and len(stack)==1:
                arguments.append(masked[start:index]);start=index+1
        else:raise ValueError('Unterminated table.cell call')
        seen=set()
        for argument in arguments:
            named=re.match(r'\s*([A-Za-z_]\w*)\s*=(?!=)',argument)
            if named:
                name=named.group(1)
                if name in seen:duplicates.append((masked.count('\n',0,call.start())+1,name))
                seen.add(name)
    return duplicates


class PresentationTests(unittest.TestCase):
    def ready(self,side=1,t=START,settings=Settings(),steps=1001):
        e=Lifecycle();e.process(f.bar(t-STEP));d=f.decision(t,side,steps);e.queue(d)
        p=Presentation(settings);s=snapshot(e,d)
        p.observe(f.bar(t-STEP),s,d,enabled=True,viewport=(t-STEP,t-STEP))
        return e,d,p

    def test_literal_signal_owning_bar_and_close_start_exception(self):
        e,d,p=self.ready()
        self.assertEqual(p.markers,[(canonical_id('phase5b3-pine-v1','C01',1793749500000,1),1793749500000,1793750400000,1)])
        self.assertEqual(p.objects[0][2],START);self.assertEqual(p.objects[0][3],START+STEP)

    def test_no_marker_without_accepted_queue_or_disabled_or_quarantine(self):
        for enabled,available,phase,plan in [(False,True,1,True),(True,False,1,True),(True,True,0,True),(True,True,1,False)]:
            p=Presentation();s=Snapshot(owner='x',phase=phase,available=available)
            p.observe(f.bar(START-STEP),s,f.decision() if plan else None,enabled=enabled)
            self.assertEqual(p.markers,[]);self.assertEqual(p.objects,[])

    def test_consumed_repeat_does_not_duplicate_marker_or_alert(self):
        e,d,p=self.ready(settings=Settings(alerts=True));s=snapshot(e,d)
        p.observe(f.bar(START-STEP),s,d,enabled=True,realtime=True)
        self.assertEqual(len(p.markers),1);self.assertEqual(p.alerts,[])
        self.assertFalse(e.queue(d))

    def test_long_short_markers_and_price_mapping(self):
        for side,levels in [(1,[100.,98.,103.,105.]),(-1,[100.,102.,97.,95.])]:
            e,d,p=self.ready(side=side)
            self.assertEqual(p.markers[-1][-1],side);self.assertEqual([row[4] for row in p.objects],levels)
            self.assertEqual([row[5] for row in p.objects],['yellow','red','blue','green'])

    def test_frozen_entry_reference_distinct_from_hypothetical_gap_fill(self):
        e,d,p=self.ready();e.process(f.bar(o=101,h=102,l=100,c=101))
        p.observe(f.bar(),snapshot(e,d),enabled=True)
        self.assertEqual(p.objects[0][4],100.);self.assertAlmostEqual(e.position.fill,101.0202)

    def test_expiration_after_second_subsequent_confirmed_bar(self):
        e,d,p=self.ready();self.assertFalse(p.expired)
        for t,expected in [(START,False),(START+STEP,True)]:
            e.process(f.bar(t));p.observe(f.bar(t),snapshot(e,d),enabled=True)
            self.assertEqual(p.expired,expected)
        self.assertEqual(p.expiry,START+2*STEP)

    def test_unconfirmed_bar_does_not_expire_or_notify(self):
        e,d,p=self.ready(settings=Settings(alerts=True));before=deepcopy(p.markers)
        p.observe(f.bar(START+STEP),snapshot(e,d),d,enabled=True,confirmed=False,realtime=True)
        self.assertFalse(p.expired);self.assertEqual(p.markers,before);self.assertEqual(p.alerts,[])

    def test_expiration_does_not_cancel_position_or_reprice_protection(self):
        e,d,p=self.ready()
        for t in (START,START+STEP):
            e.process(f.bar(t));before=e.serialized();p.observe(f.bar(t),snapshot(e,d),enabled=True)
            self.assertEqual(e.serialized(),before)
        self.assertTrue(p.expired);self.assertIsNotNone(e.position);self.assertEqual(e.position.decision,d)
        self.assertEqual(len(p.objects),4)

    def test_expired_manual_and_closed_research_remove_objects(self):
        e,d,p=self.ready();e.process(f.bar(h=106));p.observe(f.bar(),snapshot(e,d),enabled=True)
        self.assertEqual(len(p.objects),4)
        e.process(f.bar(START+STEP));p.observe(f.bar(START+STEP),snapshot(e,d),enabled=True)
        self.assertTrue(p.expired);self.assertEqual(p.objects,[])

    def test_partial_and_closed_status_require_matching_owner(self):
        e,d,p=self.ready();e.process(f.bar(h=104));s=snapshot(e,d)
        self.assertEqual(p.research_status(s),'TP1 FILLED / LEG 2 OPEN')
        self.assertEqual(p.research_status(replace(s,owner='other')),'UNKNOWN')
        e.process(f.bar(START+STEP,l=97));self.assertEqual(p.research_status(snapshot(e,d)),'HYPOTHETICAL CLOSED')

    def test_margin_rejection_does_not_become_actual_position(self):
        e,d,p=self.ready();e.process(f.bar(o=30000,h=30001,l=29999,c=30000))
        p.observe(f.bar(),snapshot(e,d),enabled=True,viewport=(START-STEP,START))
        self.assertEqual(p.dashboard['research'],'ENTRY REJECTED');self.assertEqual(p.dashboard['actual'],'REAL_POSITION_UNKNOWN')
        self.assertEqual(p.dashboard['manual'],'UNCONFIRMED')

    def test_replacement_deletes_all_old_owned_objects(self):
        e,d,p=self.ready();old=list(p.objects);e.process(f.bar(h=106));d2=f.decision(START+STEP);e.queue(d2)
        p.observe(f.bar(),snapshot(e,d2),d2,enabled=True)
        self.assertEqual(len(p.objects),4);self.assertTrue(all(o in p.deleted for o in old))
        self.assertTrue(all(o[0]!=old[0][0] for o in p.objects));self.assertEqual((p.max_lines,p.max_labels),(4,4))
        self.assertEqual(p.research_status(snapshot(e,d2)),'QUEUED — NOT FILLED')

    def test_replaced_older_opportunity_still_expires_at_its_own_deadline(self):
        e,d,p=self.ready();first=p.owner;e.process(f.bar(h=106));d2=f.decision(START+STEP);e.queue(d2)
        p.observe(f.bar(),snapshot(e,d2),d2,enabled=True)
        self.assertEqual(len(p.manual_records),2);self.assertFalse(p.manual_records[0]['expired'])
        e.process(f.bar(START+STEP));p.observe(f.bar(START+STEP),snapshot(e,d2),enabled=True)
        self.assertEqual(p.manual_records[0]['owner'],first);self.assertTrue(p.manual_records[0]['expired'])
        self.assertEqual(p.manual_records[0]['expired_at'],START+2*STEP)
        self.assertFalse(p.manual_records[1]['expired']);self.assertFalse(p.expired)
        self.assertTrue(all(o[0]==p.owner for o in p.objects))

    def test_presentation_capacity_fails_closed_without_kernel_mutation(self):
        from tests.phase5c_reference import MANUAL_CAPACITY
        self.assertEqual(MANUAL_CAPACITY,2592)
        e=Lifecycle();e.process(f.bar(START-STEP));d=f.decision();e.queue(d);p=Presentation(Settings(alerts=True))
        p.manual_records=[dict(deadline=END+STEP)]*MANUAL_CAPACITY;before=e.serialized()
        p.observe(f.bar(START-STEP),snapshot(e,d),d,enabled=True,realtime=True)
        self.assertTrue(p.presentation_blocked);self.assertEqual((p.markers,p.alerts,p.objects),([],[],[]))
        self.assertEqual(e.serialized(),before)

    def test_objects_cannot_cross_end_and_no_future_expiry_evaluation(self):
        e,d,p=self.ready(t=END-STEP)
        self.assertTrue(all(START<=o[2]<=o[3]<END for o in p.objects))
        self.assertEqual(p.objects[0][3],END-1)
        e.process(f.bar(END-STEP));p.observe(f.bar(END-STEP),snapshot(e,d),enabled=True)
        self.assertFalse(p.expired);self.assertEqual(p.objects,[])
        self.assertEqual(p.dashboard,None)

    def test_final_authorized_bar_can_expire_internally_without_end_disclosure(self):
        t=END-2*STEP;e,d,p=self.ready(t=t,settings=Settings(alerts=True))
        e.process(f.bar(t));p.observe(f.bar(t),snapshot(e,d),enabled=True)
        self.assertFalse(p.expired)
        e.process(f.bar(END-STEP));p.observe(f.bar(END-STEP),snapshot(e,d),enabled=True,realtime=True)
        self.assertTrue(p.expired);self.assertEqual(p.manual_records[0]['expired_at'],END)
        self.assertEqual((p.objects,p.dashboard,p.alerts),([],None,[]))
        self.assertEqual(e.censored[-1].remaining,[500,501])

    def test_no_new_objects_or_alerts_before_start_or_at_end(self):
        for close in (START-STEP,END,END+STEP):
            p=Presentation(Settings(alerts=True));d=f.decision(close)
            s=Snapshot(owner='x',phase=1)
            p.observe(f.bar(close-STEP),s,d,enabled=True,realtime=True)
            self.assertEqual((p.markers,p.alerts,p.objects),([],[],[]))

    def test_dashboard_title_unknown_real_position_and_filter_identity(self):
        for cid,flags in REGISTRY.items():
            e=Lifecycle(cid);e.process(f.bar(START-STEP));d=f.decision(candidate=cid);e.queue(d)
            p=Presentation();p.observe(f.bar(START-STEP),snapshot(e,d),d,enabled=True,viewport=(START-STEP,START-STEP))
            self.assertEqual(p.dashboard['title'],'UNVALIDATED — RESEARCH / MANUAL SIGNALS')
            self.assertEqual(p.dashboard['candidate'],cid);self.assertEqual(p.dashboard['filters'],' '.join(('B',)+flags))
            self.assertEqual(p.dashboard['actual'],'REAL_POSITION_UNKNOWN')

    def test_dashboard_hides_unknown_or_forbidden_viewport(self):
        e,d,p=self.ready();s=snapshot(e,d)
        for viewport in (None,(ANCHOR,START),(START,END-STEP),(END,START)):
            p.observe(f.bar(),s,enabled=True,viewport=viewport)
            self.assertIsNone(p.dashboard)

    def test_dashboard_disabled_and_unavailable_have_no_active_claim(self):
        p=Presentation();s=Snapshot(available=False)
        p.observe(f.bar(START-STEP),s,enabled=False,viewport=(START-STEP,START-STEP))
        self.assertEqual(p.dashboard['manual'],'NONE — DISABLED');self.assertEqual(p.dashboard['research'],'DISABLED')
        p.observe(f.bar(START-STEP),s,enabled=True,viewport=(START-STEP,START-STEP))
        self.assertEqual(p.dashboard['research'],'UNKNOWN');self.assertEqual(p.dashboard['direction'],'NEUTRAL')

    def test_available_flat_dashboard_has_no_setup_claim(self):
        p=Presentation();p.observe(f.bar(START-STEP),Snapshot(),enabled=True,viewport=(START-STEP,START-STEP))
        self.assertEqual(p.dashboard['research'],'NO SETUP');self.assertEqual(p.dashboard['phase'],'FLAT')
        self.assertEqual(p.dashboard['manual'],'NONE');self.assertEqual(p.dashboard['actual'],'REAL_POSITION_UNKNOWN')

    def test_alert_default_off(self):
        e=Lifecycle();e.process(f.bar(START-STEP));d=f.decision();e.queue(d);p=Presentation()
        p.observe(f.bar(START-STEP),snapshot(e,d),d,enabled=True,realtime=True)
        self.assertEqual(p.alerts,[])

    def test_alert_confirmed_realtime_single_accepted_owner(self):
        e=Lifecycle();e.process(f.bar(START-STEP));d=f.decision();e.queue(d);p=Presentation(Settings(alerts=True));s=snapshot(e,d)
        p.observe(f.bar(START-STEP),s,d,enabled=True,confirmed=False,realtime=True)
        self.assertEqual(p.alerts,[])
        p.observe(f.bar(START-STEP),s,d,enabled=True,realtime=True)
        p.observe(f.bar(START-STEP),s,d,enabled=True,realtime=True)
        self.assertEqual(len(p.alerts),1);a=p.alerts[0]
        self.assertEqual((a['candidate'],a['direction'],a['signal_close'],a['entry_ref'],a['sl'],a['tp1'],a['tp2']),('C01','LONG',START,100.,98.,103.,105.))
        self.assertEqual(a['actual'],'REAL_POSITION_UNKNOWN')

    def test_short_alert_and_no_historical_delivery(self):
        e=Lifecycle();e.process(f.bar(START-STEP));d=f.decision(side=-1);e.queue(d)
        for realtime in (False,True):
            p=Presentation(Settings(alerts=True));p.observe(f.bar(START-STEP),snapshot(e,d),d,enabled=True,realtime=realtime)
            self.assertEqual(len(p.alerts),int(realtime))
            if realtime:self.assertEqual(p.alerts[0]['direction'],'SHORT')

    def test_hidden_visuals_do_not_disable_explicit_notification(self):
        e=Lifecycle();e.process(f.bar(START-STEP));d=f.decision();e.queue(d)
        p=Presentation(Settings(markers=False,levels=False,dashboard=False,quality=False,alerts=True))
        p.observe(f.bar(START-STEP),snapshot(e,d),d,enabled=True,realtime=True)
        self.assertEqual((p.markers,p.objects,p.dashboard),([],[],None));self.assertEqual(len(p.alerts),1)

    def test_unconfirmed_gap_hides_stale_objects_without_mutating_research(self):
        e,d,p=self.ready();before=e.serialized()
        p.observe(f.bar(START+STEP),snapshot(e,d),enabled=True,confirmed=False,viewport=(START-STEP,START+STEP))
        self.assertEqual(p.objects,[]);self.assertEqual(p.dashboard['research'],'UNKNOWN')
        self.assertEqual(e.serialized(),before)

    def test_all_visual_toggles_leave_immutable_decision_stream_unchanged(self):
        path=CandidatePath(enabled=True);frames=[];last=None
        for b in synthetic_bars():
            event=path.feed(b,volume=100)
            if event:last=path.model.pending[0]
            frames.append((b,snapshot(path.model,last),last if event else None))
        expected=list(path.decisions);before=path.model.serialized();owners=[]
        for toggles in itertools.product((False,True),repeat=5):
            p=Presentation(Settings(*toggles))
            for b,s,d in frames:p.observe(b,s,d,enabled=True,realtime=True,last=False)
            owners.append((p.owner,p.signal_open,p.expired));self.assertEqual(path.model.serialized(),before)
            self.assertEqual(path.decisions,expected);self.assertLessEqual(len(p.objects),4)
        self.assertTrue(expected);self.assertEqual(len(set(owners)),1)

    def test_deterministic_synthetic_presentation_replay(self):
        outputs=[]
        for _ in range(2):
            e,d,p=self.ready(settings=Settings(alerts=True))
            for t in (START,START+STEP):
                e.process(f.bar(t));p.observe(f.bar(t),snapshot(e,d),enabled=True,viewport=(START-STEP,t))
            outputs.append(hashlib.sha256(json.dumps(p.__dict__,sort_keys=True,default=lambda x:asdict(x)).encode()).hexdigest())
        self.assertEqual(outputs[0],outputs[1])

    def test_fixture_provenance_denied_before_presentation(self):
        p=Presentation()
        with self.assertRaises(FixtureError):p.observe(replace(f.bar(),provenance='HISTORICAL'),Snapshot())
        self.assertEqual(p.objects,[])


class SourceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source=SOURCE.read_text();cls.probe=PROBE.read_text();cls.ui=cls.source[cls.source.index(BOUNDARY):]

    def test_whole_approved_backend_byte_preserved_except_indicator_header(self):
        old=self.probe[:self.probe.index('// Data Window observations only')]
        new=self.source[:self.source.index(BOUNDARY)]
        self.assertEqual(old.splitlines(keepends=True)[2:],new.splitlines(keepends=True)[2:])
        self.assertEqual(self.source.count('request.security('),1)

    def test_table_cell_named_arguments_are_unique(self):
        original=subprocess.check_output(['git','show',
            '150b7ecbdad2203969a5a5f5a88cc471d8781700:pine/Trading_Signals.pine']).decode()
        self.assertEqual([name for _,name in duplicate_table_cell_named_arguments(original)],['text_color'])
        fixture=r'''
// table.cell(p, 0, 0, text_color=a, text_color=b)
string note = "table.cell(p, 0, 0, text_color=a, text_color=b)"
table.cell(panel, 0, 0,
    "comma, // text_color=fake, escaped \" quote",
    text_color = color.new(color.white, 5), // text_color=ignored
    bgcolor = nested([1, 2], inner(text_color = color.red)),
    text_size = size.small)
'''
        self.assertEqual(duplicate_table_cell_named_arguments(fixture),[])
        duplicate=fixture.replace('text_size = size.small','text_color = color.green,\n    text_size = size.small')
        self.assertEqual([name for _,name in duplicate_table_cell_named_arguments(duplicate)],['text_color'])
        self.assertEqual(duplicate_table_cell_named_arguments(self.source),[])

    def test_overlay_classification_and_fixed_object_limits(self):
        self.assertIn('UNVALIDATED — RESEARCH / MANUAL SIGNALS',self.source.splitlines()[1])
        self.assertIn('overlay = true, max_lines_count = 4, max_labels_count = 4',self.source)
        self.assertIn('table.new(position.top_right, 2, 8',self.ui)

    def test_default_toggles_and_no_experimental_k_input(self):
        for field,value in [('showSignalMarkers','true'),('showPriceLevels','true'),('showDashboard','true'),('showQualityDiagnostics','false'),('enableSetupAlerts','false')]:
            self.assertIn('bool '+field+' = input.bool('+value+',',self.ui)
        self.assertIn('diagnosticEnabled = input.bool(false,',self.source)
        self.assertIn('const float K_COST_STOP = 2.5',self.source)
        self.assertIsNone(re.search(r'input\.(?:float|int)\(',self.source))

    def test_marker_owner_offset_and_colors(self):
        markers=[l for l in self.ui.splitlines() if l.startswith('plotshape(')]
        self.assertEqual(len(markers),2)
        self.assertTrue(all('newQueuedSetup' in l and 'offset = 0' in l and 'size = size.tiny' in l for l in markers))
        self.assertIn('shape.triangleup',markers[0]);self.assertIn('color.green',markers[0])
        self.assertIn('shape.triangledown',markers[1]);self.assertIn('color.red',markers[1])

    def test_manual_expiration_is_presentation_only(self):
        self.assertIn('view.expiresClose := time_close + 2 * STEP',self.ui)
        self.assertIn('time_close >= view.expiresClose',self.ui)
        self.assertNotIn('strategy.cancel',self.ui)
        self.assertIsNone(re.search(r'\b(?:book|state)\.\w+\s*(?::=|\+=|-=)',self.ui))
        self.assertIsNone(re.search(r'\b(?:accepted|side|candidate|consumedLong|consumedShort)\s*:=',self.ui))

    def test_exact_frozen_price_snapshot_and_object_bounds(self):
        for token in ['view.reference := book.entryRef','view.stop := book.slTicks / 10.0','view.target1 := book.tp1Ticks / 10.0','view.target2 := book.tp2Ticks / 10.0','TRADE_END - 1','xloc = xloc.bar_time','extend = extend.none','line.delete(array.pop(ownedLines))','label.delete(array.pop(ownedLabels))']:
            self.assertIn(token,self.ui)
        self.assertNotIn('extend.right',self.ui.split('f_syncLevelObjects',1)[1].split('f_setupMessage',1)[0].split('// No extend.right.',1)[-1])
        self.assertNotIn('line.set_y',self.ui);self.assertNotIn('label.set_y',self.ui)
        self.assertLess(self.ui.index('f_clearLevelObjects(ownedLevelLines, ownedLevelLabels)\n    view.owner'),self.ui.index('view.owner := book.entryId'))

    def test_every_manual_deadline_survives_owner_replacement(self):
        self.assertIn('const int UI_SIGNAL_CAPACITY = 2592',self.ui)
        self.assertIn('array.push(manualSignalRecords, ManualSignalView.new(',self.ui)
        self.assertIn('record.expiredAt := time_close',self.ui)
        self.assertIn('time_close <= TRADE_END',self.ui)
        self.assertIn('presentationBlocked := true',self.ui)
        self.assertLess(self.ui.index('// Mature all earlier manual opportunities'),self.ui.index('view.owner := book.entryId'))
        self.assertNotIn('array.clear(manualSignalRecords)',self.ui)

    def test_owner_proof_prevents_same_bar_old_fill_reassignment(self):
        self.assertIn('view.owner == state.entryId and view.signalClose == state.lastQueue',self.ui)
        self.assertNotIn('book.filledThisBar',self.ui);self.assertNotIn('book.exitMask',self.ui)
        self.assertIn('state.phase == 2 and state.hasFilled and state.left1 == 0 and state.left2 > 0',self.ui)

    def test_alert_one_dynamic_text_api_gated_not_execution_payload(self):
        code='\n'.join(l.split('//')[0] for l in self.ui.splitlines())
        self.assertEqual(len(re.findall(r'\balert\(',code)),1)
        self.assertIn('if enableSetupAlerts and barstate.isrealtime and newQueuedSetup and signalOwnerWindow and presentationAvailable and view.owner != view.lastAlertId',code)
        self.assertIn('alert.freq_once_per_bar_close',code)
        self.assertIn('view.lastAlertId := view.owner',code)
        for token in ['signal_close_utc_ms=','entry_ref=','SL=','TP1=','TP2=','REAL_POSITION_UNKNOWN','No order sent']:self.assertIn(token,self.ui)
        self.assertNotIn('alertcondition(',code);self.assertNotIn('webhook',code)

    def test_dashboard_mask_and_no_money_or_performance(self):
        self.assertIn('displayClock >= TRADE_START and displayClock < TRADE_END',self.ui)
        self.assertIn('chart.left_visible_bar_time + STEP >= TRADE_START',self.ui)
        self.assertIn('chart.right_visible_bar_time + STEP < TRADE_END',self.ui)
        self.assertIn('table.delete(dashboard)',self.ui)
        self.assertIn('var table dashboard = na',self.ui)
        self.assertIn('REAL_POSITION_UNKNOWN',self.ui)
        for token in ('state.cash','state.settled','book.cash','book.settled','win rate','Profit Factor','expectancy','drawdown'):self.assertNotIn(token,self.ui)

    def test_pine_global_udt_local_declarations_unique(self):
        normalized=re.sub(r'(?m)^(\s*)(?:ResearchAuditRow|SignalView|ManualSignalView|table)(\s+\w+\s*=)',r'\1ResearchBook\2',self.source)
        self.assertEqual(declaration_scan(normalized)['duplicates'],[])

    def test_conservative_reserved_names_not_used_as_declarations(self):
        reserved={'catch','class','do','ellipse','in','is','polygon','range','return','struct','text','throw','try'}
        names={row[0] for row in declaration_scan(self.source)['declarations']}
        self.assertEqual(names & reserved,set())
        seeded=declaration_scan(self.source+'\nstring text = "unsafe"\n')
        self.assertIn('text',{row[0] for row in seeded['declarations']} & reserved)

    def test_no_forbidden_execution_api_or_price_recalculation_in_ui(self):
        code='\n'.join(l.split('//')[0] for l in self.source.splitlines())
        self.assertIsNone(re.search(r'\bstrategy\s*\.|\bstrategy\s*\(',code))
        self.assertNotIn('request.',self.ui)
        self.assertNotIn('syminfo.mintick', '\n'.join(l.split('//')[0] for l in self.ui.splitlines()))
        self.assertNotIn('input.float',self.ui)

    def test_guarded_runner_has_explicit_allowlist_and_no_discovery(self):
        runner=(ROOT/'tests/run_phase5c_checks.py').read_text()
        self.assertIn('sys.addaudithook(guard.audit)',runner);self.assertNotIn('discover(',runner)
        for module in ['tests.test_phase5b3_pine_remediation','tests.test_phase5b3_pine','tests.test_phase5b3_state','tests.test_phase5b3_integration','tests.test_phase5b2_filters','tests.test_phase5b1_c01','tests.test_phase5a_temporal']:self.assertIn(module,runner)
