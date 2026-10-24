# Requirements: Proofline

## Introduction
Proofline lets a Massachusetts benefits navigator upload a client's MassHealth notice and evidence documents, processes and verifies them, and proves the strongest single month that meets the MassHealth work and education requirements, producing a PDF packet and a submission record. Rules come only from rules/masshealth.yaml. The LLM classifies and extracts; code verifies and decides what the evidence shows. Synthetic data only. Exact values and decisions are in BUILD_PLAN.md.

## R1 Rules
1. WHEN the backend starts THE SYSTEM SHALL load and validate rules/masshealth.yaml and refuse to start if any rule lacks a valid source/status, naming the rule id.
2. THE SYSTEM SHALL expose thresholds only through rule accessors.

## R2 Case setup
1. THE SYSTEM SHALL accept client name, case type (renewal | new application), renewal window or application month, and RFI received date.
2. WHEN the case is a new application THE SYSTEM SHALL evaluate only the month before the application month.
3. WHEN an RFI date is given THE SYSTEM SHALL show the response deadline labeled with the rule's status.

## R3 Document processing pipeline
1. THE SYSTEM SHALL accept PDF, PNG, and JPG files up to the configured size and reject others with UNSUPPORTED_FILE.
2. THE SYSTEM SHALL run ingest, render, classify, extract, normalize, and verify stages and return a per-stage trace with status and duration.
3. THE SYSTEM SHALL classify each document as rfi_notice, paystub, employer_statement, gig_earnings, volunteer_letter, school_letter, or unknown, offline by keywords when possible and by LLM when configured.
4. THE SYSTEM SHALL extract fields with per-field confidence, page, and evidence text, using the template parser for known layouts and the LLM otherwise.
5. IF no extractor can process a document THEN THE SYSTEM SHALL return no records and a warning asking for manual entry.
6. THE SYSTEM SHALL NOT persist uploaded files or extracted data.

## R4 Verification
1. WHEN a page has a text layer THE SYSTEM SHALL check each extracted value against the page text and mark it grounded or ungrounded.
2. IF a value is ungrounded THEN THE SYSTEM SHALL set its confidence to low and flag UNGROUNDED_VALUE.
3. THE SYSTEM SHALL flag out-of-range dates and arithmetic mismatches (hours × rate vs gross beyond 2%).

## R5 Cross-document validation
1. THE SYSTEM SHALL flag duplicates, stale documents (provisional rule), ineligible volunteer organizations, name mismatches, and low-confidence unconfirmed fields.

## R6 Navigator review
1. THE SYSTEM SHALL show each document beside its fields with confidence, verification, evidence, and flags.
2. THE SYSTEM SHALL let the navigator edit and confirm any field.
3. WHEN a record has any unconfirmed low-confidence field THE SYSTEM SHALL exclude it from "meets".

## R7 Ledger
1. THE SYSTEM SHALL allocate hours and income to calendar months, splitting multi-month periods as specified.
2. THE SYSTEM SHALL set each month to meets, conditional (naming unresolved rules), or short (with shortfalls).
3. THE SYSTEM SHALL select the best month by the specified ordering and never count a record twice.

## R8 Exemptions
1. THE SYSTEM SHALL present a questionnaire from the rules file and show "Possible exemption — navigator to confirm" with sources, never "exempt".

## R9 Outputs
1. THE SYSTEM SHALL produce a gap report, a plain-language summary restating computed facts (en/es), a PDF packet with the disclaimer, and a submission record PDF.
