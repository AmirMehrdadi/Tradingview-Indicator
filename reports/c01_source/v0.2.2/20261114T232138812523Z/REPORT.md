# Phase 5B1 — offline C01 Baseline decision source

Baseline commit: `9d6ef94818ff1ddd7f0ef3b9e7de9789b662607c`, main, 141 tracked files. Local/remote main and both original annotated freeze tags matched before editing. This is a new independent, explicitly UNVALIDATED Pine v6 diagnostic source. No TradingView site/chart, compiler, runtime, live feed, raw cache or private ledger was accessed in this phase. No historical path, candidate selection or profitability evaluation occurred.

## Implemented contract

Explicit November-anchored 15m EMA20/50 and Wilder ATR14; strict trend and complete pullback/trigger sequence; strict confirmed 3/3 pivots and latest suitable pivot within 80 bars; structural stop, conservative integer tick rounding, inclusive stop range; frozen K=2.5 Research cost predicate; cost-inclusive sizing and leverage cap; minimum-order and quantity-max validation; whole-step TP1/TP2 split; frozen target geometry and rounded reward/risk reporting; stable UTC pivot/pullback IDs; confirmed-close and half-open-window ownership; missing/gap quarantine. No seed reset occurs on November 4.

The Research fee .00055 and friction .0002, historical instrument tick .10/BTC step .001, entry minimum notional 5, minimum step and current snapshot maxima/bounds are explicit assumptions copied from frozen metadata. No account rate or historical effectiveness is claimed. Raw values use binary64 floor/ceil without epsilon. Integer counts are retained and only rendered as ticks/10 or steps/1000. K has no UI override. Cost model is deliberately Research, not TradingView tick-friction Parity, despite the preserved November technical window.

Section 4.5 removes the old post-rounding TP1 minimum-R condition; no replacement threshold is introduced. Frozen 1.5R/2.5R raw construction and target geometry are implemented. Q is not part of C01 and is not introduced as a reward/risk filter.

## Context and scope limits

Source acceptance is disabled by default. Static synthetic balance, busy/pending occupancy and daily-stop inputs model explicit decision snapshots only. They never become an evolving position or financial ledger. Accepted diagnostics consume the direction-specific pullback ID but do not place or assert any order/fill. Failed/busy/stopped/disabled decisions do not consume IDs. No full indicator, real signal display, alerts, webhook, broker connection or account access exists. Only masked Data Window diagnostics are emitted, intended to align to the owning close with offset=1; actual alignment remains a runtime gate.

R/H/V/M/Q and other candidates, HTF requests, execution/position/margin accounting, actual PnL/Funding, manual signal-expiration UI and actual Parity are outside scope. Inactive H does not impose hourly readiness. Data predicates restrict arithmetic only; they do not establish platform-level data isolation. Phase 5A-V1's safe-environment blocker remains unresolved. The prior Phase 5A source and protocol are unchanged.

## Verification performed

35 new deterministic synthetic tests PASSED, with 0 failures, 0 errors, 0 skips and zero offline/data guard violations. Exact frozen environment verification passed. The accepted command was:

`PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b1_checks`

The runner executes only the new module. Historical regression tests were NOT rerun. No real snapshots or candidate paths are loaded. tests.log records full actual output. Fixtures include an accepted Long with literal SL/TP tick counts and IDs, mirrored Short, strict direction and trigger equalities, touch/depth and 2..5 ages, selected-pullback failure without fallback, pivot delay/ties/80-bar ownership/latest selection, invalid stop sides, inclusive stop and K boundaries, adverse tick rounding without epsilon, cost/sizing consistency, odd/even splits, whole-signal partial rejection, entry minimum/maximum constraints, closing-notional exemption, rounded TP1 R below 1.5 without an invented rejection, consumption/busy/daily semantics, missing/invalid data, UTC endpoints, anchored state, causal prefix behavior and deterministic replay.

Tests compare synthetic recurrence/predicate/pivot/sizing values with preserved research.indicators, stage0a.baseline and stage0b.model helpers, not historical engine runs. Literal expectations supplement those comparisons. The new reference is a pure synthetic decision implementation, not a Pine emulator. Static source safety checks do not claim parsing, compilation or runtime success. Source-level review compared new Pine branches with frozen spec sections 2–6/8.1 and preserved Python features/offer/size behavior. It supports the translation design with the explicit fixture-context limits above; independent review and actual Pine proof remain necessary.

## Evidence, preservation and next review

All 141 baseline tracked files match initial SHA-256 and their exact baseline Git blobs. Neither original annotated tag object nor target changes. No old file or final README is edited. Only the eight additive files listed in verification.json are included. Security review found no credentials, raw/synthetic cache exports, private ledgers, large binaries or unrelated additions. The pre-existing untracked .DS_Store is excluded. No push or tag mutation occurs.

verification.json records source/report/test hashes and Git blob identities plus the baseline inventory. It omits its own self-referential hash; its identity is bound by the local commit and verified after commit. The final response records the complete eight-file hash inventory. The normal additive commit SHA is reported there rather than embedded into its own contents.

The concise docs/phase5b1/VALIDATION_PROTOCOL.md explains the cost/quantity/price assumptions, fixture acceptance contract, exact reproduction command and later proof requirements. Real compiler and runtime tests require separate authorization and an independently demonstrated non-Holdout environment. Matching same-input Pine/reference booleans, IDs and grid counters must be exact; tolerance applies only to the frozen continuous numerical contract. Real dynamic snapshots require later authorized integration, never inferred fills from these diagnostics. Do not start Phase 5B2/5C or publish without authorization.

## Status

PRECHECK_STATUS = PASS
SOURCE_IMPLEMENTED = C01_DIAGNOSTIC_SOURCE_ONLY_UNVALIDATED
SYNTHETIC_FIXTURES = PASS
SOURCE_LEVEL_CONTRACT_REVIEW = PASS_WITH_EXPLICIT_SYNTHETIC_CONTEXT_LIMITS
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
PROTECTED_DATA_ACCESS = NONE
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
HOLDOUT_ACCESS_STATUS = LOCKED_NOT_ACCESSED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
