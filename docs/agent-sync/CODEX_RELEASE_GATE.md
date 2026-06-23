# Codex Release Gate

Codex owns final verification before every commit.

## Per-Phase Checklist

- [ ] Git branch is not `main`.
- [ ] Scope is only `haqeeqiazadee-ux/Scraper-app`.
- [ ] `IMPLEMENTATION_LEDGER.md` includes reuse-gate proof for the phase.
- [ ] No Apify execution redirects were added.
- [ ] Missing API keys are documented as skipped workflow requirements, not hard failures.
- [ ] Tests/builds required by the phase were run or an explicit blocker is recorded.
- [ ] Secret scan did not find committed secret values.
- [ ] Git diff reviewed before commit.

## Phase 0 Gate

- [x] Branch created: `codex/own-stack-actors`.
- [x] Auto-mode roadmap created.
- [x] Claude handoff created.
- [x] Missing-key ledger created.
- [x] Claude reuse audit recorded and Codex-corrected where verification disagreed.
- [x] Secret scan completed.
- [ ] Commit completed.
