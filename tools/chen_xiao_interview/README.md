# Chen Xiao interview page

Sources: the three-page PDF `大模型推理优化工程师-陈潇 27年应届生.pdf` (sent by the recruiter on 23 November 2026) and the GitHub public record checked on the same day. Interview: 24 November 2026, 15:00 Singapore time, 大模型推理优化工程师技术一面.

The page includes all internship, project and open-source paragraphs: 蚂蚁集团 inference acceleration (six projects), 蚂蚁集团 post-training (TorchTurbo), 北京开源芯片研究院, and the résumé's 开源贡献 section. Original wording, technical terms, figures, project order and link labels are retained. Only line wrapping and extraction spacing are normalized; watermarks, contact details, education, awards and the skills list are omitted. All experience and performance figures remain candidate claims.

`公开核验` lines under a paragraph come from `content.json` (`evidence`). They state who filed each linked RFC or PR, whose commits or co-author lines it contains, and whether it merged. They do not verify performance figures.

Ten preset questions (`questions.json`), numbered in the suggested asking order: q1 to q6 are anchored to résumé paragraphs (DyCP, PD PP, DSA sharded CP, fine-grained TP, precision debugging, open-source authorship); q7 to q10 are the four standard questions (GEMM M/N/K, conditional kernel-time estimate, AI-tool experience, best AI-tool experience) with their usual wording. Every question carries review checkpoints, a rating guide and an interviewer hint with a priority. Browser-local keys use `chen-xiao-interview`; annotations use `/chen-xiao-interview/`.

Build from the repository root:

```bash
python3 tools/chen_xiao_interview/build.py
```

Output is limited to `docs/chen-xiao-interview/`.
