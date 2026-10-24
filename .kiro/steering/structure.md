---
inclusion: always
---
# Project structure

```
app/                      Next.js routes and pages
  page.tsx                Landing + start a case
  case/page.tsx           Upload -> review -> results flow (client component)
  api/extract/route.ts    POST: classify + extract one document
  api/packet/route.ts     POST: build PDF packet + submission record
components/               UI components (Uploader, ReviewTable, LedgerView, GapReport, DemoBadge)
lib/
  rules/                  load + validate rules/masshealth.yaml
  schemas/                zod schemas (EvidenceRecord, ExtractionResult, MonthResult, etc.)
  llm/                    provider interface + bedrock + anthropic implementations
  extraction/             prompts, per-document-type schemas, demo-mode fixtures
  validation/             recency, arithmetic, duplicate, name-match checks
  ledger/                 pure ledger engine (month bucketing, splitting, evaluation, best month)
  packet/                 pdf-lib packet + submission record timeline
rules/masshealth.yaml     every rule with source + status
synthetic/                generator script, sample PDFs, ground-truth JSON
eval/                     eval script and latest report
tests/                    Vitest unit + property-based tests
docs/KIRO_LOG.md          running log of how Kiro features helped (for the write-up)
```

Keep `lib/ledger/` free of framework imports so it can be tested in isolation.
