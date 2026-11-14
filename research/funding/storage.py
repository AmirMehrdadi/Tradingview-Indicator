"""Create-only, hashed snapshots; authorization before cache data reads/exports."""
import json
import re
from datetime import datetime
from pathlib import Path

from research.access import AccessDenied, UTC
from research.loader import canonical, sha256
from .policy import Period, FUNDING, MARK, authorize_request, authorize_response
from .validation import funding_rows, mark_rows


def ordinary_path(path):
    path=Path(path).absolute()
    if any(p.is_symlink() for p in (path,*path.parents)):
        raise AccessDenied("SYMLINK_STORAGE_PATH")
    return path


def write_once(path,data):
    path=ordinary_path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)


def validate_export(period,rates,marks,calls,bodies):
    period.validate()
    settlements=[]
    for rate in rates:
        period.settlement(rate['settlement_ms'])
        settlements.append(rate['settlement_ms'])
    normalized,_=funding_rows([{'symbol':'BTCUSDT','fundingRateTimestamp':str(r['settlement_ms']),'fundingRate':r['funding_rate']} for r in rates],period)
    if normalized!=rates:
        raise ValueError("NONCANONICAL_FUNDING_EXPORT")
    now=int(datetime.now(UTC).timestamp()*1000)
    rawmarks=[]
    for m in marks:
        period.mark_minute(m['settlement_ms'])
        if m['minute_open_ms']!=m['settlement_ms']-60000:
            raise AccessDenied("INVALID_MARK_LINKAGE_EXPORT")
        rawmarks.append([str(m['minute_open_ms']),m['open'],m['high'],m['low'],m['close']])
    normalized,_=mark_rows(rawmarks,settlements,period,now)
    if normalized!=marks:
        raise ValueError("NONCANONICAL_OR_UNLINKED_MARK_EXPORT")
    allowed_ids=set()
    for call in calls:
        if call['period']!=period.public():
            raise AccessDenied("REQUEST_PROVENANCE_PERIOD_MISMATCH")
        params=call['params']
        linked=tuple(t for t in settlements if call['path']==MARK and params['start']<=t-60000<=params['end'])
        authorize_request(period,call['path'],params,linked)
        if call['request_id'] in allowed_ids:
            raise ValueError("DUPLICATE_REQUEST_PROVENANCE_ID")
        allowed_ids.add(call['request_id'])
        if call['request_id'] in bodies:
            raw=bodies[call['request_id']]
            if sha256(raw)!=call['response_sha256'] or call['status']!='OK':
                raise ValueError("RAW_RESPONSE_HASH_OR_STATUS_MISMATCH")
            result=json.loads(raw)['result']
            authorize_response(period,call['path'],params,result['list'],linked)
    if not set(bodies)<=allowed_ids:
        raise AccessDenied("UNAUTHORIZED_RAW_RESPONSE_EXPORT")


def save_snapshot(directory,period,rates,marks,calls,bodies,quality,source_proof,synthetic=False):
    validate_export(period,rates,marks,calls,bodies)  # Before creating a directory or export file.
    if quality.get('year')!=period.year:
        raise AccessDenied("EXPORT_QUALITY_YEAR_MISMATCH")
    directory=ordinary_path(directory)
    if directory.exists():
        raise FileExistsError("IMMUTABLE_SNAPSHOT_ALREADY_EXISTS")
    files={'funding.json':canonical(rates),'marks.json':canonical(marks),'requests.json':canonical(calls)}
    files.update({f'raw/{i:05d}.json':body for i,body in sorted(bodies.items())})
    manifest={'schema_version':1,'phase':'phase4a-development-funding-mark','symbol':'BTCUSDT','category':'linear','period':period.public(),
              'synthetic':bool(synthetic),'files_sha256':{name:sha256(data) for name,data in files.items()},'quality':quality,'source_proof':source_proof,
              'proxy_classification':'APPROXIMATE_MARK_PREVIOUS_1M_CLOSE','raw_response_policy':'Only authorized responses retained; errors/unauthorized bodies retain hashes/status only'}
    for name,data in files.items():
        write_once(directory/name,data)
    write_once(directory/'manifest.json',canonical(manifest))
    return manifest


def read_snapshot(directory,period,allow_synthetic=False):
    period.validate()  # Unauthorized caller years/ranges rejected before ANY path read.
    directory=ordinary_path(directory)
    manifest=json.loads(ordinary_path(directory/'manifest.json').read_text())
    if manifest.get('phase')!='phase4a-development-funding-mark' or manifest.get('period')!=period.public() or manifest.get('symbol')!='BTCUSDT' or manifest.get('category')!='linear':
        raise AccessDenied("CACHE_PERIOD_OR_IDENTITY_MISMATCH")
    if manifest.get('synthetic') is not False and not (allow_synthetic and manifest.get('synthetic') is True):
        raise AccessDenied("SYNTHETIC_CACHE_NOT_REAL_EVIDENCE")
    files=manifest.get('files_sha256',{})
    if not {'funding.json','marks.json','requests.json'}<=set(files):
        raise AccessDenied("CACHE_DATA_INVENTORY_INVALID")
    for name in files:
        if name not in {'funding.json','marks.json','requests.json'} and not re.fullmatch(r'raw/\d{5}\.json',name):
            raise AccessDenied("CACHE_PATH_NOT_ALLOWED")
    # Authorize cached request metadata before opening any cached market-data file.
    request_bytes=ordinary_path(directory/'requests.json').read_bytes()
    if sha256(request_bytes)!=files['requests.json']:
        raise ValueError("CACHE_REQUEST_PROVENANCE_HASH_MISMATCH")
    for call in json.loads(request_bytes):
        if call.get('period')!=period.public():
            raise AccessDenied("CACHE_REQUEST_PERIOD_MISMATCH")
        params=call['params']
        linked=()
        if call['path']==MARK:
            lo,hi=params.get('start'),params.get('end')
            if type(lo) is not int or type(hi) is not int or not 0<=hi-lo<60000*1000:
                raise AccessDenied("CACHE_MARK_REQUEST_BOUNDS_INVALID")
            linked=tuple(t+60000 for t in range(lo,hi+1,60000))
        authorize_request(period,call['path'],params,linked)
    checked={}
    for name,digest in files.items():
        target=ordinary_path(directory/name)
        data=target.read_bytes()
        if sha256(data)!=digest:
            raise ValueError("CACHE_SHA256_MISMATCH")
        checked[name]=data
    rates=json.loads(checked['funding.json'])
    for row in rates:
        period.settlement(row['settlement_ms'])
    marks=json.loads(checked['marks.json'])
    calls=json.loads(checked['requests.json'])
    bodies={int(Path(name).stem):data for name,data in checked.items() if name.startswith('raw/')}
    validate_export(period,rates,marks,calls,bodies)
    return rates,marks,manifest
