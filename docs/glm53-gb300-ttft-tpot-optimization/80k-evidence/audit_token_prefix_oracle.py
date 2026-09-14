"""Independent prefix oracle over original token bytes; no compressed trie or inference."""
import hashlib,json,subprocess,time
from pathlib import Path
N=Path(__file__).resolve().parent
code=r'''
import hashlib,json,sys,time
from pathlib import Path
sys.path.insert(0,'/app/replay');import bench_timeseries as b
plans=json.load(sys.stdin);root=Path('/var/cache/replay/prompt-tokens/bench_timeseries/prompt_tokens/c41ea65501c59bb711c1c1f0a42ea12bfdbb842f63ace941d9ef0d610e68c559');manifest=json.loads((root/'manifest.json').read_bytes())
assert hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest()=='f81755f71bf3b4ceff5a80b1aa99b41dcfe8f9b30a7903675d44ad9866625481'
store=b._load_prompt_token_store(root,manifest['cache_key'],'read_only_independent_prefix_oracle')
rows={r.request_id:r for s in b._load_trace_pack_directory(Path('/mnt/HPC/replay/data/traffic_log_20260724_0700-2000_replay_v2')) for r in s.rows}
results=[]
for name,p in plans.items():
 seen=set();fail=[];checked=0;measured_uncached=0;started=time.monotonic()
 for x in p['warmup_requests']+p['measured_requests']:
  tokens=store.tokens(rows[x['request_id']]);assert len(tokens)==x['length'];raw=tokens.cast('B');width=tokens.itemsize
  h=hashlib.sha256();pages=[];hit=0;limit=(len(tokens)-1)//64;continuous=True
  for i in range(len(tokens)//64):
   h.update(raw[i*64*width:(i+1)*64*width]);digest=h.digest();pages.append(digest)
   if i<limit and continuous and digest in seen:hit+=64
   else:continuous=False
  raw.release();tokens.release()
  if hit!=x['ideal_cached_tokens']:fail.append({'request_id':x['request_id'],'expected':x['ideal_cached_tokens'],'actual':hit})
  seen.update(pages);checked+=1
  if x['phase']=='measured':measured_uncached+=x['length']-hit
 results.append({'candidate':name,'checked':checked,'passed':not fail,'failures':fail[:10],'failure_count':len(fail),'measured_uncached_tokens':measured_uncached,'unique_prefix_pages':len(seen),'elapsed_s':time.monotonic()-started,'method':'SHA256 of cumulative original uint32 token bytes at each64-token boundary; lookup reserves final token; immediate completion/infinite capacity reference only; no metadata trie reused'})
store.close();print(json.dumps(results))
'''
plans={name:json.loads((N/name/'candidate.json').read_bytes()) for name in ['dataset-1p1d-candidate01','dataset-2p1d-candidate29']}
k=['kubectl','--kubeconfig','/home/tom/armory/z_local/kubeconfigs/prod-maas-gb300-taiguo.kubeconfig.yaml','-n','maas-test','exec','-i','alex-stress-test-5df9b67c84-z4z78','--','/opt/replay-venv/bin/python','-c',code]
p=subprocess.run(k,input=json.dumps(plans),text=True,capture_output=True,timeout=180)
(N/'prefix-oracle-stderr.txt').write_text(p.stderr);assert p.returncode==0,p.stderr[-1000:]
for result in json.loads(p.stdout):
 c=N/result['candidate'];result['plan_sha256']=hashlib.sha256((c/'candidate.json').read_bytes()).hexdigest();result['auditor_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
 with (c/'token-prefix-oracle.json').open('x') as f:json.dump(result,f,indent=2)
 print(json.dumps(result),flush=True)
 assert result['passed']
