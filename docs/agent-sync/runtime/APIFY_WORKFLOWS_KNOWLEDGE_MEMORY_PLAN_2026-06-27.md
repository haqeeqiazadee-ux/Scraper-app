# Apify Workflows Knowledge Memory Plan

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Reuse decision: `extend_existing`

## Existing-State Rule

Implement knowledge-backed behavior as an inherited trait around the current actor runtime. Do not replace the existing `packages/core/actor_runtime` package, actor catalog, or actor run API.

## Proposed Runtime Trait

`KnowledgeBackedActorRunner` should wrap or extend the existing `BaseActorRunner` path and preserve current `ActorSpec`, `ProviderStep`, `ProviderChain`, `ActorRunState`, and `ActorRuntimeResult` behavior.

Decision modes:

- `serve_cached`
- `serve_cached_and_refresh`
- `partial_refresh`
- `run_fresh`
- `unsupported`

## Store Layers

1. Database/cache: tenant-scoped runs, rows, timestamps, provenance, policy version, cache decision.
2. Graph store: actor, base family, tenant namespace, target, domain, entity, field, run, provider step, source artifact, freshness policy, learning profile.
3. Vector/semantic index: sanitized intent/schema/content summaries only.
4. Artifact store: immutable source payloads by checksum and retention policy.
5. Obsidian/Graphify mirror: audit/navigation only, not production serving.

## First Implementation Packet

`B1-knowledge-runtime-contract-tests`

Add deterministic tests first:

- `tests/unit/test_actor_knowledge_memory.py`
- `tests/unit/test_actor_freshness_policy.py`
- `tests/unit/test_actor_graph_memory.py`

Expected first tests:

- existing actor runner still runs without knowledge profile
- exact fresh cached result returns `serve_cached`
- stale cache returns `serve_cached_and_refresh` or `run_fresh` by policy
- missing required fields returns `partial_refresh`
- tenant mismatch is a hard blocker
- missing provenance is a hard blocker
- graph traversal uses bounded depth/cutoff metadata
- freshness factor floors/clamps avoid accidental zeroing

## Guardrails

- AI can propose strategy/profile changes only.
- Deterministic replay validates before promotion.
- Tenant mismatch, missing provenance, unsafe privacy state, unsupported base family, and TTL-expired high-volatility fields are hard blockers.
- Cached or graph-derived customer-visible results must include provenance, freshness state, source timestamps, policy version, tenant scope, and decision path.
