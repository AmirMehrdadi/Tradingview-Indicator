"""Synthetic C01 reference decisions only. No loader, execution or profitability."""
from dataclasses import dataclass, field
import math
from tests.phase5a_reference import ANCHOR, START, END, STEP, Reference


@dataclass(frozen=True)
class Bar:
    time: int
    open: float
    high: float
    low: float
    close: float


@dataclass
class Context:
    balance: float = 10000.0
    busy: bool = False
    daily_stop: bool = False
    consumed: set = field(default_factory=set)


def finite(*values):
    return all(type(x) in (int, float) and math.isfinite(x) for x in values)


def direction(close, fast, slow):
    if not finite(close, fast, slow):
        return 0
    return 1 if fast > slow and close > slow else -1 if fast < slow and close < slow else 0


def pullback(bars, fast, slow, atr, i):
    if i < 5 or not finite(fast[i], slow[i], atr[i]):
        return None, 0, 'NOT_READY'
    d = direction(bars[i].close, fast[i], slow[i])
    if not d:
        return None, d, 'DIRECTION'
    p = None
    for j in range(i-2, i-6, -1):
        if not finite(fast[j], atr[j]):
            continue
        depth = fast[j]-bars[j].low if d == 1 else bars[j].high-fast[j]
        if bars[j].low <= fast[j] <= bars[j].high and depth <= .75*atr[j]:
            p = j
            break
    if p is None:
        return None, d, 'PULLBACK'
    if any(not finite(slow[j]) or not (bars[j].close > slow[j] if d == 1 else bars[j].close < slow[j]) for j in range(p, i+1)):
        return p, d, 'SEQUENCE'
    b = bars[i]
    trigger = b.close > b.open and b.close > fast[i] and b.close > bars[i-1].high if d == 1 else b.close < b.open and b.close < fast[i] and b.close < bars[i-1].low
    return p, d, None if trigger else 'TRIGGER'


def confirmed_pivot(bars, i, d):
    j = i-3
    if j < 3:
        return None
    v = bars[j].low if d == 1 else bars[j].high
    ns = [k for k in range(j-3, j+4) if k != j]
    return j if all(v < bars[k].low if d == 1 else v > bars[k].high for k in ns) else None


def stop_range(risk, atr):
    return finite(risk, atr) and atr > 0 and .75*atr <= risk <= 2.5*atr


def cost_gate(risk, cost):
    return finite(risk, cost) and risk > 0 and cost > 0 and risk/cost >= 2.5


def ticks(raw, d):
    if not finite(raw) or d not in (1, -1):
        raise ValueError('INVALID_GRID_INPUT')
    return math.floor(raw/.1) if d == 1 else math.ceil(raw/.1)


def split(total):
    if type(total) is not int or total < 2:
        return None
    a, b = total//2, total-total//2
    return (total, a, b) if max(a, b) <= 150000 and max(a, b) <= 1500000 else None


def size(entry, risk, cost, balance):
    if not finite(entry, risk, cost, balance) or min(entry, risk, cost, balance) <= 0:
        return None, 'BUDGET'
    total = math.floor(min(.0025*balance/(risk+cost), 2.0*balance/entry)/.001)
    if total <= 0 or (total/1000.0)*entry < 5:
        return None, 'ENTRY_MINIMUM'
    if total > 150000:
        return None, 'ENTRY_MAXIMUM'
    result = split(total)
    return (result, None) if result else (None, 'PARTIAL_QUANTITY')


def levels(entry, pivot, atr, d, balance=10000.0):
    if not finite(entry, pivot, atr) or min(entry, pivot, atr) <= 0 or d not in (1, -1):
        return None, 'INVALID_LEVEL_INPUT'
    if not (pivot < entry if d == 1 else pivot > entry):
        return None, 'PIVOT_SIDE'
    sln = ticks(pivot-d*.15*atr, d)
    sl = sln/10.0
    if not (0 < sl < entry if d == 1 else sl > entry):
        return None, 'STOP_SIDE'
    risk = abs(entry-sl)
    if not stop_range(risk, atr):
        return None, 'STOP_RANGE'
    cost = (entry+sl)*(.00055+.0002)
    if not cost_gate(risk, cost):
        return None, 'COST'
    t1n, t2n = ticks(entry+d*1.5*risk, d), ticks(entry+d*2.5*risk, d)
    t1, t2 = t1n/10.0, t2n/10.0
    if not (t2 > t1 > entry if d == 1 else 0 < t2 < t1 < entry):
        return None, 'TP_GEOMETRY'
    if not all(.1 <= x <= 1999999.8 for x in (entry, sl, t1, t2)):
        return None, 'PRICE_LIMIT'
    q, error = size(entry, risk, cost, balance)
    if error:
        return None, error
    return {'direction':d,'entry_ref':entry,'sl_ticks':sln,'tp1_ticks':t1n,'tp2_ticks':t2n,
            'risk':risk,'cost':cost,'steps':q,'rr1':abs(t1-entry)/risk,'rr2':abs(t2-entry)/risk}, None


def decide(bars, fast, slow, atr, context):
    i = len(bars)-1
    if i < 0 or not START <= bars[i].time+STEP < END:
        return None, 'WINDOW'
    if i+1 < 200:
        return None, 'WARMUP'
    p, d, error = pullback(bars, fast, slow, atr, i)
    if error:
        return None, error
    points = [j for j in range(max(3, i-80), i-2) if confirmed_pivot(bars, j+3, d) == j and (bars[j].low < bars[i].close if d == 1 else bars[j].high > bars[i].close)]
    if not points:
        return None, 'PIVOT'
    j = points[-1]
    plan, error = levels(bars[i].close, bars[j].low if d == 1 else bars[j].high, atr[i], d, context.balance)
    if error:
        return None, error
    key = (d, bars[p].time)
    if context.daily_stop:
        return None, 'DAILY_STOP'
    if context.busy:
        return None, 'BUSY'
    if key in context.consumed:
        return None, 'CONSUMED'
    plan.update(pullback_id=bars[p].time, pivot_id=bars[j].time, signal_close=bars[i].time+STEP,
                decision_id=f'fixture:Research:C01:November2026:{bars[i].time}:{d}')
    return plan, None


def accept(plan, context):
    key = (plan['direction'], plan['pullback_id'])
    if key in context.consumed:
        raise ValueError('CONSUMED')
    context.consumed.add(key)  # Diagnostic acceptance only; no order/fill.


class State:
    def __init__(self):
        self.numeric = Reference()
        self.bars, self.fast, self.slow, self.atr = [], [], [], []

    def feed(self, t, values, context, confirmed=True):
        s = self.numeric.feed(t, values, confirmed)
        if s is None:
            return None, 'UNAVAILABLE'
        self.bars.append(Bar(t, *values))
        self.fast.append(s[0]); self.slow.append(s[1]); self.atr.append(s[2])
        return decide(self.bars, self.fast, self.slow, self.atr, context)
