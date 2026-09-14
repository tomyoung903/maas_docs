"""Bounded two-Prefill sensitivity model; no registration or inference traffic."""
import collections
import hashlib
import heapq
import json
from pathlib import Path
import sys
import time

R=Path('/mnt/HPC/tom/pd-80k-rerun-20260914')
D=R/'dataset-2p1d-candidate29'
OLD=Path('/mnt/HPC/tom/dataset-capacity-v2-20260911.yGzjq1')
sys.path.insert(0,str(OLD))
from finite_plan_v5 import FiniteCache
from check_finite import all_windows

raw=(OLD/'prefix-metadata.json').read_bytes();data=json.loads(raw)
pr=(D/'candidate.json').read_bytes();plan=json.loads(pr)
assert plan['input_sha256']==hashlib.sha256(raw).hexdigest()
warm,rows=plan['warmup_requests'],plan['measured_requests']
assert len({r['request_id'] for r in warm+rows})==len(warm)+len(rows)
assert len(warm)==400 and len(rows)==7504

def scenario(route, local_capacity, l3_capacity, completion_delay, publication_delay):
    local=[FiniteCache(data['nodes'],local_capacity),FiniteCache(data['nodes'],local_capacity)]
    shared=FiniteCache(data['nodes'],l3_capacity) if l3_capacity else None
    queue=[];sequence=0;totals=[0,0];last_route={};l3_rescues=0;l3_tokens=0;values=[];extra=[];work=[0,0];done_warm=[]
    def route_for(row,ordinal):
        if route=='session_hash':return int.from_bytes(hashlib.sha256(row['session_id'].encode()).digest()[:8],'big')%2
        if route=='round_robin':return ordinal%2
        hits=[c.lookup(row) for c in local]
        return min(range(2),key=lambda j:(-hits[j],totals[j],j))
    def submit(t,row,pod):
        nonlocal sequence
        sequence+=1;heapq.heappush(queue,(t,sequence,'local',pod,row))
        if shared:
            sequence+=1;heapq.heappush(queue,(t+publication_delay,sequence,'shared',pod,row))
    def advance(t):
        while queue and queue[0][0]<=t:
            ct,_,kind,pod,row=heapq.heappop(queue)
            (local[pod] if kind=='local' else shared).commit(row,ct)
        for c in local:c.advance(t)
        if shared:shared.advance(t)
    # Warmup completions are spread across 120s, not made fresh at t=0.
    for i,row in enumerate(warm):
        t=120*i/max(1,len(warm)-1);advance(t);pod=route_for(row,i)
        submit(t,row,pod);totals[pod]+=row['length'];advance(t)
    for i,row in enumerate(rows):
        t=120+row['offset_s'];advance(t);pod=route_for(row,i+len(warm))
        local_hit=local[pod].lookup(row);shared_hit=shared.lookup(row) if shared else 0
        hit=max(local_hit,shared_hit);uncached=row['length']-hit
        if shared_hit>local_hit:l3_rescues+=1;l3_tokens+=shared_hit-local_hit
        delta=uncached-row['ideal_uncached_tokens'];values.append(uncached)
        if delta:extra.append({'ordinal':i,'offset_s':row['offset_s'],'extra_uncached_tokens':delta,'pod':pod})
        work[pod]+=uncached;totals[pod]+=row['length'];submit(t+completion_delay,row,pod)
    total=sum(row['length'] for row in rows);uncached=sum(values)
    return {'routing':route,'local_capacity_each':local_capacity,'shared_L3_capacity_tokens':l3_capacity,'completion_delay_s':completion_delay,'additional_L3_publication_delay_s':publication_delay,'total_uncached_tokens':uncached,'average_uncached_tpm':uncached/10,'hit_ratio':1-uncached/total,'extra_uncached_tokens':sum(x['extra_uncached_tokens'] for x in extra),'changed_requests':len(extra),'L3_rescue_requests':l3_rescues,'L3_rescue_tokens':l3_tokens,'per_prefill_uncached_tokens':work,'local_peak_tokens':[c.peak*64 for c in local],'shared_peak_tokens':shared.peak*64 if shared else 0,'rolling':all_windows(rows,values,plan['parameters']),'largest_miss_changes':sorted(extra,key=lambda x:-x['extra_uncached_tokens'])[:8]}

started=time.monotonic();out=[]
# L3 is an explicit hypothetical logical budget, not a proven byte capacity.
for route,localcap,sharedcap,delay,pubdelay in [
 ('session_hash',13878208,0,10,0),
 ('best_local',13878208,0,10,0),
 ('round_robin',13878208,0,10,0),
 ('session_hash',11102528,20000000,10,2),
 ('best_local',11102528,20000000,10,2),
 ('round_robin',11102528,20000000,10,2),
 ('round_robin',11102528,20000000,10,5),
 ('round_robin',11102528,20000000,10,10),
]:
    result=scenario(route,localcap,sharedcap,delay,pubdelay);out.append(result)
    print(json.dumps({k:result[k] for k in ['routing','local_capacity_each','shared_L3_capacity_tokens','additional_L3_publication_delay_s','average_uncached_tpm','extra_uncached_tokens','L3_rescue_requests']}|{'failed_rolling_probes':result['rolling']['failed_probes']}),flush=True)
record={'schema':'two-prefill-cache-sensitivity/v1','candidate_sha256':hashlib.sha256(pr).hexdigest(),'metadata_sha256':hashlib.sha256(raw).hexdigest(),'scenarios':out,'elapsed_s':time.monotonic()-started,'status':'planning model only','assumptions':['Each Prefill has one inclusive local capacity; L1 and L2 are not added.','Prefix-closed page leaf-LRU; no active pinning or host allocation pressure.','Requests commit local KV after fixed completion delay; shared publication has an extra delay.','L3 lookup credit assumes the whole matching prefix can be fetched; transport latency/failures are not simulated.','Routing variants are sensitivity cases, not a reimplementation of Dynamo KV routing.','20M logical-token budget fits the measured Store payload capacity before fragmentation; ordinary-object eviction and local-hit lease invisibility are not simulated.','Original source IDs and exact token-prefix metadata used; no request duplication.','Prompt-only cache state; generated output KV not modeled.'],'runtime_hit_rate_guaranteed':False}
with (D/'two-prefill-cache-audit.json').open('x') as f:json.dump(record,f,indent=2)
print(json.dumps({'output':str(D/'two-prefill-cache-audit.json'),'elapsed_s':record['elapsed_s']}))
