"""Descriptive opportunities only. No position, exits, returns, or K selection."""
from collections import Counter

from .access import AccessDenied, Window, iso
from .indicators import ema, atr14, confirmed_pivot, round_stop

PERCENTILES = (5, 10, 25, 50, 75, 90, 95)


def percentiles(values):
    ordered = sorted(values)
    if not ordered:
        return {str(p): None for p in PERCENTILES}
    result = {}
    for p in PERCENTILES:
        h = (len(ordered) - 1) * p / 100
        low = int(h)
        fraction = h - low
        result[str(p)] = ordered[low] + fraction * (ordered[min(low+1, len(ordered)-1)] - ordered[low])
    return result


def baseline(candles, i, fast, slow, atr):
    bar = candles[i]
    if i < 5 or atr[i] is None:
        return None, None, "INDICATORS_NOT_READY"
    if fast[i] > slow[i] and bar.close > slow[i]:
        direction = "Long"
    elif fast[i] < slow[i] and bar.close < slow[i]:
        direction = "Short"
    else:
        return None, None, "NO_BASELINE_DIRECTION"
    p = None
    for k in range(i-2, i-6, -1):
        b = candles[k]
        if atr[k] is None:
            continue
        depth = fast[k] - b.low if direction == "Long" else b.high - fast[k]
        if b.low <= fast[k] <= b.high and depth <= 0.75 * atr[k]:
            p = k
            break
    if p is None:
        return direction, None, "NO_ELIGIBLE_PULLBACK"
    if any(not (candles[k].close > slow[k] if direction == "Long" else candles[k].close < slow[k]) for k in range(p, i+1)):
        return direction, p, "EMA50_SEQUENCE_VIOLATION"
    trigger = (bar.close > bar.open and bar.close > fast[i] and bar.close > candles[i-1].high) if direction == "Long" else (bar.close < bar.open and bar.close < fast[i] and bar.close < candles[i-1].low)
    return direction, p, None if trigger else "TRIGGER_NOT_MET"


def risk_cost(entry_ref, sl, fee_rate=0.00055, slippage_rate=0.0002):
    risk = abs(entry_ref - sl)
    cost = (entry_ref + sl) * (fee_rate + slippage_rate)
    if risk <= 0 or cost <= 0:
        raise ValueError("Nonpositive risk/cost")
    return risk, cost, risk / cost


def describe(candles, window: Window, tick_size: str, config: dict):
    window.validate()
    if window.interval != "15" or config.get("K_cost_stop") != "UNSET":
        raise AccessDenied("Only the 15m Stage-0A profile with K=UNSET is authorized")
    for i, bar in enumerate(candles):
        window.authorize_bar(bar.open_time)
        if bar.open_time != window.anchor + i*window.step:
            raise AccessDenied("Analysis input must start at anchor and have no gaps/duplicates")
    closes = [b.close for b in candles]
    fast, slow, atr = ema(closes, 20), ema(closes, 50), atr14(candles)
    lows, highs, opportunities = [], [], []
    baseline_rejections, rejections = Counter(), Counter()
    all_atr = []
    evaluated = 0
    for i, bar in enumerate(candles):
        for direction, pivots in (("Long", lows), ("Short", highs)):
            point = confirmed_pivot(candles, i, direction)
            if point:
                pivots.append(point)
            while pivots and pivots[0][0] < i - 80:
                pivots.pop(0)
        if window.start <= bar.open_time < window.end and atr[i] is not None:
            all_atr.append(100 * atr[i] / bar.close)
        close_time = bar.open_time + window.step
        if not window.start <= close_time < window.end:
            continue
        if i + 1 < 200:  # Includes the current closed bar; annual anchor supplies 240.
            baseline_rejections["INSUFFICIENT_WARMUP"] += 1
            continue
        evaluated += 1
        direction, p, rejection = baseline(candles, i, fast, slow, atr)
        if rejection:
            baseline_rejections[rejection] += 1
            continue
        record = {"year": window.year, "direction": direction, "signal_bar_open_utc": iso(bar.open_time), "signal_close_utc": iso(close_time),
                  "entry_ref": bar.close, "pullback_open_utc": iso(candles[p].open_time), "atr14": atr[i], "atr_pct": 100 * atr[i] / bar.close,
                  "pivot_open_utc": None, "pivot_confirmed_at_utc": None, "pivot_age_bars": None, "sl_ticks": None, "sl": None,
                  "planned_risk_price": None, "stop_pct": None, "roundtrip_cost_per_btc": None, "risk_to_cost": None, "status": None}
        candidates = lows if direction == "Long" else highs
        pivot = next(((j, value) for j, value in reversed(candidates) if value < bar.close), None) if direction == "Long" else next(((j, value) for j, value in reversed(candidates) if value > bar.close), None)
        if pivot is None:
            record["status"] = "NO_CONFIRMED_PIVOT_ON_REQUIRED_SIDE"
        else:
            j, value = pivot
            raw_sl = value - 0.15 * atr[i] if direction == "Long" else value + 0.15 * atr[i]
            ticks, sl = round_stop(raw_sl, tick_size, direction)
            record.update(pivot_open_utc=iso(candles[j].open_time), pivot_confirmed_at_utc=iso(candles[j+3].open_time + window.step), pivot_age_bars=i-j, sl_ticks=ticks, sl=sl)
            if not (0 < sl < bar.close if direction == "Long" else sl > bar.close):
                record["status"] = "INVALID_SL_SIDE_OR_PRICE"
            else:
                risk, cost, ratio = risk_cost(bar.close, sl, config["fee_rate"], config["slippage_rate"])
                record.update(planned_risk_price=risk, stop_pct=100*risk/bar.close, roundtrip_cost_per_btc=cost, risk_to_cost=ratio)
                record["status"] = "STOP_TOO_SMALL" if risk < 0.75*atr[i] else "STOP_TOO_LARGE" if risk > 2.5*atr[i] else "STOP_RANGE_VALID"
        if record["status"] != "STOP_RANGE_VALID":
            rejections[record["status"]] += 1
        opportunities.append(record)
    summary = {"year": window.year, "status": "DESCRIPTIVE_ONLY", "K_cost_stop": "UNSET", "anchor_utc": iso(window.anchor), "start_utc": iso(window.start), "end_utc_exclusive": iso(window.end),
               "evaluated_signal_bars": evaluated, "baseline_rejections_by_bar": dict(sorted(baseline_rejections.items())), "rejections_after_baseline": dict(sorted(rejections.items())),
               "all_development_closed_bars_atr_pct": {"n": len(all_atr), "percentiles": percentiles(all_atr)}, "groups": {}}
    for name, rows in (("All", opportunities), ("Long", [x for x in opportunities if x["direction"] == "Long"]), ("Short", [x for x in opportunities if x["direction"] == "Short"])):
        pivot_rows = [x for x in rows if x["pivot_open_utc"] is not None]
        stop_rows = [x for x in rows if x["status"] == "STOP_RANGE_VALID"]
        summary["groups"][name] = {"raw_opportunities": len(rows), "confirmed_pivot_survivors": len(pivot_rows), "stop_range_survivors": len(stop_rows),
            "unique_pullbacks": len({x["pullback_open_utc"] for x in rows}), "rejection_reasons": dict(sorted(Counter(x["status"] for x in rows if x["status"] != "STOP_RANGE_VALID").items())),
            "pivot_age_bars": {"n": len(pivot_rows), "percentiles": percentiles([x["pivot_age_bars"] for x in pivot_rows])},
            "distributions": {}}
        for population, sample in (("raw", rows), ("pivot_available", pivot_rows), ("stop_range_valid", stop_rows)):
            summary["groups"][name]["distributions"][population] = {}
            for metric in ("atr_pct", "stop_pct", "risk_to_cost"):
                values = [x[metric] for x in sample if x[metric] is not None]
                summary["groups"][name]["distributions"][population][metric] = {"n": len(values), "percentiles": percentiles(values)}
    return summary, opportunities
