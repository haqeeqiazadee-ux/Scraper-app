# QA Execution Prompt — Paste This to Start a Session

> Copy everything below the line and paste it as your prompt to Claude Code.

---

## PROMPT START

You are executing the QA strategy for the AI Scraping Platform. Your job is to work through `docs/qa_strategy.md` **one use case at a time**, fix any failures, and keep a detailed log.

### MANDATORY STARTUP RITUAL (Do this FIRST, every session)

1. Read these files to refresh your memory:
   - `CLAUDE.md`
   - `docs/qa_strategy.md`
   - `docs/qa_execution_log.md` (create if missing)
   - `system/todo.md`
   - `system/lessons.md`
   - `system/execution_trace.md`
2. Find the **last completed use case** in `docs/qa_execution_log.md`
3. Resume from the **next unchecked use case** in `docs/qa_strategy.md`

### EXECUTION RULES (Follow these strictly)

**Rule 1: One use case at a time.**
- Pick the next `[ ]` item from `docs/qa_strategy.md`
- Test it (make real API calls, check UI, run code)
- Record the result: PASS, FAIL, or SKIP

**Rule 2: Fix before moving on.**
- If a test FAILS, diagnose and fix the issue immediately
- Make the code change, verify it works, then mark the test as passed
- If you cannot fix it (external dependency, needs user input), mark as `[!] BLOCKED` with a note and move to the next test

**Rule 3: Log every action.**
- After each use case (pass or fail), append to `docs/qa_execution_log.md` using this format:

```
### UC-X.X.X — [Short description]
- **Status:** PASS / FAIL / FIXED / BLOCKED / SKIP
- **Tested:** [What you actually did]
- **Result:** [What happened]
- **Fix applied:** [If any — file:line changed and why]
- **Commit:** [commit hash if code was changed]
- **Timestamp:** [current date/time]
```

**Rule 4: Commit and push frequently.**
- After every fix, commit with a clear message
- After every 3-5 use cases (even if all pass), commit the updated log
- Push to `claude/check-repo-connection-rHL5M` after every push-worthy batch
- Never let more than 5 use cases go without a commit

**Rule 5: Update qa_strategy.md as you go.**
- Change `[ ]` to `[x]` for passed tests
- Change `[ ]` to `[!]` for failed/blocked tests (add note)
- Change `[ ]` to `[~]` for skipped tests (add reason)

**Rule 6: Update system files after every phase.**
- After completing each Phase (1, 2, 3...), update:
  - `system/todo.md` — mark phase done, add next phase
  - `system/execution_trace.md` — add phase summary
  - `system/development_log.md` — add engineering notes
  - `system/lessons.md` — add anything learned
- Commit these updates

**Rule 7: Refresh memory before each phase.**
- Before starting a new Phase, re-read:
  - `CLAUDE.md` (may have been updated)
  - `docs/qa_strategy.md` (to see current state)
  - `docs/qa_execution_log.md` (your own last entries)
  - `system/lessons.md` (avoid repeating mistakes)
- This prevents context drift in long sessions

**Rule 8: Respect the priority order.**
- Follow the priority order from Appendix B of qa_strategy.md:
  1. Phase 1 (Infrastructure) — blocks everything
  2. Phase 2 (Auth) — blocks UI testing
  3. Phase 3 (Task CRUD) — core functionality
  4. Phase 6 (HTTP Lane) — primary scraping
  5. Phase 11 (Results/Export) — user sees output
  6. Phase 7 (Browser Lane) — JS sites
  7. Phase 17 (E-commerce scenarios) — real value
  8. Then remaining phases in order

**Rule 9: Ask the user when stuck.**
- If you need environment variables, credentials, or access you don't have — ASK
- If a fix requires architectural changes beyond the scope — ASK
- If you're unsure whether to change behavior or just document it — ASK
- Do NOT guess passwords, API keys, or external service configurations

**Rule 10: Keep it small and incremental.**
- Do NOT try to test or fix multiple things at once
- One use case → one test → one fix → one log entry → move on
- If a fix touches multiple files, that's fine — but the TRIGGER is one use case

### SESSION OUTPUT FORMAT

At the end of each session (or when context is getting long), output a summary:

```
## Session Summary — [Date]

### Progress
- Started at: UC-X.X.X
- Ended at: UC-Y.Y.Y
- Tests run: N
- Passed: N
- Failed and fixed: N
- Blocked: N

### Key fixes
- [Brief description of each fix]

### Blockers for next session
- [What needs to happen before continuing]

### Next use case to start with
- UC-Z.Z.Z
```

### GETTING STARTED

Start now. Read the files listed in the startup ritual, find where you left off (or start from UC-1.1.1 if this is the first run), and begin testing.

## PROMPT END
