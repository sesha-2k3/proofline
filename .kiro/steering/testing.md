---
inclusion: fileMatch
fileMatchPattern: "backend/tests/**"
---
# Testing standards
- pytest + hypothesis. Property tests use @settings(max_examples=200, deadline=None).
- Generators follow the "valid input assumptions" in the BUILD_PLAN Appendix.
- When hypothesis finds a counterexample, add it as a named regression test and note it in docs/KIRO_LOG.md.
- Fixtures are synthetic only.
