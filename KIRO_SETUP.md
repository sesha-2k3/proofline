# Proofline: Kiro setup and 5-hour build guide

## 1. Put the files in place (5 minutes)
1. Create an empty folder `proofline`, open it in Kiro IDE, and `git init`.
2. Copy in everything from this starter: `.kiro/` (steering + spec), `rules/masshealth.yaml`, `docs/KIRO_LOG.md`, and this file.
3. Make sure `.kiro/` is NOT in `.gitignore` (the hackathon disqualifies submissions that ignore it).
4. In Kiro's sidebar, check that the 5 steering files appear and the spec `proofline-mvp` shows requirements, design, and tasks.

## 2. Create the hooks (10 minutes)
Open the Agent Hooks panel, click +, and paste each description. Kiro writes the hook file in the right format for your IDE version.

**Hook 1 — Rules integrity check**
> When `rules/masshealth.yaml` is saved: check that every rule has a `source` and a `status` (confirmed, provisional, or unresolved; source may be null only if unresolved). Then run `npm test -- tests/ledger` and report any failures. If a rule changed from unresolved to confirmed, list which ledger outcomes could change. Add a one-line entry to docs/KIRO_LOG.md under Hooks if anything failed.

**Hook 2 — Ledger property tests on change**
> When any file in `lib/ledger/**` is saved: run `npm test -- tests/ledger` (unit + property tests P1–P8). If a property test fails, show the shrunk counterexample, explain the bug, fix it, add the counterexample as a named regression test, and add a line to docs/KIRO_LOG.md under Property-based testing.

**Hook 3 — No real data in fixtures**
> When any file in `synthetic/**`, `lib/extraction/fixtures/**`, or `tests/**` is saved: scan it for anything that looks like a real Social Security number (###-##-####), a real-looking full address, or a known real company or brand name. If found, replace it with clearly synthetic values and warn me.

**Hook 4 — Extraction eval**
> Manual trigger: run `npm run eval`, then summarize field accuracy per document type and the false-pass count (months marked "meets" that ground truth says are not). If false passes > 0, investigate and propose a fix.

**Hook 5 — Rules hardcoding guard**
> When any file in `lib/**` is saved: check for hardcoded eligibility numbers (80, 580, 58000, 60, 30) used as thresholds outside `lib/rules/`. If found, replace them with the rules accessors and tell me.

## 3. Optional MCP (5 minutes, skip if behind)
In Kiro's MCP settings (`.kiro/settings/mcp.json`), add a fetch server so Kiro can read the mass.gov source pages while you work:
```json
{
  "mcpServers": {
    "fetch": { "command": "uvx", "args": ["mcp-server-fetch"] }
  }
}
```
Requires `uv` installed. Then ask Kiro: "Fetch S1 from rules/masshealth.yaml and confirm the rules file still matches the page." Log the result in KIRO_LOG.md under MCP.

## 4. Build: prompts to give Kiro, in order
Open the spec `proofline-mvp` → tasks.md and click "Start task" on each, or paste these prompts in chat.

1. "Execute task 1 from the proofline-mvp spec."
2. "Execute tasks 2 and 3."
3. "Execute task 4, including all property tests P1–P8 and the synthetic scenario test. Then run the tests." ← most important step
4. "Execute task 6. Then run `npm run synth`."
5. "Execute task 7. Use demo mode if LLM env vars are not set."
6. "Execute task 8."
7. "Execute task 9. Keep the UI simple, clean, and accessible. The 'Load sample case (Jorge)' button must work in demo mode."
8. "Execute task 10."
9. "Execute tasks 11 and 12." (eval + README + deploy)

After each step: run the app, check it works, commit, and add a line to docs/KIRO_LOG.md.

## 5. Five-hour timeline
| Time | Work |
|---|---|
| 0:00–0:20 | Setup, hooks, optional MCP |
| 0:20–1:20 | Tasks 1–5 (scaffold, rules, schemas, ledger + property tests) |
| 1:20–2:10 | Tasks 6–8 (synthetic docs, extraction with demo mode, validation) |
| 2:10–3:10 | Task 9 (UI) |
| 3:10–3:35 | Task 10 (packet + submission record) |
| 3:35–3:55 | Deploy, README, testing instructions (task 12; skip task 11 if behind) |
| 3:55–4:25 | Record and upload the demo video (public on YouTube or Vimeo) |
| 4:25–4:50 | Text description, Kiro write-up, submission form |
| 4:50–5:00 | Buffer |

**Cut list if behind (in order):** task 11 eval script → submission timeline PDF → gap report detail → real LLM calls (demo mode only). Never cut the ledger property tests; they are your strongest Kiro story.

**If you have teammates:** one person on tasks 4–5, one on 6–8, one on 9 against mocked data, one on video, README, and write-up from hour 3.

## 6. Demo video (under 3 minutes)
1. 0:00–0:20 Problem: new Medicaid work requirements start Jan 1, 2027; a Boston University study found nearly 1 in 5 eligible adults in expansion states are at risk of noncompliance due to hours; Massachusetts members who can't be verified automatically get a short response window.
2. 0:20–2:05 Jorge's case: load sample case → review shows the pantry's May hours as low confidence → May is "conditional" (depends on gross vs net self-employment income, an unresolved rule) → navigator confirms 24 hours → May becomes "meets" → generate packet → log submission.
3. 2:05–2:45 Kiro: the spec, steering's rules-integrity file, a hook running property tests, one bug a property test caught.
4. 2:45–3:00 Impact: navigators in Massachusetts first; the rules file makes other states a configuration change.

## 7. Kiro write-up skeleton (fill from docs/KIRO_LOG.md)
- **Tools:** Kiro IDE (specs, hooks, agent chat). Note anything you did differently in the CLI, if used.
- **Spec-driven development:** EARS requirements mapped to MassHealth rules; design doc with eight correctness properties; tasks executed in order. Compare with vibe coding: what the spec prevented.
- **Steering:** rules-integrity.md kept thresholds out of code and kept the LLM from deciding eligibility; give one concrete example.
- **Hooks:** which of the five ran, what they caught (especially property-test and no-real-data hooks).
- **MCP:** fetch server used to check rules against mass.gov sources (if set up).
- **Property-based testing:** list P1–P8 and any counterexample found.
- **Powers:** list any you enabled, or state none were used.

## 8. Submission checklist
- [ ] Team members added (max 4)
- [ ] Track: Civic Services (or Healthcare & Biotech)
- [ ] Text description
- [ ] Video under 3 minutes, public, no copyrighted music or trademarks
- [ ] Public GitHub repo with source, assets, README, and `.kiro/` at the root
- [ ] Working demo link (free, no login, or credentials provided)
- [ ] Kiro write-up
