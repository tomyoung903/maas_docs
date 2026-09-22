"""Validate equivalent KDA/MLA contractions independently using small tensors."""
import json
from pathlib import Path
import numpy as np

rng = np.random.default_rng(913)
errors = {}

# KDA: matrix transition equation versus factored decay/predict/correct/read.
dk, dv, nt = 5, 7, 11
direct = np.zeros((dk,dv))
factored = direct.copy()
maxerr = 0.
for _ in range(nt):
    q,k,v = rng.normal(size=dk),rng.normal(size=dk),rng.normal(size=dv)
    q /= np.linalg.norm(q)
    k /= np.linalg.norm(k)
    alpha = rng.uniform(.01,.99,size=dk)
    beta = rng.uniform(.01,.99)
    direct = (np.eye(dk)-beta*np.outer(k,k))@np.diag(alpha)@direct + beta*np.outer(k,v)
    decayed = alpha[:,None]*factored
    delta = beta*(v-k@decayed)
    factored = decayed + np.outer(k,delta)
    maxerr = max(maxerr,np.max(np.abs(direct-factored)),np.max(np.abs(q@direct-q@factored)))
errors['kda_recurrence_max_abs_error'] = float(maxerr)
assert maxerr < 1e-12

# MLA: expanded per-token K/V versus absorbed query and post-attention V expand.
nt,nhead,dk,dv,rank,pos = 13,3,5,7,11,2
q = rng.normal(size=(nt,nhead,dk))
qpos = rng.normal(size=(nt,nhead,pos))
latent = rng.normal(size=(nt,rank))
kpos = rng.normal(size=(nt,pos))
wk = rng.normal(size=(nhead,rank,dk))
wv = rng.normal(size=(nhead,rank,dv))
maxerr = 0.
for h in range(nhead):
    keys = latent@wk[h]
    values = latent@wv[h]
    absorbed_q = q[:,h]@wk[h].T
    scores = (q[:,h]@keys.T+qpos[:,h]@kpos.T)/(dk+pos)**.5
    other_scores = (absorbed_q@latent.T+qpos[:,h]@kpos.T)/(dk+pos)**.5
    for i in range(nt):
        ps = np.exp(scores[i,:i+1]-scores[i,:i+1].max());ps/=ps.sum()
        po = np.exp(other_scores[i,:i+1]-other_scores[i,:i+1].max());po/=po.sum()
        result = ps@values[:i+1]
        other = (po@latent[:i+1])@wv[h]
        maxerr=max(maxerr,np.max(np.abs(result-other)))
errors['mla_contractions_max_abs_error'] = float(maxerr)
assert maxerr < 1e-11
print(json.dumps(errors,indent=2))
