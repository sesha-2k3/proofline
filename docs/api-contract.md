# Proofline API contract (v1)

Owner: backend. Source of truth for types: `lib/schemas/` (zod). This doc must match those schemas.
All endpoints are Next.js route handlers under `app/api/`. The server is stateless: the browser holds the case and sends what each endpoint needs. Nothing is stored server-side.

From the first backend push, every endpoint exists and returns realistic mock data from `lib/mocks/`, so the frontend can build against the real URLs immediately. Backend later swaps each mock for the real implementation without changing the contract.

## Conventions
- JSON bodies, `Content-Type: application/json`, except `/api/extract` (multipart) and PDF responses.
- Dates `YYYY-MM-DD`, months `YYYY-MM`, money in integer cents, hours as numbers (max 2 decimals).
- Errors: HTTP 4xx/5xx with body `{ "error": { "code": string, "message": string, "details"?: unknown } }`.
  Codes: `BAD_REQUEST`, `UNSUPPORTED_FILE`, `EXTRACTION_FAILED`, `RULES_INVALID`, `INTERNAL`.
- Every successful JSON response includes `"rulesVersion": string` (from `meta.last_reviewed` in the rules file).

## Shared types
```ts
type Lang = "en" | "es";
type Confidence = "high" | "low";
type RuleStatus = "confirmed" | "provisional" | "unresolved";

interface Field<T> {
  value: T | null;
  confidence: Confidence;
  page: number;          // 1-based page in the source document
  confirmed: boolean;    // set true by the navigator in the review screen
}

interface CaseInfo {
  clientName: string;
  caseType: "renewal" | "new_application";
  windowStart?: string;      // YYYY-MM, renewal only
  windowEnd?: string;        // YYYY-MM, renewal only
  applicationMonth?: string; // YYYY-MM, new_application only (evaluates the month before)
  rfiReceivedDate?: string;  // YYYY-MM-DD
  lang: Lang;
}

type DocType = "rfi_notice" | "paystub" | "employer_statement" | "gig_earnings"
             | "volunteer_letter" | "school_letter" | "unknown";

type ActivityType = "work" | "volunteer" | "job_training" | "school" | "income_only";

interface EvidenceRecord {
  id: string;
  docId: string;
  docType: Exclude<DocType, "rfi_notice" | "unknown">;
  activity: ActivityType;
  personName: Field<string>;
  issuer: Field<string>;
  orgType?: Field<"public" | "nonprofit" | "for_profit" | "political" | "unknown">;
  nonPartisan?: Field<boolean>;
  periodStart: Field<string>;
  periodEnd: Field<string>;
  hours?: Field<number>;
  hourlyRateCents?: Field<number>;
  grossCents?: Field<number>;
  expensesCents?: Field<number>;
  halfTimeEnrolled?: Field<boolean>;
  documentDate: Field<string>;
  flags: Flag[];
}

interface Flag {
  code: "ARITHMETIC_MISMATCH" | "DUPLICATE" | "STALE_DOCUMENT" | "VOLUNTEER_ORG_INELIGIBLE"
      | "NAME_MISMATCH" | "LOW_CONFIDENCE_UNCONFIRMED";
  message: string;               // plain language, in CaseInfo.lang
  field?: keyof EvidenceRecord;
  ruleId?: string;               // rule that produced the flag
  ruleStatus?: RuleStatus;       // e.g. STALE_DOCUMENT is provisional
}

interface NoticeInfo {           // extracted from an rfi_notice
  noticeDate: Field<string>;
  responseDeadline?: Field<string>;
  requestSummary: Field<string>;
}

type MonthStatus = "meets" | "conditional" | "short";

interface MonthResult {
  month: string;
  workHours: number; volunteerHours: number; trainingHours: number;
  schoolHalfTime: boolean;
  grossIncomeCents: number; netIncomeCents: number;
  status: MonthStatus;
  pathsMet: string[];             // rule ids, e.g. ["hours_threshold"]
  dependsOnUnresolved: string[];  // rule ids
  hoursShortfall: number;
  incomeShortfallCents: number;
  countedRecordIds: string[];
  excludedRecordIds: string[];
}

interface GapItem {
  month: string;
  kind: "hours" | "income" | "unresolved_rule" | "unconfirmed_record";
  message: string;                       // plain language, in CaseInfo.lang
  suggestedDocTypes: DocType[];
  ruleId?: string;
}

interface PossibleExemption { id: string; label: string; source: string; sourceUrl: string }

interface Deadline { date: string; ruleId: "rfi_response_days"; ruleStatus: RuleStatus }

interface SubmissionEntry {
  submittedAt: string;                   // YYYY-MM-DD
  channel: "online" | "mail" | "fax" | "in_person" | "phone";
  confirmationNumber?: string;
  documentsIncluded: string[];           // docIds or file names
  notes?: string;
}
```

## Endpoints

### GET /api/health
Response `200`: `{ "ok": true, "demoMode": boolean, "llmProvider": "bedrock" | "anthropic" | "none", "rulesVersion": string }`
Frontend shows the "Demo mode" badge when `demoMode` is true.

### GET /api/rules
Response `200`:
```json
{
  "rulesVersion": "2026-10-24",
  "thresholds": { "hours": 80, "incomeCents": 58000, "rfiResponseDays": 30 },
  "ruleStatuses": { "rfi_response_days": "provisional", "self_employment_income_basis": "unresolved" },
  "unresolvedRules": [ { "id": "self_employment_income_basis", "description": "Whether gig income counts before or after expenses." } ],
  "exemptionQuestions": [ { "id": "pregnant_postpartum", "label": "Pregnant or less than 12 months postpartum", "source": "S1", "sourceUrl": "https://www.mass.gov/..." } ],
  "sources": { "S1": "https://www.mass.gov/info-details/new-work-and-education-requirements-for-masshealth-members" }
}
```
Frontend builds the exemption questionnaire from `exemptionQuestions` (never hardcodes them).

### GET /api/samples
Response `200`: `{ "files": [ { "name": "quickdash_2027-05.pdf", "url": "/samples/quickdash_2027-05.pdf", "docType": "gig_earnings" } ], "caseInfo": CaseInfo }`
Powers the "Load sample case (Jorge)" button. Files live in `public/samples/`.

### POST /api/extract
Request: `multipart/form-data` with `file` (PDF/PNG/JPG, max 10 MB), `docId` (client-generated UUID), optional `docTypeHint` (DocType, used when the navigator labels an unknown document).
Response `200`:
```json
{
  "docId": "uuid",
  "docType": "volunteer_letter",
  "classificationConfidence": "high",
  "records": [ /* EvidenceRecord[] — one document can yield several (e.g. April and May) */ ],
  "notice": null,
  "demoMode": true,
  "warnings": [],
  "rulesVersion": "2026-10-24"
}
```
- `docType: "unknown"` → `records: []`; frontend asks the navigator to pick a type and re-calls with `docTypeHint`.
- `docType: "rfi_notice"` → `records: []` and `notice: NoticeInfo`.
- Flags are NOT set here (cross-document checks need all records); `flags: []`.

### POST /api/validate
Request: `{ "caseInfo": CaseInfo, "records": EvidenceRecord[] }`
Response `200`: `{ "records": EvidenceRecord[], "rulesVersion": string }` — same records with `flags` filled.
Frontend calls this after all uploads finish and again after any edit in the review screen.

### POST /api/evaluate
Request: `{ "caseInfo": CaseInfo, "records": EvidenceRecord[], "exemptionAnswers": { "id": string, "answer": boolean }[] }`
Response `200`:
```json
{
  "months": [ /* MonthResult[] in chronological order */ ],
  "bestMonth": "2027-05",
  "deadline": { "date": "2027-07-12", "ruleId": "rfi_response_days", "ruleStatus": "provisional" },
  "possibleExemptions": [ /* PossibleExemption[] */ ],
  "gaps": [ /* GapItem[] */ ],
  "summary": "Plain-language paragraph restating the computed results, in caseInfo.lang.",
  "demoMode": true,
  "rulesVersion": "2026-10-24"
}
```
`bestMonth` is null only if the window is empty. The server re-runs validation internally; records with unconfirmed low-confidence fields are excluded from `meets`.

### POST /api/packet
Request: `{ "caseInfo": CaseInfo, "records": EvidenceRecord[], "evaluation": <evaluate response> }`
Response `200`: `application/pdf` (filename `proofline-packet-<month>.pdf`).

### POST /api/timeline
Request: `{ "caseInfo": CaseInfo, "submissions": SubmissionEntry[] }`
Response `200`: `application/pdf` (filename `proofline-submission-record.pdf`).

## Frontend call sequence
1. `GET /api/health`, `GET /api/rules` on load.
2. Case setup form → hold `CaseInfo` in state. (Sample button: `GET /api/samples`, then fetch each file URL and treat it as an upload.)
3. For each file: `POST /api/extract` (show per-file progress; parallel is fine).
4. `POST /api/validate` with all records → review screen.
5. Navigator edits/confirms fields → update records locally → `POST /api/validate` again.
6. Exemption questionnaire answers + "Evaluate" → `POST /api/evaluate` → results, gaps, summary.
7. "Download packet" → `POST /api/packet`. Submission log form → `POST /api/timeline`.

## Change policy
- Backend changes `lib/schemas/` first, then updates this doc and `lib/mocks/`, then tells the frontend in the team chat.
- Additive changes only after the frontend starts integrating; no renames or removals without agreement.
