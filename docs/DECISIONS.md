# Decisions

- B1: Routers are registered through a `ROUTERS` list in `app/main.py`; it starts empty and later steps append to it.
- B1: The SPA fallback is a catch-all GET route registered after `/api` and `/samples`; it returns 404 for `/api/*` and `/samples/*`.
- B3: `rules_version()` returns `meta.last_reviewed` from rules/masshealth.yaml; the loader also rejects any non-null source not in `SOURCES`.
- B4: Mock records use the sample file name as `docId`; POST /documents replaces it with the request `doc_id`. Multipart form fields are named `file`, `doc_id`, `doc_type_hint` (snake_case, as in BUILD_PLAN).
- B4: Mock pipeline trace: all six stages "ok" for recognized files; for unknown files ingest/render "ok" and the rest "skipped", extractor "none", classificationConfidence "low".
- B4: Mock thresholds in Jorge data (shortfalls, "80"/"$580" in messages) are computed from rules accessors, not literals. Spanish summaries are in `SUMMARIES` in app/mocks/jorge.py.
- B4: POST /packet and /timeline return `application/pdf` with Content-Disposition attachment; no JSON response model.
