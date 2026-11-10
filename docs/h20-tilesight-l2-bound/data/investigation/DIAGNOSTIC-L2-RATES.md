# Diagnostic-only L2-rate substitutions

The independent HMMA rate stays at 95.804007744 TFLOP/s. The original five-operation plan, exact declared-access cache trace, residency 4, and other rates stay fixed.
These CPU substitutions test sensitivity. They do not validate transfer of an effective bandwidth between different instruction paths or traffic definitions. No stored profile was changed.

| Input-rate source | L2 input TB/s | Prediction µs | Gap to 34.368 µs | Underprediction |
|---|---:|---:|---:|---:|
| accepted_inherited_l2 | 8.123448629 | 28.401411 | 5.966589 | 17.361% |
| ld_global_cg_30mib_8192_iterations | 5.726513277 | 33.364074 | 1.003926 | 2.921% |
| cp_async_shared_32mib_with_waits_barriers_checksum | 7.906417530 | 28.420843 | 5.947157 | 17.304% |
| cp_async_shared_16mib_with_waits_barriers_checksum | 8.025505437 | 28.410050 | 5.957950 | 17.336% |

The lower ld.global.cg-to-register rate can reduce the numeric gap, but this GEMM uses cp.async-to-shared. The separate cp.async tests reach about 7.91–8.03 TB/s while including waits, barriers, and checksum work. They are effective path rates, not isolated L2 service capacities. Choosing the lower rate because it gives a closer answer would not establish a valid correction.
The model charges 184,025,088 declared input-request bytes, while the archived cold L2 sector counter reports 128,696,096 bytes. That accounting mismatch must also be resolved before interpreting any substituted effective rate as a matched hardware parameter.
The accepted instruction-family correction remains 28.401411 µs versus 34.368 µs. These results do not establish full reconciliation.
