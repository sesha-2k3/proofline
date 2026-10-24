# Proofline

Proofline helps Massachusetts benefits navigators keep eligible MassHealth members covered under the Medicaid work and education requirements that begin January 1, 2027. A navigator uploads a client's notice and evidence. Proofline reads each document, checks what it read against the page, finds the strongest single qualifying month, and builds a PDF packet and a submission record.

AI reads; code decides. Every threshold comes from `rules/masshealth.yaml`, and results that depend on an unresolved rule are shown as "Conditional" with the rule named. MassHealth makes all eligibility decisions.

All sample data is synthetic (demo persona: Jorge Ramos).

## Live demo

**URL:** `<add the Render URL here after deploying>`

The live app runs in demo mode: no LLM keys, offline template extraction of the synthetic samples. No documents or case data are stored.

### Testing steps (about 3 minutes)
1. Open the URL and click **Load sample case (Jorge)**.
2. Step 1 is prefilled (renewal, February–June 2027, RFI received June 12, 2027). Click **Continue to documents**.
3. Step 2 uploads the 7 sample documents. Open a **pipeline trace** to see each stage (ingest, render, classify, extract, normalize, verify). Click **Continue to review**.
4. Step 3: the Eastside Community Food Pantry's May hours (24.00) show **Needs confirmation** (handwritten in the source). Leave it unconfirmed and click **Evaluate**.
5. Step 4: May 2027 is **Conditional**. The gaps list the unconfirmed record and the two unresolved rules. Click **Back to review**.
6. Confirm the pantry's May hours, then **Evaluate** again. May 2027 now **Meets** (92.93 hours).
7. Click **Continue to packet**. Step 5: **Download packet**, log a submission, then **Download submission record**.

Optional: toggle **ES** for Spanish, or upload your own synthetic PDF/PNG (unknown types ask you to choose a type).

## Run locally

Requirements: Python 3.12 with [uv](https://docs.astral.sh/uv/), Node 22+.

```bash
cd backend && uv sync && cd ..
cd frontend && npm install && cd ..
make dev-backend     # terminal 1: http://localhost:8000 (API docs at /docs)
make dev-frontend    # terminal 2: http://localhost:5173
```

Other commands:

| Command | What it does |
|---|---|
| `make test` | Backend tests (pytest + hypothesis property tests) |
| `make openapi` | Export `shared/openapi.json` and regenerate frontend API types |
| `make synth` | Regenerate the synthetic sample PDFs and ground truth |
| `make eval` | Run the pipeline over the samples and write `docs/eval_report.md` |

Optional LLM extraction (for non-template documents): set `LLM_PROVIDER` (`anthropic` or `bedrock`), `MODEL_ID`, and `ANTHROPIC_API_KEY` or AWS credentials with `AWS_REGION`. Without them the app runs in demo mode.

## Docker (one URL)

The multi-stage `Dockerfile` builds the frontend, then runs FastAPI, which serves the SPA, `/api`, and `/samples` on one port.

```bash
docker build -t proofline .
docker run --rm -p 8000:8000 proofline   # open http://localhost:8000
```

The container listens on `$PORT` (default 8000).

## Deploy (Render)

`render.yaml` defines one Docker web service with a health check on `/api/health` and no LLM env vars (demo mode). To deploy: push the repo to GitHub, then in Render choose **New → Blueprint**, select the repo, and apply. Put the resulting URL in the "Live demo" section above.

## Layout

- `backend/` FastAPI app: document pipeline (`app/pipeline`), ledger engine (`app/ledger`), validation, reporting, PDF packet.
- `frontend/` React + Vite + Tailwind SPA; API types generated from `shared/openapi.json`.
- `rules/masshealth.yaml` rules source of truth (each rule has a source and status).
- `docs/` decisions, Kiro log, evaluation report.
- `.kiro/` spec, steering, and hooks used to build the project.
