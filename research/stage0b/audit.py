"""Audit committed counts against restricted execution evidence, without disclosure."""
import json
import re
import subprocess

from research.access import AccessDenied
from research.loader import canonical, sha256
from .guard import ROOT
from .model import IntegrityError
from .output import no_financial_outputs, validate_path_summary


def check_summary(p):
    validate_path_summary(p)
    g = p["N_after_each_gate"]
    if list(sorted(g)) != list("ABCDEFG") or any(type(n) is not int or n < 0 for n in g.values()):
        raise IntegrityError("INVALID_FUNNEL_COUNTS")
    if any(g[a] < g[b] for a, b in zip("ABCDEF", "BCDEFG")):
        raise IntegrityError("NONMONOTONIC_FUNNEL")
    if (p["N_raw_candidate"] != g["A"] or p["N_nonoverlap"] != g["G"] or p["N_signals"] != g["G"]
            or p["N_signals"] != p["N_filled"]+p["N_rejected_margin"]
            or p["N_filled"] != p["N_completed"]+p["N_censored"]
            or p["N_censored"] not in (0, 1) or p["distance_from_120"] != p["N_completed"]-120):
        raise IntegrityError("PUBLIC_COUNT_CONSERVATION_FAILED")
    for gate in "ABCDEFG":
        if sum(p["direction_counts"][d]["after_"+gate] for d in ("Long", "Short")) != g[gate]:
            raise IntegrityError("DIRECTION_FUNNEL_CONSERVATION_FAILED")
    for name in ("N_filled", "N_completed", "N_censored", "N_rejected_margin"):
        if sum(p["direction_counts"][d][name] for d in ("Long", "Short")) != p[name]:
            raise IntegrityError("DIRECTION_COUNT_CONSERVATION_FAILED")


def audit_run(run_id):
    if not re.fullmatch(r"\d{8}T\d{12}Z", run_id):
        raise AccessDenied("INVALID_RUN_ID")
    public = ROOT / "reports/stage0b/v0.2.2" / run_id
    private = ROOT / "data/stage0b_private/v0.2.2" / run_id
    manifest = json.loads((public / "manifest.json").read_text())
    counts = json.loads((public / "counts.json").read_text())
    no_financial_outputs(manifest)
    if sha256(canonical(counts)) != manifest["public_counts_sha256"]:
        raise IntegrityError("PUBLIC_COUNTS_HASH_CHANGED")
    for name, digest in manifest["source_files_sha256"].items():
        if not name.startswith("research/stage0b/") or (ROOT / name).is_symlink() or sha256((ROOT / name).read_bytes()) != digest:
            raise IntegrityError("EXECUTED_SOURCE_HASH_CHANGED")
    expected = {(year, f"C{i:02d}") for year in (2023, 2024) for i in range(1, 13)}
    if len(counts) != 24 or {(p["year"], p["candidate"]) for p in counts} != expected:
        raise IntegrityError("CANDIDATE_YEAR_INVENTORY_CHANGED")
    if private.is_symlink() or private.stat().st_mode & 0o777 != 0o700:
        raise AccessDenied("PRIVATE_DIRECTORY_PERMISSIONS")
    digests = json.loads((private / "checksums.json").read_text())
    for p in counts:
        check_summary(p)
        label = f"{p['year']}_{p['candidate']}"
        if (public / (label+".json")).read_bytes() != canonical(p):
            raise IntegrityError("PER_PATH_EXPORT_CHANGED")
        target = private / (label+".json")
        if target.is_symlink() or target.stat().st_mode & 0o777 != 0o600:
            raise AccessDenied("PRIVATE_FILE_PERMISSIONS")
        raw = target.read_bytes()
        if sha256(raw) != digests[label]:
            raise IntegrityError("PRIVATE_LEDGER_HASH_CHANGED")
        payload = json.loads(raw)
        events = payload["ledger"]
        plans, entered, closed, rejected, exits = {}, set(), set(), set(), {}
        for event in events:
            kind = event["event"]
            if kind == "SIGNAL_AND_BRACKETS_QUEUED":
                plan = event["plan"]
                identity = plan["entry_id"]
                if identity in plans:
                    raise IntegrityError("DUPLICATE_LEDGER_SIGNAL")
                plans[identity] = plan
            elif kind == "ENTRY_FILLED":
                identity = event["entry_id"]
                if identity not in plans or identity in entered:
                    raise IntegrityError("ORPHAN_OR_DUPLICATE_LEDGER_ENTRY")
                entered.add(identity)
            elif kind == "ENTRY_REJECTED_MARGIN":
                rejected.add(event["entry_id"])
            elif kind == "EXIT_LEG":
                identity = event["entry_id"]
                leg = (identity, event["bracket"])
                if identity not in entered or leg in exits or identity in closed:
                    raise IntegrityError("ORPHAN_OR_DUPLICATE_LEDGER_EXIT")
                exits[leg] = event["quantity_steps"]
                if event["quantity_steps"] != plans[identity][f"tp{event['bracket']}_steps"]:
                    raise IntegrityError("LEDGER_PARTIAL_QUANTITY_CHANGED")
            elif kind == "POSITION_CLOSED":
                identity = event["entry_id"]
                if identity in closed or sum(exits.get((identity, leg), 0) for leg in (1, 2)) != plans[identity]["total_steps"]:
                    raise IntegrityError("LEDGER_CLOSURE_QUANTITY_CHANGED")
                closed.add(identity)
        if (len(plans) != p["N_signals"] or len(entered) != p["N_filled"] or len(closed) != p["N_completed"]
                or len(rejected) != p["N_rejected_margin"] or len(entered-closed) != p["N_censored"]
                or entered & rejected or entered | rejected != set(plans)):
            raise IntegrityError("LEDGER_PUBLIC_COUNT_MISMATCH")
        if payload["funding_cashflows"] is not None or payload["funding_status"] != "MISSING_NOT_ZERO":
            raise IntegrityError("FUNDING_MISSINGNESS_CHANGED")
        if subprocess.run(["git", "check-ignore", "--quiet", str(target.relative_to(ROOT))], cwd=ROOT).returncode != 0:
            raise AccessDenied("PRIVATE_LEDGER_NOT_IGNORED")
    return {"status": "PASS", "candidate_year_paths": 24, "count_and_ledger_conservation": "PASS",
            "source_and_export_hashes": "PASS", "private_permissions_and_git_ignore": "PASS",
            "financial_values_disclosed": False}


if __name__ == "__main__":
    import sys
    try:
        print(json.dumps(audit_run(sys.argv[1]), sort_keys=True))
    except Exception:
        print('{"status":"BLOCKED","reason":"STAGE0B_AUDIT_FAILED_DETAILS_SUPPRESSED"}')
        raise SystemExit(2)
