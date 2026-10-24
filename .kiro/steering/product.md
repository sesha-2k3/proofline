---
inclusion: always
---
# Product: Proofline

Proofline helps Massachusetts benefits navigators (staff at community health centers, nonprofits, legal aid) keep eligible MassHealth members covered under the federal Medicaid work and education requirements that begin January 1, 2027.

## The user and the moment
- Primary user: a trained navigator working with a client who received a MassHealth renewal or Request for Information (RFI) because MassHealth could not verify them automatically ("blue envelope" cases).
- The client has messy, multi-source evidence: gig earnings, part-time or cash jobs, unpaid work, volunteer hours, school enrollment.
- The client usually has about 30 days to respond (provisional; see rules file).

## Core flow (MVP)
1. Navigator uploads the notice and the client's documents, and answers a short exemption questionnaire.
2. The app classifies and extracts each document into structured evidence records.
3. Code validates the records; low-confidence fields are flagged.
4. The navigator confirms or corrects flagged fields.
5. The ledger engine evaluates each month in the renewal window and picks the strongest month.
6. The app shows a gap report and generates a PDF packet, plus a submission record.

## Key Massachusetts rule
MassHealth requires members to meet the requirement for ONE month between their last renewal and their next renewal; new applicants must meet it in the month before they apply. The product's job is to find and prove the strongest single month, not every month.

## Never do
- Never decide eligibility. Say what the evidence appears to show; MassHealth decides.
- Never give legal advice. Suggest questions for the navigator, not instructions to the client.
- Never store documents or personal data. Process in memory for the session only.
- Never use real personal data in code, fixtures, tests, or demos. Synthetic data only.
- Never use third-party trademarks in sample documents (use invented names like "QuickDash").
- Never take political positions in UI copy. Neutral, plain language.

## Demo persona
Jorge Ramos (synthetic): gig delivery driver for "QuickDash", helps unpaid at his family's bakery, volunteers at "Eastside Community Food Pantry" (a 501(c)(3) nonprofit). He received an RFI and needs to prove one qualifying month.
