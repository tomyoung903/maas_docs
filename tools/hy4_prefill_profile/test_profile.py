"""Synthetic CPU tests for ownership, denominator and publication invariants."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import build


def fixture():
    artifact={'id':'test','label':'Synthetic unit-test evidence only','sha256':'a'*64}
    empty={'status':'unavailable','flops_by_precision':None,'scalar_ops':None,'useful_bytes':None,'useful_bytes_note':'','dram_bytes':None,'dram_counter_artifact_id':None}
    def n(id,parent,kind,rank=None,layer=None):
        return {'id':id,'parent_id':parent,'kind':kind,'label':id,'rank':rank,'chunk':0 if kind not in {'model','rank'} else None,'layer':layer,'work':copy.deepcopy(empty),'work_matches_events':False,'artifact_ids':['test']}
    nodes=[n('model',None,'model')];events=[]
    for rank,layer in enumerate([0,16,37,58]):
        r=f'r{rank}';nodes.extend([n(r,'model','rank',rank),n(r+'c',r,'chunk',rank),n(r+'l',r+'c','layer',rank,layer),n(r+'o',r+'l','operator',rank,layer)])
        op=nodes[-1];op['work'].update(status='verified',flops_by_precision={'bf16':2_000_000_000},useful_bytes=1_000_000,useful_bytes_note='Synthetic one-interface test');op['work_matches_events']=True
        events.append({'id':r+'e','rank':rank,'start_ns':0,'duration_ns':2_000_000,'owner_id':r+'o','artifact_id':'test'})
    return {'schema_version':build.SCHEMA,'status':'measured','request':{'input_tokens':100000,'output_tokens':1,'cached_tokens':0,'wall_time_ms':10,'layer_partition':[16,21,21,20],'configuration':'synthetic test','execution_coverage_complete':True,'coverage_artifact_ids':['test']},'hardware':{'devices':[0,1,2,3],'compute_roofs_tflops':{'bf16':2},'bandwidth_roof_tb_s':1,'roof_artifact_ids':['test']},'artifacts':[artifact],'nodes':nodes,'events':events,'limitations':['Synthetic CPU unit-test fixture; never a measurement.']}


class ProfileTests(unittest.TestCase):
    def test_default_regeneration_preserves_current_source(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            with patch.object(build,'ROOT',root):
                self.assertEqual(build.default_input(),build.HERE/'pending-input.json')
                current=root/'docs/hy4-100k-prefill/source-data.json';current.parent.mkdir(parents=True);current.write_text('{}')
                self.assertEqual(build.default_input(),current)
    def test_disjoint_gpu_clock_domains_and_named_denominators(self):
        r=build.compile_report(fixture());m=r['derived']['nodes']['model']
        self.assertEqual(m['summed_residency_ms'],8);self.assertEqual(m['device_union_sum_ms'],8)
        self.assertEqual(m['mfu_active_union_percent'],50)
        self.assertEqual(r['derived']['request_mfu_percent'],10)
    def test_overlap_and_single_owner(self):
        f=fixture();f['events'].append({'id':'overlap','rank':0,'start_ns':1_000_000,'duration_ns':2_000_000,'owner_id':'r0o','artifact_id':'test'})
        r=build.compile_report(f);m=r['derived']['nodes']['r0o']
        self.assertEqual(m['summed_residency_ms'],4);self.assertEqual(m['device_union_sum_ms'],3);self.assertEqual(m['event_count'],2)
        self.assertEqual(m['overlap_excess_ms'],1)
    def test_unknown_events_not_dropped_from_gpu_summary(self):
        f=fixture();f['events'].append({'id':'unknown','rank':0,'start_ns':10_000_000,'duration_ns':1_000_000,'owner_id':None,'artifact_id':'test'})
        d=build.compile_report(f)['derived'];self.assertEqual(d['total_event_count'],5);self.assertEqual(d['unattributed_event_count'],1);self.assertEqual(d['all_events_residency_ms'],9);self.assertEqual(d['nodes']['model']['summed_residency_ms'],8);self.assertIsNone(d['request_mfu_percent'])
    def test_interface_bytes_are_not_parent_summed(self):
        m=build.compile_report(fixture())['derived']['nodes'];self.assertIsNone(m['model']['useful_bytes']);self.assertIsNone(m['r0']['estimated_mbu_active_union_percent']);self.assertAlmostEqual(m['r0o']['estimated_mbu_active_union_percent'],.05)
    def test_no_dram_counter_fabricated(self):
        m=build.compile_report(fixture())['derived']['nodes'];self.assertIsNone(m['r0o']['counter_mbu_active_union_percent'])
    def test_no_roof_means_no_percentage(self):
        f=fixture();f['hardware']['compute_roofs_tflops']={};f['hardware']['bandwidth_roof_tb_s']=None;m=build.compile_report(f)['derived']['nodes']['r0o'];self.assertIsNone(m['mfu_active_union_percent']);self.assertIsNone(m['estimated_mbu_active_union_percent'])
    def test_mixed_precision_uses_separate_roofs(self):
        f=fixture();f['hardware']['compute_roofs_tflops']['fp8']=4;f['nodes'][4]['work']['flops_by_precision']['fp8']=4_000_000_000;m=build.compile_report(f)['derived']['nodes']['r0o'];self.assertEqual(m['mfu_active_union_percent'],100)
    def test_missing_join_blocks_rate(self):
        f=fixture();f['nodes'][4]['work_matches_events']=False;m=build.compile_report(f)['derived']['nodes']['r0o'];self.assertIsNone(m['mfu_active_union_percent']);self.assertIsNone(m['estimated_mbu_active_union_percent'])
    def test_partial_work_not_silently_zero(self):
        f=fixture();f['nodes'][4]['work']['flops_by_precision']=None;m=build.compile_report(f)['derived']['nodes']['model'];self.assertFalse(m['flop_coverage_complete']);self.assertIsNone(m['mfu_active_union_percent']);self.assertEqual(m['leaves_with_flops'],3)
    def test_pending_retains_null_not_zero(self):
        f=fixture();f['status']='pending';f['events']=[];f['request']['execution_coverage_complete']=False;f['request']['wall_time_ms']=None;f['request']['cached_tokens']=None;m=build.compile_report(f)['derived']['nodes']['model'];self.assertIsNone(m['event_count']);self.assertIsNone(m['summed_residency_ms']);self.assertIsNone(m['mfu_active_union_percent'])
    def test_duplicate_and_wrong_ownership_rejected(self):
        for mutate in [lambda f:f['events'].append(copy.deepcopy(f['events'][0])),lambda f:f['events'][0].update(owner_id='r0'),lambda f:f['events'][0].update(owner_id='r1o')]:
            f=fixture();mutate(f)
            with self.assertRaises(ValueError):build.validate(f)
    def test_cycle_and_partition_rejected(self):
        f=fixture();f['nodes'][1]['parent_id']='r0l'
        with self.assertRaises(ValueError):build.validate(f)
        f=fixture();f['nodes'][3]['layer']=77
        with self.assertRaises(ValueError):build.validate(f)
    def test_bad_numbers_rejected(self):
        for value in [float('nan'),float('inf'),-1,True]:
            f=fixture();f['events'][0]['duration_ns']=value
            with self.assertRaises(ValueError):build.validate(f)
    def test_publication_privacy_guard(self):
        for text in ['/home/tom/secret','http://localhost:8080','https://internal.example/api','192.168.1.7','Bearer abcdef']:
            f=fixture();f['limitations'].append(text)
            with self.assertRaises(ValueError):build.validate(f)
    def test_embedded_json_and_literal_html_safe(self):
        f=fixture();f['nodes'][0]['label']='</script><img src=x onerror=alert(1)>'
        encoded=build.encoded(build.compile_report(f));self.assertNotIn('</script>',encoded);self.assertEqual(json.loads(encoded)['nodes'][0]['label'],f['nodes'][0]['label'])
    def test_partial_capture_blocks_request_proxy(self):
        f=fixture();f['request']['execution_coverage_complete']=False
        self.assertIsNone(build.compile_report(f)['derived']['request_mfu_percent'])
    def test_independent_target_model_fraction_survives_unknown_events(self):
        f=fixture();f['request']['execution_coverage_complete']=False
        f['events'][0]['owner_id']=None
        f['target_model_work']={'flops_by_precision':{'bf16':8_000_000_000},'scope':'Synthetic useful target work, excludes draft.','source_artifact_ids':['test'],'request_artifact_ids':['test'],'request_completed':True,'input_tokens':100000,'output_tokens':1}
        d=build.compile_report(f)['derived']
        self.assertEqual(d['target_model_request_mfu_percent'],10)
        self.assertIsNone(d['request_mfu_percent'])
        f['hardware']['compute_roofs_tflops']={}
        self.assertIsNone(build.compile_report(f)['derived']['target_model_request_mfu_percent'])
        f['target_model_work']['request_completed']=False
        with self.assertRaises(ValueError):build.validate(f)
    def test_empty_branch_rejected(self):
        f=fixture();f['nodes']=[n for n in f['nodes'] if n['id']!='r3o'];f['events']=f['events'][:3]
        with self.assertRaises(ValueError):build.validate(f)
    def test_precomputed_metric_field_rejected(self):
        f=fixture();f['mfu']=50
        with self.assertRaises(ValueError):build.validate(f)
    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):build.load_json('{"x":1,"x":2}')
        with self.assertRaises(ValueError):build.load_json('{"x":NaN}')
    def test_common_clock_timeline_keeps_cross_rank_offsets(self):
        f=fixture();f['request']['wall_time_ms']=40
        for i,e in enumerate(f['events']):e['start_ns']=i*10000000
        f['timeline']={'clock_alignment':'single_host_nsight_common_origin','origin_ns':1234567890123,'artifact_id':'test','clock_evidence':'Synthetic common clock fixture','chunks':[]}
        r=build.compile_report(f)
        self.assertTrue(r['derived']['timeline']['available'])
        self.assertEqual(r['derived']['timeline']['end_ns'],32000000)
        self.assertEqual([e['start_ns'] for e in r['events']],[0,10000000,20000000,30000000])
        self.assertEqual(r['derived']['nodes']['model']['device_union_sum_ms'],8)
    def test_no_clock_evidence_no_shared_timeline(self):
        r=build.compile_report(fixture());self.assertFalse(r['derived']['timeline']['available']);self.assertIsNone(r['derived']['timeline']['start_ns'])
    def test_pending_cannot_claim_common_measured_clock(self):
        f=fixture();f['status']='pending';f['events']=[];f['request'].update(wall_time_ms=None,cached_tokens=None,execution_coverage_complete=False)
        f['timeline']={'clock_alignment':'single_host_nsight_common_origin','origin_ns':1,'artifact_id':'test','clock_evidence':'Fake','chunks':[]}
        with self.assertRaises(ValueError):build.validate(f)
    def test_generated_page_binding(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);s=p/'source.json';s.write_text(json.dumps(fixture()));r=build.build(s,p/'out');h=(p/'out/index.html').read_text();embedded=h.split('<script id="report-data" type="application/json">',1)[1].split('</script>',1)[0];self.assertEqual(json.loads(embedded),r);self.assertEqual(h.count('data-maas-annotator'),1);self.assertIn('aria-expanded',h)

if __name__=='__main__':unittest.main()
