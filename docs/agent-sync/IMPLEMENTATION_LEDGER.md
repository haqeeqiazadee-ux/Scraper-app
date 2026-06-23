# Implementation Ledger

This file is the mandatory proof trail for the pre-code reuse gate.

## Entry Format

- Task:
- Phase:
- Existing files inspected:
- Reuse decision:
- Reason:
- Files to modify:
- Tests/gates:
- Status:

## Phase 0 - Repo Lock And Agent Coordination

- Task: Establish auto-mode operating base before implementation.
- Phase: 0
- Existing files inspected:
  - `CLAUDE.md`
  - `pyproject.toml`
  - `apps/web/package.json`
  - `requirements-dev.txt`
  - `docs/agent-sync/OWN_STACK_RND_V2/*`
  - `C:\Users\PC\Scraper-app-fresh` git status and actor-catalog worktree inventory
- Reuse decision: `extend_existing`
- Reason: Existing R&D packet and `saas-repair` catalog work provide the right base; no implementation code should be written before preserving provenance, agent lanes, and reuse gates.
- Files to modify:
  - `CLAUDE.md`
  - `docs/agent-sync/AUTO_MODE_ROADMAP.md`
  - `docs/agent-sync/PHASE_STATUS.md`
  - `docs/agent-sync/IMPLEMENTATION_LEDGER.md`
  - `docs/agent-sync/CLAUDE_HANDOFF.md`
  - `docs/agent-sync/CODEX_RELEASE_GATE.md`
  - `docs/agent-sync/MISSING_KEYS_AND_SKIPPED_ACTORS.md`
  - `docs/agent-sync/CLAUDE_REUSE_AUDIT_PROMPT_PHASE1.md`
  - `docs/agent-sync/CLAUDE_REUSE_AUDIT_PHASE1.md`
- Tests/gates:
  - Git remote/provenance check.
  - Claude Phase 1 reuse audit recorded.
  - Codex verified Claude's generated-artifact claim against disk and corrected the audit.
  - Secret scan on agent-sync docs and `CLAUDE.md` passed.
  - Git diff scoped to Scraper-app only.
- Status: Phase 0 gate passed; ready to commit.

## Phase 1 - Catalog Foundation

- Task: Integrate the 27,753-row actor catalog foundation into the verified repo.
- Phase: 1
- Existing files inspected:
  - `services/control-plane/app.py`
  - `apps/web/src/App.tsx`
  - `apps/web/src/components/SidebarNav.tsx`
  - `docs/apify_catalog_implementation_mapping.csv`
  - `docs/apify_catalog_implementation_mapping.xlsx`
  - `apify_store_catalog.xlsx`
  - `C:\Users\PC\Scraper-app-fresh\services\control-plane\routers\actors.py`
  - `C:\Users\PC\Scraper-app-fresh\packages\core\actor_catalog\registry.py`
  - `C:\Users\PC\Scraper-app-fresh\packages\core\actor_catalog\__init__.py`
  - `C:\Users\PC\Scraper-app-fresh\scripts\generate_actor_catalog.py`
  - `C:\Users\PC\Scraper-app-fresh\tests\unit\test_actor_catalog.py`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\src\App.tsx`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\src\components\SidebarNav.tsx`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\src\pages\ActorsPage.tsx`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\src\pages\ActorDetailPage.tsx`
  - `C:\Users\PC\Scraper-app-fresh\packages\core\actor_catalog\generated\apify_actor_catalog.json`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\src\data\apifyActors.generated.json`
  - `C:\Users\PC\Scraper-app-fresh\apps\web\public\data\actors\*`
- Reuse decision: `extend_existing`
- Reason: Verified has the application/router/navigation shells and source catalog CSV/XLSX; `saas-repair` has the catalog registry/router/generator/tests/pages already written. Reuse and wire these pieces instead of creating a duplicate implementation.
- Files to modify:
  - `tests/unit/test_actor_catalog.py`
  - `packages/core/actor_catalog/*`
  - `scripts/generate_actor_catalog.py`
  - `services/control-plane/routers/actors.py`
  - `services/control-plane/app.py`
  - `apps/web/src/App.tsx`
  - `apps/web/src/components/SidebarNav.tsx`
  - `apps/web/src/pages/ActorsPage.tsx`
  - `apps/web/src/pages/ActorDetailPage.tsx`
  - `apps/web/src/data/apifyActors.generated.json`
  - `apps/web/public/data/actors/*`
- Tests/gates:
  - Red test: copied catalog tests fail before source/data is ported.
  - `python -m pytest tests/unit/test_actor_catalog.py -v`
  - Frontend build or typecheck from `apps/web`.
  - Secret scan on generated catalog artifacts.
- Evidence:
  - Red baseline: `C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py -q` failed with 19 failures and 1 skipped before registry/data were ported.
  - Green catalog suite: `C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py -q` passed 20 tests with 1 pre-existing pytest config warning.
  - Frontend build: `npm.cmd run build` in `apps/web` passed.
  - Backend OpenAPI smoke confirmed `/api/v1/actors`, `/api/v1/actors/stats`, `/api/v1/actors/{actor_id}`.
  - Backend TestClient smoke returned 27,753 total actors and 27,753 stats total.
  - Secret scan passed across 34 catalog/source artifacts.
- Status: Phase 1 gate passed; ready to commit.

## Phase 2 - Actor Runtime Core

- Task: Add the native actor runtime contract that lets workflow implementations run on our own stack and skip only workflows with unavailable required keys.
- Phase: 2
- Existing files inspected:
  - `packages/contracts/task.py`
  - `packages/contracts/run.py`
  - `packages/core/router.py`
  - `packages/core/secrets.py`
  - `packages/core/storage/models.py`
  - `packages/core/storage/repositories.py`
  - `packages/core/actor_catalog/registry.py`
  - `services/control-plane/routers/actors.py`
- Reuse decision: `extend_existing`
- Reason: Existing task/run contracts, execution routing, secret-provider abstraction, and storage repositories should remain the system backbone. A small actor-runtime package is needed because no existing module expresses per-actor provider chains, missing-key skip semantics, or reusable base runner results.
- Files to modify:
  - `tests/unit/test_actor_runtime.py`
  - `packages/core/actor_runtime/__init__.py`
  - `packages/core/actor_runtime/models.py`
  - `packages/core/actor_runtime/provider_chain.py`
  - `packages/core/actor_runtime/runner.py`
  - `docs/agent-sync/CLAUDE_RUNTIME_AUDIT_PROMPT_PHASE2.md`
  - `docs/agent-sync/CLAUDE_RUNTIME_AUDIT_PHASE2.md`
  - `docs/agent-sync/CLAUDE_RUNTIME_AUDIT_PHASE2.err`
- Tests/gates:
  - Red test: runtime tests fail before `packages.core.actor_runtime` exists.
  - `C:\Python314\python.exe -m pytest tests/unit/test_actor_runtime.py -q`
  - `C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py tests/unit/test_actor_runtime.py -q`
  - Secret scan on new runtime/test/sync docs.
- Evidence:
  - Red baseline: `C:\Python314\python.exe -m pytest tests/unit/test_actor_runtime.py -q` failed with `ModuleNotFoundError: No module named 'packages.core.actor_runtime'`.
  - Fallback-provider red baseline: added a test proving a runnable first provider must not be blocked by missing fallback-provider keys; it failed as `skipped_missing_key` before the runner fix.
  - Green runtime suite: `C:\Python314\python.exe -m pytest tests/unit/test_actor_runtime.py -q` passed 5 tests with 1 pre-existing pytest config warning.
  - Green catalog+runtime regression: `C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py tests/unit/test_actor_runtime.py -q` passed 25 tests with 1 pre-existing pytest config warning.
  - Claude Phase 2 reviewer lane was attempted, but the CLI returned a stale Phase 1 handoff and a hook warning; Codex treated that lane as degraded and did not count it as validation.
  - Secret scan passed across Phase 2 runtime/test/sync artifacts.
- Status: Phase 2 gate passed; ready to commit.

## Phase 3 - Native Actor Run API

- Task: Add native actor run endpoints and persistence using the existing backend state model.
- Phase: 3
- Existing files inspected:
  - `services/control-plane/routers/actors.py`
  - `services/control-plane/routers/tasks.py`
  - `services/control-plane/routers/execution.py`
  - `services/control-plane/routers/smart_scrape.py`
  - `services/control-plane/dependencies.py`
  - `packages/core/storage/models.py`
  - `packages/core/storage/repositories.py`
  - `packages/core/actor_catalog/registry.py`
  - `packages/core/actor_runtime/*`
  - `services/worker-http/worker.py`
  - `tests/unit/test_api_execution.py`
  - `tests/integration/test_api/test_tasks_api.py`
  - `apps/web/src/pages/ActorDetailPage.tsx`
  - `docs/agent-sync/AUTO_MODE_ROADMAP.md`
- Reuse decision: `extend_existing`
- Reason: The repo already has catalog routing, tenant/session DI, task/run/result tables, repository classes, and HTTP worker execution. Phase 3 extends these instead of adding a duplicate actor-run persistence model or any Apify execution path.
- Files to modify:
  - `services/control-plane/routers/actors.py`
  - `tests/unit/test_actor_runs_api.py`
  - `docs/agent-sync/CODEX_SUBAGENT_PHASE3_REVIEW.md`
  - `docs/agent-sync/CLAUDE_PHASE3_REVIEW_ATTEMPT.md`
  - `docs/agent-sync/IMPLEMENTATION_LEDGER.md`
  - `docs/agent-sync/PHASE_STATUS.md`
  - `docs/agent-sync/CODEX_RELEASE_GATE.md`
- Tests/gates:
  - Red test: actor run API returned `405 Method Not Allowed` before endpoints existed.
  - `C:\Python314\python.exe -m pytest tests/unit/test_actor_runs_api.py -q`
  - `C:\Python314\python.exe -m pytest tests/unit/test_actor_catalog.py tests/unit/test_actor_runtime.py tests/unit/test_actor_runs_api.py -q`
  - OpenAPI smoke for `/api/v1/actors/{actor_id}/runs` and `/api/v1/actors/{actor_id}/runs/{run_id}`.
  - Secret scan on Phase 3 router/test/sync docs.
- Evidence:
  - Red baseline: Phase 3 tests failed with HTTP 405 before endpoints were implemented.
  - Green actor-run API suite: 6 tests passed.
  - Green Phase 1-3 regression: 31 tests passed with only pre-existing warnings.
  - OpenAPI smoke confirmed actor run create/list/detail paths.
  - Codex explorer subagent completed read-only review and its recommendations were incorporated.
  - Claude MCP review attempt failed with `Agent type 'general-purpose' not found`; not counted as validation.
  - Secret scan passed across Phase 3 router/test/sync artifacts.
- Status: Phase 3 gate passed; ready to commit.
