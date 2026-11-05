#include <cuda_runtime.h>
#include <cublas_v2.h>
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <random>
#include <vector>
#include "cutlass/cutlass.h"
#include "cutlass/gemm/device/gemm.h"
#include "cutlass/epilogue/thread/linear_combination.h"
#include "cutlass/gemm/threadblock/threadblock_swizzle.h"

#define CUDA(x) do {auto e=(x); if(e!=cudaSuccess){fprintf(stderr,"CUDA %s at %d\n",cudaGetErrorString(e),__LINE__);exit(1);}}while(0)
#define CUT(x) do {auto e=(x); if(e!=cutlass::Status::kSuccess){fprintf(stderr,"CUTLASS %d at %d\n",int(e),__LINE__);exit(2);}}while(0)
#define BLAS(x) do {auto e=(x); if(e!=CUBLAS_STATUS_SUCCESS){fprintf(stderr,"CUBLAS %d at %d\n",int(e),__LINE__);exit(3);}}while(0)
using Element = cutlass::half_t;
using RowLayout = cutlass::layout::RowMajor;
using Gemm = cutlass::gemm::device::Gemm<
  Element,RowLayout,Element,RowLayout,Element,RowLayout,float,
  cutlass::arch::OpClassTensorOp,cutlass::arch::Sm80,
  cutlass::gemm::GemmShape<16,128,64>,
  cutlass::gemm::GemmShape<16,32,64>,
  cutlass::gemm::GemmShape<16,8,16>,
  cutlass::epilogue::thread::LinearCombination<Element,8,float,float>,
  cutlass::gemm::threadblock::GemmIdentityThreadblockSwizzle<1>,3,8,8,false>;
using Kernel = typename Gemm::GemmKernel;

// Touch far more than L2; launch before (outside) the measured interval.
__global__ void flush_l2(unsigned* p, size_t n) {
  for(size_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=size_t(gridDim.x)*blockDim.x)
    p[i] = p[i] + 1;
}

// The read-only eviction buffer has a deterministic nonzero integer pattern.
__global__ void init_read_buffer(unsigned* p, size_t n) {
  for (size_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=size_t(gridDim.x)*blockDim.x)
    p[i]=unsigned(i*1664525u+1013904223u);
}

// Explicit .cg loads bypass L1 and allocate in L2. Each block stores one
// checksum word: 1024 blocks make only 4 KiB of output dirty, versus 512 MiB
// of writes in the original RMW eviction kernel.
__global__ void evict_read_cg(const unsigned* p, size_t n, unsigned* checksums) {
  unsigned sum=0;
  for (size_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=size_t(gridDim.x)*blockDim.x) {
    unsigned value;
    asm volatile("ld.global.cg.u32 %0, [%1];" : "=r"(value) : "l"(p+i) : "memory");
    sum+=value;
  }
  __shared__ unsigned partial[256];
  partial[threadIdx.x]=sum;
  __syncthreads();
  for (unsigned offset=128;offset;offset>>=1) {
    if (threadIdx.x<offset) partial[threadIdx.x]+=partial[threadIdx.x+offset];
    __syncthreads();
  }
  if (threadIdx.x==0) checksums[blockIdx.x]=partial[0];
}

// Separate untimed kernel allows memory traffic to settle while keeping the
// device active. This also changes scheduling/clock state, so it is a control,
// not proof that a measured difference is exclusively dirty writeback.
__global__ void wait_device_ns(unsigned long long duration_ns) {
  unsigned long long start,now;
  asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(start));
  do { asm volatile("mov.u64 %0, %%globaltimer;" : "=l"(now)); }
  while (now-start<duration_ns);
}

__global__ void prep_empty() { asm volatile("" ::: "memory"); }
__global__ void prep_shared_only() {
  extern __shared__ unsigned storage[];
  volatile unsigned* p=storage;
  p[threadIdx.x]=threadIdx.x;
}

constexpr int mode_count=7;
const char* mode_names[]={"ro_then_no_write","ro_then_empty", "ro_then_dirty4mib",
                         "ro_then_dirty16mib","ro_then_dirty32mib",
                         "ro_then_dirty64mib","ro_then_dirty128mib"};
constexpr size_t dirty_bytes[mode_count]={0,0,4ull<<20,16ull<<20,32ull<<20,64ull<<20,128ull<<20};

int main(int argc,char**argv){
  if(argc!=4){fprintf(stderr,"usage: benchmark M N K\n");return 5;}
  const int M=std::stoi(argv[1]),N=std::stoi(argv[2]),K=std::stoi(argv[3]);
  if(M<=0 || N<=0 || K<=0 || M%16 || N%128 || K%64){fprintf(stderr,"unaligned shape\n");return 6;}
  const int repeats=std::getenv("CACHE_CONTROL_REPEATS")?std::stoi(std::getenv("CACHE_CONTROL_REPEATS")):51;
  if(repeats<=0 || repeats>1000) return 7;
  std::vector<int> modes{0,1,2,3,4,5,6};
  if(const char* requested=std::getenv("CACHE_CONTROL_MODE")) {
    modes.clear();
    for(int i=0;i<mode_count;++i)if(std::string(requested)==mode_names[i])modes.push_back(i);
    if(modes.empty()){fprintf(stderr,"unknown mode\n");return 8;}
  }
  CUDA(cudaSetDevice(0));
  cudaDeviceProp prop{}; CUDA(cudaGetDeviceProperties(&prop,0));
  cudaStream_t stream; CUDA(cudaStreamCreate(&stream));
  const int smem_size=sizeof(typename Kernel::SharedStorage);
  if(smem_size >= 48*1024)CUDA(cudaFuncSetAttribute(cutlass::Kernel<Kernel>,cudaFuncAttributeMaxDynamicSharedMemorySize,smem_size));
  CUDA(cudaFuncSetAttribute(prep_shared_only,cudaFuncAttributeMaxDynamicSharedMemorySize,smem_size));
  const bool matched=true;  // Fixed across every mode in this dirty-footprint sweep.
  if(matched){
    CUDA(cudaFuncSetAttribute(cutlass::Kernel<Kernel>,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(flush_l2,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(init_read_buffer,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(evict_read_cg,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(wait_device_ns,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(prep_empty,cudaFuncAttributePreferredSharedMemoryCarveout,100));
    CUDA(cudaFuncSetAttribute(prep_shared_only,cudaFuncAttributePreferredSharedMemoryCarveout,100));
  }
  printf("{\"matched_carveout_requested\":%s,\"carveout_setting\":\"%s\"}\n",matched?"true":"false",matched?"100_percent_preference_all_kernels":"default");
  int occupancy=0;CUDA(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occupancy,cutlass::Kernel<Kernel>,Kernel::kThreadCount,smem_size));
  cudaFuncAttributes attr{};CUDA(cudaFuncGetAttributes(&attr,cutlass::Kernel<Kernel>));
  printf("{\"device\":\"%s\",\"sms\":%d,\"m\":%d,\"n\":%d,\"k\":%d,\"tile\":[16,128,64],\"stages\":3,\"threads\":%d,\"dynamic_smem\":%d,\"regs_per_thread\":%d,\"max_active_blocks\":%d,\"grid\":[%d,%d,1],\"repeats\":%d}\n",prop.name,prop.multiProcessorCount,M,N,K,Kernel::kThreadCount,smem_size,attr.numRegs,occupancy,(M+15)/16,(N+127)/128,repeats);
  fflush(stdout);
  size_t sz=size_t(M)*N, asz=size_t(M)*K, bsz=size_t(K)*N;
  std::vector<Element> hA(asz),hB(bsz),hD(sz),hR(sz);
  std::mt19937 rng(17);
  for(size_t i=0;i<asz;++i)hA[i]=Element(float(int(rng()%17)-8)*0.125f);
  for(size_t i=0;i<bsz;++i)hB[i]=Element(float(int(rng()%17)-8)*0.125f);
  Element *a,*b,*c,*d,*ref;
  CUDA(cudaMalloc(&a,asz*sizeof(Element))); CUDA(cudaMalloc(&b,bsz*sizeof(Element)));
  CUDA(cudaMalloc(&c,sz*sizeof(Element))); CUDA(cudaMalloc(&d,sz*sizeof(Element))); CUDA(cudaMalloc(&ref,sz*sizeof(Element)));
  CUDA(cudaMemcpy(a,hA.data(),asz*sizeof(Element),cudaMemcpyHostToDevice));
  CUDA(cudaMemcpy(b,hB.data(),bsz*sizeof(Element),cudaMemcpyHostToDevice));
  CUDA(cudaMemset(c,0,sz*sizeof(Element)));
  typename Gemm::Arguments args({M,N,K},{a,K},{b,N},{c,N},{d,N},{1.f,0.f});
  Gemm gemm; CUT(gemm.can_implement(args));
  void* workspace=nullptr; size_t ws=gemm.get_workspace_size(args); if(ws)CUDA(cudaMalloc(&workspace,ws));
  CUT(gemm.initialize(args,workspace,stream));
  std::ofstream launches("launches.csv");launches<<"gemm_index,phase,mode,sample,round\n";
  size_t gemm_index=0;
  auto record=[&](const char* phase,const char* mode,int sample,int round){
    const size_t index=gemm_index++;
    launches<<index<<","<<phase<<","<<mode<<","<<sample<<","<<round<<"\n";
    return index;
  };
  record("correctness","none",-1,-1);
  CUT(gemm.run(stream));CUDA(cudaStreamSynchronize(stream));
  cublasHandle_t blas; BLAS(cublasCreate(&blas));BLAS(cublasSetStream(blas,stream));
  float alpha=1.f,beta=0.f;
  BLAS(cublasGemmEx(blas,CUBLAS_OP_N,CUBLAS_OP_N,N,M,K,&alpha,b,CUDA_R_16F,N,a,CUDA_R_16F,K,&beta,ref,CUDA_R_16F,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT_TENSOR_OP));
  CUDA(cudaStreamSynchronize(stream));
  CUDA(cudaMemcpy(hD.data(),d,sz*sizeof(Element),cudaMemcpyDeviceToHost));
  CUDA(cudaMemcpy(hR.data(),ref,sz*sizeof(Element),cudaMemcpyDeviceToHost));
  float maxerr=0;size_t mismatches=0;
  for(size_t i=0;i<sz;++i){float err=std::abs(float(hD[i])-float(hR[i]));if(!std::isfinite(err))err=INFINITY;maxerr=std::max(maxerr,err);mismatches+=(err!=0);}
  printf("{\"correctness\":\"%s\",\"reference\":\"cuBLAS\",\"elements\":%zu,\"max_abs_error\":%.9g,\"mismatches\":%zu}\n",maxerr==0?"PASS":"FAIL",sz,maxerr,mismatches);
  if(mismatches!=0)return 4;

  constexpr size_t flushbytes=512ull<<20;
  constexpr size_t count=flushbytes/sizeof(unsigned);
  constexpr unsigned blocks=1024,threads=256;
  unsigned *flush,*readbuf,*pattern_rmw,*checksums;
  CUDA(cudaMalloc(&flush,flushbytes));CUDA(cudaMemsetAsync(flush,0,flushbytes,stream));
  CUDA(cudaMalloc(&readbuf,flushbytes));CUDA(cudaMalloc(&checksums,blocks*sizeof(unsigned)));
  CUDA(cudaMalloc(&pattern_rmw,flushbytes));
  init_read_buffer<<<blocks,threads,0,stream>>>(pattern_rmw,count);CUDA(cudaGetLastError());
  init_read_buffer<<<blocks,threads,0,stream>>>(readbuf,count);CUDA(cudaGetLastError());
  evict_read_cg<<<blocks,threads,0,stream>>>(readbuf,count,checksums);CUDA(cudaGetLastError());
  evict_read_cg<<<blocks,threads,0,stream>>>(readbuf,count,checksums);CUDA(cudaGetLastError());
  CUDA(cudaStreamSynchronize(stream));
  std::vector<unsigned> hchecks(blocks);CUDA(cudaMemcpy(hchecks.data(),checksums,blocks*sizeof(unsigned),cudaMemcpyDeviceToHost));
  unsigned check_errors=0;
  const unsigned long long trips=count/(blocks*threads), stride=blocks*threads;
  for(unsigned block=0;block<blocks;++block){
    unsigned long long first=block*threads;
    unsigned long long sum_indices=trips*(threads*first+threads*(threads-1)/2)+threads*stride*trips*(trips-1)/2;
    unsigned expected=unsigned(sum_indices*1664525ull+trips*threads*1013904223ull);
    check_errors+=(hchecks[block]!=expected);
  }
  printf("{\"eviction_checksum\":\"%s\",\"blocks\":%u,\"errors\":%u,\"read_bytes\":%zu,\"checksum_write_bytes\":%zu}\n",check_errors?"FAIL":"PASS",blocks,check_errors,flushbytes,blocks*sizeof(unsigned));
  if(check_errors)return 9;

  cudaEvent_t start,end;CUDA(cudaEventCreate(&start));CUDA(cudaEventCreate(&end));
  for(int i=0;i<100;++i){record("warmup","none",i,-1);CUT(gemm.run(stream));}
  CUDA(cudaStreamSynchronize(stream));
  std::ofstream samples("samples.csv");samples<<"mode,sample,time_us,round,gemm_index\n";
  std::mt19937 order_rng(20261105);
  std::vector<double> times[mode_count];
  for(int round=0;round<repeats;++round){
    auto order=modes;std::shuffle(order.begin(),order.end(),order_rng);
    for(int mode:order){
      // Same priming GEMM before every mode establishes a repeatable input state.
      record("prime",mode_names[mode],round,round);CUT(gemm.run(stream));
      // Common clean-cache preparation for every sample. Then introduce
      // a controlled additional dirty footprint, excluded from GEMM timing.
      evict_read_cg<<<blocks,threads,0,stream>>>(readbuf,count,checksums);CUDA(cudaGetLastError());
      if(mode==1){prep_empty<<<blocks,threads,0,stream>>>();CUDA(cudaGetLastError());}
      if(dirty_bytes[mode]){
        flush_l2<<<blocks,threads,0,stream>>>(pattern_rmw,dirty_bytes[mode]/sizeof(unsigned));CUDA(cudaGetLastError());
      }
      auto index=record("measure",mode_names[mode],round,round);
      CUDA(cudaEventRecord(start,stream));CUT(gemm.run(stream));CUDA(cudaEventRecord(end,stream));CUDA(cudaEventSynchronize(end));
      float ms;CUDA(cudaEventElapsedTime(&ms,start,end));double us=ms*1000.;times[mode].push_back(us);
      samples<<mode_names[mode]<<","<<round<<","<<us<<","<<round<<","<<index<<"\n";
    }
  }
  for(int mode:modes){
    auto v=times[mode];std::sort(v.begin(),v.end());
    printf("{\"mode\":\"%s\",\"samples\":%zu,\"median_event_us\":%.6f,\"p10_us\":%.6f,\"p90_us\":%.6f}\n",mode_names[mode],v.size(),v[v.size()/2],v[v.size()/10],v[(v.size()*9)/10]);
  }
  printf("{\"gemm_launches\":%zu,\"mode_order_seed\":20261105,\"common_read_eviction_bytes\":%zu}\n",gemm_index,flushbytes);fflush(stdout);
  for(int mode:modes)printf("{\"mode\":\"%s\",\"additional_rmw_bytes\":%zu}\n",mode_names[mode],dirty_bytes[mode]);
  // Recheck the complete checksum after all read-only modes.
  CUDA(cudaMemcpy(hchecks.data(),checksums,blocks*sizeof(unsigned),cudaMemcpyDeviceToHost));
  check_errors=0;
  for(unsigned block=0;block<blocks;++block){
    unsigned long long first=block*threads;
    unsigned long long sum_indices=trips*(threads*first+threads*(threads-1)/2)+threads*stride*trips*(trips-1)/2;
    unsigned expected=unsigned(sum_indices*1664525ull+trips*threads*1013904223ull);
    check_errors+=(hchecks[block]!=expected);
  }
  printf("{\"final_eviction_checksum\":\"%s\",\"errors\":%u}\n",check_errors?"FAIL":"PASS",check_errors);
  if(check_errors)return 10;
  CUDA(cudaEventDestroy(start));CUDA(cudaEventDestroy(end));
  BLAS(cublasDestroy(blas));for(void* p:{(void*)a,(void*)b,(void*)c,(void*)d,(void*)ref,(void*)flush,(void*)readbuf,(void*)pattern_rmw,(void*)checksums,workspace})if(p)CUDA(cudaFree(p));CUDA(cudaStreamDestroy(stream));
}
