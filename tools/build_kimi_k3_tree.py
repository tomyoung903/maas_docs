#!/usr/bin/env python3
"""Build the K3 100K text-prefill tree from a pinned, audited configuration."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from kimi_k3_tree.ledger import build_ledger, walk, shape, num, HF, HF_REV, SG, SG_REV
from kimi_k3_tree.render import render_report, format_flops
from inject_maas_annotator import expected_text

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/kimi-k3-flops"
NAME = "kimi_k3_100k_prefill_execution_tree.html"
URL = "https://tomyoung903.github.io/maas_docs/kimi-k3-flops/"+NAME
REFERENCE = "https://tomyoung903.github.io/maas_docs/glm52-flops/glm52_100k_prefill_execution_tree.html"
CONFIG_SHA = "9710e121a58d03ac92c8d6da287a19541994319afbbe6d6202af001ffd379213"


def table(headers, rows, cls=""):
    return '<table class="'+cls+'"><thead><tr>'+''.join('<th>'+x+'</th>' for x in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+str(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</tbody></table>'


def link(url,label):
    return f'<a href="{url}">{label}</a>'


def report(data):
    byid={x['id']:x for x in walk(data['tree'])}
    param_total=data['parameter_total']
    exact=data['tree']['flops']
    P=data['counts']['causal_pairs']
    kda_core=byid['K8']['flops']
    expanded_scan=24*96*P*2*(192+128)
    absorbed_scan=24*96*P*2*((512+64)+512)
    absorbed_total=exact+absorbed_scan-expanded_scan
    family_rows=[
        ['KDA + dense','0','1','KDA','Dense SiTU; intermediate 33,792'],
        ['KDA + MoE','1, 2, 4, 5, 6, …, 88, 89, 90','68','KDA','16 routed experts + widened shared MLP'],
        ['MLA + MoE','3, 7, 11, …, 91, plus 92','24','Full causal MLA; QK width 192','Same latent-MoE layout'],
        ['Total','0–92','93','69 KDA + 24 MLA','1 dense + 92 MoE'],
    ]
    pattern_rows=[]
    for first in range(0,93,12):
        last=min(first+11,92)
        names=['KDA' if l['attention']=='KDA' else '<strong>MLA</strong>' for l in data['layers'][first:last+1]]
        pattern_rows.append([f'{first}–{last}',' → '.join(names),str(first), 'Dense only at 0; otherwise MoE' if first==0 else 'MoE throughout'])
    layer_html=(
        '<p>All layer IDs on this page are <strong>zero-based</strong>. The official configuration lists attention layer IDs one-based; subtract one to obtain these IDs. '
        'Execute layers 0 through 92 in order, choosing exactly one attention branch and one feed-forward branch per layer.</p>'
        +table(['Layer family','Zero-based layer IDs','Copies','Attention','Feed-forward'],family_rows)
        +'<p>The repeated attention pattern is KDA → KDA → KDA → MLA, repeated 23 times, followed by the additional final MLA at layer 92. '
        'The table below also marks the eight Attention Residual snapshot boundaries.</p>'
        +table(['Layer block','Attention order','Snapshot before layer','Feed-forward'],pattern_rows)
        +'<div class="note">'+link('layer-map.json','Download the complete 93-layer map')+' for every layer’s attention family, feed-forward family, candidate counts, and residual-add condition.</div>'
    )
    groups=[('Token input and output',['embedding','lm_head']),
            ('Kimi Delta Attention · 69 layers',['kda_qkvg','kda_forget','kda_beta','kda_conv','kda_decay','kda_norm','kda_output']),
            ('Multi-head Latent Attention · 24 layers',['mla_a','mla_q','mla_kv','mla_gate','mla_output','mla_norm']),
            ('Feed-forward networks',['dense','router','routed','latent','latent_norm','shared']),
            ('Norms and depth aggregation',['layer_norms','attn_res','final_norm'])]
    pd={x['key']:x for x in data['parameters']}
    parameter_rows=[]
    for label,keys in groups:
        parameter_rows.append('<tr class="param-group"><th colspan="4"><span class="param-group-title">'+label+'</span></th></tr>')
        for k in keys:
            p=pd[k]
            parameter_rows.append('<tr class="param-leaf"><th scope="row" class="param-component">'+p['component']+'</th><td>'+p['shape']+
                '</td><td>'+p['formula']+('<span class="param-rule">'+p['note']+'</span>' if p['note'] else '')+
                '</td><td><span class="param-count">'+num(p['count'])+'</span></td></tr>')
    parameters_html=(
        '<p>Count each model-owned learned object once, including <strong>all 896 experts</strong> in every MoE layer. '
        'These are unpacked logical element counts in the SGLang runtime parameter layout; they are not active parameters per token, packed checkpoint bytes, VRAM, or per-rank allocations. '
        'The vision tower/projector, quantization scales, runtime caches, derived matrices, and TP replicas are outside this ledger.</p>'
        '<div class="grid"><section class="card"><div class="label">Logical text parameter state</div><div class="value">2.779484 T elements</div></section>'
        '<section class="card"><div class="label">Stored routed experts / MoE layer</div><div class="value">896</div></section>'
        '<section class="card"><div class="label">Executed routed experts / token</div><div class="value">16</div></section></div>'
        '<div class="parameter-table-scroll"><table class="parameter-table logical-parameter-table"><colgroup>'
        '<col class="param-col-component"><col class="param-col-shape"><col class="param-col-expansion"><col class="param-col-logical"></colgroup>'
        '<thead><tr><th>Component</th><th>Logical shape / object</th><th>Unique-ownership formula</th><th>Learned elements</th></tr></thead><tbody>'
        +''.join(parameter_rows)+f'<tr><th colspan="3">Logical runtime-layout text total</th><td><strong>{num(param_total)}</strong></td></tr></tbody></table></div>'
        '<div class="note"><strong>Checkpoint reconciliation:</strong> all 94 text-bearing safetensors headers and 497,052 text tensor entries were checked against the checkpoint index. '
        f'The unpacked checkpoint has {num(param_total+data["checkpoint_inactive_a_log"])} learned text elements. '
        'Each of the 69 KDA layers stores 128 A-log entries, while SGLang uses the first 96: the difference is exactly 69 × 32 = 2,208 elements. '
        'Quantization-scale tensors are identified and excluded from both learned-element totals. '+link('parameter-header-audit.json','Header audit and per-layer reconciliation')+'.</div>'
    )
    residual_html=(
        '<p>Attention Residuals reuse representations across <strong>depth for the same token</strong>. '
        'At each mixing site, normalized candidates supply scalar scores, and softmax weights mix the original candidate vectors. '
        'The ordinary input RMSNorm is then applied to the mixture. The raw within-block prefix remains a separate stream.</p>'
        +table(['Site','Executed mixtures','Candidates per token, summed over sites','Learned scoring modules'],[
            ['Before attention','92','492','93 declared; layer 0 bypasses its scorer'],
            ['Before dense/MoE','93','501','93'],
            ['After layer 92','1','9','1'],
            ['Total','186','1,002','187'],
        ])
        +'<p>For zero-based layer <span class="math-var">i</span>, the attention-side bank has ⌈<span class="math-var">i</span>/12⌉ prior snapshots. '
        'Its mixture uses that bank plus the current prefix, except layer 0 has an empty bank and skips mixing. '
        'After the possible block-entry snapshot, the MLP-side mixture has ⌊<span class="math-var">i</span>/12⌋ + 2 candidates. '
        'The final mixture has eight snapshots plus the final prefix.</p>'
        '<div class="note"><strong>Residual additions:</strong> the eight block-entry layers reset their running prefix. '
        'There are 85 attention residual additions and 93 feed-forward residual additions. '
        'Snapshot copies are memory movement; the bank belongs to the current forward pass and is not a sequence KV cache.</div>'
    )
    rollup_keys=[('K','All KDA layers'),('A','All MLA layers'),('D','Dense MLP'),('M','All latent-MoE layers'),
                 ('2.1','Attention-side depth aggregation'),('2.6','MLP-side depth aggregation'),
                 ('2.3','Attention input RMSNorms'),('2.7','MLP input RMSNorms'),
                 ('2.5','Attention block-prefix additions'),('2.9','Feed-forward block-prefix additions'),
                 ('3','Final depth aggregation'),('4','Final RMSNorm'),('5','Last-token head')]
    assert sum(byid[k]['flops'] for k,_ in rollup_keys)==exact
    rollup_html=table(['Disjoint subtree','Logical FLOPs','Exact integer FLOPs'],[
        [label,format_flops(byid[k]['flops']),num(byid[k]['flops'])] for k,label in rollup_keys
    ]+[['Root total',format_flops(exact),num(exact)]])
    convention_html=(
        '<p>The tree preserves the reference’s raw logical accounting: every floating-arithmetic leaf contributes once, parent cells are subtotals, and comparison/movement work is separate. '
        'The following conventions make this numerator reproducible. Special functions counted as one operation do not have equal hardware costs.</p>'
        +table(['Operation','Declared logical rule'],[
            ['Matrix products and dot contractions','2 × <span class="math-var">m</span> × <span class="math-var">k</span> × <span class="math-var">n</span>; one multiply-add is two FLOPs, including accumulation from zero.'],
            ['Scalar arithmetic / special functions','Add, subtract, multiply, divide, reciprocal, rsqrt, exp, and tanh each count as one. Unary signs, casts, views, and index arithmetic are excluded.'],
            ['RMSNorm of width d','4<span class="math-var">d</span> + 2: squares, sum, mean, epsilon, rsqrt, and two coordinate multiplications.'],
            ['Q/K L2 normalization','3<span class="math-var">d</span> + 1: squares, sum, epsilon, rsqrt, and output multiplication.'],
            ['Softmax over R values','4<span class="math-var">R</span> − 1; maximum comparisons remain auxiliary work.'],
            ['Weighted sums','<span class="math-var">R</span> multiplies + <span class="math-var">R</span>−1 adds per coordinate.'],
            ['Convolution','Four zero-padded taps per Q/K/V channel; 2 FLOPs per tap, including initial padding. SiLU costs four further operations.'],
            ['SiTU','11 operations per gated coordinate: 4·tanh(gate/4)·sigmoid(gate) × 25·tanh(up/25).'],
            ['Attention Residual scores','Expanded SGLang eager reference: learned RMSNorm followed by scalar score projection. Fused paths may precombine those weights and use fewer scalar operations.'],
            ['Parameter-only transforms','exp(A-log) is prepared once per active head and layer in this reference; kernels may repeat it by tile. Fixed norm/attention scale constants are already prepared.'],
            ['Non-floating work','TopK comparisons, gathers, tensor copies, cache writes, permutations, dispatch, and communication are shown separately; no GPU timing or bandwidth is inferred.'],
        ])
        +'<h3 id="parent-rollup">Additive Parent Rollup</h3><p>These subtrees are disjoint. Their exact integer values add to the root; embedding and snapshot/cache movement have zero arithmetic FLOPs.</p>'
        +rollup_html
        +'<p>'+link('ledger.json','Download the full machine-readable tree and parameter ledger')+'. Exact integers express this convention, not an exact instruction count for every implementation.</p>'
    )
    contraction_html=(
        '<p>The main value uses <strong>expanded causal MLA</strong> and a <strong>sequential-equivalent KDA recurrence</strong>. '
        'Both are specified mathematical factorizations. They establish a logical numerator; a measured execution numerator also needs the backend, kernel path, padding and precision.</p>'
        '<h3 id="mla-contraction">MLA: expanded prefill versus absorbed scan</h3>'
        '<p>At 100,000 tokens there are 5,000,050,000 causal pairs per head. K3 keeps all 192 QK coordinates even though RoPE rotation is disabled. '
        'The expanded scan uses value width 128. An absorbed formulation uses QK width 512 + 64 and accumulates 512-dimensional latent values instead.</p>'
        +table(['MLA formulation','QK width','Accumulated value width','QK + P×V scan, all 24 layers','Whole-model reference'],[
            ['Expanded causal prefill — used in this tree','192','128',f'{expanded_scan/1e15:.10f} PFLOP',f'{exact/1e15:.12f} PFLOP'],
            ['Absorbed latent scan — alternative','576','512',f'{absorbed_scan/1e15:.10f} PFLOP',f'{absorbed_total/1e15:.12f} PFLOP'],
        ])
        +'<p>For this full T-query/T-key cold prefill, expanding K/V before attention and performing query absorption plus value expansion afterward use the same total projection arithmetic. '
        'The scan alone changes by 17.6948969472 PFLOP. The two whole-model values are alternatives; they must not be added. '
        'Neither value establishes which path an unspecified deployment uses.</p>'
        '<h3 id="kda-contraction">KDA: the counted recurrence</h3>'
        '<p>Per head, let <span class="math-mat">S</span> be the 128 × 128 state, '
        '<span class="math-vec">α</span> the 128-coordinate decay, and <span class="math-var">β</span> the scalar update strength. '
        'Only Q and K are L2-normalized. The value vector is the convolution-plus-SiLU result.</p>'
        +table(['Logical operation','Equation','Operations per token/head'],[
            ['Decay','<span class="math-mat">D</span> = diag(<span class="math-vec">α</span>) <span class="math-mat">S</span><sub>prev</sub>','128²'],
            ['Predict / correct','<span class="math-vec">u</span> = <span class="math-var">β</span> (<span class="math-vec">v</span> − <span class="math-mat">D</span><sup>T</sup><span class="math-vec">k</span>)','2 × 128² + 2 × 128'],
            ['Update','<span class="math-mat">S</span> = <span class="math-mat">D</span> + <span class="math-vec">k</span><span class="math-vec">u</span><sup>T</sup>','2 × 128²'],
            ['Read','<span class="math-vec">o</span> = <span class="math-mat">S</span><sup>T</sup><span class="math-vec">q</span><sub>scaled</sub>','2 × 128²'],
        ])
        +f'<p>The 69-layer recurrence subtotal is {num(kda_core)} FLOPs ({kda_core/1e15:.10f} PFLOP). '
        'Projection, convolution, normalization, gate and query-scale leaves are separate. The state is fixed-size per sequence/head; MLA token history still grows with context.</p>'
        '<div class="note"><strong>Chunked prefill boundary:</strong> KDA prefill evaluates an equivalent chunked algorithm with intra-chunk gated products, transforms/solves, inter-chunk state propagation and outputs. '
        'Its executed arithmetic differs from the recurrence above and depends on kernel implementation and tiling. '
        'This page does not substitute an approximate chunk formula for a verified executed-kernel count, and does not add both formulations.</div>'
        '<h3 id="mfu-handoff">MFU and precision handoff</h3>'
        '<p>The GLM reference includes a separately verified H200 precision view. This K3 page has no matching runtime capture, so it reports raw logical work without an FP8-equivalent conversion. '
        'A checkpoint quantization format alone does not establish operand precision, accumulation, kernels, elapsed time, or peak-throughput normalization. '
        'If this logical numerator is used for an MFU convention, name the selected contractions and use a separately measured, compatible denominator.</p>'
    )
    sources_html=(
        '<p>Architecture and weights are pinned independently of the moving upstream default branch. The serving implementation is pinned to the same revision used by the existing K3 architecture comparison.</p>'
        +table(['Evidence','Pinned source / validation'],[
            ['Official checkpoint configuration',link(HF+'/config.json','Moonshot Kimi-K3 config')+' · revision <code>'+HF_REV+'</code><br>SHA-256 <code>'+CONFIG_SHA+'</code>'],
            ['Official model definitions',link(HF+'/modeling_kimi_linear.py','Public text model')+'; '+link(HF+'/modeling_kimi_k3.py','Public multimodal wrapper')],
            ['SGLang model',link(SG+'/python/sglang/srt/models/kimi_k3.py','KDA, MLA, latent MoE and residual schedule')+' · <code>'+SG_REV+'</code>'],
            ['Attention Residual reference',link(SG+'/python/sglang/srt/layers/attn_residual.py','aggregate_stream_torch, AttnResidual and fused implementations')],
            ['KDA normalization / gate / kernels',link(SG+'/python/sglang/kernels/ops/attention/fla/kda.py','KDA implementation')+'; '+link(SG+'/python/sglang/kernels/ops/attention/fla/l2norm.py','L2 normalization')],
            ['Checkpoint tensor audit',link('parameter-header-audit.json','94 header hashes and every-layer counts')+'; packed routed expert shapes are unpacked logically, quantization metadata counted separately.'],
            ['Independent arithmetic and algebra',link('validation.json','Leaf-by-leaf reconciliation and algebra checks')+'; KDA matrix transition and expanded/absorbed MLA were compared on small float64 tensors.'],
            ['Preserved UI reference',link(REFERENCE+'#execution-tree','GLM-5.2 100K execution tree')+'; its complete CSS and collapse/column-toggle JavaScript are reused byte-for-byte.'],
            ['Reproducible artifacts',link('config.json','Pinned config')+' · '+link('ledger.json','Exact ledger')+' · '+link('layer-map.json','93-layer map')+' · '+link('source-audit.json','Source hashes and node anchors')],
        ])
        +'<p>Private GitLab links may require authorization. Public configuration, model code, and generated numerical evidence remain available independently. '
        'Text-only scope excludes vision processing, draft/MTP, backward work, sampling, cached-prefix reuse, all-token logits, and runtime quantization/packing overhead.</p>'
    )
    return dict(
        title='Kimi K3 100K Prefill Execution Tree',canonical=URL,
        lead='A model-level map of one 100,000-token text prefill: embedding, 93 ordered hybrid decoder layers, final depth aggregation and normalization, then one next-token output projection. '
             'Every tree row aligns tensor flow, model-owned parameter state, and a declared logical FLOP scope.',
        nav=[{'label':'MaaS Docs','href':'../'},{'label':'K3 Overview','href':'./'},
             {'label':'K3 Architecture','href':'../k3-vs-glm53-architecture/'},
             {'label':'100K Prefill Tree','href':NAME},
             {'label':'GLM-5.2 Reference','href':'../glm52-flops/glm52_100k_prefill_execution_tree.html'},
             {'label':'Evidence','href':'#sources'},{'label':'Public URL','href':URL}],
        overview=[{'label':label,'href':'#'+id,'depth':depth} for label,id,depth in [
            ('Execution Tree','execution-tree',1),('Layer Families','layer-families',1),('Logical Parameters','parameter-ledger',1),
            ('Depth Aggregation','depth-aggregation',1),('Counting Convention','accounting',1),('Parent Rollup','parent-rollup',2),
            ('Contraction Choices','contractions',1),('MLA Formulation','mla-contraction',2),('KDA Recurrence','kda-contraction',2),
            ('MFU Handoff','mfu-handoff',2),('Evidence & Audit','sources',1)]],
        cards=[{'label':'prefill input','value':'100,000 token IDs'},
               {'label':'decoder stack','value':'93 ordered layers'},
               {'label':'attention families','value':'69 KDA + 24 MLA'},
               {'label':'logical 100K FLOPs','value':format_flops(exact)},
               {'label':'MoE routing','value':'16 of 896 experts'},
               {'label':'logical text parameter state','value':'2.779484 T elements'}],
        legend=[{'label':label,'kind':kind} for label,kind in [('KDA','branch-refresh'),('MLA','branch-reuse'),('Dense SiTU','branch-dense'),('Latent MoE','branch-moe')]],
        intro_html='<p>Read from top to bottom. Indentation means logical ownership; branch subtotals cover disjoint layer families. '
                   'The stack describes a repeated layer body, not 69 KDA layers followed by 24 MLA layers. '
                   'Sibling rows follow dependency order, while independent projections and the shared MoE branch may read the same saved input and execute concurrently. '
                   'This is not a kernel launch timeline. Parent and child values must not be added twice.</p>'
                   '<div class="note"><strong>Declared reference:</strong> one cold text sequence; T = 100,000; all 93 target layers; one next-token logits row. '
                   '<strong>Expanded causal MLA + sequential-equivalent KDA + eager Attention Residual arithmetic.</strong> '
                   'The main number is logical model work under these conventions, not measured chunk-kernel work. '
                   'Matrix products use two FLOPs per multiply-add; scalar/SFU operations are counted as specified below. '
                   'TopK comparisons and memory/communication work remain separate. '
                   'Shapes use logical input→output matrix orientation; checkpoint matrices may be transposed, packed, or merged. '
                   'All parent rows start expanded, matching the GLM reference; click a parent to collapse it.</div>',
        tree=data['tree'],sections=[
            {'id':'layer-families','title':'Expand the 93 Layers','html':layer_html},
            {'id':'parameter-ledger','title':'Logical Parameter Ledger','html':parameters_html},
            {'id':'depth-aggregation','title':'Attention Residual Schedule','html':residual_html},
            {'id':'accounting','title':'Arithmetic Convention and Reconciliation','html':convention_html},
            {'id':'contractions','title':'Contraction Choices and Execution Boundary','html':contraction_html},
            {'id':'sources','title':'Evidence and Validation','html':sources_html},
        ],
        footer_html='Public URL: '+link(URL,URL)+'<br>Generated from pinned Kimi-K3 configuration and independently audited logical arithmetic. '
                    'UI preserved from the GLM-5.2 execution tree. Source and accounting boundary are recorded above.'
    )


def overview_html(data):
    style=(ROOT/'tools/kimi_k3_tree/reference-style.css').read_text()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Kimi K3 100K text-prefill execution tree with audited shapes, layer families, parameter state and logical FLOPs.">
<link rel="canonical" href="https://tomyoung903.github.io/maas_docs/kimi-k3-flops/">
<title>Kimi K3 FLOPs and Execution Tree</title><style>{style}</style></head>
<body><main><nav><a href="../">MaaS Docs</a><a href="../k3-vs-glm53-architecture/">K3 Architecture</a><a href="{NAME}#execution-tree">100K Prefill Tree</a></nav>
<h1>Kimi K3 FLOPs and Execution Tree</h1><p class="lead">A source-grounded 100,000-token text-prefill tree, using the same collapsible hierarchy, tensor-flow columns and logical parameter/FLOP presentation as the GLM-5.2 reference.</p>
<div class="grid"><section class="card"><div class="label">100K prefill tree</div><div class="value"><a href="{NAME}#execution-tree">Open the execution tree →</a></div></section>
<section class="card"><div class="label">Logical reference work</div><div class="value">{format_flops(data['tree']['flops'])}</div></section>
<section class="card"><div class="label">Hybrid decoder stack</div><div class="value">69 KDA + 24 MLA</div></section></div>
<p>The tree uses expanded causal MLA, a sequential-equivalent KDA recurrence, and an explicit scalar-arithmetic convention. Source evidence, alternative MLA contraction counts, complete parameter reconciliation and implementation boundaries are included in the page.</p>
<p><a href="ledger.json">Exact ledger</a> · <a href="layer-map.json">93-layer map</a> · <a href="config.json">Pinned configuration</a> · <a href="source-audit.json">Source audit</a></p>
</main><script defer src="../assets/maas-annotator.js" data-maas-annotator data-page-key="/kimi-k3-flops/index.html"></script></body></html>'''


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    actual=hashlib.sha256((OUT/'config.json').read_bytes()).hexdigest()
    assert actual==CONFIG_SHA, 'Pinned config changed; re-audit before generating.'
    data=build_ledger()
    rendered={NAME:render_report(report(data)), 'index.html':overview_html(data),
              'ledger.json':json.dumps(data,indent=2,ensure_ascii=False)+'\n',
              'layer-map.json':json.dumps(data['layers'],indent=2,ensure_ascii=False)+'\n'}
    for name,body in rendered.items():
        path=OUT/name
        if name.endswith('.html'):
            body=body.replace('class="math-vec"','class="math-var math-vec"')
            body=body.replace('class="math-mat"','class="math-func math-mat"')
            body=expected_text(path,body)
        if args.check:
            assert path.read_text()==body, f'{name} is stale; regenerate'
        else:
            path.write_text(body)
    print(f'{"Verified" if args.check else "Generated"} {len(rendered)} files; {data["tree"]["flops"]:,} logical FLOPs; {data["parameter_total"]:,} logical learned text elements.')


if __name__=='__main__':
    main()
