# Targeted H20 memory controls

The stock source is from TileSight revision `6673bc3941d23572caad5d25473c9f129c3f000a`; the probe files originate at `75428c41b7a1127497151a3db4316a1223d342cf`. CUDA12.8, SM90a. Both core files include the common `data_pattern.hpp`. The only semantic change in the volatile core is `ld.shared.v4.u32` → `ld.volatile.shared.v4.u32`. Inspect disassembly before trusting counted loads.

On an allocated idle H20, set CUDA_VISIBLE_DEVICES to that device. Example commands:

```sh
nvcc -std=c++17 -Xptxas=-v -O3 -DNDEBUG -arch=sm_90a -lineinfo stock-core.cu -o core
nvcc -std=c++17 -Xptxas=-v -O3 -DNDEBUG -arch=sm_90a -lineinfo volatile-core.cu -o core-volatile
nvcc -std=c++17 -Xptxas=-v -O3 -DNDEBUG -arch=sm_90a -lineinfo dram_sweep.cu -o dram_sweep
./core l2 --iters 8192 --repeat 7 --seed 1729
./core-volatile smem --iters 8192 --repeat 7 --seed 1729
cuobjdump --dump-sass core-volatile > core-volatile.sass
```

See the memory recheck report for complete workload and measurement definitions. Warm cp.async timing includes waits, barriers and checksum reads; it is not an isolated L2-port rate. The original shared-probe timing is invalid and excluded from calibration.

Exact warm-control commands (one complete warmup before each timed sample):

```sh
./dram_sweep --device 0 --bytes 16777216 --methods read_cg --threads 128 --unroll 8 --guard-kb 54 --blocks 78,156,312 --iters 4096 --repeats 7 --seed 1729
./dram_sweep --device 0 --bytes 16777216 --methods cp_async --threads 128 --unroll 8 --guard-kb 38 --blocks 78,156,312 --iters 4096 --repeats 7 --seed 1729
./dram_sweep --device 0 --bytes 33554432 --methods read_cg --threads 128 --unroll 8 --guard-kb 54 --blocks 78,156,312 --iters 4096 --repeats 7 --seed 1729
./dram_sweep --device 0 --bytes 33554432 --methods cp_async --threads 128 --unroll 8 --guard-kb 38 --blocks 78,156,312 --iters 4096 --repeats 7 --seed 1729
```
