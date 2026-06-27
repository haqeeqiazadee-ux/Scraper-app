# Blocker-Closure One-Shot Execution Prompt: Scraper-App Apify Competitor

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch: `codex/own-stack-actors`
Supersedes: `docs/agent-sync/SCRAPER_APP_FINAL_APIFY_COMPETITOR_EXECUTION_PROMPT_2026-06-27.md`

## 0. Correction And Scope

The previous prompt was execution-campaign ready, but the phrase "one-shot SaaS execution-prompt ready" was too loose because downstream release blockers remained open. This prompt corrects that by making the blockers mandatory release packets.

You are Codex executing in `C:\Users\PC\Scraper-app-verified`.

Your mission is to continue from the current existing state and close the remaining SaaS release blockers without starting from scratch. The accepted local baseline already includes actor catalog, native actor runtime, knowledge/freshness trait, API-first provider ladders, extensible workflow substrate, MCP actor tools, self-learning profile substrate, trace-to-fixture candidates, runtime ledgers, focused tests, and existing React/Vite UI pages.

Do not claim `full_saas_release_candidate_ready` until every blocker below is implemented, tested, ledgered, validated, and accepted by Codex final QA.

## 1. Source Files To Read First

Read or inspect these before implementation:

- `AGENTS.md`
- `docs/agent-sync/IMPLEMENTATION_LEDGER.md`
- `docs/agent-sync/PHASE_STATUS.md`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_EXECUTION_VALIDATION_2026-06-27.md`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_TASK_DAG_2026-06-27.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_EXTERNAL_RND_GAP_MATRIX_2026-06-27.md`
- `packages/core/actor_runtime/`
- `services/control-plane/routers/actors.py`
- `packages/core/storage/models.py`
- `packages/core/storage/repositories.py`
- `services/control-plane/routers/results.py`
- `services/control-plane/routers/schedules.py`
- `services/control-plane/routers/webhooks.py`
- `services/control-plane/routers/billing.py`
- `apps/web/src/pages/ActorsPage.tsx`
- `apps/web/src/pages/ActorDetailPage.tsx`
- `apps/web/src/pages/ScraperPage.tsx`
- `apps/web/src/pages/ResultsPage.tsx`
- `apps/web/src/pages/SchedulesPage.tsx`
- `apps/web/src/pages/BillingPage.tsx`
- `apps/web/src/components/`
- `apps/web/src/styles/`

If `graphify-out/wiki/index.md` exists, use it as navigation before raw file expansion. If absent, record `GRAPHIFY_ABSENT` and continue with `rg`, current ledgers, and tests.

## 2. Mandatory Authority And Roles

Codex is execution owner, task router, source-of-truth arbiter, final QA authority, and only git authority.

Claude is an independent syntax, semantic, business-logic, topology, UI/product-design, and fixback validator. Claude must use its design-review skills for the UI parity/superiority packet: information architecture, visual hierarchy, interaction design, accessibility, responsive layout, operational-console ergonomics, and competitive benchmark critique against Apify-level SaaS UI expectations. Claude cannot approve completion unless Codex verifies its claims against files, tests, screenshots, and git state.

Antigravity is optional read-only UI/runtime observer only when explicitly available. It cannot edit or approve.

Python SaaS Gurus are optional bounded research/implementation lanes for FastAPI, SQLAlchemy, Pydantic, async workflows, API contracts, migrations, tests, dashboards, and deployment mechanics. Their output must return as a result packet and pass Codex QA.

Jules escalation is only for repeated blockers after local fixback and Claude review. Jules cannot mutate this repo.

## 3. Non-Negotiable Guardrails

- Do not execute through Apify as runtime backend.
- Do not copy proprietary Apify implementation code.
- Keep Apify URLs as competitor metadata only.
- Preserve API-first/provider-first routing. Official/public APIs, provider SDKs, internal APIs, and existing connectors come before scrape/browser work.
- Do not add raw secrets, API keys, cookies, tokens, credentials, private customer inputs, or unredacted PII to code, docs, fixtures, logs, prompts, graph memory, or result packets.
- All profile, fixture, trace, dashboard, and value metrics must be tenant-scoped.
- No customer-visible cached/graph-derived result may be served without provenance, freshness, timestamp, policy version, tenant scope, and decision path.
- Do not overwrite unrelated dirty files.
- Do not claim full release readiness while any blocker packet is incomplete, untested, externally blocked, or only documented.
- Do not claim "same level as Apify" or "better than Apify" for UI unless the UI packet has implemented changes, responsive screenshot evidence, accessibility checks, build verification, and Claude design validation with no blocking findings.

## 4. Existing-Code Reuse Gate

Every packet starts with:

```text
reuse_as_is
extend_existing
replace_existing
new_code_required
defer_or_skip
```

Default expected outcome is `extend_existing`.

Before editing a packet:

1. Run the second-brain reuse gate:
   `python C:\Users\PC\second-brain\tools\reuse_gate.py --project C:\Users\PC\Scraper-app-verified --task "<packet>" --terms "<keywords>"`
2. Use `rg` to inspect local implementation surfaces.
3. Record the reuse decision in `docs/agent-sync/IMPLEMENTATION_LEDGER.md`.
4. Lock files in `docs/agent-sync/runtime/APIFY_WORKFLOWS_LOCKS_2026-06-27.json`.

## 5. Priority Blockers And How To Close Them

### Priority 1: `F2-workflow-ops-parity`

Why first: workflow operations are the SaaS backbone. Dashboards, E2E, and deployment are not meaningful until actor runs have production-grade lifecycle behavior.

Meet the requirement by extending existing routers/storage/UI for:

- actor run status history and logs
- retry, cancel, and re-run
- schedules for actor runs
- webhooks for actor run completion/failure
- result artifacts, datasets, exports, and pagination
- usage/quota tracking per actor run
- consistent API envelopes and error codes

Expected files:

- `services/control-plane/routers/actors.py`
- `services/control-plane/routers/results.py`
- `services/control-plane/routers/schedules.py`
- `services/control-plane/routers/webhooks.py`
- `services/control-plane/routers/billing.py`
- `packages/core/storage/models.py`
- `packages/core/storage/repositories.py`
- `apps/web/src/pages/ActorDetailPage.tsx`
- `apps/web/src/pages/ResultsPage.tsx`
- focused tests under `tests/unit/`

Acceptance:

- actor run lifecycle API tests pass
- schedule/webhook/export API tests pass
- retry/cancel/re-run is actor-native and does not call Apify
- tenant isolation and pagination are tested

### Priority 2: `E3-persisted-profile-apis`

Why second: self-learning must be durable and tenant-safe before fixture review or dashboards can use it.

Meet the requirement by adding DB/repository/API support for:

- `StrategyProfile`
- `ActorLearningEvent`
- `StrategyPatchProposal`
- `ReplayValidationResult`
- promotion history and policy version

Expected files:

- `packages/core/storage/models.py`
- `packages/core/storage/repositories.py`
- `services/control-plane/routers/actors.py` or a new narrow actor-profile router if app patterns support it
- `packages/core/actor_runtime/profiles.py`
- `tests/unit/test_actor_strategy_profile_api.py`

Acceptance:

- profile CRUD is tenant-isolated
- learning events store redacted payload fingerprints only
- promotion is blocked unless replay validation passed
- actor run metadata exposes active profile version and policy version

### Priority 3: `G3-fixture-review-materialization`

Why third: trace-to-fixture candidates exist, but they are not production useful until reviewed, persisted, and materialized safely.

Meet the requirement by adding:

- fixture candidate review queue
- approve/reject API
- redacted fixture materializer
- deterministic fixture file layout
- CI replay command or script
- linkage from fixture approval to strategy proposal/profile promotion

Expected files:

- `packages/core/actor_runtime/fixtures.py`
- `packages/core/storage/models.py`
- `packages/core/storage/repositories.py`
- `services/control-plane/routers/actors.py` or `services/control-plane/routers/fixtures.py`
- `scripts/`
- `tests/fixtures/actor_runtime/`
- `tests/unit/test_actor_fixture_review.py`

Acceptance:

- approved candidate writes sanitized fixture only
- rejected candidate never materializes
- fixture file contains no raw secrets
- CI replay command runs approved fixtures deterministically
- fixture approval can satisfy replay requirements for profile promotion

### Priority 4: `G4-customer-value-dashboards`

Why fourth: value dashboards depend on stable workflow ops, profile persistence, and fixture/replay signals.

Meet the requirement by adding backend aggregate APIs and frontend dashboard views for:

- successful runs
- failed/blocked/skipped runs
- cache/knowledge reuse savings
- estimated and actual cost per result
- data freshness
- data quality score
- time saved estimate
- profile/replay improvement impact
- fixture candidates and accepted fixes

Expected files:

- `services/control-plane/routers/actors.py`
- `services/control-plane/routers/billing.py`
- `packages/core/storage/repositories.py`
- `apps/web/src/pages/ActorsPage.tsx`
- `apps/web/src/pages/ActorDetailPage.tsx`
- new dashboard component/page only if existing pages cannot carry it cleanly
- `tests/unit/test_actor_value_metrics.py`

Acceptance:

- backend aggregate tests pass
- frontend build passes
- empty/loading/error states exist
- dashboard metrics are tenant-scoped and derived from persisted data

### Priority 5: `U1-apify-grade-ui-product-design`

Why fifth: once workflow data and value metrics exist, the product must expose them through an Apify-grade or better operator experience before full E2E and deployment can be credible.

Meet the requirement by improving the existing UI, not replacing it from scratch:

- actor store/catalog browsing, filtering, search, category sections, and actor cards
- actor detail pages with run setup, API-first/provider-first hints, pricing/usage signals, inputs, outputs, logs, schedules, webhooks, exports, and related actors
- run console with status timeline, retries, cancel/re-run, datasets, artifacts, and provenance/freshness metadata
- customer value dashboards with saved-time, avoided-rerun, cache-hit, freshness, cost, quality, and success-rate metrics
- API-first developer experience: public API examples, copyable requests, webhook setup, schedule setup, and SDK-ready response shapes
- responsive desktop/tablet/mobile layouts
- empty, loading, error, blocked-policy, permission, quota, and degraded-data states
- accessibility basics: keyboard flow, focus states, contrast, labels, and non-overlapping text

Claude design lane is mandatory:

1. Claude reviews the existing UI files and Apify Store/operator-console screenshot or live benchmark as competitor reference only.
2. Claude writes a concise design brief covering what must be improved to reach Apify-grade or better quality.
3. Codex implements the accepted design changes in the existing React/Vite UI.
4. Codex captures or records responsive verification evidence.
5. Claude performs a second read-only design validation and returns `PASS` or `BLOCKING`.
6. Codex fixes accepted blocking findings before this packet can close.

Expected files:

- `apps/web/src/pages/ActorsPage.tsx`
- `apps/web/src/pages/ActorDetailPage.tsx`
- `apps/web/src/pages/ScraperPage.tsx`
- `apps/web/src/pages/ResultsPage.tsx`
- `apps/web/src/pages/SchedulesPage.tsx`
- `apps/web/src/pages/BillingPage.tsx`
- `apps/web/src/components/`
- `apps/web/src/styles/`
- frontend tests or screenshot artifacts under existing test/artifact locations
- result packet under `docs/agent-sync/runtime/result-packets/`

Acceptance:

- Claude design brief exists and is referenced in the packet
- UI is implemented in existing app surfaces, not as a disconnected mockup
- actor catalog/detail/run experience is visibly competitive with Apify-level SaaS UX
- API-first developer actions are first-class in the UI
- desktop and mobile layouts are verified without overlapping text or broken cards
- `npm.cmd run build` passes from `apps/web`
- Claude design validation returns no blocking findings
- Codex final QA confirms superiority/parity is evidence-backed, not merely claimed

### Priority 6: `H1-full-e2e`

Why sixth: E2E should verify completed behavior, not chase unfinished contracts.

Meet the requirement by adding/running E2E coverage for:

- actor search/detail/run
- actor lifecycle retry/cancel/re-run
- actor schedules/webhooks/exports
- profile event/proposal/replay/promotion
- fixture review/materialization
- value dashboard metrics
- Apify-grade actor store/detail/run-console UI across desktop and mobile where frontend tooling allows
- MCP actor discovery/route/run surface where feasible

Expected files:

- `tests/e2e/`
- `tests/e2e/playwright/`
- `run_e2e.bat` or equivalent existing runner
- result packet under `docs/agent-sync/runtime/result-packets/`

Acceptance:

- focused actor regression remains green
- frontend E2E passes or every blocked live dependency is explicitly recorded
- backend E2E passes against local test app
- no skipped critical path without a blocker entry

### Priority 7: `H2-deployment-verification`

Why last: deployment verification is only credible after features and E2E pass.

Meet the requirement by verifying:

- Railway backend health/readiness
- Netlify frontend build/deploy
- DB migrations applied
- env vars present without leaking values
- public API smoke
- actor run smoke on deployed backend
- result export smoke
- schedule/webhook smoke if safe
- MCP docs/config accuracy

Expected files:

- `docs/agent-sync/CODEX_RELEASE_GATE.md`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_DEPLOYMENT_VERIFICATION_2026-06-27.md`
- smoke scripts under `scripts/` only if needed

Acceptance:

- deployment URLs checked
- smoke test report saved
- secret scan passes
- release gate updated
- Codex final QA records either `full_saas_release_candidate_ready` or exact external blockers

## 6. Required DAG

Use this order unless current code proves a narrower dependency change:

```json
[
  {
    "packet_id": "F2-workflow-ops-parity",
    "priority": 1,
    "depends_on": ["B1", "B2", "B3", "C1", "D1", "E1"],
    "status": "pending"
  },
  {
    "packet_id": "E3-persisted-profile-apis",
    "priority": 2,
    "depends_on": ["E2", "F2"],
    "status": "pending"
  },
  {
    "packet_id": "G3-fixture-review-materialization",
    "priority": 3,
    "depends_on": ["G2", "E3"],
    "status": "pending"
  },
  {
    "packet_id": "G4-customer-value-dashboards",
    "priority": 4,
    "depends_on": ["F2", "E3", "G3"],
    "status": "pending"
  },
  {
    "packet_id": "U1-apify-grade-ui-product-design",
    "priority": 5,
    "depends_on": ["F2", "E3", "G3", "G4"],
    "status": "pending"
  },
  {
    "packet_id": "H1-full-e2e",
    "priority": 6,
    "depends_on": ["F2", "E3", "G3", "G4", "U1"],
    "status": "pending"
  },
  {
    "packet_id": "H2-deployment-verification",
    "priority": 7,
    "depends_on": ["H1"],
    "status": "pending"
  }
]
```

Independent sub-lanes may run read-only discovery in parallel, but implementation order must respect dependencies.

## 7. Continuous Execution Loop

Use the continuous-agent-loop pattern:

1. Recover current state from git, disk, runtime DAG, and ledgers.
2. Run reuse gate for the next packet.
3. Lock the packet files.
4. Implement narrowly using existing patterns.
5. Prefer Python scripts for structured inspection, migrations, fixture generation, JSON validation, and mechanical rewrites.
6. Run focused tests.
7. Run impacted regressions.
8. Write result packet.
9. Run Claude validation after meaningful packet groups or before release claims. For `U1-apify-grade-ui-product-design`, Claude validation must include a dedicated design critique before implementation and a dedicated design validation after implementation.
10. Fix accepted findings.
11. Update ledgers and release gate.
12. Continue until all seven blocker packets are accepted or an external blocker remains after fixback.

Do not stop after one packet unless the user explicitly pauses execution.

## 8. Result Packet Contract

Every packet must write:

`docs/agent-sync/runtime/result-packets/<packet_id>.json`

Required fields:

```json
{
  "packet_id": "",
  "priority": 0,
  "agent": "codex",
  "phase": "",
  "lock_group": "",
  "reuse_decision": "",
  "files_read": [],
  "files_changed": [],
  "implementation_summary": "",
  "tenant_isolation_checked": false,
  "secrets_touched": false,
  "api_first_boundary_checked": false,
  "profile_persistence_checked": false,
  "fixture_materialization_checked": false,
  "workflow_ops_checked": false,
  "dashboard_value_checked": false,
  "ui_design_checked": false,
  "claude_design_review_status": "",
  "e2e_checked": false,
  "deployment_checked": false,
  "tests_run": [],
  "tests_passed": [],
  "tests_failed": [],
  "known_limitations": [],
  "qa_status": "",
  "next_recommended_packet": ""
}
```

## 9. Validation Commands

Minimum after backend/runtime changes:

```powershell
python -m compileall -q packages services tests
python -m pytest tests/unit/test_actor_runtime.py tests/unit/test_actor_runs_api.py -q
```

Minimum after profile/fixture changes:

```powershell
python -m pytest tests/unit/test_actor_strategy_profiles.py tests/unit/test_actor_trace_to_fixture.py -q
```

Minimum after workflow ops changes:

```powershell
python -m pytest tests/unit/test_actor_runs_api.py tests/unit/test_webhook.py tests/unit/test_quota_manager.py -q
```

Minimum after frontend changes:

```powershell
Set-Location apps/web
npm.cmd run build
```

Minimum after UI/product-design changes:

```powershell
Set-Location apps/web
npm.cmd run build
```

Also run the existing Playwright/frontend screenshot workflow when available. At minimum, record desktop and mobile verification notes for actor catalog, actor detail/run console, result export, schedules/webhooks, dashboards, loading/error/empty states, and API-first developer actions.

Minimum release gate:

```powershell
python -m pytest tests/unit/test_actor_runtime.py tests/unit/test_actor_families.py tests/unit/test_actor_freshness_policy.py tests/unit/test_actor_graph_memory.py tests/unit/test_actor_knowledge_memory.py tests/unit/test_actor_runs_api.py tests/unit/test_actor_traces.py tests/unit/test_actor_evals.py tests/unit/test_actor_ai_security.py tests/unit/test_actor_costs.py tests/unit/test_actor_provider_ladder.py tests/unit/test_workflow_extension_contract.py tests/unit/test_mcp_actor_tools.py tests/unit/test_actor_strategy_profiles.py tests/unit/test_actor_trace_to_fixture.py -q
npm.cmd run build
git diff --check
```

If full unit/E2E cannot run because of environment dependencies, record exact missing dependency, affected command, and the smallest valid substitute. Do not convert substitute validation into full release readiness.

## 10. Completion States

Allowed final states:

- `full_saas_release_candidate_ready`: all seven blocker packets accepted, full release gate passed, Claude validation has no blocking findings, Claude UI design validation has no blocking findings, deployment verification complete.
- `partial_blocked_not_release_ready`: at least one mandatory blocker remains incomplete, untested, or externally blocked.
- `blocked`: same external blocker persists after local fixback and Claude review, and no unrelated blocker packet can progress.

Forbidden final states:

- "one-shot ready" while blocker packets remain pending.
- "better than Apify" while parity/superiority gates are only documented.
- "complete" when only prompt/documentation work has been done.

## 11. Final Response Required

When the run completes or blocks, report only:

- final state
- completed blocker packets
- remaining blocker packets
- tests run and results
- Claude validation status
- release/deployment status
- exact artifact paths
