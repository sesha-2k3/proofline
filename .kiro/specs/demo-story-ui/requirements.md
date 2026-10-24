# Requirements Document

## Introduction

This feature reframes the Proofline UI and the Jorge sample demo around the human problem, so that a 1–2 minute video tells one story: a person with a letter, a deadline, and a pile of paperwork (Problem); the navigator loads the evidence and Proofline sorts it (Help); Proofline flags the one handwritten entry for a person to confirm (Trust); May 2027 is covered by proof and the packet is ready (Relief); and "Proofline helps with the paperwork. MassHealth makes the decision." (Close).

The feature changes copy, layout, and visual design in the frontend, adds a backend endpoint for the response deadline, and optionally adds page images with line positions to the document result for source highlighting. It does not change the Jorge scenario numbers, dates, records, synthetic samples, or ground truth. The existing spec (.kiro/specs/proofline) and BUILD_PLAN.md remain the source of truth for the existing build. Deviations and unspecified choices are recorded as one line each in docs/DECISIONS.md.

## Glossary

- **Proofline_UI**: The React single-page app in frontend/src.
- **Proofline_API**: The FastAPI backend in backend/app, reached by the Proofline_UI only through frontend/src/api/client.ts.
- **Navigator**: The trained helper who uses Proofline_UI on behalf of a client.
- **Client**: The person whose MassHealth evidence is being organized (in the demo, the synthetic person Jorge Ramos).
- **Sample_Case**: The Jorge Ramos scenario loaded by "Load sample case", made of JORGE_CASE and the 7 files in JORGE_SAMPLES (backend/app/mocks/jorge.py).
- **Case_Step**: One of the five steps of the case page: Case, Documents, Review, Results, Packet.
- **Rules_State**: The GET /api/rules response held in case state (`state.rules`), including `thresholds.hours`, `thresholds.incomeCents`, `thresholds.rfiResponseDays`, `ruleStatuses`, and `unresolvedRules`.
- **Evaluation**: The POST /api/evaluate response held in case state, including `months`, `bestMonth`, and `deadline`.
- **Response_Deadline**: The date by which the Client should respond to the Request for Information, computed by backend/app/reporting/deadline.py and labeled with the status of rule `rfi_response_days`.
- **Deadline_Chip**: A compact element in the case page header that shows the Response_Deadline.
- **Month_Strip**: A horizontal row of the months in the case window (Feb–Jun 2027 for the Sample_Case), one cell per MonthResult.
- **Progress_Bar**: A bar inside a month card showing counted hours (work hours plus volunteer hours) against `Rules_State.thresholds.hours`.
- **Stage_Strip**: A row of six chips (Ingest, Render, Classify, Extract, Normalize, Verify) per uploaded document showing each pipeline stage's status.
- **Story_Headline**: The sentence at the top of the Results step that restates the best month's computed totals.
- **Counted_Source**: A distinct issuer value among the records listed in a month's `countedRecordIds`.
- **Source_View**: A panel that shows a page image of an uploaded document with the line that contains an extracted value highlighted.
- **Threshold_Literal**: Any of the numbers 80, 580, 58000, 60, or 30 used as an eligibility threshold or rule value.
- **Reduced_Motion**: The state where the browser reports `prefers-reduced-motion: reduce`.

## Requirements

### Requirement 1: Landing page tells the problem

**User Story:** As a Navigator watching the demo, I want the landing page to start with the person's problem, so that I understand why Proofline exists before I see any feature.

#### Acceptance Criteria

1. THE Proofline_UI SHALL show the tagline "You live your life. We'll help sort the proof." as the landing page's top-level heading in English.
2. WHILE the UI language is Spanish, THE Proofline_UI SHALL show the Spanish translation of the tagline from frontend/src/i18n/es.ts as the landing page's top-level heading.
3. THE Proofline_UI SHALL show, below the tagline, one sentence stating that people can lose coverage over paperwork even when they qualify, with no numeric statistic.
4. THE Proofline_UI SHALL show one sentence stating that MassHealth work and education requirements begin January 1, 2027.
5. THE Proofline_UI SHALL show the "Load sample case" button and the "Start a case" button on the landing page.
6. THE Proofline_UI SHALL show the sentence "Proofline helps with the paperwork. MassHealth makes the decision." (and its Spanish translation in Spanish) on the landing page and on the Packet step.

### Requirement 2: Case header shows the person

**User Story:** As a Navigator, I want the case header to show the client as a person with the places he works and volunteers and his deadline, so that the case feels like a person and not a file.

#### Acceptance Criteria

1. WHILE a case is open, THE Proofline_UI SHALL show the client name from `caseInfo.clientName` in the case header on every Case_Step.
2. WHILE the Sample_Case is loaded, THE Proofline_UI SHALL show the four places QuickDash, Ramos Family Bakery, Eastside Community Food Pantry, and Harbor Cafe in the case header.
3. WHILE a case that is not the Sample_Case is open, THE Proofline_UI SHALL show the distinct issuer values of the case's records in the case header once records exist.
4. WHEN the Sample_Case is loaded, THE Proofline_UI SHALL show loading and placeholder text that describes Jorge's letter and documents in plain language (EN and ES).
5. THE Proofline_UI SHALL use the Sample_Case values for client name, case type, window, RFI date, records, and sample files exactly as defined in backend/app/mocks/jorge.py.

### Requirement 3: Deadline chip on every case step

**User Story:** As a Navigator, I want the response deadline visible on every step, so that I keep the client's deadline in mind while I work.

#### Acceptance Criteria

1. THE Proofline_API SHALL provide an endpoint that accepts a CaseInfo and returns the Response_Deadline computed by backend/app/reporting/deadline.py, or no deadline when `rfiReceivedDate` is empty.
2. FOR ALL CaseInfo values, THE Proofline_API SHALL return the same Response_Deadline from the deadline endpoint as in the `deadline` field of POST /api/evaluate for that CaseInfo.
3. WHEN the Navigator saves case setup with an RFI received date, THE Proofline_UI SHALL request the Response_Deadline from the Proofline_API and store the result in case state.
4. WHILE a Response_Deadline is in case state, THE Proofline_UI SHALL show the Deadline_Chip with the deadline date on every Case_Step.
5. WHILE the rule `rfi_response_days` has a status other than confirmed, THE Deadline_Chip SHALL show the rule status as text next to the date.
6. WHILE the reference date is on or before the Response_Deadline and the remaining days are at most `Rules_State.thresholds.rfiResponseDays`, THE Deadline_Chip SHALL show the number of days left, where the reference date is the case's `rfiReceivedDate` WHILE the Sample_Case is loaded and the local date otherwise.
7. WHILE the reference date is after the Response_Deadline, THE Deadline_Chip SHALL show text stating that the reply date has passed, with an icon and the date.
8. THE Proofline_UI SHALL obtain the Response_Deadline date only from the Proofline_API.

### Requirement 4: Results headline and month timeline

**User Story:** As a Navigator, I want the Results step to say plainly which month has enough proof and show progress per month, so that the client sees relief at a glance.

#### Acceptance Criteria

1. WHILE an Evaluation has a `bestMonth` with status meets, THE Proofline_UI SHALL show the Story_Headline "{month} has enough proof: {hours} hours from {n} sources", where hours is the best month's work hours plus volunteer hours and n is the number of Counted_Sources.
2. WHILE an Evaluation has a `bestMonth` with status conditional, THE Proofline_UI SHALL show a Story_Headline stating that the month may have enough proof and naming each rule in `dependsOnUnresolved`.
3. WHILE an Evaluation has no month with status meets or conditional, THE Proofline_UI SHALL show a Story_Headline stating that no month has enough proof yet and pointing to the gap list.
4. THE Proofline_UI SHALL compute every number in the Story_Headline from the Evaluation and the case records in state.
5. THE Proofline_UI SHALL show the Month_Strip with one cell per MonthResult in month order, each cell showing the month name, a status icon, and the status text.
6. THE Proofline_UI SHALL mark the best month in the Month_Strip with a text label in addition to color.
7. THE Proofline_UI SHALL show a Progress_Bar in each month card with fill equal to counted hours divided by `Rules_State.thresholds.hours`, capped at 100 percent.
8. THE Progress_Bar SHALL expose its value, maximum, and a text label to assistive technology.
9. THE Proofline_UI SHALL use the phrase "the evidence appears to show" (or its Spanish translation) in Results text that describes what a month shows, and SHALL state that MassHealth decides.

### Requirement 5: Calm Conditional to Meets transition

**User Story:** As a Navigator, I want a calm visual change when a month moves from Conditional to Meets after I confirm a field, so that the change is noticed without implying approval.

#### Acceptance Criteria

1. WHEN a new Evaluation changes a month's status from conditional to meets, THE Proofline_UI SHALL animate that month's Progress_Bar fill from the previous value to the new value and swap the status badge, completing within 800 ms.
2. WHILE Reduced_Motion is active, THE Proofline_UI SHALL show the new Progress_Bar value and status badge without animation.
3. WHEN a month's status changes, THE Proofline_UI SHALL announce the new status of that month in an aria-live polite region.
4. THE Proofline_UI SHALL label the meets status with wording that states the evidence appears to meet the requirement, without the words "approved", "eligible", or "covered" as a decision.

### Requirement 6: Live pipeline stage strip

**User Story:** As a Navigator, I want to see each document go through the six pipeline stages, so that I trust how Proofline read it.

#### Acceptance Criteria

1. THE Proofline_UI SHALL show a Stage_Strip with six chips in the order Ingest, Render, Classify, Extract, Normalize, Verify for each uploaded document.
2. WHILE a document upload request is in progress, THE Stage_Strip SHALL show every chip in a working state with an icon and the text "Working".
3. WHEN a DocumentResult arrives, THE Stage_Strip SHALL show each chip with the status from the matching `pipeline` entry (ok, warning, failed, skipped) as an icon and text.
4. IF a document upload fails with an error, THEN THE Stage_Strip SHALL show the failure as text with an icon and the error message.
5. THE Proofline_UI SHALL keep the per-stage duration, detail, extractor, and warnings available in an expandable detail view under the Stage_Strip.
6. WHEN any stage has status warning or failed or the result has warnings, THE Proofline_UI SHALL open the detail view by default.
7. WHILE Reduced_Motion is active, THE Stage_Strip SHALL show the working state without animation.

### Requirement 7: The handwritten entry is flagged for a person

**User Story:** As a Navigator, I want the handwritten pantry entry to stand out as needing my confirmation, so that the demo shows that a person checks uncertain values.

#### Acceptance Criteria

1. WHILE a record field is unconfirmed and low confidence or ungrounded, THE Proofline_UI SHALL show a "Needs confirmation" label with an icon next to the field on the Review step.
2. WHILE the Sample_Case is loaded and the Eastside Community Food Pantry May hours field (24.00) is unconfirmed, THE Proofline_UI SHALL show that field's evidence text on the Review step.
3. WHEN the Navigator confirms a field, THE Proofline_UI SHALL replace the "Needs confirmation" label with a "Confirmed by navigator" label with an icon.

### Requirement 8: Packet step is the finish line

**User Story:** As a Navigator, I want the Packet step to read as the finish line, so that the client knows what is ready and what happens next.

#### Acceptance Criteria

1. WHILE an Evaluation exists on the Packet step, THE Proofline_UI SHALL show the heading "{client first name}'s packet is ready to send" (and its Spanish translation).
2. THE Proofline_UI SHALL show the packet disclaimer and the sentence "Proofline helps with the paperwork. MassHealth makes the decision." on the Packet step.
3. THE Proofline_UI SHALL state on the Packet step that Proofline does not send the packet and the Navigator or Client sends the packet to MassHealth.

### Requirement 9: Visual polish

**User Story:** As a Navigator, I want a clean, consistent look, so that the tool feels trustworthy.

#### Acceptance Criteria

1. THE Proofline_UI SHALL use one self-hosted typeface bundled with the frontend build, with a system font fallback.
2. THE Proofline_UI SHALL show hours and money values with tabular numerals.
3. THE Proofline_UI SHALL show the case steps as a connected stepper where each completed step shows a check icon and the text label, and the current step is marked with `aria-current="step"`.
4. THE Proofline_UI SHALL use one icon library for all status icons, with each icon paired with a text label and hidden from assistive technology.
5. WHILE data for a section is loading, THE Proofline_UI SHALL show a skeleton placeholder for that section with an accessible "Loading" text.
6. THE Proofline_UI SHALL define colors, radius, and shadow values as theme tokens in frontend/src/index.css.
7. THE Proofline_UI SHALL keep text and icon contrast at WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text and icons) against their backgrounds.

### Requirement 10: Source highlight (optional)

**User Story:** As a Navigator, I want to click an extracted value and see the page with that line highlighted, so that I can check the value against the document.

#### Acceptance Criteria

1. WHERE source highlight is enabled, THE Proofline_API SHALL include in each DocumentResult a page image for each page and the text lines of each page with a bounding box in page-relative coordinates between 0 and 1.
2. WHERE source highlight is enabled, WHEN the Navigator activates an extracted value on the Review step, THE Proofline_UI SHALL open the Source_View for that field's page with the line whose text equals the field's evidence highlighted.
3. WHERE source highlight is enabled, IF no line on the page matches the field's evidence, THEN THE Source_View SHALL show the page image and the text "Could not find this line on the page."
4. WHERE source highlight is enabled, THE Source_View SHALL be operable by keyboard, close with the Escape key, and return focus to the activated value.
5. WHERE source highlight is enabled, THE Proofline_API SHALL keep page images and line boxes in memory for the request only.
6. WHERE source highlight is enabled, THE Proofline_API SHALL keep every existing DocumentResult field and value unchanged, so that the existing contract and ground-truth tests pass.

### Requirement 11: Product and rules constraints

**User Story:** As the product owner, I want the new story UI to keep Proofline's rules and product limits, so that the demo stays honest.

#### Acceptance Criteria

1. THE Proofline_UI SHALL read every eligibility threshold shown or used from Rules_State, with no Threshold_Literal in frontend/src.
2. THE Proofline_API SHALL read every eligibility threshold from rules/masshealth.yaml through backend/app/rules/accessors.py, with no new Threshold_Literal in backend/app.
3. THE Proofline_UI SHALL show each month status exactly as returned by the Evaluation.
4. WHILE a month has status conditional, THE Proofline_UI SHALL name each rule in that month's `dependsOnUnresolved`.
5. THE Proofline_UI SHALL show exemptions only as "Possible exemption — navigator to confirm" with the source link.
6. THE Proofline_UI SHALL keep all new client-facing copy in en.ts and es.ts in plain, neutral language at about a 6th-grade reading level, with no legal advice and no political language.
7. THE Proofline_UI SHALL keep case data only in React state, with no use of localStorage, sessionStorage, or cookies.
8. THE Proofline_UI SHALL call the Proofline_API only through frontend/src/api/client.ts using types generated in frontend/src/api/schema.d.ts.
9. WHEN a backend schema changes, THE developer workflow SHALL run `make openapi`, regenerate frontend/src/api/schema.d.ts with `npm run gen:api`, and add a line under "Changes" in docs/FRONTEND_REQUESTS.md.
10. THE Proofline_UI SHALL use only synthetic data and the fictional names QuickDash, Harbor Cafe, Ramos Family Bakery, and Eastside Community Food Pantry.

### Requirement 12: Accessibility and layout

**User Story:** As a Navigator using a phone or a keyboard, I want every new element to work for me, so that I can use Proofline in the field.

#### Acceptance Criteria

1. THE Proofline_UI SHALL show every status with an icon and text, in addition to color.
2. THE Proofline_UI SHALL lay out every Case_Step at a 375 px viewport width with no horizontal page scrolling.
3. THE Proofline_UI SHALL show a visible focus outline on every interactive element, including the stepper, Month_Strip cells that are interactive, and extracted values.
4. WHEN an upload starts, finishes, or fails, THE Proofline_UI SHALL announce the change in an aria-live polite region.
5. WHEN an evaluation starts, finishes, or fails, THE Proofline_UI SHALL announce the change in an aria-live polite region.
6. WHILE Reduced_Motion is active, THE Proofline_UI SHALL disable every transition and animation added by this feature.
