# Phase 4B — historical BTCUSDT settlement-calendar evidence addendum

Audit date: **2026-11-14 UTC**. Starting commit: `917927b379a8f1d3b93c1d7f88537060a6a3a1e0`. Scope: independently dated documentation and announcements compared with the existing 2023/2024 Development settlement inventories. No market-data acquisition, position simulation or private-ledger access occurred.

**Finding:** the evidence supports the observed eight-hour convention but does not independently establish a complete, continuously applicable BTCUSDT calendar or exception history for either year. Retain **PARTIAL_DATA**. Separately, the unavailable first boundary Mark minute is **not required for exposure in the authorized annual 2023 model**. That structural conclusion does not alter the raw snapshot or close the calendar prerequisite.

## Dated source-evidence table

All sources below were inspected. Git revisions are immutable references; publication labels on current pages are distinguished from independently archived payload dates. Detailed URLs, publishers, capture times, hashes and limitations are in `sources.json` and `captures.json`.

| ID / primary source | Verified date evidence | Claim and instrument scope | Historical period actually supported | Assessment |
|---|---|---|---|---|
| S01 — [Bybit legacy FundingApi](https://github.com/bybit-exchange/api-connectors/blob/cc021a371bde30c2fd282be9fdc8eef0ed0e362e/swagger-gen/csharp/docs/FundingApi.md) | File history last change: 2020-11-12; repository deprecation commit: 2021-11-24 | Legacy service describes settlements at 00:00, 08:00 and 16:00 UTC; no BTCUSDT-specific calendar | Versioned pre-Development wording only | Indirect support; obsolete service scope limits applicability |
| S02 — [Bybit archived Swagger](https://github.com/bybit-exchange/api-connectors/blob/cc021a371bde30c2fd282be9fdc8eef0ed0e362e/swagger.json) | Last file-change commit dated 2021-03-25 | Explicit eight-hour summary belongs to legacy Funding; LinearFunding is a separate service | Archived schema, no effective-period history | Scope limitation; do not import legacy semantics into V5 |
| S03 — [Bybit Learn current page](https://www.bybit.com/en/learn/bybit-guide/what-is-the-funding-fee) | Displays 2021-11-10; retrieved HTML also contains CMS update metadata dated 2025-06-18 | General perpetual explanation with a BTCUSDT illustration | Current retrieved wording; the original label does not date all current text | Insufficient alone for historical applicability |
| S04 — [Bybit Learn archived capture](https://web.archive.org/web/20230604184133id_/https://learn.bybit.com/bybit-guide/what-is-the-funding-fee/) | Capture: **2023-06-04 18:41:33 UTC**; payload matches CDX digest | General eight-hour convention, symbol-specific intervals and possible adjustments; BTCUSDT appears in an example | Wording at that capture, not a continuous operating interval | Independently dated indirect support |
| S05 — [Bybit Learn archived capture](https://web.archive.org/web/20240712172746id_/https://learn.bybit.com/bybit-guide/what-is-the-funding-fee/) | Capture: **2024-07-12 17:27:46 UTC**; payload matches CDX digest | Same general convention and adjustment caveat | Wording at that capture only | Independently dated indirect support |
| S06 — [V5 instrument documentation](https://github.com/bybit-exchange/docs/blob/a2fe2fd86ca67a514f089ef808a66a77a18ddbd1/docs/v5/market/instrument.mdx) | Commit: 2022-12-30 06:30:37 UTC | Linear example has a 480-minute interval but is **ETHUSDT** | Documentation version only | Different symbol; not BTCUSDT start-of-year proof |
| S07 — [V5 Funding-history documentation](https://github.com/bybit-exchange/docs/blob/5b5123d5ce986b7c0079a72bbc3607507c64eaea/docs/v5/market/history-fund-rate.mdx) | Commit: 2023-12-18 16:07:41 UTC | Intervals are symbol-specific; instrument information is referenced | Schema wording at that revision | Does not supply historical instrument settings |
| S08 — [V5 instrument documentation](https://github.com/bybit-exchange/docs/blob/5b5123d5ce986b7c0079a72bbc3607507c64eaea/docs/v5/market/instrument.mdx) | Commit: **2023-12-18 16:07:41 UTC** | BTCUSDT / LinearPerpetual / USDT example has `fundingInterval=480` minutes | Dated documentation example, not a recorded effective-period instrument snapshot | Symbol-specific indirect support |
| S09 — [V5 instrument documentation](https://github.com/bybit-exchange/docs/blob/af79c07e920e87296646e75efd5b89d99b75f344/docs/v5/market/instrument.mdx) | Commit: **2024-12-05 15:21:34 UTC** | BTCUSDT example again has a 480-minute interval | Documentation example at that revision only | Agrees with observations; does not certify the full year |
| S10 — [Bybit USDCUSDT interval-change notice](https://announcements.bybit.com/en/article/adjustment-of-funding-rate-interval-upper-and-lower-limit-of-funding-rate-for-usdcusdt-perpetual-contract-blt5761d7aac6282f7b/) | Publisher date: 2023-03-11; stated effective time: **16:00 UTC** | A funding-interval change for **USDCUSDT** | That announced different-contract event | Excluded from BTCUSDT coverage; demonstrates the scope error in assuming all contracts were immutable |
| S11 — [Bybit dynamic-frequency press release](https://www.bybit.com/en/press/post/bybit-launches-dynamic-settlement-frequency-system-for-perpetual-contracts-bltcd0548e9d1b5c84a), [original notice](https://announcements.bybit.com/en/article/bybit-to-introduce-automatic-funding-rate-adjustment-for-perpetual-contracts-blt2c875cbad4b89667/) | Published 2025-10-29; feature effective 2025-10-30 08:00 UTC | Automatic adjustment feature initially excludes BTCUSDT | Prospective 2025 rollout only; the pages describe the same event | Later context, not retroactive proof or independent corroborating histories |
| S12 — [Internet Archive availability/CDX metadata](https://web.archive.org/cdx/search/cdx?url=learn.bybit.com%2Fbybit-guide%2Fwhat-is-the-funding-fee%2F&output=json&filter=statuscode%3A200&from=2022&to=2024&collapse=timestamp%3A6&limit=24) | Retrieved 2026-11-14; identifies exact capture timestamps and payload digests | Archive discovery and payload identity | Dates of captured documents, not exchange operations | Metadata only; a requested lookup date is not the returned capture date |

The 2023-12-31 availability lookup returned a nearest capture from July 2024; the 2024-12-31 lookup returned March 2025. Neither was misdated as the requested date. The June 2023 capture was found through CDX and fetched separately. Both admitted archived bodies match their recorded SHA-1/base32 payload digests. The June 2023 payload is gzip encoded; its raw and decoded SHA-256 values are separately identified. The nearest March 2025 replay was not fetched.

## Comparison with the preserved Development inventories

| Year / settlement ownership window UTC | Observed valid settlements | First / last observed settlement UTC | Gaps / extra points relative to eight-hour hypothesis | Observed off-15m settlements | Independently proven continuous calendar coverage |
|---|---:|---|---:|---:|---|
| 2023: `[2023-01-01,2024-01-01)` | 1095 | Jan 1 00:00 / Dec 31 16:00 | 0 / 0 | 0 | Not established for the full window |
| 2024: `[2024-01-01,2025-01-01)` | 1098 | Jan 1 00:00 / Dec 31 16:00 | 0 / 0 | 0 | Not established for the full window |

Every observed consecutive gap, including the cross-year gap, is eight hours. The BTCUSDT documentation examples' 480 minutes agree with that spacing. Original annual/re-query agreement and linked Mark counts remain 1094 for 2023 and 1098 for 2024. No direct contradiction between an admitted BTCUSDT claim and the observed timestamps was established. S10 concerns another contract and is not a BTCUSDT contradiction.

These are checks of the observed inventory and its consistency with documents. They do not detect settlements absent from every historical API response, prove no temporary interval change occurred, or turn unsuccessful announcement searches into negative evidence. Actual missing-settlement counts remain **UNKNOWN**, not zero. No assertion of zero missing settlements is made from a zero hypothesis-grid gap count.

For **each whole annual window above**, the unresolved evidence is a verifiable primary BTCUSDT linear-perpetual calendar or effective-dated interval/change record covering the entire period, including temporary exceptions, independently of the queried Funding-history rows. None of the admitted documents certifies those continuous intervals. Documentation examples and dated general wording improve support, but do not close that gap. The search was bounded and is not claimed exhaustive.

## Separate first-boundary Mark verdict

At `t0=2023-01-01 00:00 UTC`, the frozen contract gives a structural proof of **no authorized old-position exposure**:

1. Section 9.0.2 resets the annual path Flat with no pending orders or carried position; warm-up carries indicators, not positions.
2. Section 8.3.1 places the annual reset before Funding, and Funding before SIGNAL_CLOSE and OPEN.
3. Even a signal whose candle closes exactly at `t0` can create its first entry only in the later OPEN phase. Section 7.3 excludes a new entry at that same Open from the settlement, under both registered event-order scenarios.

Therefore the old quantity subject to the initial settlement is **zero for every one of the twelve authorized annual paths**, without inspecting any ledger or simulating a trade. The prior minute `[2022-12-31 23:59,2023-01-01 00:00)` is **not required for exposure-specific Funding input in this annual model**. No pre-2023 market price was requested or read, and no Mark value or rate was invented.

Raw snapshot completeness remains a separate fact: that minute is unavailable and the original annotations remain untouched. This conclusion resolves its exposure-specific necessity, not calendar completeness or Funding for any later trade. It does not grant access outside Development. The overall unresolved data prerequisite is the historical BTCUSDT calendar/exception coverage identified above.

## Integrity, hashes and reproduction

Only this versioned evidence addendum is added to Git. Existing code, raw snapshots, manifests, reports, configuration, original specification, README and both annotated tags remain intact. Full external source bodies are cached separately under the already ignored `data/funding/calendar_evidence/v0.2.2/20261114T195000Z/`; they are not committed or republished. The capture log records 24 document/metadata requests, including one failed locale route, and no market-data requests. There was no Funding/Mark reacquisition.

- `sources.json`: exact source URLs, publishers, date basis, scope, supported period and assessment.
- `captures.json` and `SOURCE_SHA256SUMS`: source-body SHA-256, Git blob identities, archive digest checks, retrieval status and local cache provenance.
- `inventory_comparison.json`: input-dataset and timestamp-inventory hashes, annual comparison and explicit unresolved windows.
- `boundary.json`: the separate structural boundary conclusion and its specification references.
- `baseline_files_sha256.json`: all 113 previously tracked files, bound to the starting commit.
- `verification.json`: relevant offline integrity checks; historical test evidence is checked, not rerun.

From the repository root, with the preserved local snapshots/source cache:

```sh
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh reports/funding_calendar/v0.2.2/20261114T195000Z/verify_evidence.py
shasum -a 256 -c reports/funding_calendar/v0.2.2/20261114T195000Z/SHA256SUMS
shasum -a 256 -c reports/funding_calendar/v0.2.2/20261114T195000Z/SOURCE_SHA256SUMS
git diff --exit-code 917927b379a8f1d3b93c1d7f88537060a6a3a1e0 -- README.md .gitignore STRATEGY_SPEC_v0.2.2.md configs research research_freeze tests reports/funding reports/stage0b
```

The evidence verifier is an offline audit artifact in this addendum, not a research-engine change. It hashes original files, checks source/capture identity, compares authorized timestamp inventories and checks the frozen reset/phase references. It contains no network transport or position simulation. No full trading test suite was run in Phase 4B; the original 135-test PASS evidence remains intact. No 2025+ price/Selection data, Holdout, financial ledger, profitability metric, Pine, real order or new tag was accessed or produced. No GitHub push occurred.

**Final data verdict: PARTIAL_DATA.** Independent continuous BTCUSDT settlement-calendar/exception coverage remains unestablished for both annual windows. The first 2023 boundary Mark minute is no longer an exposure-specific prerequisite under the frozen annual reset contract; its raw-snapshot absence remains honestly recorded.
