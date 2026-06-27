# Apify Workflows Trace-To-Fixture Promotion

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch: `codex/own-stack-actors`
Packet: `G2-trace-to-fixture-promotion`
Status: `accepted_local_validation_passed`

## Reuse Decision

Decision: `extend_existing`

D1 already adds actor trace, eval, security, and cost metadata. E2 adds replay-gated strategy profiles. G2 extends those primitives with a deterministic fixture-candidate generator so failed, low-confidence, missing-field, or security-risk traces can become regression fixtures without storing secrets.

## Implemented Units

- `RegressionFixtureCandidate`: redacted fixture candidate model with actor/base-family/tenant scope, trace ID, trigger reasons, expected assertions, and tags.
- `build_regression_fixture_candidate(...)`: pure function that converts a qualifying actor result into a deterministic fixture candidate.
- `TraceToFixturePromoter`: small policy wrapper with configurable score threshold.

## Promotion Rules

A fixture candidate is created only when at least one trigger exists:

- actor run failed
- eval score is below threshold
- required fields are missing
- security risk flags are present

Successful high-confidence traces do not create fixture candidates.

## Safety

- Payload keys matching secret/token/cookie/session/password patterns are redacted.
- Fixture IDs are deterministic from actor, tenant, trace, state, provider, sanitized input, and trigger reasons.
- Fixture candidates are data models only. This packet does not auto-write fixtures into the test tree or promote runtime behavior.

## Validation

Commands run:

- `python C:\Users\PC\second-brain\tools\reuse_gate.py --project C:\Users\PC\Scraper-app-verified --task "G2 trace to fixture promotion" --terms "trace fixture promotion eval actor runtime regression low confidence"`
- `python -m pytest tests/unit/test_actor_trace_to_fixture.py -q`
- `python -m pytest tests/unit/test_actor_traces.py tests/unit/test_actor_evals.py tests/unit/test_actor_strategy_profiles.py tests/unit/test_actor_runtime.py -q`
- `python -m compileall -q packages/core/actor_runtime tests/unit/test_actor_trace_to_fixture.py`

Result:

- Reuse gate: `extend_existing`
- Trace-to-fixture tests: `3 passed`
- Impacted trace/eval/profile/runtime tests: `14 passed`
- Compileall: passed

## Remaining Work

G2 creates fixture candidates only. Persisted fixture queues, reviewer approval, automatic fixture file materialization, and CI replay scheduling remain downstream work.
