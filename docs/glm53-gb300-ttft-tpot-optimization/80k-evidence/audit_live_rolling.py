"""Audit every actual60s admission boundary with final usage; preserve unknown coverage."""
import hashlib,json,subprocess,sys
from pathlib import Path
N=Path(__file__).resolve().parent;A=N/sys.argv[1];P=A/'replay';C=N/('dataset-2p1d-candidate29' if A.name=='run-2p1d-80k' else 'dataset-1p1d-candidate01')
final=json.loads((P/'measured-final.json').read_text());D=N/'evidence'/final['run_id'];rows=[json.loads(l) for l in (D/'timing-events.jsonl').read_text().splitlines()];base=json.loads((D/'timeseries.json').read_text())['distribution_sliding']['base_time'];source=json.loads((C/'candidate.json').read_text());expected={x['request_id']:x for x in source['measured_requests']}
unknown=[x['request_id'] for x in rows if not x['success'] or x.get('input_tokens') is None or x.get('cached_tokens') is None or not x.get('cache_usage_available')]
coverage={'expected':len(expected),'recorded':len(rows),'usage_unknown_requests':unknown,'unknown_usage_policy':'No zero-imputation. Complete live-cache audit requires all planned requests and recognized final cache usage.'}
(P/'live-rolling-coverage.json').write_text(json.dumps(coverage,indent=2)+'\n')
assert len(rows)==len(expected) and not unknown,'Incomplete live-usage coverage; retain partial result without complete-load certification'
actual=[dict(expected[x['request_id']],offset_s=x['request_body_sent_time']-base,planned_offset_s=x['request_body_sent_time']-base,length=x['input_tokens'],ideal_uncached_tokens=x['input_tokens']-x['cached_tokens'],finite_uncached_tokens=x['input_tokens']-x['cached_tokens']) for x in rows];actual.sort(key=lambda x:x['offset_s'])
projection={'schema':'observed-runtime-usage-projection/v1','parameters':source['parameters'],'measured_requests':actual,'basis':'Observed dispatch offsets and final server usage. The legacy auditor field ideal_uncached_tokens contains observed uncached usage in this projection only.','source_plan_sha256':hashlib.sha256((C/'candidate.json').read_bytes()).hexdigest(),'source_events_sha256':hashlib.sha256((D/'timing-events.jsonl').read_bytes()).hexdigest()}
file=P/'observed-runtime-usage-projection.json';file.write_text(json.dumps(projection)+'\n')
cmd=['python3','/mnt/HPC/tom/armory/environment/.codex/skills/datasets/create-custom-dataset/scripts/audit_all_rolling_boundaries.py','--plan',str(file),'--output',str(P/'live-rolling-audit.json')]
r=subprocess.run(cmd,text=True,capture_output=True);(P/'live-rolling-audit.stdout').write_text(r.stdout+r.stderr);assert r.returncode in [0,1],r.stderr
out=json.loads((P/'live-rolling-audit.json').read_text());print(json.dumps({'run_id':final['run_id'],'coverage':coverage,'all_boundary_numeric_audit':out},indent=2))
