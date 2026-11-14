"""Private execution/accounting state. Public output is built separately."""
import math
from dataclasses import dataclass
from decimal import Decimal


class IntegrityError(RuntimeError):
    pass


class FundingMissingError(RuntimeError):
    pass


@dataclass(frozen=True)
class FundingEvidence:
    rates: str = "MISSING_NOT_RETRIEVED"
    settlement_mark: str = "MISSING_NOT_RETRIEVED"

    def require_net_research(self):
        raise FundingMissingError("NET_RESEARCH_NOT_EVALUABLE_MISSING_FUNDING_AND_MARK")

    def public(self):
        return {"rates": self.rates, "settlement_mark": self.settlement_mark,
                "funding_adjusted_result": "NOT_EVALUABLE", "zero_substitution": False,
                "count_scope": "PREFUNDING_FEASIBILITY_ONLY"}


@dataclass(frozen=True)
class Plan:
    entry_id: str
    direction: str
    signal_time: int
    signal_bar_open: int
    pullback: int
    pivot_index: int
    entry_ref: float
    sl: float
    tp1: float
    tp2: float
    total_steps: int
    tp1_steps: int
    tp2_steps: int
    signal_balance: float
    risk_budget: float
    planned_risk: float

    @property
    def sign(self):
        return 1 if self.direction == "Long" else -1


@dataclass
class Position:
    plan: Plan
    entry_fill: float
    remaining: list
    margin_flagged: bool = False
    funding_cashflows: object = None


def quantity(config, steps):
    return float(Decimal(config["instrument_assumption"]["qty_step"]) * steps)


def size_steps(setup, settled, config):
    meta = config["instrument_assumption"]
    if not setup.levels_valid:
        return None, "INVALID_TP_GEOMETRY"
    if settled <= 0 or setup.risk is None or setup.cost is None:
        return None, "NO_VALID_RISK_BUDGET"
    budget = 0.0025*settled
    raw = min(budget/(setup.risk+setup.cost), 2.0*settled/setup.entry_ref)
    total = math.floor(raw/float(meta["qty_step"]))
    first, second = total//2, total-total//2
    q = Decimal(meta["qty_step"])*total
    if total <= 0 or q < Decimal(meta["min_order_qty"]) or float(q)*setup.entry_ref < float(meta["min_opening_notional"]):
        return None, "ENTRY_MINIMUM"
    if q > Decimal(meta["max_market_order_qty"]):
        return None, "ENTRY_MAXIMUM"
    for index, steps in enumerate((first, second), 1):
        amount = Decimal(meta["qty_step"])*steps
        if steps <= 0 or amount < Decimal(meta["min_order_qty"]):
            return None, "INVALID_PARTIAL_QUANTITY"
        if amount > Decimal(meta["max_market_order_qty"]) or amount > Decimal(meta["max_limit_order_qty"]):
            return None, "PARTIAL_MAXIMUM"
        if meta["minimum_order_rules"][f"tp{index}_reduce_only_limit"]["minimum_notional_applies"]:
            target = setup.tp1 if index == 1 else setup.tp2
            if float(amount)*target < float(meta["min_opening_notional"]):
                return None, "PARTIAL_MINIMUM_NOTIONAL"
    return (total, first, second), None
