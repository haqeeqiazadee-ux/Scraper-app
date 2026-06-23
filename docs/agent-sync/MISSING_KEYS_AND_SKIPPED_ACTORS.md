# Missing Keys And Skipped Actors

Do not store secret values in this file. Store env var names only.

## Rule

If an actor/workflow requires an external API key that is not configured:

1. Mark only that actor/workflow as `skipped_missing_key`.
2. Record actor ID, title, base family, missing env var name, and date.
3. Continue to the next actor/workflow.

## Entries

No skipped actors recorded yet.

## Phase 4 Family Key Rules

- `marketplace_product_catalog` for Amazon actors requires `KEEPA_API_KEY`.
  If the key is absent, the affected actor run is persisted as `skipped_missing_key` with `missing_env_names=["KEEPA_API_KEY"]`.
- `local_maps_serp` does not hard-require `SERPER_API_KEY` or `GOOGLE_MAPS_API_KEY`.
  Missing maps provider keys degrade to `maps_browser_fallback` and do not skip the actor.
- `commerce_storefront_generic` does not hard-require external keys for Shopify `/products.json`.
- `generic_web_page_extraction` does not hard-require external keys.
