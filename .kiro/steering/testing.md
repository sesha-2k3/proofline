---
inclusion: fileMatch
fileMatchPattern: "tests/**/*.ts"
---
# Testing standards

- Every ledger property in the design doc gets a fast-check property test (minimum 200 runs).
- Generators must produce realistic records: hours 0–60 per record, income 0–150000 cents, dates within 2026-10-01..2027-12-31, all activity types, confidence high/low, confirmed true/false.
- Include explicit boundary unit tests: 79.99 hours vs 80 hours; $579.99 vs $580.00; a pay period spanning a month boundary.
- Fixtures must be synthetic. No real names, SSNs, addresses, or employers.
- When a property test finds a bug, add the shrunk counterexample as a named regression unit test and note it in docs/KIRO_LOG.md.
