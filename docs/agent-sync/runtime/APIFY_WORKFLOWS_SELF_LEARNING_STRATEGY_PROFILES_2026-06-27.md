# Apify Workflows Self-Learning Strategy Profiles

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch: `codex/own-stack-actors`
Packet: `E2-self-learning-strategy-profiles`
Status: `accepted_local_validation_passed`

## Reuse Decision

Decision: `extend_existing`

B3 introduced `WorkflowProfile`, and D1 introduced actor eval/security/trace metadata. E2 extends the existing actor runtime with versioned strategy profiles, sanitized learning events, deterministic replay validation, and guarded promotion. It does not add autonomous runtime patching or hidden model-driven behavior.

## Implemented Units

- `StrategyProfile`: versioned actor/base-family profile with provider order, schema aliases, freshness overrides, replay fixtures, metrics, and policy version.
- `ActorLearningEvent`: tenant-scoped event with redacted payload keys, payload fingerprint, trigger reason, evidence, and metrics.
- `StrategyPatchProposal`: structured strategy patch candidate generated from deterministic event signals.
- `ReplayValidationResult`: deterministic fixture replay gate.
- `StrategyProfileEngine`: builds events, proposes patches, validates replay, and promotes only after replay passes.
- `StrategyProfileStore`: storage protocol for future DB-backed profile persistence.

## Runtime Inheritance

`BaseActorRunner` now has a default strategy profile for every actor spec. Every actor result can expose:

- profile version
- policy version
- provider order
- replay fixture IDs
- profile promoter

When a `strategy_profile_store` is supplied, the runner emits sanitized learning events. Sensitive payload keys are redacted before fingerprinting and recording. Security-risk signals become learning events, not automatic profile promotions.

## Promotion Rule

AI or heuristic logic may propose structured patches, but a strategy profile cannot be promoted unless deterministic replay passes:

- required fixtures must run
- replay errors must be empty
- security blockers must be empty
- score after patch must be at least score before patch

This keeps the self-learning loop reviewable and replay-gated.

## Validation

Commands run:

- `python C:\Users\PC\second-brain\tools\reuse_gate.py --project C:\Users\PC\Scraper-app-verified --task "E2 self-learning strategy profiles" --terms "strategy profile learning event replay promote actor runtime eval fixture"`
- `python -m pytest tests/unit/test_actor_strategy_profiles.py -q`
- `python -m pytest tests/unit/test_actor_runtime.py tests/unit/test_actor_knowledge_memory.py tests/unit/test_actor_traces.py tests/unit/test_actor_evals.py tests/unit/test_actor_runs_api.py tests/unit/test_mcp_actor_tools.py -q`
- `python -m compileall -q packages/core/actor_runtime tests/unit/test_actor_strategy_profiles.py`

Result:

- Reuse gate: `extend_existing`
- Strategy profile tests: `5 passed`
- Impacted runtime/API/MCP tests: `31 passed`
- Compileall: passed

## Remaining Work

E2 implements the safe inherited profile and learning-event substrate. Persisted DB tables, profile-management API endpoints, and production trace-to-fixture queues remain downstream release-readiness work.
