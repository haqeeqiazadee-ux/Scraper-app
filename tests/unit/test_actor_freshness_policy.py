from __future__ import annotations


def test_freshness_policy_clamps_ttl_bounds_and_high_volatility_floor() -> None:
    from packages.core.actor_runtime import FreshnessPolicy

    policy = FreshnessPolicy(
        fresh_ttl_seconds=-10,
        stale_ttl_seconds=5,
        high_volatility_ttl_seconds=1,
        minimum_ttl_seconds=60,
        maximum_ttl_seconds=120,
    )

    assert policy.fresh_ttl_seconds == 60
    assert policy.stale_ttl_seconds == 60
    assert policy.high_volatility_ttl_seconds == 60
    assert policy.ttl_for_family("generic_web_page_extraction") == 60
    assert policy.ttl_for_family("marketplace_product_catalog") == 60


def test_freshness_policy_uses_shorter_ttl_for_high_volatility_families() -> None:
    from packages.core.actor_runtime import FreshnessPolicy

    policy = FreshnessPolicy(
        fresh_ttl_seconds=7200,
        stale_ttl_seconds=86400,
        high_volatility_ttl_seconds=900,
    )

    assert policy.ttl_for_family("generic_web_page_extraction") == 7200
    assert policy.ttl_for_family("local_maps_serp") == 900
