# BTC Strategy V1 — source-only native parity — UNVALIDATED

No TradingView compilation, chart, Strategy Tester, market data or profitability
execution is authorized or performed. All runtime-dependent cases, particularly
T06/T07/T13/T17/T18/T22/T23, remain EXECUTION GATE — UNVERIFIED.

The strategy copies the approved chart numerical state, strict pivots, C01–C12,
optional predicates and HTF ownership. Its adapter uses native observed settled
flat balance, pending/active occupancy and daily stop. The sole decision-formula
model difference is the spec 7.2 Parity cost proxy:
fee*((entry_ref+d)+(SL+d))+2*d, d=N_ticks*syminfo.mintick. K remains 2.5. This is
EXPECTED_MODEL_DIFFERENCE_COST relative to Research's percentage proxy, not a new
filter or optimized threshold. No Research fill/haircut/Stop-first path drives
native order fills. Future Logic Parity requires identical inputs/state/costs.

Declaration properties are explicit: initial 10000, percentage commission .055,
50% long/short margin, no pyramiding, no every-tick/fill recalculation, no close
processing, no magnifier and zero trade-through assumption. slippage=0 and
PARITY_SLIPPAGE_TICKS=0 are matching UNVALIDATED placeholders, NOT official N.
PARITY_VALIDATED is permanently false; order enable defaults false. A later
explicitly authorized parity run must choose/freeze exact integer N in both
places, preserve all Strategy Properties and source/config hashes and record
symbol/tick/quantity/pointvalue mapping. Properties can be overridden by the
platform; no actual snapshot has been verified. currency.NONE uses chart quote
units, intended BTCUSDT USDT; historical unit mapping remains an explicit
UNVERIFIED instrument assumption. USD/USDT or contract/BTC equivalence is not proved.

At an accepted confirmed close, canonical run_id/Parity/C-ID/November2026/
signal_bar_open_utc/direction freezes entry, two leg and two OCA identities,
prices and integer quantities. Caller must choose a distinct non-secret run_id
for distinct compared runs; no automatic cross-instance uniqueness is claimed.
One entry and both exits are submitted immediately in that calculation. Each
exit has explicit qty, from_entry, frozen TP/common SL and its own oca_name.
strategy.exit's native implicit reduce grouping is used; there is no invented
oca_type argument. Independent names express the required two reservation groups;
actual reservation/activation semantics are NOT established by source inspection.
Brackets are never reconstructed after an observed fill.

Native open/closed trade IDs, quantities, prices, comments, commissions and clocks
provide observations, including entry/exit between close callbacks. Closed rows
are retained as primitive snapshots, not substituted Research fills. Remaining
steps are observed with an exact round-trip quantity check; mapping disagreement,
foreign/duplicate/reduced exits or quantity conservation violations invalidate new
entries without deleting adverse native executions or stripping protection.
TP1 classification uses the bracket's profit comment, not a price-path guess.
Forced/unknown exits are anomalies, not an invented Bybit liquidation diagnosis.
Actual native overfill/underfill, fee conventions and margin behavior remain gates.

No fill after submission is UNKNOWN, not a specific rejection. Pending occupancy
is retained without retries. Partial exits do not settle sizing balance or free
occupancy. Only observed full flat updates 10000+strategy.netprofit, applies the
one-percent realized stop and cancels that entry's two remaining children. No
performance metrics are calculated or plotted. Entry deviation/risk/notional
flags retain adverse fills. Native trade commission/profit conventions require
actual platform verification; no Funding is modeled.

The current completed bar's native executions are processed under its opening
UTC day before the closing boundary resets the next day. Delayed closed-row bar
ownership invalidates the adapter rather than pretending UTC parity. Pine fill
metadata, callback visibility and this attribution require genuine runtime tests.

The November 1 anchor, November 4 first CLOSE and December 1 exclusive new-entry
boundary are preserved. At END an unresolved pending entry alone is canceled to
prevent a later entry; its children are not canceled while exposure is unknown.
An existing position records CROSSED_WINDOW_END internally and retains its initial
protective brackets until observed flat. There is no forced close, fake censor
fill or entry after END. Adapter observation/protection may continue beyond END;
that implicit platform input exposure is part of SAFE_TV_ENVIRONMENT=UNVERIFIED.
No unauthorized post-window chart is loaded in this task. Plots are close-window
masked. No alert, webhook or broker transport exists.

Resource cap: 10000 retained native exit observations. Exhaustion marks the run
invalid, blocks new entries and retains protection; it is not platform capacity
proof. Native closed-trade tables remain the underlying observation source.
Source date predicates do not prove platform-level data isolation.

Coverage inventory: existing temporal/C01/filter/lifecycle/quantity/daily/window
fixtures already test frozen mathematics and Research partial-TP1/residual-stop
cases. Nine new static checks cover the genuinely new native declaration, order
calls, OCA IDs, observation and cancellation seams. They do not execute Pine or
claim emulator equivalence. No new Python trading engine is built. A thin Phase5D
allowlist wrapper reuses the existing guard/environment/loader infrastructure;
the old runner hardcodes its suite list and all 204 baseline files must remain
unchanged, so that original runner is not edited.

Focused: PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5d_checks --focused
Final: PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5d_checks

Only one comprehensive regression follows final source edits. Focused repetitions
and durations are disclosed in evidence; no packaging reruns or historical suites.
All compile, runtime, numerical parity, native execution and safe-environment
statuses remain UNVERIFIED; historical Funding PARTIAL_DATA; Selection/Holdout
LOCKED_NOT_ACCESSED. No push or next phase is authorized.
