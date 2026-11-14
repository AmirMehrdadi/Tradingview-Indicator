"""Offline Phase 4B evidence integrity only; no network, prices or trading paths."""
import base64
import gzip
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
BASE = "917927b379a8f1d3b93c1d7f88537060a6a3a1e0"
PHASE4A = "20261114T192333525994Z"
TAGS = {"v0.2.2-design": ("638ec6d99413c8dbc82a111209015953809ced08", "ac8fc4bb9b66a59c7224aaec1630a594b41d7e80"),
        "v0.2.2-research-parameters": ("826b05146e99a5a87e9951da9b4e0ac2deea1d09", "4bc7447755ef7a9dbd8832221f2ded5afc21401f")}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False)+"\n").encode()


def read(path):
    path = Path(path)
    assert path.is_relative_to(ROOT) and not any(p.is_symlink() for p in (path, *path.parents)), "UNSAFE_EVIDENCE_PATH"
    return path.read_bytes()


def load(path):
    return json.loads(read(path))


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.PIPE)


def instrument_examples(raw):
    results = []
    for block in re.findall(r"```json\s*\n(.*?)```", raw.decode(), re.S):
        # Official examples contain comments and multiple JSON responses in one fence.
        block = re.sub(r'("(?:\\.|[^"\\])*")|//[^\r\n]*', lambda m: m.group(1) or "", block)
        while block.strip():
            block = block.lstrip()
            try:
                value, used = json.JSONDecoder().raw_decode(block)
            except ValueError:
                break
            block = block[used:]
            for item in value.get("result", {}).get("list", []):
                if isinstance(item, dict) and item.get("contractType") == "LinearPerpetual":
                    results.append({k: item.get(k) for k in ("symbol", "contractType", "settleCoin", "fundingInterval")})
    return results


def verify():
    from research.funding.policy import Period
    manifest = load(OUT/"manifest.json")
    assert manifest["verdict"] == "PARTIAL_DATA"
    for name, digest in manifest["addendum_files_sha256"].items():
        assert re.fullmatch(r"[A-Za-z0-9_.-]+", name) and sha(read(OUT/name)) == digest, "ADDENDUM_FILE_CHANGED"
    baseline = load(OUT/"baseline_files_sha256.json")
    expected_names = set(git("ls-tree", "-r", "--name-only", BASE).decode().splitlines())
    assert set(baseline) == expected_names
    assert subprocess.run(["git", "merge-base", "--is-ancestor", BASE, "HEAD"], cwd=ROOT).returncode == 0
    for name, digest in baseline.items():
        assert sha(read(ROOT/name)) == digest == sha(git("show", BASE+":"+name)), "EXISTING_TRACKED_ARTIFACT_CHANGED"
    for tag, (oid, target) in TAGS.items():
        assert git("cat-file", "-t", tag).strip() == b"tag"
        assert git("rev-parse", tag).decode().strip() == oid
        assert git("rev-parse", tag+"^{commit}").decode().strip() == target
    captures = load(OUT/"captures.json")
    bodies = {}
    allowed = ("https://api.github.com/repos/bybit-exchange/", "https://raw.githubusercontent.com/bybit-exchange/", "https://www.bybit.com/en/learn/", "https://www.bybit.com/en/press/", "https://announcements.bybit.com/", "https://archive.org/wayback/available?", "https://web.archive.org/")
    for record in captures["requests"]:
        assert record["url"].startswith(allowed), "NON_DOCUMENT_SOURCE_URL"
        if record["status"] != "OK":
            continue
        relative = record["cache_relative_path"]
        assert relative.startswith(captures["cache_root_relative"]+"/") and ".." not in Path(relative).parts
        raw = read(ROOT/relative)
        assert sha(raw) == record["sha256"], "SOURCE_BODY_CHANGED"
        if "git_blob_sha1" in record:
            assert hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest() == record["git_blob_sha1"]
        if record.get("content_decoding") == "gzip":
            assert sha(gzip.decompress(raw)) == record["decoded_sha256"]
        bodies[record["source_id"]] = raw
    cdx = json.loads(bodies["archive_learn_cdx_2022_2024"])
    for check in captures["archive_payload_checks"]:
        raw = bodies[check["capture_id"]]
        got = base64.b32encode(hashlib.sha1(raw).digest()).decode()
        expected = next(row[5] for row in cdx[1:] if row[1] == check["archive_timestamp"])
        assert got == expected == check["cdx_sha1_base32"], "ARCHIVE_PAYLOAD_DATE_BINDING_FAILED"
        text = (gzip.decompress(raw) if raw.startswith(b"\x1f\x8b") else raw).decode()
        assert "every 8 hours" in text and "Bybit may adjust the funding time interval" in text and "BTCUSDT" in text
    wanted = {"symbol": "BTCUSDT", "contractType": "LinearPerpetual", "settleCoin": "USDT", "fundingInterval": 480}
    assert wanted in instrument_examples(bodies["docs_instrument_2023_pinned"])
    assert wanted in instrument_examples(bodies["docs_instrument_2024_pinned"])
    assert wanted not in instrument_examples(bodies["docs_instrument_20221230_pinned"])
    source_index = load(OUT/"sources.json")
    assert len(source_index["sources"]) == 12 and all(s["continuous_btcusdt_calendar_coverage_utc"] == [] for s in source_index["sources"])
    comparison = load(OUT/"inventory_comparison.json")
    snapshot_files, observed = 0, []
    public = ROOT/"reports/funding/v0.2.2"/PHASE4A
    phase4a = load(public/"manifest.json")
    for year in (2023, 2024):
        period = Period.annual(year)
        annual_bytes = read(public/f"{year}_manifest.json")
        assert sha(annual_bytes) == phase4a["annual_manifest_sha256"][str(year)]
        annual = json.loads(annual_bytes)
        assert annual["period"] == period.public() and annual["synthetic"] is False
        directory = ROOT/"data/funding/v0.2.2"/PHASE4A/str(year)
        assert read(directory/"manifest.json") == annual_bytes
        for name, digest in annual["files_sha256"].items():
            assert name in ("funding.json", "marks.json", "requests.json") or re.fullmatch(r"raw/\d{5}\.json", name)
            assert sha(read(directory/name)) == digest, "ORIGINAL_SNAPSHOT_CHANGED"
            snapshot_files += 1
        # Only settlement timestamps are analyzed. Mark files were hash-checked without decoding prices.
        times = []
        for row in load(directory/"funding.json"):
            period.settlement(row["settlement_ms"])
            times.append(row["settlement_ms"])
        assert times == sorted(set(times))
        hypothesis = set(range(period.start, period.end, 28800000))
        expected = next(v for v in comparison["annual"] if v["year"] == year)
        assert len(times) == expected["observed_settlements"]
        assert sha(canonical(times)) == expected["timestamp_inventory_sha256"]
        assert len(hypothesis-set(times)) == expected["hypothesis_grid_gaps"] == 0
        assert len(set(times)-hypothesis) == expected["hypothesis_grid_extra_points"] == 0
        assert expected["actual_missing_settlement_count"] is None
        observed.append({"year": year, "settlements": len(times), "calendar_proven": False})
    prior = load(public/"verification.json")
    assert prior["data_verdict"] == "PARTIAL_DATA" and prior["tests"]["total"] == 135
    assert sha(read(public/"tests.log")) == prior["tests"]["log_sha256"]
    assert b"Ran 135 tests" in read(public/"tests.log") and read(public/"tests.log").rstrip().endswith(b"OK")
    spec = read(ROOT/"STRATEGY_SPEC_v0.2.2.md").decode()
    order = spec.split("### 8.3.1", 1)[1].split("### 8.4", 1)[0]
    assert order.index("3. **UTC_DAY_RESET / PARTITION_START") < order.index("4. **FUNDING") < order.index("5. **SIGNAL_CLOSE") < order.index("6. **OPEN")
    reset = spec.split("### 9.0.2", 1)[1].split("### 9.0.3", 1)[0]
    assert "Flat" in reset and "pending" in reset
    boundary = load(OUT/"boundary.json")
    assert boundary["old_position_exposure_at_initial_funding"] == 0 and boundary["proof_type"].startswith("STRUCTURAL_DEDUCTION")
    return {"integrity": "PASS_EVIDENCE_INTEGRITY_ONLY", "verdict": "PARTIAL_DATA", "baseline_files_unchanged": len(baseline),
            "source_payloads_hash_verified": len(bodies), "archive_payload_date_bindings_verified": len(captures["archive_payload_checks"]),
            "original_snapshot_files_unchanged": snapshot_files, "freeze_tags": "UNCHANGED", "annual": observed,
            "initial_2023_mark": "NOT_REQUIRED_FOR_AUTHORIZED_ANNUAL_EXPOSURE_RAW_ABSENCE_PRESERVED",
            "original_135_test_evidence": "INTACT_NOT_RERUN", "network_or_market_acquisition": False,
            "position_simulation_or_private_ledger_access": False}


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), indent=2, sort_keys=True))
    except Exception:
        print('{"integrity":"FAILED","verdict":"PARTIAL_DATA","details":"Evidence check failed; no financial values disclosed"}')
        raise SystemExit(2)
