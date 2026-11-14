# Phase 4A implementation and acquisition review

The Development-only acquisition and validation package is implemented, tested and executed. Snapshot integrity is verified. **Data readiness remains PARTIAL_DATA**, distinct from net-research validity, which was not evaluated.

Starting commit: `fd573b3d3b6f35f796defa74d2cbde00957f503c`. Both existing annotated freeze tag objects, the original specification/configuration, all frozen parameters and all Stage-0B tracked artifacts remain unchanged. Only the related `data/funding/` exclusion was added among previously tracked files. No Stage-0B private ledger was accessed or modified.

## Tests and actual retrieval

All **135 tests passed**, including the existing 93 tests and 42 new deterministic tests. New tests cover explicit bounded/reverse funding pagination, short/empty pages, out-of-page boundary overlap refusal, duplicate/conflicting/invalid settlements, annual/leap-year and UTC boundaries, historical cadence gaps and interval-change ambiguity, exact prior-minute linkage, Mark geometry/completeness, approximate proxy semantics, event phases, network failures/retries/403 circuit behavior, hashes/cache integrity, unauthorized cache/export rejection and immutable snapshots. Existing Stage-0B synthetic unit fixtures ran as regression tests; no real Development Stage-0B path was rerun.

The actual acquisition made **2,258 successful public API requests**: 66 Funding-history requests, including independent 14-day window checks, and 2,192 requests for necessary linked Mark minutes. No request failed. No raw full-year minute-price dataset was downloaded. All successful raw responses, normalized observations and request evidence are retained in ignored create-only snapshots.

| Year | Observed valid Funding settlements | Linked valid Mark minutes | Missing requestable Mark minutes | Unavailable Mark minutes | Off-15m timestamps | Status |
|---|---:|---:|---:|---:|---:|---|
| 2023 | 1095 | 1094 | 0 | 1 | 0 | PARTIAL_DATA |
| 2024 | 1098 | 1098 | 0 | 0 | 0 | PARTIAL_DATA |

Both annual Funding traversals match their independently partitioned 14-day re-queries. Observed timestamps match a regular eight-hour UTC grid across each year. No invalid/conflicting Funding records, invalid/conflicting Mark minutes, missing requestable Mark minutes or observed alignment anomalies were found. That is a result about the acquired observations; it is not a claim that independently dated historical schedule evidence has been established.

The unavailable minute is `[2022-12-31 23:59,2023-01-01 00:00)`, linked to the first 2023 settlement. It was never requested because it precedes authorized Development. This is a scope boundary, not an HTTP failure. Annual reset guarantees no carried position at that instant; the data snapshot nevertheless discloses the unavailable price rather than filling it or treating missing Funding as zero. The minute before the first 2024 settlement is in authorized 2023 and was acquired.

## Open prerequisite and interpretation

The conservative completeness interpretation used here distinguishes a complete traversal of the provider's returned historical rows from independently established settlement-calendar coverage. The allowed responses supplied historical observations and consistent re-queries, but no separately dated calendar/interval-change artifact. Observed modal cadence cannot on its own distinguish an omitted row from an interval change, and empty responses are not evidence of no settlement. Actual missing-settlement counts therefore remain **UNKNOWN**, not zero. The API-derived interval histograms and suspected-gap diagnostics remain visible in the annual manifests.

That historical calendar/coverage evidence remains the unresolved data-readiness prerequisite for certifying complete net-research input. No dates or rates were invented to close it. The first pre-Development Mark minute is separately unavailable within the authorized scope; no request for expanded historical access was inferred. Future exposure-specific Funding application, registered sensitivities and execution verification remain outside this phase. No data-only integrity PASS closes those gates.

Every retained Mark price is labeled **APPROXIMATE_MARK_PREVIOUS_1M_CLOSE**. Close supplies the prescribed proxy and the same minute's Low/High are retained for later sensitivities. These are neither exact settlement ticks nor guaranteed bounds. No cashflows or position outcomes were calculated.

## Hashes and commands

| Artifact | SHA-256 |
|---|---|
| Phase 4A executable source aggregate | `a416465e66dca7467ecb35b2e9470be89c40984becab61e584e23fd411334327` |
| Frozen official configuration | `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37` |
| 2023 Funding dataset | `de2fafb54ca13f8d11dcb220df43300a6c3fa09df4b4cedb8bbccec16a8a3e92` |
| 2023 Mark dataset | `5221bbcec75e21354cded5a90c6e2e9ac495c227590664c0d5d5bb6dd8bddeb3` |
| 2024 Funding dataset | `0342aa84d3507837678db7d672c57413d4013f40159646a6f3bf62a8e791f010` |
| 2024 Mark dataset | `88f53f379d5653c5ccaab87103f90e6397e9508fdcefd31d13bf41252d6885e3` |

`manifest.json` and both annual manifests contain exact source, configuration, environment, snapshot and raw-response hashes, request timestamps/bounds and explicit missing-data reasons. `verification.json` records independent linkage/geometry/inventory checks and test-source/log hashes. `tests.log` retains the complete passing test output. The unchanged environment is CPython 3.9.6 / NumPy 1.26.4 with its pinned PCG64 contract; no sampling or Bootstrap was run.

```
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m research.funding acquire
sh tools/research_python.sh -m research.funding verify 20261114T192333525994Z
```

Acquisition deliberately returned exit status 2 for PARTIAL_DATA. The independent offline verification returned PASS_SNAPSHOT_INTEGRITY_ONLY and retained the PARTIAL_DATA verdict. Reacquisition creates a new immutable run; offline verification reads the ignored local snapshot and performs no network request.

The local commit includes implementation, tests, the protocol, Git exclusion and non-sensitive evidence. Raw market datasets and local caches remain ignored. No 2025 Selection, 2026 Holdout, profitability evaluation, private financial-value output, Pine work, Bootstrap, real trading, final README change, new tag or GitHub push occurred.
