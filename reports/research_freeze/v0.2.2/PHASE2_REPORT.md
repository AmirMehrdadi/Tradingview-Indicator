# Phase 2 verification and release record

All mandatory pre-tag Research Parameter Freeze checks passed. The record becomes effective through annotated tag `v0.2.2-research-parameters`; resolve that tag for the final commit hash. The report does not embed its own containing commit hash.

| Required condition | Executed evidence | Result |
|---|---|---|
| Preserve design/specification | Original design commit/tag object, specification bytes and SHA-256 verified | PASS |
| Verify completed Phase 1 | Original source/config hashes, 40-test recheck, offline Stage-0A replay, eight saved reports verified | PASS |
| Verify Development inputs | Four actual CSV hashes and complete 15m/1h coverage verified; 91 historical request URLs audited locally | PASS |
| Record authorized K | Official K=2.5; inclusive cost/stop predicate; 40% ex-ante cost policy; descriptive-only rationale | PASS |
| Freeze costs | 0.055% taker per side and 0.02% research friction per fill; explicitly unverified account assumptions | PASS |
| Freeze instrument scenario | Saved actual snapshot, BTC units, tick/step/minima/maxima and current closing-notional exemption documented as historical assumptions | PASS |
| Pin numerical environment | CPython 3.9.6, macOS arm64, NumPy 1.26.4 wheel hash, PCG64 vectors, exact package/build inventory and process controls verified | PASS |
| Separate future UI K | Default 2.5; alternatives EXPERIMENTAL / UNVALIDATED; no inherited official validation | PASS |
| Relevant tests | All 55 tests passed, including evidence verification with network connections disabled | PASS |

Phase 1 was committed separately as `c17f04c0f8f89b0d31a39a8860c11ac63f9e62cb`. Its original implementation, historical UNSET configuration and report bytes remain unchanged. Phase 2 adds a separate official parameter configuration and English freeze records, not a rewritten design specification. Historical Persian artifacts are retained as requested in their original phase.

The full test list is in `tests.txt`. `phase1_recheck.txt` contains the separately executed 40-test recheck. `pretag_verification.json` records READY_TO_TAG and the verified configuration/environment/data hashes; post-tag verification is run explicitly with `--require-tag` and reported to the user. NumPy probes draw only synthetic random integers; no Bootstrap, trade sampling or profitability metric was computed.

The approved economic rule is exact in policy terms: `planned_stop / estimated_roundtrip_cost >= 2.5`, so estimated cost is at most 40% of planned stop distance. Stage-0A supports the descriptive scale of that policy: stop-valid risk/cost medians were 2.774410 in 2023 and 3.791527 in 2024. The value was explicitly selected by the user; no K optimization or alternate-K comparison occurred.

Complete configuration and four data hashes are listed in `research_freeze/v0.2.2/RESEARCH_PARAMETER_FREEZE.md` and machine-readable `record.json`. The official configuration hash is `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37`. The saved environment and dependency lock are separately hash-bound. Raw candle datasets, the virtual environment, downloaded software wheel and unrelated `.DS_Store` are excluded from commits.

**Remaining gates:**

- Stage-0B implementation/testing and twelve independent full-path feasibility runs: NOT RUN; execution was not authorized in this phase.
- Funding/Mark completeness, future authorized research data access and all essential execution checks: OPEN.
- Actual historical instrument enforcement, account-specific rates and TradingView quantity/pointvalue mapping: UNVERIFIED. Frozen scenario assumptions are not claims of exact historical execution.
- Pine compile, T06/T13/T17, OCA/partial quantities, Gap/Margin/UTC/HTF/window behavior and technical Parity: OPEN / UNVERIFIED.
- 2025 Selection, separate pre-holdout freeze, final Holdout and prospective validation: NOT RUN. The current loader still denies price data from 2025 onward.

No trading rule, indicator, candidate combination, sample-size threshold or Holdout boundary was changed. No Stage-0B, profitability backtest, Pine, Selection or Holdout evaluation ran. No 2025+ price data was accessed, and no GitHub push or remote configuration occurred. Parameter freeze is not validation of strategy performance.
