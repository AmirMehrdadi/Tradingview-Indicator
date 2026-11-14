"""Synthetic in-memory numerical reference, not a Pine emulator or data loader."""
from datetime import datetime, timezone
import math


def utc(s):
    return int(datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()*1000)


ANCHOR = utc('2026-11-01T00:00:00Z')
START = utc('2026-11-04T00:00:00Z')
END = utc('2026-12-01T00:00:00Z')
STEP, HOUR = 900000, 3600000


class Reference:
    def __init__(self, step=STEP):
        if step not in (STEP, HOUR):
            raise ValueError('Unsupported synthetic timeframe')
        self.step, self.n, self.last = step, 0, None
        self.fast = self.slow = self.atr = self.previous = None
        self.seed, self.poisoned = [], False

    def feed(self, t, values, confirmed=True):
        # Authorization before touching even a single OHLC value.
        if not ANCHOR <= t < END or not confirmed:
            return None
        if self.poisoned:
            return None
        if t != (ANCHOR if self.n == 0 else self.last):
            self.poisoned = True
            return None
        if len(values) != 4 or any(type(v) not in (int, float) or not math.isfinite(v) for v in values):
            self.poisoned = True
            return None
        o, h, l, c = values
        if not 0 < l <= min(o, c) <= max(o, c) <= h:
            self.poisoned = True
            return None
        tr = h-l if self.n == 0 else max(h-l, abs(h-self.previous), abs(l-self.previous))
        self.fast = c if self.n == 0 else (2.0/21)*c+(1-2.0/21)*self.fast
        self.slow = c if self.n == 0 else (2.0/51)*c+(1-2.0/51)*self.slow
        self.n += 1
        if self.n <= 14:
            self.seed.append(tr)
            if self.n == 14:
                self.atr = sum(self.seed)/14
        else:
            self.atr = (1.0/14)*tr+(1-1.0/14)*self.atr
        self.previous, self.last = c, t+self.step
        return (self.fast, self.slow, self.atr, tr, self.n)


def consumed_hour(execution_open, hourly):
    """hourly maps synthetic close times to (EMA, close, observation count)."""
    end = execution_open-execution_open % HOUR
    current, past = hourly.get(end), hourly.get(end-3*HOUR)
    if end < ANCHOR+HOUR or current is None or past is None or current[2] < 60:
        return None
    return (current[0], past[0], current[1], end, current[2])


def eligible(t, state, hour, confirmed=True):
    return bool(confirmed and ANCHOR <= t < END and START <= t+STEP < END
                and state is not None and state[4] >= 200 and state[2] is not None and hour is not None)
