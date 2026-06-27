# Blocker-Closure Prompt Validation

Date: 2026-06-27
Prompt: `docs/agent-sync/SCRAPER_APP_BLOCKER_CLOSURE_ONE_SHOT_EXECUTION_PROMPT_2026-06-27.md`
Verdict: `validated_claude_pass`

## Local Checks

- Graphify: `GRAPHIFY_ABSENT`
- Reuse gate: `extend_existing`
- Project validator: `PROMPT_VALIDATOR_ABSENT`
- Local required-section check: `PASS`
- Markdown whitespace check: `PASS`
- Claude read-only validation: `PASS`
- Required blockers included:
  - `F2-workflow-ops-parity`
  - `E3-persisted-profile-apis`
  - `G3-fixture-review-materialization`
  - `G4-customer-value-dashboards`
  - `U1-apify-grade-ui-product-design`
  - `P1-actor-proof-factory-27753`
  - `H1-full-e2e`
  - `H2-deployment-verification`

## Validation Scope

This validation checks prompt syntax, semantic completeness, execution order, blocker coverage, role assignment, task delegation, guardrails, Python-first workflow, speed/performance workflow, UI/product-design workflow, validation workflow, and Codex final QA authority.

## Claude Validation Summary

Claude returned `PASS` with zero blocking findings after the UI/product-design update and the actor proof-factory fixback. It validated syntax, semantics, business logic, execution order, blocker coverage, role assignment, guardrails, Python-first workflow, validation workflow, and false one-shot prevention.

Claude specifically confirmed the prompt now has eight blocker packets in DAG order: `F2`, `E3`, `G3`, `G4`, `U1`, `P1`, `H1`, and `H2`.

For the UI/product-design requirement, Claude confirmed that `U1-apify-grade-ui-product-design` explicitly requires Claude to use design-review skills across information architecture, visual hierarchy, interaction design, accessibility, responsive layout, operational-console ergonomics, and competitive benchmark critique. Claude also confirmed the prompt forbids claiming "better than Apify" without implemented UI changes, evidence, and a no-blocking-finding Claude design validation.

## Strict One-Shot Execution Validation

Claude strict verdict: `ONE_SHOT_EXECUTION_READY`.

Claude validated the prompt as ready to finish the remaining SaaS blockers from the existing project state, not as a from-scratch rebuild. The strict pass covered:

- all remaining blocker packets included
- coherent priority order and acyclic DAG
- simultaneous multi-agent and continuous multi-loop execution workflow
- API-first/non-Apify-runtime guardrails
- mandatory Claude UI/product-design role
- mandatory proof factory for converting catalog/UI/API mapped actors into individually verified workflow proof states
- existing-code reuse gate
- result packet, lock, and ledger requirements
- validation commands and completion states that prevent false readiness claims
- honest handling of external blockers

## Actor Proof-Factory Fixback

Codex updated the prompt after the user correctly challenged that catalog/UI/API mapping is not individual E2E proof.

Added non-deferrable packet: `P1-actor-proof-factory-27753`.

New proof-factory requirements:

- durable per-actor proof ledger
- explicit proof levels: `catalog_only`, `api_mapped`, `runtime_smoke_passed`, `fixture_replay_passed`, `ui_route_passed`, `live_e2e_passed`
- generated per-actor test inputs
- resumable batch runner with concurrency, retries, rate limits, and status reporting
- API run, result, and export proof
- UI route proof
- deterministic fixture proof separated from live E2E proof
- failure classification and self-improvement loop
- proof dashboard and per-actor UI proof status
- forbidden claim against "27,753 individually proven E2E workflows" unless the proof ledger equals the current catalog count and every actor is `live_e2e_passed`

Claude pass 1 returned `BLOCKING` because one continuous-loop sentence still said "seven blocker packets" after P1 was added.

Codex fixed the stale count to "eight blocker packets".

Claude pass 2 returned:

```text
VERDICT: PASS
BLOCKERS: NONE
FIXBACKS: NONE
```

## Output Discipline Fixback

Codex added a mandatory guardrail prohibiting unnecessary execution text. The prompt now requires only necessary status, blockers, decisions, validation results, artifact paths, and final required output.

Claude read-only validation returned:

```text
VERDICT: PASS
BLOCKERS: NONE
```

## H1/P1 Implementation Validation

Claude read-only validation was rerun after the P1 implementation and H1 local fixback.

Claude returned:

```text
VERDICT: PASS
BLOCKERS: None
FIXBACKS: H1 execution and smart_scrape recovery confirmed; Trustpilot fallback confirmed source-level only.
```

Claude also confirmed the prompt still contains the required output discipline, API-first rule, proof factory, UI parity, deployment, live E2E gates, role assignments, eight-packet DAG, and forbidden false one-shot-ready claims.

## Limitation

The project-level validator required by the prompt protocol was not present at `scripts/oneshot/validate_prompt_contract.py`, so validation used the documented fallback path: local checklist, `git diff --check`, and Claude read-only validation.
