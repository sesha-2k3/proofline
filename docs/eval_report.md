# Proofline pipeline evaluation

Samples: 7 synthetic PDFs in backend/samples, compared with backend/synthetic/ground_truth.json.

| Metric | Result |
|---|---|
| Classification accuracy | 7/7 (100.0%) |
| Field accuracy (value and confidence) | 57/57 (100.0%) |
| Grounding rate (non-null extracted values) | 57/57 (100.0%) |
| False-pass count (extracted 'meets' where ground truth is not) | 0 |

## Ledger by month, as extracted (false passes: 0)

| Month | Extracted | Ground truth |
|---|---|---|
| 2027-02 | short | short |
| 2027-03 | short | short |
| 2027-04 | short | short |
| 2027-05 | conditional | conditional |
| 2027-06 | short | short |

## Ledger by month, after navigator confirmation (false passes: 0)

| Month | Extracted | Ground truth |
|---|---|---|
| 2027-02 | short | short |
| 2027-03 | short | short |
| 2027-04 | short | short |
| 2027-05 | meets | meets |
| 2027-06 | short | short |

## Mismatches

None.
