"""Pure historical-event adapter using the unchanged Phase 4C exact arithmetic."""
from collections import Counter
from decimal import Decimal, localcontext
import math

from research.access import timestamp, iso
from research.funding.policy import Period, EXECUTION_STEP, MINUTE
from research.funding_lifecycle.accounting import (
    BASE, ALTERNATE, PROXY, SCENARIOS, btc, exact_add, exact_product, funding_cashflow,
)

LABEL = "CONDITIONAL_DEVELOPMENT_DIAGNOSTIC"
CALENDAR = "USER_ATTESTED_OFFICIAL_CALENDAR"


class AttributionError(ValueError):
    """Public-safe error code only; never attach a private value."""


def need(condition, code):
    if not condition:
        raise AttributionError(code)


def number(value):
    need(type(value) in (str, float, int, Decimal), "INVALID_DECIMAL_INPUT")
    try:
        result = Decimal(str(value))
    except Exception:
        raise AttributionError("INVALID_DECIMAL_INPUT") from None
    need(result.is_finite(), "NONFINITE_ACCOUNTING_VALUE")
    return result


def total(values):
    result = Decimal(0)
    for value in values:
        result = exact_add(result, value)
    return result


def observations(year, rates, marks):
    """Attested calendar is conditional authority, never independent completeness."""
    period = Period.annual(year)
    expected = tuple(range(period.start, period.end, 8*3600000))
    schedule, prices = {}, {}
    for row in rates:
        t = row['settlement_ms']
        period.settlement(t)  # Authorize timestamps before inspecting values.
        need(t % EXECUTION_STEP == 0, "FUNDING_ALIGNMENT_UNRESOLVED")
        need(t not in schedule, "DUPLICATE_OR_CONFLICTING_SETTLEMENT")
        schedule[t] = number(row['funding_rate'])
    need(tuple(sorted(schedule)) == expected, "ATTESTED_CALENDAR_RECORDS_MISSING_OR_EXTRA")
    for row in marks:
        t = row['settlement_ms']
        opening = period.mark_minute(t)
        need(t in schedule and t not in prices, "DUPLICATE_OR_UNLINKED_MARK")
        need(row['minute_open_ms'] == opening and row['minute_end_ms'] == t,
             "MARK_MINUTE_ALIGNMENT_INVALID")
        need(row['proxy_classification'] == PROXY and row['exact_tick'] is False
             and row['guaranteed_settlement_bounds'] is False, "MARK_PROXY_CLASSIFICATION_INVALID")
        o, h, l, c = [number(row[k]) for k in ('open', 'high', 'low', 'close')]
        need(min(o, h, l, c) > 0 and l <= o <= h and l <= c <= h, "INVALID_MARK_GEOMETRY")
        need(number(row['settlement_price_proxy']) == c
             and number(row['low_sensitivity']) == l and number(row['high_sensitivity']) == h,
             "MARK_PROXY_LINKAGE_INVALID")
        prices[t] = dict(close=c, low=l, high=h)
    required = set(expected) - ({period.start} if year == 2023 else set())
    need(set(prices) == required, "REQUIRED_MARK_MISSING_OR_EXTRA")
    return period, schedule, prices


def prepare_path(payload, logical_id):
    """Validate immutable ledger ownership and reconstruct exposure, not prices."""
    year, candidate = payload['year'], payload['candidate']
    period = Period.annual(year)
    need(candidate in {f'C{i:02}' for i in range(1, 13)}, "INVALID_CANDIDATE")
    need(payload['funding_cashflows'] is None and payload['funding_status'] == 'MISSING_NOT_ZERO',
         "ORIGINAL_FUNDING_STATE_CHANGED")
    plans, trades, transitions = {}, {}, []
    pending = active = None
    cash = settled = day_start = 10000.0
    day = None
    daily_stop = False
    censored = set()
    last_key = (period.start, -1)
    phases = {'PRIOR_BAR': 0, 'PARTITION_END': 1, 'UTC_DAY_RESET': 2,
              'SIGNAL_CLOSE': 3, 'OPEN': 4}
    for index, event in enumerate(payload['ledger']):
        need(event['candidate'] == candidate and event['year'] == year, "CROSS_PATH_EVENT")
        t = timestamp(event['time_utc'])
        phase, kind = event['phase'], event['event']
        need(phase in phases and period.start <= t <= period.end and t % EXECUTION_STEP == 0,
             "EVENT_TIME_OR_PHASE_INVALID")
        key = (t, phases[phase])
        need(key >= last_key, "EVENT_ORDER_INVALID")
        last_key = key
        need(t < period.end or phase in ('PRIOR_BAR', 'PARTITION_END'), "ANNUAL_END_EVENT_LEAK")
        if phase in ('PRIOR_BAR', 'SIGNAL_CLOSE', 'OPEN'):
            opening = t if phase == 'OPEN' else t-EXECUTION_STEP
            need(event['bar_open_time'] == iso(opening)
                 and event['bar_end_time'] == iso(opening+EXECUTION_STEP), "BAR_PHASE_OWNERSHIP_INVALID")
        if kind == 'UTC_DAY_RESET':
            need(phase == 'UTC_DAY_RESET' and t//86400000 != day
                 and event['settled_balance'] == settled, "DAILY_SNAPSHOT_CHANGED")
            day, day_start, daily_stop = t//86400000, settled, False
        elif kind == 'SIGNAL_AND_BRACKETS_QUEUED':
            need(phase == 'SIGNAL_CLOSE' and pending is None and active is None and not daily_stop,
                 "SIGNAL_OCCUPANCY_OR_DAILY_GATE_INVALID")
            p = event['plan']; identity = p['entry_id']
            need(identity == f"{logical_id}:Research:{candidate}:{year}:{p['signal_bar_open']}:{p['direction']}",
                 "NONCANONICAL_ENTRY_ID")
            need(identity not in plans and p['direction'] in ('Long', 'Short'), "DUPLICATE_PLAN_OR_DIRECTION")
            need(p['signal_time'] == t and p['signal_bar_open'] == t-EXECUTION_STEP,
                 "SIGNAL_CLOSE_OWNERSHIP_INVALID")
            steps = p['total_steps']
            need(type(steps) is int and steps >= 2 and p['tp1_steps'] == steps//2
                 and p['tp2_steps'] == steps-steps//2, "PLAN_QUANTITY_CONSERVATION_FAILED")
            risk = number(p['planned_risk'])
            need(risk > 0 and float(risk) == abs(p['entry_ref']-p['sl']), "PLANNED_PRICE_RISK_CHANGED")
            need(p['signal_balance'] == settled and p['risk_budget'] == 0.0025*settled,
                 "SHARED_SIZING_SNAPSHOT_CHANGED")
            need(event['bracket_ids'] == [identity+':L1', identity+':L2']
                 and event['oca_names'] == [identity+':OCA1', identity+':OCA2'], "BRACKET_OWNERSHIP_CHANGED")
            plans[identity] = p; pending = identity
        elif kind == 'ENTRY_REJECTED_MARGIN':
            need(phase == 'OPEN' and pending == event['entry_id'] and active is None,
                 "REJECTION_OWNERSHIP_INVALID")
            pending = None
        elif kind == 'ENTRY_FILLED':
            identity = event['entry_id']
            need(phase == 'OPEN' and pending == identity and active is None and identity not in trades,
                 "ENTRY_OWNERSHIP_OR_OCCUPANCY_INVALID")
            p = plans[identity]
            need(p['signal_time'] == t and event['quantity_steps'] == p['total_steps'], "ENTRY_QUANTITY_OR_TIME_CHANGED")
            fee = number(event['entry_fee']); need(fee >= 0, 'INVALID_FEE')
            cash -= event['entry_fee']; need(math.isfinite(cash) and event['cash'] == cash, "ENTRY_CASH_CHANGED")
            trades[identity] = {'entry_id': identity, 'plan': p, 'remaining': p['total_steps'],
                                'exited_legs': set(), 'components': [fee.copy_negate()],
                                'planned_R_usdt': exact_product(btc(p['total_steps']), number(p['planned_risk'])),
                                'state': 'OPEN', 'entry_fill': event['fill']}
            transitions.append((t, phase, index, 'ENTRY', identity, p['total_steps']))
            active, pending = identity, None
        elif kind == 'EXIT_LEG':
            identity = event['entry_id']; need(identity == active, "ORPHAN_EXIT")
            trade = trades[identity]; leg = event['bracket']; p = trade['plan']
            need(phase in ('PRIOR_BAR', 'OPEN') and leg in (1, 2) and leg not in trade['exited_legs'],
                 "DUPLICATE_OR_INVALID_EXIT")
            steps = event['quantity_steps']
            need(type(steps) is int and steps == p[f'tp{leg}_steps'] and steps <= trade['remaining'],
                 "EXIT_QUANTITY_CONSERVATION_FAILED")
            realized, fee = number(event['realized_pnl']), number(event['exit_fee'])
            need(fee >= 0 and number(event['fill']) > 0, "INVALID_EXIT_ACCOUNTING")
            cash += event['realized_pnl']-event['exit_fee']
            need(math.isfinite(cash) and event['cash'] == cash, "EXIT_CASH_CHANGED")
            trade['components'] += [realized, fee.copy_negate()]
            trade['exited_legs'].add(leg); trade['remaining'] -= steps
            transitions.append((t, phase, index, 'EXIT', identity, steps))
        elif kind == 'POSITION_CLOSED':
            identity = event['entry_id']; need(identity == active, "ORPHAN_CLOSURE")
            trade = trades[identity]
            need(trade['remaining'] == 0 and event['settled_balance'] == cash,
                 "CLOSURE_CONSERVATION_FAILED")
            trade['state'] = 'COMPLETED'; settled = cash; active = None
        elif kind == 'DAILY_STOP_ACTIVATED':
            need(not daily_stop and settled-day_start <= -0.01*day_start, "DAILY_STOP_CHANGED")
            daily_stop = True
        elif kind == 'CENSORED_AT_PARTITION_END':
            need(phase == 'PARTITION_END' and t == period.end and active is not None,
                 "CENSOR_BOUNDARY_INVALID")
            trade = trades[active]
            need(event['open_plan'] == trade['plan'] and sum(event['remaining_steps']) == trade['remaining']
                 and trade['remaining'] > 0, "CENSOR_QUANTITY_CHANGED")
            trade['state'] = 'CENSORED'; censored.add(active)
        elif kind == 'MARGIN_MODEL_EVENT':
            raise AttributionError('INVALID_ORIGINAL_MARGIN_PATH')
        else:
            raise AttributionError('UNRECOGNIZED_LEDGER_EVENT')
    need(pending is None and (active is None or active in censored), "UNFINISHED_LEDGER")
    need(payload['censored_open_position'] == bool(censored)
         and payload['final_cash'] == cash and payload['settled_flat_balance'] == settled,
         "FINAL_SHARED_SNAPSHOT_CHANGED")
    for trade in trades.values():
        need(trade['state'] in ('COMPLETED', 'CENSORED'), "UNCLASSIFIED_TRADE")
        trade['net_before_funding'] = total(trade.pop('components'))
        trade['exited_legs'] = sorted(trade['exited_legs'])
    return {'year': year, 'candidate': candidate, 'trades': trades, 'transitions': transitions}


def attribute(prepared, observation, scenario):
    """No shared sizing/day state is read or written by the Funding scan."""
    scenario.validate()
    period, rates, marks = observation
    need(prepared['year'] == period.year, "CROSS_YEAR_OBSERVATIONS")
    transitions = prepared['transitions']; trades = prepared['trades']
    active, remaining, index = None, 0, 0
    records, amounts = [], {identity: [] for identity in trades}
    counts = Counter(settlements=len(rates), old_exposure=0, ties=0, nonzero_quantity=0,
                     initial_2023_mark_exemptions=0, flat_exemptions=0)
    for t, rate in sorted(rates.items()):
        while index < len(transitions):
            time, phase, _, kind, identity, steps = transitions[index]
            if time > t or time == t and phase != 'PRIOR_BAR':
                break
            if kind == 'ENTRY':
                need(active is None, "TIMELINE_OVERLAP")
                active, remaining = identity, steps
            else:
                need(active == identity and 0 < steps <= remaining, "TIMELINE_QUANTITY_INVALID")
                remaining -= steps
                if not remaining:
                    active = None
            index += 1
        if active is None:
            counts['flat_exemptions'] += 1
            if t == period.start and period.year == 2023:
                counts['initial_2023_mark_exemptions'] += 1
            continue
        need(not (period.year == 2023 and t == period.start), "INITIAL_OLD_EXPOSURE_FORBIDDEN")
        exits = 0
        cursor = index
        while cursor < len(transitions) and transitions[cursor][0] == t:
            _, phase, _, kind, identity, steps = transitions[cursor]
            if phase == 'OPEN' and kind == 'EXIT' and identity == active:
                exits += steps
            cursor += 1
        need(exits <= remaining, "OPEN_EXIT_PREVIEW_OVERFILL")
        quantity = remaining-exits if scenario.precedence == ALTERNATE else remaining
        mark = marks.get(t)
        need(mark is not None, "MISSING_EXPOSED_MARK")
        value = funding_cashflow(quantity, trades[active]['plan']['direction'], mark[scenario.mark_field], rate)
        records.append({'entry_id': active, 'settlement_ms': t, 'quantity_steps': quantity,
                        'rate': rate, 'mark': mark[scenario.mark_field], 'mark_field': scenario.mark_field,
                        'minute_open_ms': t-MINUTE, 'cashflow': value, 'tie': bool(exits),
                        'proxy_classification': PROXY, 'exact_tick': False,
                        'guaranteed_settlement_bounds': False})
        amounts[active].append(value)
        counts['old_exposure'] += 1; counts['ties'] += bool(exits)
        counts['nonzero_quantity'] += quantity > 0
    outputs = []
    for identity, trade in trades.items():
        funding = total(amounts[identity]); net = exact_add(trade['net_before_funding'], funding)
        with localcontext() as ctx:
            ctx.prec = 50
            r_net = net/trade['planned_R_usdt'] if trade['state'] == 'COMPLETED' else None
        outputs.append({'entry_id': identity, 'state': trade['state'], 'remaining_steps': trade['remaining'],
                        'net_before_funding': trade['net_before_funding'], 'attributed_funding': funding,
                        'net_after_funding' if trade['state'] == 'COMPLETED' else 'censored_realized_accounting': net,
                        'planned_R_usdt': trade['planned_R_usdt'], 'trade_R_net': r_net})
    need(total(x['cashflow'] for x in records) == total(x['attributed_funding'] for x in outputs),
         "ATTRIBUTION_CONSERVATION_FAILED")
    need(len({(r['entry_id'], r['settlement_ms']) for r in records}) == len(records),
         "DUPLICATE_ATTRIBUTION")
    return {'classification': LABEL, 'calendar_authority': CALENDAR,
            'historical_funding_data': 'PARTIAL_DATA', 'official_strategy_profitability': 'UNVALIDATED',
            'year': period.year, 'candidate': prepared['candidate'], 'scenario': scenario.identity,
            'ratio_decimal_precision': 50, 'records': records, 'trades': outputs, 'counts': dict(counts)}
