# Requirements: Proofline MVP

## Introduction
Proofline lets a Massachusetts benefits navigator turn a client's scattered evidence into proof of one qualifying month for the MassHealth work and education requirements, plus a PDF packet and submission record. All rules come from `rules/masshealth.yaml`. The LLM extracts and explains; code decides what the evidence shows. Synthetic data only.

## Requirement 1: Rules loading
**User story:** As a developer, I want all rules loaded from one validated file, so that no threshold is hardcoded.
1. WHEN the app starts THE SYSTEM SHALL load `rules/masshealth.yaml` and validate it with a zod schema.
2. IF any rule lacks `source` or `status` (null source is allowed only when status is `unresolved`) THEN THE SYSTEM SHALL fail validation with the rule id.
3. THE SYSTEM SHALL expose rules through typed accessors so ledger code never contains literal thresholds.

## Requirement 2: Case setup
**User story:** As a navigator, I want to start a case with the client's renewal window, so that the app evaluates the right months.
1. THE SYSTEM SHALL let the navigator enter: case type (renewal or new application), window start month, window end month, and RFI received date.
2. WHEN case type is new application THE SYSTEM SHALL evaluate only the month before the application month.
3. WHEN an RFI received date is entered THE SYSTEM SHALL show the response deadline using `rfi_response_days` and label it "provisional" if that rule is provisional.

## Requirement 3: Document upload and extraction
**User story:** As a navigator, I want to upload documents and get structured data, so that I don't retype everything.
1. THE SYSTEM SHALL accept PDF, PNG, and JPG uploads.
2. WHEN a document is uploaded THE SYSTEM SHALL classify it as one of: rfi_notice, paystub, employer_statement, gig_earnings, volunteer_letter, school_letter, unknown.
3. THE SYSTEM SHALL extract fields into the zod schema for that type, with a confidence of `high` or `low` per field and the page number each field came from.
4. IF the type is `unknown` THEN THE SYSTEM SHALL ask the navigator to label it and SHALL NOT extract automatically.
5. IF LLM credentials are missing or the call fails THEN THE SYSTEM SHALL use demo-mode fixtures for known synthetic documents and SHALL show a visible "Demo mode" badge.
6. THE SYSTEM SHALL NOT persist uploaded files or extracted data beyond the session.

## Requirement 4: Validation
**User story:** As a navigator, I want automatic checks, so that AI misreads are caught.
1. WHEN a paystub or employer statement has hours, rate, and gross pay THE SYSTEM SHALL flag it if |hours × rate − gross| exceeds 2% of gross.
2. THE SYSTEM SHALL flag duplicate documents (same type, same issuer, same period).
3. THE SYSTEM SHALL flag documents older than `paystub_recency_days` relative to the RFI date, labeled provisional.
4. THE SYSTEM SHALL flag volunteer records whose organization type is not in `allowed_org_types` or is not non-partisan.
5. THE SYSTEM SHALL flag names that do not match the client name entered at case setup.

## Requirement 5: Navigator review
**User story:** As a navigator, I want to confirm flagged fields, so that only trusted data is counted.
1. THE SYSTEM SHALL show each document beside its extracted fields, with low-confidence and flagged fields highlighted.
2. THE SYSTEM SHALL let the navigator edit any field and mark it confirmed.
3. WHEN a record has any unconfirmed low-confidence field THE SYSTEM SHALL exclude that record from `meets` determinations.

## Requirement 6: Ledger evaluation
**User story:** As a navigator, I want to see which month is strongest, so that I submit the best proof.
1. THE SYSTEM SHALL assign record hours and income to calendar months, splitting multi-month periods using `pay_period_split_method` and noting that the rule is unresolved.
2. FOR each month in the window THE SYSTEM SHALL compute: work hours (including unpaid), eligible volunteer hours, job training hours, half-time school status, and income in cents.
3. THE SYSTEM SHALL set month status to `meets` if combined hours ≥ `hours_threshold`, OR school half-time is confirmed, OR income ≥ `income_threshold_cents` under confirmed rules.
4. IF meeting the requirement depends on an unresolved rule (for example gross vs net self-employment income, or unapproved job training) THEN THE SYSTEM SHALL set status `conditional` and name the rule.
5. OTHERWISE THE SYSTEM SHALL set status `short` and report the hour and income shortfall.
6. THE SYSTEM SHALL select the best month: prefer `meets` over `conditional` over `short`; then fewer flagged records; then most recent; then largest margin.
7. THE SYSTEM SHALL never count the same record twice.

## Requirement 7: Exemption screening
**User story:** As a navigator, I want possible exemptions surfaced, so that I don't miss them.
1. THE SYSTEM SHALL present a yes/no questionnaire generated from the `exemptions` list.
2. WHEN any answer is yes THE SYSTEM SHALL show "Possible exemption — navigator to confirm" with the label and source, and SHALL NOT state that the person is exempt.

## Requirement 8: Gap report, packet, and submission record
**User story:** As a navigator, I want a ready-to-send packet and a record of submission, so that nothing gets lost.
1. THE SYSTEM SHALL show a gap report listing, for the best month and any short months, what is missing and which document types could close the gap.
2. THE SYSTEM SHALL generate a PDF packet: cover page (client, month, status, totals by activity, unresolved rules, deadline), a per-record table with source document and page, and a disclaimer that MassHealth makes all decisions.
3. THE SYSTEM SHALL let the navigator log a submission (date, channel, confirmation number) and SHALL generate a one-page timeline PDF.
4. THE SYSTEM SHALL generate a plain-language summary of the result using the LLM, constrained to restate code-computed facts only; in demo mode a template is used.
