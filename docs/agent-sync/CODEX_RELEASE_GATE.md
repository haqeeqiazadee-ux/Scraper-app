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
- [x] Commit completed: `fdca008`.

## Phase 1 Gate

- [x] Existing code inspected before implementation.
- [x] Reused prior `saas-repair` catalog source instead of recoding.
- [x] Red test observed before implementation.
- [x] Catalog unit tests passed.
- [x] Frontend build passed.
- [x] Backend OpenAPI/API smoke passed.
- [x] Secret scan passed.
- [x] Commit completed: `e835a76`.

## Phase 2 Gate

- [x] Existing contracts/router/secrets/storage inspected before implementation.
- [x] Runtime tests written before implementation.
- [x] Red missing-module baseline observed.
- [x] Provider fallback semantic red baseline observed.
- [x] Missing-key skip behavior implemented without executing skipped workflows.
- [x] First available provider does not get blocked by missing fallback-provider keys.
- [x] Runtime unit tests passed.
- [x] Catalog+runtime regression passed.
- [x] Claude reviewer lane attempted but degraded with stale output; not counted as validation.
- [x] Secret scan passed.
- [x] Commit completed by the Phase 2 gate commit.
