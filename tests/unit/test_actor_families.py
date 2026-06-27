from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from packages.core.secrets import SecretsManager


class EmptySecrets:
    def get(self, key: str, default: str | None = None) -> str | None:
        return default


def _entry(**overrides: Any) -> SimpleNamespace:
    base = {
        "actor_id": "actor-1",
        "name": "generic-scraper",
        "title": "Generic Scraper",
        "description": "Scrape a public web page.",
        "categories": ("AUTOMATION",),
        "route_strategy": "native_pipeline",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_build_actor_spec_maps_shopify_storefront_family_without_required_keys() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            name="shopify-store-scraper",
            title="Shopify Store Scraper",
            description="Extract products from Shopify storefront products.json.",
            categories=("ECOMMERCE", "AUTOMATION"),
        )
    )

    assert spec.base_family == ActorBaseFamily.COMMERCE_STOREFRONT_GENERIC
    assert spec.required_env_names == ()


def test_build_actor_spec_maps_amazon_marketplace_family_with_keepa_required_key() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            name="amazon-product-search-scraper",
            title="Amazon Product Search Scraper",
            description="Extract Amazon products, prices, ranks, and reviews.",
            categories=("ECOMMERCE",),
        )
    )

    assert spec.base_family == ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG
    assert spec.required_env_names == ("KEEPA_API_KEY",)


def test_build_actor_spec_maps_local_maps_family_with_optional_provider_keys() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            name="google-maps-business-scraper",
            title="Google Maps Business Leads Scraper",
            description="Find local businesses, addresses, ratings, websites, and phone numbers.",
            categories=("LEAD_GENERATION", "BUSINESS"),
        )
    )

    assert spec.base_family == ActorBaseFamily.LOCAL_MAPS_SERP
    assert spec.required_env_names == ()
    assert "SERPER_API_KEY" in spec.optional_env_names
    assert "GOOGLE_MAPS_API_KEY" in spec.optional_env_names
    assert [step.name for step in spec.provider_chain] == [
        "serper_places",
        "google_places",
        "maps_browser_fallback",
    ]


def test_build_actor_spec_does_not_treat_leading_as_lead_generation() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            name="avito-cars-details-scraper",
            title="Avito Cars Details Scraper",
            description="Extract vehicle listing data from Morocco's leading classifieds platform.",
            categories=("AUTOMATION", "DEVELOPER_TOOLS", "OTHER"),
        )
    )

    assert spec.base_family == ActorBaseFamily.GENERIC_WEB_PAGE_EXTRACTION


def test_build_actor_spec_maps_job_board_strategy_to_schema_family() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            route_strategy="job_board_schema",
            name="linkedin-jobs-scraper",
            title="LinkedIn Jobs Scraper",
            description="Extract job postings with titles, companies, salaries, and apply URLs.",
            categories=("JOBS", "LEAD_GENERATION"),
        )
    )

    assert spec.base_family == ActorBaseFamily.JOB_BOARD_SCHEMA
    assert spec.required_env_names == ()
    assert [step.name for step in spec.provider_chain] == ["http_worker_schema_match"]
    assert "title" in spec.output_schema["properties"]
    assert "company_name" in spec.output_schema["properties"]


def test_build_actor_spec_maps_real_estate_strategy_to_schema_family() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    spec = build_actor_spec(
        _entry(
            route_strategy="real_estate_schema",
            name="auction-com-property-scraper",
            title="Auction.com Property Scraper",
            description="Extract distressed property listings, prices, addresses, beds, and baths.",
            categories=("REAL_ESTATE", "LEAD_GENERATION"),
        )
    )

    assert spec.base_family == ActorBaseFamily.REAL_ESTATE_SCHEMA
    assert spec.required_env_names == ()
    assert [step.name for step in spec.provider_chain] == ["http_worker_schema_match"]
    assert "price" in spec.output_schema["properties"]
    assert "address" in spec.output_schema["properties"]


def test_build_actor_spec_maps_lead_review_and_news_native_families() -> None:
    from packages.core.actor_runtime.families import ActorBaseFamily, build_actor_spec

    lead = build_actor_spec(
        _entry(
            name="shopify-lead-scraper",
            title="Shopify Lead Scraper",
            description="Extract business contact emails, phones, and websites for prospecting.",
            categories=("LEAD_GENERATION", "BUSINESS"),
        )
    )
    review = build_actor_spec(
        _entry(
            name="trustpilot-reviews-scraper",
            title="Trustpilot Reviews Scraper",
            description="Extract company reviews, ratings, reviewer names, and dates.",
            categories=("LEAD_GENERATION", "ECOMMERCE"),
        )
    )
    news = build_actor_spec(
        _entry(
            name="cnn-article-scraper",
            title="CNN Article Scraper",
            description="Extract news articles, headlines, authors, dates, and article body.",
            categories=("NEWS",),
        )
    )

    assert lead.base_family == ActorBaseFamily.LEAD_GENERATION_GENERIC
    assert [step.name for step in lead.provider_chain] == ["http_worker_contacts"]
    assert review.base_family == ActorBaseFamily.REVIEW_MONITORING_GENERIC
    assert [step.name for step in review.provider_chain] == ["http_worker_reviews"]
    assert news.base_family == ActorBaseFamily.NEWS_CONTENT_MONITORING
    assert [step.name for step in news.provider_chain] == ["http_worker_content_monitoring"]


def test_commerce_storefront_runner_uses_shopify_connector() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import CommerceStorefrontGenericRunner, build_actor_spec

    class FakeShopifyConnector:
        async def get_store_products(self, store_url: str, limit: int = 50, collection: str | None = None) -> list[dict]:
            assert store_url == "https://example.myshopify.com"
            assert limit == 2
            return [{"name": "Hat", "price": "19.00", "source": "shopify_products_json"}]

        async def close(self) -> None:
            pass

    runner = CommerceStorefrontGenericRunner(
        build_actor_spec(
            _entry(
                title="Shopify Store Scraper",
                description="Extract Shopify products.",
                categories=("ECOMMERCE",),
            )
        ),
        task_id="task-1",
        tenant_id="tenant-1",
        shopify_factory=FakeShopifyConnector,
    )

    result = asyncio.run(
        runner.run({"target": "https://example.myshopify.com", "max_results": 2})
    )

    assert result.state == ActorRunState.SUCCEEDED
    assert result.output["item_count"] == 1
    assert result.output["extracted_data"][0]["source"] == "shopify_products_json"
    assert result.provider == "shopify_products_json"


def test_marketplace_runner_skips_missing_keepa_key_without_execute() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import MarketplaceProductCatalogRunner, build_actor_spec

    runner = MarketplaceProductCatalogRunner(
        build_actor_spec(
            _entry(
                title="Amazon Product Search Scraper",
                description="Extract Amazon product listings.",
                categories=("ECOMMERCE",),
            )
        ),
        task_id="task-1",
        tenant_id="tenant-1",
        secrets_manager=EmptySecrets(),
    )

    result = asyncio.run(runner.run({"target": "https://www.amazon.com/s?k=laptop"}))

    assert result.state == ActorRunState.SKIPPED_MISSING_KEY
    assert result.missing_env_names == ("KEEPA_API_KEY",)


def test_local_maps_runner_executes_with_browser_fallback_when_provider_keys_are_missing() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import LocalMapsSerpRunner, build_actor_spec

    class FakeMapsConnector:
        async def search_businesses(
            self,
            query: str,
            max_results: int = 20,
            location: str | None = None,
            language: str = "en",
        ) -> list[dict]:
            assert query == "coffee shops in Austin"
            assert max_results == 3
            return [{"name": "Coffee A", "source": "maps_browser_fallback"}]

        async def close(self) -> None:
            pass

    runner = LocalMapsSerpRunner(
        build_actor_spec(
            _entry(
                name="google-maps-business-scraper",
                title="Google Maps Business Scraper",
                description="Find local businesses from Google Maps.",
                categories=("LEAD_GENERATION",),
            )
        ),
        task_id="task-1",
        tenant_id="tenant-1",
        secrets_manager=EmptySecrets(),
        maps_factory=FakeMapsConnector,
    )

    result = asyncio.run(runner.run({"query": "coffee shops in Austin", "max_results": 3}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.provider == "maps_browser_fallback"
    assert result.output["item_count"] == 1
    assert result.output["extracted_data"][0]["name"] == "Coffee A"


def test_local_maps_runner_prefers_serper_provider_when_key_is_present() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import LocalMapsSerpRunner, build_actor_spec

    class StaticSecretProvider:
        def get_secret(self, key: str) -> str | None:
            return "present" if key == "SERPER_API_KEY" else None

        def set_secret(self, key: str, value: str) -> None:
            raise NotImplementedError

    class FakeMapsConnector:
        async def search_businesses(
            self,
            query: str,
            max_results: int = 20,
            location: str | None = None,
            language: str = "en",
        ) -> list[dict]:
            return [{"name": "Coffee A", "source": "serper_places"}]

        async def close(self) -> None:
            pass

    manager = SecretsManager()
    manager.add_provider(StaticSecretProvider())
    runner = LocalMapsSerpRunner(
        build_actor_spec(
            _entry(
                name="google-maps-business-scraper",
                title="Google Maps Business Scraper",
                description="Find local businesses from Google Maps.",
                categories=("LEAD_GENERATION",),
            )
        ),
        task_id="task-1",
        tenant_id="tenant-1",
        secrets_manager=manager,
        maps_factory=FakeMapsConnector,
    )

    result = asyncio.run(runner.run({"query": "coffee shops in Austin"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.provider == "serper_places"


def test_job_board_runner_schema_matches_and_validates_worker_items() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import JobBoardSchemaRunner, build_actor_spec

    class FakeHttpWorker:
        async def process_task(self, task: dict) -> dict:
            assert task["url"] == "https://jobs.example.com"
            return {
                "status": "success",
                "status_code": 200,
                "extracted_data": [
                    {
                        "job_url": "https://jobs.example.com/roles/1",
                        "name": "Generic listing card heading",
                        "title": "Data Engineer",
                        "company": "Acme Inc",
                        "description": "Build data pipelines.",
                        "source": "Example Jobs",
                    }
                ],
                "item_count": 1,
                "confidence": 0.7,
                "extraction_method": "deterministic",
                "bytes_downloaded": 2048,
                "duration_ms": 12,
                "artifacts": [],
            }

        async def close(self) -> None:
            pass

    runner = JobBoardSchemaRunner(
        build_actor_spec(_entry(route_strategy="job_board_schema", title="Job Board Scraper")),
        task_id="task-1",
        tenant_id="tenant-1",
        http_worker_factory=FakeHttpWorker,
    )

    result = asyncio.run(runner.run({"target": "https://jobs.example.com"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.provider == "http_worker_schema_match"
    item = result.output["extracted_data"][0]
    assert item["url"] == "https://jobs.example.com/roles/1"
    assert item["title"] == "Data Engineer"
    assert item["company_name"] == "Acme Inc"
    assert result.output["schema_matched"]["match_confidence"] >= 0.8


def test_real_estate_runner_schema_matches_and_validates_worker_items() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import RealEstateSchemaRunner, build_actor_spec

    class FakeHttpWorker:
        async def process_task(self, task: dict) -> dict:
            assert task["url"] == "https://homes.example.com/listing/1"
            return {
                "status": "success",
                "status_code": 200,
                "extracted_data": [
                    {
                        "property_url": "https://homes.example.com/listing/1",
                        "title": "Beautiful Family Home",
                        "description": "A wonderful 4 bed 3 bath home.",
                        "source": "Example Homes",
                        "price": 450000,
                        "address": {"city": "Springfield", "state": "IL"},
                        "features": {"bedrooms": 4, "bathrooms": 3},
                    }
                ],
                "item_count": 1,
                "confidence": 0.72,
                "extraction_method": "deterministic",
                "bytes_downloaded": 4096,
                "duration_ms": 18,
                "artifacts": [],
            }

        async def close(self) -> None:
            pass

    runner = RealEstateSchemaRunner(
        build_actor_spec(_entry(route_strategy="real_estate_schema", title="Real Estate Scraper")),
        task_id="task-1",
        tenant_id="tenant-1",
        http_worker_factory=FakeHttpWorker,
    )

    result = asyncio.run(runner.run({"target": "https://homes.example.com/listing/1"}))

    assert result.state == ActorRunState.SUCCEEDED
    assert result.provider == "http_worker_schema_match"
    item = result.output["extracted_data"][0]
    assert item["url"] == "https://homes.example.com/listing/1"
    assert item["address"]["city"] == "Springfield"
    assert item["features"]["bedrooms"] == 4


def test_lead_review_and_content_runners_filter_existing_worker_items() -> None:
    from packages.core.actor_runtime import ActorRunState
    from packages.core.actor_runtime.families import (
        LeadGenerationGenericRunner,
        NewsContentMonitoringRunner,
        ReviewMonitoringGenericRunner,
        build_actor_spec,
    )

    class FakeHttpWorker:
        async def process_task(self, task: dict) -> dict:
            return {
                "status": "success",
                "status_code": 200,
                "extracted_data": [
                    {"name": "Acme", "email": "sales@example.com", "phone": "555-0100"},
                    {"review_title": "Great", "review_text": "Loved it", "rating": "5"},
                    {"title": "Market Update", "content_type": "article", "full_content": "News body"},
                    {"name": "Decorative item"},
                ],
                "item_count": 4,
                "confidence": 0.8,
                "extraction_method": "deterministic",
                "bytes_downloaded": 1024,
                "duration_ms": 10,
                "artifacts": [],
            }

        async def close(self) -> None:
            pass

    lead_runner = LeadGenerationGenericRunner(
        build_actor_spec(_entry(title="Business Lead Scraper", categories=("LEAD_GENERATION",))),
        task_id="task-1",
        tenant_id="tenant-1",
        http_worker_factory=FakeHttpWorker,
    )
    review_runner = ReviewMonitoringGenericRunner(
        build_actor_spec(_entry(title="Trustpilot Reviews Scraper", description="Extract reviews and ratings.")),
        task_id="task-1",
        tenant_id="tenant-1",
        http_worker_factory=FakeHttpWorker,
    )
    content_runner = NewsContentMonitoringRunner(
        build_actor_spec(_entry(title="News Article Scraper", categories=("NEWS",))),
        task_id="task-1",
        tenant_id="tenant-1",
        http_worker_factory=FakeHttpWorker,
    )

    lead = asyncio.run(lead_runner.run({"target": "https://example.com"}))
    review = asyncio.run(review_runner.run({"target": "https://example.com/reviews"}))
    content = asyncio.run(content_runner.run({"target": "https://example.com/news"}))

    assert lead.state == ActorRunState.SUCCEEDED
    assert lead.output["item_count"] == 1
    assert lead.output["extracted_data"][0]["email"] == "sales@example.com"
    assert review.state == ActorRunState.SUCCEEDED
    assert review.output["item_count"] == 1
    assert review.output["extracted_data"][0]["review_text"] == "Loved it"
    assert content.state == ActorRunState.SUCCEEDED
    assert content.output["item_count"] == 1
    assert content.output["extracted_data"][0]["content_type"] == "article"
