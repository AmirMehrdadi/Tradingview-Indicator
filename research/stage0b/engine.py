"""Independent Research-mode paths. Financial state is strictly private."""
import math
from collections import Counter
from dataclasses import asdict

from research.access import iso
from research.stage0a import percentiles
from .model import FundingEvidence, IntegrityError, Plan, Position, quantity, size_steps

GATES = ("A", "B", "C", "D", "E", "F", "G")


class Engine:
    def __init__(self, candidate, window, config, logical_run_id, price_bounds=(0.10, 1999999.80), input_status="UNVERIFIED_TEST_INPUT"):
        window.validate()
        if candidate not in config["candidate_combinations"]:
            raise IntegrityError("UNAUTHORIZED_CANDIDATE")
        self.candidate, self.window, self.config = candidate, window, config
        self.logical_run_id, self.price_bounds = logical_run_id, price_bounds
        self.input_status = input_status
        self._cash = self._settled = self._day_start = 10000.0
        self._day = None
        self.daily_stop = False
        self.pending = self.position = None
        self.consumed = set()
        self._ids, self._fill_ids, self._filled_steps, self._closed_steps = set(), set(), {}, {}
        self._ledger = []
        self.funding = FundingEvidence()
        self.after = Counter({k: 0 for k in GATES})
        self.by_direction = {d: Counter() for d in ("Long", "Short")}
        self.rejections, self.quality = Counter(), Counter()
        self.pivot_ages = []
        self.filled = self.completed = self.censored = self.rejected_margin = 0
        self.daily_activations = self.daily_blocked = 0
        self.ended = False

    def _event(self, name, t, phase, **values):
        if phase in ("OPEN", "PRIOR_BAR", "SIGNAL_CLOSE"):
            opening = t if phase == "OPEN" else t-self.window.step
            values.update(bar_open_time=iso(opening), bar_end_time=iso(opening+self.window.step))
        self._ledger.append({"event": name, "time_utc": iso(t), "phase": phase, "candidate": self.candidate,
                             "year": self.window.year, **values})

    def reset_day(self, t):
        day = t//86_400_000
        if day != self._day:
            self._day, self._day_start, self.daily_stop = day, self._settled, False
            self._event("UTC_DAY_RESET", t, "UTC_DAY_RESET", settled_balance=self._settled)

    def _gate(self, gate, direction):
        self.after[gate] += 1
        self.by_direction[direction]["after_"+gate] += 1

    def offer(self, setup, signal_bar_open):
        """A..F remain diagnostic while busy; only G can mutate trading state."""
        if self.ended:
            raise IntegrityError("PATH_ALREADY_FINISHED")
        if setup is None:
            return
        d = setup.direction
        self._gate("A", d)
        if setup.pivot_index is None:
            self.rejections["B:NO_CONFIRMED_SUITABLE_PIVOT"] += 1
            return
        self._gate("B", d)
        self.pivot_ages.append(setup.pivot_age)
        if not setup.stop_valid:
            self.rejections["C:STOP_RANGE_OR_SL_SIDE"] += 1
            return
        self._gate("C", d)
        if not setup.cost_valid:
            self.rejections["D:COST_STOP_FLOOR"] += 1
            return
        self._gate("D", d)
        if not setup.levels_valid or not all(self.price_bounds[0] <= x <= self.price_bounds[1] for x in (setup.entry_ref, setup.sl, setup.tp1, setup.tp2)):
            self.rejections["E:INVALID_ORDER_PRICE_GEOMETRY_OR_LIMIT"] += 1
            return
        steps, rejection = size_steps(setup, self._settled, self.config)
        if rejection:
            self.rejections["E:"+rejection] += 1
            return
        self._gate("E", d)
        flags = dict(setup.filters)
        for name in self.config["candidate_combinations"][self.candidate][1:]:
            if not flags[name]:
                self.rejections["F:FILTER_"+name] += 1
                return
        self._gate("F", d)
        key = (d, setup.pullback)
        if self.daily_stop:
            self.daily_blocked += 1
            self.rejections["G:DAILY_STOP"] += 1
            return
        if self.pending is not None or self.position is not None:
            self.rejections["G:POSITION_BUSY"] += 1
            return
        if key in self.consumed:
            self.rejections["G:CONSUMED_PULLBACK"] += 1
            return
        total, first, second = steps
        entry_id = f"{self.logical_run_id}:Research:{self.candidate}:{self.window.year}:{signal_bar_open}:{d}"
        plan = Plan(entry_id, d, signal_bar_open+self.window.step, signal_bar_open, setup.pullback, setup.pivot_index,
                    setup.entry_ref, setup.sl, setup.tp1, setup.tp2, total, first, second, self._settled,
                    0.0025*self._settled, setup.risk)
        self.queue(plan)
        self._gate("G", d)

    def queue(self, plan):
        self.window.authorize_bar(plan.signal_time)
        if self.pending is not None or self.position is not None or plan.entry_id in self._ids:
            raise IntegrityError("OVERLAPPING_OR_DUPLICATE_ENTRY")
        if (plan.direction, plan.pullback) in self.consumed:
            raise IntegrityError("PULLBACK_ALREADY_CONSUMED")
        if plan.tp1_steps <= 0 or plan.tp2_steps <= 0 or plan.tp1_steps+plan.tp2_steps != plan.total_steps:
            raise IntegrityError("INVALID_BRACKET_RESERVATION")
        self._ids.add(plan.entry_id)
        self.consumed.add((plan.direction, plan.pullback))
        self.pending = plan
        self._event("SIGNAL_AND_BRACKETS_QUEUED", plan.signal_time, "SIGNAL_CLOSE", plan=asdict(plan),
                    bracket_ids=[plan.entry_id+":L1", plan.entry_id+":L2"],
                    oca_names=[plan.entry_id+":OCA1", plan.entry_id+":OCA2"], funding_cashflows=None)

    @property
    def _fee(self):
        return self.config["cost_assumptions"]["taker_fee_rate_per_side"]

    @property
    def _friction(self):
        return self.config["cost_assumptions"]["execution_friction_rate_per_fill"]

    def _margin(self, mark, t, phase):
        p = self.position
        if p is None:
            return
        remaining = quantity(self.config, sum(p.remaining))
        if remaining <= 0:
            raise IntegrityError("ORPHANED_POSITION")
        equity = self._cash+p.plan.sign*remaining*(mark-p.entry_fill)
        if equity < 0.5*remaining*mark and not p.margin_flagged:
            p.margin_flagged = True
            self.quality["MARGIN_MODEL_EVENT"] += 1
            self._event("MARGIN_MODEL_EVENT", t, phase, entry_id=p.plan.entry_id)

    def process_open(self, bar):
        if self.ended:
            raise IntegrityError("PATH_ALREADY_FINISHED")
        self.window.authorize_bar(bar.open_time)
        if self.pending is not None and self.position is not None:
            raise IntegrityError("PENDING_AND_ACTIVE_POSITION")
        if self.pending is not None:
            plan = self.pending
            if plan.signal_time != bar.open_time:
                raise IntegrityError("ENTRY_NOT_NEXT_OPEN")
            self.pending = None
            amount = quantity(self.config, plan.total_steps)
            fill = bar.open*(1+plan.sign*self._friction)
            entry_fee = amount*fill*self._fee
            if 0.5*amount*fill+entry_fee > self._cash:
                self.rejected_margin += 1
                self.by_direction[plan.direction]["N_rejected_margin"] += 1
                self._event("ENTRY_REJECTED_MARGIN", bar.open_time, "OPEN", entry_id=plan.entry_id, cancelled_brackets=True)
                return
            fid = plan.entry_id+":ENTRY"
            if fid in self._fill_ids:
                raise IntegrityError("DUPLICATE_ENTRY_FILL")
            self._fill_ids.add(fid)
            self._cash -= entry_fee
            self.position = Position(plan, fill, [plan.tp1_steps, plan.tp2_steps])
            self._filled_steps[plan.entry_id] = 0
            self.filled += 1
            self.by_direction[plan.direction]["N_filled"] += 1
            self._event("ENTRY_FILLED", bar.open_time, "OPEN", entry_id=plan.entry_id, fill=fill,
                        raw_market_price=bar.open, quantity_steps=plan.total_steps, entry_fee=entry_fee, cash=self._cash)
            directional_risk = plan.sign*(fill-plan.sl)
            if directional_risk <= 0:
                self.quality["EXECUTION_ANOMALY"] += 1
            elif (directional_risk-plan.planned_risk)/plan.planned_risk > 0.15:
                self.quality["ENTRY_DEVIATION"] += 1
            stop_economic = plan.sl*(1-plan.sign*self._friction)
            anticipated = amount*plan.sign*(fill-stop_economic)+entry_fee+amount*stop_economic*self._fee
            if anticipated > plan.risk_budget:
                self.quality["RISK_OVERRUN"] += 1
            if amount*fill > 2.0*plan.signal_balance:
                self.quality["NOTIONAL_OVERRUN"] += 1
        p = self.position
        if p is None:
            return
        self._margin(bar.open, bar.open_time, "OPEN")
        invalid_fill = p.plan.sign*(p.entry_fill-p.plan.sl) <= 0
        stop_marketable = p.plan.sign*(bar.open-p.plan.sl) <= 0
        if stop_marketable or invalid_fill:
            if bar.open_time == p.plan.signal_time:
                self.quality["ENTRY_AT_OR_BEYOND_SL"] += 1
                if not invalid_fill:
                    self.quality["EXECUTION_ANOMALY"] += 1
            self._stop_all(bar.open, bar.open_time, "OPEN")
            return
        for leg, target in enumerate((p.plan.tp1, p.plan.tp2)):
            if self.position is None:
                break
            if p.remaining[leg] and p.plan.sign*(bar.open-target) >= 0:
                self._exit_leg(leg, target, bar.open_time, "OPEN", "TP", mark_price=bar.open)
            elif p.remaining[leg] and p.plan.sign*(p.entry_fill-target) >= 0 and bar.open_time == p.plan.signal_time:
                self.quality["FILL_FRICTION_CROSSED_TP"] += 1
                self.quality["EXECUTION_ANOMALY"] += 1
        self.assert_integrity()

    def process_intrabar(self, bar):
        p = self.position
        if p is None:
            return
        t = bar.open_time+self.window.step
        stop_hit = bar.low <= p.plan.sl if p.plan.sign == 1 else bar.high >= p.plan.sl
        favorable = bar.high if p.plan.sign == 1 else bar.low
        target_hit = any(p.remaining[i] and p.plan.sign*(favorable-target) >= 0 for i, target in enumerate((p.plan.tp1, p.plan.tp2)))
        if stop_hit:
            if target_hit:
                self.quality["UNCERTAIN_INTRABAR_ORDER"] += 1
            self._stop_all(p.plan.sl, t, "PRIOR_BAR")
            return
        # Process the frozen Research fill sequence; never apply a later extremum to a closed leg.
        for leg, target in enumerate((p.plan.tp1, p.plan.tp2)):
            if self.position is None:
                break
            if p.remaining[leg] and p.plan.sign*(favorable-target) >= 0:
                self._margin(target, t, "PRIOR_BAR")
                self._exit_leg(leg, target, t, "PRIOR_BAR", "TP")
        if self.position is not None:
            adverse = bar.low if self.position.plan.sign == 1 else bar.high
            self._margin(adverse, t, "PRIOR_BAR")
            self._margin(bar.close, t, "PRIOR_BAR")
        self.assert_integrity()

    def _stop_all(self, raw_price, t, phase):
        self._margin(raw_price, t, phase)
        for leg in (0, 1):
            if self.position is not None and self.position.remaining[leg]:
                self._exit_leg(leg, raw_price, t, phase, "STOP")
        self.assert_integrity()

    def _exit_leg(self, leg, raw_price, t, phase, kind, mark_price=None):
        p = self.position
        if p is None or p.remaining[leg] <= 0:
            raise IntegrityError("DUPLICATE_OR_ORPHANED_EXIT")
        fid = p.plan.entry_id+f":L{leg+1}"
        if fid in self._fill_ids:
            raise IntegrityError("DUPLICATE_EXIT_FILL")
        self._fill_ids.add(fid)
        steps = p.remaining[leg]
        amount = quantity(self.config, steps)
        fill = raw_price*(1-p.plan.sign*self._friction)
        fee = amount*fill*self._fee
        realized = p.plan.sign*amount*(fill-p.entry_fill)
        self._cash += realized-fee
        p.remaining[leg] = 0
        self._filled_steps[p.plan.entry_id] += steps
        if self._filled_steps[p.plan.entry_id]+sum(p.remaining) != p.plan.total_steps:
            raise IntegrityError("QUANTITY_CONSERVATION_FAILED")
        self._event("EXIT_LEG", t, phase, entry_id=p.plan.entry_id, bracket=leg+1, kind=kind,
                    fill=fill, raw_market_price=raw_price, quantity_steps=steps, realized_pnl=realized, exit_fee=fee, cash=self._cash)
        if sum(p.remaining) == 0:
            self._closed_steps[p.plan.entry_id] = p.plan.total_steps
            self.position = None
            self._settled = self._cash
            self.completed += 1
            self.by_direction[p.plan.direction]["N_completed"] += 1
            self._event("POSITION_CLOSED", t, phase, entry_id=p.plan.entry_id, settled_balance=self._settled,
                        cancelled_brackets=True, funding_adjusted_result=None, funding_status="MISSING")
            if self._settled-self._day_start <= -0.01*self._day_start and not self.daily_stop:
                self.daily_stop = True
                self.daily_activations += 1
                self._event("DAILY_STOP_ACTIVATED", t, phase)
        else:
            self._margin(raw_price if mark_price is None else mark_price, t, phase)

    def assert_integrity(self):
        if not math.isfinite(self._cash) or not math.isfinite(self._settled):
            raise IntegrityError("NONFINITE_ACCOUNTING_STATE")
        if self.position is not None:
            p = self.position
            if any(type(n) is not int or n < 0 for n in p.remaining):
                raise IntegrityError("INVALID_REMAINING_STEPS")
            if sum(p.remaining)+self._filled_steps[p.plan.entry_id] != p.plan.total_steps:
                raise IntegrityError("QUANTITY_CONSERVATION_FAILED")
        if self.ended:
            for entry_id, total in self._closed_steps.items():
                if self._filled_steps[entry_id] != total:
                    raise IntegrityError("UNDERFILLED_CLOSED_POSITION")
        active = int(self.position is not None and not self.ended)
        if self.filled != self.completed+self.censored+active:
            raise IntegrityError("POSITION_COUNT_CONSERVATION_FAILED")

    def finish(self):
        if self.ended or self.pending is not None:
            raise IntegrityError("INVALID_PARTITION_FINISH")
        if self.position is not None:
            self.censored += 1
            self.by_direction[self.position.plan.direction]["N_censored"] += 1
            self._event("CENSORED_AT_PARTITION_END", self.window.end, "PARTITION_END",
                        open_plan=asdict(self.position.plan), remaining_steps=list(self.position.remaining),
                        cash=self._cash, settled_balance=self._settled, funding_cashflows=None)
        self.ended = True
        self.assert_integrity()
        if self.after["G"] != self.filled+self.rejected_margin:
            raise IntegrityError("SIGNAL_FILL_REJECTION_CONSERVATION_FAILED")

    def run(self, features):
        if (features.window != self.window or not features.candles or len(features.candles) != len(features.setups)
                or features.candles[-1].open_time+self.window.step != self.window.end):
            raise IntegrityError("INCOMPLETE_EXECUTION_PARTITION")
        for bar, setup in zip(features.candles, features.setups):
            if bar.open_time >= self.window.start:
                self.reset_day(bar.open_time)
                self.process_open(bar)
                self.process_intrabar(bar)
            close_time = bar.open_time+self.window.step
            if close_time == self.window.end:
                self.finish()
                break
            if close_time >= self.window.start:
                self.reset_day(close_time)  # Prior-bar settlement precedes the midnight reset and signal.
                self.offer(setup, bar.open_time)
            self.assert_integrity()
        return self.public_summary()

    def public_summary(self):
        if not self.ended:
            raise IntegrityError("PATH_NOT_FINISHED")
        previous, rates = self.after["A"], {}
        for gate in GATES:
            rates[gate] = None if previous == 0 else self.after[gate]/previous
            previous = self.after[gate]
        censor_rate = 0.0 if self.filled == 0 else self.censored/self.filled
        return {"candidate": self.candidate, "year": self.window.year, "N_raw_candidate": self.after["A"],
                "N_after_each_gate": dict(self.after), "N_nonoverlap": self.after["G"], "N_signals": self.after["G"],
                "N_filled": self.filled, "N_completed": self.completed, "N_censored": self.censored,
                "N_rejected_margin": self.rejected_margin, "daily_stop_activations": self.daily_activations,
                "daily_stop_blocked_opportunities": self.daily_blocked,
                "direction_counts": {d: {k: v[k] for k in [*("after_"+g for g in GATES), "N_filled", "N_completed", "N_censored", "N_rejected_margin"]} for d, v in self.by_direction.items()},
                "pivot_age_bars": {"N": len(self.pivot_ages), "percentiles": percentiles(self.pivot_ages)},
                "rejection_reasons": dict(sorted(self.rejections.items())), "funnel_pass_rates": rates,
                "distance_from_120": self.completed-120, "censor_rate": censor_rate,
                "censoring_quality": "NO_FILLED_TRADES" if self.filled == 0 else "WITHIN_FROZEN_5_PERCENT" if censor_rate <= 0.05 else "EXCEEDS_FROZEN_5_PERCENT",
                "quality_events": dict(sorted(self.quality.items())), "integrity": "PASS",
                "execution_model_validity": "INVALID_MARGIN_MODEL_EVENT" if self.quality["MARGIN_MODEL_EVENT"] else "RESEARCH_MODEL_PREFUNDING_COUNTS",
                "funding": self.funding.public(), "data_quality": self.input_status,
                "assumptions": {"instrument": "HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION", "costs": "RESEARCH_ASSUMPTIONS_NOT_VERIFIED_ACCOUNT_RATES", "intrabar": "STOP_FIRST_AFTER_KNOWN_OPEN_FILLS", "limit_trigger": "TOUCH_BASE_CASE", "liquidity_partial_fills": "NOT_MODELED"},
                "tradingview_execution": "EXECUTION GATE — UNVERIFIED"}

    def private_payload(self):
        return {"candidate": self.candidate, "year": self.window.year, "ledger": self._ledger,
                "funding_cashflows": None, "funding_status": "MISSING_NOT_ZERO", "final_cash": self._cash,
                "settled_flat_balance": self._settled, "consumed_pullbacks": sorted(self.consumed),
                "censored_open_position": self.position is not None}
