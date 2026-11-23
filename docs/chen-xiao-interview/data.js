window.INTERVIEW_QUESTIONS = [
  {
    "id": "q1",
    "anchorId": "cx-dycp-1",
    "title": "DyCP：其他 rank 在等什么？",
    "question": "请口头按先后顺序讲一遍 decode 时的一层：没有 DyCP 时，长请求所在的 DP rank 在算什么，其他 rank 在等哪一次通信？DyCP 把哪一段计算挪走了，挪到了哪里？",
    "expected": [
      "说清同步点：MoE 层的 dispatch 和 combine 是所有 rank 一起做的集合通信，每层都要等最慢的 rank 算完 attention。所以每层的时间由最慢的 rank 决定，其他 rank 空等。",
      "说清为什么 DP 度数越大越糟：请求长度是重尾分布，N 个 rank 取最大值，N 越大越容易抽到长请求。",
      "说清动态 CP 做了什么：长请求的 KV cache 分到同一个 Domain 里有余量的几个 rank 上，每个 rank 只对自己那一段上下文算 attention，再把各段结果合并。合并要用每段的 softmax 归一化项（LSE），不是简单相加。",
      "说出代价：每层多一次合并通信；CUDA graph 要按 batch 和 CP 请求数两个维度抓；KV 容量要跨 rank 统一管理。"
    ],
    "judgement": "良好：能按先后顺序讲清一层里的同步点（其他 rank 等的是 MoE 的 dispatch 和 combine），知道合并要用 LSE，收益数字能说清负载和基线。一般：只会说“负载均衡”，讲不出其他 rank 在等哪一次通信。较差：说不清 DP、CP、EP 各自切的是什么。",
    "evidence": "RFC 列了 11 位 co-author。请他说明自己负责哪几个模块（Scheduler、KV Cache Manager、Attention 后端等），以及 vLLM 主仓的 PR 为什么关闭。",
    "followUp": "4×H800×8 上 DeepSeek R1 的 “20%∼100%” 是哪个指标？为什么区间这么宽？Kimi K2.5 灰度的 8% TPOT 是怎么对照出来的？",
    "interviewerHint": "优先级：必问。这是他署名最清楚的一项，RFC 和两个 PR 都在他本人账号下。简历写“待合入”，公开记录是：vLLM 主仓 PR #44967 已于 2026-09-16 关闭且未合并，vLLM-Ascend PR #10225 仍是 WIP。参考答案里的机制来自他的 RFC 原文；收益数字是他的自述，未核实。",
    "studySources": [
      {
        "title": "已学关联：HY4 prefill，一层的逐步讲解",
        "url": "https://tomyoung903.github.io/maas_docs/hy4-100k-prefill/"
      }
    ],
    "sources": [
      {
        "label": "RFC：Support Dynamic Context Parallelism（vllm#29295）",
        "url": "https://github.com/vllm-project/vllm/issues/29295"
      },
      {
        "label": "vLLM PR #44967（WIP，已关闭）",
        "url": "https://github.com/vllm-project/vllm/pull/44967"
      },
      {
        "label": "vLLM-Ascend PR #10225（WIP）",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/10225"
      }
    ],
    "number": 1,
    "project": 1,
    "blockIndex": 0,
    "projectLabel": "跨 DP 动态调度框架 (DyCP)（特性 Owner）",
    "claim": "问题与规模效应：MoE 的 dispatch & combine 构成强同步，attn 耗时由最慢的 DP rank 决定；线上观察该不均衡随 DP 度数系统性恶化（长度重尾，而 barrier 取 N 个 rank 的 max）(DyCP RFC)。",
    "expectedAnswer": [
      "说清同步点：MoE 层的 dispatch 和 combine 是所有 rank 一起做的集合通信，每层都要等最慢的 rank 算完 attention。所以每层的时间由最慢的 rank 决定，其他 rank 空等。",
      "说清为什么 DP 度数越大越糟：请求长度是重尾分布，N 个 rank 取最大值，N 越大越容易抽到长请求。",
      "说清动态 CP 做了什么：长请求的 KV cache 分到同一个 Domain 里有余量的几个 rank 上，每个 rank 只对自己那一段上下文算 attention，再把各段结果合并。合并要用每段的 softmax 归一化项（LSE），不是简单相加。",
      "说出代价：每层多一次合并通信；CUDA graph 要按 batch 和 CP 请求数两个维度抓；KV 容量要跨 rank 统一管理。"
    ]
  },
  {
    "id": "q2",
    "anchorId": "cx-pd-3",
    "title": "PP 为什么能让 Prefill 吞吐提升 30%？",
    "question": "你写 PP 让 DeepSeek R1 的 Prefill 吞吐提升 30%。一个请求的一次前向在 PP 下同一时刻只有一个 stage 在算，那这 30% 是从哪里来的？对照组的卡数、并行配置、并发和输入长度各是多少？",
    "expected": [
      "承认单次前向不会因为 PP 变快：各 stage 依次执行，同一时刻只有一个 stage 在算这个 pass。",
      "收益来源说得具体：流水线里同时有多个 chunk 或多个请求时，各 stage 才能同时忙；相对 TP，PP 没有每层一次的集合通信，只在 stage 边界传一次激活。",
      "给出对照组和负载：同样的卡数下，TP 多少对 TP×PP 多少，并发多少，输入多长。并发为 1 的短请求不应该有收益。",
      "解释手动划分 layers 的依据：各 stage 的耗时要接近，最慢的 stage 决定吞吐；同时要看每张卡的显存。"
    ],
    "judgement": "良好：主动说出“单个 pass 不会变快”，并给出对照组和负载。一般：只说“减少了通信”，给不出配置。较差：认为 PP 让单个请求的计算变快。",
    "followUp": "GQA 的 KV cache 为什么需要 reshard，而 MLA 的不需要？reshard 的并行化具体并行了什么？",
    "interviewerHint": "优先级：时间够再问。我们自己测过：HY4 在 PP4 下，一个 pass 装得下的请求同一时刻只用一张卡，N 个 chunk 的请求大约需要 N+3 个 stage 时间。我们还有过一个“重新划分层有收益”的说法，后来被否定并撤回，所以要问清他的划分收益是怎么量的。追问的参考（我的推理，未对照他的代码）：MLA 缓存的是所有 head 共用的压缩隐变量，各 TP rank 上内容相同，两侧 TP 度数不同也能直接用；GQA 缓存的是按 head 切开的 K、V，TP 把 head 分到各 rank，两侧 TP 度数不同就要重新分组。",
    "studySources": [
      {
        "title": "已学关联：HY4 prefill，一层的逐步讲解",
        "url": "https://tomyoung903.github.io/maas_docs/hy4-100k-prefill/"
      },
      {
        "title": "已学关联：PP 异步深度在真实 P/D 上的实测",
        "url": "https://tomyoung903.github.io/maas_docs/glm53-pp-async-depth-real-comparison/"
      }
    ],
    "sources": [
      {
        "label": "PD PP：vllm-ascend#4054",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/4054"
      },
      {
        "label": "PD GQA：vllm-ascend#2947",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/2947"
      }
    ],
    "number": 2,
    "project": 2,
    "blockIndex": 2,
    "projectLabel": "PD 分离架构核心开发",
    "claim": "PP 支持：在 PD connector 中实现 PP 的拓扑感知，为 PD 分离引入 PP 与 TP 异构；分析 PP 的性能收益并实现 PP layers 手动划分，使 DeepSeek R1 与 Qwen3-235B 的 Prefill 吞吐分别提升 30% 和 25% (PD PP)。",
    "expectedAnswer": [
      "承认单次前向不会因为 PP 变快：各 stage 依次执行，同一时刻只有一个 stage 在算这个 pass。",
      "收益来源说得具体：流水线里同时有多个 chunk 或多个请求时，各 stage 才能同时忙；相对 TP，PP 没有每层一次的集合通信，只在 stage 边界传一次激活。",
      "给出对照组和负载：同样的卡数下，TP 多少对 TP×PP 多少，并发多少，输入多长。并发为 1 的短请求不应该有收益。",
      "解释手动划分 layers 的依据：各 stage 的耗时要接近，最慢的 stage 决定吞吐；同时要看每张卡的显存。"
    ]
  },
  {
    "id": "q3",
    "anchorId": "cx-dsa-2",
    "title": "Indexer：336% 和 30% 为什么差十倍？",
    "question": "同一个方案，DeepSeek V3.2 在昇腾 910C 上 Prefill 吞吐提升 336%，在 H200 上是 30%。改之前，Indexer 和稀疏 gather 在两种芯片上各占 Prefill 时间的多少？这一项里哪部分是你本人实现的？",
    "expected": [
      "先讲清 Indexer 算什么：每个 query token 对它之前的所有 token 各算一个分数，再取 top-k，后面的 attention 只看选中的 token。8k 上下文时一层约有 8k × 8k 个分数。",
      "讲清为什么 TP 帮不上：TP 是把权重切开、各卡算一部分再求和；Indexer 要拿到完整的分数才能做 top-k，所以 TP 组内每张卡都把整个 Indexer 算一遍，TP 越大重复越多。",
      "讲清 CP 怎么省：按 query token 把序列分给各卡，每张卡只算 1/CP 的行，Indexer 的计算量和按 top-k 结果取 KV 的访存量都降到 1/CP。",
      "用时间占比解释两个数字：吞吐提升 336% 相当于每个 token 的时间降到原来的 23%，被消掉的部分在改之前占了 Prefill 的大部分；30% 说明这部分在 H200 上占比小得多。他应该能给出改前改后的分项时间，并解释 910C 上为什么占比这么高。"
    ],
    "judgement": "良好：能给出分项时间并用占比解释两个数字，说清自己写的是哪部分。一般：机制讲得清，但数字只能复述。较差：说不清 Indexer 的输入输出，或说不清自己的贡献。",
    "evidence": "请他口头说出自己的代码在哪个仓库、哪个 PR 编号，事后对照公开记录核对。简历链接的 RFC，以及 RFC 里引用的昇腾实现 PR，都不在他名下。",
    "followUp": "TP→CP→TP 的状态转换发生在一层里的哪两个位置？转换时要传什么数据？",
    "interviewerHint": "优先级：必问。公开记录：DSA-CP RFC（vllm#30055）由他人提交；RFC 引用的昇腾实现 PR #4702 也由他人提交，commit 和 co-author 里没有他。简历写的是“在 vLLM 实现”，H200 的数字可能来自没有公开的 GPU 版本，需要他自己说明。我们的参照（HY4，不是 DeepSeek V3.2）：100k 冷 prefill 里 Indexer 打分加 Top-K 约占 GPU kernel 时间的 4.7%，78 层里只有 22 层跑 Indexer。",
    "studySources": [
      {
        "title": "已学关联：HY4 prefill，一层的逐步讲解",
        "url": "https://tomyoung903.github.io/maas_docs/hy4-100k-prefill/"
      }
    ],
    "sources": [
      {
        "label": "RFC：Sharded Context Parallelism for Deepseek DSA（vllm#30055）",
        "url": "https://github.com/vllm-project/vllm/issues/30055"
      },
      {
        "label": "RFC 引用的昇腾实现：vllm-ascend#4702",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/4702"
      }
    ],
    "number": 3,
    "project": 3,
    "blockIndex": 1,
    "projectLabel": "DeepSeek Sparse Attn 分片上下文并行 (Sharded CP)",
    "claim": "方案与实现：在 vLLM 实现 Prefill 的 TP→CP→TP 状态转换，attn 与 MoE 阶段转换为 CP，使 Indexer 计算量与稀疏 gather 访存量降至 1/CP。8k 上下文下，DeepSeek V3.2 在昇腾 910C 上 Prefill 吞吐提升 336%、在 H200 上提升 30%；DeepSeek V4 在 H200 上吞吐提升 15%。",
    "expectedAnswer": [
      "先讲清 Indexer 算什么：每个 query token 对它之前的所有 token 各算一个分数，再取 top-k，后面的 attention 只看选中的 token。8k 上下文时一层约有 8k × 8k 个分数。",
      "讲清为什么 TP 帮不上：TP 是把权重切开、各卡算一部分再求和；Indexer 要拿到完整的分数才能做 top-k，所以 TP 组内每张卡都把整个 Indexer 算一遍，TP 越大重复越多。",
      "讲清 CP 怎么省：按 query token 把序列分给各卡，每张卡只算 1/CP 的行，Indexer 的计算量和按 top-k 结果取 KV 的访存量都降到 1/CP。",
      "用时间占比解释两个数字：吞吐提升 336% 相当于每个 token 的时间降到原来的 23%，被消掉的部分在改之前占了 Prefill 的大部分；30% 说明这部分在 H200 上占比小得多。他应该能给出改前改后的分项时间，并解释 910C 上为什么占比这么高。"
    ]
  },
  {
    "id": "q4",
    "anchorId": "cx-tp-3",
    "title": "o_proj 切了反而慢 1.5 ms，分界点在哪？",
    "question": "o_proj 单层只有 117 MB，切分后 TPOT 反而变差 1.5 ms，lm_head 切分却有收益。请口头估一下：切分 o_proj，每层能省多少读权重的时间，又多付多少通信时间？权重多大时切分才划算？",
    "expected": [
      "收益一侧：decode 的小 batch 下，这些层的时间近似等于读一遍权重的时间，即权重字节数除以显存带宽。切成 TP=8 后每张卡只读 1/8，省下约 7/8 的读取时间。",
      "代价一侧：每次调用多出两次集合通信，每次都有固定的启动和同步延迟，和权重大小无关。",
      "分界点：省下的读取时间大于新增的通信延迟才划算。o_proj 每层都要付一次通信代价，单层权重又小；lm_head 每个 step 只调用一次，权重是 GB 量级。",
      "指出适用范围：batch 变大后这些层转为受算力限制，读权重不再是主要时间，时间上的收益会消失，只剩显存收益。"
    ],
    "judgement": "良好：用“字节数 ÷ 带宽”对“通信固定延迟”来算，两边都报得出数量级，并知道 batch 变大后结论会变。一般：只说“通信开销大于收益”，不会算。较差：认为切分减少了计算量。",
    "followUp": "省下的 3.9 GB 显存拿去做什么了？换成 KV cache 能多扛多少并发？",
    "interviewerHint": "优先级：必问。这题和常问题 “GEMM 与 M、N、K” 是同一件事（M 小时，时间由读权重决定），可以连着问。数量级参考（我的估算，带宽按 2 TB/s 假设，他用的芯片我不知道）：117 MB 读一遍约 0.06 ms，TP=8 每层省约 0.05 ms；lm_head 按 DeepSeek V3 的公开配置（词表约 12.9 万 × 7,168 × 2 字节）约 1.9 GB，读一遍约 1 ms。117 MB 恰好等于 7,168 × 16,384 × 1 字节，像是 DeepSeek V3/R1 的 o_proj 在 8 bit 权重下的大小（我的推断）。按 DeepSeek V3 公开配置的 61 层算，1.5 ms 相当于每层净亏约 0.025 ms（我的推算，前提是他切的是每一层的 o_proj）。简历自身的数字可以顺口核对：四个模块合计约 2 ms，去掉 o_proj 后是 3.2 ms，相差 1.2 ms，和他写的 1.5 ms 不完全一致。公开记录：Embedding PR #2616 和 Dense FFN PR #4999 由他人提交并已合并，他是 co-author。",
    "studySources": [
      {
        "title": "已学关联：B300 DeepGEMM 的分段时间模型",
        "url": "https://tomyoung903.github.io/maas_docs/b300-deepgemm-timing-model-20261029/"
      },
      {
        "title": "已学关联：H200 上的 CUDA kernel 基础",
        "url": "https://tomyoung903.github.io/maas_docs/cuda-kernel-basics-h200/"
      }
    ],
    "sources": [
      {
        "label": "Embedding PR：vllm-ascend#2616",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/2616"
      },
      {
        "label": "Dense FFN PR：vllm-ascend#4999",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/4999"
      }
    ],
    "number": 4,
    "project": 4,
    "blockIndex": 2,
    "projectLabel": "细粒度张量并行优化",
    "claim": "收益与取舍：TP=8 下四模块合计单卡节省显存 9.7 GB、TPOT 净优化约 2 ms；其中 o_proj 单层权重仅 117 MB，切分引入的通信开销反使 TPOT 劣化 1.5 ms，故 TPOT 敏感场景仅开启其余三个模块，可换取 3.9 GB 显存与 3.2 ms TPOT 收益。目前正推动该方案向 vLLM 主社区适配（RFC 撰写中）。",
    "expectedAnswer": [
      "收益一侧：decode 的小 batch 下，这些层的时间近似等于读一遍权重的时间，即权重字节数除以显存带宽。切成 TP=8 后每张卡只读 1/8，省下约 7/8 的读取时间。",
      "代价一侧：每次调用多出两次集合通信，每次都有固定的启动和同步延迟，和权重大小无关。",
      "分界点：省下的读取时间大于新增的通信延迟才划算。o_proj 每层都要付一次通信代价，单层权重又小；lm_head 每个 step 只调用一次，权重是 GB 量级。",
      "指出适用范围：batch 变大后这些层转为受算力限制，读权重不再是主要时间，时间上的收益会消失，只剩显存收益。"
    ]
  },
  {
    "id": "q5",
    "anchorId": "cx-sys-2",
    "title": "怎么判定是算子错了？",
    "question": "你写推动 CANN 修复了算子精度问题，例如 MLA 在特定输入长度下的精度错误。就拿这个例子讲：你怎么确认是算子错了，而不是正常的浮点差异？你用什么当参考答案，为什么它可信？",
    "expected": [
      "参考答案来自更高精度：同一批真实输入，用 FP32 或 FP64 在另一条实现路径上算，被怀疑的算子和它比，而不是只和另一块芯片的 BF16 结果比。",
      "区分两类差异：累加顺序不同带来的差异很小，而且没有规律；算子缺陷的差异通常大得多，并且能稳定复现。“特定输入长度”说明他应该扫过长度并找到了触发条件，例如尾部处理或对齐。",
      "定位方法：逐层 dump 张量，二分到第一个出现偏差的算子，再把输入缩到能复现的最小规模交给 CANN。",
      "说得出一共是几个问题。简历里写的是“N 个”，数字没有填。"
    ],
    "judgement": "良好：有高精度参考，有最小复现，能区分“顺序不同”和“算错了”。一般：靠和 GPU 结果对比发现问题，说不清参考为什么可信。较差：认为 CPU 或 GPU 的结果天然正确。",
    "followUp": "触发问题的输入长度是多少，偏差有多大？如果两个实现都不是逐比特一致，线上该用哪个？你看什么指标来决定？",
    "interviewerHint": "优先级：时间够再问。我们自己的做法：用 FP64 在真实输入上算参考，新旧两个 kernel 都和它比，新的误差不比旧的差才接受；有 Top-K 这类离散决策时，数决策翻转的个数。“CPU 算出来的就是对的”不成立，CPU 的结果同样取决于精度和顺序。",
    "sources": [],
    "number": 5,
    "project": 6,
    "blockIndex": 1,
    "projectLabel": "系统性能优化与方案设计",
    "claim": "性能与精度排查：通过 profiling 定位 NPU 算子缺陷，累计推动 CANN 侧修复 N 个算子精度问题（如 MLA 在特定输入长度下的精度错误），保障线上服务稳定。",
    "expectedAnswer": [
      "参考答案来自更高精度：同一批真实输入，用 FP32 或 FP64 在另一条实现路径上算，被怀疑的算子和它比，而不是只和另一块芯片的 BF16 结果比。",
      "区分两类差异：累加顺序不同带来的差异很小，而且没有规律；算子缺陷的差异通常大得多，并且能稳定复现。“特定输入长度”说明他应该扫过长度并找到了触发条件，例如尾部处理或对齐。",
      "定位方法：逐层 dump 张量，二分到第一个出现偏差的算子，再把输入缩到能复现的最小规模交给 CANN。",
      "说得出一共是几个问题。简历里写的是“N 个”，数字没有填。"
    ]
  },
  {
    "id": "q6",
    "anchorId": "cx-oss-1",
    "title": "9 个 PR 里哪些是你的 commit？",
    "question": "你写在 vLLM-Ascend 累计贡献 9 个 PR、代码修改超过 3,000 行。我在你本人账号下只查到 1 个 PR，其余挂在其他账号下。请以 PD PP（#4054）为例口头说明：你写的是哪几个模块，大约占多少个 commit；评审时社区提了什么意见，你是怎么改的？",
    "expected": [
      "解释得通署名方式：为什么由其他账号提交 PR，他自己的 commit 在哪里。公开记录支持他的说法：#4054 的 56 个 commit 中 47 个是他的，#2947 的 22 个中 14 个是他的。",
      "能复述一次具体的评审往来：谁提了什么问题，他改了哪段代码。",
      "对“深度参与”的几项说得出自己的那一块：Embedding（#2616）、Dense FFN（#4999）、NZ offload（#11945）里他是 co-author，不是主要作者。",
      "对没有合并的几项如实说明状态：DyCP 的 vLLM 主仓 PR、逆 RoPE（#12767）和 compress SP（#11733）都已关闭且未合并，简历写的是“待合入”。"
    ],
    "judgement": "良好：说法和公开记录对得上，能讲出评审细节，未合并的如实说。一般：贡献是真的，但数字有拔高，或细节讲不出来。较差：说法和记录矛盾。",
    "followUp": "vLLM 主仓的 “3 个 RFC、2 个 PR” 分别是哪几个？我在你账号下查到 1 个 RFC（#29295）和 2 个 PR（#44967、#33496），都已关闭且未合并。",
    "interviewerHint": "优先级：必问。不需要他共享屏幕或发链接；让他把 PR 编号、模块名和数量说出来，事后对照 GitHub 记录核对。按公开记录（2026-11-23 查）：他本人账号在 vllm 和 vllm-ascend 下已合并的 PR 是 0 个；有他 commit 或 co-author 署名的已合并 PR 是 5 个（#2947、#4054、#2616、#4999、#11945）；TorchTurbo 下他本人提交并合并的 PR 有 6 个，commit 数居首（6 个，第二名 5 个，仓库 2026-10-09 才建）。",
    "sources": [
      {
        "label": "PD PP：vllm-ascend#4054",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/4054"
      },
      {
        "label": "PD GQA：vllm-ascend#2947",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/2947"
      },
      {
        "label": "NZ offload：vllm-ascend#11945",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/11945"
      },
      {
        "label": "逆 RoPE：vllm-ascend#12767",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/12767"
      },
      {
        "label": "compress SP：vllm-ascend#11733",
        "url": "https://github.com/vllm-project/vllm-ascend/pull/11733"
      },
      {
        "label": "vLLM PR #33496",
        "url": "https://github.com/vllm-project/vllm/pull/33496"
      }
    ],
    "number": 6,
    "project": 9,
    "blockIndex": 0,
    "projectLabel": "开源贡献",
    "claim": "vLLM-Ascend 核心贡献者：累计贡献 9 个 PR，代码修改超 3000 行。主导开发的 PD 分离特性、PP 支持，深度参与的细粒度 TP 并行、NZ 格式 MoE 权重 offload 已合入主社区，用于昇腾生产环境；主导的动态 CP 特性已在蚂蚁内部灰度上线，显著提升框架性能与显存效率。",
    "expectedAnswer": [
      "解释得通署名方式：为什么由其他账号提交 PR，他自己的 commit 在哪里。公开记录支持他的说法：#4054 的 56 个 commit 中 47 个是他的，#2947 的 22 个中 14 个是他的。",
      "能复述一次具体的评审往来：谁提了什么问题，他改了哪段代码。",
      "对“深度参与”的几项说得出自己的那一块：Embedding（#2616）、Dense FFN（#4999）、NZ offload（#11945）里他是 co-author，不是主要作者。",
      "对没有合并的几项如实说明状态：DyCP 的 vLLM 主仓 PR、逆 RoPE（#12767）和 compress SP（#11733）都已关闭且未合并，简历写的是“待合入”。"
    ]
  },
  {
    "id": "q7",
    "anchorId": "cx-kernel-gemm-mnk",
    "title": "GEMM 与 M、N、K",
    "question": "GEMM kernel 的实现与 M、N、K 有什么关系？",
    "expected": [
      "计算量是 2MNK。时间的下界是两项里较大的一项：计算量 ÷ 算力，访存字节数 ÷ 带宽。",
      "分块后，每个块的算术强度正比于 MN/(M+N)（这里的 M、N 是块的边长），和 K 无关。K 只让工作量线性增加。",
      "M 大（prefill）时受算力限制，时间正比于 MNK。M 小（decode、小 batch）时，读权重矩阵 K×N 占主导，时间近似正比于 K·N，几乎不随 M 变。",
      "分界点 M* ≈ 算力 × 每元素字节数 ÷ (2 × 带宽)。以 B300 的 BF16 为例，按我们实测的 2,304 TFLOPS 和标称的 8 TB/s 算，M* 约 290。8 TB/s 这个数我没有核实。"
    ],
    "judgement": "良好：说出两个下界并取较大者，知道 K 不改变算术强度，知道 M 小时转为受访存限制。讲到分块、L2 复用、流水级数属于超出预期。一般：只说“正比于 MNK”，或只会套整题的 roofline。较差：不分析，转去谈利用率或 profiling。",
    "followUp": "K 变成两倍，时间怎么变？M 从 8,000 降到 8，时间怎么变？",
    "interviewerHint": "优先级：必问。可以接在第 4 题（o_proj 117 MB）后面问，那一题是这题在 M 很小时的特例。他的简历偏框架和并行，没有写过 kernel，所以重点看他会不会用“两个下界取较大”的方式想问题，而不是看术语。如果他想写公式或画图，请他直接说结论：时间由哪两项决定，M 很小时时间跟什么成正比。",
    "studySources": [
      {
        "title": "已学关联：B300 DeepGEMM 的分段时间模型",
        "url": "https://tomyoung903.github.io/maas_docs/b300-deepgemm-timing-model-20261029/"
      },
      {
        "title": "已学关联：H200 上的 CUDA kernel 基础",
        "url": "https://tomyoung903.github.io/maas_docs/cuda-kernel-basics-h200/"
      }
    ],
    "sources": [],
    "number": 7,
    "project": 10,
    "blockIndex": 0,
    "projectLabel": "常问问题",
    "claim": "GEMM kernel 的实现与 M、N、K 有什么关系？",
    "expectedAnswer": [
      "计算量是 2MNK。时间的下界是两项里较大的一项：计算量 ÷ 算力，访存字节数 ÷ 带宽。",
      "分块后，每个块的算术强度正比于 MN/(M+N)（这里的 M、N 是块的边长），和 K 无关。K 只让工作量线性增加。",
      "M 大（prefill）时受算力限制，时间正比于 MNK。M 小（decode、小 batch）时，读权重矩阵 K×N 占主导，时间近似正比于 K·N，几乎不随 M 变。",
      "分界点 M* ≈ 算力 × 每元素字节数 ÷ (2 × 带宽)。以 B300 的 BF16 为例，按我们实测的 2,304 TFLOPS 和标称的 8 TB/s 算，M* 约 290。8 TB/s 这个数我没有核实。"
    ]
  },
  {
    "id": "q8",
    "anchorId": "cx-kernel-time-estimate",
    "title": "Kernel 运行时间估算（条件追问）",
    "question": "前一题回答较好时追问：给定任意 kernel 及其输入规模，假设实现合理，你如何粗略估算它的运行时间（kernel time）？",
    "expected": [
      "方法：算两个下界，取较大的一个，再乘一个效率折扣。可以给他一组便于口算的整数：BF16，M = 8,000，K = 16,000，N = 6,000，峰值算力 2,000 TFLOPS，显存带宽 8 TB/s。请他把中间结果和结论说出来。",
      "计算量：2 × 8,000 × 16,000 × 6,000 ≈ 1.5×10¹² 次浮点运算，÷ 2,000 TFLOPS ≈ 0.77 ms。",
      "访存：三个矩阵合计约 540 MB（输入 256、权重 192、输出 96），÷ 8 TB/s ≈ 0.07 ms。所以受算力限制，下界约 0.77 ms。",
      "知道实际会更慢并说得出原因。我们在 B300 上测的是相近的真实形状（8,192×16,384 乘到 6,144 维）：按实测峰值 2,304 TFLOPS 算，下界是 0.72 ms，cuBLAS 是 0.93 ms，约为纯乘法速率的 77%；连续运行时受功耗上限降频，同一个 kernel 是 1.17 ms。"
    ],
    "judgement": "良好：两个下界都算，结论是受算力限制，给出合理的效率折扣，并能列出两个以上“实际更慢”的原因。一般：只算了一边，或算对了但说不出为什么实际更慢。较差：没有方法。",
    "followUp": "实际测出来比你估的慢 30%，你先怀疑什么？",
    "interviewerHint": "优先级：时间够再问。他简历里写“分析 DeepSeek V4 的理论性能与当前实现”，也可以让他就 V4 里自己分析过的一个算子口头估一次，看他的“理论性能”是怎么算出来的。慢 30% 的可疑项（我们的实测）：操作数从 L2 送进 SM 的速率有上限（全卡约 20 TB/s）；功耗上限导致降频；测量方式本身（冷热 L2、间歇还是连续运行）。",
    "studySources": [
      {
        "title": "已学关联：B300 DeepGEMM 的分段时间模型",
        "url": "https://tomyoung903.github.io/maas_docs/b300-deepgemm-timing-model-20261029/"
      }
    ],
    "sources": [],
    "number": 8,
    "project": 10,
    "blockIndex": 1,
    "projectLabel": "常问问题",
    "claim": "前一题回答较好时追问：给定任意 kernel 及其输入规模，假设实现合理，你如何粗略估算它的运行时间（kernel time）？",
    "expectedAnswer": [
      "方法：算两个下界，取较大的一个，再乘一个效率折扣。可以给他一组便于口算的整数：BF16，M = 8,000，K = 16,000，N = 6,000，峰值算力 2,000 TFLOPS，显存带宽 8 TB/s。请他把中间结果和结论说出来。",
      "计算量：2 × 8,000 × 16,000 × 6,000 ≈ 1.5×10¹² 次浮点运算，÷ 2,000 TFLOPS ≈ 0.77 ms。",
      "访存：三个矩阵合计约 540 MB（输入 256、权重 192、输出 96），÷ 8 TB/s ≈ 0.07 ms。所以受算力限制，下界约 0.77 ms。",
      "知道实际会更慢并说得出原因。我们在 B300 上测的是相近的真实形状（8,192×16,384 乘到 6,144 维）：按实测峰值 2,304 TFLOPS 算，下界是 0.72 ms，cuBLAS 是 0.93 ms，约为纯乘法速率的 77%；连续运行时受功耗上限降频，同一个 kernel 是 1.17 ms。"
    ]
  },
  {
    "id": "q9",
    "anchorId": "cx-ai-tooling-experience",
    "title": "AI 工具使用经验",
    "question": "请介绍一下你使用 AI 工具的经验。",
    "expected": [
      "说得出具体的工具、套餐和使用频率。",
      "说得出工作方式：是补全和问答，还是让 agent 独立完成任务；有没有用过多个 agent、skill 或自动循环。",
      "有自己的方法：怎么给指令，怎么验收。验收靠测试、基准或和参考实现对比，而不是“看着差不多”。"
    ],
    "judgement": "良好：agent 化的工作方式，加上固定的验收方法。一般：在用，但讲不出深度和频率。较差：只用来问答或补全，明显落后于现在的开发方式。",
    "followUp": "最近一次你让 AI 独立完成、而你没有逐行看代码的任务是什么？你怎么确认结果是对的？",
    "interviewerHint": "优先级：必问。简历自述：熟练使用 Claude Code、Codex，日常大量使用 AI。他在 TorchTurbo 的特性 PR 很密集（2026-11-03 到 11-17 之间 4 个），可以问这些 PR 里 AI 写了多少、他是怎么验的。",
    "sources": [],
    "number": 9,
    "project": 10,
    "blockIndex": 2,
    "projectLabel": "常问问题",
    "claim": "请介绍一下你使用 AI 工具的经验。",
    "expectedAnswer": [
      "说得出具体的工具、套餐和使用频率。",
      "说得出工作方式：是补全和问答，还是让 agent 独立完成任务；有没有用过多个 agent、skill 或自动循环。",
      "有自己的方法：怎么给指令，怎么验收。验收靠测试、基准或和参考实现对比，而不是“看着差不多”。"
    ]
  },
  {
    "id": "q10",
    "anchorId": "cx-ai-tooling-best-experience",
    "title": "最好的 AI 工具使用经历",
    "question": "请描述一次你使用 AI 工具时最好的经历。",
    "expected": [
      "讲一个具体任务：目标是什么，给 AI 的指令是什么，AI 做了什么，最后的结果是什么。",
      "说得出这件事不用 AI 大约要多久。",
      "说得出 AI 在哪一步出过错，他是靠哪一项检查发现的。"
    ],
    "judgement": "良好：具体、可核对，包含一次发现 AI 出错的经过。一般：只有泛泛的“提效很多”。较差：讲不出例子。",
    "interviewerHint": "优先级：时间够再问。之前有录音的四场面试里，这题一次都没有问到，实际问的都是用什么工具和套餐。",
    "sources": [],
    "number": 10,
    "project": 10,
    "blockIndex": 3,
    "projectLabel": "常问问题",
    "claim": "请描述一次你使用 AI 工具时最好的经历。",
    "expectedAnswer": [
      "讲一个具体任务：目标是什么，给 AI 的指令是什么，AI 做了什么，最后的结果是什么。",
      "说得出这件事不用 AI 大约要多久。",
      "说得出 AI 在哪一步出过错，他是靠哪一项检查发现的。"
    ]
  }
];
