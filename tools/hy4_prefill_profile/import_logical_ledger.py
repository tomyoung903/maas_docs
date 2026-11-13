#!/usr/bin/env python3
"""Build a public-safe PENDING input from the source-audited logical ledger.

This never imports a timing, treats nominal chunks as observed, or enables a
work-to-event join. Global input/output nodes are explicit boundary groups.
"""
import argparse
import hashlib
import json
from pathlib import Path
from build import validate


def convert(ledger, ledger_sha):
    artifacts=[{'id':'logical-ledger','label':'HY4 source-based operator ledger (100K logical request)','sha256':ledger_sha}]
    for key,pin in ledger['source_pins'].items():
        path=pin['path']; label=path[path.index('python/'):] if 'python/' in path else Path(path).name
        artifacts.append({'id':'source-'+key,'label':label,'sha256':pin['sha256']})
    empty=lambda:{'status':'unavailable','flops_by_precision':None,'scalar_ops':None,'useful_bytes':None,'useful_bytes_note':'','dram_bytes':None,'dram_counter_artifact_id':None}
    nodes=[]
    def node(id,parent,kind,label,rank=None,layer=None,**extras):
        n={'id':id,'parent_id':parent,'kind':kind,'label':label,'rank':rank,'chunk':None if kind in {'model','rank'} else 'pending','layer':layer,'work':empty(),'work_matches_events':False,'artifact_ids':['logical-ledger'],**extras};nodes.append(n);return n
    node('model',None,'model','HY4 · one logical 100K prefill')
    for p in ledger['partitions']:
        rank=p['rank'];r=f'pp{rank}';node(r,'model','rank',f'PP{rank} · layers {p["layers"][0]}–{p["layers"][-1]}',rank=rank)
        c=r+'-pending';node(c,r,'chunk','Chunk schedule pending · whole-request logical work',rank=rank,note='One logical 100K request; no observed chunk allocation')
        for layer in p['layers']:
            node(f'{c}-layer{layer}',c,'layer',f'Layer {layer}',rank=rank,layer=layer)
        if rank in (0,3):node(c+'-boundary',c,'layer','Input boundary' if rank==0 else 'Output boundary',rank=rank,boundary=True)
    for op in ledger['operators']:
        layers=op['applicable_layer_ids']
        targets=[(next(p['rank'] for p in ledger['partitions'] if layer in p['layers']),layer) for layer in layers]
        if not layers:
            assert op['group']=='global',op['key']
            targets=[(0 if op['key']=='embedding' else 3,None)]
        for rank,layer in targets:
            parent=f'pp{rank}-pending-'+('boundary' if layer is None else f'layer{layer}')
            precision={'BF16_tensor':'bf16','FP8_tensor':'fp8','NVFP4_tensor':'nvfp4','FP32_SIMT':'fp32'}.get(op['precision'])
            is_matrix=op['work_kind']=='matrix_dot'
            assert not is_matrix or precision is not None,op['precision']
            n=node(parent+'-'+op['key'],parent,'operator',op['name'],rank=rank,layer=layer,boundary=layer is None,formula=op['formula'],note=op['note'])
            n['artifact_ids']=['logical-ledger','source-'+op['source']['source_key']]
            n['work']={'status':'source_estimate','flops_by_precision':{precision:op['per_applicable_layer_work']} if is_matrix else {},'scalar_ops':op['per_applicable_layer_work'] if op['work_kind']=='scalar_convention' else None,'useful_bytes':op['standalone_useful_boundary_bytes_per_layer'],'useful_bytes_note':('Planning-only standalone interface estimate over nominal chunks. Not observed traffic; not additive across operators. '+(op['byte_formula'] or '')) if op['standalone_useful_boundary_bytes_per_layer'] is not None else 'No verified useful-byte numerator.','dram_bytes':None,'dram_counter_artifact_id':None}
    result={'schema_version':'hy4-prefill-profile-v1','status':'pending','request':{'input_tokens':100000,'output_tokens':1,'cached_tokens':None,'wall_time_ms':None,'layer_partition':[16,21,21,20],'configuration':'Source-based baseline inventory; actual 100K capture pending','execution_coverage_complete':False,'coverage_artifact_ids':[]},'hardware':{'devices':[0,1,2,3],'compute_roofs_tflops':{},'bandwidth_roof_tb_s':None,'roof_artifact_ids':[]},'artifacts':artifacts,'nodes':nodes,'events':[], 'limitations':[
        'This draft has no measured 100K request. Coldness, actual chunk boundaries, repeated work and runtime provider identities await trace evidence.',
        'The hierarchy currently places whole-request logical work under a pending chunk node. It does not pretend one 100K kernel invocation or an observed 13-chunk schedule.',
        'Logical matrix/dot FLOPs are grouped by represented arithmetic precision. Scalar/SFU operations use a separate semantic convention; padded and repeated executed instructions are not included.',
        'The current source ledger is pinned, but live runtime source and kernel identity must match the eventual capture before work-to-event joins are admitted.',
        'Useful bytes describe standalone operator interfaces under a nominal chunk plan. Fusion, cache reuse, padding, repeated loads and routing change actual HBM traffic. Parent byte totals are intentionally unavailable.',
        'Nominal compute and HBM roofs are unselected in this pending draft. Utilization remains unavailable; no DRAM counters are present.',
        'Global input/output boundary groups are not decoder layers. Actual per-chunk logits and head-readout behavior must be observed.',
    ]}
    validate(result)
    expected=ledger['logical_full_request']['matrix_dot_flops_by_precision']
    got={}
    for n in nodes:
        for p,f in (n['work']['flops_by_precision'] or {}).items():got[p]=got.get(p,0)+f
    mapping={'BF16_tensor':'bf16','FP8_tensor':'fp8','NVFP4_tensor':'nvfp4','FP32_SIMT':'fp32'}
    assert got=={mapping[p]:v for p,v in expected.items()},(got,expected)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ledger',required=True,type=Path);p.add_argument('--output',type=Path,default=Path(__file__).with_name('pending-input.json'));a=p.parse_args()
    raw=a.ledger.read_bytes();result=convert(json.loads(raw),hashlib.sha256(raw).hexdigest());a.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(f'{len(result["nodes"])} pending nodes; zero measured events')
if __name__=='__main__':main()
