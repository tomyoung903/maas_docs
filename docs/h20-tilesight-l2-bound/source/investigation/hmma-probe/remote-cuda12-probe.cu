#include <cuda_runtime.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

#define CUDA_CHECK(call) do { cudaError_t e=(call); if(e!=cudaSuccess) { \
  std::fprintf(stderr,"CUDA error %s at %s:%d\n",cudaGetErrorString(e),__FILE__,__LINE__); std::exit(2); } } while(0)
constexpr int kUnroll = 8;

// Six distinct kernel arguments prevent compile-time equality propagation of
// the operand registers. Their runtime values happen to be identical.
// Every PTX instruction updates four FP32 outputs per lane, 128 outputs/warp.
template<int Groups, int Threads>
__global__ __launch_bounds__(Threads)
void hmma_register_probe(float* out, int iterations,
                         unsigned a0, unsigned a1, unsigned a2, unsigned a3,
                         unsigned b0, unsigned b1) {
  float acc[Groups][4];
#pragma unroll
  for(int g=0;g<Groups;++g) {
#pragma unroll
    for(int j=0;j<4;++j) acc[g][j]=0.0f;
  }
#pragma unroll 1
  for(int iteration=0;iteration<iterations;++iteration) {
#pragma unroll
    for(int repeat=0;repeat<kUnroll;++repeat) {
#pragma unroll
      for(int g=0;g<Groups;++g) {
        asm volatile(
          "mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 "
          "{%0, %1, %2, %3}, "
          "{%4, %5, %6, %7}, "
          "{%8, %9}, "
          "{%0, %1, %2, %3};\n"
          : "+f"(acc[g][0]), "+f"(acc[g][1]), "+f"(acc[g][2]), "+f"(acc[g][3])
          : "r"(a0), "r"(a1), "r"(a2), "r"(a3), "r"(b0), "r"(b1));
      }
    }
  }
  const size_t thread = size_t(blockIdx.x)*Threads+threadIdx.x;
  const size_t threads = size_t(gridDim.x)*Threads;
  // Coalesced SoA stores preserve every accumulator for an exact check.
#pragma unroll
  for(int g=0;g<Groups;++g) {
#pragma unroll
    for(int j=0;j<4;++j) out[size_t(g*4+j)*threads+thread]=acc[g][j];
  }
}

struct Options {
  std::vector<int> groups{1,2,4,8,16};
  std::vector<int> threads{128,256};
  std::vector<int> blocks_per_sm{1,2,4,8};
  std::vector<int> iterations{4096,8192};
  int repeats=7, warmup=3;
};
std::vector<int> parse_list(const std::string& value) {
  std::vector<int> result; std::stringstream input(value); std::string part;
  while(std::getline(input,part,',')) {
    size_t consumed=0; int number=std::stoi(part,&consumed);
    if(consumed!=part.size() || number<=0) throw std::runtime_error("invalid positive integer list");
    result.push_back(number);
  }
  if(result.empty()) throw std::runtime_error("empty list");
  return result;
}
Options parse(int argc,char** argv) {
  Options o;
  for(int i=1;i<argc;++i) {
    std::string key=argv[i];
    if(key=="--help") {
      std::printf("probe [--groups 1,2,4,8,16] [--threads 128,256] [--blocks-per-sm 1,2,4,8] [--iterations 4096,8192] [--repeats 7] [--warmup 3]\n");
      std::exit(0);
    }
    if(++i>=argc) throw std::runtime_error("missing option value");
    std::string value=argv[i];
    if(key=="--groups") o.groups=parse_list(value);
    else if(key=="--threads") o.threads=parse_list(value);
    else if(key=="--blocks-per-sm") o.blocks_per_sm=parse_list(value);
    else if(key=="--iterations") o.iterations=parse_list(value);
    else if(key=="--repeats") o.repeats=std::stoi(value);
    else if(key=="--warmup") o.warmup=std::stoi(value);
    else throw std::runtime_error("unknown option: "+key);
  }
  for(int x:o.groups) if(x!=1 && x!=2 && x!=4 && x!=8 && x!=16) throw std::runtime_error("unsupported groups");
  for(int x:o.threads) if(x!=128 && x!=256) throw std::runtime_error("unsupported threads");
  for(int x:o.blocks_per_sm) if(x>16) throw std::runtime_error("blocks-per-sm must be <=16");
  for(int x:o.iterations) if(x>(1<<20)) throw std::runtime_error("iterations too large for exact quarter-unit accumulation");
  if(o.repeats<3 || o.repeats>101 || o.warmup<1 || o.warmup>100) throw std::runtime_error("invalid sample/warmup count");
  return o;
}

std::ofstream sample_file;

template<int Groups, int Threads>
void run_configuration(const Options& options,const cudaDeviceProp& prop,
                       int blocks_per_sm,int iterations,cudaStream_t stream) {
  cudaFuncAttributes attr{};
  CUDA_CHECK(cudaFuncGetAttributes(&attr,hmma_register_probe<Groups,Threads>));
  int max_blocks=0;
  CUDA_CHECK(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&max_blocks,hmma_register_probe<Groups,Threads>,Threads,0));
  if(blocks_per_sm>max_blocks) {
    std::printf("{\"status\":\"SKIP\",\"reason\":\"requested grid exceeds single-wave occupancy capacity\",\"groups\":%d,\"threads\":%d,\"blocks_per_sm_requested\":%d,\"max_active_blocks_per_sm\":%d,\"iterations\":%d}\n",Groups,Threads,blocks_per_sm,max_blocks,iterations);
    return;
  }
  const int blocks=prop.multiProcessorCount*blocks_per_sm;
  const size_t total_threads=size_t(blocks)*Threads;
  const size_t output_count=total_threads*Groups*4;
  const uint64_t warp_instructions=uint64_t(blocks)*(Threads/32)*Groups*kUnroll*iterations;
  const uint64_t flops=warp_instructions*4096ull;
  // half(0.125) has bits0x3000, packed twice per 32-bit register.
  // A and B are both0.125, so each output increments16*(1/8)*(1/8)=1/4.
  constexpr unsigned packed_eighths=0x30003000u;
  const float expected=float(iterations*kUnroll)*0.25f;
  float* device_output=nullptr; CUDA_CHECK(cudaMalloc(&device_output,output_count*sizeof(float)));
  auto launch=[&] {
    hmma_register_probe<Groups,Threads><<<blocks,Threads,0,stream>>>(
        device_output,iterations,packed_eighths,packed_eighths,packed_eighths,packed_eighths,packed_eighths,packed_eighths);
    CUDA_CHECK(cudaGetLastError());
  };
  launch(); CUDA_CHECK(cudaStreamSynchronize(stream));
  std::vector<float> host_output(output_count);
  CUDA_CHECK(cudaMemcpy(host_output.data(),device_output,output_count*sizeof(float),cudaMemcpyDeviceToHost));
  size_t mismatches=0; float max_error=0;
  for(float value:host_output) {
    if(!std::isfinite(value) || value!=expected) ++mismatches;
    max_error=std::max(max_error,std::isfinite(value)?std::abs(value-expected):INFINITY);
  }
  if(mismatches) {
    std::fprintf(stderr,"Correctness FAIL groups=%d threads=%d blocks_per_sm=%d iterations=%d mismatches=%zu expected=%g max_error=%g\n",Groups,Threads,blocks_per_sm,iterations,mismatches,expected,max_error);
    std::exit(3);
  }
  for(int i=0;i<options.warmup;++i)launch();
  CUDA_CHECK(cudaStreamSynchronize(stream));
  cudaEvent_t start,end; CUDA_CHECK(cudaEventCreate(&start)); CUDA_CHECK(cudaEventCreate(&end));
  std::vector<double> times;
  for(int sample=0;sample<options.repeats;++sample) {
    CUDA_CHECK(cudaEventRecord(start,stream)); launch(); CUDA_CHECK(cudaEventRecord(end,stream));
    CUDA_CHECK(cudaEventSynchronize(end)); float ms=0; CUDA_CHECK(cudaEventElapsedTime(&ms,start,end));
    double us=double(ms)*1000.; times.push_back(us);
    sample_file<<Groups<<","<<Threads<<","<<blocks_per_sm<<","<<blocks<<","<<iterations<<","<<kUnroll<<","<<sample<<","<<us<<","<<flops<<","<<double(flops)/us/1e6<<"\n";
  }
  std::sort(times.begin(),times.end()); const double median=times[times.size()/2];
  std::printf("{\"status\":\"PASS\",\"instruction\":\"mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32\",\"groups\":%d,\"threads\":%d,\"warps_per_block\":%d,\"blocks_per_sm_grid\":%d,\"grid_blocks\":%d,\"max_active_blocks_per_sm\":%d,\"registers_per_thread\":%d,\"local_bytes_per_thread\":%zu,\"static_shared_bytes\":%zu,\"iterations\":%d,\"unroll\":%d,\"warp_mma_instructions\":%llu,\"flops\":%llu,\"correctness_elements\":%zu,\"correctness_expected\":%.9g,\"mismatches\":%zu,\"samples\":%zu,\"median_event_us\":%.9f,\"min_event_us\":%.9f,\"max_event_us\":%.9f,\"median_tflops\":%.9f}\n",
      Groups,Threads,Threads/32,blocks_per_sm,blocks,max_blocks,attr.numRegs,attr.localSizeBytes,attr.sharedSizeBytes,iterations,kUnroll,
      (unsigned long long)warp_instructions,(unsigned long long)flops,output_count,expected,mismatches,times.size(),median,times.front(),times.back(),double(flops)/median/1e6);
  std::fflush(stdout); sample_file.flush();
  CUDA_CHECK(cudaEventDestroy(start)); CUDA_CHECK(cudaEventDestroy(end)); CUDA_CHECK(cudaFree(device_output));
}

template<int Groups>
void run_group(const Options& options,const cudaDeviceProp& prop,cudaStream_t stream) {
  for(int threads:options.threads)for(int blocks:options.blocks_per_sm)for(int iterations:options.iterations) {
    if(threads==128)run_configuration<Groups,128>(options,prop,blocks,iterations,stream);
    else run_configuration<Groups,256>(options,prop,blocks,iterations,stream);
  }
}
int main(int argc,char**argv) {
  Options options; try { options=parse(argc,argv); } catch(const std::exception& e) {std::fprintf(stderr,"%s\n",e.what());return 1;}
  CUDA_CHECK(cudaSetDevice(0)); cudaDeviceProp prop{}; CUDA_CHECK(cudaGetDeviceProperties(&prop,0));
  if(prop.major<8) {std::fprintf(stderr,"Requires SM80 or newer\n");return 1;}
  std::printf("{\"device\":\"%s\",\"sm_count\":%d,\"cc_major\":%d,\"cc_minor\":%d,\"note\":\"Register-only instruction-family calibration; no GEMM timing fit; raw events include fixed launch/store overhead\"}\n",prop.name,prop.multiProcessorCount,prop.major,prop.minor);
  sample_file.open("probe-samples.csv"); sample_file.precision(12);
  sample_file<<"groups,threads,blocks_per_sm_grid,grid_blocks,iterations,unroll,sample,event_us,flops,tflops\n";
  if(!sample_file) {std::fprintf(stderr,"Cannot create probe-samples.csv\n");return 1;}
  cudaStream_t stream; CUDA_CHECK(cudaStreamCreate(&stream));
  for(int groups:options.groups) {
    switch(groups) {
      case 1:run_group<1>(options,prop,stream);break;
      case 2:run_group<2>(options,prop,stream);break;
      case 4:run_group<4>(options,prop,stream);break;
      case 8:run_group<8>(options,prop,stream);break;
      case 16:run_group<16>(options,prop,stream);break;
    }
  }
  CUDA_CHECK(cudaStreamDestroy(stream));
}
