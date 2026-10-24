---
inclusion: fileMatch
fileMatchPattern: "{backend/app/schemas/**,backend/app/api/**,frontend/src/**,shared/**}"
---
# API contract rules
- The contract is the Pydantic models in backend/app/schemas. FastAPI exports it to shared/openapi.json (`make openapi`); the frontend generates types from it (`npm run gen:api`).
- Every endpoint declares response_model and validates request bodies with the schema models. Errors use the ErrorBody shape.
- Frontend never hand-writes API types and calls the API only through frontend/src/api/client.ts.
- After any schema change: run `make openapi`, commit shared/openapi.json, and note the change in docs/FRONTEND_REQUESTS.md under "Changes".
