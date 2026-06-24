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

## Phase 5 Family Key Rules

- `job_board_schema` does not hard-require external keys for direct URL runs.
  Optional discovery/enrichment providers can use search or AI keys in later phases, but missing optional keys must not block direct HTTP/schema extraction.
- `real_estate_schema` does not hard-require external keys for direct URL runs.
  Optional discovery/enrichment providers can use search, maps, proxy, captcha, or AI keys in later phases, but missing optional keys must not block direct HTTP/schema extraction.
- `lead_generation_generic` does not hard-require external keys for direct URL runs.
  Optional `SERPER_API_KEY`, maps, and AI providers may improve discovery/enrichment later; absence should degrade provider choice, not globally skip the family.
- `review_monitoring_generic` does not hard-require external keys for direct URL runs.
  Optional search/maps/AI keys may improve monitoring later; absence should degrade provider choice, not globally skip the family.
- `news_content_monitoring` does not hard-require external keys for direct URL runs.
  Optional search/news discovery keys may improve query-based discovery later; absence should degrade provider choice, not globally skip the family.
