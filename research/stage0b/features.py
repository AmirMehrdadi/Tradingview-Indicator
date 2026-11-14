"""Causal shared market features only; never shared candidate trading state."""
import bisect
import math
import statistics
from dataclasses import dataclass

from research.access import AccessDenied, Window
from research.indicators import ema, rma, atr14, confirmed_pivot, round_stop
from research.stage0a import baseline, risk_cost


def rsi14(closes):
    gains, losses = [None], [None]
    for previous, current in zip(closes, closes[1:]):
        delta = current - previous
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    result = []
    for gain, loss in zip(rma(gains, 14), rma(losses, 14)):
        if gain is None or loss is None:
            result.append(None)
        elif gain == 0 and loss == 0:
            result.append(50.0)
        elif loss == 0:
            result.append(100.0)
        elif gain == 0:
            result.append(0.0)
        else:
            result.append(100.0 - 100.0 / (1.0 + gain / loss))
    return result


def adx14(candles, atr):
    plus, minus = [None], [None]
    for previous, current in zip(candles, candles[1:]):
        up, down = current.high - previous.high, previous.low - current.low
        plus.append(up if up > down and up > 0 else 0.0)
        minus.append(down if down > up and down > 0 else 0.0)
    dx = []
    for p, m, tr in zip(rma(plus, 14), rma(minus, 14), atr):
        if p is None or m is None or tr is None:
            dx.append(None)
            continue
        positive, negative = (0.0, 0.0) if tr == 0 else (100.0*p/tr, 100.0*m/tr)
        total = positive + negative
        dx.append(0.0 if total == 0 else 100.0*abs(positive-negative)/total)
    return rma(dx, 14)


def regime_pass(adx, fast, slow, atr, past_atr):
    return (adx is not None and len(past_atr) == 96 and all(x is not None for x in past_atr)
            and adx >= 20 and abs(fast-slow) >= 0.25*atr and atr <= 2*statistics.median(past_atr))


def confirmed_hour_index(hour_ends, execution_bar_open):
    return bisect.bisect_right(hour_ends, execution_bar_open) - 1


def volume_pass(current, previous):
    return (len(previous) == 20 and all(math.isfinite(v) and v >= 0 for v in previous)
            and math.isfinite(current) and current >= 0 and current >= 1.2*(sum(previous)/20))


def momentum_pass(rsi, direction):
    return rsi is not None and (rsi >= 55 if direction == "Long" else rsi <= 45)


def quality_pass(body, candle_range, atr, risk, target_distances):
    return (risk is not None and bool(target_distances) and min(target_distances) >= 1.5*risk
            and body <= 1.2*atr and candle_range <= 1.8*atr)


@dataclass(frozen=True)
class Setup:
    index: int
    direction: str
    pullback: int
    pivot_index: object
    entry_ref: float
    atr: float
    sl: object
    sl_ticks: object
    tp1: object
    tp2: object
    risk: object
    cost: object
    stop_valid: bool
    cost_valid: bool
    levels_valid: bool
    filters: tuple

    @property
    def pivot_age(self):
        return None if self.pivot_index is None else self.index-self.pivot_index


@dataclass(frozen=True)
class Features:
    window: Window
    candles: tuple
    setups: tuple


def _validate_input(candles, window):
    window.validate()
    for i, bar in enumerate(candles):
        window.authorize_bar(bar.open_time)
        if bar.open_time != window.anchor+i*window.step:
            raise AccessDenied("FEATURE_INPUT_NOT_CONTIGUOUS_FROM_ANCHOR")


def build_features(candles, hourly, window, config):
    _validate_input(candles, window)
    if window.interval != "15":
        raise AccessDenied("STAGE0B_REQUIRES_15M")
    _validate_input(hourly, Window.annual(window.year, "60"))
    fast, slow = ema([b.close for b in candles], 20), ema([b.close for b in candles], 50)
    atr = atr14(candles)
    adx, rsi = adx14(candles, atr), rsi14([b.close for b in candles])
    hour_ema = ema([b.close for b in hourly], 50)
    hour_ends = [b.open_time+3_600_000 for b in hourly]
    lows, highs, setups = [], [], []
    tick = config["instrument_assumption"]["tick_size"]
    fee = config["cost_assumptions"]["taker_fee_rate_per_side"]
    friction = config["cost_assumptions"]["execution_friction_rate_per_fill"]
    for i, bar in enumerate(candles):
        for direction, points in (("Long", lows), ("Short", highs)):
            point = confirmed_pivot(candles, i, direction)
            if point is not None:
                points.append(point)
            while points and points[0][0] < i-80:
                points.pop(0)
        if i+1 < 200 or not window.start <= bar.open_time+window.step < window.end:
            setups.append(None)
            continue
        direction, p, rejection = baseline(candles, i, fast, slow, atr)
        if rejection:
            setups.append(None)
            continue
        points = lows if direction == "Long" else highs
        eligible = [(j, price) for j, price in points if (price < bar.close if direction == "Long" else price > bar.close)]
        pivot = eligible[-1] if eligible else None
        sl = ticks = tp1 = tp2 = risk = cost = None
        stop_valid = cost_valid = levels_valid = False
        if pivot is not None:
            raw = pivot[1] + (-0.15 if direction == "Long" else 0.15)*atr[i]
            ticks, sl = round_stop(raw, tick, direction)
            if (0 < sl < bar.close if direction == "Long" else sl > bar.close):
                risk, cost, ratio = risk_cost(bar.close, sl, fee, friction)
                stop_valid = 0.75*atr[i] <= risk <= 2.5*atr[i]
                cost_valid = ratio >= config["K_cost_stop"]
                sign = 1 if direction == "Long" else -1
                _, tp1 = round_stop(bar.close+sign*1.5*risk, tick, direction)
                _, tp2 = round_stop(bar.close+sign*2.5*risk, tick, direction)
                levels_valid = tp2 > tp1 > bar.close if sign == 1 else 0 < tp2 < tp1 < bar.close
        R = regime_pass(adx[i], fast[i], slow[i], atr[i], atr[i-96:i])
        k = confirmed_hour_index(hour_ends, bar.open_time)
        H = False
        if k >= 59:  # At least 60 HTF candles actually visible under the confirmed-only timing contract.
            H = (hourly[k].close > hour_ema[k] and hour_ema[k] > hour_ema[k-3]) if direction == "Long" else (hourly[k].close < hour_ema[k] and hour_ema[k] < hour_ema[k-3])
        previous_volume = [b.volume for b in candles[i-20:i]]
        V = volume_pass(bar.volume, previous_volume)
        M = momentum_pass(rsi[i], direction)
        opposite = highs if direction == "Long" else lows
        distances = [(price-bar.close if direction == "Long" else bar.close-price) for j, price in opposite
                     if (price > bar.close if direction == "Long" else price < bar.close)]
        Q = quality_pass(abs(bar.close-bar.open), bar.high-bar.low, atr[i], risk, distances)
        setups.append(Setup(i, direction, p, None if pivot is None else pivot[0], bar.close, atr[i], sl, ticks, tp1, tp2,
                            risk, cost, stop_valid, cost_valid, levels_valid, tuple(zip(("R", "H", "V", "M", "Q"), (R, H, V, M, Q)))))
    return Features(window, tuple(candles), tuple(setups))
