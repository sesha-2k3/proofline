---
inclusion: always
---
# Tech stack and conventions

- Framework: Next.js (App Router) with TypeScript in strict mode. One repo, one language.
- Styling: Tailwind CSS. Clean, accessible, high contrast; keyboard navigable; label every input.
- Validation and schemas: zod. Every evidence record and extraction result has a zod schema.
- Tests: Vitest for unit tests; fast-check for property-based tests.
- PDF generation: pdf-lib.
- Rules: `rules/masshealth.yaml`, parsed with the `yaml` package and validated with zod at startup.
- LLM: a small provider interface in `lib/llm/` with one implementation chosen by env vars:
  - `LLM_PROVIDER` = `bedrock` or `anthropic`
  - `MODEL_ID` = the vision-capable model id to use
  - Never hardcode keys. Read from env only.
- Demo mode: if no LLM credentials are set, or a call fails, extraction falls back to fixture JSON for the synthetic documents and the UI shows a visible "Demo mode" badge.
- No database. State lives in memory (React state + request scope). Nothing is written to disk on the server.
- Deployment target: Vercel or AWS Amplify (free tier), so judges get a public link.

## Commands
- `npm run dev` — local dev server
- `npm test` — all tests (Vitest)
- `npm run synth` — regenerate synthetic sample documents and ground truth
- `npm run eval` — run extraction against synthetic documents and print accuracy and false-pass rate

## Code style
- Pure functions for all rules and ledger logic (no I/O inside `lib/ledger/`).
- Money in integer cents; hours as numbers with up to 2 decimals; dates as ISO `YYYY-MM-DD` strings; months as `YYYY-MM`.
- Small modules, explicit types, no `any`.
