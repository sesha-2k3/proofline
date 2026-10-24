---
inclusion: always
---
# Tech stack and conventions

## Backend (backend/)
- Python 3.12, FastAPI, Pydantic v2, uvicorn. Package manager: uv (`uv run ...`, `uv add ...`).
- Libraries: pydantic-settings, python-multipart, pyyaml, pypdfium2 (PDF text + page rendering), pillow, reportlab (PDF generation), anthropic and boto3 (LLM providers), httpx.
- Tests: pytest + hypothesis (property-based). Lint: ruff.
- All API models inherit `ApiModel` (Pydantic, camelCase aliases via alias_generator=to_camel, populate_by_name=True). JSON on the wire is camelCase.
- Settings from env via pydantic-settings: LLM_PROVIDER (anthropic | bedrock | empty), MODEL_ID, ANTHROPIC_API_KEY, AWS_REGION, MAX_UPLOAD_MB=10.
- No database, no disk writes of uploads. Process in memory per request.
- Rules loaded once at startup from rules/masshealth.yaml and validated; app refuses to start if invalid.

## Frontend (frontend/)
- React 18+ with Vite, TypeScript strict, Tailwind CSS 4 (@tailwindcss/vite), react-router-dom.
- API types generated from the backend OpenAPI schema with openapi-typescript into frontend/src/api/schema.d.ts; calls via openapi-fetch. Never hand-write API types.
- State: React useReducer + context. No localStorage/sessionStorage/cookies for case data.
- Dev server proxies /api and /samples to http://localhost:8000.

## Conventions
- Money in integer cents. Hours as numbers with 2 decimals; ledger arithmetic in integer hundredths. Dates "YYYY-MM-DD", months "YYYY-MM".
- Commands: `make dev-backend`, `make dev-frontend`, `make test`, `make openapi`, `make synth`, `make eval`.
