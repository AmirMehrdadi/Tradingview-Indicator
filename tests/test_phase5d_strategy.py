"""New native-order source obligations only; inherited fixtures cover trading math."""
from pathlib import Path
import re,unittest
from tests.test_phase5b3_pine import declaration_scan
R=Path(__file__).resolve().parents[1]
class StrategySourceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.s=(R/'pine/BTC_Strategy.pine').read_text();cls.old=(R/'pine/Trading_Signals.pine').read_text()
 def test_gate_a_frozen_numeric_and_candidate_regions(self):
  for start,end in [('const int DATA_START','// Hypothetical Research state only'),('f_ticks(float','if active and window')]:
   newend='// Native observations only' if start.startswith('const') else end
   self.assertEqual(self.s[self.s.index(start):self.s.index(newend)],self.old[self.old.index(start):self.old.index(end)])
 def test_decision_predicates_only_native_cost_proxy_and_submission_seam_differ(self):
  a=self.s[self.s.index('if active and window'):self.s.index('                        if f_validRun')]
  b=self.old[self.old.index('if active and window'):self.old.index('                        bool queued')]
  a=a.replace('float parityDistance = PARITY_SLIPPAGE_TICKS * syminfo.mintick\n            float cost = FEE * ((close + parityDistance) + (sl + parityDistance)) + 2.0 * parityDistance','float cost = (close + sl) * (FEE + FRICTION)')
  self.assertEqual(a,b)
 def test_declaration_and_placeholder_gate(self):
  for x in ['initial_capital = 10000','commission_type = strategy.commission.percent','commission_value = 0.055','margin_long = 50','margin_short = 50','pyramiding = 0','calc_on_every_tick = false','calc_on_order_fills = false','process_orders_on_close = false','use_bar_magnifier = false','backtest_fill_limits_assumption = 0','slippage = 0','const bool PARITY_VALIDATED = false','input.bool(false,']:
   self.assertIn(x,self.s)
 def test_entry_two_brackets_explicit_and_independent(self):
  self.assertEqual(self.s.count('strategy.entry('),1);self.assertEqual(self.s.count('strategy.exit('),2)
  self.assertIn('qty = totalSteps / 1000.0',self.s)
  for k,steps in [(1,'firstSteps'),(2,'secondSteps')]:
   line=next(l for l in self.s.splitlines() if 'strategy.exit(native.leg'+str(k) in l)
   for token in ['from_entry = native.entryId','qty = '+steps+' / 1000.0','limit = native.target'+str(k),'stop = native.stop','oca_name = native.oca'+str(k)]:self.assertIn(token,line)
  self.assertNotIn('qty_percent',self.s);self.assertNotIn('oca_type',self.s)
 def test_submission_not_waiting_for_position_and_not_reconstructed(self):
  submission=self.s[self.s.index('                        if f_validRun'):]
  self.assertNotIn('strategy.position_size',submission);self.assertNotIn('strategy.position_avg_price',submission)
  self.assertLess(submission.index('strategy.entry('),submission.index('strategy.exit('))
  self.assertIn('if active and window and count >= 200',self.s)
 def test_pending_partial_flat_and_native_ownership(self):
  for token in ['native.phase != 0','this.exited + this.remaining != this.total','this.remaining > this.total','strategy.opentrades.entry_id(0) != this.entryId','this.partialTP1 := strategy.closedtrades.exit_comment(n) == "TP1"','this.observedEntry and strategy.position_size == 0 and strategy.opentrades == 0','strategy.cancel(this.leg1)','strategy.cancel(this.leg2)','this.missingFillUnknown := true']:
   self.assertIn(token,self.s)
  self.assertNotIn('ENTRY_REJECTED_MARGIN',self.s)
 def test_daily_settled_and_boundary_protection(self):
  self.assertEqual(self.s.count('this.settled :='),1)
  self.assertIn('this.settled := 10000.0 + strategy.netprofit',self.s)
  self.assertLess(self.s.index('this.settled :='),self.s.index('this.resetDay(time_close)'))
  block=self.s[self.s.index('if time_close >= TRADE_END'):self.s.index('this.resetDay(time_close)')]
  self.assertIn('this.crossedWindow := true',block)
  self.assertNotIn('cancel(this.leg',block);self.assertIsNone(re.search(r'strategy\.close(?:_all)?\s*\(',self.s))
 def test_native_metadata_and_no_research_fill_substitution(self):
  for field in ['entry_time','entry_price','exit_price','commission','exit_time','exit_bar_index','exit_id','exit_comment']:
   self.assertIn('strategy.closedtrades.'+field+'(',self.s)
  self.assertNotIn('advanceResearchBar',self.s);self.assertNotIn('stopResearchLegs',self.s)
  self.assertIn('array.push(used, pullbackId)',self.s)
 def test_namespace_and_no_forbidden_sideeffects(self):
  self.assertIn('runId + "/Parity/" + candidate + "/November2026/" + str.tostring(time) + "/" + str.tostring(side)',self.s)
  for suffix in ['L1','L2','OCA1','OCA2']:self.assertIn('native.entryId + "/'+suffix+'"',self.s)
  self.assertNotIn('alert(',self.s);self.assertNotIn('strategy.order(',self.s)
  normalized=re.sub(r'(?m)^(\s*)(?:NativeBook|NativeExit)(\s+\w+\s*=)',r'\1ResearchBook\2',self.s)
  self.assertEqual(declaration_scan(normalized)['duplicates'],[])
