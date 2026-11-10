#pragma once
// Runtime uniform selector; host writes only before launches.
// One translation unit includes this pragma-once header.
__device__ __constant__ int h20_prefill_mode = 0;
