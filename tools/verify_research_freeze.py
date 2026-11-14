"""Offline verification only: no HTTP, no new data, no position simulation."""
import argparse
import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from research.access import Window, authorize_request
from research.loader import canonical, read_dataset, sha256
from research.stage0a import describe
from tools.environment_fingerprint import fingerprint, rng_probe, THREAD_ENV

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "research_freeze/v0.2.2"
RUN = "20261114T165617836854Z"
DESIGN_COMMIT = "ac8fc4bb9b66a59c7224aaec1630a594b41d7e80"
DESIGN_TAG_OBJECT = "638ec6d99413c8dbc82a111209015953809ced08"
PHASE1_COMMIT = "c17f04c0f8f89b0d31a39a8860c11ac63f9e62cb"
RESEARCH_TAG = "v0.2.2-research-parameters"


class FreezeError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise FreezeError(message)


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def expected_candidates(spec):
    return {m.group(1): [x.strip() for x in m.group(2).split("+")]
            for m in re.finditer(r"^\| (C\d\d) \| ([^|]+) \|", spec, re.M)}


def validate_config(config, spec, instrument):
    require(type(config.get("K_cost_stop")) is float and config["K_cost_stop"] == 2.5, "Official K must be exactly 2.5")
    require(config.get("K_scope") == ["Stage-0B", "2025 Selection", "2026 Final Holdout"], "K scope changed")
    require(config.get("K_authorization") == "EXPLICIT_USER_APPROVAL", "Missing user authorization")
    require(config.get("category") == "linear" and config.get("symbol") == "BTCUSDT", "Instrument changed")
    require(config.get("execution_timeframe_minutes") == 15 and config.get("confirmation_timeframe_minutes") == 60, "Timeframe changed")
    candidates = expected_candidates(spec)
    require(len(candidates) == 12 and config.get("candidate_combinations") == candidates, "Candidate combinations changed")
    require(config.get("partitions_utc") == {
        "development": ["2023-01-01T00:00:00Z", "2025-01-01T00:00:00Z"],
        "selection": ["2025-01-01T00:00:00Z", "2026-01-01T00:00:00Z"],
        "final_holdout": ["2026-01-01T00:00:00Z", "2026-11-01T00:00:00Z"],
    }, "Partition boundaries changed")
    cost = config["cost_assumptions"]
    require(cost["taker_fee_rate_per_side"] == 0.00055 and cost["execution_friction_rate_per_fill"] == 0.0002, "Research costs changed")
    require(cost["classification"] == "RESEARCH_ASSUMPTIONS_NOT_VERIFIED_ACCOUNT_RATES", "Costs must not claim account verification")
    require(cost["tp_limit_friction_is_accounting_haircut"] is True and cost["double_count_friction"] is False, "Cost accounting changed")
    floor = config["cost_floor"]
    require(floor["comparison"] == ">=" and floor["funding_included"] is False and floor["tolerance_or_epsilon"] is None, "Cost-floor predicate changed")
    require(floor["denominator"] == "(entry_ref + frozen_SL) * (taker_fee_rate_per_side + execution_friction_rate_per_fill)", "Cost proxy changed")
    require(Decimal(str(config["K_cost_stop"])) * Decimal(str(floor["roundtrip_cost_max_fraction_of_planned_stop"])) == 1, "K must encode the 40% economic rule")
    meta = config["instrument_assumption"]
    require(meta["classification"] == "HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION" and meta["historical_effective_dates"] == "UNVERIFIED", "Historical assumption must remain explicit")
    require(meta["quantity_unit"] == "BTC" and meta["price_and_notional_unit"] == "USDT", "Quantity/price units changed")
    mapping = {"tick_size": "tick_size", "qty_step": "qty_step", "min_order_qty": "min_qty", "min_opening_notional": "min_notional", "max_market_order_qty": "max_market_qty", "max_limit_order_qty": "max_limit_qty"}
    for key, original in mapping.items():
        require(meta[key] == instrument["constraints"][original], "Instrument constraint differs from snapshot: " + key)
    require(set(meta["minimum_order_rules"]) == {"entry_market", "tp1_reduce_only_limit", "tp2_reduce_only_limit", "protective_stop_close"}, "Missing or unexpected order-leg rules")
    for name, rule in meta["minimum_order_rules"].items():
        require(rule["minimum_qty_applies"] is True and rule["qty_step_applies"] is True, "Quantity minima/steps must apply to each leg")
        require(rule["minimum_notional_applies"] is (name == "entry_market"), "Opening/closing minimum-notional applicability changed")
    require(meta["each_partial_quantity_checked_independently"] is True and meta["invalid_partial_rejects_entire_signal"] is True, "Partial quantity rule changed")
    boot = config["bootstrap_contract_only_not_executed"]
    require((boot["numpy"], boot["bit_generator"], boot["seed"], boot["block_length"], boot["replications"]) == ("1.26.4", "PCG64", 20261114, 5, 5000), "Frozen RNG/statistical contract changed")
    require(config["official_performance_validation_status"] == "UNVALIDATED" and config["execution_gates"] == "OPEN_UNVERIFIED", "Parameter freeze cannot validate performance/execution")


def verify_environment(environment):
    require(environment["expected_process_controls"] == THREAD_ENV, "Process-control contract changed")
    current = fingerprint()
    require(current == environment["fingerprint"], "Numerical environment drift: use the recorded interpreter/build and research_python.sh")
    require(current["python_version"] == "3.9.6" and current["packages"].get("numpy") == "1.26.4", "Unpinned interpreter/NumPy")
    require(current["pointer_bits"] == 64 and current["float_format"]["mant_dig"] == 53 and current["float_format"]["numpy_float64_bits"] == 64, "binary64 contract failed")
    require(current["process_controls"] == THREAD_ENV and current["isolated_virtual_environment"], "Isolated deterministic environment required")
    require(rng_probe() == environment["rng_compatibility_probe"], "PCG64/Generator compatibility vectors differ")
    require(environment["wheel"]["sha256"] in (ROOT / "requirements-research.lock").read_text(), "Wheel not hash-pinned")


def verify_all(require_tag=False):
    record = load(BASE / "record.json")
    config_path = ROOT / "configs/research_v0.2.2.json"
    config = load(config_path)
    spec_path = ROOT / "STRATEGY_SPEC_v0.2.2.md"
    spec_bytes = spec_path.read_bytes()
    require(record["intended_tag"] == RESEARCH_TAG and record["official_K_cost_stop"] == 2.5, "Decision record differs from user approval")
    require(record["parameters_are_not_performance_validation"] is True and record["future_data_access_authorized"] is False, "Freeze scope changed")
    require(git("rev-parse", "v0.2.2-design^{commit}") == DESIGN_COMMIT, "Original design commit changed")
    require(git("rev-parse", "refs/tags/v0.2.2-design") == DESIGN_TAG_OBJECT, "Original design annotated tag changed")
    require(git("cat-file", "-t", "refs/tags/v0.2.2-design") == "tag", "Design tag is not annotated")
    require(subprocess.check_output(["git", "show", "v0.2.2-design:STRATEGY_SPEC_v0.2.2.md"], cwd=ROOT) == spec_bytes, "Frozen specification changed")
    require(record["phase1_commit"] == PHASE1_COMMIT and git("rev-parse", PHASE1_COMMIT) == PHASE1_COMMIT, "Phase 1 commit missing")
    require(record["research_config_sha256"] == sha256(config_path.read_bytes()), "Research configuration hash mismatch")
    require(config["authority"]["spec_sha256"] == sha256(spec_bytes), "Research profile references a different spec")
    require(config["authority"]["design_tag"] == "v0.2.2-design" and config["authority"]["design_commit"] == DESIGN_COMMIT, "Research profile design authority changed")
    require(config["authority"]["phase1_commit"] == PHASE1_COMMIT, "Research profile references a different implementation")
    expected_evidence = {"research_freeze/v0.2.2/evidence/" + name for name in
        ["instrument.json", "run_manifest.json"] + [f"BTCUSDT_{y}_{i}.csv.manifest.json" for y in (2023, 2024) for i in ("15", "60")]}
    require(set(record["evidence_files_sha256"]) == expected_evidence, "Unexpected evidence paths")
    for path, expected in record["evidence_files_sha256"].items():
        require(sha256((ROOT / path).read_bytes()) == expected, "Evidence hash mismatch: " + path)
    metadata = load(BASE / "evidence/instrument.json")
    validate_config(config, spec_bytes.decode("utf-8"), metadata)
    require(config["instrument_assumption"]["snapshot_sha256"] == sha256((BASE / "evidence/instrument.json").read_bytes()), "Snapshot hash mismatch")
    expected_reports = {"reports/stage0a/" + RUN + "/" + name for name in {
        "2023.json", "2024.json", "2023_opportunities.csv", "2024_opportunities.csv", "quality.json", "summary_FA.md", "analysis_provenance.json", "access_and_hash_audit.json"}}
    require(set(record["stage0a_report_files_sha256"]) == expected_reports, "Unexpected/missing Stage-0A evidence paths")
    for path, expected in record["stage0a_report_files_sha256"].items():
        require(sha256((ROOT / path).read_bytes()) == expected, "Stage-0A report changed: " + path)
        require(subprocess.check_output(["git", "show", PHASE1_COMMIT + ":" + path], cwd=ROOT) == (ROOT / path).read_bytes(), "Report differs from Phase 1 commit")
    provenance = load(ROOT / "reports/stage0a" / RUN / "analysis_provenance.json")
    for path, expected in provenance["implementation_files_sha256"].items():
        require(path in {"research/" + name for name in ("__init__.py", "__main__.py", "access.py", "indicators.py", "loader.py", "stage0a.py", "workflow.py")}, "Unexpected Phase 1 source path")
        require(sha256((ROOT / path).read_bytes()) == expected, "Phase 1 source changed: " + path)
        require(subprocess.check_output(["git", "show", PHASE1_COMMIT + ":" + path], cwd=ROOT) == (ROOT / path).read_bytes(), "Phase 1 commit/source mismatch")
    phase1_config = load(ROOT / "configs/stage0a.json")
    require(phase1_config["K_cost_stop"] == "UNSET" and sha256((ROOT / "configs/stage0a.json").read_bytes()) == provenance["config_sha256"], "Historical Stage-0A config changed")
    run = load(BASE / "evidence/run_manifest.json")
    require(run["run_id"] == RUN and run["status"] == "DATA_READY", "Phase 1 retrieval incomplete")
    require(sha256((BASE / "evidence/run_manifest.json").read_bytes()) == provenance["retrieval_manifest_sha256"], "Original run manifest mismatch")
    for request in run["requests"]:
        url = urlsplit(request["url"])
        require(url.scheme == "https" and url.netloc == "api.bybit.com", "Unexpected source host")
        params = {key: values[0] for key, values in parse_qs(url.query).items()}
        for key in ("start", "end", "limit"):
            if key in params:
                params[key] = int(params[key])
        authorize_request(url.path, params)  # Local request-log audit only; no HTTP.
        require(request["status"] == "OK" and request["retCode"] == 0, "Retrieval contains unresolved request failure")
    expected_data = {f"data/stage0a/{RUN}/BTCUSDT_{y}_{i}.csv" for y in (2023, 2024) for i in ("15", "60")}
    require(set(record["data_csv_sha256"]) == expected_data, "Data inventory contains unauthorized paths/ranges")
    source_directory = ROOT / "data/stage0a" / RUN
    require(not any(p.is_symlink() for p in (ROOT / "data", ROOT / "data/stage0a", source_directory)), "Data directory symlinks prohibited")
    verified_data, descriptive = {}, {}
    for year in (2023, 2024):
        bars_15 = None
        for interval in ("15", "60"):
            name = f"BTCUSDT_{year}_{interval}.csv"
            window = Window.annual(year, interval)
            path = source_directory / name
            require(not path.is_symlink(), "Data-file symlink prohibited")
            require(sha256(path.read_bytes()) == record["data_csv_sha256"][str(path.relative_to(ROOT))], "Raw data hash mismatch: " + name)
            copied_manifest = BASE / "evidence" / (name + ".manifest.json")
            require(copied_manifest.read_bytes() == (source_directory / copied_manifest.name).read_bytes(), "Local/captured manifest differs")
            bars, manifest = read_dataset(source_directory, source_directory / copied_manifest.name, window)
            require(manifest["quality"]["status"] == "VALID" and len(bars) == manifest["quality"]["expected_rows"], "Coverage/quality failed")
            verified_data[name] = {"sha256": manifest["csv_sha256"], "rows": len(bars)}
            if interval == "15":
                bars_15 = bars
        calculated, _ = describe(bars_15, Window.annual(year, "15"), metadata["constraints"]["tick_size"], phase1_config)
        saved = load(ROOT / "reports/stage0a" / RUN / (str(year) + ".json"))
        require(all(saved[key] == value for key, value in calculated.items()), "Descriptive Stage-0A replay differs")
        descriptive[str(year)] = saved["groups"]["All"]["distributions"]["stop_range_valid"]["risk_to_cost"]
    require(descriptive == record["descriptive_risk_cost_evidence"], "Decision evidence differs from Stage-0A")
    environment_path = BASE / "environment.json"
    require(sha256(environment_path.read_bytes()) == config["numerical_environment_sha256"] == record["numerical_environment_sha256"], "Environment hash mismatch")
    require(sha256((ROOT / "requirements-research.lock").read_bytes()) == config["dependency_lock_sha256"] == record["dependency_lock_sha256"], "Dependency lock hash mismatch")
    verify_environment(load(environment_path))
    ui_path = ROOT / record["future_ui_requirement_path"]
    require(sha256(ui_path.read_bytes()) == record["future_ui_requirement_sha256"], "UI requirement changed")
    require("EXPERIMENTAL / UNVALIDATED" in ui_path.read_text() and "2.5" in ui_path.read_text(), "Missing experimental-K disclosure")
    result = {"status": "READY_TO_TAG", "checks": "PASS", "research_config_sha256": record["research_config_sha256"],
              "environment_sha256": record["numerical_environment_sha256"], "dependency_lock_sha256": record["dependency_lock_sha256"],
              "official_K_cost_stop": 2.5, "requests_audited_offline": len(run["requests"]), "datasets": verified_data,
              "phase1_commit": PHASE1_COMMIT, "original_design_tag_unchanged": True, "execution_gates": "OPEN_UNVERIFIED",
              "official_performance_validation_status": "UNVALIDATED", "stage0b_selection_holdout_executed": False,
              "new_market_data_downloaded": False}
    if require_tag:
        require(git("cat-file", "-t", "refs/tags/" + RESEARCH_TAG) == "tag", "Research tag is not annotated")
        target = git("rev-parse", RESEARCH_TAG + "^{commit}")
        require(target == git("rev-parse", "HEAD"), "Research tag must reference the verified current commit")
        for path in ("configs/research_v0.2.2.json", "research_freeze/v0.2.2/record.json", "research_freeze/v0.2.2/environment.json", "requirements-research.lock"):
            require(subprocess.check_output(["git", "show", target + ":" + path], cwd=ROOT) == (ROOT / path).read_bytes(), "Tagged freeze file differs: " + path)
        result.update(status="RESEARCH_PARAMETERS_FROZEN", research_tag=RESEARCH_TAG, commit=target)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--require-tag", action="store_true")
    args = parser.parse_args()
    try:
        print(json.dumps(verify_all(args.require_tag), indent=2, sort_keys=True))
    except (FreezeError, ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        print(json.dumps({"status": "BLOCKED", "reason": str(exc)}, sort_keys=True))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
