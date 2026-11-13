import copy,json,unittest
from pathlib import Path
from import_trace import convert,digest
from build import compile_report

S='a'*64

def sidecar():
    return {'schema_version':'hy4-100k-trace-sidecar-v1','status':'EXTRACTED_WITH_UNRESOLVED_COVERAGE','artifacts':[{'id':'trace-sqlite','label':'/home/private/raw.sqlite','path':'/home/private/raw.sqlite','sha256':'b'*64}], 'request':{'input_tokens':100000,'output_tokens':1,'cached_tokens':0,'wall_time_ms':20,'layer_partition':[16,21,21,20],'controller_result_sha256':None},'trace':{'origin_ns':10000,'sqlite_sha256':'b'*64},'chunk_schedule':[], 'forwards':[{'rank':r,'forward_ordinal':0,'id':f'rank{r}-forward0','new_tokens':None,'context_before':None,'context_after':None} for r in range(4)], 'events':[{'id':f'kernel-{r}','rank':r,'start_ns':0,'duration_ns':1000000,'kind':'kernel','name':'PRIVATE_RAW_KERNEL_123','forward_ordinal':0,'global_target_layer':layer,'region':'target_layer','family':'q_projection','ownership_method':'same_thread_runtime_process_correlation_then_source_order','artifact_id':'trace-sqlite'} for r,layer in enumerate([0,16,37,58])],'coverage':{'complete':False},'limitations':['/home/private/trace note']}

class ImportTraceTests(unittest.TestCase):
    def test_extracted_timing_never_becomes_work_join(self):
        out=convert(sidecar(),S);self.assertTrue(all(not n['work_matches_events'] for n in out['nodes']));self.assertFalse(out['request']['execution_coverage_complete']);self.assertEqual(compile_report(out)['derived']['all_events_residency_ms'],4);self.assertNotIn('/home/private',json.dumps(out));self.assertNotIn('PRIVATE_RAW_KERNEL_123',json.dumps(out))
    def test_unknown_preserved_not_forced_into_layer(self):
        raw=sidecar();raw['events'][0].update(ownership_method='unresolved',forward_ordinal=None,global_target_layer=None,region='unknown')
        out=convert(raw,S);self.assertIsNone(out['events'][0]['owner_id']);r=compile_report(out);self.assertEqual(r['derived']['unattributed_by_rank']['0']['event_count'],1);self.assertEqual(r['derived']['all_events_residency_ms'],4)
    def test_geometry_only_from_observed_schedule(self):
        raw=sidecar();out=convert(raw,S);self.assertTrue(any('geometry unresolved' in n['label'] for n in out['nodes']))
        raw['chunk_schedule']=[{'rank':0,'forward_ordinal':0,'new_tokens':8192,'context_before':0,'context_after':8192}];out=convert(raw,S);self.assertFalse(any('8,192 new tokens' in n['label'] for n in out['nodes']));raw['forwards'][0].update(new_tokens=8192,context_before=0,context_after=8192,context_method='single_cold_request_fifo_cumulative_log_tokens');out=convert(raw,S);self.assertTrue(any('8,192 new tokens' in n['label'] for n in out['nodes']))
    def test_wrong_request_receipt_rejected(self):
        with self.assertRaises(ValueError):convert(sidecar(),S,request_receipt={'sidecar_sha256':'c'*64},request_sha='d'*64)
    def test_event_set_bound_work_review(self):
        raw=sidecar();out=convert(raw,S);owner=out['events'][0]['owner_id'];n=next(n for n in out['nodes'] if n['id']==owner);work=copy.deepcopy(n['work']);work.update(status='verified',flops_by_precision={'bf16':2048})
        bindings={'schema_version':'hy4-reviewed-work-bindings-v1','sidecar_sha256':S,'artifacts':[],'bindings':[{'node_id':owner,'event_ids_sha256':digest(['kernel-0']),'reviewed_complete_operator_scope':True,'work':work,'artifact_ids':[]}]}
        out=convert(raw,S,work_bindings=bindings,bindings_sha='d'*64);self.assertEqual(sum(n['work_matches_events'] for n in out['nodes']),1)
        bindings['bindings'][0]['event_ids_sha256']='e'*64
        with self.assertRaises(ValueError):convert(raw,S,work_bindings=bindings,bindings_sha='d'*64)
    def test_roof_selection_requires_hardware_review(self):
        roof=json.loads(Path(__file__).with_name('nominal-b300-roofs.json').read_text())
        with self.assertRaises(ValueError):convert(sidecar(),S,nominal_roofs=roof)
        hardware={'sidecar_sha256':S,'rank_ids':[0,1,2,3],'device_name':'NVIDIA B300-SXM6-AC','nominal_preset_reviewed':True}
        out=convert(sidecar(),S,nominal_roofs=roof,hardware_receipt=hardware,hardware_sha='f'*64);self.assertEqual(out['hardware']['bandwidth_roof_tb_s'],7.7)
    def test_activity_kind_is_retained(self):
        raw=sidecar();raw['events'][0]['kind']='memcpy';out=convert(raw,S);r=compile_report(out);self.assertEqual(r['derived']['nodes']['model']['event_kind_counts']['memcpy'],1)
    def test_adapter_retains_single_host_origin_and_rank_offsets(self):
        raw=sidecar();raw['trace'].update(clock_alignment='single_host_nsight_common_origin',origin_ns=1234)
        for i,e in enumerate(raw['events']):e['start_ns']=i*2000000
        for i,f in enumerate(raw['forwards']):f.update(start_ns=i*2000000,duration_ns=1000000)
        out=convert(raw,S);self.assertEqual(out['timeline']['origin_ns'],1234);self.assertEqual([e['start_ns'] for e in out['events']],[0,2000000,4000000,6000000]);self.assertEqual(len(out['timeline']['chunks']),4)
        self.assertTrue(compile_report(out)['derived']['timeline']['available'])
    def test_no_cold_receipt_no_measured_page(self):
        raw=sidecar();raw['request']['cached_tokens']=None
        with self.assertRaises(ValueError):convert(raw,S)
    def test_warmup_and_profiled_intervals_remain_separate(self):
        raw=sidecar();receipt={**raw['request'],'sidecar_sha256':S,'profiled_server_prefill_ms':18,'warmup_server_prefill_ms':30}
        out=convert(raw,S,request_receipt=receipt,request_sha='d'*64)
        self.assertEqual(out['request']['wall_time_ms'],20)
        self.assertEqual(out['request']['profiled_server_prefill_ms'],18)
        self.assertEqual(out['request']['warmup_server_prefill_ms'],30)
        self.assertEqual(out['request']['timing_artifact_ids'],['request-receipt'])
        self.assertEqual(len(out['events']),4)
        raw['request']['profiled_server_prefill_ms']=17
        with self.assertRaises(ValueError):convert(raw,S,request_receipt=receipt,request_sha='d'*64)

if __name__=='__main__':unittest.main()
