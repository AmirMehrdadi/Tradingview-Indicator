# First controlled V2 exit-management experiment

V2_EXPLORATORY_CONDITIONAL_DEVELOPMENT. Only two pre-registered policies:
V2_A_BREAKEVEN_AFTER_TP1 and V2_B_FULL_EXIT_AT_TP1. V1_REFERENCE reuses the
original immutable ledgers/accounting; V1 is neither modified nor rerun.
48 V2 candidate/year paths are independently simulated with the unchanged V1
feature calculations, entry/filter rules, initial-risk sizing function, historical
instrument assumptions and costs. Account, occupancy, daily gate, consumption and
subsequent entries are path-specific; identical accepted trade lists are not
assumed. Manifest counts disclose added/missing signals and changed quantities.

A: initial SL/targets/planned R remain frozen. After an actual TP1 fill only,
remaining SL becomes actual economic entry-fill rounded down for Long/up for
Short to the original tick. This is price breakeven, not fee/friction breakeven.
Open gaps use adverse Open fills, never guaranteed entry-price execution.
Newly marketable intrabar BE stops beyond the known TP1 touch use that touch
price with adverse friction, never an unvisited, more favorable BE reference.
An active stop takes precedence over targets when both are reachable. Initial
SL plus TP1 in a bar stops first without activating BE. If intrabar TP1 activates
BE and the same bar reaches BE, model TP1 then BE before TP2 and register
BE_ACTIVATION_INTRABAR_AMBIGUOUS. This pessimistic sequence is an explicit
research assumption; no actual intrabar ordering is asserted.

B: all quantity closes at frozen TP1 with adverse friction and fees. The two
original quantity allocations are booked simultaneously at the same TP1 price
as one logical whole-position exit, solely to reuse quantity/fee conservation.
There is no retained TP2 exposure or independent partial-execution timing. The
original sizing/quantity eligibility gates are preserved, including minimum
requirements of the original allocations; no new entry eligibility is introduced.

Funding reuses unchanged exact attribution mathematics, previous-minute Close
and FUNDING_BEFORE_OLD_OPEN_EXIT only. Six-scenario V2 Funding robustness is not
evaluated. Funding never changes shared pre-Funding sizing/day snapshots.
Calendar coverage is conditional on USER_ATTESTED_OFFICIAL_CALENDAR, not a new
independent primary-source verification. APPROXIMATE_MARK_PREVIOUS_1M_CLOSE;
exact_tick=false; guaranteed_settlement_bounds=false. Initial-2023 no-old-exposure
exemption and annual-end censoring remain narrowly scoped.

Private comparison.json contains all 72 arm/candidate/year metrics and explicit
V1 deltas. All execution/accounting and financial aggregates remain create-only
under ignored restricted private storage (0700 directories, 0600 files); they
are not committed or included in the review ZIP. Public evidence contains only
technical counts, input/output/code identities, anomaly counts and limitations.
Realized drawdown uses POSITION_CLOSED order and completed trade net R; censored
Funding stays separate and is not assigned to another completed trade. Costs
embedded in fills are not deducted again. No arm or candidate is selected.

HISTORICAL_FUNDING_DATA = PARTIAL_DATA
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

Development comparisons are exploratory and reuse previously examined data.
Better Development outcomes cannot establish independent validation. No network,
market acquisition, parameter sweep, candidate ranking, TradingView, Selection,
Holdout, calendar research, tag change or push is performed.

Reproduction requires the retained local frozen inputs, exact environment and a
separate authorization for another create-only run:
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.v2_exits.runner
