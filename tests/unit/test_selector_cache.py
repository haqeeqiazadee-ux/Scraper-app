"""Tests for the selector cache."""

import os
import tempfile
import time

import pytest

from packages.core.selector_cache import SelectorCache, _domain_key


class TestDomainKey:

    def test_same_domain_same_path_prefix(self):
        key1 = _domain_key("https://example.com/products/123")
        key2 = _domain_key("https://example.com/products/456")
        assert key1 == key2

    def test_different_domains(self):
        key1 = _domain_key("https://example.com/products")
        key2 = _domain_key("https://other.com/products")
        assert key1 != key2

    def test_different_path_prefixes(self):
        key1 = _domain_key("https://example.com/products/1")
        key2 = _domain_key("https://example.com/categories/1")
        assert key1 != key2


class TestSelectorCache:

    @pytest.fixture
    def cache(self, tmp_path):
        return SelectorCache(cache_dir=str(tmp_path), ttl_seconds=3600)

    def test_put_and_get(self, cache):
        url = "https://shop.example.com/products/1"
        cache.put(
            url=url,
            card_selector=".product-card",
            field_selectors={"name": "h3 a", "price": ".price"},
            source="dom_discovery",
        )
        entry = cache.get(url)
        assert entry is not None
        assert entry["card_selector"] == ".product-card"
        assert entry["field_selectors"]["name"] == "h3 a"
        assert entry["source"] == "dom_discovery"

    def test_get_miss(self, cache):
        entry = cache.get("https://unknown.example.com/products")
        assert entry is None

    def test_same_domain_different_pages_share_cache(self, cache):
        cache.put(
            url="https://shop.example.com/products/1",
            card_selector=".card",
            field_selectors={"name": "h3"},
        )
        # Different product ID, same domain+prefix → should hit cache
        entry = cache.get("https://shop.example.com/products/999")
        assert entry is not None
        assert entry["card_selector"] == ".card"

    def test_ttl_expiry(self, tmp_path):
        cache = SelectorCache(cache_dir=str(tmp_path), ttl_seconds=1)
        cache.put(
            url="https://example.com/products/1",
            card_selector=".card",
            field_selectors={},
        )
        assert cache.get("https://example.com/products/1") is not None
        # Simulate expiry by manipulating discovered_at
        import json
        key = _domain_key("https://example.com/products/1")
        path = os.path.join(str(tmp_path), f"{key}.json")
        with open(path, "r") as f:
            data = json.load(f)
        data["discovered_at"] = time.time() - 10  # 10 seconds ago
        with open(path, "w") as f:
            json.dump(data, f)
        # Clear memory cache
        cache._memory.clear()
        assert cache.get("https://example.com/products/1") is None

    def test_invalidate(self, cache):
        url = "https://example.com/products/1"
        cache.put(url=url, card_selector=".card", field_selectors={})
        assert cache.get(url) is not None
        cache.invalidate(url)
        assert cache.get(url) is None

    def test_disk_persistence(self, tmp_path):
        url = "https://example.com/products/1"
        cache1 = SelectorCache(cache_dir=str(tmp_path))
        cache1.put(url=url, card_selector=".card", field_selectors={"name": "h3"})

        # New cache instance, same dir — should read from disk
        cache2 = SelectorCache(cache_dir=str(tmp_path))
        entry = cache2.get(url)
        assert entry is not None
        assert entry["card_selector"] == ".card"
