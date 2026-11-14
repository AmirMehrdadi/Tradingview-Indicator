"""Frozen-spec EMA/RMA/TR and strict, causally confirmed pivots."""
import math
from decimal import Decimal


def ema(values, length):
    alpha, previous, result = 2.0 / (length + 1), None, []
    for value in values:
        if value is None:
            result.append(None)
            continue
        previous = value if previous is None else alpha * value + (1.0 - alpha) * previous
        result.append(previous)
    return result


def rma(values, length):
    alpha, seed, previous, result = 1.0 / length, [], None, []
    for value in values:
        if value is None:
            result.append(None)
            continue
        if previous is None:
            seed.append(value)
            if len(seed) == length:
                previous = sum(seed) / length
        else:
            previous = alpha * value + (1.0 - alpha) * previous
        result.append(previous)
    return result


def atr14(candles):
    ranges = []
    for i, bar in enumerate(candles):
        ranges.append(bar.high - bar.low if i == 0 else max(bar.high - bar.low, abs(bar.high - candles[i-1].close), abs(bar.low - candles[i-1].close)))
    return rma(ranges, 14)


def confirmed_pivot(candles, i, direction):
    """At closed bar i, only j=i-3 can become newly available."""
    j = i - 3
    if j < 3:
        return None
    neighbors = list(range(j-3, j)) + list(range(j+1, j+4))
    if direction == "Long":
        value = candles[j].low
        strict = all(value < candles[k].low for k in neighbors)
    elif direction == "Short":
        value = candles[j].high
        strict = all(value > candles[k].high for k in neighbors)
    else:
        raise ValueError("Invalid direction")
    return (j, value) if strict else None


def round_stop(raw, tick_size, direction):
    tick = float(tick_size)
    if tick <= 0 or not math.isfinite(tick) or not math.isfinite(raw):
        raise ValueError("Invalid tick/stop")
    if direction not in ("Long", "Short"):
        raise ValueError("Invalid direction")
    ticks = math.floor(raw / tick) if direction == "Long" else math.ceil(raw / tick)
    # Retain the integer index; avoid reconstructing it through float division.
    return ticks, float(Decimal(tick_size) * ticks)
