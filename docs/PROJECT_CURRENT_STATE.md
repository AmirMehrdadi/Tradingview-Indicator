# TradingView Indicator — CURRENT PROJECT STATE

**Snapshot UTC date:** 2026-11-15  
**Project:** `AmirMehrdadi/Tradingview-Indicator` (private)  
**Last independently verified remote `main`:** `e0f94e4f22461f61bed42599c3d34ec702b927b7`  
**Tree:** 211 tracked files; Phase 5D only adds seven paths and preserves all 204 previous blob IDs/file modes.  
**Next gated work:** verify whether the handoff documents are durably published; if already published, proceed directly to **read-only safe TradingView environment/technical validation design**. No Phase 5E implementation authorized; no Pine execution authorized.

## What is done

- **Design v0.2.2 FROZEN** via annotated tag; separate official **K_cost_stop=2.5** research tag FROZEN.
- Python Development loader/Stage-0A descriptive work, Stage-0B **12 independent 2023/24 pre-Funding feasibility paths**, Funding observed-data acquisition, incomplete calendar audit, synthetic Funding lifecycle.
- **Phase 5A, 5B1, 5B2, 5B3, 5B3-Pine, 5C, 5D** source written/published (5B3 is Python synthetic fixture; 5B3-Pine is later separate source). Indicator: `pine/Trading_Signals.pine`; strategy: `pine/BTC_Strategy.pine`.
- Phase 5D publication **GitHub independently VERIFIED**: commit `e0f94e4f22461f61bed42599c3d34ec702b927b7`, parent `eb41c4ecf52a445a5ce32464a824359abb7bbb4d`, 7 additions, 211 tracked, original 204 blobs preserved. Last synthetic/static regression **273 distinct PASS** as per committed Codex report (9 new + 264 reused); NOT Pine compile/runtime proof.

## Important incomplete/locked gates (DO NOT UPGRADE)

```
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
HISTORICAL_FUNDING_DATA = PARTIAL_DATA
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
PRE_HOLDOUT_FREEZE = NOT_CREATED
```

No TradingView compilation, chart, Strategy Tester, live order or history access took place in Phase 5D. Strategy `slippage=0` / `PARITY_SLIPPAGE_TICKS=0` is a **placeholder**, not official N; `diagnosticEnabled=false`, `PARITY_VALIDATED=false`. Actual Pine OCA, same-bar brackets, native fills, margin, contract pointvalue mapping, UTC and protected-date isolation must be proven separately. Mandatory execution T06/T07/T13/T17/T18/T22/T23 remain open.

**Funding blocker:** historical 2023/24 BTCUSDT settlement-calendar/exception coverage not independently demonstrated, despite 1095/1098 observed valid settlements. Initial 2023 boundary Mark is structurally not exposure-required, but that does NOT certify calendar completeness. Do not substitute missing settlements with zeros; no final Funding-adjusted result.

**Protected dates:** 2025 Selection **SEALED**; 2026 Jan–Oct final Holdout **SEALED**. Technical November profile must start inputs at 2026-11-01 00:00 UTC, first eligible SIGNAL CLOSE 2026-11-04 00:00, end exclusive 2026-12-01 00:00 (only currently available data allowed). **No ordinary TradingView chart loading before independently evidenced safe environment.**

## Frozen identities

| Item | Object / SHA | Target |
|---|---|---|
| Original design annotated tag `v0.2.2-design` | `638ec6d99413c8dbc82a111209015953809ced08` | `ac8fc4bb9b66a59c7224aaec1630a594b41d7e80` |
| Research annotated tag `v0.2.2-research-parameters` | `826b05146e99a5a87e9951da9b4e0ac2deea1d09` | `4bc7447755ef7a9dbd8832221f2ded5afc21401f` |
| Official config SHA-256 | `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37` | `configs/research_v0.2.2.json` |
| Phase 5D Pine Git blob SHA-1 | `212a9e86ab534bee738ff14501639285a29ef63f` | `pine/BTC_Strategy.pine` at current HEAD |

Research defaults: BTCUSDT linear perpetual 15m/confirmed 1h; K=2.5 exactly; 0.055% fee per side and 0.02% adverse Research friction *assumed*; 10,000 USDT starting balance; 0.25% risk/entry; 2x notional ceiling; frozen 1.5R/2.5R two-part exits, 1% UTC daily stop, no Breakeven/Trailing. Research vs TradingView Parity costs differ by model; never conflate. No C13 and no K retuning.

## Exact immediate next action

1. **Conditional handoff publication:** first check if these three files are already present in the current GitHub `main`. If present and reviewed, **skip publishing them again**. If not present, review the generated copies and follow the ordinary scoped Codex **local commit -> review ZIP and external Manifest -> independent ChatGPT review -> separate no-force branch-only push**. Do **not** edit frozen tags/spec or past reports. **At this 2026-11-15 baseline snapshot the documents were not yet committed; this historical fact must not be misread as their publication status after later commits.**
2. **Then start a fresh, read-only planning task for a SAFE_TRADINGVIEW_ENVIRONMENT gate**, before compiling or loading Pine on any chart. Determine exact platform-level protections for chart history and `request.security`, no Holdout leakage and evidence collection. Explicitly authorize later real execution separately.
3. After a proven safe platform, test compiler, indicator/strategy actual execution and T06/T07/T13/T17/T18/T22/T23; freeze Parity N_ticks/quantity mapping and build real Pine/Python parity evidence. Separately resolve Funding-calendar gap and complete authorized Development research before locked Selection/Holdout ever open.

## Working contract

ChatGPT guidance in **Persian**; **Codex prompt and response in English**. For each task, state **hardness /10, recommended Reasoning Low/Medium/High/Extra High and why** before the prompt. Test policy in `docs/TEST_EFFICIENCY_POLICY.md`: reuse tests, focused during dev, one applicable final offline regression, disclose new/reused/distinct/executed counts and elapsed time. Do not rerun suites for packaging/publishing.

At snapshot Codex reported tracked/staged local worktree clean; allowed only `.DS_Store`, `data/.DS_Store`, `docs/.DS_Store`, `reports/.DS_Store`, `research/.DS_Store` as untracked **regular** files. This is a local report, not verifiable from GitHub. Local repo path: `/Users/mehrdadi/Documents/ChatGPT/Tradingview Indicator`.

Before any work, **independently fetch current GitHub `main`** and both tag objects/targets. If newer than `e0f94e4f...`, reconcile changes; treat this document as its dated baseline rather than asserting its HEAD is live-current. Record future state in a reviewed, date-stamped update when material. Full context: `docs/PROJECT_HANDOFF_FULL.md`; canonical rules: `STRATEGY_SPEC_v0.2.2.md` and `configs/research_v0.2.2.json`.
