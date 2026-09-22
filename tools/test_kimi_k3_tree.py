"""Cross-map root's generated tree against the independent arithmetic ledger.

This is deliberately not a test copied from root's expressions: it compares
every independently derived leaf sum to root's separately written tree and
checks exhaustive, unique ownership on both sides.
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
root_path=HERE/'kimi_k3_tree/ledger.py'
spec=importlib.util.spec_from_file_location('root_k3_ledger',root_path)
root=importlib.util.module_from_spec(spec)
spec.loader.exec_module(root)
root_data=root.build_ledger()
ind=json.loads((HERE/'kimi_k3_tree/audit-reference.json').read_text())

mapping={
    '1':['embedding_lookup'],
    '2.1a':['attnres_attention_score_norm'],
    '2.1b':['attnres_attention_score_dot'],
    '2.1c':['attnres_attention_softmax'],
    '2.1d':['attnres_attention_weighted_mix'],
    '2.2':[],  # Snapshot copy: additional explicit non-FLOP leaf in root tree.
    '2.3':['input_norm'],
    '2.5':['prefix_attention_add'],
    '2.6a':['attnres_ffn_score_norm'],
    '2.6b':['attnres_ffn_score_dot'],
    '2.6c':['attnres_ffn_softmax'],
    '2.6d':['attnres_ffn_weighted_mix'],
    '2.7':['post_attention_norm'],
    '2.9':['prefix_ffn_add'],
    'K1':['kda_qkv','kda_output_gate_proj'],
    'K2':['kda_forget_a','kda_forget_b'],
    'K3':['kda_beta_proj'],
    'K4':['kda_depthwise_conv4'],
    'K5':['kda_qkv_silu'],
    'K6':['kda_qk_l2norm','kda_query_scale'],
    'K7':['kda_forget_gate_to_alpha','kda_exp_A_once_per_layer','kda_beta_sigmoid'],
    'K8a':['kda_state_decay'],
    'K8b':['kda_state_read_prediction','kda_delta_subtract_beta'],
    'K8c':['kda_rank_one_state_update'],
    'K8d':['kda_state_read_output'],
    'K9':['kda_output_rmsnorm','kda_output_sigmoid_multiply'],
    'K10':['kda_output_proj'],
    'A1':['mla_q_a','mla_kv_a'],
    'A2':['mla_latent_norms'],
    'A3':['mla_q_b'],
    'A4':['mla_kv_b_expand'],
    'A5':['mla_rope'],
    'A6a':['mla_qk','mla_score_scale'],
    'A6b':['mla_softmax'],
    'A6c':['mla_pv'],
    'A7':['mla_output_gate_proj'],
    'A8':['mla_output_sigmoid_multiply'],
    'A9':['mla_output_proj'],
    'D1':['dense_gate_up'],
    'D2':['dense_situ'],
    'D3':['dense_down'],
    'M1':['moe_router_gemm','moe_router_scalar'],
    'M2':['moe_latent_down'],
    'M3a':[],  # Dispatch is an explicit additional non-FLOP root leaf.
    'M3b':['moe_routed_gate_up'],
    'M3c':['moe_routed_situ'],
    'M3d':['moe_routed_down'],
    'M3e':['moe_weighted_combine'],
    'M4':['moe_latent_norm'],
    'M5':['moe_latent_up'],
    'M6a':['moe_shared_gate_up'],
    'M6b':['moe_shared_situ'],
    'M6c':['moe_shared_down'],
    'M7':['moe_shared_routed_add'],
    '3a':['attnres_final_score_norm'],
    '3b':['attnres_final_score_dot'],
    '3c':['attnres_final_softmax'],
    '3d':['attnres_final_weighted_mix'],
    '4':['final_norm'],
    '5':['last_token_lm_head'],
}

nodes=list(root.walk(root_data['tree']))
assert len({n['id'] for n in nodes})==len(nodes),'Root contains duplicate IDs'
root_leaves={n['id']:n for n in nodes if not n['children']}
assert set(root_leaves)==set(mapping),{
    'unmapped_root':sorted(set(root_leaves)-set(mapping)),
    'mapping_without_root':sorted(set(mapping)-set(root_leaves)),
}
independent_use=Counter(k for names in mapping.values() for k in names)
assert set(independent_use)==set(ind['leaves']),{
    'unmapped_independent':sorted(set(ind['leaves'])-set(independent_use)),
    'mapping_without_independent':sorted(set(independent_use)-set(ind['leaves'])),
}
assert all(n==1 for n in independent_use.values()),'Independent leaf double-counted'

results=[]
for id,names in mapping.items():
    actual=root_leaves[id]['flops']
    expected=sum(ind['leaves'][name]['flops'] for name in names)
    assert actual==expected,(id,actual,expected,names)
    results.append(dict(root_leaf=id,root_title=root_leaves[id]['title'],
                        independent_leaves=names,flops=actual,passed=True))
for n in nodes:
    if n['children']:
        assert n['flops']==sum(c['flops'] for c in n['children']),(n['id'],'subtotal')
assert sum(n['flops'] for n in root_leaves.values())==ind['total_flops']==root_data['tree']['flops']

# Layer schedule is recomputed independently from explicit layer families.
cfg=json.loads((HERE.parent/'docs/kimi-k3-flops/config.json').read_text())['text_config']
for row in root_data['layers']:
    i=row['index']
    assert row['checkpoint_layer']==i+1
    assert row['attention']==('KDA' if i+1 in cfg['linear_attn_config']['kda_layers'] else 'MLA')
    assert row['feed_forward']==('dense' if i==0 else 'latent MoE')
    assert row['snapshot']==(i in [0,12,24,36,48,60,72,84])
    assert row['attention_residual_add']==(i not in [0,12,24,36,48,60,72,84])
assert sum(r['attention_candidates'] for r in root_data['layers'])==492
assert sum(r['mlp_candidates'] for r in root_data['layers'])==501

# Compare parameter totals and all groupings, even when ownership is split differently.
pm={
    'embedding':['embedding'], 'lm_head':['lm_head'],
    'layer_norms':['decoder_input_post_norms'],
    'attn_res':['decoder_attnres_score_norm_and_proj','final_attnres_score_norm_and_proj'],
    'final_norm':['final_norm'],
    'kda_forget':['kda_forget_a_b'], 'kda_beta':['kda_beta'],
    'kda_conv':['kda_conv'], 'kda_decay':['kda_A_log_runtime','kda_dt_bias'],
    'kda_norm':['kda_output_norm'],
    'mla_norm':['mla_query_kv_norm'],
    'dense':['dense_ffn'],'router':['moe_router_and_correction'],
    'routed':['moe_all_routed_experts'],'shared':['moe_shared_experts'],
}
rp={p['key']:p['count'] for p in root_data['parameters']}
ip=ind['parameter_elements']
for key,names in pm.items():
    assert rp[key]==sum(ip[x] for x in names),(key,'parameter group')
assert rp['kda_qkvg']+rp['kda_output']==ip['kda_qkv_outputgate_oproj']
assert rp['mla_a']+rp['mla_q']+rp['mla_kv']==ip['mla_q_a_b']+ip['mla_kv_a_b']
assert rp['mla_gate']+rp['mla_output']==ip['mla_output_gate_and_projection']
assert rp['latent']+rp['latent_norm']==ip['moe_latent_projections_and_norm']
assert root_data['parameter_total']==ind['parameter_total_runtime_A_log']
assert root_data['checkpoint_inactive_a_log']==2208

report=dict(passed=True,root_nodes=len(nodes),root_leaves=len(root_leaves),
            independent_leaves=len(ind['leaves']),total_flops=ind['total_flops'],
            parameter_total=root_data['parameter_total'],leaf_mapping=results)
# Audit result is printed; no generated fixture is rewritten.
print(json.dumps({k:v for k,v in report.items() if k!='leaf_mapping'},indent=2))
