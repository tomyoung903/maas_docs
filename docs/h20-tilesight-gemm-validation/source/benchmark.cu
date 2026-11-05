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
#include "cutlass/gemm/collective/collective_builder.hpp"
#include "cutlass/epilogue/collective/collective_builder.hpp"
#include "cutlass/gemm/kernel/gemm_universal.hpp"
#include "cutlass/gemm/device/gemm_universal_adapter.h"
#include "cutlass/util/packed_stride.hpp"

#define CUDA(x) do {auto e=(x); if(e!=cudaSuccess){fprintf(stderr,"CUDA %s at %d\n",cudaGetErrorString(e),__LINE__);exit(1);}}while(0)
#define CUT(x) do {auto e=(x); if(e!=cutlass::Status::kSuccess){fprintf(stderr,"CUTLASS %d at %d\n",int(e),__LINE__);exit(2);}}while(0)
#define BLAS(x) do {auto e=(x); if(e!=CUBLAS_STATUS_SUCCESS){fprintf(stderr,"CUBLAS %d at %d\n",int(e),__LINE__);exit(3);}}while(0)
using cute::Shape;
using cute::_128;
using cute::_64;
using cute::_1;
using cute::make_shape;
using Element = cutlass::half_t;
using RowLayout = cutlass::layout::RowMajor;
using Tile = Shape<_128,_128,_64>;
using Cluster = Shape<_1,_1,_1>;
using Mainloop = typename cutlass::gemm::collective::CollectiveBuilder<
    cutlass::arch::Sm90,cutlass::arch::OpClassTensorOp,
    Element,RowLayout,8,Element,RowLayout,8,float,Tile,Cluster,
    cutlass::gemm::collective::StageCount<3>,cutlass::gemm::KernelTmaWarpSpecialized>::CollectiveOp;
using Epilogue = typename cutlass::epilogue::collective::CollectiveBuilder<
    cutlass::arch::Sm90,cutlass::arch::OpClassTensorOp,Tile,Cluster,
    cutlass::epilogue::collective::EpilogueTileAuto,float,float,
    Element,RowLayout,8,Element,RowLayout,8,cutlass::epilogue::NoSmemWarpSpecialized>::CollectiveOp;
using Kernel = cutlass::gemm::kernel::GemmUniversal<Shape<int,int,int,int>,Mainloop,Epilogue>;
using Gemm = cutlass::gemm::device::GemmUniversalAdapter<Kernel>;

// Touch far more than L2; launch before (outside) the measured interval.
__global__ void flush_l2(unsigned* p, size_t n) {
  for(size_t i=blockIdx.x*blockDim.x+threadIdx.x;i<n;i+=size_t(gridDim.x)*blockDim.x)
    p[i] = p[i] + 1;
}

int main(int argc,char**argv){
  if(argc!=4){fprintf(stderr,"usage: benchmark M N K\n");return 5;}
  const int M=std::stoi(argv[1]),N=std::stoi(argv[2]),K=std::stoi(argv[3]);
  if(M<=0 || N<=0 || K<=0 || M%128 || N%128 || K%64){fprintf(stderr,"unaligned shape\n");return 6;}
  CUDA(cudaSetDevice(0));
  cudaDeviceProp prop{}; CUDA(cudaGetDeviceProperties(&prop,0));
  cudaStream_t stream; CUDA(cudaStreamCreate(&stream));
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
  auto sa=cutlass::make_cute_packed_stride(typename Kernel::StrideA{},make_shape(M,K,1));
  auto sb=cutlass::make_cute_packed_stride(typename Kernel::StrideB{},make_shape(N,K,1));
  auto sc=cutlass::make_cute_packed_stride(typename Kernel::StrideC{},make_shape(M,N,1));
  auto sd=cutlass::make_cute_packed_stride(typename Kernel::StrideD{},make_shape(M,N,1));
  typename Gemm::Arguments args{cutlass::gemm::GemmUniversalMode::kGemm,
    {M,N,K,1},{a,sa,b,sb},{{1.f,0.f},c,sc,d,sd}};
  Gemm gemm; CUT(gemm.can_implement(args));
  void* workspace=nullptr; size_t ws=gemm.get_workspace_size(args); if(ws)CUDA(cudaMalloc(&workspace,ws));
  CUT(gemm.initialize(args,workspace,stream));
  int occupancy=Gemm::maximum_active_blocks();
  cudaFuncAttributes attr{};CUDA(cudaFuncGetAttributes(&attr,cutlass::device_kernel<Kernel>));
  auto grid=Gemm::get_grid_shape(args);
  printf("{\"device\":\"%s\",\"sms\":%d,\"m\":%d,\"n\":%d,\"k\":%d,\"tile\":[128,128,64],\"stages\":3,\"threads\":%u,\"dynamic_smem\":%d,\"regs_per_thread\":%d,\"max_active_blocks\":%d,\"grid\":[%u,%u,%u]}\n",prop.name,prop.multiProcessorCount,M,N,K,Kernel::MaxThreadsPerBlock,Kernel::SharedStorageSize,attr.numRegs,occupancy,grid.x,grid.y,grid.z);
  fflush(stdout);
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
