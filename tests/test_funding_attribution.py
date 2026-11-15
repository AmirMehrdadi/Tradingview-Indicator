"""Independent toy ledgers and literal Funding expectations; no real data access."""
from copy import deepcopy
from decimal import Decimal, localcontext
import json
from pathlib import Path
import unittest

from research.access import AccessDenied, iso
from research.funding.policy import Period, EXECUTION_STEP
from research.funding_lifecycle.accounting import Scenario, SCENARIOS, BASE, ALTERNATE, encode
from research.funding_attribution.accounting import (
    AttributionError, observations, prepare_path, attribute, PROXY,
)
from research.funding_attribution.guard import DevelopmentGuard, ROOT
from research.stage0b.output import no_financial_outputs
from tests.run_phase4c_regression import ProhibitedAccess


class Ledger:
    """Fixture builder records a predeclared path, never computes trading signals."""
    def __init__(self, year=2023, direction='Long'):
        self.period = Period.annual(year); self.year = year; self.direction = direction
        self.events = []; self.cash = self.settled = 10000.0; self.plan = None
        self.row('UTC_DAY_RESET', self.period.start, 'UTC_DAY_RESET', settled_balance=10000.0)

    def row(self, event_name, t, phase, **values):
        if phase in ('OPEN', 'PRIOR_BAR', 'SIGNAL_CLOSE'):
            opening = t if phase == 'OPEN' else t-EXECUTION_STEP
            values.update(bar_open_time=iso(opening), bar_end_time=iso(opening+EXECUTION_STEP))
        self.events.append(dict(event=event_name, time_utc=iso(t), phase=phase, candidate='C01', year=self.year, **values))

    def enter(self, t=None):
        t = self.period.start+EXECUTION_STEP if t is None else t
        identity = f'fixture:Research:C01:{self.year}:{t-EXECUTION_STEP}:{self.direction}'
        p = dict(entry_id=identity, direction=self.direction, signal_time=t, signal_bar_open=t-EXECUTION_STEP,
                 pullback=1, pivot_index=1, entry_ref=100.0, sl=90.0 if self.direction == 'Long' else 110.0,
                 tp1=110.0, tp2=120.0, total_steps=1000, tp1_steps=500, tp2_steps=500,
                 signal_balance=self.settled, risk_budget=0.0025*self.settled, planned_risk=10.0)
        self.plan=p
        self.row('SIGNAL_AND_BRACKETS_QUEUED',t,'SIGNAL_CLOSE',plan=p,
                 bracket_ids=[identity+':L1',identity+':L2'],oca_names=[identity+':OCA1',identity+':OCA2'])
        self.cash -= 0.05
        self.row('ENTRY_FILLED',t,'OPEN',entry_id=identity,quantity_steps=1000,entry_fee=0.05,fill=100.0,cash=self.cash)

    def exit(self, t, leg, phase='OPEN'):
        self.cash += 5.0-0.05
        self.row('EXIT_LEG',t,phase,entry_id=self.plan['entry_id'],bracket=leg,quantity_steps=500,
                 realized_pnl=5.0,exit_fee=0.05,fill=110.0,kind='TP',cash=self.cash)
        if leg==2:
            self.settled=self.cash
            self.row('POSITION_CLOSED',t,phase,entry_id=self.plan['entry_id'],settled_balance=self.settled)

    def payload(self, censored=False):
        if censored:
            remaining=[0 if any(e['event']=='EXIT_LEG' and e['entry_id']==self.plan['entry_id'] and e['bracket']==i for e in self.events) else 500 for i in (1,2)]
            self.row('CENSORED_AT_PARTITION_END',self.period.end,'PARTITION_END',open_plan=self.plan,
                     remaining_steps=remaining,cash=self.cash,settled_balance=self.settled)
        return dict(year=self.year,candidate='C01',ledger=self.events,funding_cashflows=None,
                    funding_status='MISSING_NOT_ZERO',final_cash=self.cash,settled_flat_balance=self.settled,
                    censored_open_position=censored)


def data(year=2023, rate='0.01'):
    p=Period.annual(year);rates=[];marks=[]
    for t in range(p.start,p.end,8*3600000):
        rates.append(dict(settlement_ms=t,funding_rate=rate))
        if year==2023 and t==p.start:continue
        marks.append(dict(settlement_ms=t,minute_open_ms=t-60000,minute_end_ms=t,
                          open='100',high='120',low='80',close='100',settlement_price_proxy='100',
                          low_sensitivity='80',high_sensitivity='120',proxy_classification=PROXY,
                          exact_tick=False,guaranteed_settlement_bounds=False))
    return rates,marks


class AttributionTests(unittest.TestCase):
    def closed(self, direction='Long', exit_phase='OPEN', exit_hour=9):
        l=Ledger(direction=direction);l.enter();t=l.period.start+exit_hour*3600000
        l.exit(t,1,exit_phase);l.exit(t,2,exit_phase);return l.payload()

    def run_path(self,payload=None,rate='0.01',scenario=Scenario()):
        payload=self.closed() if payload is None else payload
        p=prepare_path(payload,'fixture');o=observations(payload['year'],*data(payload['year'],rate))
        return attribute(p,o,scenario)

    def test_long_positive_and_negative_literal(self):
        self.assertEqual(self.run_path()['trades'][0]['attributed_funding'],Decimal('-1'))
        self.assertEqual(self.run_path(rate='-0.01')['trades'][0]['attributed_funding'],Decimal('1'))

    def test_short_positive_and_negative_literal(self):
        self.assertEqual(self.run_path(self.closed('Short'))['trades'][0]['attributed_funding'],Decimal('1'))
        self.assertEqual(self.run_path(self.closed('Short'),rate='-0.01')['trades'][0]['attributed_funding'],Decimal('-1'))

    def test_net_accounting_no_double_fees_or_friction(self):
        t=self.run_path()['trades'][0]
        self.assertEqual(t['net_before_funding'],Decimal('9.85'))
        self.assertEqual(t['net_after_funding'],Decimal('8.85'))
        self.assertEqual(t['planned_R_usdt'],Decimal('10'))
        self.assertEqual(t['trade_R_net'],Decimal('.885'))

    def test_tp1_before_settlement_reduces_quantity(self):
        l=Ledger();l.enter();l.exit(l.period.start+8*3600000,1,'PRIOR_BAR');l.exit(l.period.start+9*3600000,2)
        r=self.run_path(l.payload());self.assertEqual(r['records'][0]['quantity_steps'],500)
        self.assertEqual(r['trades'][0]['attributed_funding'],Decimal('-.5'))

    def test_tp1_after_funding_keeps_full_base_quantity(self):
        l=Ledger();l.enter();l.exit(l.period.start+8*3600000,1);l.exit(l.period.start+9*3600000,2)
        r=self.run_path(l.payload());self.assertEqual(r['records'][0]['quantity_steps'],1000)
        self.assertEqual(r['counts']['ties'],1)

    def test_all_six_independent_literal_expectations(self):
        l=Ledger();l.enter();l.exit(l.period.start+8*3600000,1);l.exit(l.period.start+9*3600000,2);p=l.payload()
        expected={('close',BASE):'-1',('low',BASE):'-.8',('high',BASE):'-1.2',
                  ('close',ALTERNATE):'-.5',('low',ALTERNATE):'-.4',('high',ALTERNATE):'-.6'}
        for s in SCENARIOS:
            with self.subTest(s=s.identity):self.assertEqual(self.run_path(p,scenario=s)['trades'][0]['attributed_funding'],Decimal(expected[s.mark_field,s.precedence]))

    def test_full_old_open_exit_alternate_zero(self):
        p=self.closed(exit_hour=8)
        self.assertEqual(self.run_path(p)['trades'][0]['attributed_funding'],Decimal('-1'))
        self.assertEqual(self.run_path(p,scenario=Scenario('close',ALTERNATE))['trades'][0]['attributed_funding'],Decimal('0'))

    def test_full_prior_exit_excludes_old_position(self):
        self.assertEqual(self.run_path(self.closed(exit_phase='PRIOR_BAR',exit_hour=8))['records'],[])

    def test_same_open_entry_exempt(self):
        l=Ledger();l.enter(l.period.start+8*3600000);l.exit(l.period.start+9*3600000,1);l.exit(l.period.start+9*3600000,2)
        self.assertEqual(self.run_path(l.payload())['records'],[])

    def test_initial_2023_missing_mark_only_narrow_exemption(self):
        r=self.run_path();self.assertEqual(r['counts']['initial_2023_mark_exemptions'],1)
        rates,marks=data();marks.pop(0)
        with self.assertRaisesRegex(AttributionError,'REQUIRED_MARK'):observations(2023,rates,marks)

    def test_zero_rate_distinct_from_missing(self):
        self.assertEqual(self.run_path(rate='0')['trades'][0]['attributed_funding'],Decimal('0'))
        rates,marks=data();rates.pop(1)
        with self.assertRaisesRegex(AttributionError,'MISSING'):observations(2023,rates,marks)

    def test_duplicate_and_conflicting_settlements_rejected(self):
        for value in ['0.01','-0.02']:
            rates,marks=data();rates.append(dict(rates[1],funding_rate=value))
            with self.assertRaisesRegex(AttributionError,'DUPLICATE'):observations(2023,rates,marks)

    def test_nonfinite_missing_and_invalid_rate(self):
        for value in [None,'NaN','Infinity','bad']:
            rates,marks=data();rates[1]['funding_rate']=value
            with self.assertRaises(AttributionError):observations(2023,rates,marks)

    def test_mark_geometry_alignment_duplicates_and_classification(self):
        for change in [{'close':'0'},{'minute_end_ms':0},{'exact_tick':True},{'guaranteed_settlement_bounds':True},{'low_sensitivity':'1'}]:
            rates,marks=data();marks[1].update(change)
            with self.assertRaises(AttributionError):observations(2023,rates,marks)
        rates,marks=data();marks.append(deepcopy(marks[0]))
        with self.assertRaises(AttributionError):observations(2023,rates,marks)

    def test_settlement_inside_execution_bar_is_unresolved(self):
        rates,marks=data();rates[1]['settlement_ms']+=60000
        with self.assertRaisesRegex(AttributionError,'ALIGNMENT_UNRESOLVED'):observations(2023,rates,marks)

    def test_multiple_settlements_same_entry(self):
        self.assertEqual(self.run_path(self.closed(exit_hour=17))['trades'][0]['attributed_funding'],Decimal('-2'))

    def test_completed_and_later_censored_entry_never_share_attribution(self):
        l=Ledger();l.enter();l.exit(l.period.start+9*3600000,1);l.exit(l.period.start+9*3600000,2)
        l.enter(l.period.end-9*3600000);r=self.run_path(l.payload(censored=True))
        self.assertEqual([t['state'] for t in r['trades']],['COMPLETED','CENSORED'])
        self.assertEqual([t['attributed_funding'] for t in r['trades']],[Decimal('-1'),Decimal('-1')])
        self.assertNotEqual(r['records'][0]['entry_id'],r['records'][-1]['entry_id'])

    def test_sizing_and_daily_gate_snapshot_changes_rejected(self):
        p=self.closed();p['ledger'][1]['plan']['signal_balance']=999.0
        with self.assertRaisesRegex(AttributionError,'SIZING'):prepare_path(p,'fixture')
        p=self.closed();p['ledger'].insert(1,dict(event='DAILY_STOP_ACTIVATED',time_utc=iso(Ledger().period.start),
                                                phase='UTC_DAY_RESET',candidate='C01',year=2023))
        with self.assertRaisesRegex(AttributionError,'DAILY_STOP'):prepare_path(p,'fixture')

    def test_no_exposure_is_structural_zero_not_filled_missing_data(self):
        p=Ledger().payload();r=self.run_path(p)
        self.assertEqual(r['records'],[]);self.assertEqual(r['trades'],[])
        self.assertEqual(r['counts']['flat_exemptions'],1095)

    def test_out_of_order_and_annual_end_open_rejected(self):
        p=self.closed();p['ledger'][2],p['ledger'][1]=p['ledger'][1],p['ledger'][2]
        with self.assertRaises(AttributionError):prepare_path(p,'fixture')
        p=self.closed();p['ledger'][-1]['time_utc']=iso(Period.annual(2023).end)
        with self.assertRaisesRegex(AttributionError,'ANNUAL_END'):prepare_path(p,'fixture')

    def test_censored_funding_retained_without_completed_r(self):
        l=Ledger();l.enter(l.period.end-9*3600000);p=l.payload(censored=True)
        r=self.run_path(p);t=r['trades'][0]
        self.assertEqual(t['state'],'CENSORED');self.assertIsNone(t['trade_R_net'])
        self.assertNotIn('net_after_funding',t);self.assertEqual(t['attributed_funding'],Decimal('-1'))

    def test_midnight_prior_exit_and_new_day_open(self):
        l=Ledger();l.enter();t=l.period.start+86400000;l.exit(t,1,'PRIOR_BAR')
        l.row('UTC_DAY_RESET',t,'UTC_DAY_RESET',settled_balance=10000.0);l.exit(t,2)
        r=self.run_path(l.payload());self.assertEqual(r['records'][-1]['quantity_steps'],500)
        self.assertEqual(r['trades'][0]['attributed_funding'],Decimal('-2.5'))

    def test_annual_end_prior_exit_not_charged_next_year(self):
        l=Ledger();l.enter(l.period.end-EXECUTION_STEP);l.exit(l.period.end,1,'PRIOR_BAR');l.exit(l.period.end,2,'PRIOR_BAR')
        self.assertEqual(self.run_path(l.payload())['records'],[])

    def test_leap_year_independent_reset(self):
        l=Ledger(2024);l.enter();l.exit(l.period.start+3600000,1);l.exit(l.period.start+3600000,2)
        r=self.run_path(l.payload());self.assertEqual(r['counts']['settlements'],1098);self.assertEqual(r['records'],[])

    def test_event_owner_ids_and_phases_rejected(self):
        for change in [{'candidate':'C02'},{'phase':'INTRABAR'},{'bar_open_time':iso(0)}]:
            p=self.closed();p['ledger'][3].update(change)
            with self.assertRaises(AttributionError):prepare_path(p,'fixture')

    def test_quantity_and_duplicate_exit_rejected(self):
        p=self.closed();p['ledger'][3]['quantity_steps']=501
        with self.assertRaisesRegex(AttributionError,'QUANTITY'):prepare_path(p,'fixture')
        p=self.closed();p['ledger'].insert(4,deepcopy(p['ledger'][3]))
        with self.assertRaises(AttributionError):prepare_path(p,'fixture')

    def test_planned_r_and_source_cash_changes_rejected(self):
        p=self.closed();p['ledger'][1]['plan']['planned_risk']=11.0
        with self.assertRaises(AttributionError):prepare_path(p,'fixture')
        p=self.closed();p['ledger'][2]['cash']=0.0
        with self.assertRaisesRegex(AttributionError,'CASH'):prepare_path(p,'fixture')

    def test_pre_funding_state_unchanged_in_all_scenarios(self):
        payload=self.closed();p=prepare_path(payload,'fixture');before=json.dumps(encode(p),sort_keys=True)
        o=observations(2023,*data())
        for s in SCENARIOS:attribute(p,o,s)
        self.assertEqual(before,json.dumps(encode(p),sort_keys=True));self.assertEqual(payload,self.closed())

    def test_deterministic_context_independent_funding_and_replay(self):
        p=prepare_path(self.closed(),'fixture');o=observations(2023,*data(rate='0.012345678901234567890123456789'))
        with localcontext() as c:
            c.prec=4;a=attribute(p,o,Scenario())
        with localcontext() as c:
            c.prec=80;b=attribute(p,o,Scenario())
        self.assertEqual(encode(a),encode(b))

    def test_future_and_foreign_years_denied(self):
        for y in [2025,2026,2022]:
            with self.assertRaises(AccessDenied):observations(y,[],[])
        p=self.closed();p['year']=2025
        with self.assertRaises(AccessDenied):prepare_path(p,'fixture')

    def test_production_guard_denies_unregistered_data_and_network(self):
        g=DevelopmentGuard(set(),ROOT/'data/stage0b_private/funding_attribution/new',ROOT/'reports/funding_attribution/new')
        with self.assertRaises(ProhibitedAccess):g.check_path(ROOT/'data/holdout/forbidden.json')
        with self.assertRaises(ProhibitedAccess):g.audit('socket.connect',())
        with self.assertRaises(ProhibitedAccess):g.check_path(ROOT/'data/stage0b_private/foreign.json')

    def test_public_whitelist_has_no_private_financial_values(self):
        r=self.run_path();no_financial_outputs({'counts':r['counts'],'completed':1,'censored':0})
        with self.assertRaises(AccessDenied):no_financial_outputs({'net_pnl':'private'})
        self.assertEqual(r['historical_funding_data'],'PARTIAL_DATA')
        self.assertEqual(r['calendar_authority'],'USER_ATTESTED_OFFICIAL_CALENDAR')
        self.assertEqual(r['official_strategy_profitability'],'UNVALIDATED')
