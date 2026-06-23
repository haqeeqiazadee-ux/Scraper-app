# Codex Subagent Phase 3 Review

Reviewer lane: Codex explorer subagent.

Scope: read-only review of Phase 3 actor-run API and persistence plan in `C:\Users\PC\Scraper-app-verified`.

Verdict:

- Reuse `services/control-plane/routers/actors.py` as the endpoint home.
- Reuse `actor_catalog.get/search` as actor source of truth.
- Reuse `ActorSpec`, `BaseActorRunner`, `ActorRunState`, and provider-chain missing-key behavior from `packages/core/actor_runtime`.
- Persist through existing `TaskRepository`, `RunRepository`, and `ResultRepository`.
- Follow existing `dependencies.py` tenant/session dependency injection.

Minimum behavior requested by the reviewer:

- `POST /api/v1/actors/{actor_id}/runs` returns 404 for unknown actors.
- Runs must never call or redirect to Apify.
- Non-native strategies must be blocked as `blocked_policy`.
- Missing keys must be terminal `skipped_missing_key`, not HTTP 500.
- Successful native runs should store output in `results`.
- Actor run list/detail must be tenant-isolated and actor-scoped.

Warnings incorporated:

- Do not leak env values, only env names.
- Do not treat skipped credentials as failure.
- Do not rely on Apify URLs or connectors.
- Do not use fragile in-memory filtering for list/detail.

Codex response:

- Added actor-scoped SQL joins against existing `tasks` and `runs`.
- Added successful-run result persistence through existing `ResultRepository`.
- Added tests for blocked non-native strategies, missing-key skip, unknown actor, tenant isolation, success result persistence, and newest-first pagination.
