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

int main(int argc,char**argv){
  if(argc!=4 && argc!=5){fprintf(stderr,"usage: benchmark M N K [--metadata-only]\n");return 5;}
  const int M=std::stoi(argv[1]),N=std::stoi(argv[2]),K=std::stoi(argv[3]);
  if(M<=0 || N<=0 || K<=0 || M%16 || N%128 || K%64){fprintf(stderr,"unaligned shape\n");return 6;}
  CUDA(cudaSetDevice(0));
  cudaDeviceProp prop{}; CUDA(cudaGetDeviceProperties(&prop,0));
  cudaStream_t stream; CUDA(cudaStreamCreate(&stream));
  const int smem_size=sizeof(typename Kernel::SharedStorage);
  if(smem_size >= 48*1024)CUDA(cudaFuncSetAttribute(cutlass::Kernel<Kernel>,cudaFuncAttributeMaxDynamicSharedMemorySize,smem_size));
  int occupancy=0;CUDA(cudaOccupancyMaxActiveBlocksPerMultiprocessor(&occupancy,cutlass::Kernel<Kernel>,Kernel::kThreadCount,smem_size));
  cudaFuncAttributes attr{};CUDA(cudaFuncGetAttributes(&attr,cutlass::Kernel<Kernel>));
  printf("{\"device\":\"%s\",\"sms\":%d,\"m\":%d,\"n\":%d,\"k\":%d,\"tile\":[16,128,64],\"stages\":3,\"threads\":%d,\"dynamic_smem\":%d,\"regs_per_thread\":%d,\"max_active_blocks\":%d,\"grid\":[%d,%d,1]}\n",prop.name,prop.multiProcessorCount,M,N,K,Kernel::kThreadCount,smem_size,attr.numRegs,occupancy,(M+15)/16,(N+127)/128);
  fflush(stdout);
  if(argc==5 && std::string(argv[4])=="--metadata-only")return 0;
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
  CUT(gemm.run(stream));CUDA(cudaStreamSynchronize(stream));
  cublasHandle_t blas; BLAS(cublasCreate(&blas));BLAS(cublasSetStream(blas,stream));
  float alpha=1.f,beta=0.f;
  BLAS(cublasGemmEx(blas,CUBLAS_OP_N,CUBLAS_OP_N,N,M,K,&alpha,b,CUDA_R_16F,N,a,CUDA_R_16F,K,&beta,ref,CUDA_R_16F,N,CUBLAS_COMPUTE_32F,CUBLAS_GEMM_DEFAULT_TENSOR_OP));
  CUDA(cudaStreamSynchronize(stream));
  CUDA(cudaMemcpy(hD.data(),d,sz*sizeof(Element),cudaMemcpyDeviceToHost));
  CUDA(cudaMemcpy(hR.data(),ref,sz*sizeof(Element),cudaMemcpyDeviceToHost));
  float maxerr=0;size_t mismatches=0;
  for(size_t i=0;i<sz;++i){float err=std::abs(float(hD[i])-float(hR[i]));if(!std::isfinite(err))err=INFINITY;maxerr=std::max(maxerr,err);mismatches+=(err!=0);}
  printf("{\"correctness\":\"%s\",\"reference\":\"cuBLAS FP16 inputs FP32 accumulation\",\"elements\":%zu,\"max_abs_error\":%.9g,\"mismatches\":%zu}\n",maxerr==0?"PASS":"FAIL",sz,maxerr,mismatches);
  if(mismatches!=0)return 4;
  unsigned* flush;size_t flushbytes=512ull<<20;CUDA(cudaMalloc(&flush,flushbytes));CUDA(cudaMemsetAsync(flush,0,flushbytes,stream));
  cudaEvent_t start,end;CUDA(cudaEventCreate(&start));CUDA(cudaEventCreate(&end));
  for(int i=0;i<100;++i)CUT(gemm.run(stream)); CUDA(cudaStreamSynchronize(stream));
  std::ofstream samples("samples.csv");samples<<"mode,sample,time_us\n";
  for(int mode=0;mode<2;++mode){
    std::vector<double> times;
    for(int i=0;i<51;++i){
      if(mode){flush_l2<<<1024,256,0,stream>>>(flush,flushbytes/sizeof(unsigned));CUDA(cudaGetLastError());}
      CUDA(cudaEventRecord(start,stream));CUT(gemm.run(stream));CUDA(cudaEventRecord(end,stream));CUDA(cudaEventSynchronize(end));
      float ms;CUDA(cudaEventElapsedTime(&ms,start,end));double us=ms*1000.;times.push_back(us);samples<<(mode?"cold":"warm")<<","<<i<<","<<us<<"\n";
    }
    std::sort(times.begin(),times.end());printf("{\"mode\":\"%s\",\"samples\":51,\"median_us\":%.6f,\"p10_us\":%.6f,\"p90_us\":%.6f}\n",mode?"cold":"warm",times[25],times[5],times[45]);fflush(stdout);
  }
  cudaGraph_t graph;cudaGraphExec_t exec;
  CUDA(cudaStreamBeginCapture(stream,cudaStreamCaptureModeGlobal));
  for(int i=0;i<20;++i)CUT(gemm.run(stream));
  CUDA(cudaStreamEndCapture(stream,&graph));CUDA(cudaGraphInstantiate(&exec,graph,nullptr,nullptr,0));
  CUDA(cudaGraphLaunch(exec,stream));CUDA(cudaStreamSynchronize(stream));
  std::vector<double> graph_times;
  for(int i=0;i<11;++i){CUDA(cudaEventRecord(start,stream));CUDA(cudaGraphLaunch(exec,stream));CUDA(cudaEventRecord(end,stream));CUDA(cudaEventSynchronize(end));float ms;CUDA(cudaEventElapsedTime(&ms,start,end));double us=ms*50.;graph_times.push_back(us);samples<<"graph_per_kernel,"<<i<<","<<us<<"\n";}
  std::sort(graph_times.begin(),graph_times.end());printf("{\"mode\":\"graph_per_kernel\",\"samples\":11,\"kernels_per_graph\":20,\"median_us\":%.6f,\"p10_us\":%.6f,\"p90_us\":%.6f}\n",graph_times[5],graph_times[1],graph_times[9]);
  CUDA(cudaGraphExecDestroy(exec));CUDA(cudaGraphDestroy(graph));CUDA(cudaEventDestroy(start));CUDA(cudaEventDestroy(end));
  BLAS(cublasDestroy(blas));for(void* p:{(void*)a,(void*)b,(void*)c,(void*)d,(void*)ref,(void*)flush,workspace})if(p)CUDA(cudaFree(p));CUDA(cudaStreamDestroy(stream));
}
