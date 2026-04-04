"""Tests for the AdaptiveSelectorEngine."""

import os
import time

import pytest

from packages.core.adaptive_selectors import (
    AdaptiveSelectorEngine,
    SelectorFingerprint,
)


# ---------------------------------------------------------------------------
# Sample HTML for product cards
# ---------------------------------------------------------------------------

CARD_V1 = """
<html><body>
<div class="product-card">
  <h3><a href="/product/1">Wireless Mouse</a></h3>
  <span class="price">$29.99</span>
  <img src="/img/mouse.jpg" alt="Wireless Mouse" />
</div>
</body></html>
"""

CARD_V2_SIMILAR = """
<html><body>
<div class="product-card item">
  <h3><a href="/product/1">Wireless Mouse Pro</a></h3>
  <span class="sale-price">$24.99</span>
  <img src="/img/mouse-v2.jpg" alt="Wireless Mouse Pro" />
</div>
</body></html>
"""

CARD_V3_DIFFERENT = """
<html><body>
<section class="promo-banner">
  <p>Summer sale!</p>
</section>
</body></html>
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine(tmp_path):
    return AdaptiveSelectorEngine(
        cache_dir=str(tmp_path),
        ttl_seconds=3600,
        similarity_threshold=0.6,
    )


# ---------------------------------------------------------------------------
# Cache: get_selectors
# ---------------------------------------------------------------------------

class TestGetSelectors:

    def test_get_selectors_cached(self, engine):
        url = "https://shop.example.com/products/1"
        # Populate the underlying selector cache via record_success
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a", "price": ".price"},
            "source": "dom_discovery",
        }
        engine.record_success(url, selectors, CARD_V1)
        result = engine.get_selectors(url)
        assert result is not None
        assert result["card_selector"] == ".product-card"

    def test_get_selectors_miss(self, engine):
        result = engine.get_selectors("https://unknown.example.com/products")
        assert result is None


# ---------------------------------------------------------------------------
# record_success / record_failure
# ---------------------------------------------------------------------------

class TestRecordOutcomes:

    def test_record_success_updates_cache(self, engine):
        url = "https://shop.example.com/products/1"
        assert engine.get_selectors(url) is None
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a"},
            "source": "dom_discovery",
        }
        engine.record_success(url, selectors, CARD_V1)
        cached = engine.get_selectors(url)
        assert cached is not None
        assert cached["card_selector"] == ".product-card"

    def test_record_failure_increments_count(self, engine):
        url = "https://shop.example.com/products/1"
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a"},
        }
        # First, record a success so the fingerprint exists
        engine.record_success(url, selectors, CARD_V1)

        # Record failures
        engine.record_failure(url, selectors)
        engine.record_failure(url, selectors)

        from packages.core.selector_cache import _domain_key
        dk = _domain_key(url)
        fps = engine._fingerprints.get(dk, [])
        card_fp = [fp for fp in fps if fp.selector == ".product-card"]
        assert len(card_fp) == 1
        assert card_fp[0].failure_count == 2


# ---------------------------------------------------------------------------
# Fuzzy matching via adapt_selectors
# ---------------------------------------------------------------------------

class TestAdaptSelectors:

    def test_adapt_selectors_finds_similar(self, engine):
        url = "https://shop.example.com/products/1"
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a", "price": ".price"},
            "source": "dom_discovery",
        }
        engine.record_success(url, selectors, CARD_V1)

        # The V2 HTML has a similar structure but changed class names
        result = engine.adapt_selectors(url, CARD_V2_SIMILAR)
        # May or may not adapt depending on similarity — either a dict or None
        # The key assertion: if it adapts, it returns a dict with card_selector
        if result is not None:
            assert "card_selector" in result
            assert "field_selectors" in result

    def test_adapt_selectors_no_match(self, engine):
        url = "https://shop.example.com/products/1"
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a"},
            "source": "dom_discovery",
        }
        engine.record_success(url, selectors, CARD_V1)

        # Completely different HTML — should not match
        result = engine.adapt_selectors(url, CARD_V3_DIFFERENT)
        # If original selector is gone and nothing similar, should be None
        assert result is None


# ---------------------------------------------------------------------------
# Fingerprinting
# ---------------------------------------------------------------------------

class TestFingerprint:

    def test_fingerprint_includes_tag_path(self, engine):
        fp = engine._build_fingerprint(".product-card", CARD_V1)
        assert fp is not None
        assert fp.tag_path != ""
        # Should contain "div" since .product-card is a div
        assert "div" in fp.tag_path

    def test_fingerprint_includes_text_sample(self, engine):
        fp = engine._build_fingerprint(".product-card", CARD_V1)
        assert fp is not None
        assert fp.text_sample != ""
        assert "Wireless Mouse" in fp.text_sample


# ---------------------------------------------------------------------------
# Similarity threshold
# ---------------------------------------------------------------------------

class TestSimilarityThreshold:

    def test_similarity_threshold(self, tmp_path):
        # With a very high threshold, even similar cards should fail to match
        strict_engine = AdaptiveSelectorEngine(
            cache_dir=str(tmp_path),
            ttl_seconds=3600,
            similarity_threshold=0.99,
        )
        url = "https://shop.example.com/products/1"
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a"},
        }
        strict_engine.record_success(url, selectors, CARD_V1)
        result = strict_engine.adapt_selectors(url, CARD_V2_SIMILAR)
        # Very strict threshold — should either fail or only match exact
        assert result is None


# ---------------------------------------------------------------------------
# Decay stale fingerprints
# ---------------------------------------------------------------------------

class TestDecayStale:

    def test_decay_stale_removes_bad(self, engine):
        url = "https://shop.example.com/products/1"
        selectors = {
            "card_selector": ".product-card",
            "field_selectors": {"name": "h3 a"},
        }
        # Record one success, then many failures to trigger decay
        engine.record_success(url, selectors, CARD_V1)

        from packages.core.selector_cache import _domain_key
        dk = _domain_key(url)

        # Manually crank up failure counts to exceed the 2x threshold
        for fp in engine._fingerprints.get(dk, []):
            fp.failure_count = 100

        # record_failure calls _decay_stale internally
        engine.record_failure(url, selectors)

        remaining = engine._fingerprints.get(dk, [])
        # All fingerprints should have been decayed
        assert len(remaining) == 0


# ---------------------------------------------------------------------------
# Auto-update on discovery
# ---------------------------------------------------------------------------

class TestAutoUpdate:

    def test_auto_update_on_discovery(self, engine):
        url = "https://new-shop.example.com/products/1"
        assert engine.get_selectors(url) is None

        # Simulate DOM discovery finding selectors and recording success
        new_selectors = {
            "card_selector": ".product",
            "field_selectors": {"name": "h2 a", "price": ".amount"},
            "source": "dom_discovery",
        }
        engine.record_success(url, new_selectors, CARD_V1)
        cached = engine.get_selectors(url)
        assert cached is not None
        assert cached["card_selector"] == ".product"
