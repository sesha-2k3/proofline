---
inclusion: fileMatch
fileMatchPattern: "{app/**,components/**,lib/schemas/**,lib/mocks/**}"
---
# API contract rules

The API contract is defined in #[[file:docs/api-contract.md]] and implemented as zod schemas in `lib/schemas/`.

- Frontend code must call only the endpoints in the contract and must import types from `lib/schemas/` (`z.infer`), never redeclare them.
- Backend route handlers must validate every request body with the zod schema and return the documented error shape on failure.
- Every mock in `lib/mocks/` must parse successfully against its zod schema (enforced by `tests/contract.test.ts`).
- Any schema change must update `docs/api-contract.md` and `lib/mocks/` in the same change.
- No new fields that the frontend relies on without adding them to the contract doc first.
