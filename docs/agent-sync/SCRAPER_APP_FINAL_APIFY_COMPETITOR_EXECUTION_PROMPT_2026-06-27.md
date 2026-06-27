# Final Execution Prompt: Existing-State Scraper-App Apify Competitor Build

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch at prompt creation: `codex/own-stack-actors`
Seed HEAD at prompt creation: `2461423885f348ffa21136e16502e5f6b8bb5ef3`
Canonical remote: `https://github.com/haqeeqiazadee-ux/Scraper-app`
Canonical main baseline: `45bdb35dcfd4764500b4b132dde186cedc767455`

## 0. Run This Prompt

You are Codex executing in `C:\Users\PC\Scraper-app-verified`.

Your mission is to continue from the existing project state and build the Scraper-app actor platform into an AI-native, API-first, own-stack Apify competitor. You are not starting from scratch. The repo already contains actor catalog generation, generated actor data, a native actor runtime, base-family runners, native actor run APIs, frontend actor data, tests, phase ledgers, and release-gate docs. Your job is to extend, harden, connect, validate, and productize what exists.

Do not create a greenfield replacement. Do not move the platform into a new app, new repo, new framework, or parallel runtime. Reuse and extend the existing architecture unless a specific packet proves that replacement is safer and narrower.

API-first and provider-first is mandatory: for every actor family, prefer stable official/public APIs, existing internal APIs, provider SDKs, managed connector surfaces, and current platform connectors before HTTP scraping, browser automation, hard-target lanes, or new scrape code. Browser/scrape logic is a fallback when no durable API/provider path satisfies the workflow. This does not mean executing through Apify; Apify docs and URLs are competitor references only.

One-shot SaaS completion mode is mandatory. This prompt is intended to run as a continuous, multi-agent, multi-loop execution system until the Scraper-app actor platform is either release-candidate ready or explicitly blocked by a real external dependency. Do not stop after producing plans, partial packets, or architecture notes. Continue cycling through state refresh, packet dispatch, implementation, QA, fixback, validation, and release gating. Ask the user only for destructive git operations, unavailable secrets/accounts, paid external services, or product decisions that cannot be inferred from the repo and source docs.

One-shot does not mean unsafe big-bang edits. It means one uninterrupted execution campaign with bounded parallel lanes, non-overlapping locks, result packets, validation gates, and fixbacks until the SaaS build is complete enough for Codex final QA or a documented blocker.

The SaaS must be built as an extensible workflow platform, not a fixed catalog of current actor categories. Future teams must be able to add new workflow categories, new platform types, new provider ladders, new schemas, and new UI/API surfaces without rewriting the core runtime, router, storage, or QA harness. Category-specific logic belongs in versioned workflow definitions, provider adapters, schemas, tests, and profiles; shared execution, memory, governance, billing, observability, and API contracts remain stable.

## 1. Source Files To Read First

Read these before implementation:

- `AGENTS.md`
- `CLAUDE.md`
- `docs/agent-sync/PHASE_STATUS.md`
- `docs/agent-sync/IMPLEMENTATION_LEDGER.md`
- `docs/agent-sync/CODEX_RELEASE_GATE.md`
- `docs/agent-sync/OWN_STACK_RND_V2/`
- `docs/agent-sync/SCRAPER_APP_APIFY_WORKFLOWS_SELF_LEARNING_LOOP_PROMPT_2026-06-27.md`
- `docs/agent-sync/SCRAPER_APP_APIFY_COMPETITOR_EXTERNAL_RND_2026-06-27.md`
- `docs/agent-sync/SCRAPER_APP_APIFY_WORKFLOWS_SELF_LEARNING_LOOP_VALIDATION_2026-06-27.md`

These files are source context, not optional background. If any are missing, stop and report the exact missing path.

If `graphify-out/wiki/index.md` exists, query/browse it before raw file expansion. If the project graph is absent, record that limitation and continue with `rg`, current files, ledgers, and tests.

## 2. Current Baseline You Must Preserve

Observed baseline at prompt creation:

- Branch: `codex/own-stack-actors`
- HEAD: `2461423885f348ffa21136e16502e5f6b8bb5ef3`
- Recent commits:
  - `2461423 docs: add repo agent instructions`
  - `5d8fbe9 feat: add schema actor base families`
  - `96f6c0d feat: add actor base family runners`
  - `941bc96 feat: add native actor run api`
  - `b2396ad feat: add actor runtime core`
- Phase: `Phase 5 - Base families B`
- Catalog total: 27,753 actors
- Generated catalog artifacts already exist under:
  - `packages/core/actor_catalog/generated/apify_actor_catalog.json`
  - `apps/web/src/data/apifyActors.generated.json`
  - `apps/web/public/data/actors/`
- Native actor runtime already exists under:
  - `packages/core/actor_runtime/`
- Native actor API route already exists:
  - `services/control-plane/routers/actors.py`
- Focused actor tests already exist:
  - `tests/unit/test_actor_catalog.py`
  - `tests/unit/test_actor_runtime.py`
  - `tests/unit/test_actor_families.py`
  - `tests/unit/test_actor_runs_api.py`

Known base-family distribution at prompt creation:

```text
lead_generation_generic       7268
generic_web_page_extraction   4840
yt_dlp                        3055
review_monitoring_generic     2768
job_board_schema              2483
commerce_storefront_generic   2357
real_estate_schema            1691
news_content_monitoring       1447
marketplace_product_catalog   1165
local_maps_serp                679
```

You must recompute this state from disk before changing code. If the state has drifted, update the state seed and reason from current files, not this snapshot.

## 3. Mandatory Boundaries

- Do not copy Apify proprietary implementation code.
- Do not execute through Apify as the runtime backend.
- Do not treat Apify source URLs from external R&D as live crawl targets or runtime dependencies. They are competitor metadata and documentation references only.
- Do not build a workflow end-to-end from scratch before proving that no official/public API, existing connector, provider SDK, or existing platform API can satisfy the actor family.
- Do not claim "better than Apify" or competitor-grade readiness until Apify parity gates and better-than-Apify superiority gates are implemented, tested, and recorded.
- Do not add secrets, API keys, tokens, cookies, credentials, or unredacted private customer data to code, docs, prompts, logs, graph memory, vector stores, fixtures, or result packets.
- Do not allow cross-tenant memory bleed. Cache keys, graph namespaces, vector namespaces, artifacts, learning events, fixtures, and replay data must be tenant/customer scoped where user data is involved.
- Do not serve cached, graph, vector, or Obsidian-derived data as current fact unless the response includes provenance, freshness state, source timestamp, policy version, tenant scope, and the decision path that allowed reuse.
- Do not use Obsidian/Graphify as the sole production source for customer-visible results. They are audit/navigation mirrors only.
- Do not overwrite user changes. If the worktree is dirty, classify every dirty file before editing.

## 4. Authority And Agent Roles

Codex is the execution owner, task router, source-of-truth arbiter, final QA authority, and only git authority.

Claude is the independent syntax, semantic, business-logic, topology, and fixback validator. Claude output is advisory until Codex verifies it against files, tests, and current repo state.

Antigravity is optional read-only observer/UI sanity validator. It cannot edit, approve, claim completion, or override Codex. Use only with an explicit Codex observer token if the execution packet requires it.

Python SaaS Gurus are optional bounded implementation specialists for FastAPI, Pydantic, SQLAlchemy, async runtime, tests, and SaaS product mechanics. Their output must return as a patch-level result packet and pass Codex QA.

Jules escalation is only for repeated blockers after local and Claude fixback attempts. Jules cannot mutate this repo or claim completion without Codex acceptance.

## 5. Existing-Code Reuse Gate

Every packet starts with reuse classification:

```text
reuse_as_is
extend_existing
replace_existing
new_code_required
defer_or_skip
```

Default expectation for this project is `extend_existing`.

Minimum reuse scan:

```powershell
rg -n "actor_catalog|ActorCatalog|apify_actor_catalog|create_actor_runner|ActorBaseFamily|ProviderChain|RUNNABLE_NATIVE_STRATEGIES|KnowledgeBackedActorRunner|freshness|MCP|trace|eval|webhook|schedule" packages services apps tests docs -S
rg --files packages/core/actor_runtime packages/core/actor_catalog services/control-plane/routers apps/web/src apps/web/public/data/actors tests docs/agent-sync
```

Before editing a packet, write the reuse decision and rationale to `docs/agent-sync/IMPLEMENTATION_LEDGER.md`.

Python-first automation is mandatory for repeatable inspection, state seeding, graph/freshness scoring, fixture generation, result-packet validation, and mechanical migrations. Prefer Python scripts over manual one-off shell parsing whenever the task touches structured data or repeated file operations.

## 6. State Seed Artifacts To Create First

Before implementation, create or refresh:

- `docs/agent-sync/runtime/APIFY_WORKFLOWS_STATE_SEED_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_TASK_DAG_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_LOCKS_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_QA_QUEUE.jsonl`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_DECISION_LEDGER.jsonl`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_KNOWLEDGE_MEMORY_PLAN_YYYY-MM-DD.md`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_EXTERNAL_RND_GAP_MATRIX_YYYY-MM-DD.md`

State seed must include:

- git branch and HEAD
- worktree status
- actor catalog totals
- base-family counts
- route-strategy counts
- runnable/unsupported counts
- current actor runtime files
- current actor API files
- current frontend actor files
- current focused test files
- current API/provider/connector coverage by actor base family
- missing or stale source docs
- Graphify/Obsidian availability
- prompt/R&D freshness status

## 7. Product Target

Build toward this product shape:

```text
Apify parity
+ API-first/provider-first execution spine
+ own-stack native runtime
+ category-agnostic workflow extension substrate
+ knowledge-backed result reuse
+ self-learning actor strategy profiles
+ graph/vector/artifact memory
+ MCP-native AI-agent distribution
+ trace/eval-driven reliability
+ AI security and governance
+ cost/pricing transparency
+ customer value proof dashboards
```

This is not only an actor clone. It is an AI-native workflow platform where every run can improve future runs without hiding provenance or bypassing freshness and tenant safety.

## 8. Required Apify Parity Gates

Build and test parity for:

- Actor marketplace/catalog: search, category, detail, examples, pricing/developer metadata.
- Actor input schemas: dynamic forms, validation, defaults, examples.
- Actor execution: runs, logs, status, retries, artifacts, datasets/results, exports.
- Workflow operations: schedules, webhooks, queues, storage, request/result artifacts, rate limits, usage tracking.
- API-first/provider-first routing: official/public APIs, provider SDKs, existing platform connectors, internal APIs, HTTP extraction, browser/unblocker, and authenticated-session fallback must be explicitly ordered per family.
- API/SDK surface: stable route contracts, result envelopes, pagination, auth, error codes, client contracts, and UI behavior built on top of public/internal API contracts rather than UI-only flows.
- MCP and AI-agent distribution: MCP tools/resources/prompts, dynamic actor discovery, actor detail inspection, structured output schemas, secure token/OAuth path, telemetry controls, and rate-limit behavior.
- Extensible workflow substrate: category-agnostic workflow definitions, provider ladders, input/output schemas, examples, adapter contracts, versioned profiles, UI form generation, API exposure, tests, docs, and migration rules for adding any future platform category without core rewrites.

## 9. Better-Than-Apify Superiority Gates

Build and test superiority for:

- Knowledge-first runtime: DB/cache, graph, vector/semantic, artifact replay, partial refresh, background refresh, freshness scoring, tenant-safe memory, and provenance.
- Self-learning actor profiles: AI proposes strategy patches, deterministic replay validates, Codex-promoted profiles become versioned runtime inputs.
- Observability/evals: trace spans for provider steps, tool calls, memory lookup, graph traversal, freshness decision, AI extraction, normalization, and failure classification.
- Trace-to-fixture loop: failed or low-confidence production traces become deterministic regression fixtures.
- AI security/governance: prompt injection, malicious/untrusted page instructions, insecure output handling, excessive agency, model/tool denial-of-service, supply chain, and data leakage tests.
- Cost/pricing intelligence: estimated cost, actual cost, cache savings, budget state, quota state, usage meter, and compute-adjusted margin by base family.
- Customer value proof: dashboards for time saved, successful runs, cache hit savings, data freshness, failure rate, cost per result, and data quality score.
- Multi-model/provider routing: route by task complexity, latency, privacy, reliability, cost, and fallback availability.

## 9A. Extensible Workflow Architecture Contract

Every new workflow category must be added through stable extension points, not hardcoded branches scattered across the SaaS.

Required extension units:

- `WorkflowSpec`: id, category, platform type, supported intents, input schema, output schema, examples, limits, pricing hints, compliance notes, freshness policy, provider ladder, and result contract.
- `ProviderLadder`: official/public API, provider SDK, internal connector, HTTP extraction, browser/unblocker, authenticated-session fallback, and unsupported reason.
- `WorkflowAdapter`: adapter interface for execution, normalization, artifact capture, provenance, and retry behavior.
- `WorkflowProfile`: versioned self-learning strategy profile with deterministic replay fixtures before promotion.
- `WorkflowUIContract`: generated form controls, defaults, examples, result columns, export modes, and customer-facing copy.
- `WorkflowAPISurface`: stable run/list/detail/result/export/schedule/webhook contracts shared across categories.
- `WorkflowQAGate`: unit, contract, fixture replay, security, cost, trace, eval, and API tests required before a category is accepted.

Extension rules:

- Adding a new category must not require rewriting `BaseActorRunner`, the actor run API persistence model, result packet schema, tenant isolation, billing/cost contracts, graph/vector/artifact memory contracts, or shared QA loop.
- `B3-extensible-workflow-substrate-contract` must be accepted before implementing any new platform category beyond the current Phase 5 base families or adding new category-specific runtime branches.
- Category-specific code must live behind adapter/profile/spec boundaries and register through a catalog/registry path.
- Every new category must start API-first/provider-first and record why each provider tier is used or skipped.
- Every new category must inherit knowledge reuse, freshness, provenance, governance metadata, cost estimation, evals, and trace contracts.
- Every new category must include at least one runnable happy-path fixture, one unsupported/provider-missing fixture, one stale/memory decision fixture when applicable, and one security/data-leakage fixture.
- If a category requires a new shared primitive, add it as a general extension point with tests, not as a one-off branch.

Acceptance test for extensibility:

```text
Can a new platform category be added by creating/registering a WorkflowSpec + adapter/profile/tests, with no core runtime/router/storage rewrite?
```

If the answer is no, the SaaS is not structurally future-proof.

## 10. Knowledge-Backed Runtime Trait

Implement once, inherit everywhere:

```text
KnowledgeBackedActorRunner
  -> normalize tenant, actor, target, intent, schema, freshness requirements
  -> select provider ladder: official/public API -> existing connector/SDK -> HTTP -> browser/unblocker -> authenticated-session gate
  -> exact DB/cache lookup
  -> graph traversal for known entities/sources/runs/fields
  -> vector/semantic lookup for sanitized intent/schema similarity
  -> artifact replay when valid
  -> freshness/provenance/coverage/volatility score
  -> decide serve_cached | serve_cached_and_refresh | partial_refresh | run_fresh | unsupported
  -> execute only missing/stale workflow path
  -> write back canonical rows, graph edges, artifacts, learning events, traces, and provenance
```

Runtime stores:

- Database: canonical runs, result rows, statuses, tenant-scoped cache keys, timestamps, provenance.
- Graph store: actor, base family, tenant namespace, customer query, target, domain, entity, field, run, provider step, source artifact, learning profile, freshness policy.
- Vector/semantic index: sanitized query intent, schema shape, actor metadata, field names, safe content chunks, and summaries.
- Artifact store: immutable source payloads by checksum and retention policy.
- Obsidian/Graphify mirror: audit/navigation only, never hot production serving.

Freshness policy:

```text
freshness_score =
  age_score(actor_family_ttl, field_ttl)
  * source_reliability
  * schema_coverage
  * query_similarity
  * provenance_quality
  * tenant_scope_match
  * entity_volatility_penalty
```

`FreshnessPolicy` must define per-family and per-field floors, ceilings, and clamp rules before multiplication. Hard blockers include tenant mismatch, missing required provenance, unsafe privacy state, unsupported base family, or TTL-expired high-volatility required fields.

Decision thresholds:

```text
>= 0.85 and required fields present: serve_cached
0.60 to 0.85 and required fields present: serve_cached_and_refresh
missing required fields and partial source path known: partial_refresh
< 0.60 or high-volatility required field stale: run_fresh
missing credentials or unsupported base family: unsupported with machine-readable reason
```

Graph traversal must be bounded, deterministic, and cycle-safe:

- Compress strongly connected components before broad traversal.
- Use deterministic seed ordering.
- Use bounded representative path walks.
- Record traversal depth, cutoff reason, and graph snapshot id.

## 11. Multi-Agent Execution Loop

Use a DAG, not a loose todo list. Each packet must include:

```json
{
  "packet_id": "",
  "phase": "",
  "lock_group": "",
  "files_allowed": [],
  "files_locked": [],
  "reuse_decision": "",
  "dependencies": [],
  "acceptance_tests": [],
  "rollback_plan": "",
  "result_packet_path": ""
}
```

### 11.1 Simultaneous Multi-Agent Coding And Gap-Fix Execution

Simultaneous execution is mandatory whenever packet locks do not overlap. Codex must keep the implementation queue moving instead of serializing unrelated work.

Active lane types:

- Codex core lane: owns repository edits, final patch integration, tests, ledgers, release gates, and git authority.
- Claude validation lanes: independent syntax, semantic, business-logic, topology, and fixback review. Use separate prompts/invocations for separate review roles. Claude output is advisory until Codex verifies it against files and tests.
- Python SaaS Guru lanes: bounded implementation research or patch proposals for FastAPI, Pydantic, SQLAlchemy, async runtime, queues, storage, API contracts, tests, pricing, and SaaS mechanics. They cannot mutate canonical files directly unless Codex applies the patch.
- Antigravity observer lane: read-only UI/runtime sanity when explicitly tokened by Codex.
- Jules escalation lane: only for repeated blockers after local and Claude fixback attempts.

Parallel dispatch rules:

- Dispatch independent packets concurrently when their `lock_group` and `files_locked` do not overlap.
- Never allow two coding lanes to mutate the same file or generated artifact at the same time.
- Use read-only research/validation lanes in parallel with coding lanes when they do not require the same mutable lock.
- Keep at least one lane focused on gap discovery while another lane implements accepted packets, unless QA backpressure is active.
- Prefer API-first/provider-first mapping and contract tests before new scrape/browser work.
- Merge order is Codex-owned: smallest proven packet first, then dependent packet, then docs/ledger/result packet update.
- Every lane returns a result packet. No packet is accepted from narrative alone.

Gap-fix loop:

1. Discover gap from tests, parity matrix, Claude review, R&D gate, API/provider ladder, or runtime trace.
2. Classify reuse: `reuse_as_is`, `extend_existing`, `replace_existing`, `new_code_required`, or `defer_or_skip`.
3. Assign lock group and decide whether it can run in parallel.
4. Implement or delegate bounded patch work.
5. Run focused tests and static checks.
6. Submit result packet to Codex QA.
7. If rejected, create fixback packet seeded from Codex-accepted baseline only.
8. Re-run focused tests plus impacted regression gates.
9. Release lock only after accepted, rejected with rollback, superseded, or externally deferred.

One-shot completion stop conditions:

- Stop with `full_saas_release_candidate_ready` only when every mandatory parity gate and every mandatory better-than-Apify superiority gate is implemented, tested, ledgered, and accepted by Codex final QA. Core gates may not be counted as complete through documentation-only deferral.
- Stop with `partial_blocked_not_release_ready` when any mandatory parity or superiority gate remains deferred, externally blocked, unimplemented, untested, or unverifiable. Deferred gates must include evidence and next packet, but they do not satisfy one-shot SaaS readiness.
- Stop with `blocked` only when the same external blocker has survived local fixback, Claude review, and recovery-mode planning, and unrelated packets cannot make meaningful progress.
- Do not stop because a single packet is accepted if dependent or unrelated release-gate packets remain.

Loop sequence:

1. State loop: refresh git/disk/catalog/tests/source docs.
2. Reuse loop: classify existing code and ledger decision.
3. DAG loop: decompose into non-overlapping packets.
4. Implementation loop: extend existing modules first.
5. Knowledge loop: decide memory/cache/fresh execution behavior.
6. QA loop: run focused tests and write result packet.
7. Claude loop: independent syntax/semantic/business/topology/fixback review where needed.
8. Antigravity loop: optional read-only runtime/UI sanity.
9. Fixback loop: rejected packets get priority, accepted-baseline rules, and re-review.
10. Release loop: no completion claim until tests, ledgers, docs, and worktree status are final.

Backpressure:

- Max 6 ordinary active packets.
- One reserved fixback slot outside the cap.
- Second same-lock fixback counts toward the ordinary cap.
- No deferred packet may hold a local implementation lock after the current QA drain pass.
- If recovery-mode packet fails, freeze only that lock group, write a recovery plan, request Claude review, and continue unrelated work.

Performance rule: route small mechanical packets to the fastest reliable local path, reserve larger reasoning passes for Claude/Codex validation, keep browser/UI runs only for packets that need them, and record cost/latency-sensitive choices in the result packet.

## 12. Implementation Phases

Phase A: state seed and existing-code map

- Refresh state artifacts.
- Recompute catalog and base-family counts.
- Build implementation gap matrix from existing code.
- Record reuse decisions.

Phase B: Apify parity gap matrix

- Build `APIFY_WORKFLOWS_EXTERNAL_RND_GAP_MATRIX_YYYY-MM-DD.md`.
- Compare Apify surface, Scraper-app current state, parity target, superiority target, files, tests, and evidence.
- Add an API-first/provider-first gap row before runtime expansion: official/public API, provider SDK, existing connector, HTTP fallback, browser fallback, authenticated-session fallback, and no-greenfield rationale.
- Add an extensible workflow architecture gap row before category expansion: WorkflowSpec, ProviderLadder, WorkflowAdapter, WorkflowProfile, UI/API contracts, QA gates, and no-core-rewrite proof.
- Block all new platform-category packets beyond existing Phase 5 base families until `B3-extensible-workflow-substrate-contract` is accepted.

Phase C: actor runtime/schema hardening

- Extend existing `packages/core/actor_runtime/`.
- Harden `ActorSpec`, provider steps, input schemas, missing-key behavior, unsupported states, and result envelopes.
- Harden provider ladders so API/SDK/connectors are attempted before scrape/browser fallback where feasible.
- Harden category extension points so future workflows register through specs/adapters/profiles/tests instead of core rewrites.

Phase D: knowledge-backed runtime

- Implement `KnowledgeBackedActorRunner` around the existing base runner/provider chain.
- Add DB/cache models and graph/vector/artifact abstractions only through existing project patterns.
- Add freshness policies, decision metadata, partial refresh, background refresh, and replay validation.

Phase E: self-learning strategy profiles

- Record learning events.
- Let AI propose structured strategy patches only.
- Validate with deterministic replay before promotion.
- Version learning profiles and expose policy version in results.

Phase F: API, UI, MCP, and workflow operations

- Extend existing actor API routes and frontend pages.
- Add MCP parity where the existing architecture supports it.
- Add schedules, webhooks, exports, run history, traces, and result views.

Phase G: observability, evals, security, pricing, value proof

- Add trace spans and trace-to-fixture promotion.
- Add OWASP-style AI security tests.
- Add cost/pricing transparency.
- Add dashboards for customer value proof.

Phase H: final release gate

- Run focused actor tests.
- Run broader impacted backend tests.
- Run frontend build if UI/data changed.
- Run secret scan.
- Run Claude validation.
- Update ledgers, phase status, and validation report.
- Codex decides commit readiness.

## 13. Required Result Packet

Every packet writes a JSON or Markdown packet under:

`docs/agent-sync/runtime/result-packets/`

Required fields:

```json
{
  "packet_id": "",
  "lane_id": "",
  "lane_type": "",
  "agent": "",
  "role": "",
  "phase": "",
  "lock_group": "",
  "files_read": [],
  "files_changed": [],
  "parallel_safe": false,
  "lock_conflicts_checked": false,
  "reuse_decision": "",
  "implementation_summary": "",
  "knowledge_decision": null,
  "freshness_policy_version": null,
  "graph_nodes_changed": [],
  "graph_edges_changed": [],
  "vector_records_changed": [],
  "cache_modes_tested": [],
  "tenant_isolation_checked": false,
  "external_rnd_sources_checked": [],
  "apify_parity_gates_checked": [],
  "better_than_apify_gates_checked": [],
  "mcp_parity_checked": false,
  "observability_eval_checked": false,
  "ai_security_checked": false,
  "pricing_cost_checked": false,
  "customer_value_proof_checked": false,
  "tests_run": [],
  "tests_passed": [],
  "tests_failed": [],
  "known_limitations": [],
  "secrets_touched": false,
  "provider_or_live_claims": [],
  "qa_status": "pending_codex_review",
  "next_recommended_packet": ""
}
```

## 14. Validation Commands

Minimum focused actor gate:

```powershell
python -m pytest tests/unit/test_actor_catalog.py tests/unit/test_actor_runtime.py tests/unit/test_actor_families.py tests/unit/test_actor_runs_api.py -q
```

Backend gates by change surface:

```powershell
python -m pytest tests/unit/test_api_execution.py tests/unit/test_api_pagination.py -q
python -m pytest tests/e2e/test_api_e2e.py -q
```

Knowledge-runtime gates to create/run:

```powershell
python -m pytest tests/unit/test_actor_knowledge_memory.py tests/unit/test_actor_freshness_policy.py tests/unit/test_actor_graph_memory.py -q
```

Observability/security/cost gates to create/run:

```powershell
python -m pytest tests/unit/test_actor_traces.py tests/unit/test_actor_evals.py tests/unit/test_actor_ai_security.py tests/unit/test_actor_costs.py -q
```

Frontend gate when `apps/web` or generated web actor data changes:

```powershell
Set-Location apps/web
npm install
npm run build
```

Secret scan:

```powershell
rg -n "(sk-[A-Za-z0-9_-]{20,}|api[_-]?key\\s*=\\s*['\\\"][^'\\\"]+['\\\"]|secret[_-]?key\\s*=\\s*['\\\"][^'\\\"]+['\\\"]|password\\s*=\\s*['\\\"][^'\\\"]+['\\\"])" . -S --glob "!node_modules/**" --glob "!.git/**" --glob "!apps/web/dist/**"
```

Prompt validator if available:

```powershell
if (Test-Path scripts/oneshot/validate_prompt_contract.py) {
  python scripts/oneshot/validate_prompt_contract.py docs/agent-sync/SCRAPER_APP_FINAL_APIFY_COMPETITOR_EXECUTION_PROMPT_2026-06-27.md --write-report
} else {
  Write-Output "PROJECT_PROMPT_VALIDATOR_UNAVAILABLE"
}
```

If the validator is unavailable, run a local structural checklist and record the limitation.

## 15. Acceptance Criteria

Do not claim complete until:

- Existing code reuse is classified and ledgered for every packet.
- Simultaneous execution rules are active: independent non-overlapping packets run in parallel lanes, lock conflicts are checked, and lane result packets are Codex-reviewed before acceptance.
- API-first/provider-first ladder is mapped for each base family before any new scrape/browser implementation is added.
- Extensible workflow substrate is implemented and tested: adding a new platform category must use registered specs/adapters/profiles/tests without rewriting shared runtime/router/storage contracts.
- All 27,753 actors have native runtime classification or explicit unsupported state.
- Runnable actors inherit the native actor runtime and knowledge-backed decision path.
- Apify parity gates are implemented, tested, and accepted; incomplete/deferred parity gates force `partial_blocked_not_release_ready`.
- Better-than-Apify superiority gates are implemented, tested, and accepted; incomplete/deferred superiority gates force `partial_blocked_not_release_ready`.
- Cache, graph, vector, partial refresh, background refresh, run fresh, unsupported, stale, and missing-field paths are tested.
- Graph traversal is bounded, deterministic, and cycle-safe.
- Every customer-visible cached/graph-derived result exposes provenance, freshness, timestamps, policy version, tenant scope, and decision path.
- MCP/agent distribution parity is tested before any agent-platform readiness claim.
- Observability traces and eval-fixture promotion exist before any self-improving platform claim.
- AI security tests cover prompt injection, malicious page instructions, unsafe output handling, excessive agency, tool misuse, denial-of-service, supply chain, and data leakage.
- Cost/pricing controls expose estimated cost, actual cost, cache savings, budget state, quota state, and compute-adjusted margin.
- Customer value proof dashboards exist and pass focused verification; if deferred, the run is not one-shot SaaS ready.
- Focused actor tests pass.
- Broader impacted backend tests pass.
- Frontend build passes if UI/generated actor data changed.
- Secret scan passes.
- Claude validation has no blocking findings or all accepted fixbacks are applied.
- Codex final QA accepts the release candidate and records the decision.

## 16. Final Response Required From Executing Codex

When execution completes or blocks, report:

- state seed path
- task DAG path
- knowledge memory plan path
- external R&D gap matrix path
- packets completed
- files changed
- tests run and results
- Claude validation status
- Antigravity status if used
- Apify parity gates completed/incomplete
- better-than-Apify gates completed/incomplete
- remaining gaps
- git status

This prompt is ready to run only from the existing Scraper-app state. It is not a greenfield build instruction.
