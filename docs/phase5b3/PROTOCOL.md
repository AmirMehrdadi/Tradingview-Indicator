# Phase 5B3 combined offline fixture model — UNVALIDATED

This package is a synthetic Python Research-state reference. It contains no
loader, network transport, historical-data adapter, TradingView execution,
actual order, alert or profitability evaluator. Prior probes are unchanged.
No new combined Pine state-machine source is delivered. That translation is
explicitly NOT_IMPLEMENTED: Pine persistence/rollback, pending/active state,
per-leg Research fills/accounting, daily snapshots and censor ownership have
not been faithfully established in a new Pine source. The Python model and
existing decision probes must not be represented as a combined Pine system.
The existing safe TradingView environment gate remains unresolved.

## Stage A: lifecycle kernel

research/fixture_state_v1/state.py is independent of the preserved Stage-0B
lifecycle implementation. Its Candle and Decision inputs must explicitly carry
SYNTHETIC_FIXTURE_ONLY. No files, paths, client objects or account credentials
are accepted. Each instance owns one registered candidate and fixture namespace.
FLAT, PENDING_ENTRY and OPEN are mutually exclusive, with terminal ENDED state.

Candle represents an explicitly completed synthetic bar, processed OPEN first,
then frozen Research INTRABAR effects recognized as PRIOR_BAR at its end. Decisions
can queue only at the last observed confirmed close with entry_ref equal to that
close. Exactly the next bar's Open fills a pending entry. Initial state is Flat,
10,000-USDT synthetic cash/settled/day-start, no pending order or consumed IDs.
Stage A has no indicators: prepared unit decisions and the first bar of an
isolated lifecycle fixture do not purport to be a complete anchored feature
stream. Stage B adds strict full-stream initialization from the numerical anchor.

A Decision is a prevalidated Baseline/filter unit-fixture plan. The kernel checks
its ownership, signal window, integer quantity/tick reservations, positive grid
geometry, frozen price bounds, opening minimum notional, quantity maximum,
cost floor, ex-ante risk-budget ceiling and two-times-notional ceiling. Stage A
unit plans may reserve a smaller valid amount to isolate execution arithmetic;
Stage B's complete stream computes the exact frozen raw sizing/floor first.
The kernel is not an alternative signal generator or a resizing policy.

Accepted queueing consumes (candidate,direction,pullback UTC ID) and freezes
entry, two exit and two independent OCA identities, total integer steps and
floor(total/2)/remaining allocations. Rejected setups do not consume IDs. A
broker margin rejection at the next Open is different: its accepted signal
stays consumed, there is no fill/fee and both child reservations are cancelled.

Research assumptions remain .00055 taker fee per side and .0002 adverse friction
per fill, including conservative TP accounting haircut. They are not verified
account rates. BTC quantities are steps/1000 and order prices ticks/10, with no
reconstruction of counters or epsilon. Existing frozen metadata constraints
remain historical assumptions; no broker pointvalue equivalence is claimed.
Entry uses raw Open with directional friction and fee. Marketability checks
use raw prices, not friction-adjusted trigger substitutes. Gaps through stops
use Open. Known OPEN TP fills occur at frozen targets before later extremes;
otherwise ambiguous intrabar TP/SL reachability is Stop-first for remaining legs.
Each bracket allocation fills wholly once; liquidity partial fills are not modeled.
TP1 is a partial position closure, not a full settled-account update.

The model records deterministic event/fill IDs and rejects duplicate, over- and
under-filled legs. Invariants require exited+remaining=entry steps and no
completed position with residual steps. Monetary state is necessary only for
synthetic sizing, fees, margin and daily stop. No trade_R, returns, expectancy,
drawdown, ranking or profitability metrics are calculated or exported.

Only complete position closure updates settled balance. At midnight, old-bar
full closure belongs to the old day, then the new day's start uses its final
settled snapshot and resets the sticky one-percent daily stop. A partial position
carries the prior full-settlement snapshot, not its partial cash result. Adverse
entry risk deviations, risk/notional overruns, marketability anomalies, ambiguous
intrabar ordering and margin insufficiency are diagnostics, not after-the-fact
trade deletion. Margin inspects remaining quantity only and no later extremum
after definitive exit. A margin-model event invalidates genuine research use;
no real liquidation process or forced reduction is invented.

At the final authorized bar's close, PRIOR_BAR effects finish before END. An
unfinished position is archived as CENSORED with remaining allocations intact;
no artificial exit, cancellation of a real protective order or completed-trade
claim is made. The fixture engine then terminates and rejects further data.
Because no live orders exist, this is Research censor semantics only: it does
not implement Pine's obligation to keep actual protective orders beyond a display
window. Such Pine behavior remains unimplemented and execution-gated.

Invalid/missing OHLC or a replay/gap stops the path before any partial bar updates
commit; the original position/pending reservations remain available for audit,
and the path is quarantined. Low-level fill methods are internal mathematical
unit seams, not external broker callbacks. Malformed values are rejected before
cash or step mutation. There is no Funding implementation or zero-rate imputation.

## Gate A and Stage B integration

Gate A must pass before Stage B begins. Its tests use literals and independent
fee/step expectations. A synthetic Long/Short two-leg case also cross-checks the
preserved Stage-0B Engine, instantiated only in memory with literal synthetic
candles and public frozen config. Its ephemeral synthetic attributes are not
historical private ledgers; no private file is opened.

research/fixture_state_v1/integration.py owns a separate lifecycle, numerical
history, hourly history, volume history and decision log for one candidate.
The exact preserved C01-C12 registry is reused, not inferred or optimized.
Existing Phase 5B1/5B2 pure fixture-reference functions provide the frozen
numerical decisions and optional predicates; they do not load data or execute
orders. The new lifecycle itself is independent, with explicit cross-checks.

CandidatePath.feed accepts only completed synthetic Candles. Unconfirmed inputs
do not change state. It requires its first numerical bar at
2026-11-01T00:00:00Z and strictly contiguous 15m bars. After execution of the
current completed bar, the signal-close snapshot uses that path's settled
balance, daily stop, occupancy and consumption. No prior accepted diagnostic
is assumed filled: QUEUED_NOT_FILLED is distinct from the later ENTRY event.
A path that remains OPEN/PENDING blocks another entry; complete prior-bar closure
can free it before the new close decision. Actual sizing uses the frozen
Research formula, quantities/targets remain frozen at queueing and Open cannot
retroactively alter the decision.

Hourly candles are separate explicit synthetic inputs. Their completed end
must be no later than the available chart close; metadata is checked before
execution updates. The H predicate still uses execution-bar-open ownership, so
the hour ending 11:00 cannot inform the 10:45–11:00 decision. It first informs
the 11:00–11:15 decision. Missing/invalid/gapped hourly input quarantines only H;
non-H candidates are not blocked by H readiness. Invalid volume blocks only V.
The pure offer_decision seam allows isolated prevalidated plan/filter fixtures;
it does not certify externally supplied indicators or bypass the strict full-
stream numerical anchor in feed. No historical data adapter exists.

Indicator history persists across TRADE_START=2026-11-04T00:00:00Z. Decisions use
signal closes in [TRADE_START,2026-12-01T00:00:00Z), and the hypothetical next Open
must also precede END. No pre-anchor numerical values, future candle/HTF state
or end-boundary Open is a decision input. Each candidate runs from its own
initial state; one path's accepted/rejected/closed trade cannot free, consume
or resize another path. Candidate/filter-bit identity is recorded exactly.

## Offline commands and evidence levels

    PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_checks --stage A
    PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_checks --stage B

Stage B's run includes all Stage A tests plus integration and the preserved
C01/Phase 5B2 synthetic suites. It is not full historical regression. Both gates
use the frozen numerical environment and existing deny-by-default access guard.
The only extra read allowance is the preserved Pine source directory/files for
static declaration checks. No market/cache/private-ledger read is permitted.

There is no new Pine source to compile. Static checks scan preserved Pine global
declarations and new Python definitions, with stated parser limitations. They
cannot establish Pine compiler success or hidden TradingView access isolation.
All real compiler/runtime/rollback/numerical/execution parity work needs separate
authorization and a demonstrably safe non-Holdout environment. Static code,
mathematical fixtures and genuine Pine runtime evidence are separate levels.

PINE_STATE_MACHINE_SOURCE = NOT_IMPLEMENTED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

Stop for independent review. No push or next phase is authorized.
