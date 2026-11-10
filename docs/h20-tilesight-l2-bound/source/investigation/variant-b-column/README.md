# B column-major layout control

This variant retains the same logical matrices, seed-17 input values, tile 16×128×64, warp tile 16×32×64, 128 threads, element types, alignment eight, and stage-count controls. It changes B's physical storage from row major (leading dimension N) to column major (leading dimension K).

The host generates B in the same logical row-major RNG order, placing each value at the appropriate column-major address. This host-side permutation is outside all kernel timings. The cuBLAS reference uses OP_T for the column-major B buffer to calculate the same row-major C. All C entries must still match exactly for these deterministic inputs.

Build stage 3 and stage 2 with `PIPELINE_STAGES=3` or `2`, as in the stage-control directory. Dynamic metadata reports the actual registers, shared storage and occupancy; do not assume they remain unchanged after layout compilation.

This is a causal layout intervention, not an equivalent execution implementation: CUTLASS selects a different B shared-memory layout and shared-to-register load orientation. The generic TileSight five-operation plan does not describe this instruction/layout difference, even though its matrix dimensions, ideal byte counts and FLOPs are unchanged. A timing change would demonstrate that missing layout/instruction details affect performance. It would not by itself identify the exact stall mechanism. Pair with shared-memory and scheduler counters if the timing difference is material.

## Why the initially suggested eight-warp shape was not used

Changing the warp tile from 16×32×64 to 16×16×64 yields eight warps/256 threads. The aligned A tile has only 16×64/8=128 vectors. The stock PitchLinearWarpRakedThreadMap calculates zero per-thread contiguous iterations and rejects this configuration. Making it legal would also require changing A alignment/cache behavior, the K tile, or implementing a custom partial-thread copy map. Those are additional interventions and are not part of this control.
