# Historical BTCUSDT Funding calendar — documentary gap-closure addendum

Evidence run: `20261115T194012Z`. Baseline: `3122897b1f4c47bf0219324a119f7961b52a5342`, sole parent `e0f94e4f22461f61bed42599c3d34ec702b927b7`, branch `main`, 214 tracked files. This is an additive continuation of Phase 4B, not a new roadmap phase or research permission.

**Task-local verdict: BLOCKED_EXTERNAL_CALENDAR_EVIDENCE.** No admitted primary evidence establishes either complete annual operating calendar together with its exception history. **Not sufficient for CALENDAR_EVIDENCE_CANDIDATE_FOR_INDEPENDENT_REVIEW. HISTORICAL_FUNDING_DATA = PARTIAL_DATA.** New sources add documentary context and another dated example, not continuous calendar coverage. This is a bounded search result, not a claim that the necessary record does not exist.

## Existing evidence reused without rerunning it

Phase 4A's unchanged committed manifests/report record 1,095 valid observed settlements and 1,094 linked previous-minute Marks for 2023, with zero missing requestable minutes and one unauthorized pre-Development boundary minute. For 2024 they record 1,098 settlements and 1,098 linked Marks, with zero missing requestable minutes. Annual pagination and independently partitioned 14-day re-queries agree; every observed settlement matches the hypothesized eight-hour grid. These statements reuse prior evidence; no raw snapshot was opened and no acquisition was repeated. True missing-settlement counts remain **UNKNOWN**, not zero.

Phase 4B already assessed 12 documentary source entries and 24 bounded document/metadata requests. Its S08/S09 instrument examples, S04/S05 archived generic explanations and interval-adjustment caveats are reused by committed identifiers and hashes. Their body caches were not reopened or fetched again. Observed consistency and unsuccessful searches do not certify an exchange calendar.

Phase 4C verified a fixture-only Funding lifecycle and six mathematical sensitivity scenarios. Its original evidence records 64 focused fixture tests and a guarded discovery of 197 passing / 2 approved skips; the historical regression was NOT FULLY RE-EXECUTED. Those are historical recorded counts, not newly executed tests or historical Funding application. No lifecycle implementation was rerun here.

The old boundary conclusion is preserved **verbatim** in `coverage_assessment.json`: `NOT_REQUIRED_FOR_AUTHORIZED_ANNUAL_2023_RESEARCH` in Phase 4B's boundary JSON; Phase 4C calls the same limited conclusion `NOT_REQUIRED_FOR_AUTHORIZED_ANNUAL_EXPOSURE`. At 2023-01-01 00:00 UTC the authorized annual path starts Flat before Funding; a new same-Open entry is exempt. Only that old-position exposure requirement is resolved. The absent `[2022-12-31T23:59:00Z,2023-01-01T00:00:00Z)` Mark remains absent in the original raw annotations. This does not establish raw or calendar completeness.

Mark classification remains `APPROXIMATE_MARK_PREVIOUS_1M_CLOSE`; Low/High sensitivity values are not exact settlement ticks or guaranteed bounds. No proxy values were inspected or repaired.

## New primary evidence and limits

| ID | Inspectable primary reference | What is documented | Coverage limitation |
|---|---|---|---|
| FC01 | [V5 changelog, immutable revision](https://github.com/bybit-exchange/docs/blob/918df41fd51d85b8ec1fced3e043eaba9098931d/docs/changelog/v5.mdx) | API release/schema history at commit 2024-12-12 08:57:17 UTC | Not a BTCUSDT production schedule/change register; no exhaustive exception guarantee; not year-end coverage |
| FC02 | [Instrument-document file history query](https://api.github.com/repos/bybit-exchange/docs/commits?path=docs/v5/market/instrument.mdx&since=2022-12-01T00:00:00Z&until=2025-01-01T00:00:00Z&per_page=100) | 56 returned file-history entries locate dated documentation revisions | Query result is mutable metadata; fewer than 100 results is not an exchange-event coverage guarantee; all 56 bodies were not fetched |
| FC03 | [February 2024 instrument example](https://github.com/bybit-exchange/docs/blob/208e13bc0447b0d520593b6872d025264d0a93ae/docs/v5/market/instrument.mdx) | BTCUSDT / LinearPerpetual / USDT example, fundingInterval=480 minutes | DOCUMENTED_FACT about an example; SUPPORTED_BUT_INCOMPLETE for the historical schedule; no effective operating interval or certified UTC alignment |
| FC04 | [Same revision's patch](https://github.com/bybit-exchange/docs/commit/208e13bc0447b0d520593b6872d025264d0a93ae) | Adds Funding-rate limit fields; the 480-minute example value remains patch context | API/schema change, not an announced Funding interval regime change; example response time is not effective-from |
| FC05 | Official repository Funding commit-message search, retained connector projection G04 | 16 discovery results, including Funding fields and wallet/feed terminology | No exhaustive index guarantee, no complete temporary-exception history or attributable retrospective confirmation |

The exact UTF-8 bytes of FC01 and FC03 independently match Git blob identities supplied by immutable commit metadata. Their SHA-256 values are respectively `b359304da51be1c39fa569150f0f916e86f6aa715c8b26deb399a5e1e0aec1e3` and `de6fb070272ce814df45f30f6cf0a61dc732375684e23bdba38a5a0aa9814975`. JSON metadata hashes identify connector-returned representations, not original HTTP wire bytes. The commit-search capture is explicitly a normalized connector projection. No archive capture timestamp is invented; no new archive lookup was performed. Publication/commit dates are never substituted for exchange-effective dates.

Search scope and limitations: 15 targeted queries in five search calls, plus 10 GitHub documentation/metadata connector calls (9 successes, 1 unsupported-route rejection, 7 distinct retained payloads). The supported commit-search tool replaced that rejected route. The last three focused announcement/help queries returned an empty combined response. Unrelated indexed snippets were discarded without opening their links or treating them as primary evidence. Search outputs were not all retained; the first call's result text was unavailable in the final working context and supplies no finding. There is no claim of exhaustive internet, announcement or Git-history review. No market-data endpoint was requested, including instruments-info; its text appears only inside public documentation.

## Exact annual coverage assessment

| Window (UTC, exclusive end) | Proven operating regimes/subintervals | Documentary classification | Exception coverage / missing settlements |
|---|---|---|---|
| `[2023-01-01T00:00:00Z,2024-01-01T00:00:00Z)` | None independently established as a continuous operating interval | UNVERIFIED annual calendar; prior examples SUPPORTED_BUT_INCOMPLETE | Complete exception history UNVERIFIED; missing count UNKNOWN |
| `[2024-01-01T00:00:00Z,2025-01-01T00:00:00Z)` | None independently established as a continuous operating interval | UNVERIFIED annual calendar; FC03/prior examples SUPPORTED_BUT_INCOMPLETE | Complete exception history UNVERIFIED; missing count UNKNOWN |

For each full window, requirements A–E and G remain open: all regimes, exact effective-from/to UTC boundaries, scheduled settlement times, temporary changes/additional settlements and complete exception/change coverage, with a defensible completeness guarantee. Requirement F (BTCUSDT LinearPerpetual USDT applicability) is documented for the illustrative examples only. The entire annual windows remain unverified for complete-calendar purposes; a dated example is not a positive-length verified subinterval. The eight-hour 00:00/08:00/16:00 grid remains an **ASSUMPTION** for independent calendar completeness. No accepted documentary contradiction or newly established extra settlement was found. That is not proof that none occurred. No affected correction interval or missing-data fetch is invented.

## DRAFT ONLY — technical inquiry for Bybit (NOT SENT)

Please identify an attributable, independently verifiable authoritative historical record for BTCUSDT Bybit Linear Perpetual, USDT settlement, for the complete windows 2023-01-01 00:00 UTC through 2024-01-01 00:00 UTC exclusive and 2024-01-01 00:00 UTC through 2025-01-01 00:00 UTC exclusive. Please provide every effective Funding interval, exact effective-from and effective-to UTC boundaries, scheduled UTC settlement times, and the complete list of temporary changes, exceptions, additional/cancelled/deferred settlements, including an explicit confirmation if that list is empty. Was the schedule continuously 480 minutes at 00:00/08:00/16:00 UTC for both years? Please state the authoritative historical configuration/change/settlement archive, its coverage guarantees, revision/capture identity and applicable product/symbol, or supply an attributable retrospective confirmation with the supporting historical record. No account records or private credentials are requested.

The smallest separately authorized next action is to obtain and independently review that complete primary historical record or attributable confirmation. This draft is not authorization to send it. Another market-data re-query or current instrument snapshot would not close the documentary gap. If future accepted evidence identifies a specific discrepancy, a separate authorization would be needed for any precisely bounded historical data request; none is proposed or executed on invented dates here.

## Scope, preservation and integrity

Only the eight files in this new addendum are added. Existing 214 tracked blobs/modes, all prior reports, frozen authorities, code, twelve candidates, K=2.5 and costs remain unchanged. Ignored documentation bodies are stored separately under `data/funding/calendar_evidence/v0.2.2/20261115T194012Z` and excluded from Git and the review ZIP. Original raw snapshots were not read, changed or rehashed; prior hashes are preserved via unchanged committed manifests, which is not a fresh snapshot verification. No market acquisition, private ledger, Selection/Holdout, TradingView, strategy execution, profitability, external support message, tag change or GitHub push occurred.

Actual test-runner executions: **0**. No historical regression, acquisition, lifecycle suite or old calendar verifier was run. Document integrity is not historical Funding validation. `verification.json` records the actual narrowly scoped check commands, exit statuses, counts and elapsed times. `SHA256SUMS` hashes the other seven addendum files and excludes itself; the external post-commit manifest hashes all eight committed files and the review ZIP without circular hashes.

Reproduction of committed evidence integrity (no market/cache runner):

```sh
git diff --check 3122897b1f4c47bf0219324a119f7961b52a5342 -- reports/funding_calendar/v0.2.2/20261115T194012Z
shasum -a 256 -c reports/funding_calendar/v0.2.2/20261115T194012Z/SHA256SUMS
python3 -m json.tool reports/funding_calendar/v0.2.2/20261115T194012Z/sources.json >/dev/null
python3 -m json.tool reports/funding_calendar/v0.2.2/20261115T194012Z/coverage_assessment.json >/dev/null
git diff --exit-code 3122897b1f4c47bf0219324a119f7961b52a5342 -- . ':(exclude)reports/funding_calendar/v0.2.2/20261115T194012Z/**'
git rev-parse v0.2.2-design 'v0.2.2-design^{}' v0.2.2-research-parameters 'v0.2.2-research-parameters^{}'
shasum -a 256 STRATEGY_SPEC_v0.2.2.md configs/research_v0.2.2.json
```

The local-only review ZIP contains committed addendum files only; public source bodies remain inspectable by immutable links and their separately ignored capture hashes. External review package identities are recorded outside the repository after committing.

**Final task-local verdict: BLOCKED_EXTERNAL_CALENDAR_EVIDENCE. HISTORICAL_FUNDING_DATA = PARTIAL_DATA.**
