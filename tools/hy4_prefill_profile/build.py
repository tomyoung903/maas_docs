#!/usr/bin/env python3
"""Validate a public-safe HY4 event/work ledger and build the static report."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
SCHEMA = 'hy4-prefill-profile-v1'
KINDS = ['model', 'rank', 'chunk', 'layer', 'operator']
PRECISIONS = {'nvfp4', 'fp8', 'bf16', 'fp16', 'tf32', 'fp32', 'fp64'}
PUBLIC_HOSTS = ('github.com', 'github.io', 'nvidia.com', 'huggingface.co', 'sglang.ai', 'arxiv.org', 'dam-cdn.nvd.orangelogic.com')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, name, *, nullable=False, integer=False, positive=False):
    if value is None and nullable:
        return
    require(not isinstance(value, bool) and isinstance(value, (int, float)), f'{name}: number required')
    require(math.isfinite(value) and value >= 0, f'{name}: finite nonnegative number required')
    if integer:
        require(isinstance(value, int), f'{name}: exact integer required')
    if positive:
        require(value > 0, f'{name}: positive value required')


def load_json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, f'duplicate JSON key: {key}')
            out[key] = value
        return out
    def bad_constant(value):
        raise ValueError(f'non-finite JSON constant: {value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=bad_constant)


def public_safe(value):
    """Reject likely private paths/URLs; this is a publication guard, not redaction."""
    if isinstance(value, dict):
        for k, v in value.items():
            public_safe(k)
            public_safe(v)
    elif isinstance(value, list):
        for v in value:
            public_safe(v)
    elif isinstance(value, str):
        require(not re.search(r'(?:/home/|/workspace/|/mnt/|/root/|/opt/|/tmp/|[A-Za-z]:\\|localhost|127\.0\.0\.1|\b10\.\d+\.\d+\.\d+\b|\b192\.168\.\d+\.\d+\b|\b172\.(?:1[6-9]|2\d|3[01])\.\d+\.\d+\b)', value, re.I), 'private path/address in public data')
        for raw in re.findall(r'https?://[^\s<>"\']+', value):
            u = urlparse(raw)
            require(u.scheme == 'https' and not u.username and not u.password, 'only public HTTPS references allowed')
            h = u.hostname or ''
            require(any(h == p or h.endswith('.' + p) for p in PUBLIC_HOSTS), f'unreviewed public URL host: {h}')
        require(not re.search(r'(?i)(?:bearer\s+[a-z0-9]|api[_-]?key\s*[:=]|access[_-]?token\s*[:=])', value), 'credential-like public data')


def keys(value, required, optional=()):
    require(set(required) <= value.keys() and set(value) <= set(required) | set(optional), 'missing or unknown fields: ' + ','.join(sorted(set(value) ^ set(required))))


def validate(data):
    keys(data, ['schema_version','status','request','hardware','artifacts','nodes','events','limitations'], ['timeline','target_model_work'])
    public_safe(data)
    require(data.get('schema_version') == SCHEMA, 'unsupported schema_version')
    require(data.get('status') in {'pending', 'measured'}, 'status must be pending or measured')
    req = data['request']
    keys(req, ['input_tokens','output_tokens','cached_tokens','wall_time_ms','layer_partition','configuration','execution_coverage_complete','coverage_artifact_ids'], ['profiled_server_prefill_ms','warmup_server_prefill_ms','timing_artifact_ids'])
    require(req['input_tokens'] == 100000 and req['output_tokens'] == 1, 'this report is exactly decimal100000 input /1 output')
    number(req.get('cached_tokens'), 'cached_tokens', nullable=True, integer=True)
    number(req.get('wall_time_ms'), 'wall_time_ms', nullable=True, positive=True)
    for key in ['profiled_server_prefill_ms','warmup_server_prefill_ms']:
        number(req.get(key), key, nullable=True, positive=True)
    require(req['layer_partition'] == [16, 21, 21, 20], 'current baseline layer partition required')
    require(isinstance(req['execution_coverage_complete'], bool), 'explicit request execution coverage required')
    hw = data['hardware']
    keys(hw, ['devices','compute_roofs_tflops','bandwidth_roof_tb_s','roof_artifact_ids'], ['device_name','roof_note'])
    require(hw['devices'] == [0, 1, 2, 3], 'baseline device/rank list must be [0,1,2,3]')
    for precision, roof in hw['compute_roofs_tflops'].items():
        require(precision in PRECISIONS, f'unknown precision roof {precision}')
        number(roof, 'compute roof', positive=True)
    number(hw['bandwidth_roof_tb_s'], 'bandwidth roof', nullable=True, positive=True)
    artifacts = {a['id']: a for a in data['artifacts']}
    require(len(artifacts) == len(data['artifacts']), 'duplicate artifact ID')
    for a in artifacts.values():
        keys(a, ['id','label','sha256'], ['url'])
        require(bool(re.fullmatch(r'[a-zA-Z0-9._-]+', a['id'])), 'unsafe artifact ID')
        require(bool(re.fullmatch(r'[0-9a-f]{64}', a['sha256'])), 'artifact SHA256 required')
        require(isinstance(a['label'], str) and bool(a['label']), 'artifact public label required')
    require(set(req['coverage_artifact_ids']) <= artifacts.keys(), 'unknown request coverage artifact')
    require(set(req.get('timing_artifact_ids',[])) <= artifacts.keys(), 'unknown request timing artifact')
    if any(req.get(k) is not None for k in ['profiled_server_prefill_ms','warmup_server_prefill_ms']):
        require(data['status']=='measured' and bool(req.get('timing_artifact_ids')), 'server timing requires measured receipt evidence')
    if req['execution_coverage_complete']:
        require(bool(req['coverage_artifact_ids']), 'complete request coverage requires evidence')
    if hw['compute_roofs_tflops'] or hw['bandwidth_roof_tb_s'] is not None:
        require(bool(hw['roof_artifact_ids']) and set(hw['roof_artifact_ids']) <= artifacts.keys(), 'roof evidence required')
    if 'target_model_work' in data:
        target=data['target_model_work']
        keys(target,['flops_by_precision','scope','source_artifact_ids','request_artifact_ids','request_completed','input_tokens','output_tokens'])
        require(target['input_tokens']==req['input_tokens'] and target['output_tokens']==req['output_tokens'], 'target model work/request geometry mismatch')
        require(data['status']=='measured' and target['request_completed'] is True and req['cached_tokens']==0 and req['wall_time_ms'] is not None, 'target model request MFU requires completed cold-request evidence')
        for ids in [target['source_artifact_ids'],target['request_artifact_ids']]:
            require(bool(ids) and set(ids)<=artifacts.keys(),'target model work requires source and request artifacts')
        require(bool(target['scope']) and bool(target['flops_by_precision']),'target model scope and work required')
        for precision,flops in target['flops_by_precision'].items():
            require(precision in PRECISIONS,'unknown target precision');number(flops,'target model FLOPs',integer=True)
    nodes = {n['id']: n for n in data['nodes']}
    require(len(nodes) == len(data['nodes']) and bool(nodes), 'duplicate/empty nodes')
    roots = [n for n in nodes.values() if n['parent_id'] is None]
    require(len(roots) == 1 and roots[0]['kind'] == 'model', 'one model root required')
    ranks = set()
    for n in nodes.values():
        keys(n, ['id','parent_id','kind','label','rank','chunk','layer','work','work_matches_events','artifact_ids'], ['note','formula','boundary'])
        require(bool(re.fullmatch(r'[a-zA-Z0-9._-]+', n['id'])), 'unsafe node ID')
        require(n['kind'] in KINDS, 'unknown node kind')
        require(isinstance(n['label'], str), 'node label required')
        require(isinstance(n['work_matches_events'], bool), 'explicit work_matches_events required')
        require(set(n['artifact_ids']) <= artifacts.keys(), 'unknown node artifact')
        parent = nodes.get(n['parent_id'])
        if parent:
            require(KINDS.index(n['kind']) == KINDS.index(parent['kind']) + 1, 'hierarchy must be model/rank/chunk/layer/operator')
            require(n['rank'] in hw['devices'], 'rank required below model')
            if parent['kind'] != 'model':
                require(n['rank'] == parent['rank'], 'rank differs from parent')
            if parent['kind'] in {'chunk', 'layer'}:
                require(n['chunk'] == parent['chunk'], 'chunk differs from parent')
            if parent['kind'] == 'layer':
                require(n['layer'] == parent['layer'], 'layer differs from parent')
        else:
            require(n is roots[0], 'missing parent or disconnected root')
        if n['kind'] == 'rank':
            require(n['rank'] not in ranks, 'duplicate rank node')
            ranks.add(n['rank'])
        if n['kind'] in {'layer', 'operator'}:
            if n['layer'] is None:
                require(n.get('boundary') is True, 'null layer must be an explicit input/output boundary')
            else:
                number(n['layer'], 'layer', integer=True)
                bounds = [0,16,37,58,78]
                require(bounds[n['rank']] <= n['layer'] < bounds[n['rank']+1], 'layer outside baseline PP partition')
        work = n['work']
        keys(work, ['status','flops_by_precision','scalar_ops','useful_bytes','useful_bytes_note','dram_bytes','dram_counter_artifact_id'])
        require(work['status'] in {'unavailable', 'source_estimate', 'verified'}, 'work status invalid')
        if work['flops_by_precision'] is not None:
            require(work['status'] != 'unavailable', 'available work cannot be labeled unavailable')
            require(n['kind'] == 'operator', 'FLOP work belongs only to operator leaves')
            require(set(work['flops_by_precision']) <= PRECISIONS, 'unknown precision class')
            for v in work['flops_by_precision'].values():
                number(v, 'FLOPs', integer=True)
        number(work['scalar_ops'], 'scalar operations', nullable=True, integer=True)
        number(work['useful_bytes'], 'useful bytes', nullable=True, integer=True)
        number(work['dram_bytes'], 'DRAM bytes', nullable=True, integer=True)
        if work['useful_bytes'] is not None:
            require(n['kind'] == 'operator' and bool(work['useful_bytes_note']), 'leaf useful-byte model note required')
        if work['dram_bytes'] is not None:
            require(n['kind'] == 'operator' and work['dram_counter_artifact_id'] in artifacts, 'leaf DRAM counter evidence required')
        if n['work_matches_events']:
            require(bool(n['artifact_ids']), 'work/event join evidence required')
    require(ranks == {0,1,2,3}, 'all four baseline ranks required')
    parents_with_children={n['parent_id'] for n in nodes.values()}
    for n in nodes.values():
        if n['kind'] != 'operator':
            require(n['id'] in parents_with_children, 'empty hierarchy branch; add an unavailable operator placeholder')
    # Strict depth increase above rules out cycles, including disconnected cycles.
    for n in nodes.values():
        seen = set()
        while n['parent_id'] is not None:
            require(n['id'] not in seen, 'node cycle')
            seen.add(n['id']); n = nodes[n['parent_id']]
        require(n is roots[0], 'disconnected hierarchy')
    ids = set()
    for e in data['events']:
        keys(e, ['id','rank','start_ns','duration_ns','owner_id','artifact_id'], ['kind','category','communication_direction','classification_artifact_id'])
        require(e.get('category','unclassified') in {'compute','communication','memory','unclassified'}, 'unknown timeline category')
        require(e.get('kind','kernel') in {'kernel','memcpy','memset'}, 'unknown GPU event kind')
        require(e['id'] not in ids, 'duplicate event ID'); ids.add(e['id'])
        require(e['rank'] in hw['devices'], 'event rank invalid')
        number(e['start_ns'], 'event start', integer=True)
        number(e['duration_ns'], 'event duration', integer=True, positive=True)
        require(e['artifact_id'] in artifacts, 'event artifact required')
        if 'communication_direction' in e or 'classification_artifact_id' in e:
            require(e.get('communication_direction') in {'send','recv'} and e.get('category')=='communication' and e.get('kind')=='kernel', 'audited communication direction requires a communication kernel')
            require(e.get('classification_artifact_id') in artifacts,'communication classification evidence required')
        owner = nodes.get(e['owner_id'])
        require(e['owner_id'] is None or (owner and owner['kind'] == 'operator' and owner['rank'] == e['rank']), 'event requires one matching operator owner or null')
    if data['status'] == 'pending':
        require(not data['events'] and req['wall_time_ms'] is None and req['cached_tokens'] is None and not req['execution_coverage_complete'], 'pending report cannot contain measured observations')
    else:
        require(all(n['chunk'] != 'pending' for n in nodes.values()), 'measured report cannot contain a planned pending chunk')
        require(bool(data['events']) and req['wall_time_ms'] is not None and req['cached_tokens'] == 0, 'measured cold request requires intervals, wall time and zero cached tokens')
    if 'timeline' in data:
        t=data['timeline']
        keys(t, ['clock_alignment','origin_ns','artifact_id','clock_evidence','chunks'])
        require(t['clock_alignment'] in {'unavailable','single_host_nsight_common_origin'}, 'unsupported timeline clock domain')
        number(t['origin_ns'], 'timeline origin', nullable=True, integer=True)
        if t['clock_alignment']!='unavailable':
            require(data['status']=='measured' and t['origin_ns'] is not None and t['artifact_id'] in artifacts and bool(t['clock_evidence']), 'aligned timeline requires measured common-clock evidence')
        for c in t['chunks']:
            keys(c, ['node_id','rank','forward_ordinal','start_ns','duration_ns','new_tokens'])
            require(c['node_id'] in nodes and nodes[c['node_id']]['kind']=='chunk', 'timeline chunk missing from tree')
            require(nodes[c['node_id']]['rank']==c['rank'] and nodes[c['node_id']]['chunk']==c['forward_ordinal'], 'timeline chunk/tree identity mismatch')
            number(c['start_ns'],'chunk start',integer=True)
            number(c['duration_ns'],'chunk duration',integer=True,positive=True)
            number(c['new_tokens'],'chunk token count',nullable=True,integer=True,positive=True)
        require(len({c['node_id'] for c in t['chunks']})==len(t['chunks']), 'duplicate timeline chunk')
        if data['status']=='pending':require(not t['chunks'],'pending report cannot have measured chunk spans')
    return nodes, roots[0]['id']


def union_ns(events):
    # Different rank/device clocks are never unioned with one another.
    total = 0
    for rank in sorted({e['rank'] for e in events}):
        end = None
        for e in sorted((x for x in events if x['rank'] == rank), key=lambda x: x['start_ns']):
            a, b = e['start_ns'], e['start_ns'] + e['duration_ns']
            total += b-a if end is None or a >= end else max(0, b-end)
            end = max(end or 0, b)
    return total


def compile_report(data):
    nodes, root_id = validate(data)
    result = copy.deepcopy(data)
    children = {k: [] for k in nodes}
    for n in nodes.values():
        if n['parent_id'] is not None:
            children[n['parent_id']].append(n['id'])
    own_events = {k: [] for k in nodes}
    for e in data['events']:
        if e['owner_id']:
            own_events[e['owner_id']].append(e)
    metrics = {}
    hw = data['hardware']
    def visit(key):
        n = nodes[key]
        leaves, events = ([n], list(own_events[key])) if n['kind'] == 'operator' else ([], [])
        for c in children[key]:
            child_leaves, child_events = visit(c)
            leaves += child_leaves; events += child_events
        measured = data['status'] == 'measured'
        ms = sum(e['duration_ns'] for e in events)/1e6 if measured else None
        active = union_ns(events)/1e6 if measured else None
        parts = {}
        for leaf in leaves:
            for p, f in (leaf['work']['flops_by_precision'] or {}).items():
                parts[p] = parts.get(p, 0)+f
        complete = bool(leaves) and all(x['work']['flops_by_precision'] is not None for x in leaves)
        join = bool(leaves) and all(x['work_matches_events'] and own_events[x['id']] for x in leaves)
        roof_complete = set(parts) <= hw['compute_roofs_tflops'].keys()
        ideal_s = sum(f/(hw['compute_roofs_tflops'][p]*1e12) for p,f in parts.items()) if complete and roof_complete and parts else None
        mfu = 100*ideal_s/(active/1e3) if ideal_s is not None and active and join else None
        mfu_r = 100*ideal_s/(ms/1e3) if ideal_s is not None and ms and join else None
        leaf_work = n['work'] if n['kind'] == 'operator' else {}
        useful = leaf_work.get('useful_bytes')
        dram = leaf_work.get('dram_bytes')
        bandwidth = hw['bandwidth_roof_tb_s']
        def mbu(b):
            return 100*b/(bandwidth*1e12*(active/1e3)) if b is not None and bandwidth and active and join else None
        metrics[key] = {
            'event_count': len(events) if measured else None,
            'event_kind_counts': {kind:sum(e.get('kind','kernel')==kind for e in events) for kind in ['kernel','memcpy','memset']} if measured else None,
            'summed_residency_ms': ms, 'device_union_sum_ms': active,
            'overlap_excess_ms': ms-active if measured else None,
            'single_device_span_ms': ((max(e['start_ns']+e['duration_ns'] for e in events)-min(e['start_ns'] for e in events))/1e6) if events and len({e['rank'] for e in events}) == 1 else None,
            'flops_by_precision': parts, 'flops_by_precision_exact': {p: str(f) for p,f in parts.items()}, 'flop_coverage_complete': complete,
            'operator_leaves': len(leaves), 'leaves_with_flops': sum(x['work']['flops_by_precision'] is not None for x in leaves),
            'work_event_join_complete': join,
            'mfu_active_union_percent': mfu, 'mfu_summed_residency_percent': mfu_r,
            'useful_bytes': useful, 'estimated_mbu_active_union_percent': mbu(useful),
            'dram_bytes': dram, 'counter_mbu_active_union_percent': mbu(dram),
            'ideal_compute_seconds': ideal_s,
        }
        return leaves, events
    visit(root_id)
    all_events = data['events']
    unknown = [e for e in all_events if e['owner_id'] is None]
    req = data['request']
    root = metrics[root_id]
    phase_mfu = 100*root['ideal_compute_seconds']/(len(hw['devices'])*req['wall_time_ms']/1000) if root['ideal_compute_seconds'] is not None and req['wall_time_ms'] and root['work_event_join_complete'] and not unknown and req['execution_coverage_complete'] else None
    target=data.get('target_model_work');target_ideal=None;target_mfu=None
    if target and set(target['flops_by_precision'])<=hw['compute_roofs_tflops'].keys():
        target_ideal=sum(f/(hw['compute_roofs_tflops'][p]*1e12) for p,f in target['flops_by_precision'].items())
        target_mfu=100*target_ideal/(len(hw['devices'])*req['wall_time_ms']/1000)
    timing=data.get('timeline')
    timeline_available=bool(data['status']=='measured' and all_events and timing and timing['clock_alignment']=='single_host_nsight_common_origin')
    timeline_result={'available':timeline_available,
        'reason':None if timeline_available else ('Measurement pending.' if data['status']=='pending' else 'Common single-host clock evidence is unavailable; cross-rank alignment is not inferred.'),
        'start_ns':0 if timeline_available else None,
        'end_ns':max(e['start_ns']+e['duration_ns'] for e in all_events) if timeline_available else None,
        'origin_ns_exact':str(timing['origin_ns']) if timeline_available else None}
    result['derived'] = {
        'timeline':timeline_result,
        'root_id':root_id, 'children':children, 'nodes':metrics,
        'request_mfu_percent':phase_mfu,
        'target_model_request_mfu_percent':target_mfu,
        'target_model_ideal_compute_seconds':target_ideal,
        'total_event_count':len(all_events) if data['status']=='measured' else None,
        'unattributed_event_count':len(unknown) if data['status']=='measured' else None,
        'unattributed_by_rank':{str(r): {'event_count':sum(e['rank']==r for e in unknown), 'residency_ms':sum(e['duration_ns'] for e in unknown if e['rank']==r)/1e6} for r in hw['devices']} if data['status']=='measured' else None,
        'unattributed_residency_ms':sum(e['duration_ns'] for e in unknown)/1e6 if data['status']=='measured' else None,
        'all_events_device_union_sum_ms':union_ns(all_events)/1e6 if data['status']=='measured' else None,
        'all_events_residency_ms':sum(e['duration_ns'] for e in all_events)/1e6 if data['status']=='measured' else None,
    }
    return result


def encoded(data):
    return json.dumps(data,ensure_ascii=False,allow_nan=False,separators=(',',':')).replace('&','\\u0026').replace('<','\\u003c').replace('>','\\u003e').replace('\u2028','\\u2028').replace('\u2029','\\u2029')


def build(source, output):
    raw = source.read_bytes()
    data = load_json(raw)
    result = compile_report(data)
    result['input_sha256'] = hashlib.sha256(raw).hexdigest()
    result['generator_sources'] = [{'label':p.name,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [HERE/'build.py',HERE/'app.js',HERE/'style.css',HERE/'template.html',HERE/'schema.json',HERE/'timeline.js']]
    output.mkdir(parents=True, exist_ok=True)
    (output/'input-schema.json').write_bytes((HERE/'schema.json').read_bytes())
    (output/'source-data.json').write_bytes(raw)
    (output/'report-data.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':'))+'\n')
    html = (HERE/'template.html').read_text().replace('<!--REPORT_DATA-->',encoded(result)).replace('/*REPORT_STYLE*/',(HERE/'style.css').read_text()).replace('/*REPORT_APP*/',(HERE/'app.js').read_text()).replace('/*REPORT_TIMELINE*/',(HERE/'timeline.js').read_text())
    require(html.count('data-maas-annotator') == 1, 'one annotator required')
    (output/'index.html').write_text(html)
    return result


def default_input():
    current=ROOT/'docs/hy4-100k-prefill/source-data.json'
    return current if current.is_file() else HERE/'pending-input.json'


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,help='Defaults to the current published-source ledger; pending bootstrap only if no current ledger exists')
    p.add_argument('--output',type=Path,default=ROOT/'docs/hy4-100k-prefill')
    p.add_argument('--validate-only',action='store_true')
    a=p.parse_args()
    if a.input is None:a.input=default_input()
    if a.validate_only:
        r=compile_report(load_json(a.input.read_bytes()))
    else:
        r=build(a.input,a.output)
    print(json.dumps({'status':r['status'],'nodes':len(r['nodes']),'events':len(r['events']),'unattributed':r['derived']['unattributed_event_count']}))

if __name__=='__main__': main()
