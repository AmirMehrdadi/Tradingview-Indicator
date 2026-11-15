# Conditional Development Funding attribution

Run: 20261115T204128239342Z. IMPLEMENTATION_VALIDATED / CONDITIONAL_DEVELOPMENT_EXECUTED.
CONDITIONAL_DEVELOPMENT_DIAGNOSTIC; USER_ATTESTED_OFFICIAL_CALENDAR.
The user's report of official Bybit confirmation supplies the conditional annual
calendar (1095 / 1098 settlements, 00:00/08:00/16:00 UTC). No independently retained
communication is claimed. Historical evidence and gates are not promoted.

Exactly 24 original candidate/year ledgers and six registered scenarios per path
were processed offline. Each accounting result was repeated in memory and matched
exactly. No Stage-0B engine or historical price path was rerun. Original events,
plans, fees, friction, sizing/day snapshots and occupancy were not altered.
Funding attribution and quantity conservation passed in all 144 scenario results.
Coverage/tie counts and source/output hashes are in manifest.json. No candidate
was ranked, selected or evaluated for official profitability.

Base: Close / FUNDING_BEFORE_OLD_OPEN_EXIT. Alternatives: Low and High, crossed
with OLD_OPEN_EXIT_BEFORE_FUNDING. OPEN exits of old positions are previewed only
for the alternate Funding quantity, never reordered in the execution ledger.
PRIOR_BAR exits precede Funding; same-OPEN new entries are exempt. Annual end
excludes its Funding/Open; each year/candidate starts Flat. Censored attribution
stays with its original entry and receives no completed-trade R metric.

APPROXIMATE_MARK_PREVIOUS_1M_CLOSE; exact_tick=false;
guaranteed_settlement_bounds=false. The absent pre-2023 minute remains absent.
Its sole exemption is zero old-position exposure at the annual 2023 start;
this does not certify raw or independent calendar completeness.

Funding uses unchanged Phase 4C context-independent exact Decimal arithmetic.
Pre-Funding amounts are the exact decimal representations of stored ledger
components (binary64-derived execution values), with no second friction charge.
Planned R is initial BTC quantity times the original frozen plan's price risk,
before costs; the adapter validates that risk against entry_ref and SL. Private
completed trade_R_net division uses local Decimal precision 50. This is a
representation of original execution accounting, not a replay using decimal fills.
No censored position is marked to market or assigned to another trade.

Private inputs match their retained checksum inventory and public event/count
audit. Original public Stage-0B evidence reports replay/hash PASS but does not
publish that private checksum digest; this provenance limitation is explicit.
Ignored immutable raw snapshots and all old outputs remain unmodified. Source
manifests and request provenance were authorized before market-body reads.
Private per-entry net accounting is create-only, mode 0600 in a 0700 directory,
Git-ignored, and excluded from reports and the review ZIP.

HISTORICAL_FUNDING_DATA = PARTIAL_DATA
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

No network, market acquisition, Pine/TradingView, Selection/Holdout, Bootstrap,
official profitability validation, external communication, new tag or push.
This conditional engineering result is not Research acceptance or data readiness.

Reproduce only under separate authorization for another create-only conditional
run: PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.funding_attribution.runner
