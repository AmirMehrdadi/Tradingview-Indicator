# Phase 4C — Funding Lifecycle Accounting (Fixture-Only)

Run ID: `20261114T211449760645Z`. This is local engineering evidence, not acceptance on behalf of an independent reviewer. No publication is authorized by this report.

## Outcome and scope

The isolated Funding lifecycle component is implemented, and all 64 new synthetic tests pass. Guarded regression discovered 199 tests: **197 passed, 0 failed, 0 errored, 2 skipped**. The remaining existing regression component accounts for 133 passing tests and the two approved skips; none of the new tests was skipped.

**The full historical regression suite was NOT FULLY RE-EXECUTED.** Skipped cases are not newly passing. Existing 93-test Stage-0B and 135-test Phase 4A evidence remains preserved, rather than recreated. No historical simulation, profitability evaluation or funding-adjusted position replay was performed.

```text
PHASE_4C_IMPLEMENTATION = IMPLEMENTED
PHASE_4C_FIXTURE_TESTS = PASS
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
HISTORICAL_CALENDAR_COMPLETENESS = UNVERIFIED
FUNDING_ADJUSTED_HISTORICAL_RESEARCH = NOT_EVALUATED
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
2025_SELECTION = NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
FULL_RESEARCH_VALIDATION = NOT_EVALUABLE
```

## Baseline and unchanged authorities

Starting local HEAD and parent of the intended additive commit: `3cd8fecf2f816414f5a70972af63b99fc8ca17d5`, branch `main`. Baseline verification found 125 tracked files byte-identical before and after the work. The pre-existing untracked `.DS_Store` is excluded.

- Specification SHA-256: `b9f35d752f4748a68a7d7677112a67007acb94a3266d33bd8b763991ef89a1c6`.
- Official configuration SHA-256: `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37`.
- Numerical environment SHA-256: `ac190965edbb3a99c4d637f32a45d710ec5c69f74e003e68edc6458c10bb63d7`.
- Dependency lock SHA-256: `e71f67460d622ed4222e28f70fd5caeb5d6745072ba6bcd6fcd56d8eb432c51e`.

Both annotated objects and targets were checked locally:

| Tag | Annotated object | Target commit |
| --- | --- | --- |
| `v0.2.2-design` | `638ec6d99413c8dbc82a111209015953809ced08` | `ac8fc4bb9b66a59c7224aaec1630a594b41d7e80` |
| `v0.2.2-research-parameters` | `826b05146e99a5a87e9951da9b4e0ac2deea1d09` | `4bc7447755ef7a9dbd8832221f2ded5afc21401f` |

Frozen K=2.5, the twelve candidates, thresholds and partition boundaries remain unchanged. The 0.055% per-side taker fee and 0.02% per-fill research friction remain research assumptions; this component neither changes nor independently verifies account-specific rates. No tag is created or moved.

## Exact new-file inventory

- `research/funding_lifecycle/__init__.py`
- `research/funding_lifecycle/accounting.py`
- `research/funding_lifecycle/PROTOCOL.md`
- `tests/test_funding_lifecycle.py`
- `tests/run_phase4c_regression.py`
- `reports/funding_lifecycle/v0.2.2/20261114T211449760645Z/REPORT.md`
- `reports/funding_lifecycle/v0.2.2/20261114T211449760645Z/verification.json`
- `reports/funding_lifecycle/v0.2.2/20261114T211449760645Z/tests.log`

No existing tracked implementation, test, authority, evidence report or final README is modified. No raw or synthetic cache, private ledger, credential or binary dataset is included.

## Architecture and API contract

`FundingLifecycle(FixtureCalendar, Scenario).advance(Boundary)` accepts explicit immutable synthetic owners, entries, exits, settlements and Mark minutes. Owner identity includes fixture, C-ID, partition and authorized annual Period. The only supported provenance is `SYNTHETIC_FIXTURE_ONLY`; there is no real-data adapter or production command. The implementation reuses the existing Period authorization without modifying it.

Each boundary is validated and applied on a trial copy. Invalid input leaves the original state unchanged. Quantities are integer 0.001-BTC steps. Funding uses exact Decimal coefficient/exponent multiplication and addition, independent of ambient precision, with no unregistered rounding. The signs are `-q*mark*rate` for Long and `+q*mark*rate` for Short. Missing rates/prices are never zero-filled. A Fraction-based independent expectation, literal expectations, and low-precision stress test check the arithmetic.

Original and remaining quantities, unique fill and entry IDs, unique settlement/scenario attribution and cumulative exact sums are conserved. Closed trades and censored exposure remain distinct; no censored amount is transferred to a completed trade. Canonical serialized fixture state includes the explicit calendar, provenance, scenario and unchanged historical validity limits.

Pre-Funding execution snapshots and Funding attribution are distinct. Explicit synthetic `cash_after` inputs represent predeclared execution states; this component does not calculate execution proceeds, trading performance or sizing. Partial exits update execution cash but not settled-flat balance. Complete execution closure alone updates settled-flat and the frozen daily-stop comparison. Funding changes neither sizing/day-start/daily-stop nor entry eligibility. Margin behavior is not implemented or extended here; its shared marker remains identical across scenarios. Existing margin regression tests passed using synthetic inputs.

The full ordering remains PRIOR_BAR → PARTITION_END when applicable → UTC_DAY_RESET / initial flat partition state → FUNDING → SIGNAL_CLOSE → OPEN → INTRABAR. Prior-bar fills reported at t belong economically before Funding(t), and at midnight to the previous day. At annual end only PRIOR_BAR is processed; residual exposure is censored and excluded Funding/entry/OPEN payloads are not processed. A new annual instance has fresh 10,000-USDT synthetic snapshots, Flat exposure, empty attribution and reset IDs.

The alternate old-OPEN-exit precedence previews those predeclared fills on a shadow copy solely to determine Funding exposure. Shared execution state and SIGNAL_CLOSE occupancy remain in their original order. Thus a full old OPEN exit cannot free an earlier signal. New same-OPEN entries remain exempt. Explicit immediate OPEN exits and later PRIOR_BAR recognition of same-bar intrabar exits are retained without invented intrabar timestamps or price-extreme ordering.

## Six mathematical sensitivity scenarios

The common synthetic fixture has an old Long of 1000 steps (1 BTC), a 400-step OPEN exit, rate 0.01, and previous-minute OHLC 100/110/98/104. All six use identical immutable execution inputs and yield identical pre-Funding shared snapshots. These toy values are not historical observations or profitability metrics.

| Mark field | Old OPEN precedence | Funding steps | Selected Mark | Exact synthetic cashflow |
| --- | --- | ---: | ---: | ---: |
| close | `FUNDING_BEFORE_OLD_OPEN_EXIT` | 1000 | 104 | -1.04 |
| close | `OLD_OPEN_EXIT_BEFORE_FUNDING` | 600 | 104 | -0.624 |
| low | `FUNDING_BEFORE_OLD_OPEN_EXIT` | 1000 | 98 | -0.98 |
| low | `OLD_OPEN_EXIT_BEFORE_FUNDING` | 600 | 98 | -0.588 |
| high | `FUNDING_BEFORE_OLD_OPEN_EXIT` | 1000 | 110 | -1.10 |
| high | `OLD_OPEN_EXIT_BEFORE_FUNDING` | 600 | 110 | -0.660 |

Every proxy retains `APPROXIMATE_MARK_PREVIOUS_1M_CLOSE`, the selected field, minute linkage, `exact_tick=false` and `guaranteed_settlement_bounds=false`. Low/High are neither exact settlement prices nor guaranteed tick bounds. These six unit scenarios are not final Holdout sensitivity execution.

## Test execution and authorization

All accepted runs used the frozen wrapper, CPython 3.9.6 / NumPy 1.26.4 and the registered process controls. The unchanged environment-matching and PCG64 known-answer tests passed; no package installation or Bootstrap took place.

From the repository root, reproduce with:

```sh
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase4c_regression --focused
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase4c_regression
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase4c_regression --replay-hashes
```

| Accepted run | Discovered | Passed | Failed | Errored | Skipped | Exit |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Focused new fixture module under guards | 64 | 64 | 0 | 0 | 0 | 0 |
| All discovered regression and fixture tests under guards | 199 | 197 | 0 | 0 | 2 | 0 |

The focused tests are included in the guarded total; the counts must not be added together. Full output and exact skip reasons are in `tests.log`; parsed results are in `verification.json`.

The user explicitly authorized only these two skips, with old test files untouched:

- `tests.test_research_freeze.ResearchFreezeTests.test_all_evidence_verified_with_network_connections_disabled` — User-approved skip: freeze.verify_all reads and replays real Stage-0A caches; fixture-only restriction.
- `tests.test_stage0b.FeatureAndGuardTests.test_all_data_hashes_checked_before_any_price_parsing` — User-approved skip: preflight reads real Stage-0A manifests/CSV bytes before injected hash rejection; fixture-only restriction.

No extra test was skipped. No additional test needed prohibited data. Early harness setup attempts aborted on public baseline root files, directory-descriptor cleanup paths inside synthetic temporary trees and the interpreter's `file -b` fingerprint probe. These incomplete setup runs were not accepted regression runs. The final harness resolves those cases without reading real caches or expanding the skip list.

The guard runs discovery and tests with repository data access and socket traffic denied before access, repository writes denied and child processes limited to read-only Git / interpreter fingerprint probes. Temporary synthetic files used by unchanged tests are allowed outside the repository. Unknown prohibited access aborts the whole run. The new API is also tested with file/network operations mocked to fail, and explicit paths rejected before read. Direct guard classification tests demonstrate denials without performing the prohibited I/O. Both final accepted runs recorded zero real-data/network guard violations.

## Required coverage and boundary evidence

The following are actual passing tests in `tests.test_funding_lifecycle.FundingLifecycleTests`; `verification.json` records all 64 IDs. Several methods contain multiple independent subcases.

| Requested case | Representative test |
| --- | --- |
| A | `test_long_positive_rate_pays` |
| B | `test_short_positive_rate_receives` |
| C | `test_negative_rate_reverses_both_directions` |
| D | `test_explicit_zero_rate_is_not_missing_rate` |
| E | `test_exact_multiplication_has_independent_fraction_expectation` |
| F | `test_prior_partial_uses_remaining_quantity` |
| G | `test_prior_full_exit_receives_no_later_funding` |
| H | `test_prior_bar_end_timestamp_is_not_an_open_tie` |
| I | `test_open_partial_base_and_alternate_differ_only_in_funding_exposure` |
| J | `test_open_full_alternate_is_structural_zero_not_zero_rate` |
| K | `test_new_open_entry_is_exempt_from_same_timestamp_funding` |
| L | `test_same_bar_intrabar_exit_is_prior_bar_at_next_boundary` |
| M | `test_multiple_settlements_accumulate_independently_expected_total` |
| N | `test_duplicate_boundary_replay_fails_atomically` |
| O | `test_duplicate_exit_fill_and_overexit_and_orphan_fail` |
| P | `test_all_six_scenarios_have_independent_literal_expectations` |
| Q | `test_all_six_scenarios_have_independent_literal_expectations` |
| R | `test_invalid_ohlc_zero_negative_nonfinite_or_missing_price_fails` |
| S | `test_incomplete_duplicate_or_implicit_fixture_calendar_fails` |
| T | `test_off_15m_settlement_with_exposure_fails_without_inferred_order` |
| U | `test_normal_midnight_prior_closure_then_reset_then_funding` |
| V | `test_partition_end_censors_after_prior_exit_without_boundary_evidence_use` |
| W | `test_independent_next_annual_partition_resets_all_state_and_ids` |
| X | `test_initial_2023_mark_omission_is_strictly_zero_exposure_exemption` |
| Y | `test_censored_attribution_cannot_leak_to_another_completed_entry` |
| Z | `test_daily_stop_is_only_from_full_prefunding_execution_settlement` |
| AA | `test_deterministic_replay_all_scenarios_serializes_identically` |
| AB | `test_no_file_or_network_dependency_even_when_access_is_denied` |
| AC | `test_regular_cadence_does_not_upgrade_historical_calendar_status` |
| AD | `test_t16_prior_full_exit_then_new_open_entry_and_exit_no_double_counting` |

Additional passing tests cover compound PRIOR_BAR plus OPEN partial exits, initial-boundary exemption abuse, malformed ownership, orphaned/duplicate attribution, source/scenario mismatch, invalid proxy claims, simultaneous new entry/immediate exit, shared snapshots across all six scenarios and failed-boundary retry without duplicate Funding.

T16 passes for all six scenarios: an old PRIOR_BAR full closure, Funding(t), new same-OPEN entry and immediate OPEN full exit preserve both completed entries with no retroactive charge or double allocation. Other tests prove old-OPEN ties, partial/full alternate exposure and same-bar intrabar exit recognition separately.

UTC midnight tests confirm previous-bar closure before reset, partial-exit snapshot semantics and new-day OPEN recognition under both precedences. Annual-end tests confirm censoring versus final prior-bar completion and deliberate non-processing of excluded payloads. A subsequent independent annual instance starts with no old position, IDs or attribution. Initial 2023 Mark exemption is structural; prior entry and fabricated pre-Development Mark evidence are rejected.

## Exact deterministic replay evidence

Each scenario was executed twice from the same immutable fixture inputs through entry, Funding/OPEN partial exit and annual censorship. Serialized bytes matched within every pair. Six distinct scenario hashes were produced; only hashes, not synthetic ledgers, are persisted:

| Scenario | SHA-256 |
| --- | --- |
| `close:FUNDING_BEFORE_OLD_OPEN_EXIT` | `0d0eb422f65ee383530f1d0ad71fbaa57e3f93452e042ad8abadcd7f5427b96b` |
| `close:OLD_OPEN_EXIT_BEFORE_FUNDING` | `509e2a38e20a515654ae07b7d699082fb7b449c817b6285c02ef5143849f101c` |
| `high:FUNDING_BEFORE_OLD_OPEN_EXIT` | `7591e39258eae07289b81f4d68276d79b8e5f186ed14cc9df309e75cd012665a` |
| `high:OLD_OPEN_EXIT_BEFORE_FUNDING` | `ab049911eaabbe884b70aa859ac6f73e839f4e76bd700bc3a63d2364dc92b49e` |
| `low:FUNDING_BEFORE_OLD_OPEN_EXIT` | `fb4958093f1caf9db93e6a0d8719ea0c2298dd931ff2e93cff2a0f445be8d549` |
| `low:OLD_OPEN_EXIT_BEFORE_FUNDING` | `54db6921793d3f9e845138a7fee93e5f243660713c2c36f985bb37641080828e` |

## Source, evidence and preservation hashes

SHA-256 of every new source/test/protocol file:

| File | SHA-256 |
| --- | --- |
| `research/funding_lifecycle/__init__.py` | `3e4b5ceb91f8d185ce9fd982ce33f3d59cf2dc5b102232eaf49b675c73fcd0b7` |
| `research/funding_lifecycle/accounting.py` | `c189edd2e824335076ae94a9cc382835a4da90859c3dffa5e4ac768d79231b53` |
| `research/funding_lifecycle/PROTOCOL.md` | `be1d76b674be67a93bb027bd2d6b5da9cd4388856f45114fefa75b3b889d520e` |
| `tests/test_funding_lifecycle.py` | `8e5bf78551784cce7dabb5e8323dbb5df747ae4254090870ed7cdcc5b2bb57a5` |
| `tests/run_phase4c_regression.py` | `21908f083681e0088ed7981c0d9baae95cda7d34605b07ad575dcd5a3a42df27` |

`verification.json` records these, the aggregate source-map hash, test-log and report hashes, all 125 baseline file hashes, both tags, accepted test results, case mapping and deterministic fixture hashes. It excludes its own hash to avoid self-reference; the local Git commit identifies the complete evidence set.

All 125 previously tracked files were checked against both their initial SHA-256 inventory and their baseline Git blobs. This preserves the original specification/config/environment/lock, Stage-0B implementation and 93-test evidence, Phase 4A implementation and 135-test evidence, Phase 4B addendum and PARTIAL_DATA findings, and all old test files. No ignored historical snapshot or private ledger was opened to repeat those historical checks. Their existing hash records are retained; raw snapshot integrity was not reverified in this phase because real-cache access is prohibited.

The local additive commit is to be created only after final content/preservation review, with this baseline as its sole parent. The commit SHA is reported in the final task response rather than inserted into a self-referential committed report. No push, amend, rebase, reset or tag mutation is performed.

Final content review covered exactly the eight new files and their complete contents. No credential-pattern matches, raw market datasets, cache bodies, private accounting exports, unrelated files or binaries were found. The largest new file is below 32 KB. Pattern scanning supports this review; it is not a claim that arbitrary repository history or external storage was rescanned. All previously tracked bytes are unchanged.

## Remaining gates

Historical Funding data remains PARTIAL_DATA. Independently continuous effective-dated 2023/2024 BTCUSDT Funding calendar and temporary-exception coverage is still unproven. The missing initial 2023 Mark minute remains present in raw missingness records and classified NOT_REQUIRED_FOR_AUTHORIZED_ANNUAL_EXPOSURE; fixture mathematics does not repair that snapshot or validate the actual historical calendar.

Real Funding/Mark integration, evidence-complete net research, profitability assessment, TradingView execution/parity, Selection and final Holdout remain separate, unexecuted gates. Historical net research is NOT_EVALUATED; complete research validation remains NOT_EVALUABLE. No protected data or private ledger was accessed, no historical candidate path was executed, and no subsequent phase was started. Independent review is required before separately authorized publication.
