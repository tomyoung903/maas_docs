#!/usr/bin/env python3
"""Rebuild the source-informed B300 GEMM model from saved measurements.

Run: python3 source/model.py --root .
Dependencies: Python3, numpy, scipy, matplotlib. No GPU/network needed.
Fit selection was exploratory: CV is internal validation, not an untouched test.
"""
import argparse,csv,json,math
from pathlib import Path
import numpy as np
from scipy.optimize import nnls
from selector import select

# NVIDIA HGX B300: 72 PFLOP/s sparse FP8 per eight-GPU system;
# dense throughput is half the sparse figure. This is an advertised reference,
# not a measurement of the rental GPU's clock-dependent maximum.
PEAK_DENSE_FP8_FLOPS = 72e15 / 2 / 8
PEAK_SOURCE = 'https://www.nvidia.com/en-us/data-center/hgx/'
PEAK_HBM_BYTES_PER_SECOND = 7.7e12
HBM_PEAK_SOURCE = 'https://dam-cdn.nvd.orangelogic.com/AssetLink/1k0p832eq8r5ca0u5383ie5o4tp3bst1.pdf'

def metrics(pred,y):
    e=pred-y; r=e/y
    return dict(mae_us=float(np.mean(abs(e))),rmse_us=float(np.mean(e**2)**.5),mape_pct=float(np.mean(abs(r))*100),median_ape_pct=float(np.median(abs(r))*100),p95_ape_pct=float(np.quantile(abs(r),.95)*100),max_ape_pct=float(max(abs(r))*100),rms_relative_pct=float(np.mean(r**2)**.5*100),relative_mse=float(np.mean(r**2)),r2=float(1-np.sum(e**2)/np.sum((y-y.mean())**2)))

def fit(X,y):
    # Relative squared error gives each shape comparable influence.
    return nnls(X/y[:,None],np.ones(len(y)))[0]

def evaluate(X,y,first):
    coef=fit(X,y);p=X@coef
    result=dict(coefficients=coef.tolist(),fit=metrics(p,y))
    n=len(y)
    for mode,labels in [('interleaved_cv',np.arange(n)%5),('blocked_cv',np.arange(n)*5//n)]:
        cv=np.zeros(n);folds=[]
        for fold in range(5):
            train=labels!=fold;test=~train
            cf=fit(X[train],y[train]);cv[test]=X[test]@cf
            folds.append(dict(test_indices=np.flatnonzero(test).tolist(),coefficients=cf.tolist(),**metrics(cv[test],y[test])))
        result[mode]=dict(**metrics(cv,y),folds=folds,predictions_us=cv.tolist())
    first_coef=fit(X,first)
    result['first_fit_to_steady']=dict(coefficients=first_coef.tolist(),**metrics(X@first_coef,y))
    return result,p

def main(root):
    payload=json.loads((root/'measurements.json').read_text());points=payload['points']
    rows=[]
    for p in points:
        cfg=select(p['m'],p['n'],p['k'],payload['metadata']['sm_count'])
        assert all(cfg[k]==v for k,v in p['observed_config'].items()),(p['m'],cfg,p['observed_config'])
        y=np.array(p['steady_gemm_samples_us']);z=np.array(p['first_gemm_samples_us'])
        assert len(y)==len(z)==30 and np.all(y>0)
        rows.append(dict(m=p['m'],n=p['n'],k=p['k'],**cfg,gemm_mean_us=float(y.mean()),gemm_sd_us=float(y.std(ddof=1)),gemm_se_us=float(y.std(ddof=1)/np.sqrt(len(y))),gemm_p10_us=float(np.quantile(y,.1)),gemm_p90_us=float(np.quantile(y,.9)),first_mean_us=float(z.mean())))
    m=np.array([r['m'] for r in rows]);y=np.array([r['gemm_mean_us'] for r in rows]);first=np.array([r['first_mean_us'] for r in rows]);w=np.array([r['waves'] for r in rows]);tiles=np.array([r['tiles'] for r in rows]);bm=np.array([r['bm'] for r in rows]);bn=np.array([r['bn'] for r in rows]);swap=np.array([r['swap'] for r in rows]);q=w*bm*bn/128;u=np.ones(len(y))
    X=np.c_[u,q*swap,q*(1-swap)];linearX=np.c_[u,m];tail=tiles/148-(w-1);X4=np.c_[u,tail,q*swap,q*(1-swap)]
    main,p=evaluate(X,y,first);linear,pl=evaluate(linearX,y,first);extended,p4=evaluate(X4,y,first)
    for i,r in enumerate(rows):
        r.update(predicted_us=float(p[i]),linear_us=float(pl[i]),tail_model_us=float(p4[i]),residual_us=float(p[i]-y[i]),residual_pct=float((p[i]/y[i]-1)*100))
        useful_flops=2*r['m']*r['n']*r['k']
        achieved_flops=useful_flops/(r['gemm_mean_us']*1e-6)
        r.update(useful_gemm_flops=useful_flops,achieved_tflops=achieved_flops/1e12,compute_utilization_pct=100*achieved_flops/PEAK_DENSE_FP8_FLOPS)
        # User-requested cold-input payload assumption: one complete FP8 read
        # of each input per GEMM and one BF16 output write, with no C read.
        # This is not a counter-derived measurement of physical HBM traffic.
        read_bytes=r['m']*r['k']+r['n']*r['k']
        write_bytes=2*r['m']*r['n']
        total_bytes=read_bytes+write_bytes
        bandwidth=total_bytes/(r['gemm_mean_us']*1e-6)
        r.update(assumed_hbm_read_bytes=read_bytes,assumed_hbm_write_bytes=write_bytes,assumed_hbm_total_bytes=total_bytes,assumed_hbm_tb_s=bandwidth/1e12,assumed_hbm_utilization_pct=100*bandwidth/PEAK_HBM_BYTES_PER_SECOND)
    summary=dict(schema='b300-deepgemm-model-v1',measurement=payload['metadata'],n_shapes=len(rows),n_samples=len(rows)*30,primary=main,linear=linear,tail_sensitivity=extended,repeat_run=metrics(first,y),within_run=dict(median_sd_us=float(np.median([r['gemm_sd_us'] for r in rows]))),effective_sm_tflops=[2*128*1536/(b*1e-6)/1e12 for b in main['coefficients'][1:]],source_selector_matches=len(rows),max_absolute_error=max(rows,key=lambda r:abs(r['residual_us'])),max_relative_error=max(rows,key=lambda r:abs(r['residual_pct'])),anchors=[r for r in rows if r['m'] in [1,100,500,1000,2000,5000,10000]],rows=rows)
    summary['compute_utilization']=dict(peak_dense_fp8_flops=PEAK_DENSE_FP8_FLOPS,peak_source=PEAK_SOURCE,peak_derivation='72 PFLOP/s sparse per system / 2 / 8 GPUs = 4.5 PFLOP/s dense per GPU',formula='100 * 2*M*N*K / (gemm_mean_us * 1e-6 * peak_dense_fp8_flops)',meaning='Useful dense GEMM throughput / advertised dense FP8 peak; not an SM-active or Tensor Core hardware counter',peak_verified_date='2026-10-30')
    summary['assumed_hbm_utilization']=dict(peak_hbm_bytes_per_second=PEAK_HBM_BYTES_PER_SECOND,peak_source=HBM_PEAK_SOURCE,peak_source_page=5,peak_verified_date='2026-10-30',formula='100 * (M*K + N*K + 2*M*N) / (gemm_mean_us * 1e-6 * peak_hbm_bytes_per_second)',assumptions=['Each FP8 input element is read from HBM once per GEMM invocation','Each BF16 output element is written once; no previous output is read','No input data persists in cache across invocations; perfect reuse after the first read within an invocation'],exclusions=['Scale metadata','Padding and transaction granularity','Additional input fetches or writeback overhead'],meaning='Assumed logical tensor-payload bandwidth / nominal HBM peak, not measured physical HBM traffic')
    (root/'model.json').write_text(json.dumps(summary,indent=2)+'\n')
    with (root/'predictions.csv').open('w',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    draw(root,rows,main,linear)
    print(json.dumps({k:summary[k] for k in ['n_shapes','effective_sm_tflops','source_selector_matches']}))
    print('primary',main['coefficients'],main['fit'])
    print('blocked CV',{k:v for k,v in main['blocked_cv'].items() if k not in ('folds','predictions_us')})
    return summary

def draw(root,rows,main,linear):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'axes.titleweight':'bold','axes.labelcolor':'#26384b','text.color':'#152737','svg.fonttype':'none'})
    m=np.array([r['m'] for r in rows]);y=np.array([r['gemm_mean_us'] for r in rows]);p=np.array([r['predicted_us'] for r in rows]);pl=np.array([r['linear_us'] for r in rows]);er=np.array([r['residual_us'] for r in rows]);sw=np.array([r['swap'] for r in rows]);first=np.array([r['first_mean_us'] for r in rows])
    def save(fig,name):
        fig.savefig(root/f'{name}.svg',bbox_inches='tight');fig.savefig(root/f'{name}.png',dpi=180,bbox_inches='tight');plt.close(fig)
    fig,a=plt.subplots(figsize=(12,7))
    a.plot(m,pl,color='#9ba7b0',lw=1.3,label='Straight-line baseline')
    a.plot(m,p,color='#dc7834',lw=1.7,label='Tile-wave model')
    a.scatter(m,y,s=15,color='#087d91',label='Measured GEMM mean',zorder=3)
    a.set_xscale('log');a.set_xlim(.85,12500);a.set_ylim(0,70)
    a.set_xlabel('M (rows)');a.set_ylabel('GEMM duration (µs)');a.grid(alpha=.18)
    right=a.twinx();purple='#7c3a9f';green='#397a36'
    utilization=np.array([r['compute_utilization_pct'] for r in rows])
    right.plot(m,utilization,color=purple,lw=1.7,ls='--',label='Compute utilization (right axis)')
    hbm=np.array([r['assumed_hbm_utilization_pct'] for r in rows])
    right.plot(m,hbm,color=green,lw=1.7,ls='-.',label='Assumed HBM utilization (right axis)')
    right.set_ylim(0,100);right.set_yticks(np.arange(0,101,20))
    right.set_ylabel('Utilization (% of respective nominal peak)',color='#26384b',labelpad=12)
    right.spines['right'].set_visible(True)
    right.scatter([m[-1]],[utilization[-1]],s=26,color=purple,zorder=4)
    right.annotate(f'Compute at M = 10,000: {utilization[-1]:.1f}%',xy=(m[-1],utilization[-1]),xytext=(.66,.80),textcoords='axes fraction',ha='center',color=purple,fontweight='bold',arrowprops=dict(arrowstyle='->',color=purple,lw=.9))
    right.scatter([m[-1]],[hbm[-1]],s=26,color=green,zorder=4)
    right.annotate(f'HBM at M = 10,000: {hbm[-1]:.1f}%',xy=(m[-1],hbm[-1]),xytext=(.44,.40),textcoords='axes fraction',ha='center',color=green,fontweight='bold',arrowprops=dict(arrowstyle='->',color=green,lw=.9))
    handles,labels=a.get_legend_handles_labels();h2,l2=right.get_legend_handles_labels()
    a.legend(handles+h2,labels+l2,loc='upper left',framealpha=.95,fontsize=10)
    a.set_title('B300 DeepGEMM: time, compute and HBM utilization',fontsize=16,pad=32)
    a.text(.5,1.02,'All 259 measured shapes · N = 6144 · K = 1536 · 30 samples per shape',transform=a.transAxes,ha='center',fontsize=10)
    fig.text(.5,.022,'Compute: 2MNK / (t × 4.5 PFLOP/s) · HBM: (MK + NK + 2MN) / (t × 7.7 TB/s) · both × 100%\nHBM assumption: read each FP8 input once from HBM + write BF16 output once per GEMM\nLogical tensor payload only; actual HBM traffic and cache hits were not measured',ha='center',fontsize=9.5,color='#526675')
    fig.subplots_adjust(left=.085,right=.885,bottom=.20,top=.84)
    save(fig,'gemm-time-and-utilization')
    fig,ax=plt.subplots(2,2,figsize=(13,8),gridspec_kw={'height_ratios':[2.1,1]})
    for i in [0,1]:
        a=ax[0,i];a.plot(m,pl,color='#9ba7b0',lw=1.2,label='Straight-line baseline');a.plot(m,p,color='#dc7834',lw=1.5,label='Tile-wave model');a.scatter(m,y,s=11,color='#087d91',label='Measured GEMM mean',zorder=3)
        a.set_xlabel('M (rows)');a.set_ylabel('GEMM duration (µs)');a.grid(alpha=.18);a.set_title('All 259 measured shapes' if i==0 else 'Large M: switches and steps')
        if i==0:a.set_xscale('log');a.legend(loc='upper left',fontsize=9)
        else:a.set_xlim(3000,10100);a.set_ylim(20,69)
        a=ax[1,i]
        a.scatter(m,er/y*100 if i==0 else er,s=13,c=np.where(sw,'#087d91','#9d46a5'));a.axhline(0,color='#617080',lw=1);a.grid(alpha=.18);a.set_xlabel('M (rows)');a.set_ylabel('Prediction error (%)' if i==0 else 'Prediction error (µs)')
        if i==0:a.set_xscale('log')
        else:a.set_xlim(3000,10100)
    fig.suptitle('B300 DeepGEMM: fixed device cost + complete tile waves',fontsize=17,y=1.01)
    fig.text(.5,-.015,'N = 6144, K = 1536 · 148 SMs · 30 GEMM samples per shape · quantization excluded\nOrange: 3 calibrated parameters + exact source selector · residual = prediction − measurement',ha='center',fontsize=10)
    fig.tight_layout();save(fig,'model-comparison')
    fig,ax=plt.subplots(3,1,figsize=(13,8),sharex=True)
    bm=np.array([r['bm'] for r in rows]);bn=np.array([r['bn'] for r in rows]);w=np.array([r['waves'] for r in rows]);tiles=np.array([r['tiles'] for r in rows])
    ax[0].plot(m,bm,'.-',ms=3,label='Bₘ');ax[0].plot(m,bn,'.-',ms=3,label='Bₙ');ax[0].legend(ncol=2);ax[0].set_ylabel('Tile dimensions')
    ax[1].step(m,w,where='mid',label='Whole waves');ax[1].plot(m,tiles/148,alpha=.6,label='Tiles ÷ 148');ax[1].legend();ax[1].set_ylabel('Waves')
    ax[2].plot(m,[r['stages'] for r in rows],'.-',ms=3,label='Pipeline stages');ax[2].scatter(m[~sw],[6]*sum(~sw),marker='x',s=50,color='#9d46a5',label='Unswapped layout');ax[2].legend();ax[2].set_ylabel('K pipeline stages');ax[2].set_xlabel('M (rows)')
    for a in ax:a.set_xscale('log');a.grid(alpha=.18)
    fig.suptitle('The piecewise boundaries come from DeepGEMM’s selector',fontsize=16);fig.tight_layout();save(fig,'kernel-geometry')
    fig,ax=plt.subplots(1,2,figsize=(13,4))
    ix=m<=64
    ax[0].errorbar(m[ix],y[ix],yerr=np.array([r['gemm_sd_us'] for r in rows])[ix],fmt='.',ms=4,alpha=.65,color='#087d91',label='Mean ± sample SD (not CI)');ax[0].plot(m[ix],p[ix],color='#dc7834',label='Tile-wave model');ax[0].axvline(16.5,color='#9ba7b0',ls=':');ax[0].axvline(32.5,color='#9ba7b0',ls=':');ax[0].set_title('Underfilled first wave');ax[0].set_xlabel('M');ax[0].set_ylabel('GEMM duration (µs)');ax[0].legend(fontsize=8)
    ax[1].scatter(m,(first-y)/y*100,s=10,label='First run − final run');ax[1].scatter(m,er/y*100,s=9,alpha=.6,label='Model − final run');ax[1].set_xscale('log');ax[1].set_title('Model error exceeds repeat-run variation');ax[1].set_xlabel('M');ax[1].set_ylabel('Relative difference (%)');ax[1].legend(fontsize=8)
    for a in ax:a.axhline(0,color='#617080',lw=.7);a.grid(alpha=.18)
    ax[0].set_ylim(4.8,7.1);fig.tight_layout();save(fig,'residual-diagnostics')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parent.parent);args=parser.parse_args();main(args.root)
