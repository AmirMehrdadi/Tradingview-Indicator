# Future indicator K control — requirement only

No Pine implementation is authorized or delivered in Phase 2.

The future indicator may expose a configurable `K_cost_stop`, defaulting to **2.5**. The official research parameter is fixed at **2.5** for Stage-0B, 2025 Selection and the final 2026 Holdout; changing a UI input must never modify the official research configuration or historical results.

Any K other than 2.5 must display **EXPERIMENTAL / UNVALIDATED** in the dashboard, signal details, alerts and exports. That configuration must have a distinct configuration fingerprint and cannot inherit official research validation, candidate eligibility, Pass/Fail results or validation badges. Restoring K to 2.5 is necessary but insufficient for any official validation label: symbol, timeframe, candidate, costs, data, engine version and every required gate must also match a genuinely validated official profile.

At this freeze, **no official strategy performance has been validated**, including the default K=2.5. Research Parameter Freeze records parameters only. Every execution gate remains OPEN / UNVERIFIED.

This requirement is separate from `configs/research_v0.2.2.json`; no alternative K is stored as an official configuration, tested, ranked or selected here.
