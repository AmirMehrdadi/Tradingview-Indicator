"""Strictly separated public counts and restricted, Git-ignored private ledgers."""
import os
import re
from pathlib import Path

from research.access import AccessDenied, Window
from research.loader import canonical, write_new

FORBIDDEN = re.compile(r"(^|_)(pnl|profit|profitability|returns?|win_rate|expectancy|drawdown|equity|cash|balance|settled|entry_fee|exit_fee)(_|$)", re.I)
PUBLIC_PATH_KEYS = {"candidate", "year", "N_raw_candidate", "N_after_each_gate", "N_nonoverlap", "N_signals", "N_filled", "N_completed", "N_censored",
                    "N_rejected_margin", "daily_stop_activations", "daily_stop_blocked_opportunities", "direction_counts", "pivot_age_bars",
                    "rejection_reasons", "funnel_pass_rates", "distance_from_120", "censor_rate", "censoring_quality", "quality_events",
                    "integrity", "execution_model_validity", "funding", "tradingview_execution", "data_quality", "assumptions"}


def no_financial_outputs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if FORBIDDEN.search(key):
                raise AccessDenied("PROHIBITED_PUBLIC_FINANCIAL_FIELD")
            no_financial_outputs(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            no_financial_outputs(item)


def validate_path_summary(summary):
    Window.annual(summary["year"], "15")
    if summary["candidate"] not in {f"C{i:02d}" for i in range(1, 13)} or set(summary) != PUBLIC_PATH_KEYS:
        raise AccessDenied("UNAUTHORIZED_PUBLIC_SUMMARY_SCHEMA")
    no_financial_outputs(summary)


def write_public_summary(directory, summary):
    validate_path_summary(summary)  # Before constructing/opening any export path.
    write_new(directory / f"{summary['year']}_{summary['candidate']}.json", canonical(summary))


def restricted_directory(path):
    if path.is_symlink():
        raise AccessDenied("PRIVATE_DIRECTORY_SYMLINK")
    path.mkdir(parents=True, exist_ok=False, mode=0o700)
    os.chmod(path, 0o700)


def write_private(path, data):
    if path.parent.is_symlink() or path.is_symlink():
        raise AccessDenied("PRIVATE_FILE_SYMLINK")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)


def report_text(paths, diagnostic):
    lines = ["# Stage-0B — Development pre-funding feasibility", "",
             "All twelve candidates have independent annual paths. This report contains counts and quality indicators only; no candidate is ranked or selected.", "",
             "Scope: validated 2023/2024 candles and frozen historical instrument assumptions; Research-mode execution, not TradingView emulator verification. Funding/settlement Mark evidence is MISSING, never zero-substituted. Full net-research validity is NOT EVALUABLE.", "",
             "| Candidate | 2023 completed | 2023 censored | 2024 completed | 2024 censored |", "|---|---:|---:|---:|---:|"]
    lookup = {(p["year"], p["candidate"]): p for p in paths}
    for candidate in (f"C{i:02d}" for i in range(1, 13)):
        a, b = lookup[2023, candidate], lookup[2024, candidate]
        lines.append(f"| {candidate} | {a['N_completed']} | {a['N_censored']} | {b['N_completed']} | {b['N_censored']} |")
    lines += ["", f"C01 mean annual completed count: **{diagnostic['C01_mean_annual_completed']}**. Diagnostic: **{diagnostic['status']}**; LOW_SIGNAL_FREQUENCY is set only below 150.", "",
              "The per-path JSON files contain A..G funnels, pass rates, Long/Short counts, pivot-age percentiles, primary rejection reasons, daily-stop counts, execution-quality events and signed distance from 120. Neither 120 nor 150 eliminates a candidate at Stage-0B.", "",
              "## Funnel totals", "", "| Year | Candidate | A raw | B pivot | C stop | D cost | E quantity/order | F filters | G accepted | Filled | Margin rejected | Daily-stop activations | Distance from 120 |",
              "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for p in paths:
        g = p["N_after_each_gate"]
        lines.append(f"| {p['year']} | {p['candidate']} | "+" | ".join(str(g[x]) for x in "ABCDEFG")+f" | {p['N_filled']} | {p['N_rejected_margin']} | {p['daily_stop_activations']} | {p['distance_from_120']} |")
    lines += ["", "## Status and limitations", "",
              "- Python Research-mode count integrity and deterministic replay are checked before accepting results. Any MARGIN_MODEL_EVENT invalidates the affected execution model; such counts are diagnostic only and the runner fails closed.",
              "- Same-bar ambiguous fills follow the frozen Stop-first rule after known Open fills. No post-exit High/Low is charged to a closed position; partial exits reduce the quantity used in subsequent checks.",
              "- All four Development OHLC datasets must be VALID with the frozen SHA-256 hashes. There is no interpolation or market-data network access in Stage-0B.",
              "- Current instrument constraints applied historically are an explicit assumption. Fees/friction are frozen research assumptions, not verified account rates.",
              "- Funding/Mark completeness and all TradingView/Pine execution gates remain OPEN / UNVERIFIED. Pre-funding feasibility counts do not establish net performance, Selection eligibility or a Pass verdict.",
              "- Private accounting/event ledgers are stored separately under restricted, Git-ignored paths; none of their financial values are exported or printed.",
              "- No 2025 Selection, Holdout, Bootstrap, rolling diagnostics, real orders, Pine implementation, final README or GitHub push was performed.", ""]
    return "\n".join(lines)
