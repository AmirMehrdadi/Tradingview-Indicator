# Stage-0B — Development pre-funding feasibility

All twelve candidates have independent annual paths. This report contains counts and quality indicators only; no candidate is ranked or selected.

Scope: validated 2023/2024 candles and frozen historical instrument assumptions; Research-mode execution, not TradingView emulator verification. Funding/settlement Mark evidence is MISSING, never zero-substituted. Full net-research validity is NOT EVALUABLE.

| Candidate | 2023 completed | 2023 censored | 2024 completed | 2024 censored |
|---|---:|---:|---:|---:|
| C01 | 397 | 0 | 493 | 0 |
| C02 | 270 | 0 | 335 | 0 |
| C03 | 338 | 0 | 404 | 0 |
| C04 | 147 | 0 | 207 | 0 |
| C05 | 350 | 0 | 455 | 0 |
| C06 | 28 | 0 | 34 | 0 |
| C07 | 237 | 0 | 287 | 0 |
| C08 | 69 | 0 | 114 | 0 |
| C09 | 229 | 0 | 293 | 0 |
| C10 | 126 | 0 | 158 | 0 |
| C11 | 15 | 0 | 21 | 0 |
| C12 | 1 | 0 | 0 | 0 |

C01 mean annual completed count: **445.0**. Diagnostic: **NO_LOW_SIGNAL_FREQUENCY_FLAG**; LOW_SIGNAL_FREQUENCY is set only below 150.

The per-path JSON files contain A..G funnels, pass rates, Long/Short counts, pivot-age percentiles, primary rejection reasons, daily-stop counts, execution-quality events and signed distance from 120. Neither 120 nor 150 eliminates a candidate at Stage-0B.

## Funnel totals

| Year | Candidate | A raw | B pivot | C stop | D cost | E quantity/order | F filters | G accepted | Filled | Margin rejected | Daily-stop activations | Distance from 120 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2023 | C01 | 3360 | 3360 | 1679 | 953 | 953 | 953 | 397 | 397 | 0 | 0 | 277 |
| 2023 | C02 | 3360 | 3360 | 1679 | 953 | 953 | 560 | 270 | 270 | 0 | 0 | 150 |
| 2023 | C03 | 3360 | 3360 | 1679 | 953 | 953 | 811 | 338 | 338 | 0 | 0 | 218 |
| 2023 | C04 | 3360 | 3360 | 1679 | 953 | 953 | 187 | 147 | 147 | 0 | 0 | 27 |
| 2023 | C05 | 3360 | 3360 | 1679 | 953 | 953 | 710 | 350 | 350 | 0 | 0 | 230 |
| 2023 | C06 | 3360 | 3360 | 1679 | 953 | 953 | 40 | 28 | 28 | 0 | 0 | -92 |
| 2023 | C07 | 3360 | 3360 | 1679 | 953 | 953 | 504 | 237 | 237 | 0 | 0 | 117 |
| 2023 | C08 | 3360 | 3360 | 1679 | 953 | 953 | 89 | 69 | 69 | 0 | 0 | -51 |
| 2023 | C09 | 3360 | 3360 | 1679 | 953 | 953 | 434 | 229 | 229 | 0 | 0 | 109 |
| 2023 | C10 | 3360 | 3360 | 1679 | 953 | 953 | 158 | 126 | 126 | 0 | 0 | 6 |
| 2023 | C11 | 3360 | 3360 | 1679 | 953 | 953 | 22 | 15 | 15 | 0 | 0 | -105 |
| 2023 | C12 | 3360 | 3360 | 1679 | 953 | 953 | 1 | 1 | 1 | 0 | 0 | -119 |
| 2024 | C01 | 3576 | 3576 | 1708 | 1314 | 1314 | 1314 | 493 | 493 | 0 | 1 | 373 |
| 2024 | C02 | 3576 | 3576 | 1708 | 1314 | 1314 | 735 | 335 | 335 | 0 | 0 | 215 |
| 2024 | C03 | 3576 | 3576 | 1708 | 1314 | 1314 | 1027 | 404 | 404 | 0 | 0 | 284 |
| 2024 | C04 | 3576 | 3576 | 1708 | 1314 | 1314 | 291 | 207 | 207 | 0 | 0 | 87 |
| 2024 | C05 | 3576 | 3576 | 1708 | 1314 | 1314 | 1036 | 455 | 455 | 0 | 0 | 335 |
| 2024 | C06 | 3576 | 3576 | 1708 | 1314 | 1314 | 42 | 34 | 34 | 0 | 0 | -86 |
| 2024 | C07 | 3576 | 3576 | 1708 | 1314 | 1314 | 634 | 287 | 287 | 0 | 0 | 167 |
| 2024 | C08 | 3576 | 3576 | 1708 | 1314 | 1314 | 149 | 114 | 114 | 0 | 0 | -6 |
| 2024 | C09 | 3576 | 3576 | 1708 | 1314 | 1314 | 603 | 293 | 293 | 0 | 0 | 173 |
| 2024 | C10 | 3576 | 3576 | 1708 | 1314 | 1314 | 217 | 158 | 158 | 0 | 0 | 38 |
| 2024 | C11 | 3576 | 3576 | 1708 | 1314 | 1314 | 27 | 21 | 21 | 0 | 0 | -99 |
| 2024 | C12 | 3576 | 3576 | 1708 | 1314 | 1314 | 0 | 0 | 0 | 0 | 0 | -120 |

## Status and limitations

- Python Research-mode count integrity and deterministic replay are checked before accepting results. Any MARGIN_MODEL_EVENT invalidates the affected execution model; such counts are diagnostic only and the runner fails closed.
- Same-bar ambiguous fills follow the frozen Stop-first rule after known Open fills. No post-exit High/Low is charged to a closed position; partial exits reduce the quantity used in subsequent checks.
- All four Development OHLC datasets must be VALID with the frozen SHA-256 hashes. There is no interpolation or market-data network access in Stage-0B.
- Current instrument constraints applied historically are an explicit assumption. Fees/friction are frozen research assumptions, not verified account rates.
- Funding/Mark completeness and all TradingView/Pine execution gates remain OPEN / UNVERIFIED. Pre-funding feasibility counts do not establish net performance, Selection eligibility or a Pass verdict.
- Private accounting/event ledgers are stored separately under restricted, Git-ignored paths; none of their financial values are exported or printed.
- No 2025 Selection, Holdout, Bootstrap, rolling diagnostics, real orders, Pine implementation, final README or GitHub push was performed.
