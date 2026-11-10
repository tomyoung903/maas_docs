# Two-warp / N=64 warp-tile control

This changes only the warp tile from 16×32×64 to 16×64×64, retaining CTA tile16×128×64, row-major A/B/C, alignment8, input values, and the correctness/timing harness. There are two warps (64 threads) per CTA instead of four. Runtime metadata reports the actual thread count, registers, shared allocation and occupancy, plus the warp tile.

Build stage3 first. The existing build script also permits other stage counts but they are separate interventions.

The stock A copy map is valid: 128 eight-half A vectors distributed over64 threads gives two accesses per thread. B has enough vector accesses as well. No custom copy mapping or alignment change is introduced.

Mechanism under test: each warp owns eight independent MMA accumulator groups instead of four; there are half as many warps executing CTA-level iterator/control work. Total MMA arithmetic is unchanged. Some copy/iterator work per warp increases because each warp covers more B. A is reread from shared memory twice rather than four times, so per-K64 shared reads fall from24,576B to20,480B perCTA. Combined global-to-shared writes plus shared-to-register reads fall from43,008B to38,912B perCTA.

Countervailing effects: fewer warps can hide less latency; more registers are needed per thread; compiler scheduling and epilogue mappings can change. Runtime/counter evidence, not the direction of the change alone, determines whether it improves this shape. Recompute any detailed plan with the measured resource metadata. The generic five-op plan omits warp geometry, so it may predict no timing difference even though the actual implementation changes.
