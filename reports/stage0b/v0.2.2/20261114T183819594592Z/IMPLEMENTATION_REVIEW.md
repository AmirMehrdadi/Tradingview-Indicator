# Phase 3 completion review

Status: **IMPLEMENTED / TESTED / EXECUTED / VERIFIED — pre-funding feasibility counts only**.

Exactly 24 independent candidate/year paths were executed on the original validated 2023/2024 Development inputs, followed by 24 fresh-engine replays. Both public summaries and restricted private ledger hashes matched for every replay. The separate post-run audit passed count conservation, entry/exit identities, partial quantities, restricted permissions and Git exclusion. A/B/C counts also match the frozen Stage-0A descriptive counts in every path: 3360/3360/1679 in 2023 and 3576/3576/1708 in 2024.

The complete existing suite and 38 focused new tests passed: **93 tests, zero failures**, before execution. The exact command and complete output appear in `tests.log`. New coverage includes independent optional-filter paths, causal HTF/pivots, Wilder initialization, inclusive filter thresholds, quantity/minimum checks, next-open margin rejection, same-entry-bar protection, raw versus economic triggers, gaps and frozen targets, remaining Stop quantities, no duplicate fills, daily settlement/UTC ordering, annual resets/censoring, future-data rejection, missing Funding, privacy and deterministic reproduction.

Observed execution quality: zero margin-model events, zero margin rejections, zero censored positions, and 14 ambiguous intrabar-order events across the independent paths. Those 14 events followed the frozen Stop-first rule; they are not 14 necessarily distinct market bars. One daily-stop activation occurred. No trades or candidates were removed because of these diagnostics. C12 in 2024 had no accepted entries; its zero censor rate is accompanied by `NO_FILLED_TRADES`, rather than implying evidence from a traded sample.

C01 completed 397 trades in 2023 and 493 in 2024, mean 445: **NO_LOW_SIGNAL_FREQUENCY_FLAG**. Every candidate's signed distance from 120 appears in the public counts/report. These are descriptive counts; no candidate ranking, elimination, tuning or profitability assessment was performed.

## Provenance and reproduction

- Base research-freeze commit: `4bc7447755ef7a9dbd8832221f2ded5afc21401f`.
- Original design and research annotated tag objects remain unchanged: `638ec6d99413c8dbc82a111209015953809ced08` and `826b05146e99a5a87e9951da9b4e0ac2deea1d09`.
- Implementation aggregate SHA-256: `77f789994e262a9edee0996237766f98d8f3a301d7664ce1e1642771d65181bc`.
- Official configuration SHA-256: `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37`.
- Public counts SHA-256: `10484fb66f296276e6d8284d8c22b78053fd6ef6442117119a83ecb6ea32a809`.
- Exact source/dataset/environment hashes and commands are in `manifest.json`; supplemental testing/privacy evidence is in `verification.json` and `audit.json`.
- Numerical environment: the unchanged `research_freeze/v0.2.2/environment.json` and `requirements-research.lock`, CPython 3.9.6, NumPy 1.26.4, with the frozen PCG64 contract and process controls. No Bootstrap was run.
- Frozen research assumptions remain K=2.5, taker fee 0.00055 per side and execution friction 0.0002 per fill. Instrument quantity, price and minimum-order metadata remain historical assumptions.

```
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m research.stage0b run
sh tools/research_python.sh -m research.stage0b.audit 20261114T183819594592Z
```

A new run creates a new artifact directory; it does not overwrite this run. Reproduction requires the original ignored local data. The implementation contract is `research/stage0b/PROTOCOL.md`.

## Remaining gates and scope

There is no mandatory blocker for the explicitly permitted **pre-funding Stage-0B count scope**. Funding rates and settlement Mark history remain MISSING, not zero, so net-research validity and Funding sensitivities are **NOT EVALUABLE**. TradingView/Pine behavior, including T06/T13/T17, remains **EXECUTION GATE — UNVERIFIED**. Historical instrument-rule applicability is an unverified assumption. Trade-through and other required research sensitivities remain unexecuted. Neither these counts nor the test suite closes those gates or establishes Selection eligibility or a research Pass.

Only the new Stage-0B package, focused tests, the related Git exclusion and non-sensitive reports are approved for the local commit. The original specification, configuration, Phase 1 helpers, frozen records and tags were not changed. Private ledgers are restricted and ignored; raw datasets, caches, environments and the unrelated `.DS_Store` are excluded. No 2025+ price access, Selection/Holdout evaluation, Pine work, final README authoring, real orders or GitHub push occurred.
