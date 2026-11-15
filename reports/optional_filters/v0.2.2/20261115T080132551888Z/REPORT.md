# Phase 5B2 correction addendum — duplicate global HOUR

This additive correction is based on local `b83405831856543bd8b4ab299051554958bc98ee`, whose sole parent is `81695989f08021dd23a4e8a386d9023df548ea57`. Remote main matched that parent before work. Both original annotated freeze tags matched their approved objects and peeled targets. The tracked/staged worktree was clean; only pre-existing untracked .DS_Store was present.

## Finding and exact correction

Independent review identified identical global `const int HOUR = 3600000` declarations at committed lines 8 and 9. The committed source was inspected and the duplicate confirmed. The original source-level review missed this blocker. No TradingView compiler has been run, and this correction does not establish compilation success.

Exactly one duplicate HOUR line was removed. An exact byte transformation check confirms the Pine file equals the original committed bytes with only that single line removed. No filter, candidate, threshold, output, numerical recurrence, cost, parameter or execution behavior is intentionally changed. The previous Phase 5B2 report's source-design PASS must not be treated as evidence that the original source lacked compilation blockers. That historical report, verification.json and tests.log remain unchanged and this addendum records the correction.

## Regression evidence

One new test, `tests.test_phase5b2_filters.FilterTests.test_pine_global_constant_declarations_are_unique`, scans unindented global constant declarations, checks it actually finds declarations, and rejects repeated names. It is a narrow source regression, not a complete Pine language parser or compiler.

Before correction, the new test ran against a working-tree Pine source confirmed byte-identical to the original Git blob: 80 tests, 79 passed, 1 failed, 0 errored, 0 skipped, expected exit 1. The failure explicitly names HOUR. After the one-line correction the same guarded runner passed 80 tests, 0 failed, 0 errored, 0 skipped, exit 0. This includes all 35 unmodified C01 synthetic tests and 45 Phase 5B2 tests. Exact frozen numerical environment verification passed in both runs, with zero data/network guard violations. No historical suites or real caches were accessed.

Command for both runs:

`PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b2_checks`

The complete before/after logs are retained separately in this addendum. The old accepted test log remains historical evidence and is not overwritten.

## Additional read-only source scan

A line-oriented read-only scan inspected global constants, typed/untyped variables, tuple-bound names and function declarations. It excluded indented local scopes, treated top-level control flow and indicator/plot calls as non-declarations, and checked for unclassified top-level statements. It found 74 declarations, zero repeated global names, and zero unclassified top-level statements. Full names and line numbers are in static_scan.json. This scoped static result does not rule out other Pine syntax/type/compiler issues or certify runtime behavior.

## Preservation, integrity and security

All 149 pre-Phase-5B2 tracked files remain byte-identical to the original parent. Of the 157 files in the original Phase 5B2 commit, only the Pine source and its filter test file change; the other 155 are preserved, including all three original Phase 5B2 evidence files. Both original freeze tag objects and targets remain unchanged. No amend, reset, rebase or history rewrite is used. The corrective commit is a single normal child of the original Phase 5B2 commit; its SHA is reported separately to avoid self-reference.

verification.json records before/corrected source hashes, changed/added-file SHA-256 and Git blob SHA-1 identities, original baseline hashes, tag identities and preservation/test results. It omits its own self-referential hash; the full seven-file committed integrity inventory is verified after commit and provided separately. Only source, tests and non-sensitive correction evidence are included. No credentials, market data, caches, private ledgers, unrelated files or large binaries are included. .DS_Store is excluded.

No TradingView, real market data, protected cache, private ledger, Selection, Holdout, profitability or subsequent-phase work occurred. No GitHub push or tag mutation occurred. Independent review remains required, followed by separately authorized genuine Pine compilation/runtime work only in a proven safe environment. The safe-environment gate remains unresolved.

## Preserved statuses

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
HOLDOUT_ACCESS_STATUS = LOCKED_NOT_ACCESSED
