window.INTERVIEW_QUESTIONS = [
  {
    "id": "q1",
    "anchorId": "tencent-inference",
    "title": "吞吐提升，延迟也合格吗？",
    "question": "从你列出的一个大模型中选一次本人主导的优化。最初瓶颈在哪里，你改了什么？在相同请求负载下，优化前后的吞吐、TTFT、TPOT 和尾延迟分别怎样？",
    "expected": [
      "先给模型、卡数、精度、并行配置、输入/输出长度分布、请求速率和 SLA 阈值；比较同一负载。",
      "用 profiler 或日志指出瓶颈和本人修改；逐项开关优化，区分绑核、算子、调度及并行策略的贡献。",
      "同时看吞吐、TTFT/TPOT 分位数、失败率与排队；更大 batch 提高吞吐可能恶化单请求延迟。",
      "拿出可复现的前后结果，不能仅凭单次 tokens/s 或平均延迟证明满足 SLA。"
    ],
    "followUp": "如果 TPOT 降了，但 TTFT 和总吞吐都变差，你还会说这次优化成功吗？请按业务目标解释。",
    "interviewerHint": "听他是否把“单用户快”和“系统总容量大”分开，并说明自己的实际改动；不要求记住特定数值。",
    "studySources": [
      {
        "title": "已学关联：TTFT 与 TPOT 的实际优化",
        "url": "https://tomyoung903.github.io/maas_docs/glm53-gb300-ttft-tpot-optimization/index.html"
      },
      {
        "title": "已学关联：DP8 的 TPOT 更好，其他指标却可能更差",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/dp8-vs-tp8-attention-kernel-breakdown/index.html"
      }
    ],
    "sources": [
      {
        "label": "vLLM：TTFT、TPOT、排队及端到端延迟定义",
        "url": "https://docs.vllm.ai/en/latest/design/metrics/"
      }
    ],
    "number": 1,
    "project": 1,
    "blockIndex": 0,
    "projectLabel": "项目经历",
    "claim": "开展 Qwen3.5、GLM5.2、Kimi2.5、DeepSeekv4 等大模型的推理性能测试与优化。结合 NUMA 绑核、rocBLAS 算子寻优、零开销调度、并行策略调整及量化配置，在满足 SLA 延迟要求和服务稳定性的前提下，提升推理吞吐、资源利用率及高并发场景下的性能。",
    "expectedAnswer": [
      "先给模型、卡数、精度、并行配置、输入/输出长度分布、请求速率和 SLA 阈值；比较同一负载。",
      "用 profiler 或日志指出瓶颈和本人修改；逐项开关优化，区分绑核、算子、调度及并行策略的贡献。",
      "同时看吞吐、TTFT/TPOT 分位数、失败率与排队；更大 batch 提高吞吐可能恶化单请求延迟。",
      "拿出可复现的前后结果，不能仅凭单次 tokens/s 或平均延迟证明满足 SLA。"
    ]
  },
  {
    "id": "q2",
    "anchorId": "tencent-inference",
    "title": "“零开销调度”到底省了什么？",
    "question": "你写到“零开销调度”。请先用一张时间线解释这个词在你项目里具体指什么：改前 CPU 和设备在等什么，改后消除了哪一段？你本人实现了哪部分？",
    "expected": [
      "先定义其项目里的实际机制和代码位置，不把它直接等同于某个通用开关，也不声称调度成本真的为零。",
      "分开 CPU 提交、设备 kernel 执行、同步/等待和空隙；说明改善的是其中哪一项。",
      "若使用 graph replay，能解释一次提交仍会执行多个 kernel、保留依赖，并说明形状变化如何处理。",
      "给出相同输入、batch 和精度下的前后时间线及端到端延迟，检查优化是否只在小 batch 有效。"
    ],
    "followUp": "假如一次提交后仍有几千个 kernel，减少 CPU 提交次数为什么可能更快？又为什么不一定更快？",
    "interviewerHint": "“零开销调度”是简历未定义的词。让他定义即可；graph replay 是条件追问，不预设他用过。",
    "studySources": [
      {
        "title": "已学关联：一次 graph launch 对应数千个设备节点",
        "url": "https://tomyoung903.github.io/maas_docs/glm52-gb300-cuda-graph-dependency-atlas/index.html"
      },
      {
        "title": "已学关联：kernel 固定开销与执行时间",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/glm52-gb300-dense-down-kernel-tutorial/index.html"
      }
    ],
    "sources": [
      {
        "label": "NVIDIA Nsight Compute：profile 范围与计时限制",
        "url": "https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html"
      }
    ],
    "number": 2,
    "project": 1,
    "blockIndex": 0,
    "projectLabel": "项目经历",
    "claim": "开展 Qwen3.5、GLM5.2、Kimi2.5、DeepSeekv4 等大模型的推理性能测试与优化。结合 NUMA 绑核、rocBLAS 算子寻优、零开销调度、并行策略调整及量化配置，在满足 SLA 延迟要求和服务稳定性的前提下，提升推理吞吐、资源利用率及高并发场景下的性能。",
    "expectedAnswer": [
      "先定义其项目里的实际机制和代码位置，不把它直接等同于某个通用开关，也不声称调度成本真的为零。",
      "分开 CPU 提交、设备 kernel 执行、同步/等待和空隙；说明改善的是其中哪一项。",
      "若使用 graph replay，能解释一次提交仍会执行多个 kernel、保留依赖，并说明形状变化如何处理。",
      "给出相同输入、batch 和精度下的前后时间线及端到端延迟，检查优化是否只在小 batch 有效。"
    ]
  },
  {
    "id": "q3",
    "anchorId": "tencent-vision",
    "title": "channels-last 为何更快？",
    "question": "在 lingbot-va、fastwam 或 ACT 中选一个你优化过的 Conv，给出真实输入尺寸。改成 channels-last 后，实际内存排列发生了什么，为什么更快？“达到 A800 的 100% 以上”又是怎样测出来的？",
    "expected": [
      "给出模型、训练/推理模式、batch、Conv 形状和原始/优化后耗时；说明比例分母及相同测试范围。",
      "区分逻辑 NCHW 维度与物理 strides：channels-last 让 C 连续，不是必须把张量 shape 改成 NHWC。",
      "结合所选后端 kernel、访存或布局转换解释收益；计算输入、权重及下游转换开销，不默认所有模型都会快。",
      "用逐项对照区分布局、编译、优化器融合和精度开关；确认数值/任务质量，避免跨精度或跨卡数的不公平比较。"
    ],
    "followUp": "如果一个 Conv 快了，但模型总时间没变，你会先查什么？能展示一次布局转换抵消收益的例子吗？",
    "interviewerHint": "channels-last 是存储方式。先听他能否用具体张量讲清楚，再看证据；MIOpen TF32 的硬件/版本支持须由他举证。",
    "studySources": [
      {
        "title": "已学关联：从张量和访存解释 kernel 时间",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/glm52-gb300-dense-down-kernel-tutorial/index.html"
      },
      {
        "title": "已学关联：单个 kernel 与完整执行流程",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/basic-kernel-understanding-first/index.html"
      }
    ],
    "sources": [
      {
        "label": "PyTorch：channels-last 保持维度顺序、改变 strides",
        "url": "https://docs.pytorch.org/tutorials/intermediate/memory_format_tutorial.html"
      },
      {
        "label": "MIOpen：数据类型与布局的支持边界",
        "url": "https://rocmdocs.amd.com/projects/MIOpen/en/latest/reference/data_type_support.html"
      }
    ],
    "number": 3,
    "project": 1,
    "blockIndex": 1,
    "projectLabel": "项目经历",
    "claim": "针对具身智能领域的 lingbot-va、fastwam、ACT 等模型，围绕 GEMM / Conv 的具体计算尺寸开展优化；通过调整卷积输入与权重的 channels-last 布局、使用 PyTorch / Apex 的 fused AdamW、启用 MIOpen TF32，以及对兼容的热点子图进行编译，改善计算与访存效率。在相关测试场景中，将性能由 A800 的约 60% 提升至 100% 以上。",
    "expectedAnswer": [
      "给出模型、训练/推理模式、batch、Conv 形状和原始/优化后耗时；说明比例分母及相同测试范围。",
      "区分逻辑 NCHW 维度与物理 strides：channels-last 让 C 连续，不是必须把张量 shape 改成 NHWC。",
      "结合所选后端 kernel、访存或布局转换解释收益；计算输入、权重及下游转换开销，不默认所有模型都会快。",
      "用逐项对照区分布局、编译、优化器融合和精度开关；确认数值/任务质量，避免跨精度或跨卡数的不公平比较。"
    ]
  },
  {
    "id": "q4",
    "anchorId": "summary-hardware",
    "title": "MFU 只有 30%，说明实现差吗？",
    "question": "假设一个热点 kernel 的有效算力只有峰值的 30%，但所有计算单元都有工作。能据此说还有 70% 性能可挖吗？你会再看哪些数据，并如何决定先改计算、访存还是调度？",
    "expected": [
      "不能把 MFU 当作启用计算单元的比例；先确认有效 FLOPs、精度峰值、计时范围和分母口径。",
      "估算运算量与字节量、算术强度和 roofline；理论字节下界不等于硬件实测 HBM 流量。",
      "再看访存/缓存、可发射 warp 或 wave、寄存器/共享存储限制、grid 覆盖及同步；低利用率有多种原因。",
      "选一个假设做单变量实验，并看 kernel 与整体关键路径是否改善；不能从 30% 直接推出三倍提速。"
    ],
    "followUp": "如果你判断是带宽问题，但实测带宽也很低，这一定推翻判断吗？还可能是什么？",
    "interviewerHint": "沿用你已学的“30% MFU ≠ 只开了 30% SM”。海光上允许用对应的 CU/wave/LDS 名称解释，不考 NVIDIA 专有名词。",
    "studySources": [
      {
        "title": "已学关联：30.84% MFU，全部 SM 都有工作",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/sparse-mla-30pct-mfu-sm-education/index.html"
      },
      {
        "title": "已学关联：decode roofline 及模型推算的边界",
        "url": "https://tomyoung903.github.io/maas_docs/glm52-flops/glm52_decode_roofline.html"
      }
    ],
    "sources": [
      {
        "label": "NVIDIA：roofline、访存及调度指标的解释",
        "url": "https://docs.nvidia.com/nsight-compute/ProfilingGuide/index.html"
      },
      {
        "label": "NVIDIA：低计算与低带宽利用率的排查",
        "url": "https://docs.nvidia.com/nsight-compute/ComputeTriage/"
      }
    ],
    "number": 4,
    "project": 2,
    "blockIndex": 0,
    "projectLabel": "个人总结",
    "claim": "硬件与性能分析：熟悉 GPU 架构及 Kernel 执行模型，理解 SM、SIMD、Warp、Thread、VGPR、SGPR、LDS 等计算与存储资源，以及 Grid / Block 调度机制。能够结合硬件参数与 Profiler 分析，定位计算、访存及通信瓶颈，开展算子与部署方案优化，并完成性能验证。",
    "expectedAnswer": [
      "不能把 MFU 当作启用计算单元的比例；先确认有效 FLOPs、精度峰值、计时范围和分母口径。",
      "估算运算量与字节量、算术强度和 roofline；理论字节下界不等于硬件实测 HBM 流量。",
      "再看访存/缓存、可发射 warp 或 wave、寄存器/共享存储限制、grid 覆盖及同步；低利用率有多种原因。",
      "选一个假设做单变量实验，并看 kernel 与整体关键路径是否改善；不能从 30% 直接推出三倍提速。"
    ]
  },
  {
    "id": "q5",
    "anchorId": "summary-serving",
    "title": "DP / TP 如何影响用户体验？",
    "question": "你说熟悉 DP、TP 和 PD 分离。请选一次实际并行策略调整，画出请求和计算在各卡上的分配：为什么换配置后，TPOT 可能更低，但 TTFT 或总吞吐反而更差？",
    "expected": [
      "先分清整模型多副本 DP、TP，以及只对 attention 做 DP；说明本人项目用的是哪一种，不把各 flag 一律相乘。",
      "结合本地 batch、权重/KV 驻留、通信和负载分布解释变化；PD 场景还需考虑 prefill 到达 decode 的节奏。",
      "保持请求数据、精度、缓存状态和总资源可比；客户端并发不等于每个 decode 步的实际 batch。",
      "拿出前后指标及时间线，区分机理解释和已测证据；不能仅凭减少通信就断言整体更快。"
    ],
    "followUp": "如果请求长度差异很大或重复前缀很多，路由策略会怎样改变这个结论？你会怎样做对照实验？",
    "interviewerHint": "重点核查数据归属、通信和测量口径。能说明自己没做过某种模式，比把所有并行术语混在一起更可信。",
    "studySources": [
      {
        "title": "已学关联：SGLang 并行策略的 rank / 分组",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/sglang-parallelism-mental-model/index.html"
      },
      {
        "title": "已学关联：DP8 与 TP8 的实测差异和证据边界",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/dp8-vs-tp8-attention-kernel-breakdown/index.html"
      }
    ],
    "sources": [
      {
        "label": "SGLang：DP、DP Attention 与路由的区别",
        "url": "https://github.com/sgl-project/sglang/blob/main/docs/docs/advanced_features/dp_dpa_smg_guide.mdx"
      }
    ],
    "number": 5,
    "project": 2,
    "blockIndex": 1,
    "projectLabel": "个人总结",
    "claim": "大模型推理与部署：熟悉 PyTorch、TensorFlow 及 vLLM、SGLang 推理引擎，理解 Continuous Batching、Prefix Caching、Chunked Prefill、Radix Attention 等机制。熟悉 TP / PP / DP / EP / CP 并行策略，具备 IFB 与 PD 分离部署经验；掌握 W8A8、W4A8、W4A16 及 KV Cache 量化部署方法。",
    "expectedAnswer": [
      "先分清整模型多副本 DP、TP，以及只对 attention 做 DP；说明本人项目用的是哪一种，不把各 flag 一律相乘。",
      "结合本地 batch、权重/KV 驻留、通信和负载分布解释变化；PD 场景还需考虑 prefill 到达 decode 的节奏。",
      "保持请求数据、精度、缓存状态和总资源可比；客户端并发不等于每个 decode 步的实际 batch。",
      "拿出前后指标及时间线，区分机理解释和已测证据；不能仅凭减少通信就断言整体更快。"
    ]
  },
  {
    "id": "q6",
    "anchorId": "summary-triton",
    "title": "Triton：FLOPs 翻倍，时间一定翻倍吗？",
    "question": "选一个你亲自写或修改过的 Triton 算子。若它是 GEMM，请给出 M/N/K、tile 和测试结果：固定 N/K，仅增大 M，为什么耗时可能先几乎不变，再明显上升？",
    "expected": [
      "说明本人修改范围、输入/输出形状和精度；若没写 GEMM，可用实际算子的工作划分解释，避免背模板。",
      "把输出 tile 映射为程序块，结合 grid、计算单元覆盖和资源占用解释并行余量、更多调度波次及边界填充。",
      "考虑固定启动开销、每块工作量及数据复用；自动调参切换也可能让局部曲线下降，不要求严格线性。",
      "展示多形状正确性和预热后计时，与库基线同口径比较，再验证整体收益；不只展示一个获胜尺寸。"
    ],
    "followUp": "如果 M 变大后反而有一个点更快，你怎样区分调参切换、测量噪声和错误实现？",
    "interviewerHint": "对应你已经看过的 M 扫描、tile 与 wave 图。听他能否把曲线连到实际 kernel 配置，而不只说“并行度更高”。",
    "studySources": [
      {
        "title": "已学关联：M 扫描、固定开销、tile 与 wave",
        "url": "https://tomyoung903.github.io/maas_docs/tmp/glm52-gb300-dense-down-kernel-tutorial/index.html"
      }
    ],
    "sources": [
      {
        "label": "Triton 官方 GEMM 教程：分块、复用与按 M/N/K 寻优",
        "url": "https://github.com/triton-lang/triton/blob/main/python/tutorials/03-matrix-multiplication.py"
      }
    ],
    "number": 6,
    "project": 2,
    "blockIndex": 2,
    "projectLabel": "个人总结",
    "claim": "算子开发基础：了解 Triton 的使用方法，能够借助 Triton 实现和优化部分算子，并结合实际模型场景验证优化效果。",
    "expectedAnswer": [
      "说明本人修改范围、输入/输出形状和精度；若没写 GEMM，可用实际算子的工作划分解释，避免背模板。",
      "把输出 tile 映射为程序块，结合 grid、计算单元覆盖和资源占用解释并行余量、更多调度波次及边界填充。",
      "考虑固定启动开销、每块工作量及数据复用；自动调参切换也可能让局部曲线下降，不要求严格线性。",
      "展示多形状正确性和预热后计时，与库基线同口径比较，再验证整体收益；不只展示一个获胜尺寸。"
    ]
  },
  {
    "id": "q7",
    "anchorId": "zhang-ai-tooling-experience",
    "title": "AI 工具使用经验",
    "question": "请介绍一下你使用 AI 工具的经验。",
    "expected": [],
    "number": 7,
    "project": 3,
    "blockIndex": 0,
    "projectLabel": "AI 工具使用",
    "claim": "请介绍一下你使用 AI 工具的经验。",
    "expectedAnswer": [],
    "sources": []
  },
  {
    "id": "q8",
    "anchorId": "zhang-ai-tooling-best-experience",
    "title": "最好的 AI 工具使用经历",
    "question": "请描述一次你使用 AI 工具时最好的经历。",
    "expected": [],
    "number": 8,
    "project": 3,
    "blockIndex": 1,
    "projectLabel": "AI 工具使用",
    "claim": "请描述一次你使用 AI 工具时最好的经历。",
    "expectedAnswer": [],
    "sources": []
  }
];
