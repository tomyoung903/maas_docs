# DeepGEMM GEMM-only timing model: derivation and verified source facts

This is a calibrated mechanistic model for the **measured** one-GPU B300 sweep, `N=6144, K=1536, M=1…10000`. It does not claim to be a validated general predictor for arbitrary N or K. `T` is GPU GEMM kernel duration in microseconds, excluding quantization and CPU gaps. Each response variable is the mean of 30 GEMM samples at one shape.

## Source-verified part: the discrete work geometry

Let the pinned DeepGEMM selector choose configuration `C(M,N,K)=(B_M,B_N,swap,stages,cluster)`; the supplied `selector.py` ports those rules without using measured latency. It matches all 259 trace configurations, including pipeline stages and output swizzle.

Define

\[
R_M=\lceil M/B_M\rceil,\quad R_N=\lceil N/B_N\rceil,\quad Q=R_MR_N,\quad W=\lceil Q/148\rceil.
\]

`Q` is the number of logical output tiles. `W` is the maximum number of tiles assigned to a persistent CTA. The actual kernel launches 148 CTAs and its next tile index is `iteration*148+blockIdx.x`. Each measured kernel uses two-CTA clusters: 74 clusters concurrently process two logical tiles each. Therefore the wave denominator remains 148; dividing it by two without dividing the tile count would double-count the cluster effect. The kernel forbids two CTAs sharing one SM's tensor memory.

For this normal GEMM, the supposedly dynamic effective M helper returns the entire `BLOCK_M`; the special shortened-tail code is only for grouped-psum. Thus padded tail tiles still issue full-tile math. With K=1536 and BLOCK_K=128, each output tile traverses 12 K stages and issues four K=32 UMMA instructions per stage. TMA loads, scale copies/transposes, tensor-core instructions and the output epilogue are pipelined.

For **1≤M≤720**, the selector reduces to

\[
B_M=16\lceil M/48\rceil,\quad B_N=128,\quad swap=1,\quad W=1.
\]

These are source-derived breakpoints, not fitted breakpoints: 1–48 uses B_M16,49–96 uses32,…,673–720 uses240. At M721–768, the selected configuration is non-swap128×128 and W2. Above this, the portable selector is the exact concise definition; smaller normal-layout128×192/224 tiles sometimes beat the swapped candidates according to the heuristic and cause dips. The observed switch at M736 is merely the first sampled point after the true M721 boundary.

The selector compares single-wave status, multicast size, wave count, last-wave utilization, tile perimeter and tile area. It does **not** calculate exact expected cycles. Consequently it is a deterministic heuristic, not an oracle that guarantees globally fastest configuration.

## Model hypothesis: fixed device cost plus critical-path tile work

A causal starting point is a pipeline critical path:

\[
T\simeq T_{setup}+T_{first\ tile}(C)+(W-1)\,T_{steady\ tile}(C),
\]

where a steady tile's interval reflects the maximum of its overlapped TMA/memory work, tensor-core work and epilogue/store work, plus non-overlapped dependencies. We do not have hardware counters or independent N/K sweeps to estimate those terms separately. For this fixed-K experiment, collapse them into an **effective** tile service rate `P_swap` or `P_normal` and an effective intercept:

\[
\widehat T=T_0+W\frac{2B_MB_NK}{P_{\sigma}},\qquad \sigma\in\{swap,normal\}.
\]

It is useful to express the same model through utilization:

\[
\eta_{tile}=\frac{MN}{R_MR_NB_MB_N},\qquad
\eta_{wave}=\frac{Q}{148W},\qquad
\widehat T=T_0+\frac{2MNK}{148P_\sigma\eta_{tile}\eta_{wave}}.
\]

This identity explains why useful FLOPs alone miss the curve. Some math is padded away; some SM capacity is idle in the last wave; the longest persistent worker determines completion. As M grows, configuration C and W change discretely, creating a piecewise function with plateaus, steps and occasional drops. Pipeline depth falls from12 to6 across observed swapped tiles16→240 because each stage grows in shared-memory footprint.

Fitting only three positive parameters by relative least squares gives:

\[
\boxed{\widehat T(M)=5.610299+\frac{W(M)B_M(M)B_N(M)}{128}
\begin{cases}
0.01759935,&swap=1,\\
0.01609597,&swap=0.
\end{cases}}
\]

All times are microseconds. At N6144,K1536 these rates correspond algebraically to effective per-SM service rates about22.34TFLOP/s and24.43TFLOP/s. They are **not measurements of tensor-core peak throughput**: they absorb pipeline, memory and epilogue effects. Likewise5.610299us is a model-dependent fitted intercept, not a directly measured hardware startup latency.

The low-M branch can be written explicitly as

\[
\widehat T(M)=5.610299+0.2815896\lceil M/48\rceil,\qquad1\le M\le720.
\]

At721≤M≤768 the second branch predicts9.730867us. Elsewhere the selector defines the piecewise configuration exactly.

Fit: RMSE0.469756us, MAPE2.312757%. Five contiguous shape-block holdouts: RMSE0.502080us, MAPE2.368590%. These validation points were not used to fit their fold's coefficients, but all measurements share one device/software setting; they do not validate transfer to new N,K,hardware or cache conditions.

## Why residual error remains

1. **A full tile is not a constant-throughput object.** Tile width changes UMMA geometry, pipeline depth, shared-memory consumption and output-store geometry. Two orientation rates average over this. The normal and swap branches use distinct epilogues. Source confirms their difference, but timings alone cannot establish exactly which subunit causes the rate difference.
2. **Underfilled waves change memory pressure.** W1 and BLOCK_M16 persist overM1–48, but Q rises48→96→144. More simultaneous CTAs can change aggregate memory traffic and completion time even though the maximum padded tile work is unchanged. The primary model is intentionally flat within such a tile branch.
3. **Memory reuse and cache are not measured bottleneck counters.** Inputs and weights are resident and reused; no L2 flush is performed. Weight FP8 data is only9,437,184bytes, but output and activation footprints grow withM. A cold-HBM roofline is not an exact description of this benchmark, and nominal L2 capacity alone does not prove the hit rate or a transition point.
4. **Timing variation.** GPU clock/power state and per-kernel execution variation cause repeat-run and within-shape variation. Nsight System kernel durations do not identify a unique hardware stall cause.
5. **The selector optimizes geometry heuristically, not actual cycles.** A change to a new tile can reduce predicted wave work while changing store or memory behavior in ways absent from the three-parameter approximation.

The fixed term covers device-side barrier/TMEM initialization, synchronization, pipeline fill/drain and other effective costs. It must not be described as CPU launch overhead: the measured interval is the GPU kernel itself.

## Sensitivity: adding tail-wave fullness is plausible but not robustly better

Let

\[
f=Q/148-(W-1)\in(0,1].
\]

A four-parameter alternative adds `delta*f` to the primary model. Relative least squares yields `T0=5.18164841`, `delta=0.54888475`, `beta_swap=0.01751405`, `beta_normal=0.01605062`.

It improves in-sample relative error (MAPE2.10363% vs2.31276%) but worsens absolute RMSE (0.50182us vs0.46976us), because the fitted objective weights relative error. More importantly, contiguous-block validation worsens to MAPE2.61917% and RMSE0.65978us, versus2.36859% and0.50208us for the primary model. The simpler model is retained. The intercept's change from5.61 to5.18us illustrates why it is not uniquely identifiable as a physical startup constant. The tail correction is a sensitivity experiment, not proof of a specific memory contention mechanism.

## Primary source links and license

All DeepGEMM links are pinned to the exact benchmark commit `b4296edce3cd07e3b6392c8eb390cee9c41a6b70`.

- [Candidate tile generation and tensor-memory checks](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/csrc/jit_kernels/heuristics/sm100.hpp#L27-L146).
- [Shared-memory pipeline-depth calculation](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/csrc/jit_kernels/heuristics/sm100.hpp#L173-L215).
- [148-CTA launch, wave count and heuristic comparison](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/csrc/jit_kernels/heuristics/sm100.hpp#L219-L265).
- [Persistent scheduler and normal-GEMM padded M helper](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/deep_gemm/include/deep_gemm/scheduler/gemm.cuh#L159-L172).
- [Kernel template, block-K, UMMA shape, and output store geometry](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/deep_gemm/include/deep_gemm/impls/sm100_fp8_fp4_gemm_1d1d.cuh#L18-L79).
- [Device synchronization and TMA pipeline](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/deep_gemm/include/deep_gemm/impls/sm100_fp8_fp4_gemm_1d1d.cuh#L175-L209).
- [One CTA per SM/TMEM and distinct output epilogues](https://github.com/deepseek-ai/DeepGEMM/blob/b4296edce3cd07e3b6392c8eb390cee9c41a6b70/deep_gemm/include/deep_gemm/impls/sm100_fp8_fp4_gemm_1d1d.cuh#L444-L495).
- [NVIDIA's explanation of tiled GEMM and wave quantization](https://docs.nvidia.com/deeplearning/performance/dl-performance-matrix-multiplication/index.html).

`selector.py` is adapted from DeepGEMM's MIT-licensed source. Include `DeepGEMM-LICENSE` (Copyright2025DeepSeek) when redistributing the port or the downloaded source files.
