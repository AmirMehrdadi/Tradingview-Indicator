"""One fixed offline conditional run of the original 24 Development ledgers."""
import json
import os
from datetime import datetime
from pathlib import Path
import sys

from research.access import UTC
from research.loader import canonical, sha256, write_new
from research.stage0b.output import restricted_directory, write_private, no_financial_outputs
from research.funding_lifecycle.accounting import SCENARIOS, encode
from .accounting import observations, prepare_path, attribute, LABEL, CALENDAR, AttributionError
from .guard import ROOT, PRIVATE, baseline, allowed_inputs, DevelopmentGuard, inventory, TAGS


def execute():
    baseline()  # Verify trusted manifests before constructing the exact data allowlist.
    run_id = datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    private = ROOT/'data/stage0b_private/funding_attribution'/run_id
    public = ROOT/'reports/funding_attribution/v0.2.2'/run_id
    guard = DevelopmentGuard(allowed_inputs(), private, public)
    sys.addaudithook(guard.audit)
    raw_observations, proof = inventory()
    checked = {y: observations(y, *rows) for y, rows in raw_observations.items()}
    # All sources are checked before creating any output.
    require_ignored = __import__('subprocess').run(['git', 'check-ignore', '--quiet',
                                                  str(private.relative_to(ROOT)/'probe')], cwd=ROOT)
    if require_ignored.returncode:
        raise RuntimeError('PRIVATE_OUTPUT_NOT_IGNORED')
    restricted_directory(private); public.mkdir(parents=True, exist_ok=False)
    summaries, output_hashes = [], {}
    for year in (2023, 2024):
        for i in range(1, 13):
            name = f'{year}_C{i:02}'
            raw = (PRIVATE/(name+'.json')).read_bytes()
            if sha256(raw) != proof['private_ledger_sha256'][name]:
                raise RuntimeError('INPUT_CHANGED_AFTER_PREFLIGHT')
            payload = json.loads(raw); immutable = canonical(payload)
            prepared = prepare_path(payload, proof['logical_run_id'])
            if prepared['year'] != year or prepared['candidate'] != f'C{i:02}':
                raise RuntimeError('PRIVATE_PATH_OWNER_MISMATCH')
            path_rows = []
            for scenario in SCENARIOS:
                before = canonical(encode(prepared))
                result = attribute(prepared, checked[year], scenario)
                repeated = attribute(prepared, checked[year], scenario)
                data = canonical(encode(result))
                if data != canonical(encode(repeated)) or before != canonical(encode(prepared)) or immutable != canonical(payload):
                    raise RuntimeError('DETERMINISM_OR_INPUT_MUTATION')
                filename = f'{name}_{scenario.mark_field}_{scenario.precedence}.json'
                write_private(private/filename, data); output_hashes[filename] = sha256(data)
                row = {'year': year, 'candidate': f'C{i:02}', 'scenario': scenario.identity,
                       'counts': result['counts'], 'completed': sum(t['state'] == 'COMPLETED' for t in result['trades']),
                       'censored': sum(t['state'] == 'CENSORED' for t in result['trades']),
                       'attribution_conservation': 'PASS', 'shared_execution_unchanged': 'PASS',
                       'deterministic_replay_sha256': sha256(data)}
                path_rows.append(row)
            summaries += path_rows
    if guard.blocked:
        raise RuntimeError('ACCESS_GUARD_VIOLATION')
    write_private(private/'checksums.json', canonical(output_hashes))
    source_hashes = {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))}
    manifest = {'run_id': run_id, 'classification': LABEL, 'calendar_authority': CALENDAR,
                'implementation_status': 'IMPLEMENTATION_VALIDATED', 'execution_status': 'CONDITIONAL_DEVELOPMENT_EXECUTED',
                'historical_funding_data': 'PARTIAL_DATA', 'official_strategy_profitability': 'UNVALIDATED',
                'source_proof': proof, 'source_files_sha256': source_hashes,
                'source_code_sha256': sha256(canonical(source_hashes)), 'paths': 24, 'scenarios_per_path': 6,
                'scenario_results': 144, 'results': summaries, 'private_output_sha256': output_hashes,
                'private_storage': str(private.relative_to(ROOT)), 'guard_violations': guard.blocked,
                'market_network_requests': 0, 'stage0b_engine_rerun': False, 'selection_holdout_access': False,
                'candidate_ranking_or_selection': False, 'public_financial_values': False,
                'tags': TAGS, 'tests': 'See verification.json and tests.log; no historical test discovery.'}
    no_financial_outputs({'source_proof': proof, 'results': summaries, 'private_output_sha256': output_hashes})
    write_new(public/'manifest.json', canonical(manifest))
    report = f'''# Conditional Development Funding attribution

Run: {run_id}. IMPLEMENTATION_VALIDATED / CONDITIONAL_DEVELOPMENT_EXECUTED.
CONDITIONAL_DEVELOPMENT_DIAGNOSTIC; USER_ATTESTED_OFFICIAL_CALENDAR.
The user's report of official Bybit confirmation supplies the conditional annual
calendar (1095 / 1098 settlements, 00:00/08:00/16:00 UTC). No independently retained
communication is claimed. Historical evidence and gates are not promoted.

Exactly 24 original candidate/year ledgers and six registered scenarios per path
were processed offline. Each accounting result was repeated in memory and matched
exactly. No Stage-0B engine or historical price path was rerun. Original events,
plans, fees, friction, sizing/day snapshots and occupancy were not altered.
Funding attribution and quantity conservation passed in all 144 scenario results.
Coverage/tie counts and source/output hashes are in manifest.json. No candidate
was ranked, selected or evaluated for official profitability.

Base: Close / FUNDING_BEFORE_OLD_OPEN_EXIT. Alternatives: Low and High, crossed
with OLD_OPEN_EXIT_BEFORE_FUNDING. OPEN exits of old positions are previewed only
for the alternate Funding quantity, never reordered in the execution ledger.
PRIOR_BAR exits precede Funding; same-OPEN new entries are exempt. Annual end
excludes its Funding/Open; each year/candidate starts Flat. Censored attribution
stays with its original entry and receives no completed-trade R metric.

APPROXIMATE_MARK_PREVIOUS_1M_CLOSE; exact_tick=false;
guaranteed_settlement_bounds=false. The absent pre-2023 minute remains absent.
Its sole exemption is zero old-position exposure at the annual 2023 start;
this does not certify raw or independent calendar completeness.

Funding uses unchanged Phase 4C context-independent exact Decimal arithmetic.
Pre-Funding amounts are the exact decimal representations of stored ledger
components (binary64-derived execution values), with no second friction charge.
Planned R is initial BTC quantity times the original frozen plan's price risk,
before costs; the adapter validates that risk against entry_ref and SL. Private
completed trade_R_net division uses local Decimal precision 50. This is a
representation of original execution accounting, not a replay using decimal fills.
No censored position is marked to market or assigned to another trade.

Private inputs match their retained checksum inventory and public event/count
audit. Original public Stage-0B evidence reports replay/hash PASS but does not
publish that private checksum digest; this provenance limitation is explicit.
Ignored immutable raw snapshots and all old outputs remain unmodified. Source
manifests and request provenance were authorized before market-body reads.
Private per-entry net accounting is create-only, mode 0600 in a 0700 directory,
Git-ignored, and excluded from reports and the review ZIP.

HISTORICAL_FUNDING_DATA = PARTIAL_DATA
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

No network, market acquisition, Pine/TradingView, Selection/Holdout, Bootstrap,
official profitability validation, external communication, new tag or push.
This conditional engineering result is not Research acceptance or data readiness.

Reproduce only under separate authorization for another create-only conditional
run: PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.funding_attribution.runner
'''
    write_new(public/'REPORT.md', report.encode())
    return {'status': 'CONDITIONAL_DEVELOPMENT_EXECUTED', 'report_directory': str(public),
            'run_id': run_id, 'paths': 24, 'scenario_results': 144, 'guard_violations': 0}


if __name__ == '__main__':
    try:
        print(json.dumps(execute(), sort_keys=True))
    except BaseException as exc:
        # Never expose an exception value or traceback that might include a ledger.
        print(json.dumps({'status': 'BLOCKED_ACCOUNTING_DEFECT' if isinstance(exc, AttributionError) else 'BLOCKED_INPUT_OR_INTEGRITY', 'reason_type': type(exc).__name__,
                          'private_details_suppressed': True}))
        sys.exit(2)
