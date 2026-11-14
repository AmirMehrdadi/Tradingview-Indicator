"""Acquire/validate evidence only; no import of any position simulation engine."""
import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

from research.access import AccessDenied, UTC
from research.loader import canonical,sha256
from . import VERSION
from .acquire import funding_scan,verify_disjoint_windows,fetch_marks
from .guard import ROOT,preflight
from .http import Client
from .policy import Period
from .storage import save_snapshot,read_snapshot,write_once,ordinary_path
from .validation import funding_rows,mark_rows,calendar_diagnostics,classify_settlement

DOC_SOURCES=["https://bybit-exchange.github.io/docs/v5/market/history-fund-rate","https://bybit-exchange.github.io/docs/v5/market/mark-kline","https://bybit-exchange.github.io/docs/v5/rate-limit"]


def year_acquisition(client,period,progress=None):
    period.validate()
    rows,scan=funding_scan(client,period)
    rates,rate_quality=funding_rows(rows,period)
    verification=verify_disjoint_windows(client,period,rates) if scan['scan_complete'] and rates else {'status':'NOT_RUN','matches':False,'reason':'PRIMARY_SCAN_INCOMPLETE_OR_NO_VALID_RECORDS'}
    times=[r['settlement_ms'] for r in rates]
    if progress:
        progress({'year':period.year,'stage':'FUNDING_SCAN','valid_records':len(rates),'scan':scan,'independent_requery':verification['status']})
    mark_raw,mark_errors=fetch_marks(client,period,times,progress=(lambda done,total:progress({'year':period.year,'stage':'MARK_QUERIES','completed_batches':done,'total_batches':total})) if progress else None)
    marks,mark_quality=mark_rows(mark_raw,times,period,int(datetime.now(UTC).timestamp()*1000))
    mark_quality['acquisition_status']='REQUIRED_LINKED_MINUTES_ATTEMPTED' if mark_quality['requestable_minutes'] else 'NOT_ATTEMPTED_NO_OBSERVED_REQUESTABLE_SETTLEMENTS'
    classifications=[classify_settlement(t,period) for t in times]
    anomalies=[c for c in classifications if c['alignment']!='ALIGNED_15M']
    calendar=calendar_diagnostics(rates,period,scan['scan_complete'],verification['matches'])
    blockers=[]
    if not scan['scan_complete']:
        blockers.append(scan['reason'])
    if not rates:
        blockers.append('NO_VALID_FUNDING_SETTLEMENTS_ACQUIRED_COVERAGE_UNKNOWN')
    if rate_quality['invalid_records'] or rate_quality['conflicting_settlements_ms']:
        blockers.append('INVALID_OR_CONFLICTING_FUNDING_RECORDS')
    if verification['status']!='MATCH':
        blockers.append('INDEPENDENT_WINDOW_REQUERY_NOT_VERIFIED')
    blockers.append('HISTORICAL_SETTLEMENT_CALENDAR_NOT_INDEPENDENTLY_ESTABLISHED')
    if mark_quality['status']!='COMPLETE_FOR_OBSERVED_SETTLEMENTS' or not times:
        blockers.append('SETTLEMENT_MARK_MINUTE_COVERAGE_NOT_COMPLETE_OR_NOT_ESTABLISHED')
    if anomalies:
        blockers.append('FUNDING_ALIGNMENT_UNRESOLVED_NO_INTRABAR_ORDER_INFERRED')
    quality={'year':period.year,'status':'PARTIAL_DATA' if rates or marks else 'BLOCKED','funding':rate_quality,'funding_scan':scan,
             'funding_requery':verification,'historical_calendar':calendar,'marks':mark_quality,'mark_retrieval_errors':mark_errors,
             'alignment_anomalies':anomalies,'alignment_anomaly_count':len(anomalies),'alignment_evidence':'CHECKED_OBSERVED_TIMESTAMPS_ONLY' if times else 'NOT_EVALUABLE_NO_OBSERVED_TIMESTAMPS',
             'blockers':blockers,'net_research_validity':'NOT_EVALUATED_NO_POSITION_SIMULATION','funding_zero_substitution':False}
    return rates,marks,quality,classifications


def report_text(manifests,run_id):
    lines=['# Phase 4A — Development Funding and settlement Mark data','',f'Run: `{run_id}`. No position simulations or performance evaluations were run.','',
           '| Year | Valid Funding records | Actual missing settlements | Linked Mark minutes | Missing requestable Mark minutes | Unavailable boundary/alignment minutes | Alignment anomalies | Verdict |',
           '|---|---:|---|---:|---:|---:|---|---|']
    for m in manifests:
        q=m['quality']
        lines.append(f"| {q['year']} | {q['funding']['valid_unique']} | UNKNOWN — calendar unproven | {q['marks']['valid_linked_minutes']} | {len(q['marks']['missing_minutes'])} | {len(q['marks']['unavailable_minutes'])} | {q['alignment_anomaly_count'] if q['funding']['valid_unique'] else 'NOT EVALUABLE'} | {q['status']} |")
    lines+=['','Zero acquired/linked records is not evidence that zero settlements occurred. Mark coverage denominators include only observed valid settlements; absent Funding means the true required-minute denominator is UNKNOWN.','']
    for m in manifests:
        q=m['quality']
        lines += [f"## {q['year']} evidence",'',f"Primary scan: `{q['funding_scan']['reason']}`. Independent requery: `{q['funding_requery']['status']}`.",'','Open prerequisites:']+['- '+b for b in q['blockers']]+['']
    lines += ['## Interpretation and scope','',
              'Historical API timestamps and bounded re-queries are retained as observational evidence. They do not prove the absence of unpublished/omitted settlements or distinguish a missing row from a historical interval change. No historical calendar is inferred from current metadata; no current instrument endpoint is called. Missing-settlement counts remain UNKNOWN unless supported by independent dated schedule/interval-change evidence. Modal cadence and suspected internal gaps are diagnostics only, never fabricated settlement records.',
              '', 'Mark requests contain only contiguous runs of necessary linked minutes. The minute before the Development start is forbidden; any such required boundary minute remains explicitly unavailable. The minute before a 2024 settlement may be in 2023, which remains inside the global Development allowlist. A 2025 boundary settlement is excluded entirely. No 2022 price is requested.',
              '', 'The stored proxy is APPROXIMATE_MARK_PREVIOUS_1M_CLOSE, retaining the same minute\'s Low and High. It is not an exact settlement tick and the sensitivity prices are not guaranteed bounds. Off-15m timestamps are flagged FUNDING_ALIGNMENT_UNRESOLVED without fabricated execution ordering.',
              '', 'Raw responses and normalized datasets are immutable create-only snapshots under ignored data/funding/. Public manifests retain hashes, explicit request ranges, provenance, quality and missing reasons. No financial ledger is accessed or modified. Data readiness cannot establish net-research validity: later funding application, required sensitivities and execution validation remain separate gates.',
              '', '## Reproduction','', 'Use the unchanged frozen CPython/NumPy environment through the repository wrapper. A fresh acquisition creates a new run; identical normalized observations produce identical dataset hashes even when retrieval timestamps/raw response metadata differ. Exact offline replay uses the saved snapshots.', '', '```',
              'sh tools/research_python.sh -m unittest discover -s tests -v',
              'sh tools/research_python.sh -m research.funding acquire',
              f'sh tools/research_python.sh -m research.funding verify {run_id}', '```','', 'Official protocol references:']+['- '+u for u in DOC_SOURCES]+['']
    return '\n'.join(lines)


def verify_run(run_id):
    if not __import__('re').fullmatch(r'\d{8}T\d{12}Z',run_id):
        raise AccessDenied('INVALID_RUN_ID')
    preflight()
    report=ROOT/'reports/funding/v0.2.2'/run_id
    root=json.loads((report/'manifest.json').read_text())
    for name,digest in root['source_files_sha256'].items():
        if not name.startswith('research/funding/') or sha256((ROOT/name).read_bytes())!=digest:
            raise ValueError('EXECUTED_FUNDING_SOURCE_CHANGED')
    for year in (2023,2024):
        period=Period.annual(year)
        directory=ROOT/'data/funding/v0.2.2'/run_id/str(year)
        _,_,manifest=read_snapshot(directory,period)
        expected=json.loads((report/f'{year}_manifest.json').read_text())
        if manifest!=expected or sha256(canonical(manifest))!=root['annual_manifest_sha256'][str(year)]:
            raise ValueError('PUBLIC_AND_PRIVATE_MANIFEST_MISMATCH')
    return {'status':'PASS_SNAPSHOT_INTEGRITY_ONLY','data_verdict':root['data_verdict'],'run_id':run_id,'positions_simulated':False}


def execute():
    proof=preflight()
    run_id=datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    data_root=ordinary_path(ROOT/'data/funding/v0.2.2'/run_id)
    public=ordinary_path(ROOT/'reports/funding/v0.2.2'/run_id)
    if subprocess.run(['git','check-ignore','--quiet','data/funding/probe'],cwd=ROOT).returncode:
        raise AccessDenied('MARKET_DATA_STORAGE_NOT_GIT_IGNORED')
    source_files={str(p.relative_to(ROOT)):sha256(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*.py'))}
    proof.update(code_sha256=sha256(canonical(source_files)),source_files_sha256=source_files,documentation_sources=DOC_SOURCES)
    client=Client()
    manifests=[]
    for year in (2023,2024):
        period=Period.annual(year)
        rates,marks,quality,_=year_acquisition(client,period,lambda event:print(json.dumps(event,sort_keys=True),flush=True))
        calls=[c for c in client.calls if c['period']['year']==year]
        bodies={c['request_id']:client.bodies[c['request_id']] for c in calls if c['request_id'] in client.bodies}
        manifest=save_snapshot(data_root/str(year),period,rates,marks,calls,bodies,quality,proof)
        read_snapshot(data_root/str(year),period)
        manifests.append(manifest)
        write_once(public/f'{year}_manifest.json',canonical(manifest))
    verdict='PARTIAL_DATA' if any(m['quality']['funding']['valid_unique'] or m['quality']['marks']['valid_linked_minutes'] for m in manifests) else 'BLOCKED'
    root={'version':VERSION,'run_id':run_id,'data_verdict':verdict,'source_files_sha256':source_files,'code_sha256':proof['code_sha256'],
          'frozen_authority':proof,'annual_manifest_sha256':{str(m['period']['year']):sha256(canonical(m)) for m in manifests},
          'positions_simulated':False,'stage0b_rerun':False,'selection_holdout_access':'DENIED','request_count':len(client.calls),
          'allowed_endpoints':['/v5/market/funding/history','/v5/market/mark-price-kline'],'calendar_evidence':'NO_INDEPENDENT_DATED_HISTORICAL_CALENDAR_AVAILABLE','net_research_validity':'NOT_EVALUATED'}
    write_once(public/'manifest.json',canonical(root))
    write_once(public/'requests.json',canonical(client.calls))
    write_once(public/'REPORT.md',report_text(manifests,run_id).encode())
    check=verify_run(run_id)
    write_once(public/'integrity.json',canonical(check))
    return {'verdict':verdict,'run_id':run_id,'request_count':len(client.calls),'report':str(public/'REPORT.md'),'snapshot_integrity':check['status']}


def main():
    parser=argparse.ArgumentParser(description='Development-only Funding/Mark acquisition; no position simulation')
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('acquire')
    verify=sub.add_parser('verify')
    verify.add_argument('run_id')
    args=parser.parse_args()
    try:
        result=execute() if args.command=='acquire' else verify_run(args.run_id)
    except Exception as exc:
        result={'verdict':'BLOCKED','reason':str(exc) if isinstance(exc,AccessDenied) else type(exc).__name__,'financial_details_disclosed':False}
    print(json.dumps(result,indent=2,sort_keys=True))
    return 0 if result.get('status')=='PASS_SNAPSHOT_INTEGRITY_ONLY' or result.get('verdict')=='DATA_READY' else 2
