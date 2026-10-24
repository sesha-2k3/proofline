# Start here: building Proofline (React + FastAPI) in Kiro

## 1. Set up the repo (10 minutes, by hand)
1. Create an empty folder `proofline`, copy this starter's contents into it (use the terminal: `unzip -o proofline-fastapi-react-starter.zip -d <parent-folder>`; avoid Finder's "Replace").
2. Run the commands in BUILD_PLAN.md → PART 0 from the `proofline` folder.
3. `git add . && git commit -m "Starter + scaffolds"`, create a public GitHub repo, `git remote add origin <url>`, `git push -u origin master`.
4. Open `proofline` in Kiro IDE. Cmd+Shift+P → "Developer: Reload Window". In the Kiro panel, check: Steering shows 8 workspace files; Specs shows `proofline`.

## 2. Kiro settings
- Chat model: Opus at **medium** effort (or Sonnet for routine steps). Avoid "high" effort; it causes long deliberation.
- Autopilot: ON. Start a **new chat session (+) for every step.**

## 3. Create the hooks (one chat message)
Paste in a new session:
```
Create these agent hooks in .kiro/hooks using the correct format for this Kiro version (ask-agent actions, triggered after Kiro edits matching files). List them when done.
1. "Ledger property tests" — files under backend/app/ledger/ — Run `cd backend && uv run pytest -q tests/test_ledger_properties.py tests/test_ledger_scenario.py tests/test_ledger_boundary.py`. If a hypothesis test fails, show the counterexample, fix the bug, add a named regression test, and log it in docs/KIRO_LOG.md under Property-based testing.
2. "Rules integrity" — rules/masshealth.yaml — Check every rule has source and status (null source only if unresolved), run `make test`, and list ledger outcomes that could change.
3. "Contract sync" — files under backend/app/schemas/ — Run `make openapi`, then add a line under "Changes" in docs/FRONTEND_REQUESTS.md describing the schema change.
4. "Pipeline regression" — files under backend/app/pipeline/ — Run `cd backend && uv run pytest -q tests/test_pipeline*.py` and report failures.
5. "No real data" — files under backend/synthetic/, backend/samples/, backend/tests/, backend/app/mocks/ — Scan for real-looking SSNs (###-##-####), real addresses, or real brand names; replace with synthetic values and warn me.
6. "Threshold guard" — files under backend/app/ except backend/app/rules/ — Check for hardcoded thresholds (80, 580, 58000, 60, 30) used as eligibility values; replace with rules accessors.
```
Tip: keep hooks 1, 2, 6 disabled while generating large steps if they slow things down; re-enable and run each once at the end for the write-up.

## 4. Backend prompts (one session each, in order)
Use this template, replacing the step:
```
#file:BUILD_PLAN.md Execute step B1 exactly as written. Write the files immediately; do not research or re-deliberate decisions in the plan or Appendix. Run the step's checks, fix failures, check off the matching task in .kiro/specs/proofline/tasks.md, and report in a few lines.
```
Order: B1 → B2 → B3 → B4 (**push to master; tell the frontend developer**) → B5 → B6 → B7 → B8 → B9 → B10 → B11 → B12 → B13.
B2+B3 and B11+B12 can be combined in one session if things are moving fast.

After each step:
```bash
make test
git add . && git commit -m "B<n>: <summary>" && git push
```

## 5. Frontend prompts (teammate, after B4 is on master)
```bash
git clone <repo-url> proofline && cd proofline
cd frontend && npm install && npm run gen:api && cd ..
git checkout -b frontend
```
Open in Kiro, reload the window, then one session per group:
```
#file:BUILD_PLAN.md Execute steps F1 and F2 exactly as written. Edit only frontend/. Use only the generated types in frontend/src/api/schema.d.ts. Write the files immediately; do not research. Run npx tsc --noEmit and npm run build, fix errors, check off the task, and report briefly.
```
Then F3+F4, F5+F6, F7+F8 with the same wording. To run locally: terminal 1 `make dev-backend`, terminal 2 `make dev-frontend`, open http://localhost:5173.

## 6. Git workflow
- Branches: `backend` and `frontend`; merge into `master` after each step (master must pass `make test` and `npm run build`).
- Backend schema changes: backend runs `make openapi` (hook 3 does it), commits `shared/openapi.json`; frontend runs `npm run gen:api` after pulling.
- Contract requests from frontend go in docs/FRONTEND_REQUESTS.md under "Requests".

## 7. If Kiro stalls
Stop it and send: `Stop analyzing. Use the simplest option consistent with BUILD_PLAN.md and its Appendix, note any assumption in one line in docs/DECISIONS.md, and write the files now.`

## 8. Submission checklist
- [ ] Public repo with `.kiro/` at the root (not gitignored), README with run steps and live URL
- [ ] Live demo (Docker deploy, demo mode, no keys needed)
- [ ] Video under 3 minutes: Jorge walkthrough (show the pipeline trace and grounded evidence), then Kiro spec/steering/hooks/property tests
- [ ] Text description and Kiro write-up (from docs/KIRO_LOG.md and docs/eval_report.md)
- [ ] Track: Civic Services (or Healthcare & Biotech)
