# Research Parameter Freeze — v0.2.2

This record becomes effective only when the annotated local Git tag **`v0.2.2-research-parameters`** references the commit containing the verified configuration and freeze evidence. It is distinct from the original **`v0.2.2-design`** tag and from any future pre-holdout freeze.

The original specification is unchanged. This is the explicit user-authorized parameter addendum filling its previously open K decision and fixing its research cost/metadata/environment assumptions. All other trading rules, twelve candidate combinations, sample-size requirements and Holdout boundaries remain governed by the original frozen specification.

## Approved parameters and rationale

Official **`K_cost_stop = 2.5`**, fixed for **Stage-0B, 2025 Selection and the final 2026 Holdout**. The normative predicate remains:

`planned_risk_price / roundtrip_cost_per_btc >= 2.5`

Equality passes. No epsilon, alternative comparison or automatic K selection is introduced. The economic rule is that estimated round-trip transaction cost may consume **at most 40% of planned stop distance**: `1 / 0.40 = 2.5`. This caps the ex-ante proxy, not actual realized cost after gaps, funding or execution anomalies.

The decision is the user's approved policy, informed exclusively by the existing descriptive Development reports. It is not a fitted optimum, a profitability claim, or an estimate obtained from 2025/2026 data. No alternative K was evaluated or ranked during this phase.

Stage-0A evidence, using only the population with a valid confirmed pivot and stop distance:

| Development year | Descriptive opportunities in population | P25 risk/cost | Median risk/cost | P75 risk/cost |
|---|---:|---:|---:|---:|
| 2023 | 1,679 | 1.860545 | 2.774410 | 4.044953 |
| 2024 | 1,708 | 2.556426 | 3.791527 | 5.166672 |

K=2.5 lies between the 2023 P25 and median, and below the 2024 P25. These observations describe the scale of the cost/stop distribution only; they do not establish the eventual non-overlapping sample count or expected performance. No K-based full-path count or Stage-0B simulation was run.

## Frozen research costs

| Assumption | Rate per side/fill | Status |
|---|---:|---|
| Taker trading fee | 0.055% = 0.00055 | Research assumption; not an account-specific verified rate |
| Research execution friction | 0.02% = 0.0002 | Research assumption; not measured live slippage |

For the cost floor and pre-entry risk sizing, the frozen proxy is `(entry_ref + frozen_SL) * (0.00055 + 0.0002)` per BTC. Funding is excluded from this ex-ante floor. Friction applies to research entry/Stop/TP fills as defined in the original specification; TP friction is an accounting haircut, not an assertion of a Limit fill worse than its limit. Cost already incorporated in an economic Fill must not be deducted twice. Research and tick-based TradingView Parity remain distinct models.

## Instrument snapshot and applicability assumption

The actual Phase 1 public metadata snapshot was retrieved at **2026-11-14T16:56:17.868567+00:00**. It is copied byte-for-byte into `evidence/instrument.json`; no market API request was made in Phase 2. Its use throughout the official research periods is explicitly **HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION**. It is not proof that these rules were in force on every historical date.

| Constraint | Frozen scenario value |
|---|---:|
| Instrument | Bybit linear BTCUSDT perpetual, USDT settlement |
| Quantity unit | BTC |
| Price/notional units | USDT per BTC / USDT |
| Tick size | 0.10 |
| Quantity step | 0.001 BTC |
| Minimum order quantity | 0.001 BTC |
| Minimum opening notional | 5 USDT |
| Maximum Market order quantity | 150 BTC |
| Maximum Limit order quantity | 1,500 BTC |

BTC quantity units follow the underlying-token convention in Bybit's [Order Cost documentation](https://www.bybit.com/en/help-center/article/Order-Cost-USDT-Contract). The snapshot supplies the numeric constraints; illustrative numbers in documentation do not override it. Under the public [Futures Trading Rules](https://www.bybit.com/en/help-center/article/Futures-Trading-Rules), opening orders meet both quantity and notional minima, while closing orders retain the quantity minimum and are exempt from minimum notional.

Accordingly, the research applicability assumption is: Market entry checks step, quantity minimum and 5-USDT notional at the frozen `entry_ref`; each genuine reducing TP/Stop leg checks its own step and quantity minimum, with no minimum-notional restriction. Both partial quantities must be independently valid and sum exactly to total quantity, as already required by the specification; an invalid leg rejects the entire signal. No new entry indicator/filter or alternative candidate is introduced. All quantity and split-step rules remain unchanged.

Unresolved execution/evidence requirements remain explicit: historical specification changes, actual exchange enforcement in earlier years, account-specific fees, TradingView contract/pointvalue mapping, broker rejections, Margin/OCA behavior, gap and same-entry-bar protection. The specification permits a documented fixed metadata scenario; freezing that scenario does not verify actual historical executability or close these execution gates.

## Exact numerical environment

- CPython **3.9.6**, the recorded Apple Clang build, **macOS arm64**, 64-bit pointers and IEEE-754 binary64. Exact OS/build/interpreter hashes are in `environment.json`.
- NumPy **1.26.4** from the CPython-3.9/macOS-arm64 wheel, verified against official PyPI metadata. Wheel SHA-256: `52b8b60467cd7dd1e9ed082188b4e6bb35aa5cdd01777621a1658910745b90be`.
- Runtime lock: `requirements-research.lock`. Bootstrap tooling inventory: pip **21.2.4**, setuptools **58.0.4**. No PyYAML, SciPy, pandas or additional numerical dependency is required or installed.
- Explicit `Generator(PCG64(20261114))`; no `default_rng` inference, no PCG64DXSM substitution. Both raw-integer and bounded-Generator compatibility vectors are recorded. These are synthetic RNG probes, not Bootstrap or trading evaluations.
- Single-thread numerical controls and `PYTHONHASHSEED=0` are applied by `sh tools/research_python.sh`. Installed numerical-extension hashes, CPU features and build configuration are recorded. A different interpreter/build/platform must fail verification and undergo explicit revalidation; cross-platform bitwise equivalence is not asserted.

The unchanged future Bootstrap contract is non-circular moving blocks of five trades, 5,000 replications, seed reset per candidate/partition/scenario, type-7 lower fifth percentile, sequential binary64 means and the original tie-break. The exact bounded-integer call contract is recorded in the research configuration. **No Bootstrap was executed.** NumPy's [compatibility policy](https://numpy.org/doc/1.26/reference/random/compatibility.html) explains why matching seed alone is insufficient; the [PCG64 reference](https://numpy.org/doc/1.26/reference/random/bit_generators/pcg64.html) identifies the explicit generator.

## Provenance, configuration and data hashes

Phase 1 implementation commit: `c17f04c0f8f89b0d31a39a8860c11ac63f9e62cb`.

Original design commit: `ac8fc4bb9b66a59c7224aaec1630a594b41d7e80`.

Original annotated design-tag object: `638ec6d99413c8dbc82a111209015953809ced08`.

| Artifact | SHA-256 |
|---|---|
| Official `configs/research_v0.2.2.json` | `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37` |
| Exact environment record | `ac190965edbb3a99c4d637f32a45d710ec5c69f74e003e68edc6458c10bb63d7` |
| Hash-pinned dependency lock | `e71f67460d622ed4222e28f70fd5caeb5d6745072ba6bcd6fcd56d8eb432c51e` |
| 2023 15m CSV, including 60-hour Warm-up | `f8ce969f1ce6be885e428b97762faa5a43840c52da95b5c8f5ee5d05aad4753b` |
| 2023 1h CSV, including 60-hour Warm-up | `543836f116ee43b2c7e0d1b2afc1669764f71b1ae08f43646a2b4942eab2d304` |
| 2024 15m CSV, including 60-hour Warm-up | `8d682dcdc466230feea582e185c51dda8fb299581c3abe71db64163db0e46523` |
| 2024 1h CSV, including 60-hour Warm-up | `11ef4cd7162f48060cdf6c963234277f34d7a89e3b8eb6891221d37426843ebe` |

`record.json` binds the configuration, environment, UI requirement, all eight Stage-0A report artifacts, four raw-data hashes and six small captured evidence manifests/snapshots. Large raw candle CSVs stay locally under the existing ignored data directory and are not committed. Phase 1 source, historical configuration and reports are preserved byte-for-byte; the historical Stage-0A `K=UNSET` and OPEN statuses remain historical evidence, superseded for subsequent official research by this separately tagged parameter record.

## Future configurable K and remaining gates

The future UI requirement is separately recorded in `docs/FUTURE_INDICATOR_K_REQUIREMENT.md`: default K=2.5; any alternative is **EXPERIMENTAL / UNVALIDATED**, with a distinct fingerprint and no inherited official validation. No Pine code is produced. Even the official K=2.5 profile has **UNVALIDATED** performance at this point.

Research Parameter Freeze closes the parameter-decision gates only. Remaining work includes implementing/testing and running the twelve independent Stage-0B paths, then valid Funding/Mark and other essential research-data checks, authorized Selection, the separate pre-holdout freeze, one final evaluation and prospective validation. All mandatory TradingView execution gates remain **OPEN / UNVERIFIED**. Historical metadata/account-rate verification remains unproven rather than silently assumed exact.

This phase authorizes none of those executions. No Stage-0B, profitability backtest, Pine, 2025 Selection, Holdout evaluation, 2025+ price access, real order or GitHub push occurred.
