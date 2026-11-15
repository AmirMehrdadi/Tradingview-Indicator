"""Exact retained-input inventory; no discovery of arbitrary data directories."""
import json
import os
from pathlib import Path
import stat
import subprocess

from tests.run_phase4c_regression import OfflineGuard
from research.access import AccessDenied, Window
from research.loader import canonical, sha256
from research.funding.policy import Period
from research.funding.storage import ordinary_path, read_snapshot
from research.stage0b.audit import audit_run
from tools.verify_research_freeze import verify_environment, validate_config

ROOT = Path(__file__).resolve().parents[2]
BASELINE = '9d451025c8d748a21987c59f35d8b5a0564e5e64'
STAGE = '20261114T183819594592Z'
FUNDING = '20261114T192333525994Z'
DATA = '20261114T165617836854Z'
STAGE_PUBLIC = ROOT/'reports/stage0b/v0.2.2'/STAGE
FUNDING_PUBLIC = ROOT/'reports/funding/v0.2.2'/FUNDING
PRIVATE = ROOT/'data/stage0b_private/v0.2.2'/STAGE
TAGS = {'v0.2.2-design': ('638ec6d99413c8dbc82a111209015953809ced08', 'ac8fc4bb9b66a59c7224aaec1630a594b41d7e80'),
        'v0.2.2-research-parameters': ('826b05146e99a5a87e9951da9b4e0ac2deea1d09', '4bc7447755ef7a9dbd8832221f2ded5afc21401f')}


def require(ok, code):
    if not ok:
        raise AccessDenied(code)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)


def load(path):
    return json.loads(ordinary_path(path).read_text())


def baseline():
    require(git('rev-parse', '--show-toplevel').decode().strip() == str(ROOT), 'REPOSITORY_CHANGED')
    require(git('rev-parse', '--abbrev-ref', 'HEAD').strip() == b'main', 'BRANCH_CHANGED')
    require(subprocess.run(['git', 'merge-base', '--is-ancestor', BASELINE, 'HEAD'], cwd=ROOT).returncode == 0,
            'UNAPPROVED_ANCESTRY')
    for tag, (obj, target) in TAGS.items():
        require(git('cat-file', '-t', tag).strip() == b'tag' and git('rev-parse', tag).decode().strip() == obj
                and git('rev-parse', tag+'^{}').decode().strip() == target, 'FROZEN_TAG_CHANGED')
    count = 0
    for row in git('ls-tree', '-rz', '--full-tree', BASELINE).split(b'\0'):
        if not row:
            continue
        meta, name = row.split(b'\t'); mode, kind, obj = meta.decode().split()
        path = ordinary_path(ROOT/name.decode()); raw = path.read_bytes()
        import hashlib
        digest = hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
        require(kind == 'blob' and digest == obj, 'BASELINE_FILE_CHANGED')
        require(('100755' if path.stat().st_mode & stat.S_IXUSR else '100644') == mode, 'BASELINE_MODE_CHANGED')
        count += 1
    require(count == 222, 'BASELINE_INVENTORY_CHANGED')


def allowed_inputs():
    """Only trusted tracked manifests are consulted when building the allowlist."""
    paths = {PRIVATE/'checksums.json'}
    paths.update(PRIVATE/f'{year}_C{i:02}.json' for year in (2023, 2024) for i in range(1, 13))
    for year in (2023, 2024):
        for interval in ('15', '60'):
            p = ROOT/f'data/stage0a/{DATA}/BTCUSDT_{year}_{interval}.csv'
            paths.update((p, Path(str(p)+'.manifest.json')))
        m = load(FUNDING_PUBLIC/f'{year}_manifest.json')
        d = ROOT/f'data/funding/v0.2.2/{FUNDING}/{year}'
        paths.add(d/'manifest.json')
        for name in m['files_sha256']:
            import re
            require(name in {'funding.json', 'marks.json', 'requests.json'} or re.fullmatch(r'raw/\d{5}\.json', name),
                    'UNAUTHORIZED_SNAPSHOT_MEMBER')
            paths.add(d/name)
    return {ordinary_path(p) for p in paths}


class DevelopmentGuard(OfflineGuard):
    def __init__(self, inputs, private_output, public_output):
        super().__init__()
        self.inputs = frozenset(inputs)
        self.outputs = {private_output, public_output}

    def check_path(self, value, writing=False):
        if isinstance(value, int):
            return
        path = Path(os.path.abspath(os.fsdecode(value)))
        resolved = Path(os.path.realpath(path))
        if path != resolved:
            # Interpreter and system library symlinks remain subject to the base guard.
            if ROOT/'data' in path.parents or ROOT/'data' in resolved.parents:
                self.deny('DATA_SYMLINK_DENIED')
        if not writing and path in self.inputs and resolved == path:
            return
        if not writing and path.parent == ROOT/'pine' and path.suffix == '.pine' and path == resolved:
            return  # Static baseline hashing only; no Pine execution capability.
        if path.parent in self.outputs:
            return
        super().check_path(value, writing)

    def audit(self, event, args):
        if event == 'subprocess.Popen':
            command = args[1]
            if isinstance(command, (tuple, list)) and len(command) == 4 and list(command[:3]) == ['git', 'check-ignore', '--quiet']:
                path = ROOT/command[3]
                if path in self.inputs or any(p in path.parents for p in self.outputs):
                    self.subprocesses_checked += 1
                    return
        super().audit(event, args)


def inventory():
    """Hash all inputs before decoding price or ledger bodies; never rerun Engine."""
    baseline()
    config = load(ROOT/'configs/research_v0.2.2.json')
    environment = load(ROOT/'research_freeze/v0.2.2/environment.json')
    verify_environment(environment)
    validate_config(config, (ROOT/'STRATEGY_SPEC_v0.2.2.md').read_text(),
                    load(ROOT/'research_freeze/v0.2.2/evidence/instrument.json'))
    sm, fm = load(STAGE_PUBLIC/'manifest.json'), load(FUNDING_PUBLIC/'manifest.json')
    require(sm['run_id'] == STAGE and sm['invalid_execution_paths'] == [] and sm['unique_candidate_year_paths'] == 24,
            'ORIGINAL_EXECUTION_NOT_VALID')
    for p, digest in {**sm['source_files_sha256'], **fm['source_files_sha256']}.items():
        require(sha256((ROOT/p).read_bytes()) == digest, 'ORIGINAL_SOURCE_CHANGED')
    record = load(ROOT/'research_freeze/v0.2.2/record.json')
    paths = {}
    for y in (2023, 2024):
        for i in ('15', '60'):
            window = Window.annual(y, i); p = ROOT/f'data/stage0a/{DATA}/BTCUSDT_{y}_{i}.csv'
            mpath = Path(str(p)+'.manifest.json'); m = load(mpath)
            require(mpath.read_bytes() == (ROOT/'research_freeze/v0.2.2/evidence'/mpath.name).read_bytes(),
                    'ORIGINAL_DATA_MANIFEST_CHANGED')
            require(m['window'] == dict(year=y, interval=i, start=window.start, end=window.end, anchor=window.anchor),
                    'UNAUTHORIZED_DATA_WINDOW')
            digest = record['data_csv_sha256'][str(p.relative_to(ROOT))]
            require(m['csv_sha256'] == digest == sm['input_verification']['datasets'][p.name]['sha256'],
                    'DATA_HASH_AUTHORITY_MISMATCH')
            paths[p] = digest
    annual = {}
    for y in (2023, 2024):
        period = Period.annual(y); period.validate()
        p = ROOT/f'data/funding/v0.2.2/{FUNDING}/{y}/manifest.json'; raw = ordinary_path(p).read_bytes()
        require(raw == (FUNDING_PUBLIC/f'{y}_manifest.json').read_bytes()
                and sha256(raw) == fm['annual_manifest_sha256'][str(y)], 'FUNDING_MANIFEST_CHANGED')
        m = json.loads(raw)
        require(m['period'] == period.public() and m['symbol'] == 'BTCUSDT' and m['category'] == 'linear'
                and m['synthetic'] is False, 'UNAUTHORIZED_SNAPSHOT_IDENTITY')
        annual[y] = p.parent
    require(stat.S_IMODE(ordinary_path(PRIVATE).stat().st_mode) == 0o700, 'PRIVATE_DIRECTORY_PERMISSIONS')
    hashes = load(PRIVATE/'checksums.json')
    require(set(hashes) == {f'{y}_C{i:02}' for y in (2023, 2024) for i in range(1, 13)}, 'PRIVATE_INVENTORY_CHANGED')
    for name, digest in hashes.items():
        p = ordinary_path(PRIVATE/(name+'.json'))
        require(stat.S_IMODE(p.stat().st_mode) == 0o600, 'PRIVATE_FILE_PERMISSIONS')
        require(sha256(p.read_bytes()) == digest, 'PRIVATE_LEDGER_HASH_CHANGED')
    for p, digest in paths.items():
        require(sha256(ordinary_path(p).read_bytes()) == digest, 'ORIGINAL_DATA_HASH_CHANGED')
    observations = {y: read_snapshot(d, Period.annual(y))[:2] for y, d in annual.items()}
    audit = audit_run(STAGE)
    require(audit['status'] == 'PASS', 'ORIGINAL_LEDGER_AUDIT_FAILED')
    proof = {'stage0b_run_id': STAGE, 'funding_run_id': FUNDING, 'logical_run_id': sm['logical_run_id'],
             'baseline_commit': BASELINE, 'config_sha256': record['research_config_sha256'],
             'spec_sha256': sha256((ROOT/'STRATEGY_SPEC_v0.2.2.md').read_bytes()),
             'environment_sha256': config['numerical_environment_sha256'],
             'dataset_sha256': {str(p.relative_to(ROOT)): d for p, d in paths.items()},
             'funding_annual_manifest_sha256': fm['annual_manifest_sha256'],
             'funding_files_sha256': {str(y): load(FUNDING_PUBLIC/f'{y}_manifest.json')['files_sha256'] for y in annual},
             'private_ledger_sha256': hashes, 'private_checksum_file_sha256': sha256((PRIVATE/'checksums.json').read_bytes()),
             'original_event_count_audit': audit,
             'private_hash_anchor_limitation': 'Original published evidence records replay/hash PASS but does not publish the private checksum digest. Current retained checksums and public event/count audit agree; no engine replay performed.'}
    return observations, proof
