"""Kimi K3 text-prefill logical operator ledger; integer arithmetic only.

This is a declared mathematical work model, not a kernel launch/timing report.
All matrix products use 2*m*k*n, scalar reductions use n-1 additions.
The KDA core is sequential-equivalent and MLA uses expanded causal attention.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "docs/kimi-k3-flops/config.json"
HF_REV = "f831ab66814297da540d832a5235f8e904f29d06"
SG_REV = "cc1ecdadaf37e5d0a912ba3a68047a89dc453e1c"
HF = f"https://huggingface.co/moonshotai/Kimi-K3/blob/{HF_REV}"
SG = f"https://git.luchentech.com/maas/sglang/-/blob/{SG_REV}"


def shape(*dims):
    return '<span class="shape">[' + ', '.join(str(d) for d in dims) + ']</span>'


def num(n):
    return f"{n:,}"


def node(id, title, role, input, output, state="No learned state", *, flops=0,
         formula="", note="", auxiliary="", children=None, kind="", repeat="", source=""):
    children = children or []
    if children:
        assert flops == 0, (id, "parents must derive their total from children")
        flops = sum(c["flops"] for c in children)
    assert isinstance(flops, int) and flops >= 0
    return dict(id=id, title=title, role=role, input=input, output=output, state=state,
                flops=flops, formula=formula, note=note, auxiliary=auxiliary,
                children=children, kind=kind, repeat=repeat, source=source)


def build_ledger(tokens=100_000):
    cfg = json.loads(CONFIG.read_text())["text_config"]
    T = tokens
    assert isinstance(T, int) and T > 0
    H, N, V = cfg["hidden_size"], cfg["num_hidden_layers"], cfg["vocab_size"]
    E, K, Z, I = (cfg[k] for k in ("num_experts", "num_experts_per_token", "routed_expert_hidden_size", "moe_intermediate_size"))
    DENSE, SHARED = cfg["intermediate_size"], I * cfg["num_shared_experts"]
    lc = cfg["linear_attn_config"]
    kd_layers, ma_layers = lc["kda_layers"], lc["full_attn_layers"]
    KD, MA, MOE = len(kd_layers), len(ma_layers), N-cfg["first_k_dense_replace"]
    h, d, w = lc["num_heads"], lc["head_dim"], lc["short_conv_kernel_size"]
    P, qrank, kvrank = h*d, cfg["q_lora_rank"], cfg["kv_lora_rank"]
    ah, dq, dv = cfg["num_attention_heads"], cfg["qk_nope_head_dim"]+cfg["qk_rope_head_dim"], cfg["v_head_dim"]
    dk, extra, BS = cfg["qk_nope_head_dim"], cfg["qk_rope_head_dim"], cfg["attn_res_block_size"]
    assert sorted(kd_layers + ma_layers) == list(range(1, N+1))
    assert (N,H,KD,MA,MOE,E,K,Z,I,h,d,w,P,qrank,kvrank,ah,dq,dv,BS) == (93,7168,69,24,92,896,16,3584,3072,96,128,4,12288,1536,512,96,192,128,12)
    assert ma_layers == list(range(4,93,4))+[93]
    assert lc["use_full_rank_gate"] and cfg["mla_use_nope"] and cfg["mla_use_output_gate"]
    assert cfg["latent_moe_use_norm"] and cfg["num_expert_group"] == cfg["topk_group"] == 1
    assert cfg["routed_scaling_factor"] == 1 and cfg["num_nextn_predict_layers"] == 0
    assert (cfg["activation_situ_beta"],cfg["activation_situ_linear_beta"]) == (4,25)
    TH = shape(T,H)
    TK = shape(T,h,d)
    pairs = T*(T+1)//2
    # Parameter objects are logical unpacked learned elements. Quantization
    # metadata and runtime replicas are deliberately outside this ledger.
    parameters = []
    def param(key, component, dims, count, formula, note=""):
        parameters.append(dict(key=key,component=component,shape=dims,count=count,formula=formula,note=note))
        return count
    param("embedding", "Token embedding", shape(V,H), V*H, f"{num(V)} × {num(H)}")
    param("kda_qkvg", "KDA Q/K/V + full-rank output gate", "four matrices per KDA layer: "+shape(H,P), KD*4*H*P, f"{KD} × 4 × {num(H)} × {num(P)}")
    param("kda_forget", "KDA low-rank forgetting gate", shape(H,d)+" + "+shape(d,P), KD*(H*d+d*P), f"{KD} × ({num(H)} × {d} + {d} × {num(P)})")
    param("kda_beta", "KDA beta projection", shape(H,h), KD*H*h, f"{KD} × {num(H)} × {h}")
    param("kda_conv", "KDA Q/K/V depthwise convolution", "three weight arrays "+shape(P,w), KD*3*P*w, f"{KD} × 3 × {num(P)} × {w}")
    param("kda_decay", "KDA decay parameters", "active A-log "+shape(h)+" + delta-time bias "+shape(P), KD*(h+P), f"{KD} × ({h} + {num(P)})", "The checkpoint stores 128 A-log values per layer; SGLang uses the first 96. The inactive tail is reconciled separately.")
    param("kda_norm", "KDA output RMSNorm", "one shared-across-heads vector "+shape(d), KD*d, f"{KD} × {d}")
    param("kda_output", "KDA output projection", shape(P,H), KD*P*H, f"{KD} × {num(P)} × {num(H)}")
    param("mla_a", "MLA query/KV down projections", shape(H,qrank+kvrank+extra), MA*H*(qrank+kvrank+extra), f"{MA} × {num(H)} × ({num(qrank)} + {kvrank} + {extra})")
    param("mla_q", "MLA query expansion", shape(qrank,ah*dq), MA*qrank*ah*dq, f"{MA} × {num(qrank)} × {ah} × {dq}")
    param("mla_kv", "MLA key/value expansion", shape(kvrank,ah*(dk+dv)), MA*kvrank*ah*(dk+dv), f"{MA} × {kvrank} × {ah} × ({dk} + {dv})", "Count this weight object once, including if a backend uses absorbed matrix views.")
    param("mla_gate", "MLA output-gate projection", shape(H,ah*dv), MA*H*ah*dv, f"{MA} × {num(H)} × {ah} × {dv}")
    param("mla_output", "MLA output projection", shape(ah*dv,H), MA*ah*dv*H, f"{MA} × {ah} × {dv} × {num(H)}")
    param("mla_norm", "MLA latent norms", shape(qrank)+" + "+shape(kvrank), MA*(qrank+kvrank), f"{MA} × ({num(qrank)} + {kvrank})")
    param("dense", "Layer 0 dense SiTU MLP", shape(H,2*DENSE)+" + "+shape(DENSE,H), 3*H*DENSE, f"3 × {num(H)} × {num(DENSE)}")
    param("router", "Latent-MoE router and correction bias", shape(H,E)+" + "+shape(E), MOE*(H*E+E), f"{MOE} × ({num(H)} × {E} + {E})")
    param("routed", "All 896 routed experts per MoE layer", "each: "+shape(Z,2*I)+" + "+shape(I,Z), MOE*E*3*Z*I, f"{MOE} × {E} × 3 × {num(Z)} × {num(I)}", "All experts are stored; only top-16 per token contribute to routed expert FLOPs.")
    param("latent", "Common latent down/up projections", shape(H,Z)+" + "+shape(Z,H), MOE*2*H*Z, f"{MOE} × 2 × {num(H)} × {num(Z)}")
    param("latent_norm", "Latent-MoE output RMSNorm", shape(Z), MOE*Z, f"{MOE} × {num(Z)}")
    param("shared", "Always-active shared MLP", shape(H,2*SHARED)+" + "+shape(SHARED,H), MOE*3*H*SHARED, f"{MOE} × 3 × {num(H)} × ({cfg['num_shared_experts']} × {num(I)})", "Two expert units form one widened MLP at full hidden width; this branch is not routed.")
    param("layer_norms", "Attention/MLP input RMSNorms", "two "+shape(H)+" vectors per layer", 2*N*H, f"{N} × 2 × {num(H)}")
    param("attn_res", "Attention Residual scoring state", "187 score projections + 187 norm vectors, each "+shape(H), (2*N+1)*2*H, f"(2 × {N} + 1) × 2 × {num(H)}", "Layer 0's attention-side scorer is stored but bypassed while the bank is empty.")
    param("final_norm", "Final RMSNorm", shape(H), H, num(H))
    param("lm_head", "Untied language-model head", shape(H,V), H*V, f"{num(H)} × {num(V)}", "Logical input→output orientation; the checkpoint stores the transposed [163840, 7168] tensor.")
    pd = {p["key"]:p for p in parameters}
    def state(key, copies=1):
        p=pd[key]
        count=p["count"]//copies
        assert p["count"]%copies==0
        return p["shape"] + f'<br><span class="flow-count">{num(count)} learned elements'+(" per layer" if copies>1 else " total")+'</span>'
    def leaf(id,title,role,inp,out,key=None,copies=1,**kw):
        return node(id,title,role,inp,out,state(key,copies) if key else "No learned state",**kw)
    def agg(prefix, label, rs):
        n, candidates = len(rs),sum(rs)
        if not n:
            return node(prefix,label,"No candidate mixing while the bank is empty.",TH,TH)
        return node(prefix,label,"Score earlier block snapshots and the current block prefix; mix the original vectors across depth for each token.",
            f'{TH} current prefix + '+shape(T,"bank rows",H),TH,
            f'{n} scoring sites; each owns a {shape(H)} score vector and {shape(H)} RMSNorm vector.',
            children=[
                leaf(prefix+"a","Candidate RMSNorm","Normalize each candidate for scoring; these normalized vectors are not the mixed values.",shape(T,"R",H),shape(T,"R",H),
                    flops=T*candidates*(4*H+2),formula=f"{num(candidates)} candidate rows across sites × {num(T)} tokens × (4 × {num(H)} + 2)",note="Expanded eager-reference norm; the fused implementation can precombine learned norm and score weights."),
                leaf(prefix+"b","Learned depth scores","Apply one scalar score projection per candidate.",shape(T,"R",H),shape(T,"R"),
                    flops=T*candidates*2*H,formula=f"{num(T)} × {num(candidates)} × 2 × {num(H)}"),
                leaf(prefix+"c","Softmax over depth","Normalize scores over the candidate bank, separately for each token.",shape(T,"R"),shape(T,"R"),
                    flops=T*(4*candidates-n),formula=f"{num(T)} × (4 × {num(candidates)} − {n})",auxiliary="Maximum comparisons are outside FLOPs."),
                leaf(prefix+"d","Weighted depth mixture","Mix the original, unnormalized candidate vectors.",shape(T,"R")+" probabilities + "+shape(T,"R",H),TH,
                    flops=T*H*(2*candidates-n),formula=f"{num(T)} × {num(H)} × (2 × {num(candidates)} − {n})",note="R multiplies + R−1 adds per hidden coordinate; this is forward-pass depth state, not token KV.")],
            formula=f"{n} active sites; ΣR = {num(candidates)} per token",repeat=f"{n} aggregation sites")

    # KDA. Projection groupings correspond to SGLang fused_qkvg/b/f_a/f_b.
    kda= node("K","Kimi Delta Attention","Update a fixed-size state per sequence and head, then read it. This branch executes in 69 layers.",TH,TH,
        "KDA parameters belong only to the 69 KDA layers.",kind="branch-refresh",repeat=f"{KD} layers",children=[
        leaf("K1","Q/K/V and full-rank output-gate projections","Four full-width projections; SGLang may fuse these as one Q/K/V/g GEMM.",TH,
             "Q, K, V and g: four "+TK,"kda_qkvg",KD,flops=KD*T*2*H*4*P,formula=f"{KD} × {num(T)} × 2 × {num(H)} × (4 × {num(P)})",note="Only the forgetting gate below is low-rank. The output gate g is full-rank."),
        leaf("K2","Forgetting-gate projections","Project through a 128-wide bottleneck to one gate input per head/key coordinate.",TH,shape(T,d)+" → "+TK,"kda_forget",KD,
             flops=KD*T*2*(H*d+d*P),formula=f"{KD} × {num(T)} × 2 × ({num(H)} × {d} + {d} × {num(P)})"),
        leaf("K3","Beta projection","Generate one update-strength logit per token and head.",TH,shape(T,h),"kda_beta",KD,
             flops=KD*T*2*H*h,formula=f"{KD} × {num(T)} × 2 × {num(H)} × {h}"),
        leaf("K4","Causal depthwise Q/K/V convolution","Apply a width-four convolution independently to each projected channel.","three "+TK,"three "+TK,"kda_conv",KD,
             flops=KD*T*3*P*2*w,formula=f"{KD} × {num(T)} × 3 × {num(P)} × 2 × {w}",note="Fixed four-tap, zero-padded logical convolution; each tap uses the 2-FLOP multiply-add convention, including the padded boundary."),
        leaf("K5","Convolution SiLU","Activate all three convolution outputs.","three "+TK,"three "+TK,
             flops=KD*T*3*P*4,formula=f"{KD} × {num(T)} × 3 × {num(P)} × 4",note="SiLU: exp + add + reciprocal + multiply; sign reversal is folded into exp's argument."),
        leaf("K6","Q/K L2 normalization and query scale","L2-normalize Q and K per head; scale Q by 1/√128 before the state read.","Q and K: two "+TK,"normalized Q and K: two "+TK,
             flops=KD*T*h*(2*(3*d+1)+d),formula=f"{KD} × {num(T)} × {h} × [2 × (3 × {d} + 1) + {d}]",note="L2 norm uses sum of squares, epsilon, reciprocal square root, and coordinate multiply; it is not RMSNorm."),
        leaf("K7","Safe decay and beta gates","Turn forgetting logits into bounded log-decay and exponentiate to multiplicative decay; sigmoid the update logits.",TK+" forgetting logits + "+shape(T,h)+" beta logits",TK+" α + "+shape(T,h)+" β","kda_decay",KD,
             flops=KD*(T*(7*P+3*h)+h),formula=f"{KD} × [{num(T)} × (7 × {num(P)} + 3 × {h}) + {h}]",
             note="log α = −5 · sigmoid(exp(A-log) · (f + dt-bias)); α = exp(log α). Count exp(A-log) once per active head per request; 7 scalar operations per decay coordinate and 3 per beta."),
        node("K8","Delta-rule state update and read","Sequential-equivalent logical recurrence; prefill uses chunked kernels rather than launching this loop token by token.",
             "Q/K/V streams: three "+TK+" + α/β + "+shape(h,d,d)+" state",TK+" outputs + final "+shape(h,d,d)+" state",
             "No learned matrix here; the live recurrent state is request state.",children=[
             leaf("K8a","Decay prior state","Scale each state key row by its coordinate-specific α.",shape(h,d,d)+" prior state + "+shape(h,d)+" α",shape(h,d,d)+" decayed state",
                  flops=KD*T*h*d*d,formula=f"{KD} × {num(T)} × {h} × {d} × {d}"),
             leaf("K8b","Predict value and form correction","Read the decayed state using K; form β · (V − prediction).",shape(h,d,d)+" decayed state + K/V/β",shape(h,d)+" correction",
                  flops=KD*T*h*(2*d*d+2*d),formula=f"{KD} × {num(T)} × {h} × (2 × {d} × {d} + 2 × {d})"),
             leaf("K8c","Rank-one state update","Add the outer product of K and the correction to the decayed state.",shape(h,d)+" K and correction + decayed state",shape(h,d,d)+" updated state",
                  flops=KD*T*h*2*d*d,formula=f"{KD} × {num(T)} × {h} × 2 × {d} × {d}"),
             leaf("K8d","Read with scaled Q","Contract the updated state with Q to obtain one value vector per head.",shape(h,d,d)+" updated state + Q",shape(h,d),
                  flops=KD*T*h*2*d*d,formula=f"{KD} × {num(T)} × {h} × 2 × {d} × {d}")],
             formula=f"{KD} × {num(T)} × {h} × (7 × {d}² + 2 × {d})",note="Q/K are L2-normalized; V is convolved/activated. Child tensors show one recurrent step, repeated for every token; FLOPs include all tokens and layers. Chunk transforms, triangular solves, tiling and padded MMA are not this numerator.",repeat=f"{num(T)} steps × {KD} layers"),
        leaf("K9","Per-head RMSNorm and sigmoid output gate","Normalize the recurrent output, then multiply by sigmoid(g) from K1.",TK+" core output + "+TK+" g",TK,"kda_norm",KD,
             flops=KD*T*h*((4*d+2)+4*d),formula=f"{KD} × {num(T)} × {h} × [(4 × {d} + 2) + 4 × {d}]",note="One 128-element learned RMSNorm vector is shared across 96 heads; it is not 96 separate learned norm vectors."),
        leaf("K10","KDA output projection","Concatenate value heads and return to the model hidden width.",shape(T,P),TH,"kda_output",KD,
             flops=KD*T*2*P*H,formula=f"{KD} × {num(T)} × 2 × {num(P)} × {num(H)}")])

    scores=MA*ah*pairs
    mla = node("A","Multi-head Latent Attention","Full causal token attention in 24 layers. The tree expands K/V before attention, matching the logical prefill formulation.",TH,TH,
        "MLA parameters belong only to the 24 MLA layers.",kind="branch-reuse",repeat=f"{MA} layers",children=[
        leaf("A1","Query/KV down projections","Project hidden states to a query latent, a KV latent, and 64 shared key coordinates.",TH,
             shape(T,qrank)+" query + "+shape(T,kvrank)+" KV + "+shape(T,extra)+" key","mla_a",MA,
             flops=MA*T*2*H*(qrank+kvrank+extra),formula=f"{MA} × {num(T)} × 2 × {num(H)} × ({num(qrank)} + {kvrank} + {extra})",note="SGLang can fuse the two matrices into one 2,112-output projection."),
        leaf("A2","Query/KV latent RMSNorm","Normalize the query and KV latents independently.",shape(T,qrank)+" + "+shape(T,kvrank),shape(T,qrank)+" + "+shape(T,kvrank),"mla_norm",MA,
             flops=MA*T*((4*qrank+2)+(4*kvrank+2)),formula=f"{MA} × {num(T)} × [(4 × {num(qrank)} + 2) + (4 × {kvrank} + 2)]"),
        leaf("A3","Query expansion","Expand to 96 query heads, each retaining all 192 coordinates.",shape(T,qrank),shape(T,ah,dq),"mla_q",MA,
             flops=MA*T*2*qrank*ah*dq,formula=f"{MA} × {num(T)} × 2 × {num(qrank)} × {ah} × {dq}"),
        leaf("A4","Key/value expansion","Expand compressed KV into per-head 128-coordinate keys and values.",shape(T,kvrank),shape(T,ah,dk)+" K + "+shape(T,ah,dv)+" V","mla_kv",MA,
             flops=MA*T*2*kvrank*ah*(dk+dv),formula=f"{MA} × {num(T)} × 2 × {kvrank} × {ah} × ({dk} + {dv})",note="This expanded prefill contraction differs from the absorbed latent scan shown in the GLM reference."),
        leaf("A5","Assemble keys and retain latent cache","Append the unrotated 64 shared key coordinates to each head. No rotary rotation and no DSA selector execute.",
             shape(T,ah,dk)+" keys + "+shape(T,extra)+" shared coordinates",shape(T,ah,dq)+" effective keys; latent cache "+shape(T,kvrank+extra),
             auxiliary=f"Broadcast/concatenation and logical cache writes: {num(MA*T*(kvrank+extra))} latent-cache elements across 24 layers.",note="NoPE removes rotation, not the 64-coordinate branch. Physical backends may additionally materialize expanded keys/values."),
        node("A6","Full causal score, softmax and value accumulation","Each query attends to its entire legal prefix, including itself.",shape(T,ah,dq)+" Q/K + "+shape(T,ah,dv)+" V",shape(T,ah,dv),
             "No learned matrix in the scan.",children=[
             leaf("A6a","Causal QK and score scaling","Score every legal query/key pair at width 192, then apply one scale multiplication per score.",shape(T,ah,dq)+" Q/K",shape(ah,f"{num(pairs)} causal scores"),
                  flops=scores*(2*dq+1),formula=f"{MA} × {ah} × {num(pairs)} × (2 × {dq} + 1)",note="The causal triangle has T(T+1)/2 pairs; no dense masked upper-triangle FLOPs are charged."),
             leaf("A6b","Causal softmax","Subtract row maximum, exponentiate, sum, and normalize causal scores.","causal attention scores","causal probabilities",
                  flops=4*scores-MA*T*ah,formula=f"4 × {num(scores)} score elements − {num(MA*T*ah)} query/head rows",auxiliary="Maximum comparisons and masks are outside floating arithmetic."),
             leaf("A6c","Value accumulation","Contract causal probabilities with 128-coordinate values.","causal probabilities + "+shape(T,ah,dv),shape(T,ah,dv),
                  flops=scores*2*dv,formula=f"{MA} × {ah} × {num(pairs)} × 2 × {dv}")],formula=f"{num(pairs)} causal pairs per head and MLA layer",note="Scores are logical tensors; a fused attention kernel need not materialize them."),
        leaf("A7","Full-rank MLA output-gate projection","Produce a gate logit for every value-head coordinate from the normalized layer input.",TH,shape(T,ah,dv),"mla_gate",MA,
             flops=MA*T*2*H*ah*dv,formula=f"{MA} × {num(T)} × 2 × {num(H)} × {ah} × {dv}"),
        leaf("A8","Sigmoid and output gating","Gate attention values before the output projection.",shape(T,ah,dv)+" attention output and gate",shape(T,ah,dv),
             flops=MA*T*ah*dv*4,formula=f"{MA} × {num(T)} × {ah} × {dv} × 4",note="Three operations for sigmoid plus one output multiplication."),
        leaf("A9","MLA output projection","Return concatenated value heads to hidden width.",shape(T,ah*dv),TH,"mla_output",MA,
             flops=MA*T*2*ah*dv*H,formula=f"{MA} × {num(T)} × 2 × {ah} × {dv} × {num(H)}")])

    dense = node("D","Dense SiTU MLP","Layer 0 uses one dense MLP with intermediate width 33,792.",TH,TH,state("dense"),kind="branch-dense",repeat="1 layer",children=[
        leaf("D1","Dense merged gate/up","Produce the two dense activation branches.",TH,shape(T,2*DENSE),flops=T*2*H*2*DENSE,formula=f"{num(T)} × 2 × {num(H)} × {num(2*DENSE)}"),
        leaf("D2","Dense SiTU and multiply","Soft-bound both activation branches and multiply them.",shape(T,2*DENSE),shape(T,DENSE),flops=T*DENSE*11,formula=f"{num(T)} × {num(DENSE)} × 11",note="4·tanh(gate/4)·sigmoid(gate) × 25·tanh(up/25); one tanh counts as one scalar special-function operation."),
        leaf("D3","Dense down projection","Return the dense intermediate to hidden width.",shape(T,DENSE),TH,flops=T*2*DENSE*H,formula=f"{num(T)} × 2 × {num(DENSE)} × {num(H)}")])
    routed = node("M3","Routed experts in latent space","Only 16 of 896 experts execute per token, using width 3,584.",shape(T,Z)+" + top-16 routes",shape(T,Z),state("routed",MOE),children=[
        leaf("M3a","Dispatch latent rows","Group latent token rows by selected expert.",shape(T,Z)+" + "+shape(T,K)+" IDs",shape(T*K,Z),
             auxiliary=f"Logical input placements: {num(MOE*T*K*Z)} elements across all 92 MoE layers. Physical packing and communication depend on the backend."),
        leaf("M3b","Expert merged gate/up","For each routed assignment, produce 3,072 gate and 3,072 up coordinates.",shape(T*K,Z),shape(T*K,2*I),
             flops=MOE*T*K*2*Z*2*I,formula=f"{MOE} × {num(T)} × {K} × 2 × {num(Z)} × {num(2*I)}"),
        leaf("M3c","Expert SiTU and multiply","Apply the checkpoint's two soft bounds and gated product.",shape(T*K,2*I),shape(T*K,I),
             flops=MOE*T*K*I*11,formula=f"{MOE} × {num(T)} × {K} × {num(I)} × 11"),
        leaf("M3d","Expert down projection","Return each expert result to latent width, not full hidden width.",shape(T*K,I),shape(T*K,Z),
             flops=MOE*T*K*2*I*Z,formula=f"{MOE} × {num(T)} × {K} × 2 × {num(I)} × {num(Z)}"),
        leaf("M3e","Weighted routed combine","Weight and sum the 16 routed results for each token in latent space.",shape(T,K,Z)+" + route weights",shape(T,Z),
             flops=MOE*T*Z*(2*K-1),formula=f"{MOE} × {num(T)} × {num(Z)} × ({K} multiplies + {K-1} adds)",note="The shared branch is separate and has no router probability.")])
    shared = node("M6","Always-active shared MLP","Two shared expert units are packed into one full-width MLP with intermediate width 6,144.",TH,TH,state("shared",MOE),children=[
        leaf("M6a","Shared merged gate/up","Read the original full-width normalized hidden state.",TH,shape(T,2*SHARED),
             flops=MOE*T*2*H*2*SHARED,formula=f"{MOE} × {num(T)} × 2 × {num(H)} × {num(2*SHARED)}"),
        leaf("M6b","Shared SiTU and multiply","Apply SiTU to the widened shared intermediate.",shape(T,2*SHARED),shape(T,SHARED),
             flops=MOE*T*SHARED*11,formula=f"{MOE} × {num(T)} × {num(SHARED)} × 11"),
        leaf("M6c","Shared down projection","Return to full hidden width.",shape(T,SHARED),TH,
             flops=MOE*T*2*SHARED*H,formula=f"{MOE} × {num(T)} × 2 × {num(SHARED)} × {num(H)}")])
    moe=node("M","Latent MoE","Route from full-width hidden states; narrow only the routed expert branch. Shared and routed branches can overlap in execution.",TH,TH,
        "896 routed experts + one widened shared module + router + latent projections/norm per layer.",kind="branch-moe",repeat=f"{MOE} layers",children=[
        leaf("M1","Router scores and top-16 weights","Score 896 experts, select with corrected scores, then normalize the original sigmoid scores of the selected experts.",TH,shape(T,K)+" IDs + "+shape(T,K)+" weights","router",MOE,
             flops=MOE*T*(2*H*E+4*E+3*K),formula=f"{MOE} × {num(T)} × [2 × {num(H)} × {E} + 4 × {E} + 3 × {K}]",
             note="3 operations per sigmoid + correction add; selected sum (K−1), epsilon add (1), K divisions and K scale multiplies. Scale is 1 in this checkpoint; retained in the logical router convention.",auxiliary=f"{num(MOE*T*E)} score inspections and {num(MOE*T*K)} selected-ID writes; exact TopK comparison count is kernel-dependent."),
        leaf("M2","Common latent down projection","Compress the routed input once per token, shared by all selected experts.",TH,shape(T,Z),
             flops=MOE*T*2*H*Z,formula=f"{MOE} × {num(T)} × 2 × {num(H)} × {num(Z)}",note="Weight per layer: "+shape(H,Z)+f" = {num(H*Z)} elements; the opposite projection is counted at M5."),
        routed,
        leaf("M4","Routed output RMSNorm","Normalize after combining routed expert outputs, before expanding them.",shape(T,Z),shape(T,Z),"latent_norm",MOE,
             flops=MOE*T*(4*Z+2),formula=f"{MOE} × {num(T)} × (4 × {num(Z)} + 2)"),
        leaf("M5","Common latent up projection","Expand the combined routed output once per token.",shape(T,Z),TH,
             flops=MOE*T*2*Z*H,formula=f"{MOE} × {num(T)} × 2 × {num(Z)} × {num(H)}",note="Weight per layer: "+shape(Z,H)+f" = {num(Z*H)} elements."),
        shared,
        leaf("M7","Add routed and shared outputs","Sum the expanded routed result and the always-active full-width shared result.","two "+TH,TH,
             flops=MOE*T*H,formula=f"{MOE} × {num(T)} × {num(H)}",note="This addition is separate from the following block-prefix residual addition.")])

    attention_candidates=[(i+BS-1)//BS+1 for i in range(1,N)]
    mlp_candidates=[i//BS+2 for i in range(N)]
    writes=list(range(0,N,BS))
    stack=node("2","Decoder stack","Repeat the following calculation-ordered layer body for layers 0–92. Attention and feed-forward branches are selected by layer ID.",TH,TH,
        f"{N} distinct decoder-layer parameter sets; tree branch values sum over their respective layers.",kind="group",repeat=f"{N} sequential layers",children=[
        agg("2.1","Attention-side depth aggregation",attention_candidates),
        leaf("2.2","Snapshot at block entry","At layers 0, 12, …, 84, save the current raw prefix to the bank and reset the within-block prefix before attention.",TH,shape(T,"up to 8",H)+" depth bank",
             auxiliary=f"{len(writes)} snapshot copies × {num(T)} × {num(H)} = {num(len(writes)*T*H)} copied elements.",note="Aggregation reads the existing bank first. A new snapshot becomes visible to the MLP-side aggregation in the same layer."),
        leaf("2.3","Attention input RMSNorm","Normalize the attention-side mixture, or the embedding at layer 0.",TH,TH,
             flops=N*T*(4*H+2),formula=f"{N} × {num(T)} × (4 × {num(H)} + 2)",note="One learned norm vector per layer, included in the layer-norm parameter family."),
        node("2.4","Choose the attention branch","Exactly one of KDA or MLA executes in a layer.",TH,TH,"Distinct KDA and MLA layer families.",children=[kda,mla]),
        leaf("2.5","Within-block attention residual add","Add attention output to the running raw block prefix only when this layer did not reset it.",TH+" attention output + optional "+TH+" prefix",TH,
             flops=(N-len(writes))*T*H,formula=f"({N} − {len(writes)} block-entry layers) × {num(T)} × {num(H)}",note="85 additions; layer 0 and the other seven block-entry layers start from attention output alone."),
        agg("2.6","MLP-side depth aggregation",mlp_candidates),
        leaf("2.7","MLP input RMSNorm","Normalize the depth mixture before the dense or MoE path.",TH,TH,
             flops=N*T*(4*H+2),formula=f"{N} × {num(T)} × (4 × {num(H)} + 2)",note="One learned norm vector per layer, counted separately from score-normalization vectors."),
        node("2.8","Choose the feed-forward branch","Layer 0 is dense; layers 1–92 use latent MoE.",TH,TH,"Disjoint dense and sparse layer families.",children=[dense,moe]),
        leaf("2.9","Feed-forward block-prefix add","Add feed-forward output to the current raw prefix; retain this prefix for the next layer.","two "+TH,TH,
             flops=N*T*H,formula=f"{N} × {num(T)} × {num(H)}",note="The fused implementation may combine this with the routed/shared sum or delay it; the logical add is counted once.")])
    tree=node("R","Kimi K3 text target forward","One uncached 100,000-token text prefill, followed by one next-token logits row.",shape(T),shape(1,V),
        f"{num(sum(p['count'] for p in parameters))} model-owned logical learned text elements, including all 896 experts per MoE layer; vision and quantization metadata excluded.",
        kind="group",repeat="one text prefill",children=[
        leaf("1","Token embedding","Look up one hidden vector per token ID.",shape(T),TH,"embedding",auxiliary=f"{num(T*H)} embedding elements gathered; no vocabulary-wide matrix product."),
        stack,
        agg("3","Final depth aggregation",[len(writes)+1]),
        leaf("4","Final RMSNorm","Normalize the final depth mixture.",TH,TH,"final_norm",flops=T*(4*H+2),formula=f"{num(T)} × (4 × {num(H)} + 2)"),
        leaf("5","Last-token language-model head","Select the last hidden row and project once to all 163,840 vocabulary logits.",shape(1,H),shape(1,V),"lm_head",flops=2*H*V,
             formula=f"2 × {num(H)} × {num(V)}",note="One logits row for next-token generation. Requesting prompt log-probabilities would change this scope.")])
    # State cells identify learned objects even when their unique ownership is
    # assigned to a parent. Repeated displays are references, not new objects.
    by_id={n["id"]:n for n in walk(tree)}
    for prefix, sites in [("2.1",92),("2.6",93),("3",1)]:
        by_id[prefix+"a"]["state"] = shape(H)+f" learned score-normalization vector at each of {sites} executed sites; included in the Attention Residual state family."
        by_id[prefix+"b"]["state"] = shape(H,1)+f" score projection at each of {sites} executed sites; included in the same state family."
    for key in ("2.3","2.7"):
        by_id[key]["state"] = shape(H)+f" learned norm vector: {num(H)} elements per layer."
    for key in ("K8a","K8b","K8c","K8d"):
        by_id[key]["repeat"] = f"per-token state step × {num(T)} × {KD} layers"
    for key, rows, cols, suffix in [
        ("D1",H,2*DENSE,"in the dense MLP"),("D3",DENSE,H,"in the dense MLP"),
        ("M2",H,Z,"per MoE layer"),("M5",Z,H,"per MoE layer"),
        ("M3b",Z,2*I,"per routed expert; all 896 sets are owned"),
        ("M3d",I,Z,"per routed expert; all 896 sets are owned"),
        ("M6a",H,2*SHARED,"per widened shared MLP"),("M6c",SHARED,H,"per widened shared MLP")]:
        by_id[key]["state"] = shape(rows,cols)+f" weight: {num(rows*cols)} learned elements {suffix}; included in the parent parameter family."
    layers=[dict(index=i,checkpoint_layer=i+1,attention="KDA" if i+1 in kd_layers else "MLA",feed_forward="dense" if i==0 else "latent MoE",snapshot=i in writes,
                 attention_candidates=0 if i==0 else (i+BS-1)//BS+1,mlp_candidates=i//BS+2,attention_residual_add=i not in writes) for i in range(N)]
    return dict(schema_version=1,tokens=T,config_revision=HF_REV,sglang_revision=SG_REV,tree=tree,parameters=parameters,
        parameter_total=sum(p["count"] for p in parameters),checkpoint_inactive_a_log=KD*(d-h),
        layers=layers,counts=dict(kda=KD,mla=MA,dense=1,moe=MOE,heads=h,hidden=H,latent=Z,vocab=V,
        causal_pairs=pairs,snapshot_writes=len(writes),attention_candidate_sum=sum(attention_candidates),mlp_candidate_sum=sum(mlp_candidates),final_candidates=len(writes)+1),
        convention="Expanded causal MLA + sequential-equivalent KDA; 2mnk matrix products; scalar/SFU logical convention; no precision normalization or timing measurement.")


def walk(node):
    yield node
    for child in node["children"]:
        yield from walk(child)


if __name__ == "__main__":
    data=build_ledger()
    print(json.dumps({"flops":data["tree"]["flops"],"parameters":data["parameter_total"],"counts":data["counts"],"nodes":len(list(walk(data["tree"])))},indent=2))
