# Trading research — frozen design and research parameters

The original specification and annotated tag `v0.2.2-design` are immutable. The separately approved official parameter profile is `configs/research_v0.2.2.json`, with **K=2.5**, 0.055% taker fee per side and 0.02% research execution friction per fill. The two rates and the historical use of the saved current instrument metadata are explicit research assumptions, not verified account/historical execution facts.

Read `research_freeze/v0.2.2/RESEARCH_PARAMETER_FREEZE.md` for the economic rationale, evidence, complete hashes, exact environment, order-minimum applicability and remaining gates. It becomes an effective Research Parameter Freeze only through the annotated tag `v0.2.2-research-parameters`.

## Reproduce the recorded local environment

The release environment is CPython **3.9.6**, macOS **arm64**, NumPy **1.26.4**; exact interpreter/build/platform/package hashes are recorded. The hash lock is intentionally specific to its CPython-3.9/macOS-arm64 wheel. Other environments require explicit revalidation rather than an automatic claim of equivalence.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --isolated --disable-pip-version-check --index-url https://pypi.org/simple --require-hashes --only-binary=:all: -r requirements-research.lock
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m tools.verify_research_freeze --require-tag
```

Use the recorded Python build; creating a virtual environment from a different Python is not sufficient. pip/setuptools must also match the inventory. NumPy has no transitive runtime dependencies in this lock. No global packages were changed. The environment launcher pins process/thread controls. Verification checks the exact local environment and the actual cached Development datasets; it makes no network requests and runs no position simulation or Bootstrap.

Raw candle files are ignored under `data/stage0a/20261114T165617836854Z/`. Their four hashes and captured request/quality manifests are committed with the freeze records, but the large raw datasets and `.venv` are not. Without those local data files, evidence verification must report BLOCKED; it must never substitute generated prices or fetch unauthorized periods. The original Phase 1 loader can retrieve only the Development data and required Warm-up if separately authorized.

## Phase separation

- Phase 1 is the development-only loader and descriptive Stage-0A. Historical artifacts, including Persian reports requested in that phase, are preserved unchanged. `configs/stage0a.json` intentionally remains `K=UNSET`; its CLI is not a Stage-0B or official validation engine.
- Phase 2 records the user-approved K and assumptions in a separate official configuration and evidence record. It does not change indicators, candidate combinations, signal rules, sample thresholds or Holdout boundaries.
- Subsequent official engines must load and fingerprint the official research configuration explicitly. Alternative K values cannot replace it or inherit validation; the separate future UI requirement specifies **EXPERIMENTAL / UNVALIDATED** labeling.
- The existing loader/cache policy still rejects price data from 2025 onward. Parameter metadata naming future partitions does not authorize reading them. Stage-0B, Selection, Holdout, Pine and profitability evaluation were not run in Phase 2.

Parameter freeze is not research success. Official performance remains UNVALIDATED; execution gates remain OPEN / UNVERIFIED. No remote was configured and no GitHub push was made.
