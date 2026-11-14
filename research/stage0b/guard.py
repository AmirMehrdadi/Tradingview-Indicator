"""Preflight all frozen authorities/hashes/environment before parsing prices."""
import json
import subprocess
from pathlib import Path

from research.access import AccessDenied, Window
from research.loader import sha256, read_dataset
from tools.verify_research_freeze import validate_config, verify_environment

ROOT = Path(__file__).resolve().parents[2]
RUN = "20261114T165617836854Z"
FREEZE_COMMIT = "4bc7447755ef7a9dbd8832221f2ded5afc21401f"
FROZEN_OBJECTS = {"v0.2.2-design": "638ec6d99413c8dbc82a111209015953809ced08",
                  "v0.2.2-research-parameters": "826b05146e99a5a87e9951da9b4e0ac2deea1d09"}


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def _same_frozen_file(name):
    path = ROOT / name
    if path.is_symlink() or path.read_bytes() != git("show", FREEZE_COMMIT+":"+name):
        raise AccessDenied("FROZEN_FILE_CHANGED")


def preflight():
    if subprocess.run(["git", "merge-base", "--is-ancestor", FREEZE_COMMIT, "HEAD"], cwd=ROOT).returncode != 0:
        raise AccessDenied("HEAD_NOT_DESCENDANT_OF_FROZEN_RESEARCH_COMMIT")
    for tag, expected in FROZEN_OBJECTS.items():
        if git("cat-file", "-t", "refs/tags/"+tag).strip() != b"tag" or git("rev-parse", "refs/tags/"+tag).decode().strip() != expected:
            raise AccessDenied("FROZEN_TAG_CHANGED")
    if git("rev-parse", "v0.2.2-research-parameters^{commit}").decode().strip() != FREEZE_COMMIT:
        raise AccessDenied("FROZEN_COMMIT_CHANGED")
    for name in ("STRATEGY_SPEC_v0.2.2.md", "configs/research_v0.2.2.json", "requirements-research.lock",
                 "research_freeze/v0.2.2/record.json", "research_freeze/v0.2.2/environment.json"):
        _same_frozen_file(name)
    base = ROOT / "research_freeze/v0.2.2"
    config = json.loads((ROOT / "configs/research_v0.2.2.json").read_text())
    record = json.loads((base / "record.json").read_text())
    environment_bytes = (base / "environment.json").read_bytes()
    if sha256((ROOT / "configs/research_v0.2.2.json").read_bytes()) != record["research_config_sha256"] or sha256(environment_bytes) != config["numerical_environment_sha256"]:
        raise AccessDenied("FROZEN_CONFIG_OR_ENVIRONMENT_HASH_CHANGED")
    # Environment verification precedes any price-data parsing.
    verify_environment(json.loads(environment_bytes))
    for name, expected in record["evidence_files_sha256"].items():
        if not name.startswith("research_freeze/v0.2.2/evidence/") or (ROOT / name).is_symlink() or sha256((ROOT / name).read_bytes()) != expected:
            raise AccessDenied("FROZEN_EVIDENCE_CHANGED")
    metadata = json.loads((base / "evidence/instrument.json").read_text())
    validate_config(config, (ROOT / "STRATEGY_SPEC_v0.2.2.md").read_text(), metadata)
    provenance_path = "reports/stage0a/"+RUN+"/analysis_provenance.json"
    _same_frozen_file(provenance_path)
    original = json.loads((ROOT / provenance_path).read_text())
    for name, expected in original["implementation_files_sha256"].items():
        if not name.startswith("research/") or (ROOT / name).is_symlink() or sha256((ROOT / name).read_bytes()) != expected:
            raise AccessDenied("FROZEN_PHASE1_HELPER_CHANGED")
    expected_names = {f"data/stage0a/{RUN}/BTCUSDT_{y}_{i}.csv" for y in (2023, 2024) for i in ("15", "60")}
    if set(record["data_csv_sha256"]) != expected_names:
        raise AccessDenied("UNAUTHORIZED_DATA_INVENTORY")
    directory = ROOT / "data/stage0a" / RUN
    if any(p.is_symlink() for p in (ROOT / "data", ROOT / "data/stage0a", directory)):
        raise AccessDenied("DATA_DIRECTORY_SYMLINK")
    checked = {}
    # Verify every dataset hash and every manifest range before parsing ANY market prices.
    for year in (2023, 2024):
        for interval in ("15", "60"):
            window = Window.annual(year, interval)
            name = f"BTCUSDT_{year}_{interval}.csv"
            data_path = directory / name
            manifest_path = directory / (name+".manifest.json")
            if data_path.is_symlink() or manifest_path.is_symlink() or manifest_path.read_bytes() != (base / "evidence" / manifest_path.name).read_bytes():
                raise AccessDenied("DATA_MANIFEST_CHANGED")
            manifest = json.loads(manifest_path.read_text())
            if manifest["window"] != {"year": year, "interval": interval, "start": window.start, "end": window.end, "anchor": window.anchor}:
                raise AccessDenied("DATA_WINDOW_CHANGED")
            digest = sha256(data_path.read_bytes())
            if digest != record["data_csv_sha256"][str(data_path.relative_to(ROOT))] or digest != manifest["csv_sha256"]:
                raise AccessDenied("DATA_HASH_CHANGED")
            checked[name] = {"sha256": digest, "quality": manifest["quality"]}
    data = {}
    for year in (2023, 2024):
        data[year] = {}
        for interval in ("15", "60"):
            window = Window.annual(year, interval)
            path = directory / f"BTCUSDT_{year}_{interval}.csv.manifest.json"
            bars, manifest = read_dataset(directory, path, window)
            if manifest["quality"]["status"] != "VALID" or len(bars) != manifest["quality"]["expected_rows"]:
                raise AccessDenied("DATA_QUALITY_NOT_VALID")
            data[year][interval] = bars
    proof = {"frozen_commit": FREEZE_COMMIT, "annotated_tag_objects": FROZEN_OBJECTS,
             "config_sha256": record["research_config_sha256"], "environment_sha256": config["numerical_environment_sha256"],
             "dataset_hashes_checked_before_price_processing": True, "datasets": checked,
             "funding_rates": "MISSING_NOT_RETRIEVED", "settlement_mark": "MISSING_NOT_RETRIEVED",
             "metadata_assumption": "HISTORICAL_INSTRUMENT_SPEC_ASSUMPTION"}
    return config, metadata, data, proof
