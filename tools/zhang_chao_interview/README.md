# Zhang Chao interview page

Source for the five marked resume excerpts and six interview questions.

Run from the repository root:

```bash
python3 tools/zhang_chao_interview/build.py
```

The builder writes only `docs/zhang-chao-interview/`. Questions include review checkpoints, official references and links to existing MaaS study notes. Browser-created questions are saved only in that browser. The shared annotation script is loaded from `docs/assets/maas-annotator.js`.

The page supports selecting a phrase within one excerpt and adding a question for that exact text. Saved questions retain the quote and UTF-16 offsets, with persisted highlights; the top-level Add Question button still creates whole-paragraph questions. Each question also has separate blank fields for the candidate's answer, the gap from expectations, and the interviewer's evaluation. Changes autosave after 400 ms and on navigation/close; the summary displays and copies only human-entered records.

Storage is isolated to this candidate:

- Questions: `zhang-chao-interview:custom-questions:v1` (payload version 2).
- Interview records: `zhang-chao-interview:evaluations:v1` (payload version 1).
- Shared annotations retain page key `/zhang-chao-interview/`.

The old question payload (version 1) used section/paragraph positions. It is migrated to version 2 by resolving those unchanged positions to the existing excerpt IDs. Question IDs, numbers and reference answers are retained; migration write failure leaves the recovered questions available in memory. New questions use stable excerpt IDs and optional text offsets, and the six preset questions remain unchanged.
