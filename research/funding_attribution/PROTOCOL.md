# Conditional Development historical Funding adapter

Authority: unchanged v0.2.2 design, frozen research configuration and the explicit
Development-only Funding-attribution request. No official profitability validation,
Selection, Holdout, execution-gate bypass or publication is authorized.

The user's report of an official Bybit communication is accepted as
USER_ATTESTED_OFFICIAL_CALENDAR: 1095 settlements in 2023, 1098 in 2024, at
00:00/08:00/16:00 UTC. This is not an independently retained primary document.
All results are CONDITIONAL_DEVELOPMENT_DIAGNOSTIC. HISTORICAL_FUNDING_DATA remains
PARTIAL_DATA and OFFICIAL_STRATEGY_PROFITABILITY remains UNVALIDATED.

## Inputs and access

The fixed source runs are Stage-0B 20261114T183819594592Z, Phase 4A
20261114T192333525994Z and the frozen Stage-0A datasets 20261114T165617836854Z.
Only the original 24 annual C01–C12 paths are accepted. No caller-supplied paths,
candidate changes, years, cost overrides, network transport or acquisition exist.
Baseline 9d451025c8d748a21987c59f35d8b5a0564e5e64 has 222 tracked files; every
baseline file/mode and both annotated tags are checked. Frozen numerical
fingerprint/PCG64 and original source hashes are checked. Existing guarded
authorization, snapshot validation, private-ledger audit and exact Phase 4C
arithmetic are reused. The fixture-only Phase 4C lifecycle is not relabeled or
relaxed to accept historical records; only its pure arithmetic and scenarios are
used. No original source, test, report, specification or configuration is edited.

The process guard reuses OfflineGuard and adds a finite allowlist of the four
Development CSVs/manifests (including their already frozen warm-ups), original
24 private ledger files/checksums and exact Phase 4A snapshot members. Other data
paths and network activity are denied. Snapshot request metadata is authorized
before market-body decoding; all hashes/identities precede integration. CSVs are
hashed only, not parsed or replayed. Private source permissions and Git exclusion
are verified by the existing Stage-0B audit. Source mismatch aborts without
regeneration or substitution. The original public reports do not publish the
private checksum-file digest: current retained checksums and original public
event/count audit are verified, without claiming a new independent historical
engine replay or stronger original cryptographic anchor.

## Accounting contract

Ledger plans, canonical entry/leg/OCA identities, UTC phases, quantity steps and
pre-Funding cash/settled/sizing/day snapshots are validated and left untouched.
The additive adapter reconstructs exposure from execution events; it never calls
Engine.run or calculates a new trading path. No intrabar fill timestamp is
invented. PRIOR_BAR exits at t precede Funding(t); old OPEN exits follow base
Funding; new OPEN entries are exempt. Alternate precedence previews only the
old position's OPEN exits to obtain a smaller Funding quantity, without mutating
the original event order or applying that exit twice.

Every observed annual rate is required to match the full user-attested grid;
zero is a valid record, absence is an error. Duplicate/conflicting rates/Marks,
unlinked minutes and off-15m settlements fail closed. All requestable prior-minute
Marks are required. The sole unavailable first-2023 Mark is exempt only because
the independent annual path starts Flat before initial Funding. Its raw absence
is not repaired, and neither raw nor independently documented calendar completeness
is certified. Mark Close/Low/High retain APPROXIMATE_MARK_PREVIOUS_1M_CLOSE,
exact_tick=false and guaranteed_settlement_bounds=false.

Six registered scenarios cross Close/Low/High with
FUNDING_BEFORE_OLD_OPEN_EXIT / OLD_OPEN_EXIT_BEFORE_FUNDING. Base is Close/Funding
first. Exact quantity-times-price-times-rate and accumulation reuse Phase 4C's
context-independent Decimal helpers. Same-path, same-entry, same-settlement
attribution and global/per-entry sums must conserve. Each accounting result is
repeated in memory to verify deterministic hashes; this is not a second execution
of the historical strategy. Year/candidate state resets independently.

Pre-Funding net is the exact sum of decimal representations of the original
stored realized and fee components. Those execution components were derived by
binary64 Stage-0B; they are not newly recomputed decimal fills. Embedded execution
friction is not charged twice. Planned R = initial BTC quantity times the frozen
stored pre-cost price risk, validated against entry_ref/SL. Completed trade_R_net
uses a local 50-digit Decimal division; Funding itself is exact. Censored entries
retain their own partial realized accounting and Funding, without completed-trade
R or terminal mark-to-market. Nothing changes signals, sizing, daily eligibility,
occupancy or the original pre-Funding shared balance.

## Outputs and checks

Private results are create-only under ignored data/stage0b_private/funding_attribution/
with 0700 run directories and 0600 files. Public reports contain only coverage,
conservation and anomaly counts, source identities/hashes, deterministic output
hashes, test metadata and limitations. No per-trade financial values, profitability
metrics, candidate rankings or selection are exported. Reports and snapshots are
immutable; a failed execution is never silently replaced or resumed.

Focused command:
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_funding_attribution_checks --focused

Final dependency-scoped offline regression (once after final executable edits):
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m tests.run_funding_attribution_checks

It includes all new fixtures, all Phase 4C lifecycle fixtures, Phase 4A synthetic
tests and Stage-0B LifecycleTests. No tests in these modules are skipped. Historical
cache-replaying freeze/feature tests and unrelated Pine suites are not selected;
full historical regression is NOT RE-EXECUTED. Actual counts and every development
failure/rerun are recorded separately, without summing overlapping executions.

The fixed conditional run command, authorized for this task only:
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.funding_attribution.runner

All Pine compilation/runtime/parity and SAFE_TV_ENVIRONMENT remain UNVERIFIED.
2025_SELECTION and 2026_FINAL_HOLDOUT remain LOCKED_NOT_ACCESSED. A successful
conditional run is not official research acceptance or a Funding data upgrade.
