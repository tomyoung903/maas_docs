# Independent CPU model audit of the H20 L2 candidate

No GPU work or architecture-rate calibration was done by this audit. All predictions use the existing H20 microbenchmark profile, including the independently measured HBM rate and unchanged upstream L2/SMEM/Tensor rates. Model files are experiments, not changes to the TileSight checkout or the published page.

## Baseline

M=64, N=9984, K=2048; FP16 A/B/C; FP32 accumulation; tile16x128x64; 3shared stages; 4CTAs/SM;78SMs;312CTAs;32K iterations. Kernel body prediction23.615784017822us versus archived device median34.368us.

The stock prediction is T=.962216991738us+(K/64)*.707923969565us for this family while cache traffic remains in the same regime. The intercept is the last MMA, cast, and store. It is not an independently measured setup latency.

## Confirmed omissions

1. `kb.gemm(As,Bs,acc)` emits one semantic tensor Compute; it does not create shared->register fragment loads. `generic_oracle.py:302` prices only work-engine throughput and returns `Traffic.compute_internal()` at365. The saved prediction marks those internal accesses unknown.
2. Move-engine service without an independently specified rate is a storage-port proxy (`generic_oracle.py:476`). Thus cp.async issue, ldmatrix issue, address arithmetic, predicates, waits and barriers are not timed as actual instructions.
3. Extra latency defaults to zero (`generic_oracle.py:291`). A bandwidth service time is treated as completion latency. No measured L2 read latency, SMEM dependency latency, or fixed kernel setup term is present.
4. Resident CTAs receive ideal equal bandwidth shares. Explicit shared-resource scheduling for multiple resident CTAs is rejected (`analysis.py:255`).
5. `active_sms=ceil(concurrent/residency)` (`analysis.py:285`) packs work onto as few SMs as possible. For156CTAs and maxresidency4 this assumes39SMs, whereas hardware may spread2CTAs each across78. This does not affect the original312CTA full-wave case, but matters for N-half or stage-count controls.

## Physical SMEM accounting

Pinned CUTLASS source and SASS audit by the kernel reviewer establish, per CTA per K64:

- Global->SMEM writes: A2048+B16384=18432B.
- SMEM->register reads: A8192 (four N-warps reread A) + B16384 =24576B.
- Total SMEM port traffic43008B. Over312CTAs and32iterations:429391872B.
- At19.768320312TB/s, the shared-memory-only resource bound is21.721211778390us.
- L2 input resource bound remains184025088/8.123448629TB/s=22.653567026084us.

Therefore the additional shared bytes alone do NOT imply a new bound of34us. Their dependency, timing, and contention with shared writes matter.

## Model experiments and interpretation

- WholeK64 explicit fragment loads predict31.890531329948us. This is NOT an accepted correction: it groups all fragment work before the aggregate MMA and changes resource-service packing. A numerically close aggregate plan is not evidence that it represents the compiled kernel.
- FourK16 substeps without source issue-window hints predict37.796467226295us using an incomplete periodic search. Again this is not an accepted model.
- Initial source-text-order K16 plan predicted28.325160758686us. Independent review found its final substep did not match the compiled SASS. That numerical improvement is withdrawn as an explanation. Its files are preserved under `superseded-source-text-order/`.
- Correcting the final substep to issue MMA3 before the wait/barrier and nextstagefragment0 gives25.625809291526us, II=.745530638975us. The result is an exploratory schedule sensitivity only. It uses no fitted rates or extra latencies, but it retains other aggregate timing approximations and incomplete search. Neither the old nor new value is a validated gap reduction.
- Its resource-II-only lower-bound variant is24.003662799579us.

The exploratory plan splits B into virtual disjoint16/16/32-row sections of each K64tile, preserving total B bytes and reuse. This corresponds to the source's2+2+4 cp.async access groups. It uses the actual CUTLASS m-fast grid; changing from the historical n-fast model does not change aggregate traffic in this full single-wave case.

The exploratory constructive search is NOT exhaustive (`periodic_searched_best`, `search_complete=false`). The plan models operation issue ordering but still uses aggregate bandwidth/compute service times. It has no cost for actual instruction issue, scoreboard stalls, integer iteration work, cp.async fence/wait execution, or CTA barriers. It also requires operation completion before reusing register fragments; exact source hardware dependence may release operands earlier. It also treats the four independently issuing warps as one aggregate actor. Changing one ordering constraint moves the result by2.699351us. Therefore the apparent proximity of any one model variant cannot be claimed to explain a measured portion of the gap.

## Kernel source ordering encoded

For current K64tilek, the four K16substeps have:

1. Load next A1/B1fragments, executeMMA0, issue globalA[k+2] and firstBpart[k+2].
2. Load A2/B2, executeMMA1, issue nextBpart[k+2].
3. Load A3/B3, executeMMA2, issue remainingBpart[k+2].
4. **Compiled-tail correction:** executeMMA3 of tilek before DEPBAR/BAR; after the wait/barrier, load first A0/B0 of tilek+1. The original source-text ordering had these reversed. SASS finalHMMA offsets0x2090/0x20e0/0x20f0/0x2100 precede DEPBAR0x2140/BAR0x2150 and nextLDSM0x2200/0x2220/0x2230.

Prologue brings two stages in before steady-state execution. Register versions0/2 and1/3 share the alternating physical banks; explicit overwrite-dependency edges protect those uses across iteration boundaries.

## Discriminating measurements

- K sweep at fixed312CTAs distinguishes fixed setup/tail from steady iteration slope.
- Stage-count control tests latency hiding. Do not feed maxoccupancy blindly into the model for partially filled grids.
- NCU shared-bank conflicts, shared/LSU throughput, per-scheduler eligible warps, issue stalls, and barrier/short-scoreboard stalls distinguish issue/latency from channel saturation.
- Use independent SMEM/L2/fragment microbenchmarks for a calibration correction. Fitting L2 bandwidth to34.368us is not independent validation, especially because hardware L2-sector traffic is lower than the modeled payload requests.
- HoldoutK/shapes are necessary if a measured per-iteration correction is introduced. Label that separately from the default or source-only model.

## Artifacts

`audit_predictions.py`, `sweep-summary.json/csv`: unchanged stock predictions, plus exploratory macro variants.
`substep_plan.py`: four-substep experiment without source order.
`substep_source_order.py`: exploratory build function with compiled-tail ordering corrected.
`source-order-plan.json`: inspectable exploratory plan.
`source-order-periodic_best.json`: full result/provenance.
`source_order_sweep.py`, `source-order-sweep.json`: exploratory K family predictions after the compiled-tail correction.
`m64_n4992_k2048_residency2.json`: explicit2CTA/SM interpretation of half-sized grid (11.807892008911us versus defaultpacked4CTA/SM19.362540845636us).

## Detailed counter evidence supplied by the primary agent

`baseline-detailed-metrics.csv` reports math-pipeline throttle5.20, barrier1.07, longscoreboard.59, shortscoreboard.49, and fixed-latency wait.75 average warpcycles perissuedinstruction. Schedulerissueactive29.91%, eligiblewarps.42, activewarps3.07/scheduler. Math-pipeline throttle is the largest observed warpstallcategory. It does NOT identify which mathpipeline by itself. It does NOT prove shared-memory bankconflicts are dominant.

The totalactive-warpcyclesperissuedinstruction ratio is10.28, so mathpipe throttle is about50.6% of that warpcycle accounting. These are overlapping warpstates, not additive wallclock time components. Do not turn them into a causal microsecond breakdown. NVIDIA's ProfilingGuide explains that mathpipe throttle means the required execution pipeline is unavailable/oversubscribed and recommends interpreting stalls when issueactivity is low: https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html#warp-stall-reasons .
