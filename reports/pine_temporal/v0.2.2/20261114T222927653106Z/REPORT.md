# Phase 5A — Pine temporal isolation and HTF feasibility

Evidence is offline only. No Pine compiler, TradingView chart or market-data API was accessed. This is a representative diagnostic source probe, not the final indicator/strategy or a trading signal implementation. All TradingView-dependent gates remain UNVERIFIED.

Baseline: `20525875dda999de0f66ca0a61df6bc68f28a3b7`; local/remote main and both freeze tags matched before work. All 133 tracked baseline files remain byte-identical. K=2.5, candidates, costs, thresholds, engines, old tests and reports are unchanged. The only pre-existing untracked file is .DS_Store, excluded.

## Contracts and source-level findings

Exact data start is 2026-11-01T00:00:00Z, diagnostic signal-close eligibility starts 2026-11-04T00:00:00Z and ends exclusively at 2026-12-01T00:00:00Z. Both timeframe states start only on their exact anchor. No reset occurs at trade start. Initial TR uses H-L and no pre-anchor previous close. Explicit EMA20/50 first-close and RMA14 mean seeds avoid implicit ta.* state. Missing/invalid inputs or gaps quarantine rather than skip or zero-fill. Source-level review supports this design; actual runtime isolation is not demonstrated.

Hourly recurrence runs within security. Its tuple components are offset there: EMA [1] and [4], Close/end/count [1], with lookahead_on. This is the confirmed-offset expression pattern applied inside the tuple-producing function. No offset is applied to chart-merged values to manufacture confirmation. The 10:00–11:00 hour belongs first to the 11:00–11:15 execution bar, consumed at its confirmed close. Existing confirmed_hour_index in Python follows bar-open ownership; this probe does not alter that engine. Hourly count and end-timestamp freshness guard readiness. No unconfirmed chart-bar diagnostics are emitted.

Data Window diagnostics are additionally masked and shifted one chart bar toward the owning close timestamp; actual offset display alignment remains a runtime check. No project chart lines/labels/colors, trading alerts, entry/exit orders, Funding or profitability exist. This diagnostic does not implement full baseline predicates, all indicators, pivots or the execution engine. No global parity or strategy eligibility claim follows from its diagnostic readiness boolean.

The request.security offset pattern alone proves neither numerical anchoring nor platform access restriction. The platform may load older chart/request history even when the source ignores its OHLC. A dedicated permitted environment excluding Holdout must be established before any actual test. None was opened here. Lack of a demonstrated environment is an explicit outstanding access prerequisite.

## Documentation and later protocol

The new docs/phase5a/VALIDATION_PROTOCOL.md records six official TradingView v6 documentation links and the exact later validation steps. Offset HTF requests, function-local history, var rollback, confirmed chart bars and strategy timing were reviewed. Documentation support is source plausibility, not compiler or runtime evidence. The indicator does not set strategy-only calc_on_every_tick/calc_on_order_fills/process_orders_on_close properties; their frozen values are documented for future separately authorized strategy work.

## Actual offline checks

23 tests passed; 0 failed, 0 errored, 0 skipped. Exact frozen CPython/NumPy environment verification passed. Command:

`PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5a_checks`

The runner denies network and real-data access before reads, using the preserved existing guard with a narrow read-only allowance for this Pine source. It runs only new tests; no historical suite or cache was rerun. Zero guard violations occurred. The initial static source check incorrectly matched a substring in a comment; its token-boundary check was corrected before the accepted run. No Pine compiler result was inferred from that static check.

The synthetic reference tests cover A–O: initial 15m/60m anchor, EMA/RMA seed, na readiness, initial TR, 11:00 HTF transition, warm-up suppression, first permitted close, no trade-start reset, excluded end, pre-anchor independence, no native-state fallback, missing-data quarantine, deterministic replay and no I/O. Additional tests cover nonconstant Wilder seed/recurrence, prior-close TR gaps, nonfinite/invalid OHLC, missing anchor, discontinuity, unconfirmed bars, 60-hour minimum, stale/missing hours and future-hour independence. Pure reference behavior is not automatic correctness of the Pine source. The reference hourly state exercises EMA50 via independent timeframe initialization; Python does not emulate Pine rollback or security merging.

## Preservation and security

All 133 old files were compared with initial SHA-256 and baseline Git bytes. Neither frozen tag object nor target moved. No protected price data, real caches, private ledgers, broker accounts or TradingView charts were accessed. Only official read-only documentation was fetched. All new source/report files are reviewed for prohibited functionality, credential patterns and accidental datasets; raw data and temporary artifacts are excluded. No existing README or file is changed. No push or tag creation is authorized.

## Remaining blockers and evidence levels

Offline mathematical fixtures: PASS. Source-level isolation review: plausible explicit state/offset design, with no compiler proof. Pine compiler success: UNVERIFIED. Realtime rollback, historical/realtime merge behavior, exact anchor isolation and shifted Data Window placement: UNVERIFIED. Numerical Pine–Python and full execution parity: UNVERIFIED. Full trading validation is outside scope. The protocol requires an independently authorized permitted environment, actual compiler diagnostics, anchored same-input comparisons, historical/realtime/reload hourly-boundary checks and independent review. Do not view Holdout as a workaround. Historical Funding remains PARTIAL_DATA because calendar continuity and temporary exceptions remain unresolved; these numerical fixtures do not affect it.

## Status labels

PRECHECK_STATUS = PASS
PINE_PROBE_IMPLEMENTATION = SOURCE_PROBE_IMPLEMENTED_UNVALIDATED
PINE_ANCHOR_ISOLATION = UNVERIFIED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

## New source hashes

`pine/Phase5A_Temporal_Probe_UNVALIDATED.pine` SHA-256 `fdc961fe4be432f0569faa678bcbe1ecbf66536cd1b2de7def82f5d778b61084`
`tests/phase5a_reference.py` SHA-256 `31e27948babc7d9f89c88c0634c239ad8b27fd670c8388ad8642823cd0c00d24`
`tests/test_phase5a_temporal.py` SHA-256 `fc99dee4c4136e4756b8ef4ce4fb085e4a172b28dec835681e7dce633bb94b96`
`tests/run_phase5a_checks.py` SHA-256 `e3508a7af6566f9846b342e286c6a5ce97751de7976431708116b15b52859580`
`docs/phase5a/VALIDATION_PROTOCOL.md` SHA-256 `959bdcb5e83d756ea0cff90b8353d66e429adb57fda8298ec4f77d70bd9eb0c9`
