# Liu Guangli interview page

Sources: the one-page PDF `【推理优化工程师（框架 _ GPU Kernel）_北京】刘光立 27年应届生.pdf` (in the interviewer's Downloads folder since 20 November 2026) and the GitHub public record checked on 25 November 2026. Interview: 25 November 2026, 17:00 Singapore time, 大模型推理优化工程师技术一面.

The page includes the two internships (MachinePulse, 哈啰出行), the 开源贡献 section, the FlagOS competition entry and the vLLM MoE kernel project, in résumé order. Original wording, technical terms and figures are retained. Only line wrapping is normalized; the watermark, contact details, education, skills list and awards are omitted. All experience and performance figures remain candidate claims.

`公开核验` lines under a paragraph come from `content.json` (`evidence`). They state who filed each linked PR, whether it merged, its size, and what the candidate's public repository `xuhuan51/vllm-moe-kernels` records. They do not verify performance figures measured outside that repository.

Ten preset questions (`questions.json`), numbered by list position, which is the suggested asking order and follows the page from top to bottom: six are anchored to résumé paragraphs (double TP4 versus TP8, prefix hit rate versus task throughput, the merged vLLM PR and the overall PR record, the FlagOS speed-up split, the 64+32 reduction and what the 1.4× consists of, local 1.4× versus end-to-end 9.7%) and four are the standard questions with their usual wording (GEMM M/N/K, conditional kernel-time estimate, AI-tool experience, best AI-tool experience). The kernel questions are kept because this candidate has kernel work. Every question carries review checkpoints, a rating guide and an interviewer hint with a priority. All questions are written for spoken answers (no drawing, written formulas or screen sharing), because answers are later checked against the audio transcript. Browser-local keys use `liu-guangli-interview`; annotations use `/liu-guangli-interview/`.

Build from the repository root:

```bash
python3 tools/liu_guangli_interview/build.py
```

Output is limited to `docs/liu-guangli-interview/`.
