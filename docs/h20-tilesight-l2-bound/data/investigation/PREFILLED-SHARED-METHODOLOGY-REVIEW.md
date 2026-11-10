# Review of the periodic-input shared-memory diagnostic

CPU/source review only, before compilation and GPU validation. No stored model rate or accepted prediction is changed.

Reviewed `prefilled-shared/source/benchmark.cu`, the `mma_multistage.h` overlay, its runtime selector, and pinned CUTLASS commit `954c8d7be60d730cc3f51e8f1ffe9850dce054d5` iterator/copy definitions.

**No invalidating source bug was found for M64 N9984 K2048 and the specified full tiles.** The compiled experiment must still pass correctness, resource/occupancy, instruction-retention, and baseline checks.

## What is controlled correctly

- A and B keep their full allocations and original strides. Only their values repeat every K64; addresses do not alias a smaller matrix. Values are nonzero multiples of 1/8, generated on the host and copied to device memory.
- One runtime constant-memory selector controls modes inside one kernel binary. Modes 1–3 share the extra initialization, so mode 1 provides the appropriate initialization control.
- The original prologue advances the original global and shared write iterators to stage 2. The extra prefill uses copied global iterators and saves/restores both shared write iterators. It does not advance original global iterators, the circular-buffer index, or the K iteration count.
- The static `kNone` requirement ensures recurring copies use instruction predication. The pinned `cp_async<..., Global>` emits `@p cp.async.cg`; a false predicate does not zero-fill the preloaded slot.
- `clear_mask(false)` preserves an already cleared mask. `add_tile_offset` recomputes predicates only at the first residue transition, which the two-stage prologue has already passed. Subsequent pointer increments do not re-enable the masks.
- All three prefilled slots are committed, drained with `wait<0>`, and followed by a CTA barrier before reads proceed. This initialization is retained in mode 3. The final wait/barrier before shared-storage reuse by the epilogue is also retained.

Relevant pinned definitions: [`clear_mask` and iterator advancement](https://github.com/NVIDIA/cutlass/blob/954c8d7be60d730cc3f51e8f1ffe9850dce054d5/include/cutlass/transform/threadblock/predicated_tile_access_iterator.h), [`cp_async` instruction predication](https://github.com/NVIDIA/cutlass/blob/954c8d7be60d730cc3f51e8f1ffe9850dce054d5/include/cutlass/arch/memory_sm80.h).

## Necessary interpretation limits

1. **Mode 1 → mode 2** tests removal of recurring transfers within the mixed loop while keeping the extra prefill and synchronization structure. The change includes any associated issue/queue pressure and memory-path effects; it is not an isolated measurement of L2 latency.
2. **Mode 2 → mode 3** removes recurring commit, wait, and CTA barrier as a bundle after operands become immutable. It does not isolate each synchronization instruction's original contribution.
3. **Mode 0 → mode 2** changes initialization as well as recurring copies. Do not use that difference alone as an attributed copy cost.
4. Compare the instrumented mode-0 kernel with the original binary and compare the periodic fixture with the original random fixture. A changed compiler schedule or data-dependent behavior can affect transferability to the original measurement even when the arithmetic remains correct.
5. Check actual register/shared-memory resources and occupancy. Confirm retained HMMA and LDSM instructions in compiled code, and preferably equal executed counts across modes. Runtime-dependent control protects against compile-time specialization, but source alone does not establish retained machine work.
6. Every mode must validate all output elements against the same cuBLAS computation outside timing. The periodic fixture is a new diagnostic workload, not the original random fixture. These timing deltas cannot be added mechanically to the original prediction or described as complete reconciliation.

The accepted original-workload result remains **28.401411 µs predicted versus 34.368 µs measured** until separate evidence justifies another model change.
