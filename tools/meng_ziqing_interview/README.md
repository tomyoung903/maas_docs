# Meng Ziqing interview page

Interview: 2026-11-02 at 17:00. Source: the two-page PDF `【资深 AI 大模型推理工程师】孟子清 2年.pdf`, extracted with `pdftotext -layout` and checked in full. Resume claims and metrics are self-reported, not verified accomplishments. Only watermark artifacts and extraction-induced line breaks/spacing were removed; content wording, numbers and source order are retained.

The source contains 18 resume bullets: 12 current-job bullets across all four WeRide project groups (4 + 3 + 3 + 2) and six personal-project bullets (CUDA GEMM 3 + accounting Agent 3). Contact details, personal demographics, education, honors, internships, personal summary and the separate skills section are not included. The bottom 常问问题 section copies exactly four reusable prompts from `tools/sun_shiniu_interview/content.json`: two AI-tooling prompts, GEMM M/N/K, and a conditional kernel-time-estimation follow-up. These four are the only preset questions, all without reference answers.

Run from the repository root:

```bash
python3 tools/meng_ziqing_interview/build.py
```

The builder writes only `docs/meng-ziqing-interview/` (HTML, data and two local assets). The UI follows the latest Zhang Chao page: phrase selection with quote/UTF-16 anchors, whole-paragraph questions, per-question notes that autosave after 400 ms and on navigation/close, summary/copy, and delete/restore without discarding notes. The shared annotation script is `docs/assets/maas-annotator.js`.

Candidate storage is isolated:

- Questions: `meng-ziqing-interview:custom-questions:v1` (payload version 2).
- Deleted questions: `meng-ziqing-interview:deleted-question:v1:<question-id>`.
- Interview records: `meng-ziqing-interview:evaluations:v1` (payload version 1).
- Shared annotations: `/meng-ziqing-interview/`.
- CSS text highlights: `meng-question-saved` and `meng-question-active`.

No catalog, landing-page or other candidate files are changed by this pack.
