# Design: Proofline MVP

## Overview
A single Next.js (TypeScript) app. The browser holds case state. Two API routes call the LLM and build PDFs. The ledger engine is pure TypeScript in `lib/ledger/` and is the most heavily tested part.

```
[Case setup] -> [Upload] -> /api/extract (classify + extract, or demo fixture)
     -> lib/validation (flags) -> [Review: navigator confirms]
     -> lib/ledger (months, statuses, best month) -> [Results + gap report + exemptions]
     -> /api/packet (PDF packet, submission timeline)
```

## Data models (zod schemas in lib/schemas)
```ts
type ActivityType = "work" | "volunteer" | "job_training" | "school" | "income_only";
type Confidence = "high" | "low";

interface Field<T> { value: T; confidence: Confidence; page: number; confirmed: boolean }

interface EvidenceRecord {
  id: string;                 // stable hash of docId + period + activity
  docId: string;
  docType: "paystub" | "employer_statement" | "gig_earnings" | "volunteer_letter" | "school_letter";
  activity: ActivityType;
  personName: Field<string>;
  issuer: Field<string>;      // employer / platform / organization
  orgType?: Field<"public" | "nonprofit" | "for_profit" | "political" | "unknown">;
  nonPartisan?: Field<boolean>;
  periodStart: Field<string>; // YYYY-MM-DD
  periodEnd: Field<string>;
  hours?: Field<number>;
  grossCents?: Field<number>;
  expensesCents?: Field<number>; // self-employment
  halfTimeEnrolled?: Field<boolean>;
  documentDate: Field<string>;
  flags: string[];            // from validation
}

type MonthStatus = "meets" | "conditional" | "short";

interface MonthResult {
  month: string;              // YYYY-MM
  workHours: number; volunteerHours: number; trainingHours: number;
  schoolHalfTime: boolean;
  grossIncomeCents: number; netIncomeCents: number;
  status: MonthStatus;
  pathsMet: string[];         // e.g. ["hours_threshold"]
  dependsOnUnresolved: string[]; // rule ids
  hoursShortfall: number; incomeShortfallCents: number;
  countedRecordIds: string[]; excludedRecordIds: string[];
}
```

## Ledger algorithm (lib/ledger)
1. **Eligibility filter:** a record is countable only if every field it contributes is `confidence: high` or `confirmed: true`. Others go to `excludedRecordIds`.
2. **Dedupe:** collapse records with identical `id`.
3. **Bucketing:** for each record, compute days in the period per calendar month. Allocate hours and cents proportionally by days (`pay_period_split_method` display default). If any record spans two months, add `pay_period_split_method` to `dependsOnUnresolved` for each affected month ONLY IF the alternative method (`by_period_end_date`) would change that month's status.
4. **Volunteer filter:** volunteer hours count only if `orgType ∈ allowed_org_types` and `nonPartisan` is true.
5. **Job training:** hours are computed but counted only as `conditional` (rule `job_training_approved` is unresolved).
6. **Status per month:**
   - `meets` if any confirmed path holds: (work + volunteer) ≥ 80; or school half-time; or employee gross + self-employment income under BOTH gross and net ≥ $580.
   - else `conditional` if a path holds only under an unresolved interpretation (self-employment gross-only, job training hours needed, or split method).
   - else `short`, with shortfalls computed against 80 hours and $580.
7. **Best month:** sort by status rank (meets > conditional > short), then fewer flagged counted records, then most recent month, then largest margin.
All thresholds come from the rules accessors.

## Correctness properties (fast-check)
- **P1 Order independence:** permuting the input records never changes any MonthResult.
- **P2 Monotonicity:** adding a countable record never lowers any month's status rank or totals.
- **P3 Unconfirmed exclusion:** a record with an unconfirmed low-confidence contributing field never appears in `countedRecordIds`.
- **P4 Split conservation:** for any record, the sum of hours (and cents) allocated across months equals the record's total (within 0.01).
- **P5 No double counting:** duplicating any record in the input leaves all results unchanged.
- **P6 Threshold boundary:** a month with exactly 80 combined countable hours is `meets`; 79.99 with no other path is not.
- **P7 Unresolved never meets:** if a month's only satisfied path depends on an unresolved rule, its status is `conditional`, never `meets`.
- **P8 Best-month dominance:** the selected best month has a status rank ≥ every other month's.

## Extraction contract (lib/extraction)
- One LLM call per page image or PDF: first classify, then extract with the per-type schema.
- The prompt requires JSON only, every field wrapped as `{value, confidence, page}`, `confidence: "low"` when text is unclear, handwritten, or missing, and `null` values rather than guesses.
- Response is parsed with zod; parse failure → one retry → fall back to `unknown` type.
- Demo mode: fixtures in `lib/extraction/fixtures/*.json` keyed by the synthetic file name. The fixtures intentionally include one low-confidence field (the volunteer letter's hours) so the review step can be demonstrated.

## Synthetic scenario (synthetic/)
Client: Jorge Ramos. Case: renewal, window 2027-02 to 2027-06, RFI received 2027-06-12 (deadline 2027-07-12, provisional).
| File | Type | Content |
|---|---|---|
| rfi_notice.pdf | rfi_notice | Marked "SAMPLE — NOT A REAL MASSHEALTH NOTICE"; asks for proof of work/education for one month |
| quickdash_2027-04.pdf | gig_earnings | 2027-04-01..30, 14.0 active hours, gross $320.00, expenses $110.00 |
| quickdash_2027-05.pdf | gig_earnings | 2027-05-01..31, 31.5 hours, gross $560.00, expenses $210.00 |
| bakery_statement_2027-05.pdf | employer_statement | Ramos Family Bakery, unpaid work, 2027-05-01..31, 26.0 hours, signed by owner |
| bakery_statement_2027-04.pdf | employer_statement | Unpaid, 2027-04-01..30, 20.0 hours |
| pantry_letter.pdf | volunteer_letter | Eastside Community Food Pantry, nonprofit, non-partisan; April 10.0 hours, May 24.0 hours (May hours slightly smudged → low confidence) |
| harbor_cafe_paystub.pdf | paystub | Harbor Cafe, period 2027-05-24..2027-06-06, 20.0 hours × $15.50 = $310.00 |

Expected results (proportional split; cafe stub puts 11.43 h and $177.14 in May, 8.57 h and $132.86 in June):
- **Before** the navigator confirms the pantry's May hours: May hours = 31.5 + 26 + 11.43 = 68.93 (short on hours). Income: gross $737.14 (meets) but net $527.14 (does not) → May is `conditional` on `self_employment_income_basis`.
- **After** confirming 24.0 pantry hours: May hours = 92.93 → `meets` via hours_threshold. Best month = May 2027.
- April: 44.0 hours, gross $320.00 → `short` (36.0 hours, $260.00 short). June: 8.57 hours → `short`. February and March: no records → `short`.
- The split method does not change May's status (it still meets with all cafe hours moved to June), so May does not depend on `pay_period_split_method`.

## Packet (lib/packet, pdf-lib)
- Cover: client name, case type, selected month and status, totals per activity, paths met, unresolved rules affecting the result, RFI deadline (labeled provisional), disclaimer: "This summary organizes evidence. MassHealth makes all eligibility decisions."
- Evidence table: record, document, issuer, period, hours, amount, page, confirmed by navigator.
- Possible exemptions section (if any) with sources.
- Submission timeline PDF: list of logged submissions (date, channel, confirmation number, documents included).

## Error handling
- Rules file invalid → app shows a blocking error naming the rule id.
- LLM failure → demo fixture if known file, else mark document `unknown` for manual labeling.
- Never log document contents on the server.

## Testing strategy
- Unit tests for rules loading, validation checks, bucketing edge cases.
- Property tests P1–P8 in `tests/ledger.property.test.ts`.
- `npm run eval`: run extraction on synthetic files, compare to ground truth, print field accuracy and false-pass count (months marked `meets` that ground truth says are not).
