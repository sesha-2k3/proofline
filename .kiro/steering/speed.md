---
inclusion: always
---
# Build speed rules

- BUILD_PLAN.md is the source of truth for files, names, numbers, and decisions. Follow it literally; it overrides the spec's design.md where they differ.
- Do not research. Do not read site-packages, node_modules, or library source/docs. Use standard, well-known APIs.
- Do not re-deliberate decisions in BUILD_PLAN.md or its Appendix. If something is truly unspecified, choose the simplest option, add one line to docs/DECISIONS.md, and continue.
- Write files first, then run the step's checks, fix failures directly, and report in a few lines.
- One BUILD_PLAN step (or the listed group) per session.
