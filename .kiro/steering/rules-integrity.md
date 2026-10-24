---
inclusion: always
---
# Rules integrity (non-negotiable)

1. Every eligibility threshold comes from rules/masshealth.yaml via backend/app/rules/accessors.py. No literal 80, 580, 58000, 60, or 30 used as thresholds anywhere else.
2. Every rule has source and status (confirmed | provisional | unresolved). Null source only when unresolved.
3. If an outcome depends on an unresolved rule, the result is "conditional" and names the rule. Never guess.
4. The LLM only classifies, extracts, and rewrites code-computed facts in plain language. It never decides whether a month meets the requirement or whether someone is exempt.
5. Exemptions are shown only as "Possible exemption — navigator to confirm" with the source.
6. A record counts toward "meets" only if every field on it is high-confidence or navigator-confirmed.
7. Client-facing text: plain, neutral, about 6th-grade reading level. No legal advice.
