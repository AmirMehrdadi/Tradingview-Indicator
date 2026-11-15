# Phase 5B2 — frozen optional filters and twelve candidates

Baseline: `81695989f08021dd23a4e8a386d9023df548ea57`, main, 149 tracked files. Local and remote main, origin, sole allowed pre-existing untracked .DS_Store and both annotated freeze tag objects/targets were checked before editing. Only eight additive diagnostic/test/evidence files are introduced. No TradingView, public web, exchange API, market dataset, raw cache, private ledger or historical candidate run was accessed or executed. The remote Git query was read-only repository metadata, not public-web research.

## Implemented source contract

The new Pine v6 source is an UNVALIDATED diagnostic. It supports one fixed C-ID per run, default C01, with the exact frozen combinations below. Input changes restart diagnostic state; candidates do not share consumption across Pine runs. Python fixture selection namespaces consumed IDs by candidate/direction/pullback and gives each Diagnostic instance its own context. Disabled mode, inactive/failed active filters, missing inputs, busy state and daily stop cannot consume a pullback. Acceptance is synthetic diagnostic acceptance only, never an order or fill.

| Candidate | Combination | Optional mask R1/H2/V4/M8/Q16 |
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

R: strict-tie Wilder DMI14 and explicit RMA14 ADX; first DM unavailable, first ADX index 27. ADX>=20, EMA separation>=.25 ATR and current ATR<=2 times the median of exactly previous 96 valid ATR values. Current ATR is excluded; the even median is the mean of sorted positions 47/48.

H: independently anchored hourly EMA50, confirmed HTF offsets [1]/[4] within the tuple-producing HTF expression, lookahead_on, count>=60 and expected-hour-end freshness. Missing hourly anchor/gap/invalid OHLC quarantines the hourly context. The 10:00–11:00 hour is consumed first by the 11:00–11:15 execution bar at confirmed close. No shifting of chart-merged values substitutes for confirmation. H readiness cannot block a profile without H. The request may evaluate its guarded context when inactive; no runtime or platform access guarantee is claimed.

V: current volume>=1.2 times mean(previous 20), current excluded. Missing/invalid/negative volume fails only V, with no global OHLC quarantine. M: first close change unavailable, explicit gain/loss RMA14, flat RSI50, gain-only100, loss-only0, Long>=55/Short<=45. Q: body<=1.2 ATR, range<=1.8 ATR and closest strictly eligible confirmed opposing pivot within 80 bars, with distance>=1.5 planned risk. Q does not require TP2 room. It shares strict 3-left/3-right pivot confirmation and tie rejection with the baseline.

C01 retains the prior explicit chart initialization and baseline/stop/target/sizing predicates. Research fee .00055, friction .0002, K=2.5, BTC step .001, tick .10 and frozen instrument minima/maxima remain assumptions, not historical/account verification. No tick-based emulator cost substitution, K control or new threshold is introduced. Price/quantity counters remain integers, with no epsilon, intermediate indicator rounding or native ta.* fallback. The prior removed post-rounding TP1 >=1.5R condition remains absent.

Both 15m and hourly numerical contexts begin at 2026-11-01T00:00:00Z, never read pre-anchor numerical inputs, and do not reset on November 4. Signal-close ownership starts 2026-11-04T00:00:00Z (the preceding 23:45 bar may supply it) and ends exclusively at 2026-12-01T00:00:00Z. Hypothetical next open is the same continuous-market boundary and must also precede end. Current computation requires confirmed execution bars. OHLC failure/discontinuity quarantines rather than skips/fills. Data Window diagnostics are masked to that ownership window and offset toward the close; actual placement remains a runtime gate.

## Actual offline verification

Command: `PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b2_checks`

79 tests PASSED: 44 new optional-filter/candidate tests plus all 35 unmodified Phase 5B1 synthetic C01 tests. Failed=0, errored=0, skipped=0, guard violations=0. The exact frozen numerical environment check also passed. The runner uses the preserved existing deny-by-default guard and only allows the old/new Pine source for read-only static review. No cache-dependent historical suite is run. Preserved research helpers are used only with explicit synthetic values.

Coverage includes exact registry/bit masks, every active-filter failure for every candidate, all profiles passing from a common computed five-filter fixture, C01 unchanged fields and integer sizing, inactive-filter null bypass, per-candidate/shared-fixture namespacing, disabled/busy/daily non-consumption, nonconstant Wilder seed and ADX/RSI helper comparisons, strict DM ties and zero TR, ADX threshold/median boundaries, a non-vacuous prior-96 ownership test, hourly seed/offsets/boundary/60-count/stale/gap/invalid/prefix/future tests, volume counts/equality/nonconstant ownership/invalid values, RSI special cases and thresholds, nearest opposing Q level/bounds/strict pivots/missing/unconfirmed/expired levels/no TP2 rule, OHLC quarantine, warm-up/window/end/no reset, deterministic replay, and direct guard classifications without prohibited I/O.

One preliminary fixture run errored because an 80-hour synthetic hourly vector did not extend to its requested 83-hour boundary. The fixture was extended to 90 hours without changing any strategy rule. The accepted final log is preserved in tests.log; no compiler or runtime success is inferred. Python exercises mathematical reference behavior, not Pine syntax/rollback/security execution.

## Source review, security and preservation

Source-level contract review compared all optional predicates and the registry with original specification sections 3/4/5/5.1, the frozen config and preserved research/stage0b/features.py, alongside preserved C01 source/predicate/model rules. No faithful-translation design conflict was found. This is a source-design PASS only; it is not independent review approval, compilation proof or numerical Pine parity.

All 149 old tracked files were compared with their initial SHA-256 values and exact baseline Git bytes. Previous probes, frozen spec/config, engines, previous tests/reports, README and both annotated tags remain unchanged. No historical raw files were opened for preservation checks. The content audit covers exactly the eight additive files: no credentials, raw market inputs, cache bodies, private financial ledgers, large binaries or unrelated additions. .DS_Store is excluded.

Machine-readable verification records the baseline hash inventory, source/report/log SHA-256 and Git blob SHA-1 identities, expected tags, exact tests and safety declarations. Its own self-referential hash is omitted; the complete committed eight-file inventory is verified after commit and reported separately. The local commit SHA is reported in the final response rather than written into its own contents. No GitHub push or new tag occurs.

## Remaining gates

Static balance/occupancy/daily-stop fixtures never become an evolving account ledger. No historical paths, order execution, realized PnL, Funding, alert, broker connection, ranking, optimization or selection is implemented. The prior safe TradingView environment gate remains unresolved: source date predicates and request.security do not prove platform-level history isolation.

Later authorized testing must establish a non-Holdout chart/request environment, genuine Pine compilation, runtime rollback and historical/realtime/reload HTF observations, exact same-input comparisons and close-owned Data Window placement. Integer IDs/bits/steps/ticks/booleans require exact equality; tolerance applies only to frozen continuous numerical values. No such actions occur here. The new docs/phase5b2/VALIDATION_PROTOCOL.md gives the detailed contract and reproduction procedure. Stop for independent review; Phase 5B3/5C/5D and publication are not authorized.

## Status

PRECHECK_STATUS = PASS
CANDIDATE_REGISTRY = EXACT_C01_C12_SELECTED_ONE_AT_A_TIME
FILTER_R_IMPLEMENTATION = SOURCE_IMPLEMENTED_UNVALIDATED
FILTER_H_IMPLEMENTATION = SOURCE_IMPLEMENTED_UNVALIDATED
FILTER_V_IMPLEMENTATION = SOURCE_IMPLEMENTED_UNVALIDATED
FILTER_M_IMPLEMENTATION = SOURCE_IMPLEMENTED_UNVALIDATED
FILTER_Q_IMPLEMENTATION = SOURCE_IMPLEMENTED_UNVALIDATED
C01_REGRESSION_STATUS = 35_PRESERVED_SYNTHETIC_TESTS_PASS
SYNTHETIC_TEST_RESULTS = 79_PASS_0_FAIL_0_ERROR_0_SKIP
SOURCE_LEVEL_CONTRACT_REVIEW = PASS_SOURCE_DESIGN_ONLY_NOT_PINE_EXECUTION
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
HOLDOUT_ACCESS_STATUS = LOCKED_NOT_ACCESSED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
