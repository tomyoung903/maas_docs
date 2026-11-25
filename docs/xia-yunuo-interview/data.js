window.INTERVIEW_QUESTIONS = [
  {
    "id": "q1",
    "anchorId": "xy-dewu-overview",
    "title": "14.22 ms 到 5.0 ms：每一步各省了多少？",
    "question": "c=1 时 TPOT 从 14.22 ms 降到 5.0 ms。请按先后顺序口头讲一遍：每一步做了什么，各省了多少毫秒？哪几步是你本人做的？",
    "expected": [
      "报得出完整的链条。简历里能对上的中间值是：14.22 → 11.2 → 9.1（Static Kernel，省 2.1 ms）→ 7.8 → 5.0（MTP 及相关优化，省 2.8 ms），合计 9.22 ms。",
      "说得出简历没有写的两步：14.22 → 11.2（3.0 ms）和 9.1 → 7.8（1.3 ms）分别是什么。",
      "解释为什么并发越高降幅越小（64.8%、49.9%、43.8%）：host 侧和算子启动的开销每步是固定的，并发高时被更多 token 分摊，计算本身的占比上升。",
      "说清“达到 H20 性能的 85%”比的是哪个指标、哪个并发，是否同一个模型和同样的精度。"
    ],
    "judgement": "良好：链条每一步有数字、能对上总数，分得清自己做的和别人做的。一般：只能复述首尾两个数，或中间值对不上。较差：说不清各项优化的先后和归属。",
    "followUp": "30 多轮单变量实验里，哪一项试了没有收益？为什么？",
    "interviewerHint": "优先级：必问。简历给了四个中间值，可以当场核对：14.22 − 11.2 = 3.0，11.2 − 9.1 = 2.1，9.1 − 7.8 = 1.3，7.8 − 5.0 = 2.8，加起来 9.22，等于 14.22 − 5.0。这条链的先后顺序是我按数值大小推的，他实际的顺序可能不同。三个月的实习把 TPOT 降了 65%，要问清哪些是他本人做的，哪些是团队或厂商做的。并发升高降幅变小的解释是我的推理。",
    "sources": [],
    "studySources": null,
    "number": 1,
    "project": 1,
    "blockIndex": 1,
    "projectLabel": "昇腾 910C 大模型推理引擎性能优化｜vLLM-Ascend",
    "claim": "项目概述：负责 Ascend 910C 上 vLLM-Ascend 推理引擎性能优化，面向客服、风控及模型网关等在线推理业务，达到 NVIDIA H20 性能的 85%；Qwen3.5-35B-A3B 在 c=1/4/8 下 TPOT 分别由 14.22/17.55/21.17ms → 5.0/8.8/11.9ms，降幅 ↓ 64.8%/49.9%/43.8%。",
    "expectedAnswer": [
      "报得出完整的链条。简历里能对上的中间值是：14.22 → 11.2 → 9.1（Static Kernel，省 2.1 ms）→ 7.8 → 5.0（MTP 及相关优化，省 2.8 ms），合计 9.22 ms。",
      "说得出简历没有写的两步：14.22 → 11.2（3.0 ms）和 9.1 → 7.8（1.3 ms）分别是什么。",
      "解释为什么并发越高降幅越小（64.8%、49.9%、43.8%）：host 侧和算子启动的开销每步是固定的，并发高时被更多 token 分摊，计算本身的占比上升。",
      "说清“达到 H20 性能的 85%”比的是哪个指标、哪个并发，是否同一个模型和同样的精度。"
    ]
  },
  {
    "id": "q2",
    "anchorId": "xy-dewu-mtp",
    "title": "MTP：7.8 ms 到 5.0 ms，平均每步接受几个 token？",
    "question": "叠加 MTP 后 c=1 的 TPOT 从 7.8 ms 降到 5.0 ms。请口头估一下：平均每一步产出几个 token？开 MTP 之后，每一步本身多花了多少时间？",
    "expected": [
      "知道关系式：TPOT = 每步时间 ÷ 每步产出的 token 数。",
      "如果每步时间不变，7.8 ÷ 5.0 = 1.56，即平均每步产出约 1.56 个 token。MTP 头和验证本身要花时间，所以实际的接受数比 1.56 更高。他应该报出草稿长度、接受率和开 MTP 后的每步时间。",
      "讲清验证阶段的同步热点：rejection sampling 要比较概率和随机数才能决定接受几个，结果每步都要在 host 和设备之间同步一次；“全词表通信”指把整个词表的 logits 或概率传出去。",
      "讲清怎么减少：greedy 验证只需要比较 argmax，不需要全词表概率；把判断留在设备上，只把接受的 token 数和 id 拿回来。"
    ],
    "judgement": "良好：用“每步时间 ÷ 每步 token 数”算出接受数，并说清同步发生在哪一步。一般：知道 MTP 能一步出多个 token，但数字对不上。较差：说不清验证在做什么。",
    "followUp": "c=8 时整体降幅比 c=1 小。MTP 的收益和并发有关吗？为什么？",
    "interviewerHint": "优先级：必问。7.8 ÷ 5.0 = 1.56 是算术；“实际接受数更高”和同步热点的描述是我的推理，没有对照 vLLM-Ascend 的代码。简历在这一条里同时写了 Graph Capture，可以问草稿长度不同时是否要分别抓图。",
    "sources": [],
    "studySources": null,
    "number": 2,
    "project": 1,
    "blockIndex": 2,
    "projectLabel": "昇腾 910C 大模型推理引擎性能优化｜vLLM-Ascend",
    "claim": "MTP 验证与采样链路优化：针对 speculative decoding 验证阶段的 Host-NPU 同步与通信热点，优化 rejection sampler、greedy verify、Graph Capture 等关键路径，减少冗余 H2D 同步与全词表通信；叠加 MTP 及相关优化后，c=1 TPOT 7.8ms → 5.0ms（-35.9%）。",
    "expectedAnswer": [
      "知道关系式：TPOT = 每步时间 ÷ 每步产出的 token 数。",
      "如果每步时间不变，7.8 ÷ 5.0 = 1.56，即平均每步产出约 1.56 个 token。MTP 头和验证本身要花时间，所以实际的接受数比 1.56 更高。他应该报出草稿长度、接受率和开 MTP 后的每步时间。",
      "讲清验证阶段的同步热点：rejection sampling 要比较概率和随机数才能决定接受几个，结果每步都要在 host 和设备之间同步一次；“全词表通信”指把整个词表的 logits 或概率传出去。",
      "讲清怎么减少：greedy 验证只需要比较 argmax，不需要全词表概率；把判断留在设备上，只把接受的 token 数和 id 拿回来。"
    ]
  },
  {
    "id": "q3",
    "anchorId": "xy-dewu-moe",
    "title": "MoE：shared expert 和 routed expert 怎么重叠？",
    "question": "你写实现了 shared expert 计算、通信与 routed expert 计算的重叠。请按先后顺序口头讲一遍：原来是怎么串行的，现在哪两件事同时在做？省了多少毫秒？",
    "expected": [
      "讲清原来的顺序：路由 → 把 token 发到专家所在的卡（集合通信）→ routed expert 计算 → 发回 → shared expert 计算，各步串行。",
      "讲清为什么可以重叠：shared expert 每个 token 都要过，权重本卡就有，不依赖路由结果和通信，所以可以在通信进行的同时用另一个 stream 计算。",
      "说清部署方式：专家是否跨卡分布（EP），用的是哪种集合通信。如果专家都在本卡，就没有通信可以重叠。",
      "报出收益的数字，以及“权重预取”具体预取什么、放到哪里。"
    ],
    "judgement": "良好：说清依赖关系（shared expert 不依赖通信）和部署方式，有数字。一般：只说“多 stream 并行”，讲不出哪两件事重叠。较差：说不清 routed 和 shared expert 的区别。",
    "followUp": "两个 stream 同时跑，会不会互相抢算力或带宽？你怎么确认重叠真的发生了？",
    "interviewerHint": "优先级：时间够再问。参考答案里的串行顺序和可重叠的理由是我按 MoE 的一般结构推的，没有对照 vLLM-Ascend 的代码。要问清专家权重在各卡上怎么分布，因为有没有通信可重叠取决于它。第 1 题里 9.1 → 7.8 的 1.3 ms 可能就是这一项，可以让他确认。",
    "sources": [],
    "studySources": null,
    "number": 3,
    "project": 1,
    "blockIndex": 3,
    "projectLabel": "昇腾 910C 大模型推理引擎性能优化｜vLLM-Ascend",
    "claim": "MoE 计算通信优化：针对 routed / shared expert 串行执行及集合通信开销，优化多 Stream 并行与权重预取策略，实现 shared expert 计算、通信与 routed expert 计算重叠，缩短 Decode 关键路径。",
    "expectedAnswer": [
      "讲清原来的顺序：路由 → 把 token 发到专家所在的卡（集合通信）→ routed expert 计算 → 发回 → shared expert 计算，各步串行。",
      "讲清为什么可以重叠：shared expert 每个 token 都要过，权重本卡就有，不依赖路由结果和通信，所以可以在通信进行的同时用另一个 stream 计算。",
      "说清部署方式：专家是否跨卡分布（EP），用的是哪种集合通信。如果专家都在本卡，就没有通信可以重叠。",
      "报出收益的数字，以及“权重预取”具体预取什么、放到哪里。"
    ]
  },
  {
    "id": "q4",
    "anchorId": "xy-dewu-static",
    "title": "Static Kernel：省下的 2.1 ms 原来花在哪？",
    "question": "Static Kernel 让 c=1 的 TPOT 从 11.2 ms 降到 9.1 ms。请口头说：一个 decode step 大约执行多少个算子？省下的 2.1 ms 原来花在哪几件事上？",
    "expected": [
      "讲清动态和静态的区别：动态 shape 下，每个算子每次执行前都要在 host 上做 shape 推导和 kernel 选择；静态 kernel 按固定 shape 提前准备好，运行时跳过这些。",
      "讲清为什么 decode 适合：decode 每步每条请求只进 1 个 token，batch 固定时各算子的 shape 固定。代价是每种 batch 大小要各准备一份。",
      "给出量级：2.1 ms ÷ 每步的算子数 = 每个算子省下的 host 时间。例如每步 2,000 个算子，就是每个约 1 微秒。他应该报出自己的算子数和 msprof 里看到的 host 占比。",
      "知道这部分是固定开销：并发升高时它不变，所以占比下降。"
    ],
    "judgement": "良好：说清省的是 host 侧的固定开销，并能给出算子数和每个算子的量级。一般：只说“减少了动态 shape 推导”，没有数字。较差：把它说成 kernel 本身算得更快。",
    "followUp": "Graph Capture 和 Static Kernel 是什么关系？batch 大小变了要重新抓图吗？",
    "interviewerHint": "优先级：时间够再问。参考答案是我按动态 shape 执行的一般机制推的，CANN 的具体实现我没有核对；“2,000 个算子”只是举例。可以对照 GPU 上的 CUDA graph：同样按 batch 大小提前抓好，省掉每步的启动开销。",
    "sources": [],
    "studySources": null,
    "number": 4,
    "project": 1,
    "blockIndex": 4,
    "projectLabel": "昇腾 910C 大模型推理引擎性能优化｜vLLM-Ascend",
    "claim": "Graph / Kernel / Runtime 优化：围绕 Decode 路径优化 Static Kernel、Graph Capture 与算子执行链路，降低动态 Shape 推导、Kernel Launch 与 Host Runtime 开销；Static Kernel 将 c=1 TPOT 11.2ms → 9.1ms（-18.7%）。",
    "expectedAnswer": [
      "讲清动态和静态的区别：动态 shape 下，每个算子每次执行前都要在 host 上做 shape 推导和 kernel 选择；静态 kernel 按固定 shape 提前准备好，运行时跳过这些。",
      "讲清为什么 decode 适合：decode 每步每条请求只进 1 个 token，batch 固定时各算子的 shape 固定。代价是每种 batch 大小要各准备一份。",
      "给出量级：2.1 ms ÷ 每步的算子数 = 每个算子省下的 host 时间。例如每步 2,000 个算子，就是每个约 1 微秒。他应该报出自己的算子数和 msprof 里看到的 host 占比。",
      "知道这部分是固定开销：并发升高时它不变，所以占比下降。"
    ]
  },
  {
    "id": "q5",
    "anchorId": "xy-tbo-profile",
    "title": "单次 AllReduce 2–4 ms：传的张量有多大？",
    "question": "你定位到单次 AllReduce 要 2 到 4 ms。请口头估一下：一次 AllReduce 传的张量有多大？按 PCIe 的带宽算，2 到 4 ms 合理吗？",
    "expected": [
      "张量大小 = token 数 × hidden 维度 × 每元素字节数。举例：8K token、hidden 4,096、BF16，约 67 MB。",
      "时间 ≈ 字节数 ÷ 链路带宽，再加固定延迟。PCIe 4.0 x16 标称约 31.5 GB/s，67 MB 约 2.1 ms；实际带宽更低，所以 2 到 4 ms 说得通。",
      "结论：这里是带宽受限，不是固定延迟受限。所以 context 越长、batch 越大，通信越慢；换成 NVLink 会快很多，重叠的收益也会变小。",
      "说得出每层有几次 AllReduce（attention 输出后一次，MLP 输出后一次）和模型的层数，由此解释 NCCL 为什么占到 50% 到 55%。"
    ],
    "judgement": "良好：用“字节数 ÷ 带宽”估出毫秒量级，并知道这是带宽受限。一般：知道 PCIe 慢，但算不出张量大小。较差：说不清 TP 下为什么要 AllReduce。",
    "followUp": "decode 时每步只有几个 token，AllReduce 还要 2 到 4 ms 吗？那时的瓶颈是什么？",
    "interviewerHint": "优先级：时间够再问。数字是我的估算：8,192 × 4,096 × 2 字节 = 67.1 MB；PCIe 4.0 x16 标称 31.5 GB/s，L20 的接口规格我没有核实。他用的模型和 hidden 维度简历没有写，要他自己报。0.22 QPS、8K context 看起来是 prefill 为主的负载，这是我的推断。",
    "sources": [],
    "studySources": null,
    "number": 5,
    "project": 2,
    "blockIndex": 2,
    "projectLabel": "NVIDIA L20 大模型推理引擎通信优化｜Two-Batch Overlap（TBO）",
    "claim": "性能瓶颈定位：基于 PyTorch Profiler 对 Transformer Forward Timeline 进行算子级分析，定位单次 AllReduce 延迟 2–4ms、NCCL 占比 50%–55% 的核心通信瓶颈，确定 Compute-Communication Overlap 优化方向。",
    "expectedAnswer": [
      "张量大小 = token 数 × hidden 维度 × 每元素字节数。举例：8K token、hidden 4,096、BF16，约 67 MB。",
      "时间 ≈ 字节数 ÷ 链路带宽，再加固定延迟。PCIe 4.0 x16 标称约 31.5 GB/s，67 MB 约 2.1 ms；实际带宽更低，所以 2 到 4 ms 说得通。",
      "结论：这里是带宽受限，不是固定延迟受限。所以 context 越长、batch 越大，通信越慢；换成 NVLink 会快很多，重叠的收益也会变小。",
      "说得出每层有几次 AllReduce（attention 输出后一次，MLP 输出后一次）和模型的层数，由此解释 NCCL 为什么占到 50% 到 55%。"
    ]
  },
  {
    "id": "q6",
    "anchorId": "xy-tbo-design",
    "title": "NCCL 占 50%–55%，理想重叠后的吞吐上限是多少？",
    "question": "NCCL 占 50% 到 55%。把一个 batch 拆成两个 micro-batch 做重叠后，理想情况下吞吐最多能提升多少？你实际拿到 31%，差在哪里？",
    "expected": [
      "讲清机制：A 的 AllReduce 在传的时候，B 在算下一段 attention 或 MLP；通信和计算各用一个 CUDA stream，两个 micro-batch 交替。",
      "给出上限：重叠后每层的周期由计算和通信里较长的一个决定，而不是两者相加。通信占 55% 时，上限约 1.8 倍；占 50% 时是 2 倍。",
      "解释差距：拆成两半后每半的计算效率下降；AllReduce 的固定延迟不会减半；通信也要占用显存带宽和 host 拷贝，和计算不是完全独立；首尾和同步点不能重叠。",
      "说清为什么小 batch 反而变慢，以及切换 TBO 和原生路径的 batch 阈值是多少。"
    ],
    "judgement": "良好：能给出“较长者决定周期”的上限，并列出两个以上的差距来源。一般：机制讲得清，但给不出上限。较差：说不清两个 micro-batch 怎么交替。",
    "followUp": "你怎么确认通信和计算真的同时在跑，而不是在 GPU 上分时？",
    "interviewerHint": "优先级：必问。上限是我的推算：原来每层耗时是计算加通信（记为 1），理想重叠后是两者中较长的一个，所以提升倍数是 1 ÷ max(计算占比, 通信占比)，即 1 ÷ 0.55 ≈ 1.8 或 1 ÷ 0.5 = 2。差距的几条原因也是我的推理。SGLang 里有同名的 two-batch overlap（`--enable-two-batch-overlap`，文档写最多 2 倍吞吐），用在 EP 的通信上；可以问他是否参考过，他的版本用在 TP 的 AllReduce 上有什么不同。",
    "sources": [
      {
        "label": "SGLang 文档：Expert Parallelism 与 two-batch overlap",
        "url": "https://docs.sglang.io/docs/advanced_features/expert_parallelism"
      }
    ],
    "studySources": null,
    "number": 6,
    "project": 2,
    "blockIndex": 3,
    "projectLabel": "NVIDIA L20 大模型推理引擎通信优化｜Two-Batch Overlap（TBO）",
    "claim": "TBO Pipeline 设计：将原始 Batch 按 Request 维度拆分为两个 Micro-Batch，设计基于 Token 数量的动态负载均衡策略，并通过 Compute / Comm 双 CUDA Stream 实现 Attention / MLP 与 NCCL AllReduce 跨 Layer 流水重叠。",
    "expectedAnswer": [
      "讲清机制：A 的 AllReduce 在传的时候，B 在算下一段 attention 或 MLP；通信和计算各用一个 CUDA stream，两个 micro-batch 交替。",
      "给出上限：重叠后每层的周期由计算和通信里较长的一个决定，而不是两者相加。通信占 55% 时，上限约 1.8 倍；占 50% 时是 2 倍。",
      "解释差距：拆成两半后每半的计算效率下降；AllReduce 的固定延迟不会减半；通信也要占用显存带宽和 host 拷贝，和计算不是完全独立；首尾和同步点不能重叠。",
      "说清为什么小 batch 反而变慢，以及切换 TBO 和原生路径的 batch 阈值是多少。"
    ]
  },
  {
    "id": "q7",
    "anchorId": "xy-tbo-result",
    "title": "吞吐 +31.1%，平均延迟只降 5.4%：怎么同时成立？",
    "question": "在 2×L20、8K context 下，吞吐从 0.22 QPS 提升到 0.29 QPS，平均延迟只降了 5.4%。请口头说明压测方式：并发是多少，延迟量的是哪一段？这两个数为什么能同时成立？",
    "expected": [
      "知道闭环压测的关系：吞吐 = 并发 ÷ 平均延迟。并发不变时，吞吐提升 31.1% 对应延迟降到原来的 76%，也就是降约 24%。",
      "所以延迟只降 5.4% 时，两次测试的并发或负载一定不同：按这两个数推，TBO 那次的并发约是原来的 1.24 倍。或者吞吐和延迟不是在同一组实验里量的。",
      "说清延迟的定义：端到端、TTFT 还是 TPOT；P99 只降 2.9% 说明尾部基本没有改善，原因是什么。",
      "说清对照是否公平：同一批请求、同样的输入输出长度、同样的并发，跑了几轮。"
    ],
    "judgement": "良好：主动说明两个数的口径，能用“吞吐 = 并发 ÷ 延迟”自己对上。一般：承认口径不同，但说不清各自是怎么量的。较差：坚持两个数来自同一组实验，又解释不了。",
    "followUp": "0.22 和 0.29 直接算是 +31.8%，简历写 +31.1%。原始数字是多少？",
    "interviewerHint": "优先级：必问。算术：1 ÷ 1.311 = 0.763，即延迟应降 23.7%；1.311 × 0.946 = 1.24。这是固定并发、闭环压测下的关系。如果他用的是固定到达率的开环压测，吞吐就等于到达率，那 31.1% 指的应该是能撑住的最大到达率，要他说明。这题看的是他对自己数字的口径是否清楚。",
    "sources": [],
    "studySources": null,
    "number": 7,
    "project": 2,
    "blockIndex": 5,
    "projectLabel": "NVIDIA L20 大模型推理引擎通信优化｜Two-Batch Overlap（TBO）",
    "claim": "性能收益：在 2×L20、8K Context 场景下，吞吐由 0.22 QPS 提升至 0.29 QPS（+31.1%），平均延迟降低 5.4%，P99 延迟降低 2.9%；实验验证 TBO 在长 Context、大 Batch 场景收益更显著。",
    "expectedAnswer": [
      "知道闭环压测的关系：吞吐 = 并发 ÷ 平均延迟。并发不变时，吞吐提升 31.1% 对应延迟降到原来的 76%，也就是降约 24%。",
      "所以延迟只降 5.4% 时，两次测试的并发或负载一定不同：按这两个数推，TBO 那次的并发约是原来的 1.24 倍。或者吞吐和延迟不是在同一组实验里量的。",
      "说清延迟的定义：端到端、TTFT 还是 TPOT；P99 只降 2.9% 说明尾部基本没有改善，原因是什么。",
      "说清对照是否公平：同一批请求、同样的输入输出长度、同样的并发，跑了几轮。"
    ]
  },
  {
    "id": "q8",
    "anchorId": "xy-agent-diagnose",
    "title": "Agent 给出的根因，怎么知道是对的？",
    "question": "你的 Agent 覆盖 1,269 张 GPU，自动识别零利用率、僵尸任务和假占用。请口头说：它的结论怎么验证？准确率是多少，误报怎么处理？",
    "expected": [
      "有评测集：一批人工标注过根因的历史故障或资源问题，Agent 的结论和标注对比，报得出准确率或召回率。",
      "说清“假占用”的判定标准：例如显存被占但利用率长期为零，持续多久才算，怎么排除正在加载或排队的任务。",
      "说清动作的边界：Agent 只给治理建议，还是会自动释放资源；自动动作之前有没有人工确认。",
      "Context Token 降约 50% 之后，工具调用遗漏有没有变少，用什么数字衡量。"
    ],
    "judgement": "良好：有评测集和数字，知道误报的代价并有人工确认环节。一般：只有“上线后反馈不错”一类的说法。较差：没有验证方法。",
    "followUp": "980 行的 Skill 拆成分层按需加载之后，Agent 怎么决定加载哪一层？加载错了会怎样？",
    "interviewerHint": "优先级：时间够再问。这个项目和推理优化关系不大，但能看出他怎么用 Agent 做事，可以和后面两道 AI 工具题连着问。时间上它和得物的实习重叠（2026.05 到 2026.07），可以顺口确认是不是同一段实习里的工作。",
    "sources": [],
    "studySources": null,
    "number": 8,
    "project": 3,
    "blockIndex": 5,
    "projectLabel": "KubeAI 智能运维与 GPU 资源治理 Agent 平台",
    "claim": "智能诊断与资源治理：融合离线数仓、APM 实时指标及 Kubernetes 多源信息进行根因分析，覆盖 1269 张 GPU，自动识别零 / 低利用率、僵尸任务、Holder 假占用等问题。",
    "expectedAnswer": [
      "有评测集：一批人工标注过根因的历史故障或资源问题，Agent 的结论和标注对比，报得出准确率或召回率。",
      "说清“假占用”的判定标准：例如显存被占但利用率长期为零，持续多久才算，怎么排除正在加载或排队的任务。",
      "说清动作的边界：Agent 只给治理建议，还是会自动释放资源；自动动作之前有没有人工确认。",
      "Context Token 降约 50% 之后，工具调用遗漏有没有变少，用什么数字衡量。"
    ]
  },
  {
    "id": "q9",
    "anchorId": "xy-ai-tooling-experience",
    "title": "AI 工具使用经验",
    "question": "请介绍一下你使用 AI 工具的经验。",
    "expected": [
      "说得出具体的工具、套餐和使用频率。",
      "说得出工作方式：是补全和问答，还是让 agent 独立完成任务；有没有用过多个 agent、skill 或自动循环。",
      "有自己的方法：怎么给指令，怎么验收。验收靠测试、基准或和参考实现对比，而不是“看着差不多”。"
    ],
    "judgement": "良好：agent 化的工作方式，加上固定的验收方法。一般：在用，但讲不出深度和频率。较差：只用来问答或补全，明显落后于现在的开发方式。",
    "followUp": "最近一次你让 AI 独立完成、而你没有逐行看代码的任务是什么？你怎么确认结果是对的？",
    "interviewerHint": "优先级：必问。他做过 Agent 平台（MCP 工具、Skill、多 Agent），这题重点听他自己写推理优化代码时怎么用 AI，而不是他给别人做的平台。可以问 TBO 和昇腾优化的代码里 AI 写了多少、他是怎么验的。",
    "sources": [],
    "studySources": null,
    "number": 9,
    "project": 4,
    "blockIndex": 0,
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
    "anchorId": "xy-ai-tooling-best-experience",
    "title": "最好的 AI 工具使用经历",
    "question": "请描述一次你使用 AI 工具时最好的经历。",
    "expected": [
      "讲一个具体任务：目标是什么，给 AI 的指令是什么，AI 做了什么，最后的结果是什么。",
      "说得出这件事不用 AI 大约要多久。",
      "说得出 AI 在哪一步出过错，他是靠哪一项检查发现的。"
    ],
    "judgement": "良好：具体、可核对，包含一次发现 AI 出错的经过。一般：只有泛泛的“提效很多”。较差：讲不出例子。",
    "followUp": null,
    "interviewerHint": "优先级：时间够再问。",
    "sources": [],
    "studySources": null,
    "number": 10,
    "project": 4,
    "blockIndex": 1,
    "projectLabel": "常问问题",
    "claim": "请描述一次你使用 AI 工具时最好的经历。",
    "expectedAnswer": [
      "讲一个具体任务：目标是什么，给 AI 的指令是什么，AI 做了什么，最后的结果是什么。",
      "说得出这件事不用 AI 大约要多久。",
      "说得出 AI 在哪一步出过错，他是靠哪一项检查发现的。"
    ]
  }
];
