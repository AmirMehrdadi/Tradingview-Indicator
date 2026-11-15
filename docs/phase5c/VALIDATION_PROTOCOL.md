# Trading Signals V1 — UNVALIDATED — RESEARCH / MANUAL SIGNALS

This is an additive source-only Pine v6 indicator. Compilation, chart rendering,
alerts, persistence and numerical/execution parity have NOT been verified on
TradingView. No chart, market feed, protected cache or account was accessed.
This protocol describes intended source behavior and observed offline evidence;
it does not authorize loading the script onto an ordinary chart.

## Authority and separation

The frozen specification v0.2.2 and configs/research_v0.2.2.json remain authoritative.
Sections 3–6, 8.3, 9.0.1–9.0.3 and 10 govern timing, manual expiration, Research
execution, protected boundaries and validation. The entire approved Phase 5B3
Research/numerical source before its Data Window footer is copied byte for byte,
except the indicator declaration. The original probe and all 191 baseline files
are preserved unchanged. The new declaration uses overlay=true and explicit
four-line/four-label limits. A marked presentation boundary separates all UI and
notification logic; that layer does not mutate ResearchBook, its audit, numerical
state, pullback consumption or candidate selection.

The twelve fixed combinations remain B, BR, BH, BV, BM, BQ, BRH, BRV, BRM, BHV,
BRHQ and BRHVMQ. All price/quantity/risk/cost rules remain unchanged, including
K=2.5, .055% fee and .02% adverse Research friction. These remain research and
historical-instrument assumptions, not verified account rates. No experimental K
control is exposed. The separate future configurable-K requirement remains intact.

The diagnostic enable switch defaults false. The inherited explicit run_id defaults
phase5b3-pine-v1. Assign distinct non-secret run IDs when comparing independent
runs/instances, including this indicator and its predecessor. IDs are reproducible,
not automatically unique across instances. Candidate/input changes and platform
alert snapshots/restarts remain subject to actual execution validation.

## Approved presentation and ownership

Default presentation inputs show markers, levels and a compact top-right dashboard;
quality diagnostics are hidden. All are presentation-only. Explicit notification
enable is separate and defaults false. Disabling markers/levels/dashboard does
not disable an independently enabled, eligible setup notification or change the
Research path. With the diagnostic disabled, there are no accepted setup graphics
or notifications. A permitted dashboard can show a static DISABLED classification.

A marker is emitted only for an actual selected-candidate queue accepted at a
confirmed signal close, with a healthy current Research state and a new canonical
owner. LONG uses a tiny green upward triangle below its signal candle; SHORT a
tiny red downward triangle above. offset=0 keeps the marker on that owning signal
candle. A hypothetical next-open fill is never used as an earlier signal event.
Historical accepted markers remain historical event observations; they do not
represent still-active manual opportunities or actual positions. A decision
rejected before queueing has no marker. A later hypothetical margin rejection
does not erase its earlier valid queued signal or use future information to
change that historical marker.

Signal authorization is CLOSE-owned, as explicitly required by specification
9.0.2. The first permissible signal close is November 4 00:00 UTC; its owning
candle opens November 3 23:45 UTC. If that candle actually produces an accepted
signal, its marker belongs there, after its close is confirmed. That is the
explicit first-close ownership rule, not retrospective backdating or permission
for other warm-up signals. The marker's allowed set is owner candles with close
in [TRADE_START, TRADE_END), not a rule shifting it to the entry candle. Price
lines/labels start at the permitted signal CLOSE and never before TRADE_START.

Four frozen levels use the accepted book snapshot: entryRef directly, SL/TP1/TP2
integer ticks divided by 10, without new rounding, optimization or recalculation.
ENTRY_REF is yellow, SL red, TP1 blue, TP2 green. Small labels say SETUP and
ENTRY_REF (signal close), explicitly distinguishing it from a hypothetical adverse
next-open economic fill. Text uses decimal formatting only; numeric line prices
remain untouched. Text formatting is not a binary64 serialization/parity claim.

Only the latest setup owns level objects. Its old four lines/labels are deleted
before replacement objects are created for a new owner. Existing lines update
only their right endpoint; no old object's price is moved to a new trade. A line
initially projects one known-duration bar for visibility, using time arithmetic
only, then follows authorized confirmed closes. Every x endpoint is explicitly
clipped to [TRADE_START, TRADE_END-1ms]; extend.none prevents rightward leakage.
No future OHLC is requested or used for this geometric projection. Bounds here
refer to source anchor timestamps. Label pixel extents, overlap, text wrapping
and actual chart clipping have not been rendered or verified.

## Manual opportunity expiration and hypothetical status

Every accepted manual opportunity retains its own owner, signal-close timestamp,
two-bar deadline and eventual confirmed expiration time. Earlier opportunities
are processed before capturing a replacement owner. Replacing drawings therefore
does not lose, shorten or reset an earlier opportunity's manual deadline.

For signal close T, the first subsequent candle closes T+15m and does not expire
it; the second closes T+30m and records EXPIRED. Expiration uses only contiguous,
authorized, confirmed bars. It changes presentation records only: Research still
enters at the frozen next Open, manages the same quantities/protective levels,
and settles/censors under its original rules. No actual entry confirmation is
inferred. Actual position status is always REAL_POSITION_UNKNOWN.

An expired opportunity can retain the latest frozen levels while its separately
labeled hypothetical Research position remains pending/open. If it is expired
and Research is flat/rejected, its level objects are removed. Historical markers
remain accepted-signal observations. No actual account balance, performance,
manual execution confirmation, forced real exit or protective order is fabricated.

TP1 partial status requires matching canonical owner and signal close, OPEN,
hasFilled, zero leg-1 residual and a positive leg-2 residual. Full-close status
requires the same owner, filled entry, FLAT and exact total exited with zero
residual. Bar-wide filled/exit flags are deliberately not used: a prior trade
may fill and close on the same bar that queues a replacement. UNKNOWN is shown
for unavailable or unmatched status; available flat with no accepted setup says
NO SETUP. The dashboard explicitly separates Research, manual opportunity and
actual position rows, and shows C-ID/filter abbreviations and UNVALIDATED status.

The final authorized candle may finish an internal manual deadline at exactly
END, using that candle's permitted completed-bar timestamp. It creates no END
marker, line, label, alert or dashboard disclosure. Deadlines requiring later
candles remain unresolved internally; later-partition input is not read to expire
them. Research censoring/protective-order distinctions remain those of the frozen
probe. Removing drawings never cancels a Research or broker protective order.

## Masking and notification contract

DATA_START is November 1 2026 00:00 UTC, TRADE_START November 4 00:00 UTC and
TRADE_END December 1 00:00 UTC exclusive for signals/display. Numerical history
is not reset at TRADE_START. Confirmed hourly [1]/[4] offsets, owning-hour timestamp,
strict pivots, access anchoring and quarantine behavior are unchanged.

A floating dashboard is created only on the last chart bar in an authorized
current context with available, ordered visible-bar timestamps wholly inside the
close-owned display window. Unknown viewport metadata or a viewport including
forbidden owner bars deletes the table. It is also deleted outside the display
clock window or when hidden. Gapped/unavailable Research snapshots produce UNKNOWN;
levels are cleared. No global background/bar coloring is added.

chart.left_visible_bar_time/right_visible_bar_time are display metadata only.
Neither viewport checks, date masks nor object clipping establish platform-level
historical-input isolation. Rendering/empty future viewport behavior and the
actual platform evaluation of hidden history/request.security remain UNVERIFIED.
SAFE_TV_ENVIRONMENT is still UNVERIFIED. Do not open a TradingView chart or load
this source under this task. Any future platform validation needs separate
explicit authorization and a demonstrably permitted environment.

A single dynamic alert() call handles new LONG and SHORT setup notifications.
No additional combined alert stream or alertcondition is created, avoiding duplicate
streams and static-message dynamic-field limitations. The plain human-readable
message includes UNVALIDATED, selected C-ID, direction, signal-close UTC epoch
milliseconds, frozen entry_ref/SL/TP1/TP2, canonical setup ID, REAL_POSITION_UNKNOWN
and No order sent. It is not a broker/execution webhook payload.

Notification requires explicit enable, realtime source flag, confirmed accepted
queue, authorized close window, available/non-quarantined state, new signal-close
ownership and an unsent canonical owner. alert.freq_once_per_bar_close adds the
platform frequency request. No TradingView alert was created or sent. The intended
platform condition is the indicator's alert() function calls; actual alert setup,
server delivery and replay/reload semantics remain untested. Deduplication is
per source execution/owner, not an assertion of durable exactly-once delivery
across restarts, independent instances or separately created server alerts.
Do not configure execution webhooks or broker integrations.

## Resource bounds and offline evidence

Owned graphics are bounded at four lines, four price labels and one 2x8 table.
Markers use two plotshape series, not accumulating label IDs. The manual record
cap is 2592, the number of permitted 15m signal closes in the frozen 27-day window;
one monotonic accepted owner per close cannot exceed it. A forward expiry cursor
processes each record once. Capacity failure blocks presentation/notifications and
clears graphics without mutating the Research kernel. No record eviction is used.
The inherited 20,000-row Research audit cap/fail-closed behavior is unchanged.
These are source bounds, not observed TradingView memory/capacity evidence.
Any platform resource/runtime error invalidates the affected run.

The independent synthetic Presentation reference owns immutable input snapshots
and its own drawing/notification records, never an execution-model reference.
Literal expectations test dates, owners, directions, prices, deadlines and statuses.
A deterministic candidate stream is replayed through all 32 presentation-toggle
combinations; the Research serialization and decision list remain unchanged.
Static checks bind the entire approved kernel, UI gates, frozen snapshots,
endpoints, object cleanup, alert APIs, declaration uniqueness and conservative
reserved-name checks. None is a Pine compiler, chart render or runtime parity test.

Reproduce from repository root in the exact frozen environment:

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5c_checks
```

The runner verifies the frozen CPython/NumPy/PCG64 fingerprint and enables the
preserved deny-by-default audit guard. Its explicit allowlist runs all new tests,
all 197 prior Phase 5B1–5B3-Pine synthetic tests and 23 Phase 5A temporal tests.
No historical discovery/data runner is invoked. Full historical regression is
NOT RE-EXECUTED. No real market, protected cache, private ledger, Selection,
Holdout, Funding implementation or profitability evaluation is accessed/performed.
All 191 baseline Git blobs, configuration, specification and freeze tags remain
unchanged. One additive local commit and review package only; no push/Phase 5D.

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
