"""Frozen authorities and Stage-0B preservation; never loads trading-price data."""
import json
import subprocess
from pathlib import Path

from research.access import AccessDenied
from research.loader import sha256
from tools.verify_research_freeze import verify_environment

ROOT=Path(__file__).resolve().parents[2]
BASE="fd573b3d3b6f35f796defa74d2cbde00957f503c"
TAGS={"v0.2.2-design":"638ec6d99413c8dbc82a111209015953809ced08","v0.2.2-research-parameters":"826b05146e99a5a87e9951da9b4e0ac2deea1d09"}


def git(*args):
    return subprocess.check_output(["git",*args],cwd=ROOT)


def preflight():
    if subprocess.run(["git","merge-base","--is-ancestor",BASE,"HEAD"],cwd=ROOT).returncode:
        raise AccessDenied("EXPECTED_STAGE0B_COMMIT_NOT_ANCESTOR")
    for tag,oid in TAGS.items():
        if git("cat-file","-t",tag).strip()!=b"tag" or git("rev-parse",tag).decode().strip()!=oid:
            raise AccessDenied("FROZEN_TAG_CHANGED")
    names=git("ls-tree","-r","--name-only",BASE).decode().splitlines()
    for name in names:
        if name==".gitignore":
            continue
        p=ROOT/name
        if p.is_symlink() or p.read_bytes()!=git("show",BASE+":"+name):
            raise AccessDenied("EXISTING_FROZEN_OR_STAGE0B_FILE_CHANGED")
    config_bytes=(ROOT/"configs/research_v0.2.2.json").read_bytes()
    config=json.loads(config_bytes)
    environment=(ROOT/"research_freeze/v0.2.2/environment.json").read_bytes()
    if sha256(environment)!=config["numerical_environment_sha256"]:
        raise AccessDenied("FROZEN_ENVIRONMENT_HASH_CHANGED")
    verify_environment(json.loads(environment))
    return {"starting_commit":BASE,"current_commit":git("rev-parse","HEAD").decode().strip(),"config_sha256":sha256(config_bytes),
            "spec_sha256":sha256((ROOT/"STRATEGY_SPEC_v0.2.2.md").read_bytes()),"environment_sha256":sha256(environment),
            "freeze_tag_objects":TAGS,"stage0b_preserved":"PASS_BYTE_IDENTICAL_TO_STARTING_COMMIT"}
