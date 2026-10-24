---
inclusion: always
---
# Project structure

```
backend/
  pyproject.toml
  app/
    main.py                FastAPI app, routers, /samples static mount, frontend dist mount (prod)
    settings.py            pydantic-settings
    schemas/               Pydantic API models = the API contract (common.py, evidence.py, ledger.py, api.py)
    api/                   routers: health.py, rules.py, samples.py, documents.py, validate.py, evaluate.py, packet.py, timeline.py
    rules/                 loader.py (YAML -> validated model), accessors.py, sources.py
    mocks/                 jorge.py (exact scenario data from BUILD_PLAN.md)
    pipeline/              document processing pipeline
      ingest.py            size/type checks, sha256, page count
      render.py            PDF text layer + page images (pypdfium2), image loading (pillow)
      classify.py          keyword classifier (offline) + LLM classifier
      extract/             template.py (offline parser for synthetic layouts), llm.py, prompts.py
      normalize.py         values -> canonical types, records from extracted fields
      verify.py            grounding, arithmetic, date sanity, confidence calibration
      orchestrator.py      runs stages, builds pipeline trace
    validation/checks.py   cross-document checks
    ledger/                split.py, evaluate.py (pure, no I/O)
    reporting/             gaps.py, exemptions.py, summary.py, deadline.py
    packet/                packet.py, timeline.py (reportlab)
  scripts/                 export_openapi.py, generate_synthetic.py, eval_extraction.py
  samples/                 generated synthetic PDFs (served at /samples)
  synthetic/ground_truth.json
  tests/
frontend/
  src/
    api/                   schema.d.ts (generated), client.ts
    state/                 caseState.tsx
    i18n/                  en.ts, es.ts, useT.ts
    pages/                 LandingPage.tsx, CasePage.tsx
    components/            AppShell, CaseSetupForm, Uploader, PipelineTrace, ReviewPanel, ExemptionQuestions, MonthCards, GapList, PacketPanel
rules/masshealth.yaml      rules source of truth
shared/openapi.json        exported by backend, consumed by frontend type generation
docs/                      KIRO_LOG.md, DECISIONS.md, FRONTEND_REQUESTS.md
Makefile
BUILD_PLAN.md
```
Ownership: backend owner: backend/, rules/, shared/. Frontend owner: frontend/. Only the backend owner changes backend/app/schemas (then runs `make openapi`).
