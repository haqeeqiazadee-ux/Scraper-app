# Actor Base Family Taxonomy V2

Generated: 2026-06-23T14:53:22Z

Source catalog: `C:\Users\PC\Scraper-app-fresh\packages\core\actor_catalog\generated\apify_actor_catalog.json`

Total actor entries classified: **27,753**

## Family Counts

| Base family | Actors | Shared base runner | Primary env names | Purpose |
| --- | --- | --- | --- | --- |
| marketplace_product_catalog | 5967 | MarketplaceProductActorBase | KEEPA_API_KEY, SERPER_API_KEY | Amazon/eBay/Walmart/AliExpress/Temu/DHgate/Etsy marketplaces and product search. |
| lead_directory_contacts | 5315 | LeadDirectoryActorBase | SERPER_API_KEY | Business directories, contact extraction, B2B/company/person lead generation. |
| job_board_ats | 2673 | JobBoardActorBase | SERPER_API_KEY | Job boards, ATS pages, careers pages, and hiring lead actors. |
| real_estate_property | 2498 | RealEstateActorBase | SERPER_API_KEY | Property listings, rentals, auctions, foreclosure, agents, and parcels. |
| authenticated_session_scrape | 2194 | AuthenticatedSessionActorBase | ZYTE_API_KEY, CAPSOLVER_API_KEY | Login/cookie/session workflows; explicit, auditable, user-provided sessions only. |
| social_video_media | 1763 | MediaVideoActorBase | SCRAPECREATORS_API_KEY | Video metadata, transcripts, subtitles, media URLs; yt-dlp only after support probe. |
| generic_web_page_extraction | 1528 | GenericWebExtractionActorBase | ZYTE_API_KEY, SERPER_API_KEY | Fallback for static/dynamic web pages when no specialized family applies. |
| browser_render_utility | 1098 | BrowserRenderUtilityActorBase | ZYTE_API_KEY | Screenshots, PDFs, rendered-page capture, link/tech/schema checks. |
| news_content_monitoring | 1076 | NewsContentMonitorActorBase | SERPER_API_KEY | News, blogs, articles, monitoring, content extraction, RSS/sitemap. |
| social_public_data | 818 | SocialPublicDataActorBase | SCRAPECREATORS_API_KEY | Profiles, posts, comments, followers, hashtags, channels, and public social metrics. |
| travel_hospitality | 734 | TravelHospitalityActorBase | SERPER_API_KEY | Hotels, rentals, flights, tours, attractions, and restaurants. |
| document_file_feed_api | 619 | DocumentFeedApiActorBase | none | CSV/XML/JSON feeds, PDFs, public datasets, government/open-data APIs. |
| review_reputation | 359 | ReviewReputationActorBase | SERPER_API_KEY, SCRAPECREATORS_API_KEY | Product, business, app, and social reviews/ratings/comments. |
| no_code_integration_automation | 357 | IntegrationAutomationActorBase | none | Automation/integration actors that take actions rather than scrape data; many should be deferred. |
| ads_marketing_seo_intel | 329 | AdsMarketingIntelActorBase | SERPER_API_KEY, DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD, META_ACCESS_TOKEN | Ad libraries, SEO/SERP, rank tracking, keyword and competitor intelligence. |
| finance_crypto_market_data | 290 | FinanceMarketDataActorBase | none | Stocks, crypto, finance filings/quotes/market data; prefer official/public APIs. |
| local_maps_serp | 85 | LocalSearchMapsActorBase | SERPER_API_KEY, DATAFORSEO_LOGIN, DATAFORSEO_PASSWORD | Google Search, Maps, Places, News, Shopping, and local business discovery. |
| commerce_storefront_generic | 50 | StorefrontCommerceActorBase | none | Shopify, WooCommerce, and generic product/listing pages with public storefront routes. |

## Why This Taxonomy Is The Right Implementation Unit

Do not build 27,753 independent scraper codepaths. Build a small number of durable base runners, then register each actor as a thin `ActorSpec` on top of a base family.

Each `ActorSpec` should define input schema fields, output dataset schema, target resolver, provider chain, required env names, rate limits, credit cost, policy gate, test fixtures, and sample expected output shape.

## Implementation Gate For Every Actor

An actor is not `native-ready` until its base runner exists, providers exist, schemas exist, required env names are present or skipped, the native run endpoint stores results, and tests cover happy path, missing-key path, bad-input path, and degraded-provider path.

## Current Mapping Risk Sample

| Actor | V2 family | Current strategy | Risk |
| --- | --- | --- | --- |
| Twitter Screenshot Generator | browser_render_utility | yt_dlp | current yt_dlp label appears semantically unsafe for non-media actor |
| Avito Cars Details Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| LinkedIn Hiring Leads \| $2.99 / 1k \| | job_board_ats | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Kununu Scraper - Company Ratings & Employer Reviews (DACH) | job_board_ats | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Intermediair.nl Vacatures Scraper | job_board_ats | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Airbnb Phone Number Scraper | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Apex Hali Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Auction.com Scraper — Foreclosures, REO & Auction Listings | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| 🛍️ eBay Product Details Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Website Tech Stack Detector | browser_render_utility | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Athenahealth Product Info Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Shopee Mall Search Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| CraftBeer.com Scraper - Beer Styles, Articles & Recipes | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| 🔍 Facebook Hashtag Search Scraper | social_public_data | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Yellow Pages Email Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Twitter B2b Email Scraper | job_board_ats | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Linkedin B2b Lead Scraper | authenticated_session_scrape | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Douyin 抖音 Profile Scraper - 博主 Followers, Posts & Hashtags | authenticated_session_scrape | yt_dlp | current yt_dlp label appears semantically unsafe for non-media actor |
| IP Geolocation Lookup — Country, City, ISP & VPN Detection | local_maps_serp | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Jora Job Scraper — Search Jobs Across 6 Countries in Seconds | job_board_ats | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Domain.com.au Real Estate Scraper | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Naver Webtoon Scraper | social_public_data | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Agoda Phone Number Scraper | travel_hospitality | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Instagram Related Person Scraper | authenticated_session_scrape | yt_dlp | current yt_dlp label appears semantically unsafe for non-media actor |
| Apartments.com Rentals Scraper — No Login Required | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| OpenStates Legislation Crawler - 50-State Bill Tracker | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| CoinGecko Cryptocurrency Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Benisouk Profile Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| LinkedIn Sales Navigator Scraper - Pay Per Result | authenticated_session_scrape | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| CNN Article Scraper | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Redbubble Email Scraper | lead_directory_contacts | yt_dlp | current yt_dlp label appears semantically unsafe for non-media actor |
| BOVAG Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| StepStone Jobs Scraper | job_board_ats | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| X User Profile Scraper | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Open Library Scraper | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Domain.com.au Property Scraper 📍🏠 - Cheap | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Stubhub Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| AbeBooks Scraper — Rare, Used & Antiquarian Books | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Egyptian Real Estate Scraper | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Imovirtual Property Search Scraper | real_estate_property | real_estate_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| Winston Salem Building Permits | real_estate_property | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Mudah Search Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Zomato Reviews Scraper | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Mercedes-Benz Parts Catalog | marketplace_product_catalog | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| TokyoDev Scraper: Japan Tech Jobs & Companies | job_board_ats | job_board_schema | schema alone is not runtime support; needs base runner, pagination, extraction, tests |
| LinkedIn Contacts Dataset for Demand Generation | browser_render_utility | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Sitemap Health Validator | browser_render_utility | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
| Cars Data API | no_code_integration_automation | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists; may require write/action permissions; defer or require explicit user-approved connector |
| YouTube Lead Scraper | marketplace_product_catalog | yt_dlp | current yt_dlp label appears semantically unsafe for non-media actor |
| World Bank Data Scraper | authenticated_session_scrape | native_pipeline | current native_pipeline label is too broad unless a dedicated base adapter exists |
