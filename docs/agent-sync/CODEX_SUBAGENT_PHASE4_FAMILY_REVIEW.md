# Codex Subagent Phase 4 Family Review

Reviewer lanes: two read-only Codex explorer subagents.

Scope: Phase 4 base actor families in `C:\Users\PC\Scraper-app-verified`.

## Generic, Commerce, Marketplace Findings

- Reuse `ActorSpec`, `BaseActorRunner`, `ProviderChain`, `ActorCatalog`, and the existing actor API router shell.
- Reuse `HttpWorker.process_task`, `ExecutionRouter`, deterministic extraction, DOM discovery, normalizer, dedup engine, and existing smart/execution extraction helpers.
- For commerce/catalog flows, reuse `ShopifyConnector`, `ApiAdapter`, `KeepaConnector`, `EbayConnector`, `WalmartConnector`, and `HttpCollector`.
- Minimal abstraction should be a small family-runner layer above `BaseActorRunner`:
  - `generic_web_page_extraction`: HTTP worker and existing extraction stack.
  - `commerce_storefront_generic`: Shopify/Woo/API probe, then HTTP fallback.
  - `marketplace_product_catalog`: provider chain by marketplace, with Keepa/eBay/Walmart before generic fallback where safe.

## Local Maps Findings

- Reuse `GoogleMapsConnector.search_businesses()` for Serper Places, Google Places, and browser fallback.
- `local_maps_serp` should have no hard-required key because browser fallback is keyless.
- Optional provider env vars:
  - `SERPER_API_KEY`
  - `GOOGLE_MAPS_API_KEY`
- Missing Serper/Google keys must not skip a local maps actor; provider should degrade to `maps_browser_fallback`.

## Codex Response

- Added `packages/core/actor_runtime/families.py`.
- Added base-family mapping and runners for:
  - `generic_web_page_extraction`
  - `commerce_storefront_generic`
  - `marketplace_product_catalog`
  - `local_maps_serp`
- Rewired `services/control-plane/routers/actors.py` to use shared family `build_actor_spec()` and `create_actor_runner()`.
- Added tests for family dispatch, Shopify connector reuse, Keepa missing-key skip, maps provider order, maps browser fallback, Serper preference, and actor API persistence for local maps.
