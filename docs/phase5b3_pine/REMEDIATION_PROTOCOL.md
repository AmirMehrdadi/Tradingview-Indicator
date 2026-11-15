# Phase 5B3-Pine identity and fill-audit correction — UNVALIDATED

This protocol supplements the original preserved Phase 5B3-Pine protocol and
reports. Independent review found two frozen-contract omissions in ae2dc037:
its ID lacked run_id (specification 6.5), and its fill-ID array/counters did not
retain complete economic fill evidence (6.6). The earlier source-completeness
claim was too broad. Those omissions are corrected at source level here; genuine
Pine compilation, runtime and parity remain unverified. Earlier artifacts are
preserved as historical evidence, not silently rewritten or re-endorsed.

## Explicit run ownership

The caller supplies researchRunId through an input.string, default
phase5b3-pine-v1. Valid names are 1–64 ASCII letters, digits, underscores or
hyphens. Empty names and separators/whitespace are invalid. Invalid configuration
quarantines before economic processing. This is an identity-integrity control,
not a trading signal/filter or a new candidate parameter.

Canonical trade/entry identity is exactly:

```
run_id/Research/C-ID/November2026/signal_bar_open_utc/direction
review-A/Research/C01/November2026/1793749500000/1
```

The UTC component is the integer epoch-millisecond Open of the confirmed SIGNAL
bar, not entry Open or signal close. Direction is 1 or -1. Candidate and all
clock/price/quantity decisions remain frozen. Entry fill is canonical/ENTRY;
reserved exit/fill identities are canonical/L1 and canonical/L2; independent
hypothetical OCA names are canonical/OCA1 and canonical/OCA2. The source freezes
all of them from the same root on queueing. None are actual broker order IDs.

The default name is deterministic and reproducible, NOT automatically unique.
A caller comparing independent runs/instances must explicitly assign distinct,
non-secret run IDs and retain the chosen value alongside source/config/input
hashes. Reusing the same ID and inputs intentionally reproduces the same keys.
No instance GUID, wall-clock nonce, credential, account ID or automatic cross-
instance uniqueness is inferred. Pine input-change/restart semantics for this
artifact remain a genuine runtime gate.

Preserved Python engines continue to use their historical fixture-prefixed IDs.
The new observer maps their immutable decisions to the complete canonical audit
namespace without altering their IDs or serialized accounting. That preserved
legacy representation is not evidence that the original Pine schema was complete.

## Append-only in-memory Research tape

ResearchBook.audit holds newly allocated ResearchAuditRow objects. Each append
copies primitive values; no row is subsequently mutated or evicted. This is a
source-level in-memory tape for one script execution, not durable storage, a
TradingView export, a validated runtime log, or a private-account ledger.
No audit monetary fields are plotted or emitted as alerts. Existing Data Window
plots remain byte-identical with their strict confirmed-close/window masks.

Every row retains sequence, canonical trade ID, event kind, unique fill ID for
fills, exact economic timestamp/phase, leg, integer steps, raw trigger price,
economic fill price, fee, two remaining reservations, frozen reserved quantities,
exited quantity, planned total, actual entered total, per-trade fill count,
observation price and remaining-exposure notional, occupancy, release timestamp,
per-trade quality code/classification, and internal cash/settled/UTC-day snapshots.

Phase codes are 0 SIGNAL_CLOSE, 1 OPEN, 2 PRIOR_BAR, 3 PARTITION_END. Observations
are reconstructed at the confirmed bar close using the existing Research order;
the tape does not purport to timestamp realtime callbacks. Observation/exposure
price is the raw price at the modeled check, not a Bybit Mark or exact tick.
Remaining exposure notional is remaining_steps/1000 * observation_price. The
source keeps exact integer steps for conservation; binary64 economic fees are
copied directly from the existing fill calculation without tick reconstruction.

| Row kind | Economic meaning |
|---|---|
| PLAN_QUEUED | Busy with frozen reservations; zero entered steps; no fee, price or fill ID |
| ENTRY | Full frozen entry fill, adverse economic price, actual fee and two open legs |
| EXIT | Exactly one remaining reserved leg, TP/STOP classification, economic price/fee and residuals |
| FULL_FLAT_SETTLEMENT | Last exit followed by settlement and occupancy release at the same timestamp/phase |
| QUALITY | First occurrence of one anomaly classification for this trade; no fictitious fill/fee |
| ENTRY_REJECTED_MARGIN | Release with zero entered steps/fills and no economic fill price or fee |
| PARTITION_CENSORED | Archive unfinished exposure after final PRIOR_BAR; no exit, fee or full-flat release |

EXIT is captured after its quantity/cash mutation and before the full-flat
settlement branch. Thus the final EXIT row may have zero remaining steps while
occupancy is still reserved; the immediately following FULL_FLAT_SETTLEMENT row
records its release and updated settled snapshot at the same economic time.
Partial EXIT rows keep the prior settled balance. Censor rows retain occupied
unresolved hypothetical exposure; they are not flat releases. Rejection and
censoring do not fabricate zero-priced fills or zero-fee executed orders: their
fillId is empty, steps zero, price/fee na. total is planned; entered is actual.
The invariant exited+remaining1+remaining2=entered therefore also covers rejected
and queued plans, for which entered is zero. Reserved planned quantities are
retained separately to explain rejected/censored plans.

Quality bits retain the original mapping: ENTRY_DEVIATION 1, EXECUTION_ANOMALY 2,
RISK_OVERRUN 4, NOTIONAL_OVERRUN 8, MARGIN_MODEL_EVENT 16,
UNCERTAIN_INTRABAR_ORDER 32, ENTRY_AT_OR_BEYOND_SL 64,
FILL_FRICTION_CROSSED_TP 128. Existing path-wide flags are unchanged; the audit
additionally resets its per-trade mask on queueing. Each first classification
appends a non-fill row, so later classifications remain linked without rewriting
an earlier entry record. A new trade does not inherit the preceding trade's
mask. No unfavorable fill is removed, resized or recomputed by instrumentation.

## Bounded storage and fail-closed behavior

AUDIT_CAPACITY is a fixed 20,000-row operational limit, not a research parameter
or profitability filter. Before processing any economic bar mutation, the source
requires room for 16 rows. At most 13 are possible in one bar: one entry, eight
first quality bits, two exits, one full-flat release and one terminal censor.
Some are mutually exclusive; 16 is conservative. Each subsequent close queue
separately requires one row before plan/consumption mutation. Appending also
checks its own capacity defensively.

Insufficient capacity sets auditBlocked and quarantined, retains all existing
rows/reservations and prevents further valid economic processing/acceptance.
No oldest-row eviction, truncation, aggregation, silent evidence loss or invented
fill is allowed. The run is invalid after that failure. Internal callback methods
have no external callers; the bar/queue budgets guard their production source
paths. Unexpected internal failure retains the original documented Pine
transaction limitation: no Python-style automatic rollback is claimed.

The platform may hit memory, object, string or execution limits before this
chosen row count. No claim is made that TradingView can sustain 20,000 rows;
that requires actual compilation/runtime evidence. A platform error is an invalid
run, never permission to drop audit evidence or claim validation. Source-level
bounds do not establish platform-level data isolation or persistent exports.

## Offline tests and reproducibility

The additive AuditedLifecycle is a synthetic observer of the preserved Lifecycle.
It intercepts existing event callbacks and adds tape records, recomputing expected
fees from immutable fill quantity/price. It does not change the engine's economic
transitions. Tests compare its inherited serialized accounting/events with the
unchanged engine at each step and on deterministic CandidatePath streams.
Literal expected quantities/prices/fees independently test important records.
Static checks separately bind the new Pine fields, canonical ID, append sites,
capacity guards and unchanged arithmetic/decision/indicator/plot blocks. This is
not a Pine translation, interpreter, compiler, or genuine Pine audit output.

Original-source negative reproduction (expected exit 1, two assertion failures):

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_pine_remediation_checks --original-source-red
```

Corrected source and all 167 preserved synthetic tests:

```
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_phase5b3_pine_remediation_checks
```

Both commands verify the frozen environment before using explicit suite allowlists
and the preserved offline guard. No historical discovery or data runner is invoked.
The full historical regression suite is NOT re-executed. The original-source mode
reads only the approved Pine Git blob and intentionally fails the two new source
contract tests; those failures are not hidden in the passing regression counts.

No TradingView, real market data, protected cache, private ledger, Funding or later
phase work is authorized or performed. All 174 pre-Phase-5B3-Pine files and all
prior reports remain unchanged. The correction changes one Pine file and adds
its own fixtures, tests, protocol and timestamped evidence. No push is authorized.

PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
