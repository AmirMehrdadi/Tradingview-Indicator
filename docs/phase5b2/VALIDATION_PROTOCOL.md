# Phase 5B2 selected-candidate diagnostic — UNVALIDATED

This additive source preserves the previous Pine probes unchanged. It is not a
strategy, execution engine, live trading indicator or validated Pine program.
No TradingView access, web research or historical input is authorized here.

## Fixed registry and identities

Exactly one input-selected candidate runs at a time, default C01:

| ID | Frozen combination | Optional bit mask |
| --- | --- | ---: |
| C01 | B | 0 |
| C02 | B+R | 1 |
| C03 | B+H | 2 |
| C04 | B+V | 4 |
| C05 | B+M | 8 |
| C06 | B+Q | 16 |
| C07 | B+R+H | 3 |
| C08 | B+R+V | 5 |
| C09 | B+R+M | 9 |
| C10 | B+H+V | 6 |
| C11 | B+R+H+Q | 19 |
| C12 | B+R+H+V+M+Q | 31 |

Bit weights are R=1,H=2,V=4,M=8,Q=16. There is no free-form combination, extra
candidate, threshold control, K input, rank, optimizer or performance UI.
Consumption arrays belong only to the selected profile for the entire Pine run;
changing the candidate input restarts the script and initializes fresh state.
The Python reference explicitly namespaces consumption by candidate, direction
and pullback UTC ID, including when a synthetic helper context is shared.
Each Diagnostic instance owns a fresh synthetic snapshot/consumption context.

## Preserved C01 and numerical context

The new source copies the explicit Phase 5B1 chart recurrence, strict baseline
predicates, confirmed pivots, Research cost/stop/sizing, target geometry and
integer tick/step handling. No native ta.* fallback is added. The same initial
TR, EMA seeds, ATR mean seed, stop rounding, K=2.5 and quantity constraints apply.
The frozen Research fee .00055 and friction .0002, tick .10 and BTC step .001,
entry minimum notional 5, minimum quantity and maxima/price bounds remain stated
assumptions, not verified historical broker or account facts. Research and
TradingView tick-based Parity cost models are not interchanged.

The old post-rounding TP1 >=1.5R gate remains absent as required by section 4.5.
Q's opposing-level 1.5R check is an independent optional predicate; it does not
add a TP2 room constraint or modify the frozen target prices.

DATA_START=2026-11-01T00:00:00Z is the exact 15m/hourly numerical anchor.
TRADE_START=2026-11-04T00:00:00Z starts eligibility; no indicator resets there.
TRADE_END=2026-12-01T00:00:00Z is exclusive for signal close/next-open eligibility.
The first eligible close may be the 23:45–00:00 bar closing at TRADE_START.
Only confirmed execution bars can accept diagnostics. Missing anchor, invalid
OHLC and discontinuities permanently quarantine the affected context. No
pre-anchor numerical OHLC, volume, seed, prior close or pivot is incorporated.

Synthetic balance/busy/daily-stop inputs are static fixture snapshots, never an
evolving ledger. Acceptance is disabled by default. Accepted diagnostics alone
consume a direction-specific pullback; rejection, missing active data, disabled
mode, busy state or daily stop never do. No order, fill or position is inferred.
Inactive optional predicates cannot block C01 or another selected candidate.
All plots are masked Data Window fields with close-ownership offset=1, including
C-ID and bit mask. No live-use signal shapes, lines, labels, alerts or orders.
Actual plotted timestamp alignment remains unverified until authorized runtime.

## Optional numerical definitions

R uses explicit fourteen-valid-observation Wilder means for +DM/-DM and ADX.
The first DM is na; strict up>down and down>up tests make ties zero. ATR uses
its separate frozen initial TR convention. DI/DX handle the frozen zero cases;
ADX first becomes available on zero-based observation 27 for complete data.
R requires ADX>=20, EMA separation>=.25 ATR and current ATR<=2 times the median
of exactly the previous 96 valid ATR values. Current ATR is excluded. Median
is the arithmetic mean of sorted elements 47 and 48, with no rounding.

H independently seeds hourly EMA50 from the exact hourly anchor and quarantines
that context on missing anchor, gap or invalid OHLC. The requested expression
returns an already-offset tuple in HTF: EMA [1], EMA [4], Close [1], end [1],
count [1], with lookahead_on. No chart-merged value is shifted to fake HTF
confirmation. The 10:00–11:00 hour is first consumed by the 11:00–11:15 bar at
its close. A count>=60 and exact expected hourly end reject missing/stale data.
Long requires confirmed Close>EMA50>EMA50 three hours earlier; Short mirrors
strictly. Non-H profiles ignore H failure/readiness. The source may evaluate
its guarded requested context even when H is inactive; this supplies no extra
readiness gate and does not prove platform access isolation.

V uses current volume>=1.2*mean(previous 20 volumes), excluding current volume.
All 21 necessary volumes must be present and nonnegative. Pine missing values
are rejected through na checks; no zero substitution or filling is used. The
Python reference also explicitly rejects nonfinite numeric fixture values.
Bad volume affects only V, never OHLC quarantine or inactive-V candidates.

M independently seeds gain/loss RMA14, with the first change na. Both means
zero yield 50; zero loss/positive gain gives 100; zero gain/positive loss gives
0. Otherwise it uses the frozen RSI formula. Long >=55 and Short <=45 include
equality, with missing RSI rejecting only an active M predicate.

Q requires body<=1.2 ATR, range<=1.8 ATR and a confirmed opposing pivot within
80 bars. Long considers pivot highs above entry, Short lows below it. It chooses
the minimum positive directional distance and requires >=1.5 planned risk.
Missing, unconfirmed or wrong-side levels cannot satisfy it. No TP2 room rule.
Pivots retain the same strict 3/3 comparisons and confirmation delay as C01.

## Offline verification and limits

From the repository root:

    PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b2_checks

The dedicated runner checks the exact frozen numerical environment, installs the
existing deny-by-default offline/data guard with only the two diagnostic Pine
sources allowed for read-only static checks, runs the new optional-filter tests
and the preserved 35 C01 synthetic tests. No historical suite, real cache or
preflight that loads real candles is invoked. Preserved helpers are cross-checks
only on synthetic values. Literal expected seeds, boundaries, IDs, bit masks and
an all-five-predicates-passing fixture supplement helper comparisons.

The reference accepts authorized synthetic arrays only. Hours retains point-in-
time quarantine ownership so an appended bad future hour cannot rewrite an
earlier valid query. OHLC quarantine is separate from optional volume validity.
The pure selection helper can test all twelve profiles without running any
historical paths; per-instance diagnostic state is not shared across candidates.

Source review and Python fixture success do not demonstrate Pine parsing,
compilation, realtime rollback, security merging or numerical parity. The prior
safe TradingView environment gate remains unresolved. Date masks and source
branches do not restrict platform-level chart/security dataset retrieval.
Later real validation needs separate authorization, a proven non-Holdout
chart/request environment, exact source/config/input hashes, genuine compiler
output, first/last-window checks, historical/realtime/reload HTF checks and
same-input comparisons. Integer IDs/steps/ticks/booleans must match exactly;
only continuous values may use the frozen numerical tolerance. Static snapshots
must not be presented as full-path position/accounting parity.

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

Stop for independent review. No publication or Phase 5B3/5C/5D is authorized.
