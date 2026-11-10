# FP16 Tensor Core rate and instruction-family audit

Status: independent CPU/source audit. No GPU use, profile edit, or fitted rate in this work. The hypothetical rate sweep is a sensitivity analysis only.

## Verified facts

1. The upstream H20 profile already contained `fp16_tensor_flops = 139.22e12` at commit `75428c4`. The current local file retains it at `tilesight/arch/h20.py:85`. The adjacent comment only says `158.14656 -> 139.22`; it does not identify an instruction family, kernel, compiler, microbenchmark command, raw measurements, or GPU clocks corresponding to that rate.
2. Searching the checked-out source and calibration files found no raw calibration record that establishes the provenance of 139.22. The local `calibrations/gpu-h20-5/bandwidth.json:45` explicitly says all other rates remain inherited from upstream. Therefore, calling 139.22 a *known WGMMA measurement* is not supported by the repository alone.
3. The generic compute lookup maps `(tensor, fp16)` to `fp16_tensor_flops` at `tilesight/modeling/ops/throughput.py:18`. `ThroughputRequest` has engine, dtype, operation class, and vector width, but no MMA instruction family or instruction shape. The default lookup at line177 ignores operation class and resolves the architecture attribute.
4. `tilesight/modeling/program/generic_oracle.py:302` uses that resolution. At lines323–340 it divides whole-device capacity by SM count and residency, then divides operation FLOPs by the resulting share. It does not distinguish SM80-style `mma.sync` from Hopper `wgmma` in the current GEMM plans. Adding `requires_arch=('wgmma',)` is a capability declaration, not a separate rate selection.
5. The earlier accurate 4096-cubed kernel used WGMMA. `outputs/h20-gemm-4096-20261105/build.log:32` names `MainloopSm90TmaGmmaWarpSpecialized` and `SM90::GMMA::MMA_64x128x16_F32F16F16_SS`, plus `SM90_TMA_LOAD`. `predict.py:17` requires WGMMA. Its successful timing comparison does not independently validate 139.22 for an HMMA kernel.
6. The current M64 N9984 K2048 kernel uses SM80-style `cp.async`, `ldmatrix`, and warp-level `mma.sync`/HMMA. It has the same mathematical dtype but a different operand path, instruction granularity, issue pattern, and synchronization scheme.

An explicit per-run override already exists at `throughput.py:125–153`: the key `tensor.fp16.mma` can supply a separately measured rate without changing the stored architecture profile. This does not automatically distinguish two instruction families inside one program; that would require a more specific operation classification or cost oracle.

## Primary documentation

- NVIDIA's [Nsight Compute Triage Guide, Tensor/CUDA interpretation](https://docs.nvidia.com/nsight-compute/ComputeTriage/#symptom-tensor-cuda-core-utilization-interpretation-is-ambiguous) distinguishes warp-level MMA using register operands from warp-group MMA using shared operands, and warns that low scheduler issue-active can be normal for tensor instructions. Pipeline-specific counters and actual instructions must be checked before interpreting a percentage.
- NVIDIA's [cuBLASDx Hopper pipeline guide](https://docs.nvidia.com/cuda/cublasdx/performance_guide_api_hopper.html) documents separate WGMMA and warp-level mma.sync paths, including conditions that silently select the older path. Thus the GPU architecture alone does not identify the executed instruction family.
- NVIDIA's [Tilus Hopper WGMMA tutorial](https://nvidia.github.io/tilus/latest/tutorials/matmul-hopper/v1.html) reports a faster H100 implementation after changing the instruction/operand path. Its autotuned tile also changes, so that timing ratio cannot be used as an H20 hardware multiplier.

No official NVIDIA H20-specific HMMA-vs-WGMMA numeric throughput ceiling was established by this audit. The often-quoted two-thirds ratio in Hopper research is not a substitute for this H20's independent measurement.

## Fixed hypothetical-rate sweep

Runner: `hypothetical_hmma_rates.py`.
Results: `HYPOTHETICAL-HMMA-RATES.md`, `hypothetical-hmma-rate-sweep.csv` and `.json`.

The requested rates 60,70,80,90,100,110,120,139.22 TF/s were all tested without selecting one as a fitted answer. At K2048, predicted body times are respectively 44.703,38.472,33.798,30.163,27.255,24.876,23.710,23.616 µs. All other profile values and the original five-operation program are unchanged.

The model's mainloop crossover is:

```
P_cross = (262144 FLOPs / 18432 L2-request bytes) × 8.123448629 TB/s
        = 115.533492 TF/s.
```

Above this tensor rate, the unchanged model is L2-service-bound. Below it, the modeled tensor service is larger. This says where the model changes classification. It does not prove a physical bottleneck or identify a measured HMMA rate.

The 80 TF/s curve happens to approach the larger-K measurements, but that coincidence is not calibration evidence. The same curve remains too short at K64. No constant was fitted to the target.

## Matched WGMMA control plan

Runner: `wgmma_matching_plan.py`. Inputs are the same logical M64 N9984 K2048, FP16 A/B/C and FP32 accumulation. Implementation-facing tile64×128×64, 3 shared stages, 256 threads, TMA copies, register accumulators, 78 CTAs, and explicit one resident CTA on each of78SMs.

The grid residency is separate from maximum hardware occupancy. Parent-reported NCU distribution confirms min1, max1, mean1, total78CTAs across SMs. Thus one resident CTA on each of78SMs is observed for this launch. Using the API maximum2 as actual residency would incorrectly make the generic model pack the launch onto39SMs.

Unchanged139.22TF/s profile gives:

```
T_model = 32 × 0.587479730 + 0.784414998 = 19.583766 µs.
```

Per-iteration load_A=.078658219µs, load_B=.331019517µs, MMA=.587479730µs. Epilogue cast=.043717745µs and store=.331019517µs. Tensor service is now the largest resource. The mathematical FLOPs and unique HBM input bytes are unchanged. Modeled L2 input requests fall from184,025,088 to61,341,696bytes because the larger CTA avoids repeated B requests by the four16-row CTAs.

Parent-reported measured cold24.576µs and warm23.872µs are still20.314% and17.966% above this prediction on the measured-time denominator. This is not a complete reconciliation. The control changed instruction family, tile, data traffic, and resident-CTA arrangement together, so its speedup cannot be attributed solely to WGMMA throughput.

## How to discriminate the remaining hypotheses

The parent/kernel agent's independent probes should measure register-resident HMMA with enough independent accumulators and compare it with WGMMA on the same H20. There are two materially different outcomes:

- HMMA saturates below139.22TF/s while WGMMA reaches that range: one generic FP16 rate overstates the current instruction path. Use the independently measured instruction-family rate per run and test the full K sweep without fitting.
- HMMA also reaches that range in isolation: the target kernel's lower rate comes from its instruction/operand/scheduling mix, rather than an intrinsic instruction-family ceiling. An isolated peak is still not a throughput guarantee for the mixed kernel.

The dominant HMMA math-pipe-throttle samples establish where warps wait; they do not on their own distinguish these two outcomes. Shared-memory excess-wavefront count zero argues against bank conflicts as the main explanation. Neither result authorizes adding stall percentages as wall-clock microseconds.

Earlier source-order schedule variants are exploratory only. The source-text tail ordering was corrected to compiled SASS order; the current result is25.625809µs, not28.325161µs. It aggregates four independent warps, conservatively uses full-operation completion for register overwrite hazards, and does not exhaust the schedule search. It must not be presented as a validated correction or a percentage of the gap explained.
