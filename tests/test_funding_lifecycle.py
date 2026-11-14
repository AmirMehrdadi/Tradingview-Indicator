"""Independent mathematical SYNTHETIC_FIXTURE_ONLY expectations, never research."""
import hashlib
import json
import socket
import unittest
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

from research.access import AccessDenied
from research.funding.policy import Period, EXECUTION_STEP as STEP, MINUTE
from research.funding_lifecycle.accounting import (
    ALTERNATE, BASE, PROXY, SCENARIOS, SYNTHETIC, Boundary, Entry, Exit, FixtureCalendar,
    FundingLifecycle, LifecycleError, MarkMinute, Owner, Scenario, Settlement,
    btc, exact_add, funding_cashflow,
)

D = Decimal
DAY = 86400000


class FundingLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.period = Period.annual(2023)
        self.owner = Owner("fixture:unit", "C01", "fixture:annual2023", self.period)
        self.t = self.period.start+8*3600000

    def engine(self, times=None, scenario=Scenario(), owner=None):
        return FundingLifecycle(FixtureCalendar(owner or self.owner, (self.t,) if times is None else tuple(times)), scenario)

    def entry(self, t=None, steps=1000, direction="Long", **changes):
        t = self.t-STEP if t is None else t
        return replace(Entry(self.owner, "entry:A", "fill:entryA", t, t, direction, steps), **changes)

    def exit(self, t=None, steps=400, phase="PRIOR_BAR", **changes):
        t = self.t if t is None else t
        return replace(Exit(self.owner, "entry:A", "fill:exitA", t, phase, t-STEP if phase == "PRIOR_BAR" else t, steps), **changes)

    def minute(self, t=None, **changes):
        t = self.t if t is None else t
        return replace(MarkMinute(self.owner, t-MINUTE, t, D("100"), D("110"), D("98"), D("104")), **changes)

    def settlement(self, t=None, **changes):
        t = self.t if t is None else t
        return replace(Settlement(self.owner, "settlement:"+str(t), t, D("0.01"), (self.minute(t),)), **changes)

    def boundary(self, t=None, **changes):
        return replace(Boundary(self.owner, self.t if t is None else t), **changes)

    def opened(self, scenario=Scenario(), times=None, **entry_changes):
        e = self.engine(times, scenario)
        ent = self.entry(**entry_changes)
        e.advance(self.boundary(ent.time_ms, entry=ent))
        return e

    def fund(self, e, evidence=None, **changes):
        e.advance(self.boundary(settlements=(self.settlement() if evidence is None else evidence,), **changes))
        return e.funding[-1]

    def assert_atomic_error(self, e, code, boundary):
        before = e.serialized()
        with self.assertRaisesRegex(LifecycleError, code):
            e.advance(boundary)
        self.assertEqual(e.serialized(), before)

    def test_long_positive_rate_pays(self):
        e = self.opened()
        self.assertEqual(self.fund(e).cashflow, D("-1.04"))

    def test_short_positive_rate_receives(self):
        e = self.opened(direction="Short")
        self.assertEqual(self.fund(e).cashflow, D("1.04"))

    def test_negative_rate_reverses_both_directions(self):
        for direction, expected in (("Long", "1.04"), ("Short", "-1.04")):
            e = self.opened(direction=direction)
            self.assertEqual(self.fund(e, self.settlement(rate=D("-0.01"))).cashflow, D(expected))

    def test_explicit_zero_rate_is_not_missing_rate(self):
        e = self.opened()
        record = self.fund(e, self.settlement(rate=D(0)))
        self.assertEqual(record.cashflow, D(0))
        self.assertEqual(record.rate, D(0))
        e = self.opened()
        self.assert_atomic_error(e, "MISSING_OR_INVALID_FUNDING_RATE", self.boundary(settlements=(self.settlement(rate=None),)))

    def test_exact_multiplication_has_independent_fraction_expectation(self):
        e = self.opened(steps=1234)
        mark = self.minute(open=D("43000"), high=D("45000"), low=D("40000"), close=D("43210.987654321"))
        record = self.fund(e, self.settlement(rate=D("0.00012345"), marks=(mark,)))
        expected = -Fraction("1.234")*Fraction("43210.987654321")*Fraction("0.00012345")
        self.assertEqual(Fraction(record.cashflow), expected)

    def test_low_global_decimal_precision_cannot_round_accounting(self):
        with localcontext() as context:
            context.prec = 2
            actual = funding_cashflow(1234, "Long", D("43210.987654321"), D("0.00012345"))
            self.assertEqual(Fraction(actual), -Fraction("1.234")*Fraction("43210.987654321")*Fraction("0.00012345"))
            self.assertEqual(exact_add(D("1234567890.000000001"), D("0.000000002")), D("1234567890.000000003"))
            self.assertEqual(btc(1234567), D("1234.567"))

    def test_prior_partial_uses_remaining_quantity(self):
        e = self.opened()
        record = self.fund(e, prior_exits=(self.exit(),))
        self.assertEqual((record.quantity_steps, record.cashflow), (600, D("-0.624")))
        self.assertEqual((e.position.remaining_steps, e.position.exited_steps), (600, 400))

    def test_prior_full_exit_receives_no_later_funding(self):
        e = self.opened()
        record = self.fund(e, prior_exits=(self.exit(steps=1000),))
        self.assertIsNone(record.entry_id)
        self.assertEqual(record.cashflow, D(0))
        self.assertFalse(record.funding_tie)
        self.assertEqual(e.completed["entry:A"].funding_events, [])

    def test_prior_bar_end_timestamp_is_not_an_open_tie(self):
        e = self.opened()
        record = self.fund(e, prior_exits=(self.exit(economic_phase="INTRABAR_TIME_UNKNOWN"),))
        self.assertFalse(record.funding_tie)
        event = next(v for v in e.events if v["name"] == "EXIT")
        self.assertEqual((event["reported_ms"], event["phase"], event["bar_open_ms"]), (self.t, "PRIOR_BAR", self.t-STEP))

    def test_open_partial_base_and_alternate_differ_only_in_funding_exposure(self):
        for precedence, quantity, expected in ((BASE, 1000, "-1.04"), (ALTERNATE, 600, "-0.624")):
            e = self.opened(Scenario("close", precedence))
            record = self.fund(e, open_exits=(self.exit(phase="OPEN"),))
            self.assertTrue(record.funding_tie)
            self.assertEqual((record.quantity_steps, record.cashflow), (quantity, D(expected)))
            self.assertEqual(e.position.remaining_steps, 600)

    def test_open_full_alternate_is_structural_zero_not_zero_rate(self):
        for precedence, expected in ((BASE, "-1.04"), (ALTERNATE, "0")):
            e = self.opened(Scenario("close", precedence))
            record = self.fund(e, open_exits=(self.exit(steps=1000, phase="OPEN"),))
            self.assertTrue(record.funding_tie)
            self.assertEqual(record.cashflow, D(expected))
            self.assertEqual(record.rate, D("0.01"))
            self.assertEqual(e.completed["entry:A"].funding_total, D(expected))

    def test_zero_alternate_exposure_needs_no_fabricated_rate_or_mark(self):
        e = self.opened(Scenario("close", ALTERNATE))
        record = self.fund(e, self.settlement(rate=None, marks=()), open_exits=(self.exit(steps=1000, phase="OPEN"),))
        self.assertEqual(record.cashflow, D(0))
        self.assertIsNone(record.rate)
        self.assertIsNone(record.selected_mark)
        self.assertEqual(record.classification, "EXEMPT_STRUCTURALLY_ZERO_OLD_EXPOSURE")

    def test_new_open_entry_is_exempt_from_same_timestamp_funding(self):
        e = self.engine()
        e.advance(self.boundary(settlements=(self.settlement(),), entry=self.entry(self.t)))
        self.assertIsNone(e.funding[-1].entry_id)
        self.assertEqual(e.position.funding_total, D(0))
        self.assertEqual(e.position.funding_events, [])

    def test_new_entry_and_immediate_open_exit_are_retained_without_funding(self):
        e = self.engine()
        e.advance(self.boundary(settlements=(self.settlement(),), entry=self.entry(self.t), open_exits=(self.exit(steps=1000, phase="OPEN"),)))
        self.assertIsNone(e.position)
        self.assertEqual(e.completed["entry:A"].funding_events, [])
        self.assertEqual([v["name"] for v in e.events if v["phase"] == "OPEN"], ["ENTRY", "EXIT"])

    def test_same_bar_intrabar_exit_is_prior_bar_at_next_boundary(self):
        later = self.t+STEP
        e = self.engine((self.t, later))
        e.advance(self.boundary(entry=self.entry(self.t)))
        e.advance(self.boundary(later, prior_exits=(self.exit(later, steps=1000, economic_phase="INTRABAR_TIME_UNKNOWN"),)))
        self.assertEqual([v.cashflow for v in e.funding], [D(0), D(0)])
        self.assertEqual(e.completed["entry:A"].funding_events, [])

    def test_multiple_settlements_accumulate_independently_expected_total(self):
        later = self.t+8*3600000
        e = self.opened(times=(self.t, later))
        self.fund(e)
        e.advance(self.boundary(later, settlements=(self.settlement(later, rate=D("-0.02"), marks=(self.minute(later, close=D("99")),)),)))
        self.assertEqual(e.position.funding_total, D("0.94"))  # -1.04 + 1.98, independent literals.
        self.assertEqual(len(e.position.funding_events), 2)

    def test_duplicate_boundary_replay_fails_atomically(self):
        e = self.opened()
        b = self.boundary(settlements=(self.settlement(),))
        e.advance(b)
        self.assert_atomic_error(e, "DUPLICATE_OR_OUT_OF_ORDER_BOUNDARY", b)

    def test_settlement_event_id_cannot_be_reused_at_later_time(self):
        later = self.t+STEP
        e = self.opened(times=(self.t, later))
        self.fund(e)
        self.assert_atomic_error(e, "DUPLICATE_SETTLEMENT_EVENT_ID", self.boundary(later, settlements=(self.settlement(later, event_id=self.settlement().event_id),)))

    def test_duplicate_and_conflicting_settlements_fail(self):
        for other in (self.settlement(), self.settlement(rate=D("-0.01"))):
            e = self.opened()
            self.assert_atomic_error(e, "DUPLICATE_OR_CONFLICTING_SETTLEMENT", self.boundary(settlements=(self.settlement(), other)))

    def test_duplicate_and_conflicting_marks_fail(self):
        for other in (self.minute(), self.minute(close=D("105"))):
            e = self.opened()
            self.assert_atomic_error(e, "DUPLICATE_OR_CONFLICTING_MARK", self.boundary(settlements=(self.settlement(marks=(self.minute(), other)),)))

    def test_duplicate_exit_fill_and_overexit_and_orphan_fail(self):
        for fills, code in (((self.exit(), self.exit()), "DUPLICATE_FILL_ID"), ((self.exit(steps=1001),), "INVALID_OR_EXCESS_EXIT_QUANTITY"), ((self.exit(entry_id="entry:other"),), "ORPHANED_EXIT")):
            e = self.opened()
            self.assert_atomic_error(e, code, self.boundary(prior_exits=fills))

    def test_exit_cannot_reuse_entry_fill_id(self):
        e = self.opened()
        self.assert_atomic_error(e, "DUPLICATE_FILL_ID", self.boundary(prior_exits=(self.exit(fill_id="fill:entryA"),)))

    def test_entry_id_cannot_be_reused_after_close(self):
        e = self.opened(times=())
        e.advance(self.boundary(prior_exits=(self.exit(steps=1000),)))
        self.assert_atomic_error(e, "DUPLICATE_ENTRY_OR_FILL_ID", self.boundary(self.t+STEP, entry=self.entry(self.t+STEP, fill_id="fill:new")))

    def test_all_six_scenarios_have_independent_literal_expectations(self):
        expected = {("close", BASE):"-1.04", ("close", ALTERNATE):"-0.624", ("low", BASE):"-0.98", ("low", ALTERNATE):"-0.588", ("high", BASE):"-1.10", ("high", ALTERNATE):"-0.660"}
        inputs = self.boundary(settlements=(self.settlement(),), open_exits=(self.exit(phase="OPEN"),))
        identities, shared = set(), []
        for scenario in SCENARIOS:
            e = self.opened(scenario)
            e.advance(inputs)
            r = e.funding[-1]
            self.assertEqual(r.cashflow, D(expected[scenario.mark_field, scenario.precedence]))
            self.assertEqual(r.selected_mark_field, scenario.mark_field)
            self.assertEqual(r.proxy_classification, PROXY)
            self.assertFalse(r.exact_tick or r.guaranteed_settlement_bounds)
            identities.add(r.scenario.identity)
            shared.append(e.shared)
        self.assertEqual(len(identities), 6)
        self.assertTrue(all(s == shared[0] for s in shared))

    def test_wrong_mark_minute_and_incomplete_candle_fail(self):
        for mark, code in ((self.minute(start_ms=self.t-2*MINUTE),"INVALID_MARK_MINUTE_LINKAGE"),(self.minute(end_ms=self.t+MINUTE),"INVALID_MARK_MINUTE_LINKAGE"),(self.minute(completed=False),"INCOMPLETE_MARK_MINUTE")):
            e = self.opened()
            self.assert_atomic_error(e, code, self.boundary(settlements=(self.settlement(marks=(mark,)),)))

    def test_invalid_ohlc_zero_negative_nonfinite_or_missing_price_fails(self):
        for changes in ({"high":D("99")},{"low":D("105")},{"close":D(0)},{"open":D(-1)},{"high":D("Infinity")},{"low":D("NaN")},{"close":None},{"close":104.0}):
            e = self.opened()
            with self.subTest(changes=tuple(changes)):
                self.assert_atomic_error(e, "MARK", self.boundary(settlements=(self.settlement(marks=(self.minute(**changes),)),)))

    def test_unverified_mark_substitutes_and_exact_tick_claims_fail(self):
        for changes in ({"classification":"TRADE_15M_CLOSE"},{"exact_tick":True},{"guaranteed_settlement_bounds":True}):
            e = self.opened()
            self.assert_atomic_error(e, "UNVERIFIED_MARK_SUBSTITUTE", self.boundary(settlements=(self.settlement(marks=(self.minute(**changes),)),)))

    def test_missing_or_nonfinite_rate_fails_with_exposure(self):
        for value in (None, D("NaN"), D("Infinity"), .01, "0.01"):
            e = self.opened()
            self.assert_atomic_error(e, "MISSING_OR_INVALID_FUNDING_RATE", self.boundary(settlements=(self.settlement(rate=value),)))

    def test_missing_required_mark_and_settlement_fail(self):
        e = self.opened()
        self.assert_atomic_error(e, "MISSING_REQUIRED_MARK", self.boundary(settlements=(self.settlement(marks=()),)))
        self.assert_atomic_error(e, "MISSING_REQUIRED_SETTLEMENT", self.boundary())

    def test_incomplete_duplicate_or_implicit_fixture_calendar_fails(self):
        for calendar in (FixtureCalendar(self.owner,(self.t,),False), FixtureCalendar(self.owner,(self.t,self.t)), FixtureCalendar(self.owner,[self.t])):
            with self.assertRaises(LifecycleError):
                FundingLifecycle(calendar)

    def test_regular_cadence_does_not_upgrade_historical_calendar_status(self):
        e = self.engine((self.t,self.t+8*3600000))
        data = json.loads(e.serialized())
        self.assertEqual(data["historical_funding_data"], "PARTIAL_DATA")
        self.assertEqual(data["historical_calendar_completeness"], "UNVERIFIED")
        self.assertEqual(data["official_research_result"], "NOT_EVALUABLE")

    def test_off_15m_settlement_with_exposure_fails_without_inferred_order(self):
        t = self.t+MINUTE
        e = self.opened(times=(t,))
        self.assert_atomic_error(e, "FUNDING_ALIGNMENT_UNRESOLVED", self.boundary(t, settlements=(self.settlement(t),)))

    def test_expected_settlement_cannot_be_silently_skipped(self):
        e = self.opened()
        self.assert_atomic_error(e, "MISSING_OR_SKIPPED_EXPECTED_SETTLEMENT", self.boundary(self.t+STEP))

    def test_unexpected_or_wrong_time_settlement_fails(self):
        e = self.opened(times=())
        self.assert_atomic_error(e, "UNEXPECTED_SETTLEMENT", self.boundary(settlements=(self.settlement(),)))
        e = self.opened()
        self.assert_atomic_error(e, "SETTLEMENT_TIMESTAMP_MISMATCH", self.boundary(settlements=(self.settlement(self.t+STEP),)))

    def test_wrong_phase_or_reported_bar_ownership_fails(self):
        for fill in (self.exit(phase="OPEN"),self.exit(bar_open_ms=self.t),self.exit(time_ms=self.t-STEP)):
            e = self.opened()
            self.assert_atomic_error(e, "PHASE|BAR_OWNERSHIP", self.boundary(prior_exits=(fill,)))

    def test_invalid_direction_entry_quantity_and_cash_are_rejected(self):
        for changes in ({"direction":"BUY"},{"total_steps":0},{"total_steps":-1},{"total_steps":True},{"total_steps":1.0},{"cash_after":D("NaN")},{"entry_id":""}):
            e = self.engine(())
            self.assert_atomic_error(e,"INVALID", self.boundary(self.t-STEP,entry=self.entry(**changes)))

    def test_zero_negative_boolean_or_fractional_exit_steps_fail(self):
        for value in (0,-1,True,.5):
            e = self.opened()
            self.assert_atomic_error(e,"INVALID_OR_EXCESS_EXIT_QUANTITY",self.boundary(prior_exits=(self.exit(steps=value),)))

    def test_other_candidate_or_partition_ownership_is_rejected(self):
        for owner in (replace(self.owner,candidate="C02"),replace(self.owner,partition_id="fixture:other")):
            e = self.opened()
            self.assert_atomic_error(e,"OWNERSHIP_MISMATCH",self.boundary(settlements=(self.settlement(owner=owner),)))
            self.assert_atomic_error(e,"OWNERSHIP_MISMATCH",self.boundary(prior_exits=(self.exit(owner=owner),)))

    def test_mark_provenance_mismatch_fails(self):
        e = self.opened()
        mark=self.minute(owner=replace(self.owner,fixture_id="fixture:other"))
        self.assert_atomic_error(e,"OWNERSHIP_MISMATCH",self.boundary(settlements=(self.settlement(marks=(mark,)),)))

    def test_normal_midnight_prior_closure_then_reset_then_funding(self):
        t=self.period.start+DAY
        e=self.engine((t,))
        e.advance(self.boundary(t-STEP,entry=self.entry(t-STEP)))
        e.advance(self.boundary(t,prior_exits=(self.exit(t,steps=1000,cash_after=D("9899")),)))
        self.assertEqual(e.shared.day_start,D("9899"))
        self.assertFalse(e.shared.daily_stop)
        self.assertEqual(e.funding[-1].quantity_steps,0)
        events=[v for v in e.events if v['reported_ms']==t]
        self.assertLess(next(i for i,v in enumerate(events) if v['name']=='EXIT'),next(i for i,v in enumerate(events) if v['name']=='UTC_DAY_RESET'))
        exit_event=next(v for v in events if v['name']=='EXIT')
        self.assertEqual(exit_event['economic_day'],(t-1)//DAY)

    def test_partial_midnight_uses_last_fully_settled_snapshot(self):
        t=self.period.start+DAY
        e=self.engine((t,))
        e.advance(self.boundary(t-STEP,entry=self.entry(t-STEP)))
        e.advance(self.boundary(t,prior_exits=(self.exit(t,cash_after=D("9950")),),settlements=(self.settlement(t),)))
        self.assertEqual((e.shared.cash,e.shared.settled_flat,e.shared.day_start),(D("9950"),D("10000"),D("10000")))
        self.assertEqual(e.funding[-1].quantity_steps,600)

    def test_midnight_open_exit_is_new_day_in_both_precedence_scenarios(self):
        t=self.period.start+DAY
        states=[]
        for p in (BASE,ALTERNATE):
            e=self.engine((t,),Scenario('close',p))
            e.advance(self.boundary(t-STEP,entry=self.entry(t-STEP)))
            e.advance(self.boundary(t,settlements=(self.settlement(t),),open_exits=(self.exit(t,1000,'OPEN',cash_after=D('9899')),)))
            self.assertEqual(e.shared.day_start,D('10000'))
            self.assertTrue(e.shared.daily_stop)
            self.assertEqual(next(v for v in e.events if v['name']=='EXIT')['economic_day'],t//DAY)
            states.append(e.shared)
        self.assertEqual(states[0],states[1])

    def test_daily_stop_is_only_from_full_prefunding_execution_settlement(self):
        e=self.opened()
        self.fund(e,self.settlement(rate=D('10')))
        self.assertEqual((e.shared.cash,e.shared.sizing_balance,e.shared.day_start),(D('10000'),D('10000'),D('10000')))
        self.assertTrue(e.shared.entry_eligible)
        later=self.t+STEP
        e.advance(self.boundary(later,prior_exits=(self.exit(later,1000,cash_after=D('9899')),)))
        self.assertTrue(e.shared.daily_stop)
        self.assert_atomic_error(e,'SHARED_DAILY_STOP_BLOCKS_ENTRY',self.boundary(later+STEP,entry=self.entry(later+STEP,entry_id='entry:B',fill_id='fill:B')))

    def test_alternate_open_exit_does_not_free_signal_eligibility_early(self):
        for p in (BASE,ALTERNATE):
            e=self.opened(Scenario('close',p))
            b=self.boundary(settlements=(self.settlement(),),open_exits=(self.exit(steps=1000,phase='OPEN'),),entry=self.entry(self.t,entry_id='entry:B',fill_id='fill:B'))
            self.assert_atomic_error(e,'POSITION_BUSY_AT_SIGNAL',b)

    def test_partition_end_censors_after_prior_exit_without_boundary_evidence_use(self):
        t=self.period.end-2*STEP
        e=self.engine((t,))
        e.advance(self.boundary(t-STEP,entry=self.entry(t-STEP)))
        e.advance(self.boundary(t,settlements=(self.settlement(t),)))
        e.advance(self.boundary(self.period.end,prior_exits=(self.exit(self.period.end,cash_after=D('9950')),),settlements=object(),entry=object(),open_exits=object()))
        self.assertTrue(e.ended)
        self.assertIsNone(e.position)
        self.assertEqual(e.completed,{})
        censored=e.censored['entry:A']
        self.assertEqual((censored.state,censored.remaining_steps,censored.funding_total),('CENSORED',600,D('-1.04')))
        self.assertEqual(len(e.funding),1)

    def test_partition_end_full_prior_exit_is_completed_not_censored(self):
        t=self.period.end-STEP
        e=self.engine(())
        e.advance(self.boundary(t,entry=self.entry(t)))
        e.advance(self.boundary(self.period.end,prior_exits=(self.exit(self.period.end,1000),)))
        self.assertEqual(e.censored,{})
        self.assertEqual(e.completed['entry:A'].state,'COMPLETED')

    def test_independent_next_annual_partition_resets_all_state_and_ids(self):
        owner=replace(self.owner,period=Period.annual(2024),partition_id='fixture:annual2024')
        e=self.engine((),owner=owner)
        self.assertEqual((e.shared.cash,e.shared.settled_flat,e.shared.day_start),(D('10000'),)*3)
        self.assertIsNone(e.position)
        self.assertIsNone(e.pending)
        self.assertEqual((e.funding,e.events,e.completed,e.censored),([],[],{},{}))
        t=owner.period.start
        e.advance(Boundary(owner,t,entry=replace(self.entry(t),owner=owner)))
        self.assertEqual(e.position.entry.entry_id,'entry:A')

    def test_initial_2023_mark_omission_is_strictly_zero_exposure_exemption(self):
        t=self.period.start
        e=self.engine((t,))
        e.advance(self.boundary(t,entry=self.entry(t)))
        record=e.funding[0]
        self.assertEqual((record.quantity_steps,record.cashflow),(0,D(0)))
        self.assertIsNone(record.rate)
        self.assertIsNone(record.selected_mark)
        self.assertEqual(e.position.funding_events,[])
        self.assertEqual(json.loads(e.serialized())['historical_funding_data'],'PARTIAL_DATA')

    def test_censored_attribution_cannot_leak_to_another_completed_entry(self):
        e=self.opened()
        self.fund(e)
        e.advance(self.boundary(self.period.end))
        self.assertEqual(e.completed,{})
        self.assertEqual(e.censored['entry:A'].funding_total,D('-1.04'))
        with self.assertRaisesRegex(LifecycleError,'PARTITION_ALREADY_ENDED'):
            e.advance(self.boundary(self.period.end,entry=self.entry()))

    def test_conservation_invariants_detect_manual_corruption(self):
        e=self.opened()
        e.position.remaining_steps+=1
        with self.assertRaisesRegex(LifecycleError,'QUANTITY_CONSERVATION_FAILED'):e._invariants()
        e=self.opened();self.fund(e)
        e.position.funding_total=D('999')
        with self.assertRaisesRegex(LifecycleError,'FUNDING_ATTRIBUTION_CONSERVATION_FAILED'):e._invariants()
        e=self.opened();self.fund(e)
        e.funding.append(e.funding[0])
        with self.assertRaisesRegex(LifecycleError,'DUPLICATE_FUNDING_RECORD'):e._invariants()

    def test_failed_boundary_can_be_retried_once_without_duplicate_attribution(self):
        e=self.opened()
        b=self.boundary(prior_exits=(self.exit(),),settlements=(self.settlement(rate=None),))
        self.assert_atomic_error(e,'MISSING_OR_INVALID_FUNDING_RATE',b)
        self.fund(e,prior_exits=(self.exit(),))
        self.assertEqual(e.position.funding_total,D('-0.624'))
        self.assertEqual(len(e.position.funding_events),1)

    def test_entry_after_settlement_receives_no_earlier_attribution(self):
        e=self.engine()
        e.advance(self.boundary())
        e.advance(self.boundary(self.t+STEP,entry=self.entry(self.t+STEP)))
        self.assertIsNone(e.funding[0].entry_id)
        self.assertEqual(e.position.funding_events,[])

    def test_t16_prior_full_exit_then_new_open_entry_and_exit_no_double_counting(self):
        for scenario in SCENARIOS:
            e=self.opened(scenario)
            new=self.entry(self.t,entry_id='entry:B',fill_id='fill:entryB')
            new_exit=self.exit(self.t,1000,'OPEN',entry_id='entry:B',fill_id='fill:exitB')
            e.advance(self.boundary(prior_exits=(self.exit(steps=1000),),settlements=(self.settlement(),),entry=new,open_exits=(new_exit,)))
            self.assertEqual(set(e.completed),{'entry:A','entry:B'})
            self.assertTrue(all(p.funding_events==[] for p in e.completed.values()))
            self.assertEqual(len(e.funding),1)
            self.assertEqual(e.funding[0].cashflow,D(0))

    def test_deterministic_replay_all_scenarios_serializes_identically(self):
        hashes = fixture_replay_hashes()
        self.assertEqual(len({row['sha256'] for row in hashes.values()}), 6)
        self.assertTrue(all(row['byte_equal'] and row['replays'] == 2 for row in hashes.values()))

    def test_wrong_or_historical_provenance_is_never_accepted(self):
        for owner in (replace(self.owner,provenance='BYBIT_HISTORICAL'),replace(self.owner,fixture_id='historical:2023')):
            with self.assertRaises(AccessDenied):self.engine(owner=owner)

    def test_future_period_boundary_and_entry_are_rejected(self):
        e=self.engine(())
        self.assert_atomic_error(e,'FUTURE_OR_OUT_OF_PARTITION_EVENT',self.boundary(self.period.end+STEP,entry=object()))
        self.assert_atomic_error(e,'ENTRY_PHASE_OR_SIGNAL_OWNERSHIP_INVALID',self.boundary(self.t-STEP,entry=self.entry(self.period.end)))
        for year in (2025,2026):
            with self.assertRaises(AccessDenied):Period.annual(year)

    def test_no_file_or_network_dependency_even_when_access_is_denied(self):
        e=self.opened()
        with patch.object(Path,'read_bytes',side_effect=AssertionError('NO_DATA_READ')) as reader, patch('builtins.open',side_effect=AssertionError('NO_FILE_OPEN')) as opened, patch.object(socket,'create_connection',side_effect=AssertionError('NO_NETWORK')) as connect:
            self.fund(e)
            e.advance(self.boundary(self.period.end))
            e.serialized()
            with self.assertRaises(AccessDenied):FundingLifecycle(Path('data/funding/forbidden'))
            with self.assertRaises(AccessDenied):e.advance(Path('data/stage0b_private/forbidden'))
            reader.assert_not_called();opened.assert_not_called();connect.assert_not_called()

    def test_unregistered_scenario_fails(self):
        for scenario in (Scenario('open',BASE),Scenario('close','UNKNOWN')):
            with self.assertRaisesRegex(LifecycleError,'UNREGISTERED_SCENARIO'):self.engine(scenario=scenario)

    def test_compound_prior_and_open_partial_exits_conserve_exposure(self):
        for precedence, expected in ((BASE, D('-0.624')), (ALTERNATE, D('-0.312'))):
            e = self.opened(Scenario('close', precedence))
            self.fund(e, prior_exits=(self.exit(),), open_exits=(self.exit(steps=300, phase='OPEN', fill_id='fill:second'),))
            self.assertEqual(e.funding[-1].cashflow, expected)
            self.assertEqual((e.position.remaining_steps, e.position.exited_steps), (300, 700))

    def test_initial_mark_exemption_cannot_authorize_a_prior_entry_or_fake_mark(self):
        t = self.period.start
        e = self.engine((t,))
        self.assert_atomic_error(e, 'FUTURE_OR_OUT_OF_PARTITION_EVENT', self.boundary(t-STEP, entry=self.entry(t-STEP)))
        before = e.serialized()
        with self.assertRaises(AccessDenied):
            e.advance(self.boundary(t, settlements=(self.settlement(t),)))
        self.assertEqual(e.serialized(), before)

    def test_malformed_owner_and_noninteger_fill_timestamp_fail_deterministically(self):
        for candidate in ([], None, 'C13'):
            with self.assertRaisesRegex(LifecycleError, 'INVALID_CANDIDATE_OWNER'):
                self.engine(owner=replace(self.owner, candidate=candidate))
        e = self.opened()
        self.assert_atomic_error(e, 'OUT_OF_ORDER_FILL_PHASE', self.boundary(prior_exits=(self.exit(time_ms=float(self.t)),)))

    def test_duplicate_and_orphaned_per_entry_attribution_are_detected(self):
        e = self.opened()
        self.fund(e)
        e.position.funding_events.append(e.funding[0])
        e.position.funding_total = D('-2.08')
        with self.assertRaisesRegex(LifecycleError, 'DUPLICATE_ENTRY_FUNDING_ATTRIBUTION'):
            e._invariants()
        e = self.opened()
        self.fund(e)
        e.position.funding_events.clear()
        e.position.funding_total = D(0)
        with self.assertRaisesRegex(LifecycleError, 'ORPHANED_FUNDING_ATTRIBUTION'):
            e._invariants()

    def test_calendar_is_part_of_serialized_fixture_provenance(self):
        a, b = self.engine(()), self.engine((self.t,))
        self.assertNotEqual(a.serialized(), b.serialized())
        self.assertEqual(json.loads(b.serialized())['fixture_calendar']['expected_settlements'], [self.t])

    def test_regression_guard_denies_data_and_network_before_io(self):
        from tests.run_phase4c_regression import OfflineGuard, ProhibitedAccess, ROOT
        guard = OfflineGuard()
        with self.assertRaisesRegex(ProhibitedAccess, 'REAL_REPOSITORY_DATA_ACCESS_DENIED'):
            guard.audit('open', (str(ROOT/'data/funding/never-opened.json'), 'r', 0))
        with self.assertRaisesRegex(ProhibitedAccess, 'NETWORK_ACCESS_DENIED'):
            guard.audit('socket.connect', (None, ('example.invalid', 443)))
        with self.assertRaisesRegex(ProhibitedAccess, 'NON_ALLOWLISTED_SUBPROCESS_DENIED'):
            guard.audit('subprocess.Popen', ('curl', ['curl', 'example.invalid'], None, None))
        self.assertEqual(len(guard.blocked), 3)


def fixture_replay_hashes():
    """Return hashes only, never a persisted synthetic accounting ledger."""
    fixture = FundingLifecycleTests()
    fixture.setUp()
    inputs = (fixture.boundary(fixture.t-STEP, entry=fixture.entry()),
              fixture.boundary(settlements=(fixture.settlement(),), open_exits=(fixture.exit(phase='OPEN'),)),
              fixture.boundary(fixture.period.end))
    output = {}
    for scenario in SCENARIOS:
        a, b = fixture.engine(scenario=scenario), fixture.engine(scenario=scenario)
        for boundary in inputs:
            a.advance(boundary)
            b.advance(boundary)
        fixture.assertEqual(a.serialized(), b.serialized())
        output[scenario.identity] = {'sha256': hashlib.sha256(a.serialized()).hexdigest(), 'replays': 2, 'byte_equal': True}
    return output


if __name__=='__main__':
    unittest.main()
