# External R&D V2 - Reusable Actor Families And Provider Strategy

Generated: 2026-06-23T14:53:22Z

## Main Finding

Apify-style scale does not come from 27,753 hand-coded scrapers. It comes from a small set of reusable actor abstractions: typed input schemas, typed dataset/output schemas, shared crawlers/runners, provider-specific adapters, storage/export primitives, and strict run-state tracking. This project should copy that architecture pattern, not Apify's URLs.

## Family-by-Family Decisions

- Marketplace/Product: official/public APIs first: Keepa, eBay Browse, Shopify/WooCommerce storefront APIs, then HTTP DOM, then browser/Zyte.
- Storefront Generic: detect Shopify, WooCommerce, JSON-LD Product, collection pagination, variants, prices.
- Search/Maps/Local: use Serper/DataForSEO before scraping Google pages directly; output should follow LocalBusiness/place shape.
- Social Public Data: official APIs where realistic, ScrapeCreators-style providers otherwise, browser only for public low-volume fallback.
- Media/Transcript: yt-dlp must be support-probed per URL and is not suitable for screenshots or non-media actors.
- Jobs/ATS: use JobPosting schema plus ATS detectors; schemas alone are not runnable workflows.
- Real Estate: requires property/listing family runner for listings, agents, auction/foreclosure fields, geo and pagination.
- Leads/Directories: combine directory crawling, contact extraction, dedupe, validation, enrichment, and strict rate limits.
- Reviews/Reputation: use nested output views or separate datasets for source entity vs reviews.
- Ads/Marketing/SEO: prefer Meta/TikTok/DataForSEO/Serper APIs; key-dependent actors must skip cleanly when missing.
- Browser Utility: screenshots, PDF, rendered HTML, link/schema/tech checks belong to Playwright/Zyte utility base.
- Authenticated Session: separate high-risk family with user-provided cookies/session vault and audit logs.

## Source Register

| Source | URL | Why it matters |
| --- | --- | --- |
| Apify input schema | https://docs.apify.com/platform/actors/development/actor-definition/input-schema/specification/v1 | Actor inputs should be typed, validated, and UI-generating. |
| Apify dataset schema | https://docs.apify.com/platform/actors/development/actor-definition/dataset-schema | Actor outputs should have dataset fields/views. |
| Crawlee Python | https://crawlee.dev/python/docs/quick-start | Reusable HTTP/browser crawler model. |
| Crawlee PlaywrightCrawler | https://crawlee.dev/python/api/class/PlaywrightCrawler | Browser lane for JS-heavy pages after cheaper lanes. |
| Zyte browser automation | https://docs.zyte.com/zyte-api/usage/browser.html | Managed rendering, screenshots, actions, network capture. |
| Serper | https://serper.dev/ | Search, maps, places, videos, shopping, patents, autocomplete. |
| DataForSEO Maps API | https://dataforseo.com/apis/serp-api/google-maps-api | Geo-targeted Maps/local business data. |
| Keepa docs | https://keepaapi.readthedocs.io/en/latest/ | Amazon product/history/deals connector. |
| WooCommerce Store API | https://developer.woocommerce.com/docs/apis/store-api/ | Public store-facing commerce API. |
| WooCommerce Products API | https://developer.woocommerce.com/docs/apis/store-api/resources-endpoints/products/ | Public product data endpoint. |
| eBay Browse API | https://developer.ebay.com/api-docs/buy/browse/static/overview.html | Official item search/detail API. |
| Shopify Product object | https://shopify.dev/docs/api/storefront/latest/objects/Product | Product/variant schema for Shopify storefronts. |
| ScrapeCreators docs | https://docs.scrapecreators.com/ | Public social data provider for 35+ platforms. |
| yt-dlp supported sites | https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md | Media support must be probed; sites break. |
| Meta Ad Library API | https://www.facebook.com/ads/library/api/ | Official ad-library search within policy limits. |
| TikTok Research API | https://developers.tiktok.com/doc/research-api-get-started | Official public-data API with eligibility constraints. |
| Schema.org JobPosting | https://schema.org/JobPosting | Base output schema for jobs. |
| Schema.org LocalBusiness | https://schema.org/LocalBusiness | Base output schema for local/maps actors. |
| Cloudflare Turnstile validation | https://developers.cloudflare.com/turnstile/get-started/server-side-validation/ | CAPTCHA/security validation is server-side and provider-gated. |
| CapSolver Turnstile docs | https://docs.capsolver.com/en/guide/captcha/cloudflare_turnstile/ | External CAPTCHA provider task model. |
| Playwright network/proxy | https://playwright.dev/python/docs/network | Browser/context proxies and network interception. |
| RFC 9309 robots.txt | https://www.rfc-editor.org/info/rfc9309/ | Crawler policy standard. |
| Browserless scraping 2026 | https://www.browserless.io/blog/state-of-web-scraping-2026 | Modern anti-bot relies on fingerprinting and behavioral signals. |
| Browser Use guide 2026 | https://browser-use.com/posts/web-scraping-guide-2026 | Modern scraping mixes APIs, browser automation, and AI extraction. |
