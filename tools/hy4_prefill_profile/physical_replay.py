"""Keep isolated replay counters separate from every original event/work metric."""
import copy
import hashlib
import json
from pathlib import Path
from build import number,public_safe,require

HERE=Path(__file__).resolve().parent

def derive(summary,payload,nominal_bandwidth):
    public_safe(summary)
    require(summary['schema_version']=='hy4-isolated-native-counters-v1' and summary['status']=='measured_isolated_replay','unsupported counter scope')
    require(summary['source_input_sha256']==payload['full_report_input_sha256'],'counter view source binding mismatch')
    s=payload['selection']
    require(summary['selected_event_ids_sha256']==s['event_ids_sha256'],'counter view event binding mismatch')
    require(summary['geometry']=={k:s[k] for k in ('layer','new_tokens','context_before','context_after')},'counter geometry mismatch')
    require(summary['hardware']['physical_gpu_index']==4,'unexpected isolated replay GPU')
    require(summary['hardware']['nominal_bandwidth_roof_tb_s']==nominal_bandwidth,'counter and page nominal bandwidth differ')
    number(nominal_bandwidth,'nominal bandwidth',positive=True)
    c=summary['collection']
    require((c['baseline_chains'],c['profiled_chains'],c['extra_warmups'])==(1,1,0),'replay sequence changed')
    require(c['cache_control']=='none' and c['clock_control']=='none' and c['initial_cache_state']=='uncontrolled','counter cache/clock scope changed')
    require(c['intermediate_host_copy'] is False and c['intermediate_synchronization'] is False,'native chain was interrupted')
    require([r['family'] for r in summary['rows']]==['indexer_fp8_mqa_logits','indexer_topk'],'counter kernel set/order changed')
    out=copy.deepcopy(summary)
    for r in out['rows']:
        evidence=payload['event_evidence'].get(r['original_event_id'])
        require(evidence and r['kernel_name']==evidence['kernel_name'] and r['kernel_symbol_sha256']==evidence['kernel_symbol_sha256'],'counter native symbol mismatch')
        require(hashlib.sha256(r['kernel_name'].encode()).hexdigest()==r['kernel_symbol_sha256'],'counter symbol checksum mismatch')
        require(r['profiling_passes']==1 and r['ncu_warmup_passes']==0,'counter collection was not one pass')
        for name in ('read_bytes','write_bytes','profiled_duration_ns'):number(r[name],name,integer=True,positive=name=='profiled_duration_ns')
        r['total_bytes']=r['read_bytes']+r['write_bytes']
        r['profiled_duration_ms']=r['profiled_duration_ns']/1e6
        r['matched_bandwidth_tb_s']=r['total_bytes']/(r['profiled_duration_ns']/1e9)/1e12
        r['matched_physical_mbu_percent']=100*r['matched_bandwidth_tb_s']/nominal_bandwidth
    return out

def load_replay(payload,nominal_bandwidth):
    selection=payload['selection'];name=selection.get('physical_replay_file')
    if name is None:return None
    require(name=='isolated-replay-counters.json','unsupported counter summary file')
    raw=(HERE/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    require(sha==selection.get('physical_replay_sha256'),'counter summary checksum mismatch')
    out=derive(json.loads(raw),payload,nominal_bandwidth);out['summary_source_sha256']=sha
    return out
