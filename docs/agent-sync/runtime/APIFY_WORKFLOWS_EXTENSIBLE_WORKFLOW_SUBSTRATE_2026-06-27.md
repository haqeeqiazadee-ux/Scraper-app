# Apify Workflows Extensible Workflow Substrate

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch: `codex/own-stack-actors`
Packet: `B3-extensible-workflow-substrate-contract`
Status: `accepted_local_validation_passed`

## Reuse Decision

Decision: `extend_existing`

The existing actor runtime already has shared `ActorSpec`, `ProviderStep`, `BaseActorRunner`, actor API endpoints, knowledge-memory hooks, and governance metadata. B3 extends that shared runtime with a category-agnostic workflow contract instead of adding a parallel platform stack or rewriting router/storage foundations.

## Extension Units

- `WorkflowSpec`: canonical contract for a new workflow category or platform.
- `ProviderLadder`: ordered API-first/provider-first execution ladder built from existing `ProviderStep` metadata.
- `WorkflowAdapter`: adapter protocol for workflow execution and output normalization.
- `WorkflowProfile`: versioned strategy/profile metadata for promotion and fixture replay.
- `WorkflowUIContract`: UI form/result/export contract for future frontend generation.
- `WorkflowAPISurface`: stable public API endpoint contract inherited by future workflows.
- `WorkflowQAGate`: mandatory QA gate set covering unit, contract, fixture replay, security, cost, trace, eval, and API checks.
- `WorkflowRegistry`: runtime registry that rejects duplicate workflow IDs and categorizes workflow specs.

## No-Core-Rewrite Proof

The test fixture defines a synthetic future platform category:

- Category: `health_devices`
- Platform type: `wearable_device_api`
- Provider ladder: official public API first, user-authorized HTTP export second
- Inherited API run endpoint: `/api/v1/actors/{actor_id}/runs`
- Inherited freshness policy: tenant-isolated by default
- Inherited export modes: JSON and CSV
- Required rewrite flags: all false

The registry accepts the workflow only when it passes `WorkflowSpec.assert_extension_safe()`. A separate regression verifies that core runtime rewrites and incomplete QA gates are rejected.

## API-First Rule

Every new workflow category must provide a mapped `ProviderLadder` before registration. The ladder is expected to rank official public APIs, provider SDKs, and existing internal connectors ahead of HTTP extraction, browser unblockers, or authenticated sessions. Unsupported or unmapped routes must be explicit, not silently treated as scrape-ready.

## Validation

Commands run:

- `python C:\Users\PC\second-brain\tools\reuse_gate.py --project C:\Users\PC\Scraper-app-verified --task "B3 extensible workflow substrate contract" --terms "WorkflowSpec workflow registry extensible platform category actor runtime"`
- `python -m pytest tests/unit/test_workflow_extension_contract.py tests/unit/test_actor_provider_ladder.py tests/unit/test_actor_runtime.py -q`
- `python -m compileall -q packages/core/actor_runtime tests/unit/test_workflow_extension_contract.py`

Result:

- Reuse gate: `extend_existing`
- Focused tests: `15 passed`
- Compileall: passed

## Remaining Work

B3 proves the substrate contract and extension gate. It does not implement concrete future-platform adapters, generated UI rendering from workflow specs, or full production release readiness. Those remain downstream packets after the substrate is accepted.
