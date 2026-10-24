# Implementation Plan: Proofline MVP

Labels: [BE] backend owner, [FE] frontend owner. Backend pushes tasks 1–3 first so the frontend is unblocked.
API contract: docs/api-contract.md.

- [x] 1. [BE] Scaffold the project (push within ~15 minutes)
  - Next.js App Router, TypeScript strict, Tailwind, Vitest, fast-check, zod, yaml, pdf-lib.
  - npm scripts: dev, build, test, synth, eval.
  - Create `docs/KIRO_LOG.md` headings if missing.
  - _Requirements: 1.1_

- [ ] 2. [BE] Shared schemas from the API contract
  - Implement every type in docs/api-contract.md as zod schemas in `lib/schemas/` with exported `z.infer` types.
  - Request/response schemas for each endpoint.
  - _Requirements: 3.3, 6.2_

- [ ] 3. [BE] Mock endpoints (unblocks frontend)
  - `lib/mocks/` JSON for every endpoint, based on the Jorge scenario in design.md (include a low-confidence pantry field, a conditional May before confirmation, and a meets May after).
  - Route handlers for all 8 endpoints returning mocks; validate requests with zod; documented error shape.
  - `tests/contract.test.ts`: every mock parses against its schema.
  - Push and notify the frontend.

- [ ] 4. [BE] Rules loader + real GET /api/rules and /api/health
  - Zod schema for rules/masshealth.yaml; fail with rule id on missing source/status.
  - Typed accessors; unit tests.
  - _Requirements: 1.1–1.3_

- [ ] 5. [BE] Ledger engine (pure TypeScript)
  - Countability filter, dedupe, proportional split with alternative-method check, month evaluation, best month.
  - Property tests P1–P8 (≥200 runs) + boundary tests + synthetic scenario test.
  - _Requirements: 6.1–6.7, 5.3_

- [ ] 6. [BE] Checkpoint: `npm test` all green.

- [ ] 7. [BE] Synthetic documents + real GET /api/samples
  - `synthetic/generate.ts` creates the seven PDFs into `public/samples/`, `synthetic/ground_truth.json`, and demo fixtures in `lib/extraction/fixtures/`.
  - _Requirements: 3.5_

- [ ] 8. [BE] Real POST /api/extract
  - LLM provider interface (bedrock | anthropic via env), classification + extraction prompts, zod parse with one retry, demo-mode fallback.
  - _Requirements: 3.1–3.6_

- [ ] 9. [BE] Real POST /api/validate
  - Arithmetic, duplicate, stale (provisional), volunteer org, name match, low-confidence-unconfirmed flags; unit tests.
  - _Requirements: 4.1–4.5_

- [ ] 10. [BE] Real POST /api/evaluate
  - Wire validation + ledger + exemptions + gap report + deadline; LLM summary constrained to computed facts (template in demo mode); en/es.
  - _Requirements: 6, 7, 8.1, 8.4_

- [ ] 11. [BE] Real POST /api/packet and POST /api/timeline (pdf-lib)
  - _Requirements: 8.2, 8.3_

- [ ] 12. [FE] UI flow against the contract (start immediately on mocks)
  - [ ] 12.1 App shell, health check, Demo mode badge, en/es toggle.
  - [ ] 12.2 Case setup form (renewal window or application month, RFI date, deadline display with "provisional" label).
  - [ ] 12.3 Uploader with per-file progress + "Load sample case (Jorge)" via /api/samples.
  - [ ] 12.4 Unknown-document labeling (re-call extract with docTypeHint).
  - [ ] 12.5 Review table: document preview beside fields, low-confidence and flags highlighted, edit + confirm, re-validate.
  - [ ] 12.6 Exemption questionnaire from /api/rules ("Possible exemption — navigator to confirm").
  - [ ] 12.7 Results: month cards with status badges, best month highlighted, unresolved rules explained, gap report, summary.
  - [ ] 12.8 Packet download and submission log + timeline download.
  - [ ] 12.9 Accessibility pass (labels, focus order, contrast).
  - _Requirements: 2, 3.4, 5, 7, 8_

- [ ] 13. [BE] Eval script (`npm run eval`, writes eval/report.md). Skip if behind.

- [ ] 14. [BE+FE] README (run, env vars, demo mode, judge testing steps, Kiro section) and deploy; live link in README.
