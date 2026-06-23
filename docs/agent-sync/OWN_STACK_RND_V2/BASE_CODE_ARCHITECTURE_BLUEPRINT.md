# Base Code Architecture Blueprint V2

Generated: 2026-06-23T14:53:22Z

## Target Architecture

```text
ActorCatalog UI
  -> ActorSpec registry
    -> ActorRunService
      -> Base runner by family
        -> Provider chain: official/public API -> HTTP -> browser/unblocker -> authenticated session gate
          -> Normalizer/Pydantic schema
            -> tasks/runs/results/artifacts/export
```

## Core Interfaces To Add

### ActorSpec

Fields: `actor_id`, `slug`, `title`, `base_family`, `input_schema`, `output_schema`, `required_env_names`, `optional_env_names`, `provider_chain`, `default_limits`, `credit_policy`, `skip_policy`, `compliance_notes`, `tests`.

### BaseActorRunner

Methods: `validate_input`, `resolve_targets`, `check_requirements`, `execute`, `normalize`, `persist`, `export`. It returns `ready`, `skipped_missing_key`, `blocked_policy`, `provider_degraded`, `failed`, or `succeeded`.

### Missing-Key Clause

If a workflow needs an external key that is not configured, Claude/Codex must mark only that actor/spec as `skipped_missing_key`, record the env var name and actor ID in `docs/agent-sync/MISSING_KEYS_AND_SKIPPED_ACTORS.md`, continue with the next actor, never invent live keys, and never print or commit secret values.

## Build Order

1. Lock repo provenance: use `C:\Users\PC\Scraper-app-verified` or a fresh clone of `haqeeqiazadee-ux/Scraper-app`; never commit to `yousell-admin`.
2. Review and preserve useful `saas-repair` catalog/UI files.
3. Add `packages/core/actor_runtime/` with `ActorSpec`, `BaseActorRunner`, `ProviderChain`, and family registry.
4. Add first base families: `generic_web_page_extraction`, `marketplace_product_catalog`, `commerce_storefront_generic`, `local_maps_serp`.
5. Add social/media with provider gates and strict missing-key skip behavior.
6. Add jobs, real estate, lead directories, reviews, and content monitoring.
7. Add browser utility, authenticated session, and integration automation last because they have higher compliance and permission risk.
8. Wire `POST /api/v1/actors/{actor_id}/runs` and UI Run button only after a family runner passes tests.
9. Promote actors family-by-family: `cataloged` -> `family-ready` -> `adapter-ready` -> `native-ready` -> `live-verified`.

## Acceptance Criteria

- Apify URLs remain metadata only; native Run calls this platform's backend.
- Catalog count remains 27,753.
- Every actor has a base family and clear state.
- Missing keys do not stop the overall run plan.
- Tests prove shared runner behavior before bulk actor status is upgraded.
