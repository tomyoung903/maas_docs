#!/usr/bin/env python3
"""Render one reviewed layer from the retained complete public report."""
import argparse
import hashlib
import json
from pathlib import Path
from build import encoded, public_safe, require, union_ns

HERE=Path(__file__).resolve().parent

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def row(node, metrics, role=None):
    return dict(id=node['id'],title=node['label'],role=role or 'Recorded operator family.',
        count=metrics['event_count'],time_ms=metrics['summed_residency_ms'],union_ms=metrics['device_union_sum_ms'],
        mfu_percent=metrics['mfu_active_union_percent'],mbu_percent=metrics['estimated_mbu_active_union_percent'],
        work=node['work'],work_bound=node['work_matches_events'])

def select(report, selection):
    require(report['status']=='measured','single-layer view requires measured data')
    require(selection['source_input_sha256']==report['input_sha256'],'selection/source mismatch')
    nodes={n['id']:n for n in report['nodes']};node=nodes[selection['node_id']]
    require(node['kind']=='layer' and all(node[k]==selection[k] for k in ['rank','chunk','layer']),'selected layer identity differs')
    leaves={n['id']:n for n in report['nodes'] if n['parent_id']==node['id']}
    require(leaves and all(n['kind']=='operator' for n in leaves.values()),'selected layer must contain operator leaves')
    events=[e for e in report['events'] if e['owner_id'] in leaves]
    events.sort(key=lambda e:(e['start_ns'],e['id']))
    event_hash=hashlib.sha256(('\n'.join(e['id'] for e in events)+'\n').encode()).hexdigest()
    require(selection['event_ids_sha256_format']=='chronological_ids_newline_terminated','unknown selected-event digest format')
    require(len(events)==selection['event_count'] and event_hash==selection['event_ids_sha256'],'selected event set differs')
    group_ids=[id for g in selection['groups'] for id in g['operator_ids']]
    require(len(group_ids)==len(set(group_ids)) and set(group_ids)==set(leaves),'groups must partition selected operators exactly once')
    colors=['#16845b','#c27a16','#c46b2d','#16808a','#326b9a','#7c4d9e','#a04e6c','#667085']
    roles=selection.get('operator_roles',{});titles=selection.get('operator_titles',{})
    metrics=report['derived']['nodes'];groups=[];owner_group={}
    for i,spec in enumerate(selection['groups']):
        members=[leaves[id] for id in spec['operator_ids']]
        ee=[e for e in events if e['owner_id'] in spec['operator_ids']]
        parts={}
        for n in members:
            for p,f in (n['work']['flops_by_precision'] or {}).items():parts[p]=parts.get(p,0)+f
        covered=all(n['work_matches_events'] and n['work']['flops_by_precision'] is not None for n in members)
        roofs=report['hardware']['compute_roofs_tflops'];active=union_ns(ee)/1e6
        ideal=sum(f/(roofs[p]*1e12) for p,f in parts.items()) if covered and parts and set(parts)<=set(roofs) else None
        children=[]
        for n in members:
            child=row(n,metrics[n['id']],roles.get(n['id']))
            child['title']=titles.get(n['id'],n['label'])
            children.append(child);owner_group[n['id']]=spec['id']
        groups.append(dict(id=spec['id'],number=i+1,title=spec['title'],role=spec['role'],color=colors[i%len(colors)],
            count=len(ee),time_ms=sum(e['duration_ns'] for e in ee)/1e6,union_ms=active,
            mfu_percent=100*ideal/(active/1000) if ideal is not None and active else None,mbu_percent=None,children=children))
    events=[dict(e,group_id=owner_group[e['owner_id']]) for e in events]
    layer_metrics=metrics[node['id']]
    used_artifacts=set(node['artifact_ids'])|{a for n in leaves.values() for a in n['artifact_ids']}|set(report['hardware']['roof_artifact_ids'])
    payload=dict(schema_version='hy4-selected-layer-v1',selection=selection,layer_metrics=layer_metrics,groups=groups,events=events,
        origin_ns=min(e['start_ns'] for e in events),end_ns=max(e['start_ns']+e['duration_ns'] for e in events),
        bound_operators=sum(n['work_matches_events'] for n in leaves.values()),operator_count=len(leaves),
        request_context=dict(input_tokens=report['request']['input_tokens'],server_prefill_ms=report['request'].get('profiled_server_prefill_ms'),
            client_wall_ms=report['request']['wall_time_ms'],target_model_mfu_percent=report['derived'].get('target_model_request_mfu_percent')),
        artifacts=[a for a in report['artifacts'] if a['id'] in used_artifacts],selection_sha256=digest(selection),
        full_report_input_sha256=report['input_sha256'])
    from semantic_tree import load_semantics, project
    semantics=load_semantics(selection)
    if semantics is not None:
        payload['tree']=project(payload,semantics,report['hardware']['compute_roofs_tflops'])
        payload['event_evidence']=semantics['event_evidence']
        payload['semantic_provenance']=semantics['provenance']
        from metric_completion import load_completion, apply
        completion=load_completion(selection)
        if completion is not None:
            apply(payload,completion,report['hardware']['compute_roofs_tflops'],report['hardware']['bandwidth_roof_tb_s'])
    public_safe(payload)
    return payload

def render(report, selection, output):
    payload=select(report,selection);output.mkdir(parents=True,exist_ok=True)
    payload['renderer_sources']=[dict(label=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in [HERE/'single_layer.py',HERE/'semantic_tree.py',HERE/'metric_completion.py',HERE/'single-layer-app.js',HERE/'single-layer-style.css',HERE/'single-layer-template.html']]
    (output/'selected-layer-data.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':'))+'\n')
    html=(HERE/'single-layer-template.html').read_text().replace('/*LAYER_STYLE*/',(HERE/'single-layer-style.css').read_text()).replace('/*LAYER_APP*/',(HERE/'single-layer-app.js').read_text()).replace('<!--LAYER_DATA-->',encoded(payload))
    (output/'index.html').write_text(html)
    return payload

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--selection',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();payload=render(json.loads(a.report.read_text()),json.loads(a.selection.read_text()),a.output)
    print(json.dumps(dict(events=len(payload['events']),operators=payload['operator_count'],html_bytes=(a.output/'index.html').stat().st_size)))

if __name__=='__main__':main()
