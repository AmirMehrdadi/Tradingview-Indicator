"""Run and replay exactly 24 independent Development paths, entirely offline."""
import contextlib
import json
import socket
import subprocess
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from research.access import AccessDenied, UTC, Window
from research.loader import canonical, sha256, write_new
from . import VERSION
from .engine import Engine
from .features import build_features
from .guard import ROOT, preflight
from .model import IntegrityError
from .output import no_financial_outputs, restricted_directory, write_private, write_public_summary, report_text
from .audit import audit_run


@contextlib.contextmanager
def offline_only():
    with patch.object(socket, "getaddrinfo", side_effect=AccessDenied("STAGE0B_NETWORK_PROHIBITED")), \
         patch.object(socket, "create_connection", side_effect=AccessDenied("STAGE0B_NETWORK_PROHIBITED")), \
         patch.object(socket.socket, "connect", side_effect=AccessDenied("STAGE0B_NETWORK_PROHIBITED")):
        yield


def frequency_diagnostic(paths):
    baseline = [p for p in paths if p["candidate"] == "C01"]
    if sorted(p["year"] for p in baseline) != [2023, 2024]:
        raise IntegrityError("BASELINE_FREQUENCY_REQUIRES_TWO_YEARS")
    value = sum(p["N_completed"] for p in baseline)/2
    return {"C01_mean_annual_completed": value, "threshold": 150,
            "status": "LOW_SIGNAL_FREQUENCY" if value < 150 else "NO_LOW_SIGNAL_FREQUENCY_FLAG",
            "candidate_elimination": False}


def execute():
    with offline_only():
        config, metadata, data, proof = preflight()
        source_hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))}
        code_hash = sha256(canonical(source_hashes))
        logical_id = sha256(canonical({"code": code_hash, "config": proof["config_sha256"], "data": {k: v["sha256"] for k, v in proof["datasets"].items()}}))[:20]
        run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        output = ROOT / "reports/stage0b/v0.2.2" / run_id
        private_base = ROOT / "data/stage0b_private"
        if private_base.is_symlink() or (ROOT / "data").is_symlink():
            raise AccessDenied("PRIVATE_STORAGE_SYMLINK")
        if subprocess.run(["git", "check-ignore", "--quiet", "data/stage0b_private/probe"], cwd=ROOT).returncode != 0:
            raise AccessDenied("PRIVATE_STORAGE_NOT_GIT_IGNORED")
        if not private_base.exists():
            private_base.mkdir(mode=0o700)
        else:
            import os
            os.chmod(private_base, 0o700)
        private_version = private_base / "v0.2.2"
        if private_version.is_symlink():
            raise AccessDenied("PRIVATE_STORAGE_SYMLINK")
        if not private_version.exists():
            private_version.mkdir(mode=0o700)
        else:
            import os
            os.chmod(private_version, 0o700)
        private = private_version / run_id
        restricted_directory(private)
        output.mkdir(parents=True, exist_ok=False)
        summaries, private_hashes = [], {}
        for year in (2023, 2024):
            features = build_features(data[year]["15"], data[year]["60"], Window.annual(year, "15"), config)
            for candidate in config["candidate_combinations"]:
                bounds = (float(metadata["instrument"]["priceFilter"]["minPrice"]), float(metadata["instrument"]["priceFilter"]["maxPrice"]))
                engine = Engine(candidate, features.window, config, logical_id, bounds, "VALID_FROZEN_SHA256_VERIFIED")
                summary = engine.run(features)
                # Full replay from a NEW engine, never from a previous candidate's accepted-trade list.
                replay = Engine(candidate, features.window, config, logical_id, bounds, "VALID_FROZEN_SHA256_VERIFIED")
                repeated = replay.run(features)
                private_bytes = canonical(engine.private_payload())
                if canonical(summary) != canonical(repeated) or sha256(private_bytes) != sha256(canonical(replay.private_payload())):
                    raise IntegrityError("INDEPENDENT_PATH_REPLAY_MISMATCH")
                write_private(private / f"{year}_{candidate}.json", private_bytes)
                private_hashes[f"{year}_{candidate}"] = sha256(private_bytes)
                write_public_summary(output, summary)
                summaries.append(summary)
        if len(summaries) != 24:
            raise IntegrityError("EXPECTED_24_PATHS")
        write_private(private / "checksums.json", canonical(private_hashes))
        diagnostic = frequency_diagnostic(summaries)
        no_financial_outputs(diagnostic)
        counts_hash = sha256(canonical(summaries))
        invalid = [f"{p['year']}_{p['candidate']}" for p in summaries if p["execution_model_validity"] != "RESEARCH_MODEL_PREFUNDING_COUNTS"]
        manifest = {"version": VERSION, "run_id": run_id, "logical_run_id": logical_id, "code_sha256": code_hash,
                    "source_files_sha256": source_hashes, "input_verification": proof, "public_counts_sha256": counts_hash,
                    "unique_candidate_year_paths": 24, "full_replay_of_each_path": "PASS", "financial_ledger_values_published": False,
                    "private_storage": "RESTRICTED_MODE_0700_DIRECTORY_0600_FILES_GIT_IGNORED", "funding_adjusted_research": "NOT_EVALUABLE_MISSING_FUNDING_AND_MARK",
                    "status": "BLOCKED_MARGIN_MODEL" if invalid else "EXECUTED_PREFUNDING_FEASIBILITY_VERIFIED",
                    "invalid_execution_paths": invalid,
                    "execution_authority": "Explicit Phase 3 user request supersedes Phase 2 execution-scope wording, without changing any frozen parameters.",
                    "commands": ["sh tools/research_python.sh -m unittest discover -s tests -v", "sh tools/research_python.sh -m research.stage0b run"],
                    "execution_gates": "OPEN_UNVERIFIED", "candidate_ranking": "NOT_PERFORMED", "selection_and_holdout": "NOT_ACCESSED_NOT_RUN"}
        no_financial_outputs(manifest)
        write_new(output / "manifest.json", canonical(manifest))
        write_new(output / "counts.json", canonical(summaries))
        write_new(output / "frequency_diagnostic.json", canonical(diagnostic))
        write_new(output / "REPORT.md", report_text(summaries, diagnostic).encode("utf-8"))
        audit = audit_run(run_id)
        write_new(output / "audit.json", canonical(audit))
        if invalid:
            return {"status": "BLOCKED", "reason": "MARGIN_MODEL_EVENT", "affected_paths": invalid, "report": str(output / "REPORT.md")}
        return {"status": manifest["status"], "run_id": run_id, "paths": 24, "replay": "PASS", "counts_sha256": counts_hash,
                "C01_frequency": diagnostic, "report": str(output / "REPORT.md"), "funding_evidence": "MISSING_NOT_ZERO"}


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stage-0B: exactly 24 offline pre-funding Development feasibility paths")
    parser.add_argument("command", choices=["run"])
    parser.parse_args()
    try:
        result = execute()
    except Exception as exc:
        # Never print exception arguments, object reprs, tracebacks or private accounting values.
        allowed = isinstance(exc, (AccessDenied, IntegrityError))
        result = {"status": "BLOCKED", "reason_code": str(exc) if allowed else type(exc).__name__,
                  "financial_details_suppressed": True}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result["status"] == "BLOCKED" else 0
