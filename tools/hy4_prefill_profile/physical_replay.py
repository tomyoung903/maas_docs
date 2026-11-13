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

def derive_moe_range(summary,payload):
    """App-range bytes/time never become an original-event or kernel MBU."""
    public_safe(summary)
    require(summary['schema_version']=='hy4-isolated-moe-range-counters-v1' and summary['status']=='measured_isolated_app_range','unsupported MoE range scope')
    require(summary['comparison_source_input_sha256']==payload['full_report_input_sha256'],'MoE comparison source mismatch')
    require(summary['geometry']=={k:payload['selection'][k] for k in ('layer','new_tokens','context_before','context_after')},'MoE comparison geometry mismatch')
    require(summary['capture']['input_tokens']==100000 and summary['capture']['cached_tokens']==0,'MoE capture is not cold100k')
    require(summary['hardware']['physical_gpu_index']==4,'unexpected MoE replay GPU')
    c=summary['collection'];t=summary['timing'];n=summary['numerical'];b=summary['counters']
    require(c['replay_mode']=='app-range' and c['range']=='HY4_MOE_NATIVE_COUNTER','MoE range identity changed')
    require((c['preparation_calls'],c['profiled_calls'],c['profiling_passes'],c['profiler_warmup_passes'])==(1,1,1,0),'MoE collection sequence changed')
    require(c['observers_restored_before_range'] is True and c['pdl_preserved'] is True,'MoE native call scope changed')
    require(c['cache_control']==c['clock_control']=='none' and c['initial_cache_state']=='uncontrolled','MoE cache/clock conditions changed')
    require(t['metric']=='gpu__time_duration_measured_wallclock.sum' and t['deprecation_warning_at_measured_callsite'] is True,'MoE duration scope changed')
    number(t['range_wallclock_ns'],'MoE range wall clock',integer=True,positive=True)
    for key,value in b.items():number(value,key,integer=True)
    require(b['dram_total_bytes']==b['dram_read_bytes']+b['dram_write_bytes'],'MoE DRAM bytes do not reconcile')
    require(b['l2_sector_bytes']==32 and b['l2_requested_sector_bytes']==b['l2_sectors']*32,'MoE L2 requested sectors do not reconcile')
    require(n['calls']==2 and n['values_per_call']==50331648 and n['bit_mismatches_per_call']==n['nonfinite_per_call']==[0,0] and n['repeat_bit_mismatches']==0 and n['route_ids_and_weights_unchanged'] is True,'MoE complete baseline qualification failed')
    require(n['fp64_candidate_validation'] is False,'baseline is not candidate validation')
    for key in ('per_fc_attribution','cache_hit_ratio','physical_kernel_mbu_percent','unprofiled_latency_ms','candidate_speedup'):
        require(summary[key] is None,'unsupported MoE inference: '+key)
    out=copy.deepcopy(summary)
    out['range_wallclock_ms']=t['range_wallclock_ns']/1e6
    out['profiled_range_bandwidth_tb_s']=b['dram_total_bytes']/(t['range_wallclock_ns']/1e9)/1e12
    return out

def load_moe_range(payload):
    selection=payload['selection'];name=selection.get('moe_range_replay_file')
    if name is None:return None
    require(name=='isolated-moe-range-counters.json','unsupported MoE summary file')
    raw=(HERE/name).read_bytes();sha=hashlib.sha256(raw).hexdigest()
    require(sha==selection.get('moe_range_replay_sha256'),'MoE summary checksum mismatch')
    out=derive_moe_range(json.loads(raw),payload);out['summary_source_sha256']=sha
    return out
