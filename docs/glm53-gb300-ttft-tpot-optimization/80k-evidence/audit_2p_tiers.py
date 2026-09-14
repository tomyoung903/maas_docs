"""CPU sensitivity only: distinguish GPU, inclusive host and shared-cache hits."""
import collections,hashlib,heapq,json,sys,time
from pathlib import Path
R=Path('/mnt/HPC/tom/pd-80k-rerun-20260914');D=R/'dataset-2p1d-candidate29'
sys.path.insert(0,'/mnt/HPC/tom/dataset-capacity-v2-20260911.yGzjq1')
from finite_plan_v5 import FiniteCache
raw=Path('/mnt/HPC/tom/dataset-capacity-v2-20260911.yGzjq1/prefix-metadata.json').read_bytes();data=json.loads(raw)
pr=(D/'candidate.json').read_bytes();plan=json.loads(pr);assert plan['input_sha256']==hashlib.sha256(raw).hexdigest()
assert len(plan['warmup_requests'])==400 and len(plan['measured_requests'])==7504
dest=D/'three-tier-affinity-sensitivity.json';assert not dest.exists()
started=time.monotonic();results=[]
for mode in ['greedy_local_unpinned','first_choice_affinity','session_hash']:
    gpu=[FiniteCache(data['nodes'],9252096) for _ in range(2)]
    host=[FiniteCache(data['nodes'],13878208) for _ in range(2)];shared=FiniteCache(data['nodes'],20000000)
    bindings={};work=[0,0];queue=[];seq=0;minutes=collections.defaultdict(collections.Counter);routes=collections.Counter()
    def advance(t):
        while queue and queue[0][0]<=t:
            ct,_,kind,pod,row=heapq.heappop(queue)
            if kind=='local':gpu[pod].commit(row,ct);host[pod].commit(row,ct)
            else:shared.commit(row,ct)
        for c in gpu+host+[shared]:c.advance(t)
    def choose(row):
        sid=row['session_id']
        if mode=='session_hash':return int.from_bytes(hashlib.sha256(sid.encode()).digest()[:8],'big')%2
        if mode=='first_choice_affinity' and sid in bindings:return bindings[sid]
        h=[max(gpu[j].lookup(row),host[j].lookup(row)) for j in range(2)]
        pod=min(range(2),key=lambda j:(-h[j],work[j],j));bindings.setdefault(sid,pod);return pod
    def commit_at(t,row,pod):
        global seq
        seq+=1;heapq.heappush(queue,(t,seq,'local',pod,row))
        seq+=1;heapq.heappush(queue,(t+2,seq,'shared',pod,row))
    for i,row in enumerate(plan['warmup_requests']):
        t=120*i/399;advance(t);pod=choose(row);work[pod]+=row['length'];commit_at(t,row,pod);advance(t)
    for row in plan['measured_requests']:
        t=120+row['offset_s'];advance(t);pod=choose(row)
        g=gpu[pod].lookup(row);h=max(host[pod].lookup(row),g);s=max(shared.lookup(row),h)
        values={'requests':1,'input':row['length'],'new':row['length']-s,'device_hit':g,'host_hit':h-g,'storage_hit':s-h,'extra_uncached':row['length']-s-row['finite_uncached_tokens']}
        assert values['new']>0 and sum(values[k] for k in ['new','device_hit','host_hit','storage_hit'])==values['input']
        minute=int(row['offset_s']//60);minutes[minute].update(values);routes[pod]+=1;work[pod]+=row['length'];commit_at(t+10,row,pod)
    total=sum(minutes.values(),collections.Counter());result={'routing_scenario':mode,'per_minute':dict(minutes),'total':dict(total),'requests_per_prefill':dict(routes),
        'average_uncached_tpm':total['new']/10,'host_plus_shared_tokens':total['host_hit']+total['storage_hit']}
    results.append(result);print(json.dumps({k:result[k] for k in ['routing_scenario','average_uncached_tpm','host_plus_shared_tokens','requests_per_prefill']}),flush=True)
record={'candidate_sha256':hashlib.sha256(pr).hexdigest(),'metadata_sha256':hashlib.sha256(raw).hexdigest(),'elapsed_s':time.monotonic()-started,'scenarios':results,
    'fixed_capacities':{'gpu_each':9252096,'inclusive_host_each':13878208,'shared':20000000},'completion_delay_s':10,'publication_delay_s':2,
    'status':'CPU sensitivity only; not native router/allocator simulation or acceptance',
    'limitations':['Greedy first-choice uses local prefix and cumulative input ties, not Dynamo queue/load scoring.','Independent prefix-preserving leaf-LRU tiers with whole-path refresh are optimistic; physical Store eviction, pinning and transfer latency are not modeled.','Real-request frontend/prepared token equivalence is not fully proven.','Session affinity may influence Decode DP balance; this model covers only Prefill caches.','No warmup drain/pause wall-time drift or output KV is modeled.']}
with dest.open('x') as f:json.dump(record,f,indent=2)
