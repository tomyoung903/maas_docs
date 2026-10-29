"""Pure-Python port of DeepGEMM b4296ed SM100 layout selector.

Scope: Normal single-group FP8 E4M3 K-major A/B, BF16 output, Kernel1D1D,
128-element scaling, default block-size multiple=1. Positive M,N,K and SM count.
Matches csrc/jit_kernels/heuristics/{sm100,common,utils,runtime}.hpp.
No fitted thresholds, measured latencies or GPU calls are used by select().
"""
# Portions derived from DeepGEMM, Copyright (c) 2025 DeepSeek.
# Distributed under the MIT License; see DeepGEMM-LICENSE.
from math import ceil
import json,re

def cdiv(x,y):return (x+y-1)//y

def align(x,y):return cdiv(x,y)*y

def swizzle(x,element_size):
    return next(s for s in (128,64,32,16) if x*element_size%s==0)

def select(m,n=6144,k=1536,sms=148):
    if min(m,n,k,sms)<=0:raise ValueError('Positive dimensions and SM count required')
    candidates=[]
    for swap in (False,True):
        bms=range(16,257,16) if swap else ([32] if m<=32 else [64] if m<=64 else [128])
        bns=[128] if swap else [16]+list(range(32,(128 if k<=256 else 256)+1,32))
        for cm in (1,2):
            if swap and cm>1:continue
            for cn in (1,2):
                if cm*cn>2 or (not swap and cn>1) or sms%(cm*cn):continue
                for bm in bms:
                    if (bm//cn)%8 or cdiv(m,bm)%cm:continue
                    for bn in bns:
                        if (bn//cm)%8 or cdiv(n,bn)%cn:continue
                        if swap and bn!=128:continue
                        sfm,sfn=align(bm,128),align(bn,128)
                        if 2*(bm if swap else bn)+(sfm+sfn)//32>512:continue
                        # K-major A/B: fixed BK128 gives both swizzles128.
                        smem_cd=16*bn*2*2 if swap else bm*swizzle(bn,2)*2
                        extra=smem_cd+32*8*3+2*8*2+8+4
                        per_stage=(bm//cn+bn//cm)*128+(sfm+sfn)*4
                        stages=min((232448-extra)//per_stage,32)
                        tiles=cdiv(m,bm)*cdiv(n,bn)
                        waves=cdiv(tiles,sms)
                        # This lexicographic key matches source comparator,
                        # including preference of any single wave before multicasting.
                        key=(waves!=1,-cm*cn,waves,-(tiles%sms or sms),bm+bn,bm*bn)
                        candidates.append((key,{'bm':bm,'bn':bn,'bk':128,'stages':stages,'swap':swap,'multicast':cm*cn,'multicast_on_a':cn>1,'cm':cm,'cn':cn,'sms':sms,'tiles':tiles,'waves':waves,'tail':tiles%sms or sms,'smem_bytes':extra+stages*per_stage,'swizzle_cd':swizzle(bn,2)}))
    return min(candidates,key=lambda a:a[0])[1]

def from_trace(point):
    name=point['samples'][0]['kernels'][1]['name']
    v=list(map(int,re.findall(r'\((?:unsigned int|bool)\)(\d+)',name)))
    return {'bm':v[5],'bn':v[6],'bk':v[7],'stages':v[12],'multicast':v[15],'multicast_on_a':bool(v[16]),'sms':v[17],'swap':bool(v[18]),'swizzle_cd':v[11]}

if __name__=='__main__':
    import sys
    points=json.load(open(sys.argv[1] if len(sys.argv)>1 else 'outputs/b300-reproduction/steady_results.json'))['points']
    mismatches=[]
    for p in points:
        predicted=select(p['m'],p['n'],p['k'])
        observed=from_trace(p)
        diff={k:[v,predicted[k]] for k,v in observed.items() if v!=predicted[k]}
        if diff:mismatches.append({'m':p['m'],'diff':diff})
    print(json.dumps({'checked':len(points),'mismatches':mismatches},indent=2))
