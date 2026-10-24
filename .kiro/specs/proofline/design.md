# Design: Proofline

BUILD_PLAN.md is authoritative for files, data, and decisions. This document summarizes the architecture.

## Architecture
React (Vite) SPA → FastAPI (/api) → document pipeline + ledger + reporting. In production FastAPI also serves the built SPA and /samples, so the app is one URL. The API contract is the Pydantic models in backend/app/schemas, exported to shared/openapi.json; the frontend generates TypeScript types from it.

```
Upload → ingest → render (text layer + page images) → classify (keywords | LLM)
       → extract (template | LLM) → normalize → verify (grounding, dates, arithmetic)
       → DocumentResult (records + pipeline trace)
Review (navigator confirms) → validate (cross-document flags)
       → evaluate (ledger → months, best month) → gaps, exemptions, deadline, summary
       → packet PDF, submission record PDF
```

## Why two extractors
The template parser makes the pipeline work fully offline and deterministically for the synthetic samples (judges can test without API keys). The LLM extractor handles arbitrary real-world layouts and images when configured. Both feed the same normalize and verify stages, so verification applies regardless of which extractor ran.

## Correctness properties (hypothesis)
- P1 Order independence: permuting records never changes MonthResults.
- P2 Monotonicity: adding a countable record never lowers a month's status rank or totals.
- P3 Unconfirmed exclusion: records with an unconfirmed low-confidence field never appear in countedRecordIds.
- P4 Split conservation: allocated hours (hundredths) and cents sum exactly to the record totals.
- P5 Duplicates collapse: duplicating any record leaves results unchanged.
- P6 Threshold boundary: exactly the threshold meets; 0.01 hour less with no other path does not.
- P7 Unresolved never meets: a month whose only satisfied path depends on an unresolved rule is never "meets".
- P8 Best-month dominance: the best month's status rank ≥ every other month's.

## Pipeline correctness checks
- Template extraction on every synthetic sample equals ground truth.
- Every extracted value on a text-layer page is grounded; a tampered value is detected as ungrounded.
- End-to-end on the 7 samples reproduces EVAL_BEFORE and, after confirmation, EVAL_AFTER.
- `make eval` reports classification accuracy, field accuracy, grounding rate, and false-pass count.
