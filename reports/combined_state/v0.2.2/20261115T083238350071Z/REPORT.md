# Phase 5B3 — combined offline state and candidate integration

This report covers an explicitly UNVALIDATED Python synthetic state reference. It does not claim a combined Pine state-machine implementation, TradingView execution or research validation. The user allowed a Pine source where practical; none is delivered because faithful combined Pine persistence/rollback, fills/accounting and boundary protection have not been established. Those parts remain explicitly NOT_IMPLEMENTED, rather than represented by a partial toy adapter.

Baseline: `e8232cc19a1d8374ccd6fee58771f858d26bedbb`, main, 162 tracked files. Repository identity/origin, local and remote main, clean tracked/staged tree and original annotated freeze tags were verified before implementation. Only pre-existing untracked .DS_Store was permitted. The read-only Git remote query is the required repository precheck; no market-data/web endpoint or TradingView was used.

## Stage A implementation and gate

The versioned research/fixture_state_v1 package defines typed SYNTHETIC_FIXTURE_ONLY Candle/Decision inputs, independent candidate paths and mutually exclusive FLAT/PENDING_ENTRY/OPEN states. Queued decisions freeze deterministic entry/bracket/OCA identities and integer leg reservations. Entry uses the next Open, never the prior Close. Entry_ref must equal the observed confirmed signal close. Opening margin rejection charges no fee, cancels reservations and retains the consumed accepted pullback. There is no actual order or broker connection.

The new Research lifecycle independently models raw-Open directional friction and fee, conservative target fills, gaps through Stop, known-Open fills before later extrema, remaining-position Stop-first intrabar ambiguity, TP1 partial versus full-flat settlement, quantity conservation, duplicate/over/under-fill rejection, ex-ante risk/notional ceilings and diagnostic actual-fill overruns. Margin uses remaining quantity/cash and processed prices only, never a later adverse extremum after definitive full closure. No liquidation algorithm is invented. A margin-model event invalidates research use; it is retained rather than deleting a filled trade.

Settled balance changes only on full closure. Midnight completes PRIOR_BAR economics before setting the next day's start and resetting the sticky one-percent daily stop. Partial results never settle into the shared snapshot. Window-end processing completes the last authorized bar and archives unfinished exposure as censored with its remaining bracket allocations, without an artificial exit or completed-trade classification. No end-boundary Open is read. New independent instances start Flat at 10,000 USDT. This is internal synthetic accounting, not a historical PnL/performance evaluation.

Prepared Stage A decisions are unit fixtures for already-validated signal plans. The kernel checks geometry, tick/step types, minima/maxima, cost floor, risk ceiling and notional ceiling; it does not regenerate indicators/ATR or require unit tests to use the maximum sized amount. Stage B's full feed computes the exact frozen decision sizing before queueing. The pure unit seam is not a real-data adapter or alternative trading rule. Fee .00055, friction .0002, K=2.5, BTC step .001, tick .10 and the preserved metadata constraints remain explicit Research/historical assumptions. No Funding is implemented or missing Funding set to zero.

Gate A passed before Stage B source implementation began. The initial 27 lifecycle tests passed; subsequent source review added observed-close ownership, invalid-fill prechecks and independent synthetic Engine cross-checks, with the final 31-test Gate A rerun passing before the final combined run. Gate A never failed. The tests verify Long/Short TP1→TP2, TP1→SL, Stop-first both-target ambiguity, odd/even reservations, broker rejection, gaps and immediate closure, daily stop/reset, partial midnight snapshot, window censorship, invalid inputs, conservation failures and deterministic replay. A literal synthetic fee calculation and preserved Stage-0B Engine synthetic-instance comparison supplement the new implementation. No historical ledger is read; comparison uses newly created in-memory toy instances only.

## Stage B integration and gate

CandidatePath owns separate lifecycle, numerical/hourly/volume histories and decision records for exactly one C01-C12 profile. The exact frozen registry and predicates are reused from the preserved pure Phase 5B1/5B2 references. No thirteenth candidate, altered threshold, experimental K or cost-model substitution is introduced. No feature is inferred from C01's fills for another candidate. Accepted and queued plans consume only their candidate/direction/pullback ID; rejected, disabled, busy, daily-blocked or active-filter-failed setups do not. A later entry-margin rejection is a separate already-accepted event and remains consumed.

The complete stream requires an exact November 1 numerical anchor and contiguous closed 15m inputs. Current bar OPEN/PRIOR_BAR fills and settlement/reset are processed before the signal-close snapshot. Dynamic sizing reads only that path's settled balance, occupancy, daily stop and consumed IDs. Indicator history is not reset on November 4. An unconfirmed bar has no effects; a future auxiliary hour is rejected before execution updates. Hourly inputs must already be completed by available chart time, while H still uses the execution-bar OPEN ownership rule. Invalid hourly data affects H only; bad volume affects V only. All data is synthetic.

Signal-close eligibility is [2026-11-04T00:00:00Z,2026-12-01T00:00:00Z), and its hypothetical next Open also precedes end. The initial permitted signal may use the bar opening at November 3 23:45. The full feed never accepts pre-November inputs. The explicit offer_decision unit seam accepts prevalidated synthetic plan/filter fixtures; it does not certify externally supplied feature values or replace full-feed numerical anchoring. Decision records are QUEUED_NOT_FILLED until a separate modeled ENTRY event exists. A later/future candle cannot rewrite the accepted decision.

Twenty integration tests passed. A constructed, deterministic 500-bar synthetic wave exercises the full numerical-decision/state path and produces modeled decisions and fills; the same fixture supplies twelve independent paths, without ranking or profitability metrics. Other fixtures cover all registry members, filter rejection, candidate-isolated consumption/state, dynamic own-balance snapshots, H availability, chronology, warm-up continuity, disabled/busy/daily gates, invalid data, end rejection and replay. No actual OHLC, Funding, Mark or protected dataset is used.

## Exact final checks

Final Gate A: 31 passed, 0 failed, 0 errored, 0 skipped. Final combined Gate B: 131 passed, 0 failed, 0 errored, 0 skipped = 31 state + 20 integration + all 80 preserved Phase 5B1/5B2 fixture tests. Zero guard violations occurred in both final runs, and exact frozen numerical environment verification passed. The 80 preserved tests include the duplicate-HOUR regression. Full historical regression and cache-dependent suites were NOT run.

Commands:

`PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_checks --stage A`

`PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_checks --stage B`

A preliminary Stage B attempt stopped at the guard when its static scan enumerated the preserved pine/ directory. That was a legitimate source-directory read, not a data/cache read. A narrow read-only allowance for that directory and its Pine files resolved the harness issue; protected-data/network denials were not relaxed. This aborted attempt is not represented as a passing Gate B run. No test was skipped or source invariant weakened.

Static review found no duplicate global names in the three preserved Pine sources (21,44,74 declarations respectively) and no duplicate top-level Python definitions/class methods in the new source/tests. All new Python parsed successfully. These are scoped static checks, not Pine parsing/compilation or a complete semantic proof. Independent review remains required.

## Preservation, security and package

All 162 baseline files match their initial SHA-256 and baseline Git blobs, including prior probes, original reports, frozen specification/config, engines and tests. Both original annotated tag objects and targets remain unchanged. Only additive artifacts are created. Existing .DS_Store is excluded. No raw dataset, private financial ledger, synthetic cache, credentials, large binary, final README change or unrelated file is included.

Internal synthetic balances/events are necessary to test lifecycle semantics. They are not historical ledger inspection or a profitability report. Serialized synthetic state is used only in memory for replay comparisons, never exported as a committed ledger. No Funding, selection, historical backtest, Bootstrap, Pine execution, actual trade or next phase occurs. No GitHub push or tag mutation is authorized.

verification.json records all new source/report/test hashes and Git blob identities except its own self-referential identity, the complete baseline inventory, tags and actual test evidence. After the single local additive commit, every committed added file including verification.json is bound to exact Git blobs and included in a review-only ZIP. The external plain-text manifest records all member SHA-256/Git blob SHA-1 identities, commit/parent, ZIP SHA-256, preserved baseline/tags and post-commit worktree. ZIP members are independently extracted and compared with committed bytes. Package paths and commit identity are reported in the final task response, avoiding self-referential report/commit hashes.

## Remaining unimplemented and unverified requirements

The Python fixture model and integration are implemented; a new combined Pine state-machine source is NOT_IMPLEMENTED. Specifically, Pine pending/active transitions, bracket-accounting state, Research fill ordering, settled/daily snapshots and post-window protective-order behavior have not been delivered or established. Research censorship is not a claim that actual Pine orders are protected beyond a display window. No real orders exist here. All three earlier Pine probes remain unchanged.

The safe TradingView environment, genuine compiler/runtime evidence, rollback and HTF merge observations, same-input numerical parity and broker-emulator execution parity remain open. Source dates cannot prove platform-level historical data isolation. Nothing here closes Funding calendar completeness or net-research validity. Stop for independent review; no Phase 5C/5D or publication.

## Status

PRECHECK_STATUS = PASS
STAGE_A_IMPLEMENTATION = PYTHON_SYNTHETIC_RESEARCH_KERNEL_IMPLEMENTED_UNVALIDATED
STAGE_A_TESTS = 31_PASS_0_FAIL_0_ERROR_0_SKIP
STAGE_A_GATE = PASS_OFFLINE_PYTHON_ONLY
STAGE_B_INTEGRATION = PYTHON_C01_C12_INDEPENDENT_PATHS_IMPLEMENTED_UNVALIDATED
STAGE_B_TESTS = 20_NEW_INTEGRATION_TESTS_PASS
STAGE_B_GATE = PASS_OFFLINE_PYTHON_ONLY
FULL_SYNTHETIC_REGRESSION = 131_PASS_31_STATE_20_INTEGRATION_80_PRESERVED
SOURCE_LEVEL_CONTRACT_REVIEW = PASS_PYTHON_FIXTURE_MODEL_ONLY_PINE_TRANSLATION_NOT_IMPLEMENTED
STATIC_SCAN_RESULTS = PASS_WITH_DOCUMENTED_LIMITATIONS
PROTECTED_DATA_ACCESS = NONE
PINE_STATE_MACHINE_SOURCE = NOT_IMPLEMENTED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
