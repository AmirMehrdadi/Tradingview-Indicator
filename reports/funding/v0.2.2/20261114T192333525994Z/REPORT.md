# Phase 4A — Development Funding and settlement Mark data

Run: `20261114T192333525994Z`. No position simulations or performance evaluations were run.

| Year | Valid Funding records | Actual missing settlements | Linked Mark minutes | Missing requestable Mark minutes | Unavailable boundary/alignment minutes | Alignment anomalies | Verdict |
|---|---:|---|---:|---:|---:|---|---|
| 2023 | 1095 | UNKNOWN — calendar unproven | 1094 | 0 | 1 | 0 | PARTIAL_DATA |
| 2024 | 1098 | UNKNOWN — calendar unproven | 1098 | 0 | 0 | 0 | PARTIAL_DATA |

Zero acquired/linked records is not evidence that zero settlements occurred. Mark coverage denominators include only observed valid settlements; absent Funding means the true required-minute denominator is UNKNOWN.

## 2023 evidence

Primary scan: `REACHED_ANNUAL_START_NOT_CALENDAR_PROOF`. Independent requery: `MATCH`.

Open prerequisites:
- HISTORICAL_SETTLEMENT_CALENDAR_NOT_INDEPENDENTLY_ESTABLISHED
- SETTLEMENT_MARK_MINUTE_COVERAGE_NOT_COMPLETE_OR_NOT_ESTABLISHED

## 2024 evidence

Primary scan: `REACHED_ANNUAL_START_NOT_CALENDAR_PROOF`. Independent requery: `MATCH`.

Open prerequisites:
- HISTORICAL_SETTLEMENT_CALENDAR_NOT_INDEPENDENTLY_ESTABLISHED

## Interpretation and scope

Historical API timestamps and bounded re-queries are retained as observational evidence. They do not prove the absence of unpublished/omitted settlements or distinguish a missing row from a historical interval change. No historical calendar is inferred from current metadata; no current instrument endpoint is called. Missing-settlement counts remain UNKNOWN unless supported by independent dated schedule/interval-change evidence. Modal cadence and suspected internal gaps are diagnostics only, never fabricated settlement records.

Mark requests contain only contiguous runs of necessary linked minutes. The minute before the Development start is forbidden; any such required boundary minute remains explicitly unavailable. The minute before a 2024 settlement may be in 2023, which remains inside the global Development allowlist. A 2025 boundary settlement is excluded entirely. No 2022 price is requested.

The stored proxy is APPROXIMATE_MARK_PREVIOUS_1M_CLOSE, retaining the same minute's Low and High. It is not an exact settlement tick and the sensitivity prices are not guaranteed bounds. Off-15m timestamps are flagged FUNDING_ALIGNMENT_UNRESOLVED without fabricated execution ordering.

Raw responses and normalized datasets are immutable create-only snapshots under ignored data/funding/. Public manifests retain hashes, explicit request ranges, provenance, quality and missing reasons. No financial ledger is accessed or modified. Data readiness cannot establish net-research validity: later funding application, required sensitivities and execution validation remain separate gates.

## Reproduction

Use the unchanged frozen CPython/NumPy environment through the repository wrapper. A fresh acquisition creates a new run; identical normalized observations produce identical dataset hashes even when retrieval timestamps/raw response metadata differ. Exact offline replay uses the saved snapshots.

```
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m research.funding acquire
sh tools/research_python.sh -m research.funding verify 20261114T192333525994Z
```

Official protocol references:
- https://bybit-exchange.github.io/docs/v5/market/history-fund-rate
- https://bybit-exchange.github.io/docs/v5/market/mark-kline
- https://bybit-exchange.github.io/docs/v5/rate-limit
