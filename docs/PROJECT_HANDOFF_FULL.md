# TradingView Indicator — FULL PROJECT HANDOFF

**Snapshot:** 2026-11-15 | **Repository:** `AmirMehrdadi/Tradingview-Indicator` (private) | **Branch:** `main`  
**Independently verified remote HEAD:** `e0f94e4f22461f61bed42599c3d34ec702b927b7`  
**Verified Git tree:** 211 tracked files, Phase 5D commit has **7 additions only**; all 204 blobs/file modes from its parent preserved.  
**Status:** Phase 5D **SOURCE IMPLEMENTED AND PUBLISHED**, **PINE COMPILE/RUNTIME/PARITY UNVERIFIED**; research profitability **UNVALIDATED**.  
**Scope:** handoff/snapshot **only** — this file is not a new design freeze, research permission, execution evidence, selected candidate, or validation result.

> **START HERE when resuming in a new ChatGPT Project conversation.** Read this file, then `docs/PROJECT_CURRENT_STATE.md`, then fetch the live private repository and verify `main`, the frozen tags, and the referenced authoritative sources. If HEAD differs from the snapshot, reconcile from actual commits/reports instead of assuming the snapshot remains current. Never substitute a chat summary for the immutable source of truth.

## 1. Executive description: what we are building

A **semi-automatic, manual-decision trading research and signal system** for **Bybit linear BTCUSDT USDT perpetual**, primarily on **15-minute standard OHLC candles**, with optional **confirmed 60-minute** higher-timeframe logic. The aim is to test a **single frozen strategy family of twelve pre-registered candidates**, create a TradingView indicator showing Long/Short opportunities, frozen Entry/SL/TP1/TP2 and alerts, run an independent Python research engine, and provide a separate Pine `strategy()` for **TradingView broker-emulator simulation only**. Live order execution remains the trader's responsibility.

**V1 prohibits:** authenticated Bybit trading, real order placement, broker integrations, auto-trading webhooks, changing the strategy based on unseen Selection/Holdout outcomes, claiming profits, or presenting synthetic/static tests as actual Pine compilation. V1 is not a trading recommendation or proven profitable system.

**Delivered source paths:**

- `pine/Trading_Signals.pine` — Pine v6 indicator, overlay, setup markers, four price levels, compact dashboard, optional manual notifications, Research diagnostics; **source-only**.
- `pine/BTC_Strategy.pine` — Pine v6 **native simulated** `strategy()` adapter, entry plus two separately sized protective brackets, internal native observations; **source-only**, orders default disabled.
- `research/` — Python Development loader/indicators, Stage-0A and Stage-0B, Funding acquisition and synthetic Funding lifecycle; strict data guards.
- `tests/`, `reports/`, `docs/`, `configs/`, `research_freeze/` — test/provenance/report/frozen-parameter records.

## 2. Source-of-truth hierarchy and non-negotiable freezes

1. **Immutable original technical design:** `STRATEGY_SPEC_v0.2.2.md` from annotated **`v0.2.2-design`**, target commit `ac8fc4bb9b66a59c7224aaec1630a594b41d7e80`, annotated tag object `638ec6d99413c8dbc82a111209015953809ced08`. Its header's historical `NO IMPLEMENTATION / K NOT FROZEN` is a **historical snapshot**, NOT the current project status. Never rewrite it to update history.
2. **Official Research Parameter Freeze addendum:** `research_freeze/v0.2.2/RESEARCH_PARAMETER_FREEZE.md` and `configs/research_v0.2.2.json`, anchored by annotated **`v0.2.2-research-parameters`** object `826b05146e99a5a87e9951da9b4e0ac2deea1d09`, target `4bc7447755ef7a9dbd8832221f2ded5afc21401f`. It legitimately fills the design's previously open K decision without changing the design tag.
3. The stage-specific protocols and code implement the above contract; they **do not supersede** it. Later dated reports are evidence of particular stages, not permission to change frozen rules. `docs/TEST_EFFICIENCY_POLICY.md` governs engineering workflow only.
4. **Pre-Holdout freeze** is a third, separate, **NOT YET CREATED** gate. Do not confuse it with either existing tag. No 2025 Selection or 2026 final Holdout has been opened.

**Official research K:** `K_cost_stop=2.5` exactly, inclusive predicate `planned_risk_price / roundtrip_cost_per_btc >= 2.5`, **no epsilon**. Cost proxy can therefore consume at most 40% of planned Stop distance. This K is the user's deliberately approved, non-optimized policy based on 2023–24 descriptive distributions; it is **not a demonstrated performance optimum**.

**UI K future requirement:** `docs/FUTURE_INDICATOR_K_REQUIREMENT.md` permits a future configurable K with **default 2.5**, but any other value must be prominently **EXPERIMENTAL / UNVALIDATED**, with distinct fingerprints and no inherited results. Neither published V1 Pine file currently exposes a user K input. Do not quietly add that capability to a source-only parity/validation task.

**Official research assumptions** (NOT verified account costs): 0.055% taker commission per fill/side (`0.00055`) and 0.02% adverse Research friction per fill (`0.0002`). The saved contemporary instrument snapshot is treated as `HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION`, not proof of 2023–26 rules. Tick `0.10 USDT`; BTC quantity step `0.001 BTC`; minimum qty `0.001 BTC`; minimum entry notional `5 USDT`; maximum Market `150 BTC`; maximum Limit `1500 BTC`. Reducing TP/Stop legs are independently qty/step checked; closing min-notional is assumed exempt. TradingView quantity/contract/pointvalue equivalence is **UNVERIFIED**.

**Numerical reproducibility:** recorded **CPython 3.9.6, macOS arm64, NumPy 1.26.4** with hash-pinned `requirements-research.lock`; environment manifests in `research_freeze/v0.2.2/`. Wrapper `sh tools/research_python.sh` sets registered numerical/process controls. RNG contract is NumPy `Generator(PCG64(20261114))`, never a guessed or version-swapped generator. Different runtime/platform requires revalidation, not automatic numerical-parity claims. Official config SHA-256: `196dfd9b9bc88007fbaa1be8172b861ec847c18ec591346c4f2a9e177256ff37`; original specification SHA-256: `b9f35d752f4748a68a7d7677112a67007acb94a3266d33bd8b763991ef89a1c6`.

## 3. Frozen signal logic (implementation must not optimize it)

**Baseline B:** at confirmed 15m candle `i`, Long requires `EMA20[i] > EMA50[i]` and `C[i] > EMA50[i]`; Short is strictly reversed. EMA seeded from first authorized Close; ATR14 is Wilder RMA with first 14 TR seed; first TR = H-L. Binary64 without intermediate indicator rounding. No missing-candle interpolation.

**Pullback:** select the latest qualifying prior candle `p` with `i-p` in **2..5** whose High/Low touches EMA20 and penetration is `<=0.75*ATR14[p]`; all intervening closes must remain strictly on the correct side of EMA50. Long confirmation candle bullish, above EMA20 and strictly above prior High; Short is mirror below prior Low. Each accepted `(candidate, direction, pullback identity)` is consumed once. No new signal while pending/position busy.

**Pivot/Stop:** strict manual 3-left/3-right pivots, equality to *any* neighbor invalidates the pivot, and pivot becomes available only on `j+3` close. Use latest confirmed appropriate pivot from last 80 bars. Long `SL_raw = pivot_low - 0.15*ATR14`, rounded **down** to tick; Short `SL_raw = pivot_high + 0.15*ATR14`, rounded **up**. Entry reference is SIGNAL close, **not** next Open. Planned stop distance must be within `[0.75*ATR14, 2.5*ATR14]` inclusive. TP1 = `1.5R`, TP2 = `2.5R`; round Long TP down / Short TP up conservatively; maintain proper distinct order. **No Breakeven and no Trailing**. An obsolete post-rounding TP1 >=1.5R gate was intentionally removed: do not resurrect it.

**Filters** (only as listed): `R` = ADX14 >=20, EMA separation >=0.25 ATR14, ATR14 <=2x median preceding 96 ATR; `H` = confirmed-only hourly Close/EMA50 and slope, Pine security offset `[1]`/`[4]` with `lookahead_on` in **HTF expression**; `V` = current volume >=1.2x prior 20-volume SMA; `M` = RSI14 Long >=55 / Short <=45; `Q` = body <=1.2 ATR, range <=1.8 ATR, and known opposing confirmed pivot with >=1.5R clearance toward TP1. No arbitrary additional filter.

| ID | Fixed candidate | ID | Fixed candidate |
|---|---|---|---|
| C01 | B | C07 | B+R+H |
| C02 | B+R | C08 | B+R+V |
| C03 | B+H | C09 | B+R+M |
| C04 | B+V | C10 | B+H+V |
| C05 | B+M | C11 | B+R+H+Q |
| C06 | B+Q | C12 | B+R+H+V+M+Q |

**No C13, free-form ablations, threshold optimization, post-result filter changes, lower sample minima, or hidden parameter sweeps.** Only one selected C-ID runs within a given Pine instance; other C-IDs need independent annual research paths in Python.

## 4. Frozen sizing, lifecycle and order semantics

- Research initial balance **10,000 USDT**; per-entry risk budget **0.25% of settled-flat balance**; maximum entry notional **2x settled-flat balance** using signal-time `entry_ref`. Qty computed from risk including model-specific cost proxy, capped by notional then **floored** to BTC step. Do not resize after a gap or after observing the next Open.
- Convert qty to **integer steps**; `TP1_steps=floor(total_steps/2)` and `TP2_steps=total_steps-TP1_steps`. Each leg must be independently valid for step/min quantity or reject entire signal. For 3 steps the division is **1+2**, never rounding both to two. Sum of two exits plus remaining == full entry; no overfill/underfill.
- Signal evaluated ONLY at confirmed Close, market entry and **both protective `strategy.exit()` brackets with frozen explicit `qty`, SL and appropriate TP** submitted together in the same signal-close computation. Intended market Fill occurs at **next bar Open**, never at signal Close; actual same-entry-bar bracket activation requires real TradingView verification.
- Two distinct exit IDs, two OCA names and the same matching `from_entry`; no `qty_percent`; filled legs never re-created. TP1 alone never releases occupancy or settles shared balance. On confirmed full Flat cancel sibling orders and free the path. Rejection without real evidence stays **UNKNOWN**; do not invent specific native Margin failure. Do not delete adverse filled trades due to anomaly.
- Unique trade key components: `run_id / execution_mode / C-ID / partition / signal_bar_open_utc / direction`, with derived entry/TP/SL/OCA identities; deterministic run IDs must be deliberately made distinct for compared instances. Research's hypothetical audit/IDs and TradingView native orders are not the same source of fill truth.
- Research Gap rule: directional deviation from signal-ref stop risk uses **actual Fill**, and **unfavorable deviation >15% of planned Stop risk** flags `ENTRY_DEVIATION`; favorable gaps do not. Invalid positive-direction risk is an `EXECUTION_ANOMALY`. Research known-Open fills precede the rest of intrabar; afterward ambiguous TP+SL is **Stop-first on remaining quantity**. Gap-through-stop executes at adverse Open under Research friction, not at frozen nominal SL. Parity obeys native broker emulator behavior; do not force Research Fill ordering onto native Pine.
- **UTC daily loss stop:** after FULL Flat only, settled snapshot updates; at -1% or worse of midnight `day_start_balance`, block NEW entries for that UTC day. TP1 partial, floating PnL and Funding do not update this shared gate. Do not close a position merely because the daily gate activates; preserve its protective orders.
- Ordered accounting timeline at boundary `t`: `PRIOR_BAR -> PARTITION_END if applicable -> UTC_DAY_RESET / PARTITION_START -> FUNDING -> SIGNAL_CLOSE -> OPEN -> INTRABAR`. Close at partition end may exit, **Open at exact end cannot** enter old partition. Annual independent runs start Flat at 10k with fresh state; no carrying positions across annual partitions.
- Research 50% margin assumption per direction; reject insufficient next-Open entry without fee or resizing; preserve consumed accepted signal. Existing-position margin model is a diagnostic; `MARGIN_MODEL_EVENT` invalidates research evaluability; it is NOT Bybit's real liquidation model.
- Censor positions remaining at research partition end, **without artificial exit**, exclude the whole censored trade from completed-trade PnL/Bootstrap while maintaining occupancy until end. In Pine, a position still open at technical `TRADE_END` **must retain protective brackets**; the post-window position is recorded `CROSSED_WINDOW_END`, not forcibly closed to manufacture a backtest result.

## 5. Research versus TradingView Parity are distinct models

| Area | Python Research (official economic research) | Pine TradingView Parity (technical comparison) |
|---|---|---|
| Commission | Assumed 0.055% per side/fill | 0.055% `strategy.commission.percent`, subject to actual properties snapshot |
| Execution friction | 0.02% adverse **percentage per fill**, including conservative TP haircut | `strategy(slippage=N_ticks)` **integer ticks**, applied to Market/Stop, not TP Limit |
| Ambiguous intrabar path | Frozen Research Stop-first after known Open | Native TradingView broker emulator OHLC model; inspect actual behavior |
| Cost floor / size | Research percentage cost proxy | Model-consistent native Parity tick proxy, `EXPECTED_MODEL_DIFFERENCE_COST` if inputs differ |
| Funding | Required for final net research, with scenario sensitivity | **No Funding in Strategy Tester Parity**; compare pre-Funding costs only |
| Evidence | Development offline Python state/tests; Funding incompleteness remains | **UNVERIFIED** compile, behavior, property/pointvalue mapping |

**Current strategy source:** `pine/BTC_Strategy.pine` is Pine v6, `currency.NONE` (intended chart quote currency, mapping unverified), initial capital 10000, margin_long/short=50, no pyramiding, no tick/fill recalculation, no process-on-close, no bar magnifier, no trade-through extra assumption; `slippage=0` and `PARITY_SLIPPAGE_TICKS=0` are **explicit UNVALIDATED placeholders**. Official `N_ticks` has **not been frozen**. `PARITY_VALIDATED=false`, `diagnosticEnabled` defaults **false**. Never interpret these as approved Parity settings or proof of live safety. Strategy source registers native entries/closed rows, distinguishes unknown vs observed failures, protects pending/active ownership and attempts final-Flat cleanup; actual broker-emulator behavior not yet proven.

**Current indicator source:** `pine/Trading_Signals.pine` includes green/red setup markers, yellow `entryRef`/red SL/blue TP1/green TP2 lines, a top-right dashboard, separately enabled notifications and manual opportunity expiry after two subsequent confirmed candles. It uses internal hypothetical Research state, not actual account position. Explicit label `REAL_POSITION_UNKNOWN`, `SOURCE ONLY / COMPILE UNVERIFIED`. Its source-only duplicate `table.cell(...text_color...)` regression was fixed in corrective commit `eb41c4ec...`; do not reintroduce it.

## 6. Data partitions and protected-data boundary — CRITICAL

| Partition | Exact UTC window | Current permission/status |
|---|---|---|
| Development | `[2023-01-01 00:00, 2025-01-01 00:00)` | Previously accessed in controlled Development-only workflows. Existing verified input hashes; no arbitrary new access without scope checks. |
| Selection | `[2025-01-01 00:00, 2026-01-01 00:00)` | **LOCKED_NOT_ACCESSED**. Do not read/fetch/cache/preview. |
| Final Holdout | `[2026-01-01 00:00, 2026-11-01 00:00)` (Jan–Oct 2026) | **LOCKED_NOT_ACCESSED**; **one-shot only**, after future pre-Holdout tag and explicit gate satisfaction. |
| Technical November Parity | Inputs `[2026-11-01 00:00, 2026-12-01 00:00)`; first permitted **signal CLOSE** `2026-11-04 00:00`; entry Open must be `< 2026-12-01 00:00` | Source-only window gates implemented; **safe platform-level isolation UNVERIFIED**, no TradingView run yet. Only data actually available as of execution date allowed. |
| Prospective observation | On/after 2026-12-01 | Later stage; does not become automatically authorized. |

November 1 is an **exact independent numerical/HTF anchor** for both 15m and 1h (no October seed, no 2026 Holdout warm-up, no off-window cache). November 4 starts permitted signals, not a numerical reset. The bar `[Nov 3 23:45, Nov 4 00:00)` may own the first permitted signal **if** its Close actually qualifies. Neither 15m nor `request.security` may import earlier history. Merely hiding labels/orders outside the window does **not** establish actual TradingView input isolation. Loading these scripts on an ordinary chart is **NOT YET AUTHORIZED**. 2025/Jan–Oct 2026 charts and cached data are forbidden as a Parity shortcut. Use separate, evidenced safe-environment gate before any platform execution.

Raw 2023/24 datasets reside only in Git-ignored local `data/stage0a/20261114T165617836854Z/`; Git stores **hashes/manifests, not the CSV payloads**. The local environment path used by Codex was `/Users/mehrdadi/Documents/ChatGPT/Tradingview Indicator`. A new ChatGPT chat does **not** thereby gain access to that Mac directory or the caches. Do not invent their presence. On missing caches, report `BLOCKED`, not substitute synthetic market prices. Access control must cover loader, cache, exports, market API, Pine/TradingView and related HTF inputs. Future `final-evaluation` is gated and restricted to the frozen winner once.

## 7. Research results and the Funding blocker

**Stage-0A:** Completed real Development descriptive analysis (not a trade backtest). Stop-valid pivot/opportunity population: 2023 **1,679**, 2024 **1,708**. Risk/cost median: **2.774410** (2023), **3.791527** (2024). This motivated the approved economic K=2.5 policy only.

**Stage-0B:** Ran twelve **independent annual Research-mode pre-Funding feasibility** paths on 2023 and 2024. Counts are legitimate *diagnostic* completed-fill counts, **not** a declaration of Funding-adjusted performance or validated winning candidates:

| Candidate | 2023 completed | 2024 completed |
|---|---:|---:|
| C01 | 397 | 493 |
| C02 | 270 | 335 |
| C03 | 338 | 404 |
| C04 | 147 | 207 |
| C05 | 350 | 455 |
| C06 | 28 | 34 |
| C07 | 237 | 287 |
| C08 | 69 | 114 |
| C09 | 229 | 293 |
| C10 | 126 | 158 |
| C11 | 15 | 21 |
| C12 | 1 | 0 |

C01 average annual count **445**, so no `LOW_SIGNAL_FREQUENCY` diagnostic (<150) there. No candidate has been chosen/ranked; Stage-0B is not profitability, Selection eligibility or Bootstrap.

**Phase 4A Funding acquisition:** Valid observed settlements **1,095 in 2023**, **1,098 in 2024**. Observed linked previous-minute Mark: **1,094 in 2023**, **1,098 in 2024**; no missing *requestable observed-settlement* minute, but one 2023 initial boundary minute unavailable. Crucially, whether some actual historical settlements are absent from **all** Bybit responses is UNKNOWN. Funding/Mark completeness **PARTIAL_DATA**. Current 8-hour cadence cannot certify whole historical BTCUSDT intervals.

**Phase 4B calendar audit:** Independently dated docs/archive evidence supports an 8-hour convention and 480-min BTCUSDT examples, but **not complete, continuous, independently established 2023/24 BTCUSDT settlement calendar or exception history**. Keep `HISTORICAL_FUNDING_DATA=PARTIAL_DATA`. The unavailable pre-2023 first boundary Mark minute was proven **not exposure-required** under the independent annual Flat reset; that narrow conclusion does NOT establish raw calendar completeness or permit pre-2023 price access.

**Phase 4C Funding lifecycle:** Pure synthetic fixture accounting component complete, six registered Mark/OPEN precedence sensitivity cases and exact decimal math. Synthetic evidence includes 64 new tests; historical Funding-adjusted research was **NOT** run. Funding does NOT alter common ex-ante sizing/day-stop snapshot. `APPROXIMATE_MARK_PREVIOUS_1M_CLOSE` is an imperfect proxy, not exact settlement tick, and High/Low are **not guaranteed bounds**. No missing rate is zero-filled.

**Resolution requirement:** Find verifiable independent 2023/24 BTCUSDT effective-period settlement calendar/exception evidence or apply the frozen spec's appropriate missing-data verdict; do not simply assume unobserved settlements do not exist. Only after legitimate data sufficiency may the relevant historical Funding-adjusted pipeline and research criteria be evaluated. Do not choose a profitable-looking candidate from pre-Funding counts.

## 8. Statistical research and future gates (not yet executed)

- **Rolling stability diagnostics:** fixed trailing 12-month reference and following 3-month evaluation, three-month steps; diagnostics do **not** change candidates, thresholds or Selection eligibility.
- **2025 Selection** (locked): all 12 separately evaluated under authorized data and quality. Eligibility: `N_completed >= 120`, `MaxDD_R <= 15`, censor rate `<=5%` and essential valid data/execution. Rank **only** Eligible candidates by highest lower **5th percentile** of bootstrap mean trade net R. Tie: six-decimal round-half-even, then fewer optional filters, then lower candidate ID. If no valid winner or competitor-quality data incomplete: `RESEARCH_INCONCLUSIVE`, Holdout stays locked.
- **Bootstrap:** non-circular moving blocks of 5 trades, **5,000** resamples, explicit PCG64 **seed 20261114** reset per candidate/partition/scenario; type-7 5th percentile, sequential binary64 mean. A TP1+TP2 trade is **one trade R** observation. The parameter record has only a future **contract**, not a completed research Bootstrap.
- **Pre-Holdout freeze:** separate commit/tag for selected C-ID, data/config/environment/code and complete required gates. This tag **does not exist yet**.
- **Final 2026 Jan–Oct Holdout:** **exactly one authorized evaluation**. Main verdict precedence: invalid data/protocol/execution/censoring -> INCONCLUSIVE; valid risk `MaxDD_R>15` -> FAIL_RISK; valid N>=100 with mean_R<=0 or PF<=1 -> FAIL_PERFORMANCE; PASS requires valid N>=100, mean_R>0, lower bootstrap 5th>0, PF>=1.20, MaxDD_R<=15 **and** required Funding sensitivities meeting conditions; otherwise INCONCLUSIVE. Exactly 5% censoring is allowed; >5% is invalid. The result has NOT been attempted.
- **Forward observation** after technical validation; cannot present historical or November debugging sample as untouched prospective data.

## 9. Phases actually completed, their scope, and evidence map

| Stage | Real deliverable / evidence | Truthful status |
|---|---|---|
| Design v0.2.2 | `STRATEGY_SPEC_v0.2.2.md`, original annotated design tag | FROZEN; historical header not current status |
| Phase 1 / Stage-0A | `research/{loader,indicators,stage0a}.py`, `reports/stage0a/...` | Completed Development-only descriptive data work; no performance |
| Phase 2 | `research_freeze/v0.2.2/`, official config/tag | K=2.5 and environment frozen |
| Stage-0B | `research/stage0b/`, `reports/stage0b/v0.2.2/20261114T183819594592Z/` | Twelve pre-Funding paths run; no ranking/performance verdict |
| Phase 4A | `research/funding/`, `reports/funding/...` | Retrieved observed Funding/Mark; PARTIAL_DATA |
| Phase 4B | `reports/funding_calendar/v0.2.2/20261114T195000Z/` | Date-evidence audit; calendar still unproven |
| Phase 4C | `research/funding_lifecycle/`, `reports/funding_lifecycle/...` | Synthetic Funding accounting, not historical application |
| Phase 5A | `pine/Phase5A_Temporal_Probe_UNVALIDATED.pine` | Source-only 15m/HTF anchor proof design |
| Phase 5B1 | `pine/Phase5B1_C01_Decision_Probe_UNVALIDATED.pine` | C01 decision diagnostic source-only |
| Phase 5B2 | `pine/Phase5B2_Selected_Candidate_Probe_UNVALIDATED.pine` | C01-C12 and R/H/V/M/Q source-only |
| Phase 5B3 | `research/fixture_state_v1/` | Python-only synthetic lifecycle; its historical `Pine NOT_IMPLEMENTED` statement is true **for that earlier phase**, not for later 5B3-Pine |
| Phase 5B3-Pine | `pine/Phase5B3_Integrated_Research_Probe_UNVALIDATED.pine`; later identity/audit remediation | Integrated hypothetical Research tape source-only, no native TV fills |
| Phase 5C | `pine/Trading_Signals.pine`, presentation, 5C bug correction, test-efficiency policy | Published source-only, 264 synthetic/static tests in final correction evidence |
| Phase 5D | `pine/BTC_Strategy.pine`, native adapter and protocol | **PUBLISHED source-only**, last final evidence 273 synthetic/static tests; no TradingView |

**Phase 5D report:** `reports/native_strategy/v0.2.2/20261115T130843618828Z/REPORT.md` and `verification.json`; 9 *new* static tests + 264 *reused*, one final 273-pass offline regression, with two targeted development runs (first had an overbroad substring-test false-positive). All gate statuses below still open. This 273 is the final **distinct offline cases reported by Codex**, not 273 real TradingView trades or Pine runtime tests; no reason to rerun solely to create a Handoff.

**Phase 5C correction report:** `reports/trading_signals/v0.2.2/20261115T111850751378Z/REPORT.md` (264 distinct, 1 new/263 reused). **Phase 5B3 and remedial reports remain intact** and describe their original stage-specific scopes. Do not revise historical evidence to match a later stage.

## 10. GitHub snapshot / local workflow provenance

Private remote: `https://github.com/AmirMehrdadi/Tradingview-Indicator`  
Local Codex repository: `/Users/mehrdadi/Documents/ChatGPT/Tradingview Indicator`  
Default branch: `main`.

**Verified branch history tail:**

- `479342971bf042fb9611e3a5aec1c311377cf159` — baseline before Phase 5C, 191 files.
- `150b7ecbdad2203969a5a5f5a88cc471d8781700` — Phase 5C additive source/evidence, 9 files.
- `eb41c4ecf52a445a5ce32464a824359abb7bbb4d` — Phase 5C focused correction + test-efficiency policy, 3 modifications / 4 additions; 204 files.
- **`e0f94e4f22461f61bed42599c3d34ec702b927b7`** — Phase 5D, 7 additions; **211 files**. Independently verified on GitHub 2026-11-15.

Phase 5D Pine source SHA-256 `a2e3acd710fc26697e0766cbdf4d9c85422c45b249f476863f9d3568fb651037`; Git blob SHA-1 `212a9e86ab534bee738ff14501639285a29ef63f`. Phase 5D approved review ZIP SHA-256 `a878ebf8c75b4abd2796c227d088adf3d81737a5f0029cbd6385837b45ab6ea1`. Corrected 5C Pine blob `3811241a77689655cc682a1da2e04998abb883e3`. These hashes apply to specific historical commits and must not be silently applied to later modifications.

At publication Codex reported tracked/staged worktree clean, with only these five **untracked regular** macOS metadata files permitted: `.DS_Store`, `data/.DS_Store`, `docs/.DS_Store`, `reports/.DS_Store`, `research/.DS_Store`. Do **not** read/delete/modify/commit them; refuse any additional untracked path until reviewed. This local claim cannot be independently verified from GitHub; ask Codex for local precheck when doing local work.

**Never assume the private local Mac repo is visible to a newly opened ChatGPT conversation.** Use the GitHub connector for up-to-date remote state and have Codex report local work. Older review ZIP/Manifest paths under `/private/tmp` on the Mac are not sandbox download links and may not persist; Git commit objects and committed reports are the durable sources.

## 11. Mandatory current gate ledger

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
PHASE_5D_SOURCE_PUBLICATION = VERIFIED_COMPLETE
```

**Mandatory Pine execution tests still open:** especially T06 TP1-then-residual SL; T07 stop before TP1; T13 independent reservation/no over-underfill; T17 next-Open fill with immediate pre-position brackets and same-entry-bar protection; T18 odd quantity split; T22 gap beyond SL/TPs/marketability; T23 margin/forced behavior. Also 15m/1h non-repainting, 1h boundary, compiler diagnostics, change-of-input/restart, alert behavior, property snapshot, pointvalue mapping, UTC flat settlement, end-window carry protection, and no prohibited history consumption. See spec §10.1 T01–T29 and stage protocols. Static PASS never upgrades these.

## 12. Remaining roadmap — ordered by prerequisite, not arbitrary phase naming

**Next: platform isolation design and safe-environment gate, before any actual TradingView use.** Design a test environment that can prove ALL accessible chart/HTF inputs and seed do not expose Jan–Oct 2026 Holdout. Include the Chart/Strategy Tester behavior, symbol/feed, time filters, `request.security`, bar replay/platform auto-history, privacy, no broker linkage, property snapshots, and audit evidence; identify any limitations and stop rather than opening an ordinary chart. **Planning/read-only docs research does not itself authorize execution.** It is acceptable to ask for explicit user permission at a later execution gate. Do not label this stage Phase 5E as formally frozen without separately agreeing the label/scope.

Once authorized and safe: **true Pine compile and runtime** on an isolated permitted dataset/chart, resolve actual compiler errors additively with reviewable commits; demonstrate indicator rendering and strategy exit mechanics T06/T07/T13/T17/T18/T22/T23; freeze official integer `N_ticks`, verify BTC/USDT contract and `syminfo.pointvalue`, full Properties, exact source/config hashes. Then perform **numeric and logic parity** (same input/state/cost model, transparent reasons for expected Research vs Parity differences), collect evidence of trade IDs, fills and remaining quantities, explicitly report insufficient sample and unresolved scenarios. Never infer full historical parity from a handful of technical tests.

In parallel or afterward: resolve the **historical Funding-calendar evidence** deficiency, finish valid Funding-adjusted Development research/sensitivities; complete fixed rolling diagnostics. Only then, and subject to required gates, explicitly authorize **2025 Selection**, choose one eligible winner, create the separate **pre-Holdout freeze**, explicitly authorize exactly **one** 2026 Jan–Oct Holdout evaluation; afterward prospective observation/hand-off of the indicator, still no actual automated trading in V1. No pending stage is automatically authorized merely because source was pushed.

## 13. Efficient Codex and independent-review operating procedure

**Conversation language:** ChatGPT guidance **Persian**; ALL Codex prompts and Codex answers **English only**.

**Before each Codex prompt, provide:** `Task name`, `Hardness /10`, `Reasoning = Low / Medium / High / Extra High`, and a short justification. Heuristic: Low trivial formatting; Medium small fixes/source publication; High major multi-module state; Extra High delicate architecture, safety and hard-to-prove execution/selection logic. The task-specific risk and Codex mode availability may require adjustment; no need to overpay for trivial tests.

**Default workflow:**

1. ChatGPT establishes authoritative spec, live remote SHA, allowed local baseline, scope, forbidden data, expected outputs and blockers.
2. Codex prechecks repo identity, branch, origin, exact HEAD/ancestry, 2 frozen annotated objects+targets, tracked tree and untracked exceptions; fail closed on unexpected differences.
3. Freeze-preserving **additive** work, minimal focused test coverage; reuse existing runners/fixtures. No unnecessary frameworks or inflated passing counts.
4. During development targeted tests; exactly **one comprehensive offline regression after final edit** per applicable gate; if retry necessary disclose every rerun and actual wall/test durations. Distinguish **distinct cases** from repeated method invocations and synthetic checks from Pine runtime. Historical/protected data tests not rerun just for reports. Never waive required safety gates.
5. Local-only committed delta: **one commit unless a reviewed correction requires one extra**, no amend/history rewrite, one ZIP of the committed file delta plus **external** integrity manifest with SHA-256/Git Blob SHA-1 and extracted-byte verification. Include timestamped technical report and immutable prior-report preservation. No auto-push.
6. User supplies actual ZIP+Manifest to ChatGPT. ChatGPT verifies hashes, source diff, protocol, tests, baseline preservation and known limitations; demands a corrective commit if genuine defect, not reflexive overengineering.
7. After independent approval, a separate **publication-only Codex task** rechecks all invariants, performs one ordinary **branch-only fast-forward** push, then independently verifies remote HEAD, commit chain, unchanged baseline blobs/tags and clean worktree. Never push tags by accident or force push. Do not rerun the full suite merely for push.
8. Update the small current-state handoff **after the push is independently verified**. Do not silently rewrite historic freeze tags, source or reports.

The `docs/TEST_EFFICIENCY_POLICY.md` in repo is normative for the engineering-test portion. Citable evidence and actual GitHub state beat chat assumptions. If the next task is just planning/research, avoid coding and redundant tests.

## 14. Reliable chat-to-chat handoff protocol

1. On entering a new chat in **this ChatGPT Project**, provide `docs/NEW_CHAT_START.md` or paste its content.
2. The new chat **must read** both Handoff docs and verify their snapshot on the *actual connected GitHub repo*; retrieve the source files in §2, protocols and latest reports as needed. If private GitHub is not accessible, explain limitation and obtain the files; do not invent current state.
3. Explicitly distinguish `PUBLISHED SOURCE`, `OFFLINE SYNTHETIC TESTED`, `TRADINGVIEW VERIFIED`, `HISTORICAL RESEARCH VALIDATED`, and `PROTECTED DATA SEALED` as different evidence levels.
4. Reconcile any HEAD advance by inspecting intervening commits and updating the **state** document. Update the full document if architecture, stages, frozen authorities, important decisions or risks change; never silently assume older text still matches Git.
5. Resume the next gated task from §12. Do **not** re-run Phase 1–5D work or ask the user to retell it. Ask only for necessary new permissions, unavailable tools/evidence or genuine unresolved choices.
6. Preserve frozen tags and protected-date partitions. Any suspect leak or stale/contradictory evidence must STOP the relevant action and become an explicit issue.

## 15. Reference index — minimum sources to reopen

**Authority and scope:** `STRATEGY_SPEC_v0.2.2.md` §§0–10 and §13; `configs/research_v0.2.2.json`; `research_freeze/v0.2.2/RESEARCH_PARAMETER_FREEZE.md`; `docs/FUTURE_INDICATOR_K_REQUIREMENT.md`; `docs/TEST_EFFICIENCY_POLICY.md`.

**Research:** `research/README_FA.md`; `reports/stage0a/20261114T165617836854Z/summary_FA.md`; `reports/stage0b/v0.2.2/20261114T183819594592Z/REPORT.md`; `reports/funding/v0.2.2/20261114T192333525994Z/REPORT.md`; `reports/funding_calendar/v0.2.2/20261114T195000Z/REPORT.md`; `reports/funding_lifecycle/v0.2.2/20261114T211449760645Z/REPORT.md`.

**Stateful implementation:** `docs/phase5a/VALIDATION_PROTOCOL.md`; `docs/phase5b1/VALIDATION_PROTOCOL.md`; `docs/phase5b2/VALIDATION_PROTOCOL.md`; `docs/phase5b3/PROTOCOL.md`; `docs/phase5b3_pine/VALIDATION_PROTOCOL.md`; `docs/phase5b3_pine/REMEDIATION_PROTOCOL.md`; `docs/phase5c/VALIDATION_PROTOCOL.md`; `docs/phase5d/VALIDATION_PROTOCOL.md`.

**Actual final source/evidence:** `pine/Trading_Signals.pine`; `pine/BTC_Strategy.pine`; `reports/trading_signals/v0.2.2/20261115T111850751378Z/REPORT.md`; `reports/native_strategy/v0.2.2/20261115T130843618828Z/REPORT.md`; `reports/native_strategy/v0.2.2/20261115T130843618828Z/verification.json`; `tests/test_phase5d_strategy.py`.

**Common invariant:** **A published and statically tested Pine script is NOT a compiled or validated TradingView indicator/strategy, and a count-only pre-Funding research path is NOT a verified profitable strategy.**

---

**Handoff document provenance:** authored from the live connected private GitHub files and independently verified HEAD/tree/tag records on 2026-11-15, plus the user's Phase 5D publication report. This document was **authored against the independently verified Phase-5D baseline**. At the time it was first generated, it had not yet been committed to GitHub. If it is later present in GitHub, treat that as its subsequent publication, NOT as proof that the snapshot HEAD shown here is still the newest commit. Verify live remote state before every continuation.
