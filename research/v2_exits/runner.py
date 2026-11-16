"""Exactly 48 independent V2 paths; retained V1 is the unchanged reference."""
import json
import stat
import sys
import time
from datetime import datetime
from pathlib import Path

from research.access import UTC, Window
from research.loader import canonical, sha256, read_dataset, write_new
from research.stage0b.features import build_features
from research.stage0b.output import restricted_directory, write_private
from research.funding_attribution.guard import (ROOT, PRIVATE, DevelopmentGuard, allowed_inputs, inventory, ordinary_path, git)
from research.funding_attribution.accounting import observations, prepare_path, attribute
from research.funding_lifecycle.accounting import Scenario, encode
from .engine import ExitExperiment, ARMS
from .metrics import metrics

BASELINE = '2100d62ef0e42c3f8230d9ac1760e2cb28f270f2'
REFERENCE_RUN = '20261115T204128239342Z'


def verify_baseline():
    import hashlib
    rows = [r for r in git('ls-tree','-rz',BASELINE).split(b'\0') if r]
    if len(rows) != 234:
        raise ValueError('BASELINE_INVENTORY_CHANGED')
    for row in rows:
        metadata,name=row.split(b'\t');mode,kind,obj=metadata.decode().split()
        p=ordinary_path(ROOT/name.decode());raw=p.read_bytes()
        if kind!='blob' or hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=obj:
            raise ValueError('BASELINE_FILE_CHANGED')
        if ('100755' if p.stat().st_mode & stat.S_IXUSR else '100644') != mode:
            raise ValueError('BASELINE_MODE_CHANGED')


def signal_plans(payload):
    return {(e['plan']['signal_time'],e['plan']['direction']):e['plan']
            for e in payload['ledger'] if e['event']=='SIGNAL_AND_BRACKETS_QUEUED'}


def execute():
    started=time.monotonic();verify_baseline()
    reference=json.loads((ROOT/f'reports/funding_attribution/v0.2.2/{REFERENCE_RUN}/manifest.json').read_text())
    references=ROOT/reference['private_storage']
    inputs=allowed_inputs()
    for y in (2023,2024):
        for i in range(1,13):
            name=f'{y}_C{i:02}_close_FUNDING_BEFORE_OLD_OPEN_EXIT.json'
            inputs.add(ordinary_path(references/name))
    run_id=datetime.now(UTC).strftime('%Y%m%dT%H%M%S%fZ')
    private=ROOT/'data/stage0b_private/v2_exits'/run_id
    public=ROOT/'reports/v2_exits'/run_id
    guard=DevelopmentGuard(inputs,private,public);sys.addaudithook(guard.audit)
    raw_observations,proof=inventory();checked={y:observations(y,*r) for y,r in raw_observations.items()}
    original={};base_results={}
    # Establish all source/reference identities before any new experiment outputs.
    for y in (2023,2024):
        for i in range(1,13):
            label=f'{y}_C{i:02}';path=ordinary_path(PRIVATE/(label+'.json'));raw=path.read_bytes()
            if sha256(raw)!=proof['private_ledger_sha256'][label]:raise ValueError('V1_INPUT_HASH_CHANGED')
            original[y,f'C{i:02}']=json.loads(raw)
            name=label+'_close_FUNDING_BEFORE_OLD_OPEN_EXIT.json';path=ordinary_path(references/name)
            raw=path.read_bytes()
            if sha256(raw)!=reference['private_output_sha256'][name] or stat.S_IMODE(path.stat().st_mode)!=0o600:
                raise ValueError('V1_ACCOUNTING_IDENTITY_CHANGED')
            base_results[y,f'C{i:02}']=json.loads(raw)
    data={}
    for y in (2023,2024):
        data[y]={}
        for interval in ('15','60'):
            directory=ROOT/'data/stage0a/20261114T165617836854Z'
            data[y][interval]=read_dataset(directory,directory/f'BTCUSDT_{y}_{interval}.csv.manifest.json',Window.annual(y,interval))[0]
    config=json.loads((ROOT/'configs/research_v0.2.2.json').read_text())
    metadata=json.loads((ROOT/'research_freeze/v0.2.2/evidence/instrument.json').read_text())
    bounds=(float(metadata['instrument']['priceFilter']['minPrice']),float(metadata['instrument']['priceFilter']['maxPrice']))
    source_hashes={str(p.relative_to(ROOT)):sha256(p.read_bytes()) for p in sorted(Path(__file__).parent.glob('*')) if p.is_file()}
    import subprocess
    if subprocess.run(['git','check-ignore','--quiet',str(private.relative_to(ROOT)/'probe')],cwd=ROOT).returncode:
        raise ValueError('PRIVATE_NOT_IGNORED')
    restricted_directory(private);public.mkdir(parents=True,exist_ok=False)
    public_rows=[];financial=[];output_hashes={}
    logical=sha256(canonical({'sources':source_hashes,'config':proof['config_sha256'],'data':proof['dataset_sha256']}))[:20]
    old_counts=json.loads((ROOT/'reports/stage0b/v0.2.2/20261114T183819594592Z/counts.json').read_text())
    for y in (2023,2024):
        features=build_features(data[y]['15'],data[y]['60'],Window.annual(y,'15'),config)
        for i in range(1,13):
            candidate=f'C{i:02}';base_payload=original[y,candidate];base_metric=metrics(base_payload,base_results[y,candidate])
            base_plans=signal_plans(base_payload)
            financial.append(dict(year=y,candidate=candidate,arm='V1_REFERENCE',metrics=base_metric,
                                  quality_events=next(x['quality_events'] for x in old_counts if x['year']==y and x['candidate']==candidate)))
            for arm in ARMS:
                identity=logical+':'+arm
                engine=ExitExperiment(candidate,features.window,config,identity,bounds,'VALID_FROZEN_SHA256_VERIFIED',arm=arm)
                counts=engine.run(features)
                if counts['execution_model_validity']!='RESEARCH_MODEL_PREFUNDING_COUNTS':
                    raise ValueError('EXPERIMENT_INVALID_MARGIN_MODEL')
                original_counts=next(x for x in old_counts if x['year']==y and x['candidate']==candidate)
                if any(counts['N_after_each_gate'][k]!=original_counts['N_after_each_gate'][k] for k in 'ABCD'):
                    raise ValueError('SIGNAL_FORMULA_OR_INPUT_DIVERGENCE')
                payload=engine.private_payload();before=canonical(payload)
                prepared=prepare_path(payload,identity);accounting=attribute(prepared,checked[y],Scenario())
                if canonical(payload)!=before:raise ValueError('EXECUTION_MUTATED_BY_FUNDING')
                measured=metrics(payload,accounting);plans=signal_plans(payload);common=set(plans)&set(base_plans)
                changed_qty=sum(plans[k]['total_steps']!=base_plans[k]['total_steps'] for k in common)
                row=dict(year=y,candidate=candidate,arm=arm,completed=measured['completed'],censored=measured['censored'],
                         signals=len(plans),signals_retained=len(common),signals_added=len(set(plans)-set(base_plans)),
                         signals_missing=len(set(base_plans)-set(plans)),common_signals_quantity_changed=changed_qty,
                         daily_stop_activations=counts['daily_stop_activations'],quality_events=counts['quality_events'],
                         conservation='PASS',funding_scope='CONDITIONAL_CLOSE_FUNDING_FIRST',
                         signal_formula_prefix_A_B_C_D='MATCH_V1')
                public_rows.append(row)
                deltas={k:measured[k]-base_metric[k] if measured[k] is not None and base_metric[k] is not None else None
                        for k in ('completed','win_rate','net_usdt','mean_R','max_realized_drawdown_R')}
                financial.append(dict(year=y,candidate=candidate,arm=arm,metrics=measured,differences_vs_V1=deltas,
                                      path_difference=row))
                filename=f'{y}_{candidate}_{arm}.json'
                private_result=dict(arm=arm,execution=payload,activation_events=engine.activations,
                                    funding=accounting,metrics=measured,differences_vs_V1=deltas)
                raw=canonical(encode(private_result));write_private(private/filename,raw);output_hashes[filename]=sha256(raw)
    raw=canonical(encode(financial));write_private(private/'comparison.json',raw);output_hashes['comparison.json']=sha256(raw)
    write_private(private/'checksums.json',canonical(output_hashes))
    result=dict(run_id=run_id,baseline_commit=BASELINE,classification='V2_EXPLORATORY_CONDITIONAL_DEVELOPMENT',
                historical_funding_data='PARTIAL_DATA',official_strategy_profitability='UNVALIDATED',
                calendar_authority='USER_ATTESTED_OFFICIAL_CALENDAR',source_proof=proof,
                source_files_sha256=source_hashes,reference_run=REFERENCE_RUN,
                reference_output_sha256={n:d for n,d in reference['private_output_sha256'].items() if '_close_FUNDING_BEFORE' in n},
                private_storage=str(private.relative_to(ROOT)),private_output_sha256=output_hashes,
                executed_paths=48,reference_paths_reused=24,reference_engine_reruns=0,
                funding_scenarios='BASE_ONLY; six-scenario V2 robustness not evaluated',paths=public_rows,
                guard_violations=guard.blocked,elapsed_seconds=round(time.monotonic()-started,6),
                ranking_or_selection=False,market_data_acquisition=False,selection_holdout_access=False,
                pine_execution=False,push=False)
    if guard.blocked:raise ValueError('ACCESS_GUARD_VIOLATION')
    write_new(public/'manifest.json',canonical(result))
    report='''# First controlled V2 exit-management experiment

V2_EXPLORATORY_CONDITIONAL_DEVELOPMENT. Only two pre-registered policies:
V2_A_BREAKEVEN_AFTER_TP1 and V2_B_FULL_EXIT_AT_TP1. V1_REFERENCE reuses the
original immutable ledgers/accounting; V1 is neither modified nor rerun.
48 V2 candidate/year paths are independently simulated with the unchanged V1
feature calculations, entry/filter rules, initial-risk sizing function, historical
instrument assumptions and costs. Account, occupancy, daily gate, consumption and
subsequent entries are path-specific; identical accepted trade lists are not
assumed. Manifest counts disclose added/missing signals and changed quantities.

A: initial SL/targets/planned R remain frozen. After an actual TP1 fill only,
remaining SL becomes actual economic entry-fill rounded down for Long/up for
Short to the original tick. This is price breakeven, not fee/friction breakeven.
Open gaps use adverse Open fills, never guaranteed entry-price execution.
Newly marketable intrabar BE stops beyond the known TP1 touch use that touch
price with adverse friction, never an unvisited, more favorable BE reference.
An active stop takes precedence over targets when both are reachable. Initial
SL plus TP1 in a bar stops first without activating BE. If intrabar TP1 activates
BE and the same bar reaches BE, model TP1 then BE before TP2 and register
BE_ACTIVATION_INTRABAR_AMBIGUOUS. This pessimistic sequence is an explicit
research assumption; no actual intrabar ordering is asserted.

B: all quantity closes at frozen TP1 with adverse friction and fees. The two
original quantity allocations are booked simultaneously at the same TP1 price
as one logical whole-position exit, solely to reuse quantity/fee conservation.
There is no retained TP2 exposure or independent partial-execution timing. The
original sizing/quantity eligibility gates are preserved, including minimum
requirements of the original allocations; no new entry eligibility is introduced.

Funding reuses unchanged exact attribution mathematics, previous-minute Close
and FUNDING_BEFORE_OLD_OPEN_EXIT only. Six-scenario V2 Funding robustness is not
evaluated. Funding never changes shared pre-Funding sizing/day snapshots.
Calendar coverage is conditional on USER_ATTESTED_OFFICIAL_CALENDAR, not a new
independent primary-source verification. APPROXIMATE_MARK_PREVIOUS_1M_CLOSE;
exact_tick=false; guaranteed_settlement_bounds=false. Initial-2023 no-old-exposure
exemption and annual-end censoring remain narrowly scoped.

Private comparison.json contains all 72 arm/candidate/year metrics and explicit
V1 deltas. All execution/accounting and financial aggregates remain create-only
under ignored restricted private storage (0700 directories, 0600 files); they
are not committed or included in the review ZIP. Public evidence contains only
technical counts, input/output/code identities, anomaly counts and limitations.
Realized drawdown uses POSITION_CLOSED order and completed trade net R; censored
Funding stays separate and is not assigned to another completed trade. Costs
embedded in fills are not deducted again. No arm or candidate is selected.

HISTORICAL_FUNDING_DATA = PARTIAL_DATA
OFFICIAL_STRATEGY_PROFITABILITY = UNVALIDATED
PINE_COMPILE = UNVERIFIED
PINE_RUNTIME_VALIDATION = UNVERIFIED
NUMERICAL_PARITY = UNVERIFIED
TRADINGVIEW_EXECUTION_PARITY = UNVERIFIED
SAFE_TV_ENVIRONMENT = UNVERIFIED
2025_SELECTION = LOCKED_NOT_ACCESSED
2026_FINAL_HOLDOUT = LOCKED_NOT_ACCESSED

Development comparisons are exploratory and reuse previously examined data.
Better Development outcomes cannot establish independent validation. No network,
market acquisition, parameter sweep, candidate ranking, TradingView, Selection,
Holdout, calendar research, tag change or push is performed.

Reproduction requires the retained local frozen inputs, exact environment and a
separate authorization for another create-only run:
PYTHONDONTWRITEBYTECODE=1 sh tools/research_python.sh -m research.v2_exits.runner
'''
    write_new(public/'REPORT.md',report.encode())
    return dict(status='EXPERIMENT_EXECUTED_CONDITIONALLY',run_id=run_id,public_directory=str(public),
                executed_V2_paths=48,unchanged_V1_references=24,guard_violations=0)


if __name__=='__main__':
    try:print(json.dumps(execute(),sort_keys=True))
    except BaseException as exc:
        print(json.dumps(dict(status='BLOCKED',reason_type=type(exc).__name__,private_details_suppressed=True)))
        sys.exit(2)
