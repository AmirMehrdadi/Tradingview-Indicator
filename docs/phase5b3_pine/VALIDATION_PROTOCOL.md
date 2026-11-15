# Phase 5B3-Pine — UNVALIDATED source-only Research diagnostic

This additive artifact implements the intended combined Pine source contract.
It has not been compiled, executed, or validated on TradingView. The preserved
Phase 5B3 Python-only report remains a correct description of its earlier commit;
this addendum does not rewrite that report or its NOT_IMPLEMENTED finding.

## Authority and fixed scope

The frozen specification v0.2.2 governs, particularly sections 3–6, 7.1, 7.2.1,
8.1, 8.3–8.3.1, 9.0.1–9.0.3 and 10. The official frozen configuration supplies
K=2.5, fee=.00055 per side and adverse friction=.0002 per Research fill. These
costs and the instrument limits are research assumptions, not verified account
rates or historical exchange rules. BTC prices render integer ticks / 10 and
quantities render integer steps / 1000. No Funding is modeled or imputed.

The new Pine file preserves the Phase 5B2 numerical, pivot, optional-filter and
candidate-selector blocks byte for byte. The decision calculation changes only
its account/occupancy/daily-stop sources and successful-queue/consumption path.
C01–C12 remain B, BR, BH, BV, BM, BQ, BRH, BRV, BRM, BHV, BRHQ, BRHVMQ.
Only one input-selected candidate owns a run. Candidate/enable input changes
are intended to restart the whole script under normal Pine input semantics;
that platform behavior has not been verified for this artifact.

## Intended source execution sequence

The enable switch defaults false. Numerical warm-up starts at November 1,
2026 00:00 UTC, with no reset at November 4. Missing anchors, discontinuities
and malformed OHLC quarantine the affected numerical/lifecycle path.
First permitted signal close is November 4 00:00 UTC. Signal close and the
next hypothetical entry Open must both precede December 1 00:00 UTC.

At each confirmed 15m close, the ResearchBook object first reconstructs that
completed bar's OPEN, then its intrabar PRIOR_BAR effects. Only then does the
selected candidate evaluate the close using the evolving settled balance,
occupancy and daily stop. A successful plan queue freezes entry_ref, SL/TP
integer ticks, total quantity, floor(total/2)/remainder reservations, candidate,
pullback and entry/leg/OCA identity strings. Consumption happens after queue
success; queue and entry flags are distinct. These OCA strings identify two
independent hypothetical reservations, not actual broker OCA orders.

The pending plan is evaluated using exactly the following authorized bar's raw
Open. Fee-inclusive 50% hypothetical margin rejection releases occupancy, charges
no fee and preserves consumed identity. Otherwise the complete frozen quantity
fills adversely at Open*(1+side*.0002), with fee. It is never resized at Open.
Entry-bar exits are then evaluated with the same rules as later bars. This is
retrospective recognition on a confirmed completed bar, not a realtime Open
callback. It uses the previous close's frozen plan, not that bar's future signal.

Raw Open stop priority precedes marketable TP1/TP2 at their frozen targets;
a stop gap fills at raw Open before adverse exit friction. Remaining ambiguous
intrabar stop/target reachability is Stop-first. TP friction is the separate
Research accounting haircut, not a trigger adjustment or future TradingView
limit-order fill claim. A friction-only crossing of TP is an anomaly, not raw
price marketability. Long/Short fills are symmetric. Each leg fills at most once,
for its whole remaining integer reservation; no liquidity partial fills exist.
Exited plus remaining steps must equal the filled total. No forced liquidation
is invented. Quality flags retain unfavorable fills and never filter them away.

Cash changes on entry fees and leg exits. Partial exits retain the prior fully
settled balance and busy state. Full closure alone sets settled cash and applies
the sticky realized one-percent daily stop. PRIOR_BAR settlement at midnight
belongs to the old day; the new UTC day then snapshots its final settled balance
and clears the stop. Daily stop blocks only new queues. Margin checks use actual
remaining quantity and stop after a known full exit; later bar extremes cannot
create a margin event for that closed position.

The final authorized bar completes PRIOR_BAR effects, then sets ENDED_FLAT or
CENSORED with residual reservations intact. No END Open is read, no forced exit
is invented, and no new close signal is accepted at END. Terminal state is stored
internally; it is deliberately hidden by the strict display mask at END. No genuine
protective order exists in this indicator. A future Pine Strategy must separately
retain protective orders beyond a display window for real simulated exposure
(specification 9.0.1); Research censoring does not satisfy that execution gate.

## Observation and containment limits

All plots are Data Window only, masked by accepted close or enabled confirmed
state in [November 4, December 1). offset=1 assigns observations to the owning
close boundary. Warm-up/forbidden-date state, monetary balances and performance
metrics are not plotted. No graphical signal, order or alert API is used.

The confirmed-hour function uses [1] for the latest completed hour and [4] for
its three-hour-old EMA, lookahead_on, explicit November initialization, 60-hour
readiness and exact owning-hour timestamps. The 10:00–11:00 hour can first inform
the 11:00–11:15 decision, not the 10:45–11:00 close. Non-H candidates do not wait
for H; invalid volume blocks only candidates with V. Strict 3/3 pivots use only
seven authorized chart observations and no future information.

Source predicates mask and seed computations; they do NOT prove platform-level
input isolation. request.security still executes in TradingView's chart context.
The safe environment gate is unresolved. Do not paste/load/run the file on an
ordinary BTC chart or open TradingView under this task. No claim is made that
scrolling, replay, hidden history or display masks exclude protected inputs.

UDT/reference-field mutation, rollback, input restart, method typing, historical
series behavior, offset display, security timestamps and resource limits require
genuine platform evidence. Fields use ordinary var state, not varip; the source
mutates its book only on confirmed chart bars. There is no intrabar persistence
or realtime execution equivalence claim. Guards validate a bar before economic
mutation and quarantine invalid internal transitions. Pine has no Python deepcopy
transaction here: an unexpected internal invariant failure quarantines its current
state, rather than claiming automatic rollback of a partially mutated object.
No external callback can invoke these internal fill methods.

## Offline evidence and reference discrepancies

The new Book is an independent Python abstract model of the object's intended
accounting contract. It is not a Pine interpreter, translation, transpiler or
compiler. It shares only immutable fixture types/constants/validators with the
preserved Lifecycle, and uses the preserved CandidatePath for signal-stream
comparisons. Static checks separately bind unchanged source blocks and required
transition guards. Neither form of evidence proves that Pine executes the model.

The isolated Lifecycle/Book unit seam can begin at an explicitly prepared bar
inside the window; it accepts prevalidated decisions to isolate arithmetic. The
combined CandidatePath and Pine source require the full November 1 anchor.
Thus the unit seam alone is not a full-stream readiness certificate. Python IDs
also include a fixture namespace; Pine IDs contain the corresponding canonical
Research/candidate/November/bar/direction identity without that test namespace.
No raw ID-string parity across those different namespaces is claimed. The
preserved terminal Lifecycle archives residuals and reports ENDED; Pine keeps
its CENSORED fields, and Book exposes that enum while comparing archive residuals.
These representation differences do not authorize changes to the frozen rules.

Reference comparisons cover both sides, entry/stop/TP/gap paths, literal fee and
quantity expectations, partial/full settlement, UTC, censoring, quarantine and
all twelve deterministic candidate streams with synthetic hourly/volume inputs.
The corpus is not guaranteed to generate a positive signal for every candidate;
separate preserved prevalidated-plan tests cover every registry combination.
The static declaration scanner checks global/type/local indentation scopes and
has duplicate-constant/field mutation tests. It is not a complete Pine grammar
or type checker, and cannot certify compilability.

Reproduce from the repository root using only the frozen environment:

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_pine_checks
```

The runner validates the frozen CPython/NumPy/PCG64 environment before its explicit
allowlist of suites. An audit hook prohibits real repository data/cache reads,
network connections, repository writes and non-allowlisted processes. Direct
policy-denial tests use no file/network access. No historical test discovery or
performance runner is invoked. The preserved synthetic suites are fully rerun;
the full historical regression suite is NOT re-executed. Tests log passed,
failed, errored and skipped counts separately; a skip or guard violation fails
this runner. Baseline preservation is additionally verified by Git identities
and worktree SHA-256, without opening raw datasets or private ledgers.

## Gates deliberately left open

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

There is no new authorization for platform access, protected data, a later phase,
alerts, orders, strategy-emulator parity or research profitability evaluation.
