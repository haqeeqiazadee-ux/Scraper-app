from __future__ import annotations

from types import SimpleNamespace
from typing import Any


def _entry(**overrides: Any) -> SimpleNamespace:
    data = {
        "actor_id": "actor-provider-ladder",
        "name": "provider-ladder-demo",
        "title": "Provider Ladder Demo",
        "description": "Generic extraction actor",
        "categories": (),
        "route_strategy": "native_pipeline",
        "runnable_status": "runnable",
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_provider_steps_preserve_api_first_tiers_and_rationales() -> None:
    from packages.core.actor_runtime import ProviderStep, ProviderTier

    step = ProviderStep(
        name="official_api",
        tier="official_public_api",
        connector="packages.connectors.example.ExampleConnector",
        rationale=" Prefer the stable API. ",
    )

    assert step.tier == ProviderTier.OFFICIAL_PUBLIC_API
    assert step.connector == "packages.connectors.example.ExampleConnector"
    assert step.rationale == "Prefer the stable API."


def test_commerce_provider_ladder_prefers_storefront_api_before_http() -> None:
    from packages.core.actor_runtime import ProviderTier, build_actor_spec

    spec = build_actor_spec(
        _entry(
            title="Shopify Product Storefront",
            description="Extract products and prices from a Shopify store",
            categories=("ECOMMERCE",),
        )
    )

    assert [step.name for step in spec.provider_chain] == ["shopify_products_json", "http_worker"]
    assert [step.tier for step in spec.provider_chain] == [
        ProviderTier.OFFICIAL_PUBLIC_API,
        ProviderTier.HTTP_EXTRACTION,
    ]


def test_local_maps_provider_ladder_orders_api_sdk_before_browser_fallback() -> None:
    from packages.core.actor_runtime import ProviderTier, build_actor_spec

    spec = build_actor_spec(
        _entry(
            title="Google Maps Business Search",
            description="Find local businesses and places near me",
            categories=("LOCAL",),
        )
    )

    assert [step.name for step in spec.provider_chain] == [
        "serper_places",
        "google_places",
        "maps_browser_fallback",
    ]
    assert [step.tier for step in spec.provider_chain] == [
        ProviderTier.PROVIDER_SDK,
        ProviderTier.OFFICIAL_PUBLIC_API,
        ProviderTier.BROWSER_UNBLOCKER,
    ]


def test_amazon_marketplace_provider_ladder_uses_keepa_without_apify_runtime() -> None:
    from packages.core.actor_runtime import ProviderTier, build_actor_spec

    spec = build_actor_spec(
        _entry(
            title="Amazon Product Catalog",
            description="Amazon ASIN and product data",
            categories=("ECOMMERCE",),
        )
    )

    assert spec.provider_chain[0].name == "keepa"
    assert spec.provider_chain[0].tier == ProviderTier.PROVIDER_SDK
    assert spec.provider_chain[0].required_env_names == ("KEEPA_API_KEY",)
    assert all("apify" not in step.name.lower() for step in spec.provider_chain)
    assert all(not (step.connector and "apify" in step.connector.lower()) for step in spec.provider_chain)


def test_unsupported_route_strategy_gets_machine_readable_provider_ladder() -> None:
    from packages.core.actor_runtime import ProviderTier, build_actor_spec

    spec = build_actor_spec(_entry(route_strategy="yt_dlp", title="Video Downloader"))

    assert spec.base_family == "yt_dlp"
    assert spec.provider_chain[0].name == "unsupported_route_strategy"
    assert spec.provider_chain[0].tier == ProviderTier.UNSUPPORTED
    assert "not yet mapped" in spec.provider_chain[0].rationale


def test_all_current_base_families_have_tiered_provider_ladders() -> None:
    from packages.core.actor_runtime import ActorBaseFamily, ProviderTier, build_actor_spec

    samples = {
        ActorBaseFamily.GENERIC_WEB_PAGE_EXTRACTION: _entry(title="Generic Web Scraper"),
        ActorBaseFamily.COMMERCE_STOREFRONT_GENERIC: _entry(title="Shopify Store Products"),
        ActorBaseFamily.MARKETPLACE_PRODUCT_CATALOG: _entry(title="eBay Marketplace Catalog"),
        ActorBaseFamily.LOCAL_MAPS_SERP: _entry(title="Google Maps Places"),
        ActorBaseFamily.JOB_BOARD_SCHEMA: _entry(route_strategy="job_board_schema", title="Job Board"),
        ActorBaseFamily.REAL_ESTATE_SCHEMA: _entry(route_strategy="real_estate_schema", title="Property Listings"),
        ActorBaseFamily.LEAD_GENERATION_GENERIC: _entry(
            title="Lead Email Finder",
            description="Find business contacts and emails",
            categories=("LEAD_GENERATION",),
        ),
        ActorBaseFamily.REVIEW_MONITORING_GENERIC: _entry(title="Trustpilot Review Monitor"),
        ActorBaseFamily.NEWS_CONTENT_MONITORING: _entry(title="News Article Monitor", categories=("NEWS",)),
    }

    for expected_family, entry in samples.items():
        spec = build_actor_spec(entry)
        assert spec.base_family == expected_family
        assert spec.provider_chain
        assert all(step.tier != ProviderTier.UNSUPPORTED for step in spec.provider_chain)
        assert all(step.connector for step in spec.provider_chain)
        assert all(step.rationale for step in spec.provider_chain)
