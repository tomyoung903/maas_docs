# Remaining-rate sensitivity: fixed independent HMMA rate

M64 N9984 K2048; original five-operation plan; independently measured HMMA95.804007744TF/s held fixed.
Every row changes only one remaining architecture scalar. No profile edit, GPU execution, or fitted parameter.
All timings are kernel-body predictions, excluding the separate2µs launch term.

| Parameter | Multiplier | Prediction µs | Change µs | Remaining to34.368µs |
|---|---:|---:|---:|---:|
| l2_bandwidth | 0.75 | 31.433204 | +3.031793 | 2.934796 |
| l2_bandwidth | 1 | 28.401411 | +0.000000 | 5.966589 |
| l2_bandwidth | 1.25 | 28.259826 | -0.141585 | 6.108174 |
| ddr_bandwidth | 0.75 | 28.511751 | +0.110340 | 5.856249 |
| ddr_bandwidth | 1 | 28.401411 | +0.000000 | 5.966589 |
| ddr_bandwidth | 1.25 | 28.335207 | -0.066204 | 6.032793 |
| smem_bandwidth | 0.75 | 28.401411 | +0.000000 | 5.966589 |
| smem_bandwidth | 1 | 28.401411 | +0.000000 | 5.966589 |
| smem_bandwidth | 1.25 | 28.401411 | +0.000000 | 5.966589 |
| fp32_cuda_core_flops | 0.75 | 28.415983 | +0.014573 | 5.952017 |
| fp32_cuda_core_flops | 1 | 28.401411 | +0.000000 | 5.966589 |
| fp32_cuda_core_flops | 1.25 | 28.392667 | -0.008744 | 5.975333 |
| register_bandwidth | 0.75 | 28.401411 | +0.000000 | 5.966589 |
| register_bandwidth | 1 | 28.401411 | +0.000000 | 5.966589 |
| register_bandwidth | 1.25 | 28.401411 | +0.000000 | 5.966589 |
| max_freq | 1.13597 | 28.401411 | +0.000000 | 5.966589 |

Changing `max_freq` alone does not rescale already installed rates when no Context clock override is supplied. This reproduces our actual call path.
An explicit Context clock override is different: GenericOracle scales compute/SMEM/register rates by the ratio to the stored max_freq. Using such an override with a separately calibrated rate can double-correct it unless calibration clocks are consistent.
Sensitivity is not a replacement calibration. An input is not justified merely because it reduces the measured gap.
