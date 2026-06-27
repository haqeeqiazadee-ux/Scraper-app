# Scraper App Apify Workflows Prompt Validation

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Prompt: `docs/agent-sync/SCRAPER_APP_APIFY_WORKFLOWS_SELF_LEARNING_LOOP_PROMPT_2026-06-27.md`

## Verdict

PASS. The prompt is validated as an execution-ready multi-agent, self-learning, self-improving, multi-loop prompt for continuing the Scraper-app own-stack Apify-style workflow implementation.

This verdict applies to prompt readiness only. It is not a claim that the product implementation is complete.

## Local Checks

- Worktree before report creation: prompt file untracked, no other current prompt/report artifacts.
- Reuse gate: `extend_existing`
- Reuse gate evidence: existing actor catalog, generated catalog JSON, actor runtime, actor API tests, frontend actor data, and phase ledgers were detected.
- Project prompt validator: unavailable. `scripts/oneshot/validate_prompt_contract.py` is not present in this checkout.
- Local structural checklist: PASS, 27 checks, 0 missing.
- `git diff --check` on the prompt: PASS.
- Graphify project navigation: unavailable in this checkout. `graphify-out/wiki/index.md` was absent and `graphify` command was not available from the current shell.

## Claude Validation

Claude syntax, semantic, and current-state validation: PASS.

Confirmed evidence:

- Branch: `codex/own-stack-actors`
- HEAD: `2461423885f348ffa21136e16502e5f6b8bb5ef3`
- Phase status: `Phase 5 - Base families B`
- Focused tests present:
  - `tests/unit/test_actor_catalog.py`
  - `tests/unit/test_actor_runtime.py`
  - `tests/unit/test_actor_families.py`
  - `tests/unit/test_actor_runs_api.py`
- Runtime files present:
  - `packages/core/actor_runtime/families.py`
  - `packages/core/actor_runtime/models.py`
  - `packages/core/actor_runtime/provider_chain.py`
  - `packages/core/actor_runtime/runner.py`
- Required prompt-contract sections present: role/authority, routing, source of truth, mutation boundaries, Python-first workflow, performance rules, validation workflow, result packet contract, and Codex final QA/git authority.
- No secret values, live-provider proof claims, Apify runtime execution claims, or product-completion claims were found.

Claude adversarial topology validation: PASS.

Accepted fixbacks applied after Claude review:

- Added one reserved fixback slot outside the 6 ordinary active-packet cap.
- Required a second same-lock fixback to count toward the ordinary active-packet cap.
- Added accepted-baseline rules before fixback dispatch.
- Added accepted-hunk manifest requirement for partial rejected-delta acceptance.
- Added external/HITL lock release after the current QA drain pass.
- Added two-drain-cycle escalation for unresolved external/HITL blockers.
- Added recovery-mode failed-packet exit and minimum recovery-plan fields.
- Added Claude adversarial review when Jules is unavailable for recovery planning.

Claude final topology confirmation: PASS.

Note: Claude CLI returned valid validation responses. Its session-end hook reported a nonblocking hook cancellation after responses were returned.

## Antigravity Validation

Antigravity status: available after connection.

Antigravity read-only sanity pass: PASS.

Confirmed evidence:

- Codex is sole final QA/git authority.
- Claude, Antigravity, Python SaaS Gurus, and Jules are bounded by explicit role limits.
- Antigravity remains observer-only and requires `codex_observer_approval_token.json`.
- Queue, fixback, deferred lock, and baseline-safety rules are present.
- Source-of-truth and mutation boundaries are scoped to `C:\Users\PC\Scraper-app-verified`.
- Python-first workflow, validation commands, and result packet contract are present.
- Proprietary Apify code-copying and Apify runtime execution are banned.
- No required fixes were returned.

## Final Readiness

The prompt is ready to be used as the next execution prompt for the Scraper-app own-stack actor/workflow completion loop.

Before executing it, Codex should start from a fresh state seed and write the runtime state artifacts requested by the prompt under `docs/agent-sync/runtime/`.

## Knowledge-Backed Runtime Update Validation

Date: 2026-06-27

Codex updated the prompt to make the graph/cache/memory mechanism a first-class inherited trait for every runnable actor.

Added requirements:

- `KnowledgeBackedActorRunner` inherited runtime trait.
- Database/cache, graph, vector/semantic index, artifact store, and Obsidian/Graphify audit mirror layers.
- Deterministic freshness decision contract with `serve_cached`, `serve_cached_and_refresh`, `partial_refresh`, `run_fresh`, and `unsupported` modes.
- Per-family and per-field TTL policy.
- Per-factor freshness floor, ceiling, and clamp rules to avoid accidental multiplicative threshold dead zones.
- Explicit hard blockers: tenant mismatch, missing required provenance, unsafe privacy state, unsupported base family, and TTL-expired high-volatility required fields.
- Tenant isolation across cache keys, graph namespaces, vector namespaces, artifacts, learning events, and replay fixtures.
- Bounded graph traversal with SCC compression, deterministic seed ordering, cutoff metadata, and cycle-safe acceptance criteria.
- Knowledge-specific result packet fields and focused test gates.

Local validation:

- `git diff --check` on the prompt: PASS.
- Local knowledge prompt checklist: PASS, 19 checks, 0 missing.
- Local knowledge fixback checklist: PASS, 14 checks, 0 missing.
- Graphify project entrypoint remains unavailable in this checkout: `graphify-out/wiki/index.md` is absent and `graphify` is not available from the current shell.

Claude validation:

- Syntax: PASS.
- Semantics: PASS.
- Business logic: PASS.
- Claude advisory: add freshness factor floors/clamps to avoid threshold dead zones.
- Codex applied the advisory.
- Claude fixback validation: PASS.

Antigravity validation:

- Read-only sanity pass: PASS.
- No required fixes.

Updated readiness:

The prompt remains execution-ready. The knowledge-backed runtime addition is now validated for syntax, semantic integration, business logic, tenant isolation, provenance requirements, bounded graph traversal, deterministic freshness policy, and audit-only Obsidian/Graphify usage.

## External R&D Future-Proof SaaS Update Validation

Date: 2026-06-27

Codex added a current external R&D artifact and integrated it into the execution prompt so the platform targets an AI-native, future-proof Apify competitor rather than only actor-catalog parity.

Added artifact:

- `docs/agent-sync/SCRAPER_APP_APIFY_COMPETITOR_EXTERNAL_RND_2026-06-27.md`

Added prompt requirements:

- External R&D file is listed as secondary prompt context.
- External R&D must be refreshed before major roadmap or superiority claims when older than 60 days.
- Runtime state seed now requires `APIFY_WORKFLOWS_EXTERNAL_RND_GAP_MATRIX_YYYY-MM-DD.md`.
- Section 5B defines Apify parity gates and better-than-Apify superiority gates.
- Phase G requires future-proof SaaS and competitor-grade productization tasks.
- Result packet contract now includes external R&D, Apify parity, superiority, MCP, observability/eval, AI security, pricing/cost, and customer-value proof fields.
- Acceptance criteria now block competitor-grade readiness claims until those gates are implemented, tested, or explicitly marked incomplete with evidence.
- Hard boundary added: Apify R&D source URLs are competitor metadata and documentation references only, not live crawl targets or runtime dependencies.

Local validation:

- `git diff --check` on prompt plus R&D artifact: PASS.
- Local external R&D prompt checklist: PASS, 16 checks, 0 missing.
- Local external R&D fixback checklist: PASS, 6 checks, 0 missing.

Claude validation:

- Syntax: PASS.
- Semantics: PASS.
- Business logic: PASS.
- Competitive logic: PASS.
- Claude advisory: add explicit boundary that Apify R&D URLs are not live crawl targets or runtime dependencies.
- Codex applied the advisory.
- Claude fixback validation: PASS.

Antigravity validation:

- Read-only sanity pass: PASS.
- No required fixes.

Updated readiness:

The prompt remains execution-ready and is now R&D-backed for 2026 SaaS/AI-agent trends, Apify parity, MCP parity, observability/evals, AI security/governance, knowledge-backed reuse, pricing/cost transparency, customer value proof, and no premature better-than-Apify claims.

## Final Execution Prompt Validation

Date: 2026-06-27

Codex created a final run-ready execution prompt that consolidates the existing-state baseline, validated self-learning loop prompt, knowledge-backed runtime design, and external R&D findings.

Added artifact:

- `docs/agent-sync/SCRAPER_APP_FINAL_APIFY_COMPETITOR_EXECUTION_PROMPT_2026-06-27.md`

Final prompt guarantees:

- It starts from the existing `Scraper-app-verified` state and explicitly forbids greenfield rebuilds.
- It requires reuse/extension of the existing actor catalog, actor runtime, actor API, frontend actor data, ledgers, and tests.
- It preserves Codex final QA and git authority.
- It includes Claude, Antigravity, Python SaaS Gurus, and Jules authority boundaries.
- It includes source-of-truth files, mutation boundaries, code execution workflow, Python-first automation, speed/performance rules, validation workflow, and result packet requirements.
- It includes external R&D, Apify parity, better-than-Apify superiority gates, MCP parity, observability/evals, AI security, pricing/cost transparency, customer value proof, and no premature competitor-readiness claims.

Local validation:

- `git diff --check` on final prompt: PASS.
- Local final prompt checklist: PASS, 19 checks, 0 missing.
- Local final prompt fixback checklist: PASS, 9 checks, 0 missing.
- Project prompt validator: unavailable. `scripts/oneshot/validate_prompt_contract.py` is not present in this checkout.

Claude validation:

- Final prompt syntax: PASS.
- Final prompt semantics: PASS.
- Final prompt business logic: PASS.
- Existing-state reuse validation: PASS.
- Claude advisory: add explicit Python-first automation sentence and speed/performance rule.
- Codex applied both advisories.
- Claude fixback validation: PASS.

Antigravity validation:

- Read-only final prompt sanity pass: PASS.
- No required fixes.

Updated readiness:

The final prompt is ready to run from the existing project state. It is not a greenfield build prompt.

## One-Shot SaaS Readiness Fixback

Date: 2026-06-27

Codex re-reviewed the final execution prompt after a user challenge that simultaneous multi-agent, multi-loop coding/gap-fix execution and one-shot SaaS completion were not explicit enough.

Accepted fixbacks applied:

- Added mandatory one-shot SaaS completion mode.
- Added explicit simultaneous multi-agent coding and gap-fix execution section.
- Added lane types for Codex core, Claude validation, Python SaaS Gurus, Antigravity observer, and Jules escalation.
- Added parallel dispatch rules for non-overlapping `lock_group` and `files_locked`.
- Added Codex-owned merge order, QA drain, fixback baseline, and stop conditions.
- Added result packet fields: `lane_id`, `lane_type`, `parallel_safe`, and `lock_conflicts_checked`.
- Added hard stop-state distinction: `full_saas_release_candidate_ready`, `partial_blocked_not_release_ready`, and `blocked`.
- Closed the documentation-deferral loophole: mandatory parity and superiority gates cannot be counted complete through documentation-only deferral.

Local validation:

- `PROJECT_PROMPT_VALIDATOR_UNAVAILABLE` because `scripts/oneshot/validate_prompt_contract.py` is absent in this repo.
- Local checklist confirmed explicit one-shot mode, simultaneous lane rules, API-first provider ladder, lock isolation, QA/fixback/backpressure, result packet lane fields, and non-deferral release criteria.

Claude validation pass 1:

- VERDICT: PASS.
- BLOCKING_FINDINGS: NONE.
- FIXBACKS_REQUIRED: NONE.
- Business risk noted: the prompt allowed deferred mandatory gates to appear compatible with release-candidate status.

Codex fixback after Claude pass 1:

- Updated stop conditions so `full_saas_release_candidate_ready` requires every mandatory parity and better-than-Apify superiority gate to be implemented, tested, ledgered, and accepted by Codex final QA.
- Updated acceptance criteria so incomplete/deferred parity or superiority gates force `partial_blocked_not_release_ready`.
- Updated customer value proof gate so deferral is not one-shot SaaS ready.

Claude validation pass 2:

- VERDICT: PASS.
- BLOCKING_FINDINGS: NONE.
- FIXBACKS_REQUIRED: NONE.
- Business logic risk after fixback: scope magnitude remains high, but the prompt now prevents unsafe release claims and forces honest status if gates are incomplete.

Final validation status:

- PASS for one-shot SaaS execution-prompt readiness.
- This means the prompt is ready to run a single uninterrupted completion campaign with bounded parallel lanes and strict release gates.
- This does not claim the SaaS is already built; the prompt can still truthfully terminate as `partial_blocked_not_release_ready` if implementation gates remain unfinished.

## Extensible Workflow Substrate Fixback

Date: 2026-06-27

Codex re-reviewed the final execution prompt after a user requirement that the SaaS must leave room for adding future workflows for any category of platforms.

Accepted fixbacks applied:

- Added an extensible workflow platform requirement to the final prompt.
- Added a category-agnostic workflow extension substrate to the product target.
- Added `Extensible Workflow Architecture Contract` with required units: `WorkflowSpec`, `ProviderLadder`, `WorkflowAdapter`, `WorkflowProfile`, `WorkflowUIContract`, `WorkflowAPISurface`, and `WorkflowQAGate`.
- Added no-core-rewrite rules for future categories.
- Added a mandatory extensibility acceptance test: a new category must be addable by creating/registering a spec, adapter/profile, and tests without rewriting shared runtime/router/storage contracts.
- Added an extensibility gate to acceptance criteria.
- Added R&D guidance that future categories must register through stable extension points.
- Added gap-matrix row and `B3-extensible-workflow-substrate-contract` DAG packet.

Validation status:

- Local validation: `EXTENSIBILITY_JSON_VALIDATION=PASS`; grep checklist found required extension units and B3 gate references.
- Claude validation pass 1: VERDICT PASS, no blocking findings, no required fixbacks; advisory flagged a timing risk if new category work could start before B3.
- Codex fixback: added a sequencing gate that `B3-extensible-workflow-substrate-contract` must be accepted before any new platform-category packet beyond existing Phase 5 base families.
- Claude validation pass 2: VERDICT PASS, BLOCKING_FINDINGS NONE, FIXBACKS_REQUIRED NONE.
- Final status: accepted Claude-validated extensibility prompt fixback.
