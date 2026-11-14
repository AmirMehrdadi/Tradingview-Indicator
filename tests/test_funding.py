"""Phase 4A deterministic tests use explicitly synthetic public API fixtures."""
import io
import json
import socket
import tempfile
import unittest
import urllib.error
import urllib.parse
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from research.access import AccessDenied,timestamp
from research.loader import canonical,sha256
from research.funding.acquire import funding_scan,verify_disjoint_windows,fetch_marks,mark_batches
from research.funding.http import Client,AcquisitionError,NoRedirect
from research.funding.policy import Period,MINUTE,FUNDING,MARK,authorize_request,authorize_response
from research.funding.storage import save_snapshot,read_snapshot
from research.funding.validation import funding_rows,mark_rows,calendar_diagnostics,classify_settlement,classify_fill_event
from research.funding.runner import year_acquisition


def rate(t,value='0.0001'):
    return {'symbol':'BTCUSDT','fundingRateTimestamp':str(t),'fundingRate':value}


def minute(t):
    return [str(t-MINUTE),'100','102','98','101']


def envelope(rows,path=FUNDING,code=0):
    result={'category':'linear','list':rows}
    if path==MARK:
        result['symbol']='BTCUSDT'
    return canonical({'retCode':code,'result':result})


def query(url):
    parts=urllib.parse.urlsplit(url)
    return parts.path,dict(urllib.parse.parse_qsl(parts.query))


def fake_client(transport,**kwargs):
    return Client(transport=transport,sleep=lambda _:None,**kwargs)


class PolicyTests(unittest.TestCase):
    def setUp(self):
        self.p=Period.annual(2023)
        self.t=self.p.start+8*3600000
        self.f={'category':'linear','symbol':'BTCUSDT','startTime':self.p.start,'endTime':self.p.end-1,'limit':200}
        self.m={'category':'linear','symbol':'BTCUSDT','interval':'1','start':self.t-MINUTE,'end':self.t-1,'limit':1}

    def test_exact_annual_and_leap_year_boundaries(self):
        self.assertEqual((self.p.end-self.p.start)//86400000,365)
        p=Period.annual(2024)
        self.assertEqual((p.end-p.start)//86400000,366)
        self.p.settlement(self.p.start)
        self.p.settlement(self.p.end-1)
        with self.assertRaises(AccessDenied):
            self.p.settlement(self.p.end)

    def test_future_or_forged_year_denied_before_any_network(self):
        transport=unittest.mock.Mock()
        c=fake_client(transport)
        for y in (2022,2025,2026,True,'2023'):
            with self.subTest(year=y),self.assertRaises(AccessDenied):
                Period.annual(y)
        with self.assertRaises(AccessDenied):
            c.get(replace(self.p,end=self.p.end+1),FUNDING,self.f)
        transport.assert_not_called()

    def test_request_requires_both_explicit_timestamps_and_max_200(self):
        authorize_request(self.p,FUNDING,self.f)
        for key,value in (('limit',201),('limit',True),('startTime',self.p.start-1),('endTime',self.p.end)):
            with self.subTest(key=key),self.assertRaises(AccessDenied):
                authorize_request(self.p,FUNDING,dict(self.f,**{key:value}))
        del self.f['startTime']
        with self.assertRaises(AccessDenied):
            authorize_request(self.p,FUNDING,self.f)

    def test_only_two_unauthenticated_exact_endpoints_allowed(self):
        for path in ('/v5/market/kline','/v5/market/instruments-info','/v5/account/wallet-balance','https://example.invalid'):
            with self.subTest(path=path),self.assertRaises(AccessDenied):
                authorize_request(self.p,path,self.f)
        for key,value in (('symbol','ETHUSDT'),('category','inverse'),('api_key','synthetic')):
            with self.subTest(key=key),self.assertRaises(AccessDenied):
                authorize_request(self.p,FUNDING,dict(self.f,**{key:value}))

    def test_necessary_mark_minutes_only_no_unrelated_range(self):
        authorize_request(self.p,MARK,self.m,(self.t,))
        for params,events in ((self.m,()),(dict(self.m,start=self.t-2*MINUTE,limit=2),(self.t,)),(dict(self.m,interval='15'),(self.t,))):
            with self.assertRaises(AccessDenied):
                authorize_request(self.p,MARK,params,events)

    def test_first_development_prior_minute_forbidden_but_2024_boundary_allowed(self):
        with self.assertRaises(AccessDenied):
            self.p.mark_minute(self.p.start)
        p=Period.annual(2024)
        self.assertEqual(p.mark_minute(p.start),timestamp('2023-12-31T23:59:00Z'))
        with self.assertRaises(AccessDenied):
            p.mark_minute(p.end)

    def test_unauthorized_response_denied_before_rate_or_price_parse_and_cache(self):
        bad=rate(self.p.end,'deliberately-unparseable')
        c=fake_client(lambda _:envelope([bad]))
        with self.assertRaises(AccessDenied):
            c.get(self.p,FUNDING,self.f)
        self.assertEqual(c.bodies,{})
        self.assertEqual(c.calls[0]['status'],'ACCESS_DENIED_RESPONSE')
        with self.assertRaises(AccessDenied):
            funding_rows([bad],self.p)

    def test_mark_response_outside_requested_minute_rejected_before_prices(self):
        c=fake_client(lambda _:envelope([[str(self.t),'bad','bad','bad','bad']],MARK))
        with self.assertRaises(AccessDenied):
            c.get(self.p,MARK,self.m,(self.t,))
        self.assertEqual(c.bodies,{})


class PaginationNetworkTests(unittest.TestCase):
    def setUp(self):
        self.p=Period.annual(2023)
        self.times=[self.p.start+i*8*3600000 for i in range(5)]

    def transport(self,records):
        def get(url):
            path,params=query(url)
            lo,hi=int(params['startTime']),int(params['endTime'])
            rows=[r for r in records if lo<=int(r['fundingRateTimestamp'])<=hi]
            return envelope(sorted(rows,key=lambda r:int(r['fundingRateTimestamp']),reverse=True)[:int(params['limit'])],path)
        return get

    def test_reverse_pagination_explicit_end_moves_one_millisecond(self):
        c=fake_client(self.transport([rate(t) for t in self.times]))
        rows,status=funding_scan(c,self.p,limit=2)
        normalized,_=funding_rows(rows,self.p)
        self.assertEqual([r['settlement_ms'] for r in normalized],self.times)
        self.assertTrue(status['scan_complete'])
        self.assertEqual(c.calls[1]['params']['endTime'],self.times[3]-1)
        self.assertEqual(len(c.calls),3)
        self.assertTrue(all(call['params']['startTime']==self.p.start for call in c.calls))

    def test_short_pages_do_not_terminate_early(self):
        wrapped=self.transport([rate(t) for t in self.times])
        def short(url):
            data=json.loads(wrapped(url))
            data['result']['list']=data['result']['list'][:1]
            return canonical(data)
        c=fake_client(short)
        rows,status=funding_scan(c,self.p)
        self.assertEqual(len(rows),5)
        self.assertEqual(len(c.calls),5)
        self.assertTrue(status['scan_complete'])

    def test_unordered_page_normalized_without_losing_records(self):
        wrapped=self.transport([rate(t) for t in self.times])
        def ascending(url):
            data=json.loads(wrapped(url))
            data['result']['list'].reverse()
            return canonical(data)
        rows,status=funding_scan(fake_client(ascending),self.p,limit=2)
        self.assertEqual([r['settlement_ms'] for r in funding_rows(rows,self.p)[0]],self.times)

    def test_boundary_overlap_outside_explicit_page_fails_closed(self):
        wrapped=self.transport([rate(t) for t in self.times])
        calls=[]
        def overlap(url):
            calls.append(url)
            return wrapped(url) if len(calls)==1 else envelope([rate(self.times[3])])
        c=fake_client(overlap)
        rows,status=funding_scan(c,self.p,limit=2)
        self.assertFalse(status['scan_complete'])
        self.assertEqual(len(rows),2)
        self.assertEqual(len(c.bodies),1)
        self.assertEqual(status['reason'],'FUNDING_RESPONSE_OUTSIDE_EXPLICIT_PAGE')

    def test_empty_response_is_unknown_coverage_not_no_settlements(self):
        rows,status=funding_scan(fake_client(lambda _:envelope([])),self.p)
        self.assertTrue(status['scan_complete'])
        d=calendar_diagnostics([],self.p,True,False)
        self.assertIsNone(d['missing_settlement_count'])
        self.assertEqual(d['coverage_verdict'],'NO_SETTLEMENT_COVERAGE_ESTABLISHED')

    def test_independent_disjoint_requery_matches_and_detects_omission(self):
        records=funding_rows([rate(t) for t in self.times],self.p)[0]
        c=fake_client(self.transport([rate(t) for t in self.times]))
        self.assertTrue(verify_disjoint_windows(c,self.p,records)['matches'])
        c=fake_client(self.transport([rate(t) for t in self.times[1:]]))
        self.assertFalse(verify_disjoint_windows(c,self.p,records)['matches'])

    def test_timeout_bounded_retries_and_request_budget(self):
        c=fake_client(lambda _:(_ for _ in ()).throw(socket.timeout()))
        rows,status=funding_scan(c,self.p)
        self.assertFalse(status['scan_complete'])
        self.assertEqual(len(c.calls),3)
        c=fake_client(lambda _:(_ for _ in ()).throw(socket.timeout()),max_requests=1)
        _,status=funding_scan(c,self.p)
        self.assertEqual(len(c.calls),1)
        self.assertEqual(status['reason'],'GLOBAL_REQUEST_BUDGET_EXHAUSTED')

    def test_403_is_terminal_and_shared_circuit_prevents_another_year_request(self):
        transport=unittest.mock.Mock(side_effect=urllib.error.HTTPError('https://api.bybit.com',403,'Forbidden',{},io.BytesIO(b'Forbidden')))
        c=fake_client(transport)
        _,status=funding_scan(c,self.p)
        self.assertEqual(status['reason'],'HTTP_403_PUBLIC_ACCESS_FORBIDDEN_NO_BYPASS')
        _,status=funding_scan(c,Period.annual(2024))
        self.assertEqual(status['reason'],'HTTP_403_CIRCUIT_OPEN_NO_BYPASS')
        self.assertEqual(transport.call_count,1)
        self.assertEqual(c.calls[0]['response_sha256'],sha256(b'Forbidden'))
        self.assertEqual(c.bodies,{})

    def test_retry_429_then_success(self):
        values=[urllib.error.HTTPError('https://api.bybit.com',429,'Rate limited',{},None),envelope([])]
        def transport(_):
            result=values.pop(0)
            if isinstance(result,Exception): raise result
            return result
        c=fake_client(transport)
        _,status=funding_scan(c,self.p)
        self.assertTrue(status['scan_complete'])
        self.assertEqual(len(c.calls),2)

    def test_nonzero_api_schema_wrong_symbol_and_oversize_pages_rejected(self):
        cases=[envelope([],code=10001),b'not-json',canonical({'retCode':0,'result':{'category':'inverse','list':[]}}),envelope([dict(rate(self.times[0]),symbol='ETHUSDT')]),envelope([rate(t) for t in self.times])]
        for body in cases:
            with self.subTest(case=cases.index(body)):
                c=fake_client(lambda _:body)
                _,status=funding_scan(c,self.p,limit=2)
                self.assertFalse(status['scan_complete'])
                self.assertEqual(len(c.calls),1)
                self.assertEqual(c.bodies,{})

    def test_redirect_refused(self):
        with self.assertRaises(AcquisitionError):
            NoRedirect().redirect_request(None,None,302,'',{},'https://example.invalid')

    def test_partial_results_kept_on_later_network_error(self):
        wrapped=self.transport([rate(t) for t in self.times])
        count=[]
        def transport(url):
            count.append(1)
            if len(count)>1: raise socket.timeout()
            return wrapped(url)
        rows,status=funding_scan(fake_client(transport),self.p,limit=2)
        self.assertEqual(len(rows),2)
        self.assertFalse(status['scan_complete'])


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.p=Period.annual(2023)
        self.t=self.p.start+8*3600000

    def test_duplicates_equivalent_rates_and_conflicts_quarantined(self):
        a,q=funding_rows([rate(self.t),rate(self.t,'0.000100')],self.p)
        self.assertEqual(len(a),1)
        self.assertEqual(q['identical_duplicates'],1)
        a,q=funding_rows([rate(self.t),rate(self.t,'-0.0001')],self.p)
        self.assertEqual(a,[])
        self.assertEqual(q['conflicting_settlements_ms'],[self.t])

    def test_invalid_rate_not_hidden_by_valid_duplicate_no_zero_substitution(self):
        for value in ('NaN','Infinity','bad',None):
            a,q=funding_rows([rate(self.t,value),rate(self.t)],self.p)
            self.assertEqual(a,[])
            self.assertTrue(q['invalid_records'])
            self.assertGreaterEqual(q['identical_duplicates'],0)
        a,_=funding_rows([rate(self.t,'0')],self.p)
        self.assertEqual(a[0]['funding_rate'],'0')

    def test_canonical_hash_independent_of_order_and_decimal_format(self):
        one=funding_rows([rate(self.t,'0.00010'),rate(self.t+8*3600000,'-0.000200')],self.p)[0]
        two=funding_rows([rate(self.t+8*3600000,'-.0002'),rate(self.t,'.0001')],self.p)[0]
        self.assertEqual(sha256(canonical(one)),sha256(canonical(two)))

    def test_historical_gaps_and_interval_changes_remain_unproven(self):
        h=3600000
        times=[self.t,self.t+8*h,self.t+24*h,self.t+32*h,self.t+36*h]
        rates=funding_rows([rate(t) for t in times],self.p)[0]
        d=calendar_diagnostics(rates,self.p,True,True)
        self.assertEqual(d['modal_observed_interval_ms'],8*h)
        self.assertEqual(d['suspected_internal_missing_ms'],[self.t+16*h])
        self.assertIsNone(d['missing_settlement_count'])
        self.assertIn('UNVERIFIED',d['historical_calendar_status'])

    def test_regular_historical_rows_not_current_metadata_calendar_proof(self):
        rows=funding_rows([rate(self.t+i*8*3600000) for i in range(10)],self.p)[0]
        d=calendar_diagnostics(rows,self.p,True,True)
        self.assertEqual(d['suspected_internal_missing_ms'],[])
        self.assertIsNone(d['missing_settlement_count'])
        self.assertIn('NOT_CURRENT_INSTRUMENT_METADATA',d['schedule_basis'])

    def test_proxy_uses_exact_previous_minute_close_retains_low_high(self):
        marks,q=mark_rows([minute(self.t)],[self.t],self.p,self.t)
        self.assertEqual(q['valid_linked_minutes'],1)
        m=marks[0]
        self.assertEqual(m['minute_end_ms'],self.t)
        self.assertEqual(m['settlement_price_proxy'],'101')
        self.assertEqual((m['low_sensitivity'],m['high_sensitivity']),('98','102'))
        self.assertEqual(m['proxy_classification'],'APPROXIMATE_MARK_PREVIOUS_1M_CLOSE')
        self.assertFalse(m['exact_tick'])
        self.assertFalse(m['guaranteed_settlement_bounds'])

    def test_invalid_nonpositive_nonfinite_geometry_incomplete_mark(self):
        for field,value in ((1,'0'),(2,'97'),(3,'103'),(4,'NaN'),(4,'Infinity'),(4,'-1')):
            row=minute(self.t)
            row[field]=value
            marks,q=mark_rows([row],[self.t],self.p,self.t)
            self.assertEqual(marks,[])
            self.assertEqual(len(q['missing_minutes']),1)
        marks,q=mark_rows([minute(self.t)],[self.t],self.p,self.t-1)
        self.assertEqual(marks,[])
        self.assertEqual(q['invalid_minutes'][0]['reason'],'INCOMPLETE_MARK_MINUTE')

    def test_mark_duplicates_and_conflicts_no_forward_fill(self):
        good=minute(self.t)
        marks,q=mark_rows([good,good],[self.t,self.t+8*3600000],self.p,self.p.end)
        self.assertEqual((len(marks),q['duplicate_rows'],len(q['missing_minutes'])),(1,1,1))
        bad=list(good)
        bad[4]='100'
        marks,q=mark_rows([good,bad],[self.t],self.p,self.p.end)
        self.assertEqual(marks,[])
        self.assertEqual(q['conflicting_minutes_ms'],[self.t-MINUTE])

    def test_missing_boundary_minute_explicitly_unavailable(self):
        marks,q=mark_rows([],[self.p.start],self.p,self.p.end)
        self.assertEqual(marks,[])
        self.assertEqual(q['requestable_minutes'],0)
        self.assertEqual(q['unavailable_minutes'][0]['reason'],'PRE_DEVELOPMENT_MARK_MINUTE_NOT_AUTHORIZED')

    def test_non_15m_and_non_minute_alignment_are_not_repaired(self):
        self.assertEqual(classify_settlement(self.t+MINUTE,self.p)['alignment'],'FUNDING_ALIGNMENT_UNRESOLVED')
        _,q=mark_rows([],[self.t+1],self.p,self.p.end)
        self.assertEqual(q['unavailable_minutes'][0]['reason'],'SETTLEMENT_NOT_MINUTE_ALIGNED')

    def test_event_phases_prior_exit_open_tie_new_entry_and_partition_end(self):
        c=classify_settlement(self.p.start,self.p)
        self.assertEqual(c['partition_start_carried_exposure'],'NONE_ANNUAL_RESET')
        self.assertEqual(classify_fill_event(self.t,'PRIOR_BAR','EXIT',self.t,self.p)['classification'],'BEFORE_FUNDING')
        self.assertEqual(classify_fill_event(self.t,'OPEN','ENTRY',self.t,self.p)['same_open_entry'],'EXEMPT')
        self.assertEqual(classify_fill_event(self.t,'OPEN','EXIT',self.t,self.p)['classification'],'FUNDING_TIE')
        self.assertEqual(classify_fill_event(self.t+MINUTE,'OPEN','EXIT',self.t+MINUTE,self.p)['ordering'],'NOT_INFERRED')
        with self.assertRaises(AccessDenied):
            classify_settlement(self.p.end,self.p)
        with self.assertRaises(ValueError):
            classify_fill_event(self.t,'SIGNAL_CLOSE','ENTRY',self.t,self.p)

    def test_batching_only_consecutive_required_minutes(self):
        batches=mark_batches([self.t,self.t+MINUTE,self.t+8*3600000,self.p.start],self.p)
        self.assertEqual(batches,[[self.t-MINUTE,self.t],[self.t+8*3600000-MINUTE]])
        def transport(url):
            path,params=query(url)
            rows=[[str(t),'100','102','98','101'] for t in range(int(params['start']),int(params['end'])+1,MINUTE)]
            return envelope(list(reversed(rows)),path)
        c=fake_client(transport)
        rows,errors=fetch_marks(c,self.p,[self.t,self.t+MINUTE,self.t+8*3600000],workers=2)
        self.assertFalse(errors)
        self.assertEqual(len(rows),3)
        self.assertEqual(len(c.calls),2)


class CacheAndRunnerTests(unittest.TestCase):
    def setUp(self):
        self.p=Period.annual(2023)
        self.t=self.p.start+8*3600000
        self.rates=funding_rows([rate(self.t)],self.p)[0]
        self.marks=mark_rows([minute(self.t)],[self.t],self.p,self.p.end)[0]
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory=Path(self.tmp.name).resolve()/'2023'

    def save(self,**changes):
        args=dict(directory=self.directory,period=self.p,rates=self.rates,marks=self.marks,calls=[],bodies={},quality={'year':2023},source_proof={'fixture':'SYNTHETIC'},synthetic=True)
        args.update(changes)
        return save_snapshot(**args)

    def test_cache_round_trip_and_immutable_outputs(self):
        manifest=self.save()
        rates,marks,repeated=read_snapshot(self.directory,self.p,allow_synthetic=True)
        self.assertEqual((rates,marks,repeated),(self.rates,self.marks,manifest))
        with self.assertRaises(FileExistsError): self.save()
        with self.assertRaises(AccessDenied): read_snapshot(self.directory,self.p)

    def test_hash_corruption_detected(self):
        self.save()
        (self.directory/'marks.json').write_bytes(b'[]\n')
        with self.assertRaises(ValueError): read_snapshot(self.directory,self.p,allow_synthetic=True)

    def test_forged_cache_year_rejected_before_price_file_read(self):
        self.save()
        manifest_path=self.directory/'manifest.json'
        m=json.loads(manifest_path.read_text())
        m['period']=Period.annual(2024).public()
        manifest_path.write_bytes(canonical(m))
        with patch.object(Path,'read_bytes',side_effect=AssertionError('PRICE_FILE_MUST_NOT_BE_READ')):
            with self.assertRaises(AccessDenied): read_snapshot(self.directory,self.p,allow_synthetic=True)

    def test_future_cached_request_metadata_denied_before_price_file(self):
        self.save()
        manifest_path=self.directory/'manifest.json'
        m=json.loads(manifest_path.read_text())
        requests=canonical([{'period':self.p.public(),'path':FUNDING,'params':{'category':'linear','symbol':'BTCUSDT','limit':200,'startTime':self.p.start,'endTime':self.p.end}}])
        (self.directory/'requests.json').write_bytes(requests)
        m['files_sha256']['requests.json']=sha256(requests)
        manifest_path.write_bytes(canonical(m))
        original=Path.read_bytes
        def read(path):
            if path.name!='requests.json': raise AssertionError('PRICE_FILE_MUST_NOT_BE_READ')
            return original(path)
        with patch.object(Path,'read_bytes',read),self.assertRaises(AccessDenied):
            read_snapshot(self.directory,self.p,allow_synthetic=True)

    def test_cache_traversal_symlink_data_and_symlink_manifest_denied(self):
        self.save()
        path=self.directory/'manifest.json'
        m=json.loads(path.read_text())
        m['files_sha256']['../outside.json']='0'*64
        path.write_bytes(canonical(m))
        with self.assertRaises(AccessDenied): read_snapshot(self.directory,self.p,allow_synthetic=True)
        path.unlink()
        external=Path(self.tmp.name)/'external.json'
        external.write_bytes(canonical(m))
        path.symlink_to(external)
        with self.assertRaises(AccessDenied): read_snapshot(self.directory,self.p,allow_synthetic=True)

    def test_unauthorized_exports_rejected_before_creating_paths(self):
        bad=dict(self.rates[0],settlement_ms=self.p.end)
        with self.assertRaises(AccessDenied): self.save(rates=[bad])
        self.assertFalse(self.directory.exists())
        with self.assertRaises(AccessDenied): self.save(quality={'year':2025})
        self.assertFalse(self.directory.exists())

    def test_no_synthetic_cache_labeled_real_or_wrong_proxy_accepted(self):
        wrong=dict(self.marks[0],proxy_classification='EXACT_SETTLEMENT_MARK')
        with self.assertRaises(ValueError): self.save(marks=[wrong])
        self.assertFalse(self.directory.exists())

    def test_no_raw_response_export_without_authorized_provenance(self):
        with self.assertRaises(AccessDenied): self.save(bodies={1:envelope([rate(self.t)])})
        self.assertFalse(self.directory.exists())

    def test_full_synthetic_acquisition_stays_partial_without_calendar_proof(self):
        def transport(url):
            path,params=query(url)
            if path==MARK:
                return envelope([minute(int(params['start'])+MINUTE)],MARK)
            return envelope([rate(self.t)] if int(params['startTime'])<=self.t<=int(params['endTime']) else [])
        c=fake_client(transport)
        rates,marks,q,classification=year_acquisition(c,self.p)
        self.assertEqual((len(rates),len(marks)),(1,1))
        self.assertEqual(q['status'],'PARTIAL_DATA')
        self.assertIn('HISTORICAL_SETTLEMENT_CALENDAR_NOT_INDEPENDENTLY_ESTABLISHED',q['blockers'])
        self.assertFalse(q['funding_zero_substitution'])
        self.assertNotIn('research.engine',__import__('sys').modules)

    def test_unavailable_acquisition_has_honest_blocked_empty_snapshot(self):
        c=fake_client(lambda _:(_ for _ in ()).throw(urllib.error.HTTPError('https://api.bybit.com',403,'Forbidden',{},None)))
        rates,marks,q,_=year_acquisition(c,self.p)
        self.assertEqual((rates,marks),([],[]))
        self.assertEqual(q['status'],'BLOCKED')
        self.assertEqual(q['marks']['acquisition_status'],'NOT_ATTEMPTED_NO_OBSERVED_REQUESTABLE_SETTLEMENTS')
        self.save(rates=[],marks=[],calls=c.calls,bodies=c.bodies,quality=q)
        _,_,manifest=read_snapshot(self.directory,self.p,allow_synthetic=True)
        self.assertEqual(manifest['quality']['status'],'BLOCKED')


if __name__=='__main__':
    unittest.main()
