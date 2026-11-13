import copy
import json
import unittest
from build import compile_report
from enrich_nccl import enrich
from test_profile import fixture


def pair():
    source=fixture()
    source['artifacts'] += [dict(id='parser-sidecar',label='Test sidecar',sha256='b'*64),dict(id='trace-sqlite',label='Test SQLite',sha256='c'*64)]
    source['timeline']=dict(clock_alignment='single_host_nsight_common_origin',origin_ns=123,artifact_id='test',clock_evidence='Synthetic unit-test clock',chunks=[])
    records=[]
    for event,direction in zip(source['events'][:2],['send','recv']):
        event.update(owner_id=None,kind='kernel',category='unclassified')
        records.append(dict(event_id=event['id'],rank=event['rank'],start_ns=event['start_ns'],duration_ns=event['duration_ns'],direction=direction,sidecar_forward_ordinal=None,forward_nvtx_row_id=None,peer_rank=None,communicator_id=None,message_bytes=None,private_field='/home/not-for-publication'))
    audit=dict(status='PASS_RETAINED_NCCL_DIRECTION_CENSUS_FORWARD_PEER_BYTES_UNRESOLVED',provenance=dict(sidecar_sha256='b'*64,sqlite_sha256='c'*64,trace_origin_ns=123),records=records,kernel_count=2,directions=dict(send=1,recv=1),direct_forward_enclosures=0,nonnull_operation_payload_count=0)
    return source,audit


class NcclEnrichmentTests(unittest.TestCase):
    def test_identity_does_not_become_ownership_or_work(self):
        source,audit=pair();before=copy.deepcopy(source)
        result=enrich(source,audit,'d'*64,'e'*64)
        self.assertEqual(source,before)
        self.assertEqual(compile_report(result)['derived'],compile_report(source)['derived'])
        for old,new in zip(source['events'],result['events']):
            self.assertTrue(all(new[k]==v for k,v in old.items() if k!='category'))
        self.assertEqual([e['communication_direction'] for e in result['events'][:2]],['send','recv'])
        self.assertTrue(all(e['owner_id'] is None and e['category']=='communication' for e in result['events'][:2]))
        self.assertNotIn('/home/not-for-publication',json.dumps(result))
        self.assertEqual(enrich(result,audit,'d'*64,'e'*64),result)

    def test_wrong_source_or_interval_is_rejected(self):
        for mutate in [lambda a:a['provenance'].update(sidecar_sha256='f'*64),lambda a:a['records'][0].update(duration_ns=1),lambda a:a['records'][0].update(event_id='missing'),lambda a:a['records'][0].update(peer_rank=1)]:
            source,audit=pair();mutate(audit)
            with self.assertRaises(ValueError):enrich(source,audit,'d'*64,'e'*64)

    def test_owned_event_is_not_reclassified_by_this_contract(self):
        source,audit=pair();source['events'][0]['owner_id']='r0o'
        with self.assertRaises(ValueError):enrich(source,audit,'d'*64,'e'*64)


if __name__=='__main__':unittest.main()
