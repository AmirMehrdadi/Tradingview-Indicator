# Phase 5B1 C01 source-only diagnostic contract

Authority is the unchanged v0.2.2 specification and research_v0.2.2.json, including
its explicit Research Parameter Freeze. This is not a runnable validation claim.
No TradingView environment, compiler, market feed or historical cache is used.

## Source and mathematical scope

Phase5B1_C01_Decision_Probe_UNVALIDATED.pine is a new independent indicator source.
Its initialization recurrence is copied additively from Phase 5A; the Phase 5A
artifact is unchanged. Only C01 Baseline is implemented. No R/H/V/M/Q exists,
including no request.security: inactive H imposes no extra hourly readiness.

The 15m state requires its exact November 1, 2026 00:00 UTC anchor. EMA20/50 use
first authorized Close seeds; ATR14 uses initial TR H-L and the first fourteen
TR mean before Wilder recurrence. Missing/invalid OHLC or discontinuity poisons
state. No intermediate rounding or native ta.* fallback is used. At least 200
closed bars are required. November 4 begins signal-close eligibility, not a new
seed. The December 1 boundary is exclusive for diagnostic decisions. No data
before the anchor is a numerical input; source predicates still cannot prove
platform-level history access isolation. The Phase 5A-V1 safety gate stays open.

Trend inequalities are strict. Pullback search chooses the latest qualifying
bar among ages 2..5, using touch-inclusive geometry and depth <= .75 ATR at that
bar. The entire selected sequence must keep Close strictly beyond EMA50, and
the current candle must meet all strict confirmation predicates. A failed
sequence does not fall back to an older pullback. Manual strict 3-left/3-right
pivots become available only at j+3. The latest suitable confirmed pivot with
j >= i-80 is selected. Equal neighbor prices reject the pivot.

Structural stop uses pivot +/- .15 current ATR, then Long floor / Short ceil
on raw_price/.10 without epsilon. Risk is measured from the rounded stop and
must lie inclusively in [.75 ATR,2.5 ATR]. TP1/2 use 1.5/2.5 times that risk,
then the same conservative tick directions. Targets must be positive, distinct,
and ordered on the correct side of entry. There is NO additional post-rounding
1.5R threshold: section 4.5 explicitly removed that old condition. Reported
rounded reward/risk values are diagnostics; optional Q is absent.

Prices remain integer tick counters; displayed prices are ticks/10.0. Quantity
remains integer BTC step counters, with amounts steps/1000.0. Once constructed,
no count is reconstructed by dividing a float-rendered price or quantity back
onto its grid. No tolerance can hide a one-tick/step difference.

Cost uses exactly (entry_ref+SL)*(.00055+.0002), with positive denominator and
risk/cost >= 2.5. Sizing uses min(.0025*settled/(risk+cost),2*settled/entry), then
floor(raw/.001). TP1 gets floor(total/2); TP2 the remaining steps. The whole
entry and each leg are checked against frozen minima/maxima. Entry notional
must be >=5; reduce-only closing notional is exempt under the frozen assumption.
Entry maximum is 150000 steps; each leg also respects Market 150000 and Limit
1500000 steps. Minimum is one step each. Price bounds .10..1999999.80 are from
the preserved instrument snapshot used by Stage-0B.

These are Research assumptions: fee .055% per side, friction .02% per fill,
BTC units, tick .10, step .001 and historical instrument constraints. They are
not verified account rates or historical effective-date evidence. November
window use does not convert the Research cost model into tick-based emulator
Parity. K is hard-coded 2.5; there is no experimental K control or validation
badge. TradingView pointvalue/quantity mapping remains unverified and unused
because there are no orders.

## Synthetic context and identity

fixtureEnabled is false by default; it enables diagnostic acceptance only.
fixtureBalance, fixtureBusy and fixtureDailyStop are explicitly SYNTHETIC,
static snapshots, not live account data. Changing them restarts Pine inputs;
they cannot stand in for a time-varying historical execution ledger. Python
fixtures can supply a Context per decision. The Pine source is reviewed against
those pure decision predicates, not a full account path.

After a complete eligible diagnostic decision, its direction-specific pullback
UTC ID is consumed once. Failed, disabled, busy or daily-stopped decisions do
not consume it. Consumption is diagnostic acceptance, never evidence of a
queued order or actual fill. No position, pending-order engine or settlement
snapshot evolves from prices. The post-fill/daily lifecycle and manual signal
expiration display are not implemented in this decision-only phase.

Pullback and pivot IDs are UTC bar opens derived from anchor-relative indices,
not chart-prefix-dependent bar_index. Together C01/Research/November2026,
signal-close timestamp and direction identify a diagnostic decision. Python
also records a namespaced fixture decision ID. No trade ID or order is created.
Only masked Data Window fields exist, with offset=1 toward the owning close.
That actual Data Window placement is still a Pine runtime verification gate.

## Current offline verification

Run from the repository root:

    PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b1_checks

Only new synthetic tests execute; old historical suites are not rerun. The
runner reuses the unchanged offline/data guard with a narrow read-only allowance
for this new Pine file and checks the frozen numerical environment first.
Tests have literal expected accepted levels/IDs, mirrored Short cases, strict
boundaries, invalid input failures and comparisons with preserved Python helpers
on synthetic values. No old runner/preflight that reads real caches is invoked.
Source-token tests are scope reviews, not a Pine parser or compiler proof.

## Remaining authorized-review boundary

SOURCE_IMPLEMENTED and SYNTHETIC_FIXTURES do not establish Pine correctness.
Independent review must check the translation against specification sections
2–6 and 8.1, especially raw-grid floor/ceil, selected-pullback precedence,
80-bar pivot ownership, quantity rejection and consumed-state mutation points.
Real compiler/runtime work requires separate authorization and a demonstrably
safe environment excluding Holdout in both chart and hidden requested history.
No ordinary chart, replay, zoom or date mask is an approved substitute.

A later authorized same-input comparison must preserve exact source/config and
OHLC hashes, check first divergence at confirmed close, require exact boolean,
ID and integer-grid agreement, and use the frozen tolerance only for continuous
indicator values. Real position/daily inputs need an authorized adapter; this
probe's static defaults must not be treated as execution/accounting parity.
Genuine compiler diagnostics, reload/realtime behavior and signal-close Data
Window offset placement remain unverified. No such actions are performed now.

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
