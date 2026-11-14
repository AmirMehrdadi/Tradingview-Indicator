"""Reproducible, fail-closed development-only workflow and Persian reports."""
import csv
import io
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from .access import AccessDenied, Window, UTC, iso
from .loader import PublicClient, DataError, RetrievalError, canonical, sha256, write_new, fetch_candles, fetch_instrument, save_dataset, read_dataset
from .stage0a import describe, PERCENTILES

ROOT = Path(__file__).resolve().parent.parent
SPEC = "STRATEGY_SPEC_v0.2.2.md"
TAG = "v0.2.2-design"
DESIGN_COMMIT = "ac8fc4bb9b66a59c7224aaec1630a594b41d7e80"
EXPECTED_CONFIG = {"phase": "stage0a-development-only", "category": "linear", "symbol": "BTCUSDT", "years": [2023, 2024], "intervals": ["15", "60"],
    "fee_rate": 0.00055, "slippage_rate": 0.0002, "cost_assumption": "PROVISIONAL_TAKER_0.055_PERCENT_PLUS_FRICTION_0.02_PERCENT", "K_cost_stop": "UNSET"}


def provenance():
    commit = subprocess.check_output(["git", "rev-parse", TAG + "^{commit}"], cwd=ROOT, text=True).strip()
    frozen = subprocess.check_output(["git", "show", TAG + ":" + SPEC], cwd=ROOT)
    if commit != DESIGN_COMMIT or (ROOT / SPEC).read_bytes() != frozen:
        raise DataError("Design tag/spec differs from approved freeze; no automatic changes permitted")
    config_bytes = (ROOT / "configs/stage0a.json").read_bytes()
    config = json.loads(config_bytes)
    if config != EXPECTED_CONFIG:
        raise AccessDenied("Phase-1 config differs from the authorized descriptive protocol; K must remain UNSET")
    source = {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted((ROOT / "research").glob("*.py"))}
    return config, {"design_tag": TAG, "design_commit": commit, "spec_sha256": sha256(frozen), "config_sha256": sha256(config_bytes),
        "implementation_files_sha256": source, "implementation_sha256": sha256(canonical(source)), "python_version": sys.version,
        "research_parameter_freeze": "OPEN", "execution_gates": "OPEN_UNVERIFIED", "K_cost_stop": "UNSET"}


def run_directory(run_id):
    if not re.fullmatch(r"\d{8}T\d{12}Z", run_id):
        raise AccessDenied("Invalid run ID; arbitrary cache paths are prohibited")
    base = ROOT / "data/stage0a"
    path = base / run_id
    if base.parent.is_symlink() or base.is_symlink() or path.is_symlink() or (path.exists() and path.resolve().parent != base.resolve()):
        raise AccessDenied("Cache directory escapes Phase-1 root")
    return path


def run_fetch():
    config, origin = provenance()
    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    directory = run_directory(run_id)
    directory.mkdir(parents=True, exist_ok=False)
    client = PublicClient()
    run = {"run_id": run_id, "phase": config["phase"], "provenance": origin, "started_at_utc": datetime.now(UTC).isoformat(),
           "status": "NOT_RUN", "instrument": None, "datasets": [], "blockers": []}
    try:
        instrument = fetch_instrument(client)
        data = canonical(instrument)
        write_new(directory / "instrument.json", data)
        run["instrument"] = {"file": "instrument.json", "sha256": sha256(data)}
    except (DataError, RetrievalError) as exc:
        run["blockers"].append({"operation": "current_instrument_metadata", "reason": str(exc)})
    if run["instrument"]:
        stop_network = False
        for year in (2023, 2024):
            for interval in ("15", "60"):
                window = Window.annual(year, interval)
                entry = {"year": year, "interval": interval, "status": "NOT_RUN"}
                if not stop_network:
                    before = len(client.calls)
                    try:
                        candles, quality = fetch_candles(client, window, int(datetime.now(UTC).timestamp()*1000))
                        manifest = save_dataset(directory, candles, quality, window, client.calls[before:])
                        entry.update(status=quality["status"], manifest=manifest["csv"] + ".manifest.json", manifest_sha256=sha256(canonical(manifest)), quality=quality)
                    except (DataError, RetrievalError, AccessDenied) as exc:
                        entry["reason"] = str(exc)
                        run["blockers"].append({"operation": f"candles_{year}_{interval}", "reason": str(exc)})
                        # Do not repeatedly contact a denied/unreachable host.
                        stop_network = isinstance(exc, RetrievalError)
                else:
                    entry["reason"] = "Network retrieval stopped after previous failure"
                run["datasets"].append(entry)
        run["status"] = "DATA_READY" if all(d["status"] == "VALID" for d in run["datasets"]) else "PARTIAL_OR_QUARANTINED"
    run["requests"] = client.calls
    run["finished_at_utc"] = datetime.now(UTC).isoformat()
    write_new(directory / "run_manifest.json", canonical(run))
    results = analyze_run(run_id)
    return {"run_id": run_id, "retrieval_status": run["status"], "years": {str(y): results[str(y)]["status"] for y in (2023, 2024)},
            "report": str(ROOT / "reports/stage0a" / run_id / "summary_FA.md"), "blockers": run["blockers"]}


def analyze_run(run_id):
    config, origin = provenance()
    directory = run_directory(run_id)
    manifest_path = directory / "run_manifest.json"
    if manifest_path.is_symlink():
        raise AccessDenied("Symlink run manifest prohibited")
    run = json.loads(manifest_path.read_text(encoding="utf-8"))
    if run.get("phase") != config["phase"] or run.get("run_id") != run_id:
        raise AccessDenied("Wrong cache phase/run ID")
    if any(run.get("provenance", {}).get(key) != origin[key] for key in ("design_commit", "spec_sha256", "config_sha256")):
        raise AccessDenied("Cache provenance differs from the frozen spec/config")
    # Inspect only declared ranges before opening any price dataset.
    entries = {}
    for entry in run.get("datasets", []):
        window = Window.annual(entry.get("year"), entry.get("interval"))
        key = (window.year, window.interval)
        if key in entries:
            raise DataError("Duplicate dataset descriptor")
        entries[key] = entry
    instrument = None
    if run.get("instrument"):
        if run["instrument"].get("file") != "instrument.json" or (directory / "instrument.json").is_symlink():
            raise AccessDenied("Invalid instrument cache path")
        data = (directory / "instrument.json").read_bytes()
        if sha256(data) != run["instrument"]["sha256"]:
            raise DataError("Instrument cache hash mismatch")
        instrument = json.loads(data)
    output = ROOT / "reports/stage0a" / run_id
    output.mkdir(parents=True, exist_ok=True)
    summaries, opportunities = {}, {}
    for year in (2023, 2024):
        try:
            if instrument is None:
                raise DataError("Current instrument metadata unavailable: tick/constraints not guessed")
            datasets = {}
            for interval in ("15", "60"):
                entry = entries.get((year, interval), {})
                if entry.get("status") != "VALID":
                    raise DataError(f"{year}/{interval} not VALID: " + entry.get("reason", entry.get("status", "NOT_RETRIEVED")))
                name = f"BTCUSDT_{year}_{interval}.csv.manifest.json"
                if entry.get("manifest") != name:
                    raise AccessDenied("Unexpected dataset manifest filename")
                path = directory / name
                if path.is_symlink() or sha256(path.read_bytes()) != entry.get("manifest_sha256"):
                    raise DataError("Dataset manifest hash/symlink check failed")
                datasets[interval] = read_dataset(directory, path, Window.annual(year, interval))
            summary, rows = describe(datasets["15"][0], Window.annual(year, "15"), instrument["constraints"]["tick_size"], config)
            summary["data_quality"] = {interval: datasets[interval][1]["quality"] for interval in ("15", "60")}
            summary["dataset_sha256"] = {interval: datasets[interval][1]["csv_sha256"] for interval in ("15", "60")}
            summary["instrument_assumption"] = instrument["historical_assumption"]
            summary["tick_size"] = instrument["constraints"]["tick_size"]
            summary["cost_assumptions"] = {k: config[k] for k in ("fee_rate", "slippage_rate", "cost_assumption", "K_cost_stop")}
            summaries[str(year)], opportunities[str(year)] = summary, rows
        except (DataError, AccessDenied, OSError, KeyError, ValueError) as exc:
            summaries[str(year)] = {"year": year, "status": "NOT_RUN", "reason": str(exc), "K_cost_stop": "UNSET", "descriptive_statistics": None,
                "data_quality": {i: entries.get((year, i), {}).get("quality") for i in ("15", "60")}}
    for year, summary in summaries.items():
        _stable_output(output / f"{year}.json", canonical(summary))
        if year in opportunities:
            rows = opportunities[year]
            stream = io.StringIO(newline="")
            fields = list(rows[0]) if rows else ["year", "direction", "signal_close_utc", "status"]
            writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
            _stable_output(output / f"{year}_opportunities.csv", stream.getvalue().encode("utf-8"))
    quality = {str(y): {i: entries.get((y, i), {}).get("quality") for i in ("15", "60")} for y in (2023, 2024)}
    _stable_output(output / "quality.json", canonical(quality))
    report = persian_report(summaries, run)
    _stable_output(output / "summary_FA.md", report.encode("utf-8"))
    _stable_output(output / "analysis_provenance.json", canonical({"retrieval_manifest_sha256": sha256(manifest_path.read_bytes()), **origin}))
    return summaries


def _stable_output(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise DataError("Existing report differs; refusing overwrite: " + str(path))
        return
    write_new(path, data)


def persian_report(summaries, run):
    lines = ["# Stage-0A — گزارش توصیفی توسعه", "", "داده مجاز: سال‌های ۲۰۲۳ و ۲۰۲۴، با ۶۰ ساعت Warm-up مستقل پیش از هر سال. هیچ داده قیمت از ۲۰۲۵ به بعد مجاز نیست.", "",
        "این خروجی توصیف فرصت خام است؛ معامله پذیرفته‌شده، خروج، بازده یا انتخاب K محاسبه نشده است. `K_cost_stop=UNSET`؛ قفل پارامتر پژوهش و gateهای اجرا باز هستند.", "",
        "در Stage-0A هیچ Pullback مصرف نمی‌شود و position/day/quantity gate شبیه‌سازی نمی‌شود؛ یک Pullback می‌تواند چند فرصت خام داشته باشد. این شمارش N_completed یا شاهد کف نمونه Stage-0B نیست.", "",
        "مدل هزینه فرضی: Taker هر سمت ۰٫۰۵۵٪ و اصطکاک هر سمت ۰٫۰۲٪؛ proxy هر BTC برابر `(entry_ref+SL)*(0.00055+0.0002)`، بدون Funding. نرخ حساب واقعی تأیید نشده است.", "",
        "tick و محدودیت‌های جاری ابزار، در صورت دریافت، فقط فرض تاریخی نسخه‌دار هستند؛ تغییرات تاریخی و minimum خروج reduce-only تأیید نشده‌اند. داده یا Mark/Funding برای این فاز دریافت نمی‌شود.", ""]
    for year in ("2023", "2024"):
        result = summaries[year]
        lines += [f"## {year}", "", f"وضعیت: `{result['status']}`", ""]
        if result["status"] == "NOT_RUN":
            for interval, quality in result.get("data_quality", {}).items():
                if quality is not None:
                    lines += [f"کیفیت {interval}m: دریافت {quality['received_rows']} ردیف، معتبر {quality['valid_rows']}، گمشده {len(quality['missing_open_times'])}، تکراری {quality['duplicate_rows']}، نامعتبر {len(quality['invalid_rows'])}، ناتمام {len(quality['incomplete_rows'])}؛ وضعیت `{quality['status']}`.", ""]
            lines += ["مانع: " + result["reason"], "", "هیچ شمارش یا صدک واقعی برای این سال تولید نشده است؛ صفر ساختگی گزارش نمی‌شود.", ""]
            continue
        lines += ["| فاصله | دریافت‌شده | معتبر | Warm-up معتبر | گمشده | تکراری | نامعتبر | ناتمام |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
        for interval, q in result["data_quality"].items():
            lines.append(f"| {interval}m | {q['received_rows']} | {q['valid_rows']} | {q['valid_warmup_rows']} | {len(q['missing_open_times'])} | {q['duplicate_rows']} | {len(q['invalid_rows'])} | {len(q['incomplete_rows'])} |")
        lines += ["", "| جهت | فرصت خام | دارای پیوت تأییدشده مناسب | فاصله Stop معتبر | Pullback یکتا |", "|---|---:|---:|---:|---:|"]
        for group, stats in result["groups"].items():
            lines.append(f"| {group} | {stats['raw_opportunities']} | {stats['confirmed_pivot_survivors']} | {stats['stop_range_survivors']} | {stats['unique_pullbacks']} |")
        lines += ["", "صدک‌ها با interpolation خطی type-7 محاسبه شده‌اند. درصد ATR همه کندل‌های بسته سال، بر اساس Open سال تقویمی است؛ فرصت‌ها بر اساس Close در بازه نیمه‌باز سال منتسب‌اند.", "",
            "| جهت / جامعه / متغیر | N | P5 | P10 | P25 | P50 | P75 | P90 | P95 |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
        all_atr = result["all_development_closed_bars_atr_pct"]
        populations = [("All / calendar_bars / ATR%", all_atr)]
        for group, stats in result["groups"].items():
            populations.append((f"{group} / pivot_available / pivot_age_bars", stats["pivot_age_bars"]))
            for population, metrics in stats["distributions"].items():
                for metric, distribution in metrics.items():
                    populations.append((f"{group} / {population} / {metric}", distribution))
        for label, distribution in populations:
            values = ["—" if distribution["percentiles"][str(p)] is None else format(distribution["percentiles"][str(p)], ".8g") for p in PERCENTILES]
            lines.append(f"| {label} | {distribution['n']} | " + " | ".join(values) + " |")
        lines += ["", "دلایل رد پیش از فرصت خام: `" + json.dumps(result["baseline_rejections_by_bar"], sort_keys=True) + "`", "",
                  "دلایل رد پس از فرصت خام: `" + json.dumps(result["rejections_after_baseline"], sort_keys=True) + "`", "",
                  "تفکیک دلایل رد Long/Short و ردیف‌های فرصت در فایل‌های JSON/CSV همان سال موجود است.", ""]
    lines += ["## دسترسی و شواهد", "", f"تعداد تلاش شبکه ثبت‌شده: {len(run.get('requests', []))}. وضعیت دریافت: `{run.get('status')}`.", "",
        "URL، زمان UTC، hash پاسخ و علت خطا در run_manifest ثبت شده‌اند. یکسان‌بودن داده و پیکربندی، خروجی محاسباتی یکسان می‌دهد؛ timestamp دریافت شبکه جزو شواهد هر دریافت مستقل است.", "",
        "gateهای باقی‌مانده: تکمیل/تأیید داده Development و فرض‌های metadata، بررسی انسانی توزیع‌ها و تعیین K بدون معیار سودآوری، ثبت config/commit پژوهشی، سپس Stage-0B مستقل هر ۱۲ نسخه. Funding/Mark، Selection و همه آزمون‌های واقعی TradingView مربوط به مراحل بعد و همچنان تأییدنشده‌اند.", ""]
    return "\n".join(lines)
