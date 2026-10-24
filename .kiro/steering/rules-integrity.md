---
inclusion: always
---
# Rules integrity (non-negotiable)

1. Every eligibility rule used in code must come from `rules/masshealth.yaml`. No magic numbers for thresholds (80 hours, $580, 60 days, 30 days) anywhere else.
2. Every rule entry must have `source` and `status`. Allowed statuses: `confirmed`, `provisional`, `unresolved`.
3. If a rule needed for a decision is `unresolved`, the ledger must NOT guess. It returns a `conditional` result that names the unresolved rule and shows the outcome under each plausible interpretation.
4. The LLM only extracts fields and writes plain-language explanations of results computed by code. It never decides whether a month meets the requirement or whether someone is exempt.
5. Exemptions are shown as "possible exemption — navigator to confirm," with the source citation. Never "you are exempt."
6. A month can be marked `meets` only if every record counted toward it is either high-confidence or confirmed by the navigator.
7. Output language must be neutral and plain (about a 6th-grade reading level for client-facing text). No legal advice, no political language.
8. When unsure whether something is allowed by the rules file, surface it to the navigator as a question.
