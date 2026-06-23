from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from packages.core.secrets import SecretsManager


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
        secrets_manager=SecretsManager(),
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
        secrets_manager=SecretsManager(),
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
