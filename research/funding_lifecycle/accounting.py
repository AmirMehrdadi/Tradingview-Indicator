"""Exact, transactional SYNTHETIC_FIXTURE_ONLY accounting. No I/O or network."""
from copy import deepcopy
from dataclasses import asdict, dataclass, field, replace
from decimal import Decimal
import json
import re

from research.access import AccessDenied
from research.funding.policy import Period, MINUTE, EXECUTION_STEP

SYNTHETIC = "SYNTHETIC_FIXTURE_ONLY"
PROXY = "APPROXIMATE_MARK_PREVIOUS_1M_CLOSE"
BASE = "FUNDING_BEFORE_OLD_OPEN_EXIT"
ALTERNATE = "OLD_OPEN_EXIT_BEFORE_FUNDING"
DAY = 86400000


class LifecycleError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise LifecycleError(code)


def dec(value, code="INVALID_DECIMAL"):
    require(type(value) is Decimal and value.is_finite(), code)
    return value


def identifier(value):
    require(type(value) is str and bool(re.fullmatch(r"[A-Za-z0-9_.:-]+", value)), "INVALID_ID")


def parts(value):
    dec(value)
    t = value.as_tuple()
    c = int("".join(map(str, t.digits))) * (-1 if t.sign else 1)
    return c, t.exponent


def compose(coefficient, exponent):
    return Decimal((int(coefficient < 0), tuple(map(int, str(abs(coefficient)))), exponent))


def exact_add(a, b):
    ac, ae = parts(a)
    bc, be = parts(b)
    e = min(ae, be)
    return compose(ac*10**(ae-e)+bc*10**(be-e), e)


def exact_product(*values):
    coefficient, exponent = 1, 0
    for value in values:
        c, e = parts(value)
        coefficient *= c
        exponent += e
    return compose(coefficient, exponent)


def btc(steps):
    require(type(steps) is int and steps >= 0, "INVALID_QUANTITY_STEPS")
    return compose(steps, -3)  # Frozen BTC quantity step, with no rounding.


def funding_cashflow(steps, direction, mark, rate):
    require(direction in ("Long", "Short"), "INVALID_DIRECTION")
    dec(mark, "INVALID_MARK_PRICE")
    dec(rate, "MISSING_OR_INVALID_FUNDING_RATE")
    require(mark > 0, "INVALID_MARK_PRICE")
    value = exact_product(btc(steps), mark, rate)
    return value.copy_negate() if direction == "Long" else value


@dataclass(frozen=True)
class Owner:
    fixture_id: str
    candidate: str
    partition_id: str
    period: Period
    provenance: str = SYNTHETIC

    def validate(self):
        if type(self.provenance) is not str or self.provenance != SYNTHETIC or type(self.fixture_id) is not str or not self.fixture_id.startswith("fixture:"):
            raise AccessDenied("SYNTHETIC_FIXTURE_ONLY_REQUIRED")
        identifier(self.fixture_id)
        identifier(self.partition_id)
        require(type(self.candidate) is str and self.candidate in {f"C{i:02d}" for i in range(1, 13)}, "INVALID_CANDIDATE_OWNER")
        require(type(self.period) is Period, "INVALID_PERIOD_TYPE")
        require(type(self.period.start) is int and type(self.period.end) is int, "INVALID_PERIOD_BOUNDARIES")
        self.period.validate()


@dataclass(frozen=True)
class Scenario:
    mark_field: str = "close"
    precedence: str = BASE

    def validate(self):
        require(self.mark_field in ("close", "low", "high") and self.precedence in (BASE, ALTERNATE), "UNREGISTERED_SCENARIO")

    @property
    def identity(self):
        return self.mark_field+":"+self.precedence


SCENARIOS = tuple(Scenario(m, p) for m in ("close", "low", "high") for p in (BASE, ALTERNATE))


@dataclass(frozen=True)
class FixtureCalendar:
    owner: Owner
    expected_settlements: tuple
    complete: bool = True

    def validate(self):
        require(type(self.owner) is Owner, "INVALID_OWNER_TYPE")
        self.owner.validate()
        require(self.complete is True, "INCOMPLETE_FIXTURE_CALENDAR")
        require(type(self.expected_settlements) is tuple, "EXPLICIT_FIXTURE_SCHEDULE_REQUIRED")
        for t in self.expected_settlements:
            self.owner.period.settlement(t)
        require(list(self.expected_settlements) == sorted(set(self.expected_settlements)), "DUPLICATE_OR_UNORDERED_FIXTURE_SCHEDULE")


@dataclass(frozen=True)
class MarkMinute:
    owner: Owner
    start_ms: int
    end_ms: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    completed: bool = True
    classification: str = PROXY
    exact_tick: bool = False
    guaranteed_settlement_bounds: bool = False


@dataclass(frozen=True)
class Settlement:
    owner: Owner
    event_id: str
    time_ms: int
    rate: object
    marks: tuple = ()


@dataclass(frozen=True)
class Entry:
    owner: Owner
    entry_id: str
    fill_id: str
    time_ms: int
    signal_close_ms: int
    direction: str
    total_steps: int
    cash_after: Decimal = Decimal("10000")


@dataclass(frozen=True)
class Exit:
    owner: Owner
    entry_id: str
    fill_id: str
    time_ms: int
    phase: str
    bar_open_ms: int
    steps: int
    cash_after: Decimal = Decimal("10000")
    economic_phase: str = "EXPLICIT_FIXTURE_FILL"


@dataclass(frozen=True)
class Boundary:
    owner: Owner
    time_ms: int
    prior_exits: tuple = ()
    settlements: tuple = ()
    entry: object = None
    open_exits: tuple = ()


@dataclass(frozen=True)
class SharedSnapshot:
    cash: Decimal = Decimal("10000")
    settled_flat: Decimal = Decimal("10000")
    day_start: Decimal = Decimal("10000")
    day: int = 0
    daily_stop: bool = False
    margin_model_state: str = "PRE_FUNDING_MODEL_NOT_EXECUTED"

    @property
    def sizing_balance(self):
        return self.settled_flat

    @property
    def entry_eligible(self):
        return not self.daily_stop


@dataclass
class Position:
    entry: Entry
    remaining_steps: int
    exited_steps: int = 0
    funding_total: Decimal = Decimal(0)
    funding_events: list = field(default_factory=list)
    state: str = "OPEN"


@dataclass(frozen=True)
class FundingRecord:
    owner: Owner
    scenario: Scenario
    event_id: str
    settlement_ms: int
    entry_id: object
    quantity_steps: int
    rate: object
    selected_mark_field: str
    selected_mark: object
    mark_minute_start_ms: object
    mark_minute_end_ms: object
    cashflow: Decimal
    classification: str
    funding_tie: bool
    proxy_classification: str = PROXY
    exact_tick: bool = False
    guaranteed_settlement_bounds: bool = False


def encode(value):
    if type(value) is Decimal:
        return "0" if value.is_zero() else format(value, "f")
    if isinstance(value, dict):
        return {k: encode(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encode(v) for v in value]
    return value


class FundingLifecycle:
    """A single synthetic candidate/partition/scenario. Failed boundaries are atomic."""
    def __init__(self, calendar, scenario=Scenario()):
        if type(calendar) is not FixtureCalendar:
            raise AccessDenied("IN_MEMORY_SYNTHETIC_CALENDAR_REQUIRED")
        calendar.validate()
        require(type(scenario) is Scenario, "INVALID_SCENARIO_TYPE")
        scenario.validate()
        self.calendar, self.owner, self.scenario = calendar, calendar.owner, scenario
        self.shared = SharedSnapshot(day=self.owner.period.start//DAY)
        self.position = self.pending = None
        self.completed, self.censored = {}, {}
        self.funding, self.events = [], []
        self._entry_ids, self._fill_ids, self._settlement_ids, self._applied = set(), set(), set(), set()
        self.last_time = self.owner.period.start-1
        self.ended = False

    def _owner(self, value):
        require(type(value) is Owner, "INVALID_EVENT_PROVENANCE")
        value.validate()
        require(value == self.owner, "ENTRY_OR_PARTITION_OWNERSHIP_MISMATCH")

    def _event(self, name, t, phase, **values):
        self.events.append({"name": name, "reported_ms": t, "phase": phase, **values})

    def _reset_day(self, day):
        if day > self.shared.day:
            self.shared = replace(self.shared, day=day, day_start=self.shared.settled_flat, daily_stop=False)
            self._event("UTC_DAY_RESET", day*DAY, "UTC_DAY_RESET")

    def _exit(self, fill, t, phase):
        require(type(fill) is Exit, "INVALID_EXIT_TYPE")
        self._owner(fill.owner)
        identifier(fill.entry_id)
        identifier(fill.fill_id)
        require(type(fill.time_ms) is int and fill.time_ms == t and fill.phase == phase, "OUT_OF_ORDER_FILL_PHASE")
        identifier(fill.economic_phase)
        require(type(fill.bar_open_ms) is int and t % EXECUTION_STEP == 0 and fill.bar_open_ms == (t-EXECUTION_STEP if phase == "PRIOR_BAR" else t), "INVALID_FILL_BAR_OWNERSHIP")
        require(fill.fill_id not in self._fill_ids, "DUPLICATE_FILL_ID")
        require(self.position is not None and self.position.entry.entry_id == fill.entry_id, "ORPHANED_EXIT")
        require(type(fill.steps) is int and 0 < fill.steps <= self.position.remaining_steps, "INVALID_OR_EXCESS_EXIT_QUANTITY")
        dec(fill.cash_after, "INVALID_PRE_FUNDING_CASH_SNAPSHOT")
        p = self.position
        p.remaining_steps -= fill.steps
        p.exited_steps += fill.steps
        self._fill_ids.add(fill.fill_id)
        self.shared = replace(self.shared, cash=fill.cash_after)
        self._event("EXIT", t, phase, entry_id=fill.entry_id, fill_id=fill.fill_id, quantity_steps=fill.steps,
                    bar_open_ms=fill.bar_open_ms, economic_phase=fill.economic_phase, economic_day=(t-1 if phase == "PRIOR_BAR" else t)//DAY)
        if p.remaining_steps == 0:
            p.state = "COMPLETED"
            self.completed[p.entry.entry_id] = deepcopy(p)
            self.position = None
            delta = exact_add(fill.cash_after, self.shared.day_start.copy_negate())
            stop = delta <= exact_product(Decimal("-0.01"), self.shared.day_start)
            self.shared = replace(self.shared, settled_flat=fill.cash_after, daily_stop=self.shared.daily_stop or stop)

    def _validate_mark(self, mark, t):
        require(type(mark) is MarkMinute, "INVALID_MARK_EVIDENCE_TYPE")
        self._owner(mark.owner)
        expected = self.owner.period.mark_minute(t)
        require(type(mark.start_ms) is int and type(mark.end_ms) is int and mark.start_ms == expected and mark.end_ms == t, "INVALID_MARK_MINUTE_LINKAGE")
        require(mark.completed is True, "INCOMPLETE_MARK_MINUTE")
        require(mark.classification == PROXY and mark.exact_tick is False and mark.guaranteed_settlement_bounds is False, "UNVERIFIED_MARK_SUBSTITUTE")
        values = [dec(v, "MISSING_OR_INVALID_MARK_PRICE") for v in (mark.open, mark.high, mark.low, mark.close)]
        o, h, l, c = values
        require(min(values) > 0 and l <= o <= h and l <= c <= h, "INVALID_MARK_OHLC_GEOMETRY")

    def _fund(self, boundary):
        t = boundary.time_ms
        expected = t in self.calendar.expected_settlements
        require(type(boundary.settlements) is tuple, "EXPLICIT_SETTLEMENT_RECORDS_REQUIRED")
        require(len(boundary.settlements) <= 1, "DUPLICATE_OR_CONFLICTING_SETTLEMENT")
        require(expected or not boundary.settlements, "UNEXPECTED_SETTLEMENT_OUTSIDE_FIXTURE_CALENDAR")
        if not expected:
            return
        p = self.position
        # Validate old OPEN fills on a shadow copy. Shared state and signal occupancy never use the preview.
        require(type(boundary.open_exits) is tuple, "INVALID_OPEN_EXIT_BATCH")
        preview = deepcopy(self)
        old_exits = tuple(fill for fill in boundary.open_exits if p is not None and fill.entry_id == p.entry.entry_id)
        for fill in old_exits:
            preview._exit(fill, t, "OPEN")
        tie = bool(old_exits)
        quantity_steps = 0 if p is None else p.remaining_steps
        if self.scenario.precedence == ALTERNATE:
            quantity_steps = 0 if preview.position is None else preview.position.remaining_steps
        require(not quantity_steps or t % EXECUTION_STEP == 0, "FUNDING_ALIGNMENT_UNRESOLVED")
        evidence = boundary.settlements[0] if boundary.settlements else None
        rate = mark = None
        event_id = "structural:"+str(t)
        if evidence is not None:
            require(type(evidence) is Settlement, "INVALID_SETTLEMENT_EVIDENCE_TYPE")
            self._owner(evidence.owner)
            identifier(evidence.event_id)
            self.owner.period.settlement(evidence.time_ms)
            require(evidence.time_ms == t, "SETTLEMENT_TIMESTAMP_MISMATCH")
            event_id, rate = evidence.event_id, evidence.rate
            require(type(evidence.marks) is tuple and len(evidence.marks) <= 1, "DUPLICATE_OR_CONFLICTING_MARK_EVIDENCE")
            if rate is not None:
                dec(rate, "MISSING_OR_INVALID_FUNDING_RATE")
            if evidence.marks:
                mark = evidence.marks[0]
                self._validate_mark(mark, t)
        require(event_id not in self._settlement_ids, "DUPLICATE_SETTLEMENT_EVENT_ID")
        key = (self.owner.partition_id, self.owner.candidate, self.scenario.identity, t)
        require(key not in self._applied, "DUPLICATE_FUNDING_APPLICATION")
        if quantity_steps:
            require(evidence is not None, "MISSING_REQUIRED_SETTLEMENT")
            dec(rate, "MISSING_OR_INVALID_FUNDING_RATE")
            require(mark is not None, "MISSING_REQUIRED_MARK")
            selected = getattr(mark, self.scenario.mark_field)
            amount = funding_cashflow(quantity_steps, p.entry.direction, selected, rate)
            classification = "APPLIED_SYNTHETIC_FUNDING"
        else:
            selected, amount = None, Decimal(0)
            classification = "EXEMPT_STRUCTURALLY_ZERO_OLD_EXPOSURE"
        record = FundingRecord(self.owner, self.scenario, event_id, t, None if p is None else p.entry.entry_id,
                               quantity_steps, rate, self.scenario.mark_field, selected, None if mark is None else mark.start_ms,
                               None if mark is None else mark.end_ms, amount, classification, tie)
        self.funding.append(record)
        self._settlement_ids.add(event_id)
        self._applied.add(key)
        if p is not None:
            p.funding_total = exact_add(p.funding_total, amount)
            p.funding_events.append(record)
        self._event("FUNDING_TIE" if tie else "FUNDING", t, "FUNDING", quantity_steps=quantity_steps,
                    precedence=self.scenario.precedence, old_open_exit_preview_only=self.scenario.precedence == ALTERNATE)

    def _entry(self, entry, t):
        require(type(entry) is Entry, "INVALID_ENTRY_TYPE")
        self._owner(entry.owner)
        identifier(entry.entry_id)
        identifier(entry.fill_id)
        require(type(entry.time_ms) is int and type(entry.signal_close_ms) is int and entry.time_ms == entry.signal_close_ms == t and t % EXECUTION_STEP == 0, "ENTRY_PHASE_OR_SIGNAL_OWNERSHIP_INVALID")
        self.owner.period.settlement(t)
        require(entry.direction in ("Long", "Short"), "INVALID_DIRECTION")
        require(type(entry.total_steps) is int and entry.total_steps > 0, "INVALID_ENTRY_QUANTITY")
        require(entry.entry_id not in self._entry_ids and entry.fill_id not in self._fill_ids, "DUPLICATE_ENTRY_OR_FILL_ID")
        require(self.position is None and self.pending is None, "POSITION_BUSY_AT_SIGNAL")
        require(self.shared.entry_eligible, "SHARED_DAILY_STOP_BLOCKS_ENTRY")
        dec(entry.cash_after, "INVALID_PRE_FUNDING_CASH_SNAPSHOT")
        self.pending = entry
        self._event("SIGNAL_CLOSE", t, "SIGNAL_CLOSE", entry_id=entry.entry_id)

    def _advance(self, boundary):
        t = boundary.time_ms
        require(not self.ended, "PARTITION_ALREADY_ENDED")
        require(type(t) is int and self.owner.period.start <= t <= self.owner.period.end, "FUTURE_OR_OUT_OF_PARTITION_EVENT")
        require(t > self.last_time, "DUPLICATE_OR_OUT_OF_ORDER_BOUNDARY")
        require(not any(self.last_time < s < t for s in self.calendar.expected_settlements), "MISSING_OR_SKIPPED_EXPECTED_SETTLEMENT")
        require(type(boundary.prior_exits) is tuple, "INVALID_PRIOR_EXIT_BATCH")
        if t > self.owner.period.start:
            self._reset_day((t-1)//DAY)
        for fill in boundary.prior_exits:
            self._exit(fill, t, "PRIOR_BAR")
        if t == self.owner.period.end:
            if self.position is not None:
                self.position.state = "CENSORED"
                self.censored[self.position.entry.entry_id] = deepcopy(self.position)
                self.position = None
            self.pending, self.ended, self.last_time = None, True, t
            self._event("PARTITION_END", t, "PARTITION_END", excluded_boundary_payloads_not_processed=True)
            return
        self._reset_day(t//DAY)
        require(type(boundary.open_exits) is tuple and all(type(f) is Exit for f in boundary.open_exits), "INVALID_OPEN_EXIT_BATCH")
        self._fund(boundary)
        if boundary.entry is not None:
            self._entry(boundary.entry, t)
        old_id = None if self.position is None else self.position.entry.entry_id
        for fill in boundary.open_exits:
            if fill.entry_id == old_id:
                self._exit(fill, t, "OPEN")
        if self.pending is not None:
            entry = self.pending
            self.position = Position(entry, entry.total_steps)
            self._entry_ids.add(entry.entry_id)
            self._fill_ids.add(entry.fill_id)
            self.shared = replace(self.shared, cash=entry.cash_after)
            self.pending = None
            self._event("ENTRY", t, "OPEN", entry_id=entry.entry_id)
        for fill in boundary.open_exits:
            if fill.entry_id != old_id:
                self._exit(fill, t, "OPEN")
        self._event("INTRABAR_TIMING_NOT_INFERRED", t, "INTRABAR")
        self.last_time = t

    def _invariants(self):
        require(not (self.position is not None and self.pending is not None), "OVERLAPPING_POSITION_AND_PENDING_ENTRY")
        require(len({(f.settlement_ms, f.scenario.identity) for f in self.funding}) == len(self.funding), "DUPLICATE_FUNDING_RECORD")
        positions = list(self.completed.values())+list(self.censored.values())+([] if self.position is None else [self.position])
        require(len({p.entry.entry_id for p in positions}) == len(positions), "DUPLICATE_POSITION_OWNERSHIP")
        for p in positions:
            require(type(p.remaining_steps) is int and type(p.exited_steps) is int and p.remaining_steps+p.exited_steps == p.entry.total_steps and min(p.remaining_steps, p.exited_steps) >= 0, "QUANTITY_CONSERVATION_FAILED")
            require(len({event.settlement_ms for event in p.funding_events}) == len(p.funding_events), "DUPLICATE_ENTRY_FUNDING_ATTRIBUTION")
            total = Decimal(0)
            for event in p.funding_events:
                require(event in self.funding and event.entry_id == p.entry.entry_id and event.owner == self.owner and event.scenario == self.scenario, "FUNDING_ATTRIBUTION_OWNERSHIP_FAILED")
                total = exact_add(total, event.cashflow)
            require(total == p.funding_total, "FUNDING_ATTRIBUTION_CONSERVATION_FAILED")
        for event in self.funding:
            require(event.owner == self.owner and event.scenario == self.scenario, "FUNDING_ATTRIBUTION_OWNERSHIP_FAILED")
            if event.entry_id is not None:
                require(sum(event in p.funding_events for p in positions) == 1, "ORPHANED_FUNDING_ATTRIBUTION")

    def advance(self, boundary):
        if type(boundary) is not Boundary:
            raise AccessDenied("IN_MEMORY_SYNTHETIC_BOUNDARY_REQUIRED")
        self._owner(boundary.owner)
        trial = deepcopy(self)
        trial._advance(boundary)
        trial._invariants()
        self.__dict__.clear()
        self.__dict__.update(trial.__dict__)

    def serialized(self):
        value = {"provenance": SYNTHETIC, "owner": asdict(self.owner), "scenario": asdict(self.scenario),
                 "fixture_calendar": asdict(self.calendar),
                 "shared": asdict(self.shared), "open": None if self.position is None else asdict(self.position),
                 "pending": None if self.pending is None else asdict(self.pending),
                 "completed": {k: asdict(v) for k, v in sorted(self.completed.items())},
                 "censored": {k: asdict(v) for k, v in sorted(self.censored.items())},
                 "funding": [asdict(v) for v in self.funding], "events": self.events, "ended": self.ended, "last_boundary_ms": self.last_time,
                 "historical_funding_data": "PARTIAL_DATA", "historical_calendar_completeness": "UNVERIFIED",
                 "official_research_result": "NOT_EVALUABLE"}
        return (json.dumps(encode(value), sort_keys=True, indent=2, allow_nan=False)+"\n").encode()
