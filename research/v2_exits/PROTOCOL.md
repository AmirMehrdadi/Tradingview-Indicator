# First controlled V2 exit-management experiment — pre-registered scope

Only V2_A_BREAKEVEN_AFTER_TP1 and V2_B_FULL_EXIT_AT_TP1 are authorized. V1_REFERENCE
uses the retained V1 ledgers and base conditional Funding outputs, without a V1
engine rerun. Original V1 source, tags, configuration, candidates and reports are
immutable. No original accepted-trade list is used to generate a V2 path.

All 12 candidates, independently for 2023 and 2024, start with 10000 USDT and the
frozen pre-Funding sizing/day-state contract. V2 policies use the original feature,
signal, sizing, fee (0.055%/side), adverse friction (0.02%/fill), order-minimum and
margin machinery through a separate Engine subclass. The original risk, initial
SL and targets are frozen per entry. Shared immutable features do not share
trading state. Changed occupancy and realized pre-Funding account state may change
later accepted signals and quantities; all such differences must be disclosed.

A activates its remaining-leg stop only after an actual first-leg TP1 fill.
Round actual economic entry-fill down for Long/up for Short to the original tick.
Keep initial Plan.sl and planned risk unchanged; store the active stop separately.
This is price breakeven, not net breakeven after adverse friction and fees. An
already-active stop is processed before reachable targets. If initial SL and TP1
are both touched in one OHLC bar, initial Stop-first applies and BE never activates.
If TP1 activates BE intrabar and that bar also touches the new stop, pessimistically
process TP1 then the new stop before TP2, recording explicit activation ambiguity.
The low/high might actually have occurred before TP1; no real order is asserted.
Known Open TP1 fills activate BE before remaining intrabar processing. An Open
through a BE stop uses Open plus adverse friction, never guaranteed entry price.
If economic breakeven is already beyond the known intrabar TP1 touch price,
the newly marketable stop fills at that known touch plus adverse friction,
not at an unvisited, more favorable breakeven reference.

B closes the entire position at TP1. Two original quantity allocations are
accounting components of a single logical full-quantity exit at identical time,
price and fee rate, not independently timed exit orders. No TP2 exposure remains.
Original sizing eligibility, including allocation minima, is retained so the exit
experiment does not introduce a new entry gate. Stop-first precedes TP1 on dual
touches. Favorable target gaps receive frozen TP1 with adverse haircut, not Open
price improvement. Remaining-quantity/path checks precede definitive closure;
closed quantities receive no later bar extremum or margin event.

Use only retained four 15m/60m Development datasets and exact original anchors,
Funding and Mark snapshots, frozen metadata assumptions and environment. Verify
all 234 baseline blobs/modes, both annotated tags, source hashes, dataset hashes,
request provenance and private source identities before processing. Deny network
and unregistered caches. No 2025/2026 input, fresh acquisition, TradingView or
calendar research. Original conditional calendar attestation remains an attestation.

Funding comparison uses previous-minute Close / FUNDING_BEFORE_OLD_OPEN_EXIT only,
with the unchanged exact attribution adapter. Prior-bar fills precede Funding;
old Open exits follow base Funding; same-Open new entries are exempt. Funding
changes neither sizing nor daily gates. Censored Funding remains with its own
entry; annual reset/end rules and the narrow initial-2023 Mark exemption persist.
Six-scenario V2 Funding robustness is outside this first bounded experiment.

Focused synthetic tests and one final dependency-scoped regression after final
executable edits precede historical execution. Run exactly 48 new stateful V2
simulations, no parameter sweeps or outcome-driven edits. Reproduction is by
retained code/config/data hashes; another historical execution needs separate
authorization. No arm or candidate is ranked, selected or certified profitable.

Private financial comparison and execution/accounting records are create-only,
0700 directories/0600 files under ignored data/stage0b_private/v2_exits/. Public
technical reports contain counts, anomalies, hashes, test metadata and limitations
only. All 72 comparison rows are shown privately to the user. Do not publish raw
ledgers or financial tables in Git or the review ZIP.

Commands:
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_v2_exit_checks --focused
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_v2_exit_checks
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.v2_exits.runner

HISTORICAL_FUNDING_DATA = PARTIAL_DATA
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
All Pine/TradingView execution, numerical parity and safe-environment gates remain
UNVERIFIED. Selection and Holdout remain LOCKED_NOT_ACCESSED. Improved Development
results are exploratory reuse of examined data, not independent validation.
