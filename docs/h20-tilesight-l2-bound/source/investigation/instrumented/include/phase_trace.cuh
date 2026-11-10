#pragma once
#include <cuda_runtime.h>
namespace h20_phase_trace {
struct Record {
  unsigned long long t0,t1,t2,t3;
  unsigned smid,block_x,block_y,block_z;
};
// This diagnostic is a single translation-unit executable. Define the CUDA
// symbol once here; do not redeclare/define it again in benchmark.cu.
__device__ Record* records = nullptr;
}
