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

## Phase 3 Gate

- [x] Existing actor/task/run/result code inspected before implementation.
- [x] Actor-run API tests written before implementation.
- [x] Red HTTP 405 baseline observed.
- [x] Native actor-run create/list/detail endpoints added.
- [x] Non-native strategies blocked instead of redirected.
- [x] Missing required keys persisted as `skipped_missing_key`.
- [x] Successful native runner path persists result rows.
- [x] Tenant isolation and pagination covered by tests.
- [x] Actor-run API suite passed.
- [x] Phase 1-3 regression passed.
- [x] OpenAPI smoke passed.
- [x] Codex explorer subagent review completed.
- [x] Claude MCP review attempted but unavailable; not counted as validation.
- [x] Secret scan passed.
- [x] Commit completed by the Phase 3 gate commit.

## Phase 4 Gate

- [x] Existing family/provider code inspected before implementation.
- [x] Codex explorer subagent reviews completed for generic/commerce/marketplace and local maps.
- [x] Base-family tests written before implementation.
- [x] Red missing-module baseline observed.
- [x] Shared family registry and runners added.
- [x] Actor-run API rewired to shared family registry.
- [x] Local maps optional-key/browser-fallback behavior covered.
- [x] Amazon marketplace missing `KEEPA_API_KEY` skip behavior covered.
- [x] Family unit tests passed.
- [x] Actor-run API tests passed.
- [x] Phase 1-4 regression passed.
- [x] Secret scan passed.
- [x] Commit completed by the Phase 4 gate commit.

## Phase 5 Gate

- [x] Existing schemas/templates/workers/actor API inspected before implementation.
- [x] Codex explorer subagent reuse audits completed for jobs/real estate and leads/reviews/news/content.
- [x] Phase 5 tests written before implementation.
- [x] Red baseline observed for missing family values/runners and blocked schema strategies.
- [x] `job_board_schema` and `real_estate_schema` graduated to native runnable strategies.
- [x] Job and real estate runners normalize existing HTTP worker output through contract schemas.
- [x] Lead, review, and news/content runners reuse HTTP worker output with family-specific filters.
- [x] No Apify execution redirects added.
- [x] No new hard env keys added for direct URL lead/review/news/content runs.
- [x] Focused Phase 5 suite passed.
- [x] Phase 1-5 regression passed.
- [x] Service import aliases work outside the pytest-only shim.
- [x] Secret scan passed.
- [x] Commit completed by the Phase 5 gate commit.
