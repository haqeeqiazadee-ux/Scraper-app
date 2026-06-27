# API-First Provider Ladder Map

Date: 2026-06-27
Packet: `B2-api-first-provider-ladder-map`

## Rule

Every actor family must prefer official/public APIs, provider SDKs, existing platform connectors, and internal APIs before HTTP scraping, browser automation, hard-target lanes, or new scrape code. Apify URLs remain metadata only and are not runtime providers.

## Current Catalog Evidence

- Catalog actors loaded: 27,753
- Current route strategies:
  - `native_pipeline`: 20,524
  - `yt_dlp`: 3,055
  - `job_board_schema`: 2,483
  - `real_estate_schema`: 1,691

## Provider Ladder By Current Runtime Family

| Family | Actors | Provider ladder | Status |
|---|---:|---|---|
| `commerce_storefront_generic` | 2,357 | `shopify_products_json` (`official_public_api`) -> `http_worker` (`http_extraction`) | API-first mapped |
| `local_maps_serp` | 679 | `serper_places` (`provider_sdk`) -> `google_places` (`official_public_api`) -> `maps_browser_fallback` (`browser_unblocker`) | API/provider-first mapped |
| `marketplace_product_catalog` | 1,165 | Amazon: `keepa` (`provider_sdk`, `KEEPA_API_KEY`); non-Amazon: `http_worker` (`http_extraction`) | Partial; more marketplace APIs/connectors need mapping |
| `generic_web_page_extraction` | 4,840 | `http_worker` (`http_extraction`) | No stable generic API; HTTP fallback explicit |
| `job_board_schema` | 2,483 | `http_worker_schema_match` (`http_extraction`) | Partial; ATS/platform APIs still need future mapping |
| `real_estate_schema` | 1,691 | `http_worker_schema_match` (`http_extraction`) | Partial; property platform APIs still need future mapping |
| `lead_generation_generic` | 7,268 | `http_worker_contacts` (`http_extraction`) | Partial; provider/API enrichment ladders still need future mapping |
| `review_monitoring_generic` | 2,768 | `http_worker_reviews` (`http_extraction`) | Partial; official review APIs still need future mapping |
| `news_content_monitoring` | 1,447 | `http_worker_content_monitoring` (`http_extraction`) | Partial; RSS/feed/news APIs still need future mapping |
| `yt_dlp` | 3,055 | `unsupported_route_strategy` (`unsupported`) | Explicit unsupported own-stack ladder until mapped |

## Implementation Evidence

- `ProviderTier` now records provider type on every `ProviderStep`.
- Current supported tiers: `official_public_api`, `provider_sdk`, `internal_connector`, `http_extraction`, `browser_unblocker`, `authenticated_session`, `unsupported`.
- Provider steps now carry `connector` and `rationale`.
- `build_actor_spec(...)` emits tiered ladders for every current runtime family and explicit unsupported ladders for unmapped route strategies.

## Remaining Gaps

- Marketplace non-Amazon needs provider-first mapping for eBay/Walmart/AliExpress/Temu-style connectors.
- Job boards need ATS/platform API ladder discovery.
- Real estate needs property platform and feed/API ladders.
- Leads/reviews/news need provider/API enrichment ladders.
- `yt_dlp` route needs own-stack social/media provider-ladder mapping before it can be called native runnable.

## Gate

No new scrape/browser implementation is accepted unless its result packet proves:

1. official/public API unavailable or insufficient;
2. provider SDK unavailable or insufficient;
3. existing connector unavailable or insufficient;
4. internal API unavailable or insufficient;
5. HTTP/browser fallback is the narrowest safe path;
6. unsupported status is machine-readable when no safe own-stack path exists.
