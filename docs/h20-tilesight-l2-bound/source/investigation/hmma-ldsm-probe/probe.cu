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
constexpr int kThreads=128, kGroups=4, kUnroll=8, kSmemBytes=55296;
constexpr int kChunkBytes=6144,kChunks=8;
static_assert(kChunkBytes*kChunks<=kSmemBytes,"operand chunks must fit shared allocation");
enum Mode { Pure=0, Pipelined=1, Serial=2 };
const char* mode_names[]={"pure","pipelined","serial"};

__device__ __forceinline__ void load_a(unsigned* r,unsigned address) {
  asm volatile("ldmatrix.sync.aligned.m8n8.x4.shared.b16 {%0,%1,%2,%3}, [%4];"
      : "=r"(r[0]),"=r"(r[1]),"=r"(r[2]),"=r"(r[3]) : "r"(address) : "memory");
}
__device__ __forceinline__ void load_b(unsigned* r,unsigned address) {
  asm volatile("ldmatrix.sync.aligned.m8n8.x4.trans.shared.b16 {%0,%1,%2,%3}, [%4];"
      : "=r"(r[0]),"=r"(r[1]),"=r"(r[2]),"=r"(r[3]) : "r"(address) : "memory");
}
__device__ __forceinline__ void mma(float* c,const unsigned* a,const unsigned* b) {
  asm volatile("mma.sync.aligned.m16n8k16.row.col.f32.f16.f16.f32 "
      "{%0,%1,%2,%3}, {%4,%5,%6,%7}, {%8,%9}, {%0,%1,%2,%3};"
      : "+f"(c[0]),"+f"(c[1]),"+f"(c[2]),"+f"(c[3])
      : "r"(a[0]),"r"(a[1]),"r"(a[2]),"r"(a[3]),"r"(b[0]),"r"(b[1]));
}

template<int ProbeMode>
__global__ __launch_bounds__(kThreads)
void instruction_mix_probe(float* out,unsigned long long* phase,int iterations,
                           unsigned a0,unsigned a1,unsigned a2,unsigned a3,
                           unsigned b0,unsigned b1,unsigned b2,unsigned b3,
                           unsigned b4,unsigned b5,unsigned b6,unsigned b7) {
  extern __shared__ __align__(16) unsigned data[];
  // Eight physical chunks prevent ptxas from hoisting invariant repeated loads.
  // Each chunk gives every warp three 512-byte fragments. Initialize all49152B
  // before the loop timer. The full allocation still matches baseline occupancy.
  volatile unsigned* initialized=data;
  for(int i=threadIdx.x;i<kChunkBytes*kChunks/int(sizeof(unsigned));i+=kThreads) initialized[i]=a0;
  __syncthreads();
  const unsigned shared=unsigned(__cvta_generic_to_shared(data));
  const unsigned warp=threadIdx.x/32,lane=threadIdx.x%32;
  // Four 8x8 half matrices per x4 load. Every row begins at a 16-byte boundary.
  const unsigned address_a=shared+warp*1536+lane*16;
  const unsigned address_b0=address_a+512,address_b1=address_a+1024;
  unsigned ar[2][4]={{a0,a1,a2,a3},{a0,a1,a2,a3}};
  unsigned br[2][8]={{b0,b1,b2,b3,b4,b5,b6,b7},{b0,b1,b2,b3,b4,b5,b6,b7}};
  float acc[4][4];
#pragma unroll
  for(int g=0;g<4;++g) {
#pragma unroll
    for(int j=0;j<4;++j) acc[g][j]=0;
  }
  if constexpr(ProbeMode==Pipelined) {
    load_a(ar[0],address_a);load_b(br[0],address_b0);load_b(br[0]+4,address_b1);
  }
  unsigned long long begin=0,end=0;
  if(threadIdx.x==0) asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(begin) :: "memory");
#pragma unroll 1
  for(int iteration=0;iteration<iterations;++iteration) {
#pragma unroll
    for(int round=0;round<kUnroll;++round) {
      // The outer iteration participates in each address: the rotation changes
      // between iterations, and all eight unrolled rounds use distinct chunks.
      const unsigned offset=(unsigned(iteration+round)&7u)*kChunkBytes;
      if constexpr(ProbeMode==Pure) {
#pragma unroll
        for(int g=0;g<4;++g) mma(acc[g],ar[0],br[0]+g*2);
      } else if constexpr(ProbeMode==Serial) {
        load_a(ar[0],address_a+offset);load_b(br[0],address_b0+offset);load_b(br[0]+4,address_b1+offset);
#pragma unroll
        for(int g=0;g<4;++g) mma(acc[g],ar[0],br[0]+g*2);
      } else {
        // Matches the baseline's alternating fragments and instruction ordering:
        // HMMA0, next A/B0 LDSM, HMMA1, next B1 LDSM, HMMA2, HMMA3.
        const int current=round&1,next=current^1;
        mma(acc[0],ar[current],br[current]);
        load_a(ar[next],address_a+offset);
        load_b(br[next],address_b0+offset);
        mma(acc[1],ar[current],br[current]+2);
        load_b(br[next]+4,address_b1+offset);
        mma(acc[2],ar[current],br[current]+4);
        mma(acc[3],ar[current],br[current]+6);
      }
    }
  }
  if(threadIdx.x==0) {
    asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(end) :: "memory");
    unsigned smid;asm volatile("mov.u32 %0, %%smid;" : "=r"(smid));
    phase[blockIdx.x*3]=begin;phase[blockIdx.x*3+1]=end;phase[blockIdx.x*3+2]=smid;
  }
  const size_t thread=size_t(blockIdx.x)*kThreads+threadIdx.x;
  const size_t threads=size_t(gridDim.x)*kThreads;
#pragma unroll
  for(int g=0;g<4;++g) {
#pragma unroll
    for(int j=0;j<4;++j) out[size_t(g*4+j)*threads+thread]=acc[g][j];
  }
}

struct Options {std::vector<int> iterations{4096,8192};std::vector<int> modes{Pure,Pipelined,Serial};int repeats=7,warmup=3,blocks_per_sm=4;};
Options parse(int argc,char**argv) {
  Options o;
  for(int i=1;i<argc;++i) {
    std::string key=argv[i];
    if(++i>=argc)throw std::runtime_error("missing option value");
    std::string value=argv[i];
    if(key=="--iterations") {o.iterations.clear();std::stringstream s(value);std::string x;while(std::getline(s,x,','))o.iterations.push_back(std::stoi(x));}
    else if(key=="--modes") {o.modes.clear();std::stringstream s(value);std::string x;while(std::getline(s,x,',')){int m=-1;for(int j=0;j<3;++j)if(x==mode_names[j])m=j;if(m<0)throw std::runtime_error("unknown mode");o.modes.push_back(m);}}
    else if(key=="--repeats")o.repeats=std::stoi(value);
    else if(key=="--warmup")o.warmup=std::stoi(value);
    else if(key=="--blocks-per-sm")o.blocks_per_sm=std::stoi(value);
    else throw std::runtime_error("unknown option: "+key);
  }
  for(int x:o.iterations)if(x<=0||x>(1<<20))throw std::runtime_error("iterations must be1..2^20");
  if(o.iterations.empty()||o.modes.empty()||o.repeats<3||o.repeats>101||o.warmup<1||o.warmup>100||o.blocks_per_sm<1||o.blocks_per_sm>4)throw std::runtime_error("invalid parameters");
  return o;
}
std::ofstream samples;
template<int ProbeMode>
void run(const Options& options,const cudaDeviceProp& prop,int iterations,cudaStream_t stream) {
  CUDA_CHECK(cudaFuncSetAttribute(instruction_mix_probe<ProbeMode>,cudaFuncAttributeMaxDynamicSharedMemorySize,kSmemBytes));
  cudaFuncAttributes attr{};CUDA_CHECK(cudaFuncGetAttributes(&attr,instruction_mix_probe<ProbeMode>));
  int occupancy=0;CUDA_CHECK(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occupancy,instruction_mix_probe<ProbeMode>,kThreads,kSmemBytes));
  if(options.blocks_per_sm>occupancy)throw std::runtime_error("requested grid exceeds occupancy");
  const int blocks=prop.multiProcessorCount*options.blocks_per_sm;
  const size_t count=size_t(blocks)*kThreads*16;
  const uint64_t hmma=uint64_t(blocks)*4*4*kUnroll*iterations;
  const uint64_t ldsm=ProbeMode==Pure?0:uint64_t(blocks)*4*3*kUnroll*iterations;
  const uint64_t flops=hmma*4096;
  constexpr unsigned bits=0x30003000;
  const float expected=float(iterations*kUnroll)*0.25f;
  float* out;unsigned long long* phase;
  CUDA_CHECK(cudaMalloc(&out,count*sizeof(float)));CUDA_CHECK(cudaMalloc(&phase,size_t(blocks)*3*sizeof(unsigned long long)));
  auto launch=[&]{instruction_mix_probe<ProbeMode><<<blocks,kThreads,kSmemBytes,stream>>>(out,phase,iterations,bits,bits,bits,bits,bits,bits,bits,bits,bits,bits,bits,bits);CUDA_CHECK(cudaGetLastError());};
  launch();CUDA_CHECK(cudaStreamSynchronize(stream));
  std::vector<float> host(count);CUDA_CHECK(cudaMemcpy(host.data(),out,count*sizeof(float),cudaMemcpyDeviceToHost));
  size_t errors=0;for(float x:host)if(!std::isfinite(x)||x!=expected)++errors;
  if(errors){std::fprintf(stderr,"FAIL %s iterations%d mismatches%zu expected%g\n",mode_names[ProbeMode],iterations,errors,expected);std::exit(3);}
  for(int i=0;i<options.warmup;++i)launch();CUDA_CHECK(cudaStreamSynchronize(stream));
  cudaEvent_t start,end;CUDA_CHECK(cudaEventCreate(&start));CUDA_CHECK(cudaEventCreate(&end));
  std::vector<double> times;
  for(int sample=0;sample<options.repeats;++sample){
    CUDA_CHECK(cudaEventRecord(start,stream));launch();CUDA_CHECK(cudaEventRecord(end,stream));CUDA_CHECK(cudaEventSynchronize(end));
    float ms;CUDA_CHECK(cudaEventElapsedTime(&ms,start,end));double us=double(ms)*1000;times.push_back(us);
    samples<<mode_names[ProbeMode]<<","<<iterations<<","<<sample<<","<<us<<","<<flops<<","<<double(flops)/us/1e6<<"\n";
  }
  std::sort(times.begin(),times.end());double med=times[times.size()/2];
  std::vector<unsigned long long> stamps(size_t(blocks)*3);CUDA_CHECK(cudaMemcpy(stamps.data(),phase,stamps.size()*sizeof(unsigned long long),cudaMemcpyDeviceToHost));
  std::vector<double> durations;unsigned long long earliest=~0ull,latest=0;
  std::ofstream phases(std::string("phases-")+mode_names[ProbeMode]+"-"+std::to_string(iterations)+".csv");phases<<"block,smid,begin_ns,end_ns,loop_us\n";
  for(int b=0;b<blocks;++b){auto t0=stamps[b*3],t1=stamps[b*3+1];if(t1<=t0)throw std::runtime_error("invalid phase");double us=double(t1-t0)/1000;durations.push_back(us);earliest=std::min(earliest,t0);latest=std::max(latest,t1);phases<<b<<","<<stamps[b*3+2]<<","<<t0<<","<<t1<<","<<us<<"\n";}
  std::sort(durations.begin(),durations.end());
  std::printf("{\"status\":\"PASS\",\"mode\":\"%s\",\"groups\":4,\"threads\":128,\"grid_blocks\":%d,\"blocks_per_sm_grid\":%d,\"max_active_blocks_per_sm\":%d,\"registers_per_thread\":%d,\"local_bytes_per_thread\":%zu,\"dynamic_smem\":%d,\"iterations\":%d,\"unroll\":%d,\"warp_hmma\":%llu,\"warp_ldsm_in_timed_loop\":%llu,\"shared_operand_read_bytes\":%llu,\"flops\":%llu,\"correctness_elements\":%zu,\"correctness_expected\":%g,\"mismatches\":%zu,\"median_event_us\":%.9f,\"min_event_us\":%.9f,\"max_event_us\":%.9f,\"median_tflops\":%.9f,\"thread0_loop_median_us\":%.9f,\"loop_envelope_us\":%.9f}\n",mode_names[ProbeMode],blocks,options.blocks_per_sm,occupancy,attr.numRegs,attr.localSizeBytes,kSmemBytes,iterations,kUnroll,(unsigned long long)hmma,(unsigned long long)ldsm,(unsigned long long)(ldsm*512),(unsigned long long)flops,count,expected,errors,med,times.front(),times.back(),double(flops)/med/1e6,durations[durations.size()/2],double(latest-earliest)/1000);
  std::fflush(stdout);samples.flush();CUDA_CHECK(cudaEventDestroy(start));CUDA_CHECK(cudaEventDestroy(end));CUDA_CHECK(cudaFree(out));CUDA_CHECK(cudaFree(phase));
}
int main(int argc,char**argv){
  try{
    auto options=parse(argc,argv);CUDA_CHECK(cudaSetDevice(0));cudaDeviceProp prop{};CUDA_CHECK(cudaGetDeviceProperties(&prop,0));
    if(prop.major<8)throw std::runtime_error("requiresSM80+");
    std::printf("{\"device\":\"%s\",\"sms\":%d,\"note\":\"Independent operand-loading control, not a generic Tensor peak or GEMM-time fit\"}\n",prop.name,prop.multiProcessorCount);
    samples.open("probe-samples.csv");samples.precision(12);samples<<"mode,iterations,sample,event_us,flops,tflops\n";
    cudaStream_t stream;CUDA_CHECK(cudaStreamCreate(&stream));
    for(int iterations:options.iterations)for(int mode:options.modes){if(mode==Pure)run<Pure>(options,prop,iterations,stream);else if(mode==Pipelined)run<Pipelined>(options,prop,iterations,stream);else run<Serial>(options,prop,iterations,stream);}
    CUDA_CHECK(cudaStreamDestroy(stream));
  }catch(const std::exception& e){std::fprintf(stderr,"%s\n",e.what());return 1;}
}
