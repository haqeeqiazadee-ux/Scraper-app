# Phase Status

## Current Phase

Phase 5 - Base families B.

## Phase 0 Targets

- [x] Use canonical repo `haqeeqiazadee-ux/Scraper-app`.
- [x] Create implementation branch `codex/own-stack-actors`.
- [x] Record mandatory pre-code reuse gate.
- [x] Record Claude + Codex coordination model.
- [x] Run Claude Phase 1 reuse audit.
- [x] Secret scan passed for Phase 0 docs and `CLAUDE.md`.
- [x] Commit Phase 0 docs and boundary correction: `fdca008`.

## Latest Verified Git State

- Local path: `C:\Users\PC\Scraper-app-verified`
- Branch: `main`
- Main baseline commit: `45bdb35dcfd4764500b4b132dde186cedc767455`
- Remote `main`: `45bdb35dcfd4764500b4b132dde186cedc767455`
- Remote `saas-repair`: `6802b655194a46abf3f9067f3d8a4b11a110180a`

## Next Gate

Phase 5 can be committed only after:

1. `IMPLEMENTATION_LEDGER.md` has the Phase 5 reuse/provenance entry.
2. Job, real estate, lead, review, and news/content family unit tests pass.
3. Actor-run API tests prove `job_board_schema` and `real_estate_schema` execute natively.
4. Phase 1-5 regression passes.
5. Git diff confirms no `yousell-admin` paths and no secret values.

## Phase 1 Results

- [x] Red catalog test observed before implementation.
- [x] Reused `saas-repair` catalog registry/router/generator/tests/pages instead of recoding.
- [x] 27,753 actors available in backend/frontend generated catalog artifacts.
- [x] Actor backend routes mounted under `/api/v1/actors`.
- [x] Actor catalog/detail routes wired into the React app.
- [x] Frontend build passed.
- [x] Secret scan passed.
- [x] Commit completed: `e835a76`.

## Phase 2 Results

- [x] Existing contracts/router/secrets/storage inspected before implementation.
- [x] Runtime tests written before actor-runtime implementation.
- [x] Red missing-module baseline observed.
- [x] Provider fallback red baseline observed before runner semantics fix.
- [x] Actor runtime models, provider chain, and base runner added.
- [x] Missing required keys return `skipped_missing_key` without executing the workflow.
- [x] First available provider can run without being blocked by missing fallback-provider keys.
- [x] Runtime test suite passed.
- [x] Catalog+runtime regression passed.
- [x] Secret scan passed.
- [x] Claude reviewer lane attempted but degraded; Codex gate used as final validation.
- [x] Commit completed: `b2396ad`.

## Phase 3 Results

- [x] Existing actor catalog, task/run/result repositories, DI, smart scrape, execution, HTTP worker, and tests inspected before implementation.
- [x] Actor-run tests written before endpoint implementation.
- [x] Red HTTP 405 baseline observed before endpoints existed.
- [x] Added `POST /api/v1/actors/{actor_id}/runs`.
- [x] Added `GET /api/v1/actors/{actor_id}/runs`.
- [x] Added `GET /api/v1/actors/{actor_id}/runs/{run_id}`.
- [x] Non-native strategies are blocked as `blocked_policy`, not redirected to Apify.
- [x] Missing keys are persisted as `skipped_missing_key`, not fatal errors.
- [x] Successful monkeypatched native runs persist `ResultModel` rows.
- [x] Actor run list/detail are tenant-isolated and actor-scoped.
- [x] Actor-run API suite passed.
- [x] Phase 1-3 regression passed.
- [x] OpenAPI smoke passed.
- [x] Secret scan passed.
- [x] Codex explorer subagent completed read-only review.
- [x] Claude MCP reviewer lane attempted but unavailable.
- [x] Commit completed: `941bc96`.

## Phase 4 Results

- [x] Existing HTTP worker, smart scrape, execution, maps/search routers, connectors, secrets, and tests inspected before implementation.
- [x] Codex explorer subagents completed read-only family reuse scans.
- [x] Base-family tests written before `families.py` implementation.
- [x] Red missing-module baseline observed.
- [x] Added shared base-family registry and runners.
- [x] `generic_web_page_extraction` uses the existing HTTP worker path.
- [x] `commerce_storefront_generic` uses existing Shopify connector before HTTP fallback.
- [x] `marketplace_product_catalog` uses Keepa for Amazon and skips missing `KEEPA_API_KEY`.
- [x] `local_maps_serp` uses existing Google Maps connector and treats Serper/Google keys as optional provider accelerators.
- [x] Actor-run API now uses shared family `build_actor_spec()` and `create_actor_runner()`.
- [x] Family unit tests passed.
- [x] Actor-run API tests passed with the shared family registry.
- [x] Phase 1-4 regression passed.
- [x] Secret scan passed.

## Phase 5 Results

- [x] Existing job board schemas, real estate schemas, HTTP worker, smart scrape intent/schema matching, template registry, crawl manager, change detector, and actor-run API inspected before implementation.
- [x] Codex explorer subagents completed read-only reuse audits for jobs/real estate and leads/reviews/news/content.
- [x] Catalog strategy inventory confirmed 2,483 `job_board_schema` actors and 1,691 `real_estate_schema` actors.
- [x] Phase 5 tests written before runtime/API implementation.
- [x] Red baseline observed for missing family enum values, missing runners, and blocked schema strategies.
- [x] Added `job_board_schema` family using existing HTTP worker output normalized through `JobListing`.
- [x] Added `real_estate_schema` family using existing HTTP worker output normalized through `RealEstateListing`.
- [x] Added `lead_generation_generic`, `review_monitoring_generic`, and `news_content_monitoring` families using existing HTTP worker output plus family-specific filters.
- [x] Actor-run API now treats `job_board_schema` and `real_estate_schema` as native runnable strategies.
- [x] Actor-run API also accepts direct Phase 5 family strategy names if future catalog rows use them directly.
- [x] Service import aliases work outside the pytest-only shim for `services.control_plane` and sibling service packages.
- [x] Review-found generic `name` overmatch in schema normalization fixed and covered by a red/green test.
- [x] Direct URL runs for lead, review, and news/content families have no hard external API-key requirement.
- [x] Focused Phase 5 suite passed: 22 tests.
- [x] Phase 1-5 regression passed: 53 tests.
- [x] Secret scan passed.

## Phase 6 Results - AI-Native Actor Runtime Hardening

- [x] Existing actor runtime, actor API, MCP server, frontend MCP page, and runtime ledgers inspected before implementation.
- [x] API-first/provider-first `ProviderTier` ladder added to actor provider steps.
- [x] Current base families now expose tier, connector, priority, required env names, and rationale.
- [x] Unsupported route strategies now receive machine-readable unsupported provider ladders.
- [x] Extensible workflow substrate added with `WorkflowSpec`, `ProviderLadder`, `WorkflowAdapter`, `WorkflowProfile`, `WorkflowUIContract`, `WorkflowAPISurface`, `WorkflowQAGate`, and `WorkflowRegistry`.
- [x] MCP server now exposes actor search/detail/route/run tools backed by local catalog and native runtime.
- [x] MCP page updated to list actor tools.
- [x] Strategy-profile substrate added with sanitized learning events, replay-gated patch proposals, and guarded profile promotion.
- [x] Base actor runner exposes strategy profile metadata and can emit sanitized learning events through an injected store.
- [x] Trace-to-fixture candidate substrate added for failed, low-confidence, missing-field, and security-risk actor traces.
- [x] Focused actor/MCP/profile/fixture regression passed: 70 tests.
- [x] Frontend build passed.
- [x] Runtime JSON/result packet validation passed.
- [x] Claude read-only validation passed with no blocking findings.
- [x] Workflow operations parity local packet passed for actor-native lifecycle logs, usage, retry, rerun, cancel, and per-run export.
- [x] Persisted profile APIs local packet passed for active profiles, learning events, patch proposals, replay validation, promotion history, and actor-run profile metadata.
- [x] Fixture review materialization local packet passed for candidate queues, approve/reject, materialization, tenant isolation, and redaction preservation.
- [x] Customer value dashboards local packet passed for tenant-scoped actor value metrics and actor detail dashboard build verification.
- [x] Apify-grade UI/product design local packet passed for category rail, featured workflows, active filter chips, API-first run console, value trends, accessibility labels, responsive behavior, and Claude design validation.
- [x] Actor proof-factory local packet passed for proof levels, durable proof rows, proof APIs, proof runner, proof UI status, sample ledger, and Claude validation.
- [ ] Full 27,753 live E2E proof is not claimed: current proof ledger contains 27,753 `api_mapped` rows and 0 `live_e2e_passed` rows.
- [x] Full live E2E gate was run.
- [x] Full live E2E local fixback passed for the 4 persistent scrape-execution cases: example.com, httpbin.org/html UI scrape path, Trustpilot smart scrape, and Trustpilot template execution.
- [x] Full live E2E production rerun passed: 56 passed, 1 warning in 220.62s.
- [x] Deployment verification passed for latest Railway deployment `b90de75c-6409-4bde-b47a-5e09bfd3d7d6`; frontend root returned 200, backend health returned 200, public API account returned 401 without an API key, production proof sample stayed `api_mapped`, and latest post-deploy H1 rerun passed 56/56.
- [x] Proof-factory generated inputs are URL-safe across the full ledger: 27,753 rows regenerated with 0 invalid generated targets, 27,753 `api_mapped`, and 0 `live_e2e_passed`.
- [x] Runtime smoke proof is stricter: completed zero-item runs remain `api_mapped` and cannot become `runtime_smoke_passed`.
- [x] Hosted proof fixtures added for products, jobs, real estate, contacts, reviews, news, and generic extraction; offline ledger regenerated with fixture targets while keeping all 27,753 rows `api_mapped` until live fixture replay succeeds.
- [x] Runtime family classifier now uses word-boundary lead matching, so text like `leading classifieds platform` no longer routes generic workflows into lead-generation proof lanes.
- [x] Hosted fixture replay promotion verified in production on latest Railway deployment `7e2fcb8e-6098-4a0b-82c8-e8ee041708bb` and Netlify deploy `6a40422f954dc32f20af854f`: bounded sample produced 2 `fixture_replay_passed`, 1 `api_mapped`, 0 `live_e2e_passed`, 0 `ui_route_passed`.
- [x] Non-product actor proof normalization fixed and deployed on Railway deployment `f2ecc3db-cd00-445f-9a65-a119631e0d44`: post-fix 25-actor production batch produced 23 `fixture_replay_passed`, 2 `api_mapped` unsupported `yt_dlp`, 0 `live_e2e_passed`, 0 `ui_route_passed`.
- [x] Native `yt_dlp` video actor family added and deployed on Railway deployment `07ba733e-714a-4b6e-9aa6-ce967940acdc`: post-video 25-actor production batch produced 23 `fixture_replay_passed`, 2 `runtime_smoke_passed`, 0 `api_mapped`, 0 failures, 0 `live_e2e_passed`, 0 `ui_route_passed`.
- [x] Production proof rollout scaled to 250 unique actors with retry-aware status: 217 `fixture_replay_passed`, 33 `runtime_smoke_passed`, 0 `api_mapped`, 0 failures, 0 `live_e2e_passed`, 0 `ui_route_passed`; raw ledger rows 293 after transient transport retries.
- [x] Production proof rollout scaled to 500 unique actors with retry-aware status: 419 `fixture_replay_passed`, 81 `runtime_smoke_passed`, 0 `api_mapped`, 0 failures, 0 `live_e2e_passed`, 0 `ui_route_passed`; raw ledger rows 633 after transient transport retries.
- [x] Production proof rollout scaled to 1,000 unique actors with retry-aware status: 853 `fixture_replay_passed`, 147 `runtime_smoke_passed`, 0 `api_mapped`, 0 failures, 0 `live_e2e_passed`, 0 `ui_route_passed`; raw ledger rows 1,172 after transient transport retries.
- [ ] Full SaaS release candidate not claimed: 27,753 live E2E actor proof remains open; current full catalog ledger is 27,753 `api_mapped`, 0 `live_e2e_passed`.
