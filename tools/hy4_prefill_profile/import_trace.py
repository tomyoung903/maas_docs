#!/usr/bin/env python3
"""Convert the private reviewed-extractor sidecar to the public report interface.

Raw symbols, annotations, PIDs, hostnames and private paths are never copied.
An extracted owner permits timing attribution, not an automatic work/event join.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
from build import validate, require, load_json, public_safe


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def empty_work():
    return {'status':'unavailable','flops_by_precision':None,'scalar_ops':None,'useful_bytes':None,'useful_bytes_note':'No reviewed work-to-event binding.','dram_bytes':None,'dram_counter_artifact_id':None}


def convert(sidecar, sidecar_sha, *, request_receipt=None, request_sha=None,
            work_bindings=None, bindings_sha=None, coverage_review=None,
            coverage_sha=None, nominal_roofs=None, hardware_receipt=None,
            hardware_sha=None, target_model_work=None, target_work_sha=None):
    require(sidecar.get('schema_version')=='hy4-100k-trace-sidecar-v1','unsupported trace sidecar')
    require(sidecar.get('status') in {'EXTRACTED_WITH_UNRESOLVED_COVERAGE','EXTRACTED_CORRELATED_NOT_INDEPENDENTLY_AUDITED'}, 'sidecar extraction did not finish')
    req=sidecar['request'].copy()
    if request_receipt:
        require(request_receipt.get('sidecar_sha256')==sidecar_sha,'request receipt/sidecar mismatch')
        for k in ['input_tokens','output_tokens','cached_tokens','wall_time_ms','layer_partition']:
            value=request_receipt[k]
            require(req.get(k) is None or req[k]==value,f'request receipt contradicts sidecar {k}')
            req[k]=value
        for k in ['profiled_server_prefill_ms','warmup_server_prefill_ms']:
            if k in request_receipt:
                require(req.get(k) is None or req[k]==request_receipt[k],f'request receipt contradicts sidecar {k}')
                req[k]=request_receipt[k]
    require(req.get('cached_tokens')==0 and req.get('wall_time_ms') is not None,'measured report requires actual zero-cache and wall-time receipt; no extrapolation permitted')
    artifacts=[]
    for i,a in enumerate(sidecar['artifacts']):
        artifacts.append({'id':a['id'],'label':f'Captured trace source {i+1} ({a["id"]})','sha256':a['sha256']})
    def add_art(id,label,sha):
        require(sha is not None,f'{id} hash required');require(not any(a['id']==id for a in artifacts),'reserved artifact ID collision')
        artifacts.append({'id':id,'label':label,'sha256':sha})
    add_art('parser-sidecar','CPU-extracted trace sidecar',sidecar_sha)
    if request_receipt:add_art('request-receipt','Matched cold-request measurement receipt',request_sha)
    hardware={'devices':[0,1,2,3],'compute_roofs_tflops':{},'bandwidth_roof_tb_s':None,'roof_artifact_ids':[]}
    if nominal_roofs:
        require(nominal_roofs.get('schema_version')=='hy4-nominal-roofs-v1','unsupported nominal roof preset')
        require(hardware_receipt is not None,'selecting nominal roofs requires a matched hardware identity receipt')
        require(hardware_receipt.get('sidecar_sha256')==sidecar_sha and hardware_receipt.get('rank_ids')==[0,1,2,3],'hardware receipt does not match sidecar/ranks')
        name=hardware_receipt['device_name'];require('B300' in name and 'GB300' not in name,'preset requires HGX/AWS B300 identity, not GB300')
        require(hardware_receipt.get('nominal_preset_reviewed') is True,'hardware/preset match review required')
        hardware.update(nominal_roofs['hardware']);hardware['device_name']=name
        artifacts+=nominal_roofs['artifacts'];add_art('hardware-receipt','Captured device and nominal-roof match review',hardware_sha)
    nodes=[];index={}
    def node(id,parent,kind,label,rank=None,chunk=None,layer=None,**extra):
        if id in index:return index[id]
        n={'id':id,'parent_id':parent,'kind':kind,'label':label,'rank':rank,'chunk':chunk,'layer':layer,'work':empty_work(),'work_matches_events':False,'artifact_ids':['parser-sidecar'],**extra}
        index[id]=n;nodes.append(n);return n
    node('model',None,'model','HY4 · measured 100K request (attributed subtree)')
    for r in range(4):node(f'pp{r}','model','rank',f'PP{r}',rank=r)
    forwards={(f['rank'],f['forward_ordinal']):f for f in sidecar['forwards']}
    require(len(forwards)==len(sidecar['forwards']),'duplicate forward identity')
    schedule={(f['rank'],f['forward_ordinal']):f for f in sidecar['chunk_schedule']}
    require(len(schedule)==len(sidecar['chunk_schedule']),'duplicate chunk-schedule identity')
    def forward_nodes(rank,ordinal):
        require((rank,ordinal) in forwards,'owned event points to missing forward')
        f=forwards[(rank,ordinal)];actual=schedule.get((rank,ordinal));id=f'pp{rank}-forward{ordinal}'
        if actual and all(f.get(k) is not None for k in ['new_tokens','context_before','context_after']) and f.get('context_method')=='single_cold_request_fifo_cumulative_log_tokens':
            for k in ['new_tokens','context_before','context_after']:
                require(f.get(k) is None or f[k]==actual[k],'forward/schedule geometry mismatch')
            label=f'Forward {ordinal+1} · {actual["new_tokens"]:,} new tokens · context {actual["context_after"]:,}'
            note='Chunk lengths observed in bounded logs; cumulative context uses the single-cold-request FIFO inference.'
        else:
            label=f'Forward {ordinal+1} · chunk geometry unresolved';note='Observed forward interval; no inferred fixed-size chunk geometry.'
        node(id,f'pp{rank}','chunk',label,rank=rank,chunk=ordinal,note=note)
        return id
    events=[]
    for raw in sidecar['events']:
        rank=raw['rank'];ordinal=raw['forward_ordinal'];layer=raw['global_target_layer'];method=raw['ownership_method'];owner=None
        if method!='unresolved' and ordinal is not None:
            require(method in {'same_thread_runtime_process_correlation_then_source_order','same_thread_runtime_process_correlation'},'unreviewed extraction ownership method')
            c=forward_nodes(rank,ordinal)
            if layer is not None:
                require(raw['region']=='target_layer' and method=='same_thread_runtime_process_correlation_then_source_order','layer owner lacks source-order evidence')
                parent=f'{c}-layer{layer}';node(parent,c,'layer',f'Layer {layer}',rank=rank,chunk=ordinal,layer=layer)
            else:
                region=raw['region'];require(region in {'prefix','suffix','auxiliary','unknown'},'unrecognized nonlayer region')
                parent=f'{c}-{region}';node(parent,c,'layer',f'{region.title()} boundary (outside attributed layers)',rank=rank,chunk=ordinal,boundary=True)
            family=raw['family'];require(isinstance(family,str) and re.fullmatch(r'[A-Za-z0-9_ .:+()/\-]{1,120}',family) is not None,'unsafe or noncanonical family label')
            public_safe(family)
            family_key=re.sub('[^a-z0-9]+','-',family.lower()).strip('-')[:48]+'-'+hashlib.sha256(family.encode()).hexdigest()[:8]
            owner=parent+'-'+family_key
            node(owner,parent,'operator',family.replace('_',' '),rank=rank,chunk=ordinal,layer=layer,boundary=layer is None,note='Timing ownership from CPU extraction; arithmetic/byte correspondence is unreviewed until an explicit work binding is attached.')
        category='memory' if raw['kind'] in {'memcpy','memset'} else 'communication' if raw['family'].startswith('nccl_') else 'compute' if owner is not None and raw['family']!='unclassified' else 'unclassified'
        events.append({'id':raw['id'],'rank':rank,'start_ns':raw['start_ns'],'duration_ns':raw['duration_ns'],'owner_id':owner,'artifact_id':raw['artifact_id'],'kind':raw['kind'],'category':category})
    # A rank with no attributed event still exists; this placeholder owns no time.
    for rank in range(4):
        if not any(n['parent_id']==f'pp{rank}' for n in nodes):
            c=f'pp{rank}-unresolved';node(c,f'pp{rank}','chunk','No forward ownership resolved',rank=rank,chunk='unresolved')
            l=c+'-boundary';node(l,c,'layer','Unattributed boundary',rank=rank,chunk='unresolved',boundary=True)
            node(l+'-placeholder',l,'operator','No attributed operations; see unknown coverage',rank=rank,chunk='unresolved',boundary=True)
    if work_bindings:
        require(work_bindings.get('schema_version')=='hy4-reviewed-work-bindings-v1','unsupported work bindings')
        require(work_bindings.get('sidecar_sha256')==sidecar_sha,'work binding/sidecar mismatch')
        add_art('work-binding-review','Reviewed complete operator work-to-event bindings',bindings_sha)
        for a in work_bindings['artifacts']:artifacts.append(a)
        require(len({a['id'] for a in artifacts})==len(artifacts),'duplicate work-binding artifact IDs')
        seen=set()
        event_ids_by_owner={}
        for event in events:
            event_ids_by_owner.setdefault(event['owner_id'],[]).append(event['id'])
        for binding in work_bindings['bindings']:
            id=binding['node_id'];require(id in index and index[id]['kind']=='operator' and id not in seen,'unknown/duplicate work binding target');seen.add(id)
            event_ids=sorted(event_ids_by_owner.get(id,[]))
            require(event_ids and binding['event_ids_sha256']==digest(event_ids),'work binding event-set mismatch')
            require(binding.get('reviewed_complete_operator_scope') is True,'complete fused-operator work review required')
            n=index[id];n['work']=binding['work'];n['work_matches_events']=True
            n['artifact_ids']+=['work-binding-review']+binding['artifact_ids']
            n['note']='Timing and complete operator work scope are linked by an explicit event-set review.'
    complete=False;coverage_ids=[]
    if coverage_review:
        require(coverage_review.get('schema_version')=='hy4-request-coverage-review-v1','unsupported request coverage review')
        require(coverage_review.get('sidecar_sha256')==sidecar_sha,'coverage review/sidecar mismatch')
        require(coverage_review.get('complete') is True,'coverage review is not complete')
        require(not any(e['owner_id'] is None for e in events),'unattributed events prevent complete execution coverage')
        require(coverage_review.get('all_four_ranks_all_request_events') is True,'full request event inclusion review required')
        add_art('request-coverage-review','Independent full-request event coverage review',coverage_sha)
        complete=True;coverage_ids=['request-coverage-review']
    request={k:req[k] for k in ['input_tokens','output_tokens','cached_tokens','wall_time_ms','layer_partition']}
    for key in ['profiled_server_prefill_ms','warmup_server_prefill_ms']:
        if key in req:request[key]=req[key]
    if any(request.get(k) is not None for k in ['profiled_server_prefill_ms','warmup_server_prefill_ms']):
        request['timing_artifact_ids']=['request-receipt'] if request_receipt else ['controller-result']
    request.update(configuration='HY4 cold prefill · PP4 baseline · trace-backed timing',execution_coverage_complete=complete,coverage_artifact_ids=coverage_ids)
    result={'schema_version':'hy4-prefill-profile-v1','status':'measured','request':request,'hardware':hardware,'artifacts':artifacts,'nodes':nodes,'events':events,'limitations':[
        'GPU intervals are measured. Source-order attribution is an extraction result; unresolved events remain in the full-GPU summary.',
        'Observed forward order and bounded log token counts identify chunks only where their explicit join succeeded. Context accumulation uses the stated single-request FIFO inference.',
        'The tree owns each attributed event once. Fused kernels remain complete operators; no duration is copied into multiple semantic leaves.',
        'Model FLOPs and useful bytes are unavailable without an explicit, complete, event-set-bound work review. Timing attribution alone does not qualify their numerators.',
        'Useful-byte MBU is an interface estimate against nominal per-GPU bandwidth. It is not measured HBM traffic; counter MBU remains separate.',
        'Raw symbols, host/process identities, corpus content, annotations and private source paths are excluded from this public pack.',
    ]}
    if target_model_work:
        require(target_model_work.get('schema_version')=='hy4-target-model-work-v1','unsupported target model work receipt')
        require(target_model_work.get('sidecar_sha256')==sidecar_sha,'target work/sidecar mismatch')
        add_art('target-model-work-review','Whole-request useful target-model work review',target_work_sha)
        artifacts.extend(target_model_work['artifacts'])
        result['target_model_work']=target_model_work['work']
    clock=sidecar.get('trace',{})
    alignment=clock.get('clock_alignment','unavailable')
    aligned=alignment=='single_host_nsight_common_origin'
    chunks=[]
    for (rank,ordinal), f in forwards.items():
        id=f'pp{rank}-forward{ordinal}'
        if id in index and f.get('start_ns') is not None and f.get('duration_ns') is not None and f['duration_ns']>0:
            chunks.append({'node_id':id,'rank':rank,'forward_ordinal':ordinal,'start_ns':f['start_ns'],'duration_ns':f['duration_ns'],'new_tokens':f.get('new_tokens') if f.get('context_method')=='single_cold_request_fifo_cumulative_log_tokens' else None})
    result['timeline']={'clock_alignment':alignment if aligned else 'unavailable',
        'origin_ns':clock.get('origin_ns') if aligned else None,'artifact_id':'trace-sqlite' if aligned else None,
        'clock_evidence':'One captured single-host Nsight timestamp domain; original per-rank offsets are preserved.' if aligned else 'No common cross-rank clock domain has been established.',
        'chunks':sorted(chunks,key=lambda c:(c['rank'],c['forward_ordinal']))}
    zero_count=sum(sidecar.get('coverage',{}).get('counts',{}).get('zero_duration',{}).values())
    if zero_count:result['limitations'].append(f'{zero_count} zero-duration activity records are excluded from the duration ledger; their counts remain in the source extraction audit.')
    if clock.get('collector_rank_warnings'):
        result['limitations'].append('Nsight reported that some CUDA or NVTX records might not have been collected. GPU totals describe captured activity; complete execution coverage is not certified.')
    if not complete:result['limitations'].append('Full-request execution coverage has not passed independent review; request MFU remains unavailable.')
    validate(result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--sidecar',required=True,type=Path);p.add_argument('--output',required=True,type=Path)
    for name in ['request-receipt','work-bindings','coverage-review','nominal-roofs','hardware-receipt','target-model-work']:p.add_argument('--'+name,type=Path)
    a=p.parse_args();raw=a.sidecar.read_bytes();kwargs={}
    for arg,key,sha_key in [('request_receipt','request_receipt','request_sha'),('work_bindings','work_bindings','bindings_sha'),('coverage_review','coverage_review','coverage_sha'),('nominal_roofs','nominal_roofs',None),('hardware_receipt','hardware_receipt','hardware_sha'),('target_model_work','target_model_work','target_work_sha')]:
        path=getattr(a,arg)
        if path:
            b=path.read_bytes();kwargs[key]=load_json(b)
            if sha_key:kwargs[sha_key]=hashlib.sha256(b).hexdigest()
    result=convert(load_json(raw),hashlib.sha256(raw).hexdigest(),**kwargs)
    a.output.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':'))+'\n')
    print(json.dumps({'events':len(result['events']),'nodes':len(result['nodes']),'work_bound_leaves':sum(n['work_matches_events'] for n in result['nodes']),'full_coverage':result['request']['execution_coverage_complete']}))
if __name__=='__main__':main()
