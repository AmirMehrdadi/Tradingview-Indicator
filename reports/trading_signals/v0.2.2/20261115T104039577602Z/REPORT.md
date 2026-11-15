# Phase 5C — UNVALIDATED — RESEARCH / MANUAL SIGNALS

PRECHECK_STATUS = PASS
BASELINE_COMMIT = 479342971bf042fb9611e3a5aec1c311377cf159
SIGNAL_INDICATOR_SOURCE = IMPLEMENTED_SOURCE_ONLY_UNVALIDATED
OFFLINE_REFERENCE_AND_SOURCE_GATES = PASS

Local root/origin/main and remote main matched the approved baseline. All 191
tracked baseline files matched their committed bytes. Both annotated freeze tag
objects/targets matched locally and remotely. The tracked/staged worktree was
clean; only the pre-existing untracked .DS_Store existed. No push occurred.

## Delivered source and approved visuals

pine/Trading_Signals.pine is a new overlay=true Pine v6 indicator source. Its title
and compact top-right dashboard explicitly state UNVALIDATED — RESEARCH / MANUAL
SIGNALS. No design exploration, chart loading or actual TradingView validation
was performed. This is not a complete validated chart UI or actual broker system.

Confirmed, accepted, queued LONG and SHORT setups own tiny green upward and red
downward markers on their actual signal candles (offset=0). Yellow ENTRY_REF,
red SL, blue TP1 and green TP2 lines/price labels copy the frozen accepted snapshot.
ENTRY_REF is explicitly signal-close reference, not hypothetical next-open fill.
Only the latest setup owns four lines and four labels; replacement deletes the
old objects first. Endpoints are explicit UTC milliseconds, clipped before END,
with extend.none. Text formatting does not modify numeric prices. Anchor bounds
are source-level checks; actual label pixel extents/clipping are not verified.

The dashboard shows selected C-ID/filter abbreviations, setup direction, Research
lifecycle/status, manual opportunity, REAL_POSITION_UNKNOWN and UNVALIDATED status.
Partial TP1/full closure require matching trade ownership and supported filled/
remaining state. Same-bar flags from an old trade cannot classify a new queue.
Unavailable/unmatched state is UNKNOWN; available flat with no setup is NO SETUP.
No account balance, profitability or performance dashboard is added.

Default show/hide controls enable markers, levels and dashboard, with optional
quality diagnostics off. Research diagnostic enable and setup notification enable
both default false. Visual controls have no feedback into the frozen mathematical
or Research path. Table creation is last-bar/window/viewport gated; forbidden or
unknown visible-bar ranges delete it. There is no background/bar coloring.

## Frozen logic, timing and expiration

The complete approved Phase 5B3-Pine kernel before its old Data Window footer is
byte-identical in the new source, apart from the indicator declaration. The
original probe and every baseline file remain unchanged. The new presentation
boundary separates UI helpers/state from the numerical/Research kernel.
C01–C12, EMA/ATR/DMI/RSI/HTF formulas, strict pivots, quantity/cost/risk arithmetic,
fill ordering, accounting, audit, daily stop and censoring are unchanged.
K remains 2.5; fee .055% per side and adverse Research friction .02% per fill remain
frozen assumptions. No experimental K input is introduced. The future requirement
and official configuration remain intact.

DATA_START remains November 1 00:00 UTC, first permitted signal close November 4
00:00 UTC, and December 1 00:00 UTC is exclusive for signals/display. A signal
closing exactly at START belongs to its actual candle opening START-15m under
specification 9.0.2. That explicit close-ownership exception does not backdate a
future decision, create other warm-up signals, or allow pre-anchor seed. Lines
start at its permitted CLOSE. Confirmed hourly [1]/[4] and timestamp ownership
are inherited unchanged. No next-open fill is relabeled as an earlier setup.

Each manual opportunity retains its own two-subsequent-bar deadline, even when a
new setup replaces its drawings. At T+15m it is still unconfirmed; at T+30m it is
EXPIRED after the second confirmed bar. Expiration touches only presentation state.
It never cancels, reprices or resizes Research entry/exit protection or releases
its occupancy. Expired latest levels can remain for a separately labeled pending/
open Research path; they disappear once both manual opportunity is expired and
Research is flat/rejected. All actual/manual positions remain unknown.

The final authorized completed bar can record an internal deadline exactly at
END. It produces no END display or alert and does not consume the next partition's
Open. Deadlines needing later candles stay unresolved, without unauthorized input.
A pre-queue rejected setup has no marker; a later hypothetical margin rejection
retains its valid historical queued marker, preserving no-repaint ownership.

## Alert source contract

One dynamic alert() call supports both LONG and SHORT accepted setups. Its plain
notification identifies UNVALIDATED, C-ID, direction, signal-close UTC milliseconds,
frozen entry_ref/SL/TP1/TP2, canonical owner, REAL_POSITION_UNKNOWN and No order sent.
No alertcondition/static dynamic-field workaround, duplicate combined stream,
execution webhook payload, strategy order or broker API is used.

Notification requires explicit enable, realtime and confirmed-close flags, actual
accepted queue, authorized window, available/non-quarantined state, unique close
ownership and an unsent canonical owner. alert.freq_once_per_bar_close requests
one platform notification for that bar. Deduplication is per execution, not a
claim of durable exactly-once behavior across restarts/instances/server alerts.
No actual TradingView alert was created or delivered in this task.

## Observed offline evidence

| Evidence | Passed | Failed | Errored | Skipped |
|---|---:|---:|---:|---:|
| New independent Python presentation tests | 29 | 0 | 0 | 0 |
| New Pine source/static checks | 14 | 0 | 0 | 0 |
| All previously passing Phase 5B1–5B3-Pine synthetic tests | 197 | 0 | 0 | 0 |
| Preserved Phase 5A temporal tests | 23 | 0 | 0 | 0 |
| Total | 263 | 0 | 0 | 0 |

Guard violations: zero. The exact frozen CPython 3.9.6 / NumPy 1.26.4 / PCG64
environment and process/binary fingerprint matched before execution. Only explicit
synthetic suite allowlists ran under the deny-by-default access guard. No historical
data suite ran; full historical regression was NOT RE-EXECUTED.

Literal fixtures cover owner candle/close, both directions, frozen price mapping,
manual expiry and replacement deadlines, partial/final/rejected/censored Research
states, actual-position uncertainty, labels/line bounds, viewport cleanup, default-
off/confirmed/unique alerts, no end-window exposure, and deterministic replay.
All 32 presentation-toggle combinations preserve the supplied immutable decision
stream and execution serialization. Static checks bind the whole frozen kernel,
resource caps, source gates, dynamic messages, append/cleanup ownership and no
forbidden execution API or new K parameter. The limited lexical scan found no
duplicate global/type/local declarations; conservative reserved-name checks pass.
These are Python/static checks, not a Pine compiler, chart render or runtime test.

Reproduce from repository root:

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5c_checks
```

See tests.log for exact test IDs/counts, static_scan.json for declaration/source
review and verification.json for source/environment/configuration hashes and
baseline/tag preservation evidence. The post-commit external manifest records
all committed additions and independently verified review ZIP bytes/blob identities.

## Resource limits, preservation and open gates

Source ownership caps are four lines, four labels, one 2x8 table and two marker
series. Manual records are bounded at 2592, the maximum permitted monotonic setup
closes in this fixed 27-day window, and a forward cursor expires each once. A
presentation capacity failure blocks UI/notifications, preserves records and leaves
Research unchanged. The inherited Research audit cap is unchanged. These are
source bounds, not observed platform capacity, rendering or memory evidence.

All 191 baseline blobs and 98 prior report artifacts remain unchanged. Only new
source/reference/tests/runner/protocol and versioned evidence are added. Both
annotated freeze objects and targets, official parameters and original specification
are preserved. No code/history rewrite, new tag, final README or Phase 5D is included.

SOURCE_SHA256 = dfed05db3a4940e033bc9314dd751921a8432c18af1dd5403dd495693f731add

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

The intended source UI and notification contracts are implemented; real compiler,
rendering, viewport, rollback/persistence, object resources and alert delivery are
remaining execution gates. Source masks do not establish platform input isolation.
No safe TradingView environment was demonstrated or used. No market-data dataset,
protected cache, private ledger, Selection, Holdout, Funding implementation or
profitability research was accessed/performed. Local implementation and review
package only; no push. Stop for independent review.
