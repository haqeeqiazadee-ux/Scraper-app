# Scraper App Apify Workflows Self-Learning Multi-Agent Completion Prompt

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch at seed time: `codex/own-stack-actors`
Seed HEAD at prompt creation: `2461423885f348ffa21136e16502e5f6b8bb5ef3`
Canonical remote: `https://github.com/haqeeqiazadee-ux/Scraper-app`
Canonical main baseline: `45bdb35dcfd4764500b4b132dde186cedc767455`

## 0. Mission

Build from the current Scraper-app state and deliver a fully functional, AI-powered, own-stack implementation of Apify-style workflows across the existing 27,753 actor catalog.

This is a feature-parity and workflow-parity mission, not a code-copying mission. Apify URLs, actor names, categories, descriptions, and examples are metadata only. Runtime execution must use this platform's native backend stack, existing connectors, native actor runtime, provider chain, AI extraction/classification, database, frontend, public API, and QA gates.

The prompt is execution-ready only after validation. If any validation lane blocks, fix this prompt first, rerun validation, and only then execute.

## 1. Mandatory Roles And Authority

Codex is the mission owner, task router, source-of-truth arbiter, final QA authority, and only git authority. Codex owns the task DAG, lock registry, implementation acceptance, release gates, commit decisions, and final statement of completion.

Claude is the independent research, semantic review, topology review, and fixback lane. Claude may produce findings, patches, or implementation proposals only when Codex delegates a bounded task packet. Claude output is not project truth until Codex accepts it into the repo with tests.

Antigravity is an optional read-only observer and UI/runtime sanity lane. Antigravity cannot edit files, approve code, claim completion, or override Codex. Antigravity may act only on packets in `docs/agent-sync/runtime/ANTIGRAVITY_OBSERVER_QUEUE.jsonl` that contain a Codex-issued observer approval token and an input checksum.

Python SaaS Gurus are optional implementation specialists for backend/FastAPI/Pydantic/SQLAlchemy/async runtime tasks. They receive only bounded packets from Codex, must return patch-level result packets, and have no source-of-truth or git authority.

Jules escalation is reserved for a repeatedly blocked implementation or infrastructure issue after three failed local/fixback attempts. Jules receives a narrow blocker brief only. Jules cannot claim product completion or mutate the canonical repo without Codex acceptance.

## 2. Source Of Truth And Mutation Boundaries

Primary source of truth:

- `C:\Users\PC\Scraper-app-verified`
- Current git branch and HEAD
- Current files on disk
- Existing tests and generated catalog artifacts
- `docs/agent-sync/IMPLEMENTATION_LEDGER.md`
- `docs/agent-sync/PHASE_STATUS.md`
- `docs/agent-sync/CODEX_RELEASE_GATE.md`
- `docs/agent-sync/OWN_STACK_RND_V2/`

Secondary context used to shape this prompt only:

- V5.4 state-seeded loop, roster, certificate, validation, and shared-brain lessons from `C:\Users\PC\yousell-admin` and `C:\Users\PC\second-brain`
- External 2026 SaaS and AI-agent R&D: `docs/agent-sync/SCRAPER_APP_APIFY_COMPETITOR_EXTERNAL_RND_2026-06-27.md`

Hard boundaries:

- Do not copy Apify proprietary implementation code.
- Do not execute through Apify as the runtime backend.
- Do not treat Apify source URLs from external R&D as live crawl targets or runtime dependencies for actor execution. They are competitor metadata and documentation references only.
- Do not add secrets, tokens, API keys, or credential values to code, docs, tests, logs, prompts, or result packets.
- Do not inspect or mutate unrelated repos during execution unless Codex explicitly refreshes the prompt-design context. Future implementation work is confined to `C:\Users\PC\Scraper-app-verified`.
- Do not overwrite user changes. If the worktree is dirty, classify every dirty file before editing.
- Do not claim provider-proof, live-site-proof, database-proof, or full production readiness unless the exact validation command or live check has run and passed.
- Do not serve cached, graph, vector, or Obsidian-derived data as current fact unless the response includes provenance, freshness state, source timestamp, and the decision path that allowed reuse.
- Do not store raw secrets, credentials, session cookies, private customer inputs, or unredacted PII in the graph, vector index, Obsidian/Graphify mirror, learning profiles, prompts, logs, or result packets.
- Do not allow cross-tenant memory bleed. Cache keys, graph namespaces, vector namespaces, artifacts, learning events, and replay fixtures must include tenant/customer isolation where user data is involved.
- Do not claim "better than Apify" or competitor-grade readiness until Apify parity gates and better-than-Apify superiority gates are implemented, tested, and recorded in the release ledger.

## 3. State Seed

Before any implementation, Codex must regenerate the state seed from disk and write:

- `docs/agent-sync/runtime/APIFY_WORKFLOWS_STATE_SEED_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_TASK_DAG_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_LOCKS_YYYY-MM-DD.json`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_QA_QUEUE.jsonl`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_DECISION_LEDGER.jsonl`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_KNOWLEDGE_MEMORY_PLAN_YYYY-MM-DD.md`
- `docs/agent-sync/runtime/APIFY_WORKFLOWS_EXTERNAL_RND_GAP_MATRIX_YYYY-MM-DD.md`

Seed facts observed at prompt creation:

- Phase status: Phase 5 - Base families B
- Phase 1: 27,753 actors generated, backend/frontend routes wired, frontend build passed, secret scan passed, commit `e835a76`
- Phase 2: runtime models, provider chain, base runner, missing-key skip behavior, tests passed, commit `b2396ad`
- Phase 3: native actor run API create/list/detail, blocked non-native execution, missing keys persisted, tests passed, commit `941bc96`
- Phase 4: shared base-family registry/runners, generic, commerce, marketplace, maps, tests and secret scan passed
- Phase 5: job board, real estate, lead, review, and news/content families; direct Phase 5 strategy names allowed; service import aliases; 22 focused tests and 53 regression tests passed; secret scan passed
- Catalog total: 27,753 actors
- Frontend stats route strategies: `native_pipeline` 20,524, `yt_dlp` 3,055, `job_board_schema` 2,483, `real_estate_schema` 1,691
- Runnable totals: `runnable` 20,524 and `runnable_with_schema` 7,229

Current native base-family distribution at prompt creation:

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

State seed commands:

```powershell
git status --short --branch
git log --oneline --decorate -8
git rev-parse HEAD
git rev-parse --abbrev-ref HEAD
python - <<'PY'
from collections import Counter
from packages.core.actor_catalog.registry import actor_catalog
from packages.core.actor_runtime.families import build_actor_spec
actor_catalog.load()
counts = Counter()
for actor in actor_catalog._actors:
    counts[build_actor_spec(actor).base_family.value] += 1
print("total", len(actor_catalog._actors))
for name, count in counts.most_common():
    print(name, count)
PY
```

If PowerShell heredoc syntax is awkward in the active shell, write an equivalent temporary one-liner or use an existing repo script. Do not leave temporary files behind.

## 4. Required Existing-Code Reuse Gate

Every implementation packet starts with reuse classification. Codex must classify the target as exactly one:

- `reuse_as_is`
- `extend_existing`
- `replace_existing`
- `new_code_required`
- `defer_or_skip`

Default expected classification for this mission is `extend_existing`, because the repo already has catalog generation, registry, actor runtime, family runners, API routes, frontend catalog data, tests, and phase ledgers.

Minimum reuse inspection:

```powershell
rg -n "actor_catalog|ActorCatalog|apify_actor_catalog|create_actor_runner|ActorBaseFamily|ProviderChain|RUNNABLE_NATIVE_STRATEGIES" packages services apps tests docs -S
rg --files packages/core/actor_runtime packages/core/actor_catalog services/control-plane/routers apps/web/src apps/web/public/data/actors tests docs/agent-sync
```

Record every packet decision in `docs/agent-sync/IMPLEMENTATION_LEDGER.md` before editing.

## 5. Target Product Shape

The completed system must make the actor catalog feel like a native, AI-powered copy of Apify workflow capabilities while remaining own-stack.

Expected capability layers:

1. Catalog layer
   - Search, filter, category, developer, pricing, stats, detail pages
   - Stable generated data and checksums
   - Actor detail pages with inputs, examples, run history, result previews, and limitations

2. Runtime layer
   - All catalog actors route to a native base family or explicit unsupported state
   - Runnable actors build an `ActorSpec`
   - Provider chain chooses HTTP, smart scraper, browser, search, maps, media, AI extraction, or schema-specific paths
   - Missing credentials skip cleanly with machine-readable diagnostics
   - Results use consistent state, artifacts, logs, usage, cost, and error envelopes

3. AI layer
   - Schema inference from actor metadata and user intent
   - Prompted extraction over fetched pages or search result sets
   - Self-improving field mapping examples stored as non-secret fixtures
   - Guardrails for hallucination: AI may label, normalize, infer schema, and classify; AI must not fabricate source rows

4. Knowledge and memory layer
   - Every runnable actor inherits a knowledge-backed runtime trait that checks prior evidence before running a fresh scrape.
   - Durable memory is layered: database for canonical rows and run history, graph for relationships, vector/semantic index for fuzzy query and schema matching, artifact store for raw fetched payloads by checksum, and Obsidian/Graphify as a human/audit/navigation mirror.
   - Freshness decisions combine timestamp, actor family volatility, schema coverage, query similarity, source reliability, tenant scope, and field-level volatility.
   - The system may serve cached results, serve cached results while refreshing in the background, run partial enrichment, or run the full actor workflow fresh.
   - AI may propose cache/freshness decisions, entity links, schema aliases, and graph traversals, but deterministic policy and replay validation decide whether memory is reused.

5. Workflow layer
   - Synchronous run for small jobs
   - Async run for crawl/search/bulk jobs
   - Retry, resume, cancel, schedule, webhook, and export flows where supported by existing app architecture
   - Per-family templates for ecommerce, marketplace, maps, job, real estate, lead, review, news/content, generic page extraction, and media download metadata

6. UI layer
   - Actor catalog browse and detail pages
   - Actor run form generated from native input schema
   - Live status, logs, result table, artifacts, export, run history
   - Clear disabled/unsupported states with reason and next available route

7. API layer
   - Native actor endpoints remain under existing control-plane patterns
   - Result envelopes match project conventions
   - Tests cover success, unsupported, missing key, validation, pagination, and artifact paths

## 5A. Knowledge-Backed Actor Runtime Trait

Every copied Apify-style actor must inherit a knowledge-first runtime capability. The inherited trait must be implemented once in the native actor runtime and reused by all base-family runners rather than duplicated per actor.

Target trait shape:

```text
KnowledgeBackedActorRunner
  -> normalize intent, target, schema, tenant, and freshness requirements
  -> lookup exact DB/cache matches
  -> traverse graph relationships for known entities, domains, sources, runs, and fields
  -> query semantic/vector memory for fuzzy query and schema similarity
  -> score freshness, provenance, coverage, volatility, and confidence
  -> decide serve_cached | serve_cached_and_refresh | partial_refresh | run_fresh | unsupported
  -> execute only the missing or stale workflow path
  -> write back canonical rows, graph edges, artifacts, learning events, and provenance
```

Runtime stores:

- PostgreSQL or existing database tables: canonical actor runs, result rows, task/run status, tenant-scoped cache keys, freshness timestamps, provenance, and user-visible outputs.
- Graph store: typed relationships between actor, base family, target, domain, entity, field, source artifact, run, customer query, provider step, learning profile, and tenant namespace.
- Vector/semantic index: embeddings for sanitized query intent, schema shape, actor metadata, field names, text chunks, and result summaries.
- Artifact store: immutable raw source payloads such as HTML, JSON, screenshots, extracted documents, and provider responses by checksum and retention policy.
- Obsidian/Graphify mirror: permanent human-readable and agent-readable navigation/audit layer. It may mirror graph snapshots, decisions, and run summaries, but it is not the hot production serving path.

Minimum graph node types:

```text
Actor
BaseFamily
TenantNamespace
CustomerQuery
Target
Domain
Entity
Field
Run
ProviderStep
SourceArtifact
LearningProfile
FreshnessPolicy
```

Minimum graph edges:

```text
Actor -> belongs_to -> BaseFamily
Actor -> produced -> Run
Run -> used_strategy -> ProviderStep
Run -> extracted -> Entity
Entity -> has_field -> Field
Entity -> sourced_from -> SourceArtifact
Target -> belongs_to -> Domain
CustomerQuery -> matched -> Entity
LearningProfile -> improves -> Actor
FreshnessPolicy -> governs -> BaseFamily
TenantNamespace -> owns -> CustomerQuery
TenantNamespace -> owns -> Run
```

Freshness decision contract:

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

`FreshnessPolicy` must define per-family and per-field factor floors, ceilings, and clamp rules before multiplication. A low-but-valid factor may reduce confidence, but it must not accidentally collapse every reusable memory path to zero unless the policy explicitly marks that factor as a hard blocker. Hard blockers include tenant mismatch, missing required provenance, unsafe privacy state, unsupported base family, or a requested high-volatility field whose source timestamp exceeds its TTL.

Decision thresholds:

```text
freshness_score >= 0.85 and required_fields_present:
  serve_cached

0.60 <= freshness_score < 0.85 and required_fields_present:
  serve_cached_and_refresh

missing_required_fields and partial_source_path_known:
  partial_refresh

freshness_score < 0.60 or high_volatility_required_field:
  run_fresh

missing credentials or unsupported base family:
  unsupported with machine-readable reason
```

Default TTL policy must be family-aware and field-aware:

```text
news_content_monitoring: minutes to hours
job_board_schema: hours
review_monitoring_generic: hours to days
commerce_storefront_generic: hours for price/stock, days for title/images
real_estate_schema: hours to days
local_maps_serp: days to weeks
generic_web_page_extraction: configurable by domain
static/company profile pages: weeks to months
```

The runtime must return the decision path with every result:

```json
{
  "knowledge_decision": "serve_cached",
  "freshness_score": 0.91,
  "freshness_state": "fresh",
  "source_timestamps": ["2026-06-27T08:20:00Z"],
  "provenance": ["run_id", "source_artifact_id", "graph_snapshot_id"],
  "refresh_enqueued": false,
  "missing_fields": [],
  "policy_version": "knowledge-policy-v1"
}
```

AI-based logic may rank candidate memories, propose entity links, estimate volatility, map schema aliases, and generate human-readable explanations. AI may not override deterministic freshness thresholds, tenant isolation, provenance requirements, missing-source checks, or replay validation.

Graph traversal rules:

- Never use unbounded path enumeration.
- Compress strongly connected components before broad traversal.
- Use deterministic seed ordering and bounded representative path walks.
- Prefer exact tenant, actor, target, and schema matches before semantic expansion.
- Record traversal depth, cutoff reason, and graph snapshot id in the result metadata.

## 5B. External R&D Future-Proof SaaS Gates

The platform must be shaped by current 2026 SaaS and AI-agent R&D, not only by existing Apify parity. Before major implementation phases, Codex must check whether `docs/agent-sync/SCRAPER_APP_APIFY_COMPETITOR_EXTERNAL_RND_2026-06-27.md` is older than 60 days. If stale, refresh external R&D before making roadmap or superiority claims.

Better-than-Apify is a tested product gate, not marketing language. The execution loop must maintain a gap matrix with:

```text
Apify surface
Scraper-app current state
Scraper-app parity target
Scraper-app superiority target
files to change
tests required
evidence status
```

Required Apify parity gates:

- Actor marketplace/catalog: search, categories, detail pages, examples, pricing metadata, and developer/source metadata.
- Actor execution: input schemas, validation, runs, logs, status, retries, artifacts, datasets/results, exports, and API/SDK access.
- Workflow operations: schedules, webhooks, queues, storage, datasets, key-value style artifacts, rate limits, and usage tracking.
- MCP and AI-agent distribution: MCP tools/resources/prompts, dynamic actor discovery, actor detail inspection, structured output schemas, secure token/OAuth path, telemetry controls, and rate-limit behavior.

Required better-than-Apify superiority gates:

- Knowledge-first runtime: DB/graph/vector/artifact reuse, freshness scoring, partial refresh, background refresh, tenant-safe memory, provenance, and cache-savings reporting.
- Agent observability: trace spans for provider steps, tool calls, AI extraction, memory lookup, graph traversal, freshness decision, result normalization, and failure classification.
- Eval loop: failed or low-confidence production traces become deterministic regression fixtures; recurring failures create fixback packets.
- AI governance: OWASP-style prompt injection, insecure output handling, excessive agency, model/tool denial-of-service, supply-chain, and data leakage tests.
- Cost and pricing intelligence: per-run estimated cost, actual cost, cache savings, budget state, quota state, and compute-adjusted gross margin by base family.
- Customer value proof: dashboards for time saved, successful runs, cache hit savings, data freshness, failure rate, cost per result, and data quality.
- Multi-model/provider routing: route by task complexity, cost, latency, privacy, reliability, and fallback availability.

AI-agent SaaS rules:

- Agent-native UX means workflow orchestration, not a chatbot bolted onto actor runs.
- Every customer-visible result must be explainable through run trace, source artifact, graph/memory decision, freshness policy, and result normalization.
- Every autonomous action must be bounded by tool allowlists, tenant scope, budget limits, data retention policy, and approval rules for high-risk operations.
- Pricing and margin controls must be designed before broad AI-heavy execution paths are enabled.

## 6. Multi-Agent Loop Topology

Codex maintains a DAG, not a loose todo list. Each packet has:

- `packet_id`
- `phase`
- `base_family`
- `files_allowed`
- `files_locked`
- `reuse_decision`
- `implementation_owner`
- `review_owner`
- `qa_owner`
- `dependencies`
- `acceptance_tests`
- `rollback_plan`
- `result_packet_path`

Main loops:

1. State loop
   - Refresh git, disk, catalog counts, phase status, tests, and worktree cleanliness.
   - Stop if source files are missing or expected checksums materially changed.

2. Planner loop
   - Build or update the task DAG.
   - Group by base family and system surface: catalog, runtime, API, UI, tests, docs.
   - Refuse parallel work if lock groups overlap.

3. Implementation loop
   - Extend existing files first.
   - Use Python scripts for repetitive inspection, generation, and validation.
   - Keep patches small enough for independent QA.

4. QA loop
   - Each packet enters the Codex QA queue.
   - Codex runs focused tests, then relevant broader tests.
   - Claude reviews semantic/topology risk when requested.
   - Antigravity observes only UI/runtime tasks with token approval.

5. Knowledge loop
   - Every runtime packet must decide whether actor execution should read from DB, graph, vector memory, artifact replay, or fresh provider/scrape execution.
   - Every accepted run writes back sanitized evidence, graph edges, freshness decisions, and learning events.
   - Failed or low-confidence memory decisions become learning/fixback candidates, not silent runtime behavior changes.
   - Periodically mine accepted learning events into base-family `FreshnessPolicy` and `LearningProfile` updates after replay validation.

6. Fixback loop
   - Rejected packets become priority fixback packets.
   - Fixbacks preserve original lock group and acceptance criteria.
   - Fixbacks re-enter the full maker/checker chain.

7. Learning loop
   - Durable implementation lessons go to `docs/agent-sync/IMPLEMENTATION_LEDGER.md`.
   - Durable cross-agent lessons go to second brain only when explicitly authorized by Codex/user policy.
   - Failed assumptions are recorded as anti-patterns.

8. Release loop
   - A release candidate is not complete until all active packets are accepted, all locks released, all required tests pass, secret scan passes, and git status is intentionally clean or explicitly documented.

## 7. Backpressure, Fixback, And Starvation Rules

The QA queue cap is 6 active packets in `queued`, `in_review`, or `fixback_queued`. Accepted, rejected, superseded, and externally deferred packets do not count after they are written to the decision ledger.

If the queue reaches 6, Codex stops new implementation and drains at least two packets or all packets in the currently blocked lock group before dispatching more work.

Rejected packets leave the active review queue and become `rejected` plus a new `fixback_queued` packet. Fixback packets get a reserved priority slot that can run even when ordinary implementation is paused by backpressure.

One reserved fixback slot sits outside the 6 ordinary active-packet cap. At most two fixback packets for the same lock group may be active at once. Only one fixback packet per lock group may use the reserved slot; a second active fixback for that lock group must claim an ordinary active-packet slot and counts toward the 6 ordinary active-packet cap. Additional fixbacks for that lock group remain pending until one active fixback is accepted, rejected, superseded, or escalated.

Before any fixback starts, Codex must establish the accepted baseline for the lock group. A fixback agent may not silently inherit a rejected delta as its starting point. Codex must either explicitly accept parts of the rejected delta into the baseline, revert the rejected hunks with a reviewed patch, or dispatch the fixback in a clean worktree/workspace seeded from the last Codex-accepted state. If Codex partially accepts rejected delta, Codex must write an accepted-hunk manifest to the decision ledger with file paths, hunk summaries, reason accepted, and tests that cover the accepted hunk. Do not use destructive reset commands without explicit user approval.

Deferred packets must be resolved in the same QA drain pass as one of:

- `deferred_external_or_hITL_lock_released`
- `deferred_nonblocking_lock_released`
- `needs_fixback`

No deferred packet may hold a local implementation lock indefinitely. Downstream dependencies may wait only on an explicit non-local blocker id. Otherwise, locks are released and unrelated work continues.

An external or human-in-the-loop blocker may remain recorded, but it may not keep a local lock after the current QA drain pass. If it remains unresolved after two QA drain cycles, Codex writes an escalation note, keeps the lock released, and resumes only when the external state changes or the user explicitly reactivates that blocker.

If the same lock group is rejected twice, freeze only that lock group, request Claude adversarial review, and continue unrelated queues.

If three active implementation packets fail in one run, enter `qa_recovery_mode`: stop new implementation, run state refresh, run focused tests, classify shared failure root, then resume with one packet only. If the recovery-mode packet fails, freeze that lock group, write a Jules escalation brief if Jules is available and applicable, release unrelated locks, and continue only unrelated packets until Codex accepts a new recovery plan. A new recovery plan must include root cause, accepted baseline, files still locked, next single packet, validation command, stop condition, and review owner. If Jules is unavailable, Codex writes the recovery plan locally and requests Claude adversarial review before resuming that lock group.

## 8. Read-After-Write And Truth Rules

Agents may not treat another unaccepted diff, scratch output, or pass packet as implementation truth.

Allowed truth inputs:

- Committed files
- Current disk files accepted by Codex
- Generated state artifacts written by Codex
- Codex-accepted result packets

Claude fallback must use separate no-session-persistence invocations with distinct role prompts and artifact ids for syntax, semantic, topology, and fixback review. Do not use a single continuing Claude session as multiple independent reviewers.

Antigravity may observe only packets with `codex_observer_approval_token.json`; the token file must include packet id, checksum of input packet, allowed observation surface, and expiry.

## 9. Code Execution Workflow

Use Python-first automation whenever it reduces manual error:

- Generate state seeds and DAGs with Python.
- Parse JSON with Python, not ad hoc string splitting.
- Compute catalog/family coverage with Python.
- Compute cache-key, graph, vector, and freshness-policy coverage with Python.
- Validate graph traversals with strongly connected component compression, bounded walks, and deterministic seed ordering.
- Generate repetitive test fixtures with Python.
- Validate result packet schema with Python.
- Use `rg` for fast code search.

Implementation style:

- Preserve Pydantic v2, FastAPI, async I/O, structlog, and existing route patterns.
- Add or extend protocol/helper abstractions only when they reduce real duplication across base families.
- Prefer existing smart scraper, crawl manager, public API envelopes, runtime models, provider chain, and actor family registry.
- Keep generated data deterministic and stable.
- Keep comments sparse and useful.
- Never hardcode secrets or live credentials.

Performance rules:

- Batch catalog inspections and avoid repeatedly loading 25MB JSON in tight loops.
- Cache actor-family classification inside scripts where safe.
- Keep unit tests focused and fast.
- Mark live/provider tests separately from local deterministic gates.
- Avoid browser runs unless the packet specifically requires browser/UI validation.

## 10. Phase Plan

Phase A: state seed and parity map

- Refresh current phase and git status.
- Recompute catalog total and base family distribution.
- Build actor capability matrix: base family, route strategy, runnable state, required inputs, provider steps, unsupported reason.
- Output: state seed, task DAG, lock file, initial ledger entries.

Phase B: schema and input model hardening

- Ensure each base family exposes an explicit native input schema.
- Normalize examples from catalog metadata into safe test fixtures.
- Add validation for required fields, optional fields, defaults, and unsupported states.
- Output: schema coverage report and focused tests.

Phase C: runtime parity by base family

- Extend runners family by family.
- Generic page extraction must support URL, query, schema, pagination hints, and AI extraction handoff.
- Commerce and marketplace must support product cards, prices, stock/condition, pagination, and export-ready rows.
- Local maps/search must support query/location/result count and clean missing-key behavior.
- Job and real estate must support listing extraction, detail URLs, pagination, and schema-specific fields.
- Lead, review, and news/content must support search/query targeting, extraction, dedupe, and dated/source fields where available.
- Media download/`yt_dlp` must remain metadata-safe and must not create unsafe downloads by default.

Phase D: AI-powered extraction and self-improvement

- Add AI schema inference where the existing architecture supports it.
- Keep AI output grounded in fetched content or explicit input.
- Store learned mappings as deterministic, non-secret fixtures or local config, not hidden chat state.
- Add tests proving no fabricated rows are returned when source content is empty.

Phase E: knowledge-backed runtime memory

- Design and implement the inherited `KnowledgeBackedActorRunner` trait around the existing base runner/provider chain.
- Add database/cache models for tenant-scoped knowledge decisions, source timestamps, provenance, freshness policy versions, and background refresh state.
- Add graph-write and graph-read abstractions for actor, target, domain, entity, field, run, source artifact, provider step, freshness policy, and learning profile nodes.
- Add vector/semantic lookup only for sanitized intent/schema/content summaries. Do not store secrets, raw credentials, unredacted private customer data, or unrestricted PII.
- Add exact-cache, graph-cache, semantic-cache, partial-refresh, background-refresh, and run-fresh decision tests.
- Add family-aware and field-aware TTL policies.
- Add per-factor freshness floor/clamp tests so the multiplicative score does not create accidental threshold dead zones.
- Add result metadata that exposes `knowledge_decision`, `freshness_score`, `freshness_state`, `source_timestamps`, `provenance`, `refresh_enqueued`, `missing_fields`, and `policy_version`.
- Mirror accepted graph snapshots or summaries to Obsidian/Graphify-style files for audit/navigation only when doing so is safe and non-secret.

Phase F: API and UI completion

- Actor run create/list/detail must expose consistent result data, logs, status, artifacts, and errors.
- Actor run responses must expose knowledge decision metadata when the knowledge-backed trait is active.
- Frontend actor pages must show dynamic input forms, run progress, result tables, exports, and unsupported/missing-key states.
- Frontend actor pages must distinguish fresh results, cached results, cached-and-refreshing results, partial-refresh results, and unsupported states.
- Preserve existing design language and avoid marketing-page detours.

Phase G: future-proof SaaS and competitor-grade productization

- Build the Apify parity and better-than-Apify superiority gap matrix from the external R&D file.
- Add MCP parity tasks for dynamic actor discovery, actor detail inspection, structured output schemas, secure token/OAuth path, telemetry controls, and rate-limit behavior.
- Add trace/eval tasks so every actor run can produce spans for provider steps, tool calls, memory lookups, graph traversals, freshness decisions, AI extraction, normalization, and failure classification.
- Add AI security tasks for prompt injection, malicious/untrusted page content, insecure output handling, excessive agency, tool misuse, supply-chain risk, model/tool denial-of-service, and cross-tenant leakage.
- Add cost/pricing tasks for estimated cost, actual cost, cache savings, budget caps, quota state, usage meter, and compute-adjusted gross margin by base family.
- Add customer value proof tasks for dashboards covering time saved, successful runs, cache-hit savings, freshness, failure rate, cost per result, and data quality.
- Add multi-model/provider routing tasks by complexity, cost, latency, privacy, reliability, and fallback availability.

Phase H: final regression and release gate

- Run focused actor tests.
- Run broader backend tests relevant to changed routes.
- Run frontend build when UI/generated data changes.
- Run secret scan.
- Update ledgers and phase status.
- Codex decides commit readiness.

## 11. Validation Commands

Minimum focused gate for actor runtime packets:

```powershell
python -m pytest tests/unit/test_actor_catalog.py tests/unit/test_actor_runtime.py tests/unit/test_actor_families.py tests/unit/test_actor_runs_api.py -q
```

Additional backend gates by change surface:

```powershell
python -m pytest tests/unit/test_api_execution.py tests/unit/test_api_pagination.py -q
python -m pytest tests/e2e/test_api_e2e.py -q
```

Knowledge-backed runtime gates to add and run when implementing the memory trait:

```powershell
python -m pytest tests/unit/test_actor_knowledge_memory.py tests/unit/test_actor_freshness_policy.py tests/unit/test_actor_graph_memory.py -q
```

If these files do not exist yet, the first knowledge-runtime packet must create focused deterministic tests before or alongside implementation.

Frontend gate when `apps/web` or generated actor web data changes:

```powershell
Set-Location apps/web
npm install
npm run build
```

Secret scan gate:

```powershell
rg -n "(sk-[A-Za-z0-9_-]{20,}|api[_-]?key\\s*=\\s*['\\\"][^'\\\"]+['\\\"]|secret[_-]?key\\s*=\\s*['\\\"][^'\\\"]+['\\\"]|password\\s*=\\s*['\\\"][^'\\\"]+['\\\"])" . -S --glob "!node_modules/**" --glob "!.git/**" --glob "!apps/web/dist/**"
```

Prompt validation gate before this prompt is used:

```powershell
if (Test-Path scripts/oneshot/validate_prompt_contract.py) {
  python scripts/oneshot/validate_prompt_contract.py docs/agent-sync/SCRAPER_APP_APIFY_WORKFLOWS_SELF_LEARNING_LOOP_PROMPT_2026-06-27.md --write-report
} else {
  Write-Output "PROJECT_PROMPT_VALIDATOR_UNAVAILABLE"
}
```

If the project validator is unavailable, Codex must run a local structural checklist and record the limitation in the validation report. Claude syntax/semantic/topology passes are still required when Claude CLI is available.

## 12. Result Packet Contract

Every packet returns a result packet under `docs/agent-sync/runtime/result-packets/`.

Required fields:

```json
{
  "packet_id": "",
  "agent": "",
  "role": "",
  "base_family": "",
  "files_changed": [],
  "files_read": [],
  "reuse_decision": "",
  "implementation_summary": "",
  "tests_run": [],
  "tests_passed": [],
  "tests_failed": [],
  "known_limitations": [],
  "secrets_touched": false,
  "provider_or_live_claims": [],
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
  "qa_status": "pending_codex_review",
  "codex_observer_approval_token": null,
  "observer_input_checksum": null,
  "next_recommended_packet": ""
}
```

If Antigravity is used, the result packet must include a Codex observer approval token id and the checksum of the observer input packet. Without both fields, Antigravity output is informational only and cannot support acceptance.

## 13. Acceptance Criteria

The mission can be called complete only when:

- All 27,753 actors have a native runtime classification, explicit runnable/unsupported state, and user-facing reason.
- Every runnable strategy has deterministic local tests.
- Every base family has schema coverage, runtime success tests, missing-key/unsupported tests, and result envelope tests.
- Every runnable actor inherits the knowledge-backed runtime decision path or has a documented reason why memory lookup is bypassed.
- Exact cache, graph cache, semantic cache, partial refresh, cached-and-refreshing, run-fresh, unsupported, stale, and missing-field paths are tested deterministically.
- Cached and graph-derived responses include provenance, freshness state, source timestamps, policy version, tenant scope, and refresh status.
- Graph traversal is bounded, deterministic, and cycle-safe.
- Obsidian/Graphify mirrors are audit/navigation artifacts only and are never the sole production source for customer-visible results.
- The actor API supports create/list/detail and status/result/artifact inspection for native runs.
- The frontend supports browsing, detail, run form, status, result preview, export, and clear failure/unsupported states.
- AI-powered extraction is grounded, tested, and optional when provider keys are unavailable.
- AI-powered memory selection is grounded, tested, optional when provider keys are unavailable, and cannot override deterministic freshness, provenance, tenant-isolation, or replay-validation gates.
- Apify parity gates are implemented or explicitly marked incomplete with file/test evidence.
- Better-than-Apify superiority gates are implemented or explicitly marked incomplete with file/test evidence.
- MCP and AI-agent distribution parity is tested before any AI-agent platform readiness claim.
- Actor observability traces and eval-fixture promotion are implemented before any self-improving platform claim.
- AI security tests cover prompt injection, untrusted page instructions, unsafe output handling, excessive agency, tool misuse, denial-of-service, supply-chain, and data leakage risks.
- Cost/pricing controls expose estimated cost, actual cost, cache savings, budget state, quota state, and compute-adjusted margin by base family.
- Customer value proof dashboards exist or are explicitly deferred with a blocking reason.
- Focused actor tests pass.
- Frontend build passes if UI or generated web data changed.
- Secret scan passes.
- Claude independent validation has no blocking findings or all accepted fixbacks are applied.
- Codex final QA accepts the result and records the decision in the ledger.

## 14. Launch Instruction For The Executing Codex

Start now from `C:\Users\PC\Scraper-app-verified`.

1. Read `AGENTS.md`, `CLAUDE.md`, `docs/agent-sync/PHASE_STATUS.md`, `docs/agent-sync/IMPLEMENTATION_LEDGER.md`, `docs/agent-sync/CODEX_RELEASE_GATE.md`, and `docs/agent-sync/OWN_STACK_RND_V2/`.
2. Run the state seed commands and write the runtime state artifacts.
3. Run the reuse gate and record `extend_existing` or the exact alternative decision.
4. Build the first task DAG from uncovered actor workflow parity gaps, including the knowledge-backed runtime/memory trait and external R&D parity/superiority gap matrix.
5. Execute packets in lock-safe order.
6. Validate after every packet.
7. Use Claude for independent semantic/topology review before any release claim.
8. Keep Antigravity observer-only unless Codex issues a token.
9. Stop and report if a blocker repeats three times or if source state diverges from this prompt enough to invalidate the DAG.

Codex final answer must include:

- state seed path
- task DAG path
- knowledge memory plan path
- external R&D gap matrix path
- packets completed
- files changed
- tests run and results
- Claude validation status
- Antigravity status if used
- git status
- explicit remaining gaps, if any
