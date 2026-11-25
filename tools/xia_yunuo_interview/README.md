# Xia Yunuo interview page

Source: the one-page PDF `【推理优化工程师（框架 _ GPU Kernel）_北京】夏雨诺Xsiri 27年应届生.pdf` (in Tom's Downloads since 20 November 2026). Interview: 25 November 2026, 16:00 Singapore time, 大模型推理优化工程师技术一面.

The page includes both internships (得物: Ascend 910C vLLM-Ascend optimization; 腾讯: two-batch overlap on 2×L20) and the KubeAI agent project. Original wording, technical terms, figures and order are retained; only line wrapping is normalized. Watermark strings, contact details and education are omitted, and the "项目亮点" label lines are dropped. All figures are candidate claims. The résumé has no public links, so the page carries no `公开核验` lines.

Ten preset questions (`questions.json`), numbered by list position, which is the suggested asking order and follows the page from top to bottom: eight are anchored to résumé paragraphs (TPOT chain, MTP acceptance, MoE overlap, static kernel, AllReduce size, TBO upper bound, throughput versus latency, agent verification) and two are the standard AI-tool questions. The candidate has no kernel work, so the two standard kernel questions are not included. All questions are written for spoken answers (no drawing, written formulas or screen sharing); prompts ask for numbers and conclusions aloud. Browser-local keys use `xia-yunuo-interview`; annotations use `/xia-yunuo-interview/`.

Build from the repository root:

```bash
python3 tools/xia_yunuo_interview/build.py
```

Output is limited to `docs/xia-yunuo-interview/`.
