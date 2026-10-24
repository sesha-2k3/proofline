# Proofline build plan — React + FastAPI + document processing pipeline

Agent rules: follow .kiro/steering/speed.md. Execute one step (or the listed group) per session. Write the files the step lists, run its checks, fix failures, report briefly. This plan and its Appendix override the spec's design.md where they differ.

Owners: **[BE]** backend (Python), **[FE]** frontend (React). Backend steps B1–B4 come first; after B4 is pushed the frontend can build against real URLs that return mock data.

---------------------------------------------------------------------
## PART 0 — Setup (run by a human, ~10 minutes)

```bash
# from the folder that contains this starter's files
git init
# Backend
mkdir -p backend && cd backend
uv init --app --python 3.12 --name proofline-backend .
rm -f main.py hello.py
uv add fastapi "uvicorn[standard]" pydantic pydantic-settings python-multipart pyyaml pypdfium2 pillow reportlab anthropic boto3 httpx
uv add --dev pytest hypothesis ruff
cd ..
# Frontend
npm create vite@latest frontend -- --template react-ts
cd frontend && npm install
npm install react-router-dom openapi-fetch
npm install -D tailwindcss @tailwindcss/vite openapi-typescript
cd ..
mkdir -p shared docs
```
No uv? Use `python3.12 -m venv backend/.venv && backend/.venv/bin/pip install ...` and replace `uv run` with the venv's python.

`.gitignore` must include: `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`, `__pycache__/`, `.env`. It must NOT include `.kiro/`.

---------------------------------------------------------------------
## PART 1 — Backend foundation

### B1 — skeleton [BE]
- `backend/app/settings.py`: `Settings(BaseSettings)` with `llm_provider: Literal["anthropic","bedrock",""] = ""`, `model_id: str = ""`, `anthropic_api_key: str = ""`, `aws_region: str = "us-east-1"`, `max_upload_mb: int = 10`, `rules_path: Path` (default: repo-root/rules/masshealth.yaml), `samples_dir: Path` (default backend/samples), `frontend_dist: Path` (default repo-root/frontend/dist). `get_settings()` cached. `demo_mode` property = provider empty or no model id.
- `backend/app/main.py`: create app (title "Proofline API", version "1.0.0"), include routers under prefix `/api`, CORS allowing http://localhost:5173, mount `/samples` StaticFiles from samples_dir (create dir if missing), and if frontend_dist exists mount it at `/` with SPA fallback (any non-/api, non-/samples GET returns index.html). Exception handler converting `ApiError` to the ErrorBody JSON shape.
- `backend/app/errors.py`: `class ApiError(Exception): code, message, status, details`.
- Root `Makefile`:
  - `dev-backend`: `cd backend && uv run uvicorn app.main:app --reload --port 8000`
  - `dev-frontend`: `cd frontend && npm run dev`
  - `test`: `cd backend && uv run pytest -q`
  - `openapi`: `cd backend && uv run python scripts/export_openapi.py && cd ../frontend && npm run gen:api`
  - `synth`: `cd backend && uv run python scripts/generate_synthetic.py`
  - `eval`: `cd backend && uv run python scripts/eval_extraction.py`
- `backend/pyproject.toml`: add `[tool.pytest.ini_options] testpaths=["tests"] pythonpath=["."]`.
- `docs/DECISIONS.md`, `docs/FRONTEND_REQUESTS.md` (headings "Requests" and "Changes").
Check: `make dev-backend` starts; GET http://localhost:8000/docs loads.

### B2 — schemas (the API contract) [BE]
All models inherit:
```python
class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
```
`backend/app/schemas/common.py`
- `Lang = Literal["en","es"]`, `Confidence = Literal["high","low"]`, `RuleStatus = Literal["confirmed","provisional","unresolved"]`
- `IsoDate = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}-\d{2}$")]`, `IsoMonth = Annotated[str, StringConstraints(pattern=r"^\d{4}-\d{2}$")]`
- `Verification = Literal["grounded","ungrounded","not_checked"]`
- Concrete field models (no generics): `StrField`, `NumField`, `BoolField`, `DateField`, `OrgTypeField`; each has `value: <type> | None`, `confidence: Confidence`, `page: int (>=1)`, `confirmed: bool = False`, `evidence: str | None = None` (source text snippet), `verification: Verification = "not_checked"`. OrgType values: public, nonprofit, for_profit, political, unknown.
- `DocType = Literal["rfi_notice","paystub","employer_statement","gig_earnings","volunteer_letter","school_letter","unknown"]`
- `CaseInfo`: client_name (min 1), case_type ("renewal" | "new_application"), window_start: IsoMonth | None, window_end: IsoMonth | None, application_month: IsoMonth | None, rfi_received_date: IsoDate | None, lang: Lang = "en".
- `ErrorBody { error: { code: Literal["BAD_REQUEST","UNSUPPORTED_FILE","EXTRACTION_FAILED","RULES_INVALID","INTERNAL"], message: str, details: Any | None } }`
`backend/app/schemas/evidence.py`
- `ActivityType = Literal["work","volunteer","job_training","school","income_only"]`
- `RecordDocType` = DocType minus rfi_notice and unknown.
- `FlagCode = Literal["ARITHMETIC_MISMATCH","DUPLICATE","STALE_DOCUMENT","VOLUNTEER_ORG_INELIGIBLE","NAME_MISMATCH","LOW_CONFIDENCE_UNCONFIRMED","UNGROUNDED_VALUE","DATE_OUT_OF_RANGE"]`
- `Flag { code, message, field: str | None, rule_id: str | None, rule_status: RuleStatus | None }`
- `EvidenceRecord { id, doc_id, doc_type: RecordDocType, activity, person_name: StrField, issuer: StrField, org_type: OrgTypeField | None, non_partisan: BoolField | None, period_start: DateField, period_end: DateField, hours: NumField | None, hourly_rate_cents: NumField | None, gross_cents: NumField | None, expenses_cents: NumField | None, half_time_enrolled: BoolField | None, document_date: DateField, flags: list[Flag] = [] }`
- `NoticeInfo { notice_date: DateField, response_deadline: DateField | None, request_summary: StrField }`
- `PipelineStage { stage: Literal["ingest","render","classify","extract","normalize","verify"], status: Literal["ok","warning","failed","skipped"], duration_ms: int, detail: str }`
`backend/app/schemas/ledger.py`
- `MonthStatus = Literal["meets","conditional","short"]`
- `MonthResult { month, work_hours, volunteer_hours, training_hours: float, school_half_time: bool, gross_income_cents, net_income_cents: int, status, paths_met: list[str], depends_on_unresolved: list[str], hours_shortfall: float, income_shortfall_cents: int, counted_record_ids: list[str], excluded_record_ids: list[str] }`
- `GapItem { month, kind: Literal["hours","income","unresolved_rule","unconfirmed_record"], message, suggested_doc_types: list[DocType], rule_id: str | None }`
- `PossibleExemption { id, label, source, source_url }`, `Deadline { date: IsoDate, rule_id: Literal["rfi_response_days"], rule_status: RuleStatus }`
`backend/app/schemas/api.py`
- `HealthResponse { ok: bool, demo_mode: bool, llm_provider: Literal["anthropic","bedrock","none"], rules_version: str }`
- `RulesResponse { rules_version, thresholds: { hours: float, income_cents: int, rfi_response_days: int }, rule_statuses: dict[str, RuleStatus], unresolved_rules: list[{id, description}], exemption_questions: list[PossibleExemption], sources: dict[str,str] }`
- `SampleFile { name, url, doc_type: DocType }`, `SamplesResponse { files, case_info: CaseInfo, rules_version }`
- `DocumentResult { doc_id, file_name, doc_type: DocType, classification_confidence: Confidence, extractor: Literal["template","llm","none"], records: list[EvidenceRecord], notice: NoticeInfo | None, pipeline: list[PipelineStage], warnings: list[str], demo_mode: bool, rules_version }`
- `ValidateRequest { case_info, records }`, `ValidateResponse { records, rules_version }`
- `ExemptionAnswer { id, answer: bool }`, `EvaluateRequest { case_info, records, exemption_answers: list[ExemptionAnswer] = [] }`
- `EvaluateResponse { months: list[MonthResult], best_month: IsoMonth | None, deadline: Deadline | None, possible_exemptions, gaps, summary: str, demo_mode, rules_version }`
- `SubmissionEntry { submitted_at: IsoDate, channel: Literal["online","mail","fax","in_person","phone"], confirmation_number: str | None, documents_included: list[str], notes: str | None }`
- `PacketRequest { case_info, records, evaluation: EvaluateResponse }`, `TimelineRequest { case_info, submissions: list[SubmissionEntry] }`
- `backend/scripts/export_openapi.py`: writes `app.openapi()` to `shared/openapi.json` (indent 2).
Check: `uv run python scripts/export_openapi.py` writes the file.

### B3 — rules loader and accessors [BE]
- `backend/app/rules/loader.py`: Pydantic `RuleEntry { id, description: str|None, label: str|None, value: float|bool|None, options: list[str]|None, default_for_display: str|None, allowed_org_types: list[str]|None, requires_non_partisan: bool|None, source: str|None, status: RuleStatus }` with model_validator: source may be None only if status == "unresolved" (error message includes the id). `RulesFile { meta: {program, effective_date, last_reviewed, disclaimer}, compliance_window, paths, documents, exemptions: list[RuleEntry] }`, extra="forbid". `load_rules(path) -> RulesFile`; also checks ids are unique. Loaded once at startup (lifespan); failure raises with the rule id.
- `backend/app/rules/sources.py`: `SOURCES = {"S1": "https://www.mass.gov/info-details/new-work-and-education-requirements-for-masshealth-members", "S2": "https://www.mass.gov/info-details/masshealth-and-health-connector-acceptable-verifications-list", "S3": "https://www.mass.gov/doc/external-ob3-set-deck/download", "S5": "https://www.mass.gov/MassHealthMemberChanges"}`
- `backend/app/rules/accessors.py`: `rules_version()`, `hours_threshold() -> int hundredths` and `hours_threshold_hours() -> float`, `income_threshold_cents()`, `rfi_response_days()`, `paystub_recency_days()`, `allowed_volunteer_org_types()`, `rule_status(id)`, `is_unresolved(id)`, `unresolved_rules()`, `exemptions()` (with source_url from SOURCES).
- Tests: valid file loads; a copy with a missing source on a confirmed rule fails with the id in the message.

### B4 — mocks + mock-backed API [BE] (push after this; frontend starts)
- `backend/app/mocks/jorge.py`: build the exact data in the Appendix "Jorge scenario" as model instances: `JORGE_RECORDS`, `JORGE_NOTICE`, `JORGE_SAMPLES`, `JORGE_CASE`, `EVAL_BEFORE`, `EVAL_AFTER` (MonthResults, gaps, summaries en/es).
- Routers (all under /api), each with `response_model`:
  - `GET /health` → real settings (demo_mode, llm_provider "none" if empty).
  - `GET /rules` → from accessors (real).
  - `GET /samples` → JORGE_SAMPLES + JORGE_CASE.
  - `POST /documents` (multipart: `file`, `doc_id`, optional `doc_type_hint`): mock: match file name to JORGE_SAMPLES and return its records (doc_id replaced) and a fake pipeline trace (all stages "ok"); rfi_notice returns notice; unknown names → doc_type "unknown" (or the hint), records [], warning "Could not recognize this document. Choose its type."
  - `POST /validate`: echo records; add LOW_CONFIDENCE_UNCONFIRMED (field "hours") when hours.confidence == "low" and not confirmed.
  - `POST /evaluate`: if the volunteer_letter record with period_start 2027-05-01 has hours.confirmed → EVAL_AFTER else EVAL_BEFORE; possible_exemptions = exemptions whose id has answer true; summary in case_info.lang.
  - `POST /packet`, `POST /timeline`: one-page reportlab PDF "Mock PDF"; filenames `proofline-packet-<month>.pdf`, `proofline-submission-record.pdf`.
- `tests/test_contract.py` (httpx TestClient): each endpoint returns 200 and parses into its response model; evaluate before/after switches on confirmation.
- Run `make openapi`; commit `shared/openapi.json`.
Check: `make test` green. Push to master.

---------------------------------------------------------------------
## PART 2 — Backend core

### B5 — ledger engine (pure) [BE] — the most important step
- `backend/app/ledger/split.py`: `allocate_proportional(start, end, hours_h, gross, expenses) -> dict[month, Share]` using cumulative rounding (Appendix 2); `allocate_by_end_date(...)`.
- `backend/app/ledger/evaluate.py`: `evaluate_case(case_info, records) -> tuple[list[MonthResult], str | None]` implementing Appendix decisions 1–11. Months: window_start..window_end for renewal; only the month before application_month for new applications.
- Tests:
  - `tests/test_ledger_properties.py` (hypothesis, 200 examples): P1 order independence, P2 monotonicity (adding a countable record never lowers status rank or totals), P3 unconfirmed exclusion, P4 split conservation (exact in hundredths/cents), P5 duplicates collapse, P6 threshold boundary (exactly threshold meets; threshold − 0.01 h with no other path does not), P7 a month whose only satisfied path depends on an unresolved rule is never "meets", P8 best month has the highest status rank.
  - `tests/test_ledger_scenario.py`: JORGE_RECORDS → EVAL_BEFORE months exactly; with pantry May hours confirmed → EVAL_AFTER months exactly.
  - `tests/test_ledger_boundary.py`: 79.99 vs 80 h; 57999 vs 58000 cents; a record spanning two months.

### B6 — synthetic documents [BE]
- `backend/scripts/generate_synthetic.py` (reportlab, Helvetica, letter size): writes the 7 PDFs in the Appendix to `backend/samples/` with real text layers. Every page starts with the banner "SAMPLE — SYNTHETIC — NOT A REAL DOCUMENT". Each document uses labeled lines exactly as listed in Appendix "Synthetic layouts" so the offline template parser can read them. Writes `backend/synthetic/ground_truth.json` (records + notice per file, from jorge.py).
Check: `make synth` creates 7 PDFs; open one to confirm.

---------------------------------------------------------------------
## PART 3 — Document processing pipeline [BE]

Pipeline per uploaded file (orchestrator.py), each stage timed and recorded as a PipelineStage:

| Stage | Module | What it does |
|---|---|---|
| ingest | ingest.py | Check extension/MIME in {pdf, png, jpg/jpeg}, size ≤ max_upload_mb, compute sha256, page count (PDF ≤ 10 pages). Fail → ApiError UNSUPPORTED_FILE. |
| render | render.py | PDF: per-page text via pypdfium2 (get_textpage().get_text_range()) and page images at scale 2 as PNG bytes (only if the LLM path will run). Image: load with pillow, convert to PNG. Output `PageContent { page, text, image_png | None }`. |
| classify | classify.py | If doc_type_hint given → use it. Else offline keyword classifier on text (Appendix "Keywords"); if no text or no confident match and LLM available → LLM classify on page images; else "unknown". |
| extract | extract/ | Template parser first when text matches a known layout (synthetic samples, also offline). Otherwise LLM extractor (if available) on page images + text. Otherwise none → records [] with warning "Enter the values manually." |
| normalize | normalize.py | Convert raw strings to canonical values: money → cents, hours → float (2 dp), dates (formats: YYYY-MM-DD, MM/DD/YYYY, "May 1, 2027") → ISO. Build EvidenceRecords (one per period line) with deterministic ids `rec-<docType>-<issuer-slug>-<periodStart>` and the request doc_id. |
| verify | verify.py | Field-level verification (Appendix "Verification"). Sets verification, evidence, and final confidence on each field; adds UNGROUNDED_VALUE / DATE_OUT_OF_RANGE / ARITHMETIC_MISMATCH flags. |

### B7 — ingest, render, classify [BE]
- Implement ingest.py, render.py, classify.py (offline keywords + LLM function stub that returns None when demo_mode).
- Tests with the generated samples: each of the 7 classifies correctly offline; a random PNG with no text → "unknown" in demo mode.

### B8 — extraction [BE]
- `extract/template.py`: regex parsers for the 7 synthetic layouts (Appendix). Return raw fields with confidence "high", except values on a line containing "[handwritten" → "low". Each raw field keeps `page` and the matched line as `evidence`.
- `extract/prompts.py`: classification prompt and per-doc-type extraction prompt. Instruct: return JSON only; every field `{ "value": ..., "confidence": "high"|"low", "page": n, "evidence": "<exact text you read>" }`; null instead of guessing; "low" when unclear, handwritten, or partially visible; one entry per month/period.
- `extract/llm.py`: `LlmClient` with `classify(pages)` and `extract(doc_type, pages)`; implementations for anthropic (messages API with base64 image blocks) and bedrock (boto3 bedrock-runtime converse with image blocks); parse JSON, validate with a Pydantic raw model, one retry on parse failure, then give up (warning, records []).
- Tests: template parser on all 7 samples matches ground truth exactly (including pantry May hours = "low"). LLM client tested with a fake client returning fixed JSON.

### B9 — normalize, verify, orchestrator, real POST /documents [BE]
- Implement normalize.py, verify.py (Appendix "Verification"), orchestrator.py, and swap the mock in POST /documents for the orchestrator. Response `extractor` reflects the path used; `demo_mode` from settings.
- Tests: uploading each sample through the API returns records equal to ground truth (ignoring doc_id), with every field "grounded"; a hand-edited text PDF whose value differs from its evidence → UNGROUNDED_VALUE and confidence "low".

---------------------------------------------------------------------
## PART 4 — Backend results

### B10 — validation, evaluate, reporting [BE]
- `validation/checks.py` (cross-document): DUPLICATE (same doc_type, issuer value, period), STALE_DOCUMENT (document_date more than paystub_recency_days before rfi_received_date; rule_status provisional), VOLUNTEER_ORG_INELIGIBLE, NAME_MISMATCH (case-insensitive vs case_info.client_name), LOW_CONFIDENCE_UNCONFIRMED (one flag per low-confidence unconfirmed field). Keep pipeline flags from verify.
- `reporting/deadline.py` (rfi_received_date + rfi_response_days), `reporting/exemptions.py`, `reporting/gaps.py` (rules in Appendix "Gaps"), `reporting/summary.py` (templates en/es restating computed numbers; if LLM available, it may only rephrase the template text and must keep every number unchanged — verify numbers appear unchanged, else fall back to the template).
- Swap mocks in POST /validate and POST /evaluate for real logic.
- Tests: end-to-end through the API with the 7 sample PDFs: upload all → validate → evaluate equals EVAL_BEFORE (months, gaps); confirm pantry May hours → EVAL_AFTER.

### B11 — PDFs [BE]
- `packet/packet.py` (reportlab): cover (client, case type, best month and status, totals by activity, paths met, unresolved rules affecting the result, deadline labeled "provisional" when so, disclaimer "This summary organizes evidence. MassHealth makes all eligibility decisions."), evidence table (record, issuer, period, hours, amount, source page, verification, confirmed by navigator), possible exemptions with sources. `packet/timeline.py`: submissions table.
- Tests: both endpoints return bytes starting with %PDF.

### B12 — evaluation script [BE]
- `scripts/eval_extraction.py`: run the pipeline over backend/samples, compare with ground_truth.json; print and write `docs/eval_report.md` with classification accuracy, field accuracy, grounding rate, and false-pass count (ledger on extracted vs ledger on ground truth).

### B13 — packaging and deploy [BE]
- `Dockerfile` (multi-stage): node stage builds frontend (`npm ci && npm run build`); python stage installs backend with uv, copies frontend/dist, runs `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. FastAPI serves the SPA, /api, and /samples from one URL.
- Deploy to Render (or Railway/Fly) as a Docker web service with no LLM env vars (demo mode). Put the URL in README.md with judge testing steps.

---------------------------------------------------------------------
## PART 5 — Frontend [FE] (start after B4 is on master)

Boundaries: edit only frontend/. Types only from the generated `src/api/schema.d.ts`. If the contract lacks something, write it under "Requests" in docs/FRONTEND_REQUESTS.md and continue.

### F1 — foundations
- `vite.config.ts`: react + @tailwindcss/vite plugins; dev proxy `/api` and `/samples` → http://localhost:8000.
- `src/index.css`: `@import "tailwindcss";` plus CSS variables for the palette.
- package.json script `"gen:api": "openapi-typescript ../shared/openapi.json -o src/api/schema.d.ts"`; run it.
- `src/api/client.ts`: openapi-fetch client; typed wrappers for all endpoints; throws `ApiError(message, code)` on ErrorBody; packet/timeline return Blob and trigger download.
- `src/state/caseState.tsx`: useReducer + context: caseInfo, documents ({docId, file, objectUrl, status, result}), records, evaluation, exemptionAnswers, submissions, step (1–5), health, rules.
- `src/i18n/en.ts`, `es.ts`, `useT.ts` (language from caseInfo.lang).
- React Router: `/` LandingPage, `/case` CasePage.

### F2 — shell and landing
- `AppShell`: header "Proofline", EN/ES toggle, "Demo mode" badge when health.demoMode, step indicator (1 Case · 2 Documents · 3 Review · 4 Results · 5 Packet).
- `LandingPage`: two-sentence description; buttons "Start a case" and "Load sample case (Jorge)" (→ /case?sample=1).

### F3 — case setup (step 1)
- `CaseSetupForm`: client name; case type; renewal window (month inputs) or application month; RFI received date. Sample mode prefills from GET /api/samples.

### F4 — documents (step 2)
- `Uploader`: drag-and-drop + picker (PDF/PNG/JPG, 10 MB), docId = crypto.randomUUID(), parallel POST /api/documents with per-file status. Unknown → type dropdown → re-upload with docTypeHint. Sample mode fetches each `/samples/<name>` as a File and uploads it.
- `PipelineTrace` (per document, collapsible): stage list with status icons and duration, extractor used, warnings. This makes the document processing visible in the demo.
- After all uploads: POST /api/validate → step 3.

### F5 — review (step 3)
- `ReviewPanel`: per document, preview (iframe/object for PDF via object URL, img for images) beside a field table: value (editable), confidence, verification badge (Grounded / Ungrounded / Not checked), evidence snippet, page, "Confirm" button. Low-confidence or ungrounded fields highlighted with "Needs confirmation". Counter of unconfirmed low-confidence fields. Re-validate after each change.
- `ExemptionQuestions`: yes/no from rules.exemptionQuestions; yes shows "Possible exemption — navigator to confirm" + source link. Never "exempt".
- "Evaluate" → POST /api/evaluate → step 4.

### F6 — results (step 4)
- `MonthCards`: per month status badge with color AND text (Meets / Conditional / Short), best month highlighted, hours and income totals, shortfalls, unresolved rules explained via rules.unresolvedRules.
- `GapList`, summary paragraph, deadline with "provisional" label. "Back to review" button.

### F7 — packet (step 5)
- `PacketPanel`: "Download packet"; submission log form (date, channel, confirmation number, documents included, notes), list of entries, "Download submission record".

### F8 — polish and walkthrough
- Accessibility: labels, focus rings, keyboard use, aria-live for upload/evaluate status, AA contrast, 375 px layout. Dismissible error alerts that keep work.
- Checks: `npm run build`, `npx tsc --noEmit`, `npm run lint`. Walkthrough: Load sample → 7 documents processed (pipeline traces visible) → pantry May hours "Needs confirmation" → Evaluate → May "Conditional" → Back → Confirm → Evaluate → May "Meets" → Download packet → log a submission → Download record.

---------------------------------------------------------------------
## PART 6 — Integration
1. Frontend runs `npm run gen:api` after each backend schema change (backend notes it under "Changes").
2. Merge branches into master after each step; master must always pass `make test` and `npm run build`.
3. Final: `docker build` locally, deploy (B13), run the walkthrough on the live URL, re-enable Kiro hooks and run each once for the write-up.

=====================================================================
## APPENDIX — Exact data and decisions (final; do not re-deliberate)

### Jorge scenario
Case: `{ clientName: "Jorge Ramos", caseType: "renewal", windowStart: "2027-02", windowEnd: "2027-06", rfiReceivedDate: "2027-06-12", lang: "en" }`.
Field defaults: confidence "high", page 1, confirmed false, verification "grounded", evidence = the template line. person_name "Jorge Ramos" on every record.

| id | doc_type | activity | issuer | period | hours | other | file |
|---|---|---|---|---|---|---|---|
| rec-gig_earnings-quickdash-2027-04-01 | gig_earnings | work | QuickDash | 2027-04-01..2027-04-30 | 14.00 | gross 32000, expenses 11000, docDate 2027-05-01 | quickdash_2027-04.pdf |
| rec-gig_earnings-quickdash-2027-05-01 | gig_earnings | work | QuickDash | 2027-05-01..2027-05-31 | 31.50 | gross 56000, expenses 21000, docDate 2027-06-01 | quickdash_2027-05.pdf |
| rec-employer_statement-ramos-family-bakery-2027-04-01 | employer_statement | work | Ramos Family Bakery | 2027-04-01..2027-04-30 | 20.00 | gross 0 (unpaid), docDate 2027-05-02 | bakery_statement_2027-04.pdf |
| rec-employer_statement-ramos-family-bakery-2027-05-01 | employer_statement | work | Ramos Family Bakery | 2027-05-01..2027-05-31 | 26.00 | gross 0 (unpaid), docDate 2027-06-02 | bakery_statement_2027-05.pdf |
| rec-volunteer_letter-eastside-community-food-pantry-2027-04-01 | volunteer_letter | volunteer | Eastside Community Food Pantry | 2027-04-01..2027-04-30 | 10.00 | org nonprofit, nonPartisan true, docDate 2027-06-05 | pantry_letter.pdf |
| rec-volunteer_letter-eastside-community-food-pantry-2027-05-01 | volunteer_letter | volunteer | Eastside Community Food Pantry | 2027-05-01..2027-05-31 | 24.00 **(confidence low)** | same | pantry_letter.pdf |
| rec-paystub-harbor-cafe-2027-05-24 | paystub | work | Harbor Cafe | 2027-05-24..2027-06-06 | 20.00 | rate 1550, gross 31000, docDate 2027-06-07 | harbor_cafe_paystub.pdf |

Notice (rfi_notice.pdf): noticeDate 2027-06-10, responseDeadline 2027-07-12, requestSummary "MassHealth is asking for proof that you met the work and education requirements for one month between February and June 2027."

EVAL_BEFORE months (training 0, school false everywhere):
| month | work | vol | gross | net | status | pathsMet | dependsOnUnresolved | hoursShort | incomeShort | excluded |
|---|---|---|---|---|---|---|---|---|---|---|
| 2027-02 | 0 | 0 | 0 | 0 | short | [] | [] | 80 | 58000 | [] |
| 2027-03 | 0 | 0 | 0 | 0 | short | [] | [] | 80 | 58000 | [] |
| 2027-04 | 34 | 10 | 32000 | 21000 | short | [] | [] | 36 | 26000 | [] |
| 2027-05 | 68.93 | 0 | 73714 | 52714 | conditional | [] | [self_employment_income_basis, pay_period_split_method] | 11.07 | 0 | [pantry May id] |
| 2027-06 | 8.57 | 0 | 13286 | 13286 | short | [] | [] | 71.43 | 44714 | [] |
countedRecordIds sorted by id; the cafe record counts in May and June.
EVAL_AFTER: same except 2027-05: vol 24, status meets, pathsMet [hours_threshold], dependsOnUnresolved [], hoursShort 0, incomeShort 0, excluded [], pantry May counted.
Both: bestMonth 2027-05; deadline { date 2027-07-12, ruleId rfi_response_days, ruleStatus provisional }.

Gaps BEFORE (in order): (1) 2027-05 unconfirmed_record: "The food pantry's May hours were hard to read. Confirm the 24 hours to count them." [volunteer_letter]; (2) 2027-05 unresolved_rule self_employment_income_basis: "May's income meets $580 only if gig income counts before expenses. MassHealth has not said which applies." []; (3) 2027-05 unresolved_rule pay_period_split_method: "Part of the Harbor Cafe pay period falls in June. How MassHealth splits pay periods is not published." []; (4–7) hours gaps for 2027-04, 2027-06, 2027-02, 2027-03: "<Month YYYY> is <N> hours short of 80." [employer_statement, volunteer_letter, paystub]. AFTER: only the four hours gaps.
Summary BEFORE (en): "May 2027 is the strongest month. Counted hours: 68.93 of 80. Income is $737.14 before expenses and $527.14 after. Whether May meets the requirement depends on rules MassHealth has not settled, and on confirming the food pantry's May hours. MassHealth makes the final decision." AFTER (en): "May 2027 is the strongest month. The evidence appears to show 92.93 qualifying hours, above the 80-hour requirement. Response deadline: July 12, 2027 (provisional). MassHealth makes the final decision." Provide Spanish versions.

### Synthetic layouts (labels exactly as written; one "Label: value" per line)
- rfi_notice.pdf: title "MassHealth Request for Information (SAMPLE)"; Member: Jorge Ramos; Notice date: 06/10/2027; Respond by: 07/12/2027; Request: <requestSummary>.
- quickdash_2027-MM.pdf: title "QuickDash Driver Earnings Summary"; Driver: Jorge Ramos; Period: 04/01/2027 - 04/30/2027; Active hours: 14.00; Gross earnings: $320.00; Expenses (mileage): $110.00; Statement date: 05/01/2027. (May: 31.50, $560.00, $210.00, 06/01/2027.)
- bakery_statement_2027-MM.pdf: title "Statement of Hours Worked"; Employer: Ramos Family Bakery; Worker: Jorge Ramos; Period: 04/01/2027 - 04/30/2027; Hours worked: 20.00; Pay: Unpaid ($0.00); Signed: Ana Ramos, Owner; Date: 05/02/2027. (May: 26.00, date 06/02/2027.)
- pantry_letter.pdf: title "Volunteer Service Letter"; Organization: Eastside Community Food Pantry; Organization type: 501(c)(3) nonprofit, non-partisan; Volunteer: Jorge Ramos; April 2027 hours: 10.00; May 2027 hours: 24.00 [handwritten, partially illegible]; Date: 06/05/2027.
- harbor_cafe_paystub.pdf: title "Harbor Cafe Pay Stub"; Employee: Jorge Ramos; Pay period: 05/24/2027 - 06/06/2027; Hours: 20.00; Rate: $15.50; Gross pay: $310.00; Pay date: 06/07/2027.

### Keywords (offline classifier; case-insensitive; highest score wins; need ≥ 2 hits)
rfi_notice: "request for information", "masshealth", "respond by" · gig_earnings: "earnings summary", "active hours", "driver" · employer_statement: "statement of hours", "hours worked", "employer" · volunteer_letter: "volunteer", "organization", "service letter" · paystub: "pay stub", "pay period", "gross pay" · school_letter: "enrollment", "half-time", "registrar".

### Verification (verify.py)
1. Grounding (pages with a text layer): build candidate strings for the value — numbers: "24", "24.0", "24.00"; money: "$560.00", "560.00", "560"; dates: "2027-05-01", "05/01/2027", "5/1/2027", "May 1, 2027"; strings: case-insensitive. Search the whitespace-normalized page text. Found → verification "grounded", evidence = the containing line. Booleans and enum values (e.g. nonPartisan, orgType) are grounded when their source line (the evidence from extraction) appears in the page text. Not found → "ungrounded", confidence "low", flag UNGROUNDED_VALUE. Pages without text (images) → "not_checked" (keep extractor confidence).
2. Date sanity: dates outside 2025-01-01..2028-12-31 or periodStart > periodEnd → confidence low + DATE_OUT_OF_RANGE.
3. Arithmetic: if hours, rate, and gross exist and |hours × rate − gross| > 2% of gross → ARITHMETIC_MISMATCH and gross confidence low.
4. Final confidence = low if extractor said low, value is null, or any rule above lowered it; else high.

### Gaps (gaps.py)
- For every month with excluded records: one unconfirmed_record gap per excluded record (message names the issuer and field).
- For every rule in dependsOnUnresolved of the best month: one unresolved_rule gap with that rule's plain-language text.
- For every short month: an hours gap "<Month YYYY> is <N> hours short of 80." with [employer_statement, volunteer_letter, paystub].
- Order: best-month gaps first (unconfirmed_record, then unresolved_rule in dependsOnUnresolved order); then hours gaps for short months that have any records, chronologically; then short months with no records, chronologically. (Scenario result: May items, then Apr, Jun, Feb, Mar.)

### Valid input assumptions (property-test generators; no extra defensive code)
Unique record ids; periodStart ≤ periodEnd; all numbers ≥ 0; expenses ≤ gross; dates within 2026-10-01..2027-12-31. Records with null period dates are skipped.

### Ledger decisions
1. Countability: a record counts only if EVERY field present on it is high-confidence or confirmed; otherwise its id goes in excludedRecordIds of each month its period overlaps.
2. Split: integer hundredths of an hour and integer cents; share_m = round(total × cumDays_m / totalDays) − previous cumulative; shares non-negative, sum exactly to total.
3. Income: gig net per record = max(0, gross − expenses); paystub/employer expenses ignored; volunteer and school records contribute no income. Income path met if employeeGross + gigNet ≥ threshold; conditional on self_employment_income_basis if not met by net but employeeGross + gigGross ≥ threshold.
4. Job training: tracked in trainingHours; if work + volunteer < threshold ≤ work + volunteer + training → conditional on job_training_approved.
5. Split method: evaluate each month under proportional and end-date allocation; if outcome (status + dependencies) differs, add pay_period_split_method. Overall: meets only if meets under both; conditional if either is meets or conditional; else short. Order: self_employment_income_basis, job_training_approved, pay_period_split_method.
6. pathsMet from the proportional allocation, only when overall status is meets; else [].
7. Shortfalls from proportional: hoursShortfall = max(0, threshold − (work + volunteer)), 2 dp; incomeShortfallCents = max(0, threshold − gross).
8. School half-time applies to every month the enrollment period overlaps; not affected by split method.
9. volunteer_proof and school_proof being unresolved do NOT make months conditional.
10. countedRecordIds and excludedRecordIds sorted by id; months chronological.
11. Hours arithmetic in integer hundredths; output floats with 2 decimals.
12. Best month: meets > conditional > short; then fewer flagged counted records; then most recent; then largest hours margin.
