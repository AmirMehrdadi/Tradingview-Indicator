# Stage-0B implementation contract — v0.2.2-1

Authority: the frozen design and research-parameter tags, the original v0.2.2 specification (sections 4–9), the frozen official configuration and the explicit Phase 3 execution request. The latter permits Stage-0B without rewriting the historical Phase 2 execution-scope text in the frozen configuration.

## Scope and causality

The executable accepts no parameter overrides, data paths, candidate additions or years. Its sole run command loads the four frozen local 2023/2024 Development CSVs. All four hashes and manifest windows, both original annotated tag objects, frozen authorities, Phase 1 helper hashes and the pinned environment are checked before parsing prices. Network connections are disabled during execution. No price history from 2025 onward is opened.

Each annual feature series starts at its prescribed 60-hour anchor. EMA/ATR/baseline/strict pivot helpers are reused unchanged. ADX and RSI use the specified Wilder initialization and zero-denominator cases. H uses the last hourly end at or before the execution bar's **open**, including the 60-visible-hour requirement; it never uses an hour first becoming available at that bar's close. A pivot becomes available only after three right bars. Shared features are immutable observations; candidate trading state is never shared.

## Independent state and ordering

Every candidate/year starts Flat with 10000 USDT, empty orders/consumption IDs, and independent settled/day state. A..F count diagnostic opportunities even when busy. Sizing reads only that path's settled snapshot; failed opportunities do not consume pullbacks. G counts accepted nonoverlapping signals before possible next-open margin rejection. Thus G = N_signals = N_filled + N_rejected_margin; N_filled = N_completed + N_censored.

The previous bar's fills and full settlements occur before partition termination or UTC reset. The close signal sees this state, then queues a next-open Market entry and two separately identified, fixed-quantity brackets/OCA groups. Entry fee/friction, frozen Stop/TP geometry, whole-step splitting, each partial's minima and the historical opening/closing-order rules follow the frozen profile. At entry, insufficient initial margin rejects the whole order without fees or resizing, retaining pullback consumption.

Known Open exits precede ambiguous range processing. Open-marketability uses raw prices; friction crossing a target alone cannot trigger it. Gaps through Stop use Open. Marketable TPs receive the frozen target with an adverse accounting haircut, never an improved Open. After Open, Stop-first applies to the remaining legs; otherwise targets are processed in order. Filled legs are never restored. Full exit frees the position; partial exit does not. Margin examines only remaining exposure and the processed path before definitive exit; an event invalidates the path while retaining diagnostic fills. No liquidation algorithm is invented.

Private fee/cash/realized accounting is necessary only for path state, sizing, margin and the daily stop. The settled snapshot changes only on full closure. Midnight uses the previous bar's settled outcome before resetting the day; partial results do not enter the daily snapshot. End-of-year processing completes the last bar, censors remaining exposure and never processes an end-boundary signal/Open. The next annual engine resets all state.

## Privacy, evidence and limits

Public reports contain only counts, A..G funnels/pass rates, rejection reasons, direction and pivot-age counts, censoring/daily-stop/execution-quality indicators and input provenance. C01's mean completed annual count alone receives LOW_SIGNAL_FREQUENCY below 150. Distance from 120 is descriptive for all candidates. Neither is a Stage-0B elimination or ranking rule.

Private event/accounting ledgers and their checksums reside under `data/stage0b_private/v0.2.2/<run-id>/`, with directory mode 0700, file mode 0600 and Git exclusion checked before writes. Public schema validation rejects financial fields. Restricted ledgers are never printed, committed or used to calculate profitability metrics. The audit checks event IDs/quantities/counts and hashes without displaying accounting values.

Funding rates and settlement Mark evidence are absent. They remain explicitly MISSING/None, never zero. Section 9.1 permits pre-funding feasibility counts because Funding cannot enter the shared sizing/daily gate. No funding cashflows, settlement tie assumptions or net-research metrics are fabricated. Net research and Funding sensitivity remain NOT EVALUABLE. These results do not establish Selection eligibility, investment performance or a Pass verdict.

This implementation runs only the Research touch/Stop-first base case required for Stage-0B. Trade-through and Funding sensitivities, TradingView execution/Parity, historical metadata applicability, Selection and Holdout remain separate OPEN gates. Neither Python unit tests nor count replay closes a TradingView execution gate. T06/T13/T17 and all other behavior requiring TradingView remain **EXECUTION GATE — UNVERIFIED**.

## Reproduction

Use the repository's `sh tools/research_python.sh` wrapper: CPython 3.9.6, NumPy 1.26.4 and the exact frozen environment/lock, including the pinned PCG64 contract. No random sampling or Bootstrap runs here. Commands:

```
sh tools/research_python.sh -m unittest discover -s tests -v
sh tools/research_python.sh -m research.stage0b run
sh tools/research_python.sh -m research.stage0b.audit <run-id>
```

The run executes 24 unique independent paths and replays every path from a fresh engine. Public canonical JSON and restricted ledger hashes must both match. The logical run ID binds code/config/data hashes; the wall-clock run ID only separates artifact directories. Existing outputs cannot be overwritten. Each manifest records exact implementation source hashes, frozen input hashes and environment hashes. Reproduction needs the ignored local frozen data and pinned environment; the private ledgers are not a dependency of a new run.
