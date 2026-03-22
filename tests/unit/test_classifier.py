"""Tests for URL classifier."""

import pytest
from packages.core.ai_classifier import URLClassifier
from packages.core.router import Lane


@pytest.fixture
def classifier():
    return URLClassifier()


class TestURLClassifier:

    def test_api_json_url(self, classifier):
        assert classifier.classify("https://shop.com/products.json") == Lane.API

    def test_api_versioned(self, classifier):
        assert classifier.classify("https://api.example.com/api/v1/products") == Lane.API

    def test_rss_feed(self, classifier):
        assert classifier.classify("https://blog.com/feed.xml") == Lane.API

    def test_graphql(self, classifier):
        assert classifier.classify("https://shop.com/graphql") == Lane.API

    def test_instagram_needs_browser(self, classifier):
        assert classifier.classify("https://instagram.com/user") == Lane.BROWSER

    def test_tiktok_needs_browser(self, classifier):
        assert classifier.classify("https://tiktok.com/@user") == Lane.BROWSER

    def test_html_page_is_http(self, classifier):
        assert classifier.classify("https://shop.com/product/widget.html") == Lane.HTTP

    def test_category_page_is_http(self, classifier):
        assert classifier.classify("https://shop.com/category/electronics") == Lane.HTTP

    def test_unknown_defaults_to_http(self, classifier):
        assert classifier.classify("https://random-site.com/page") == Lane.HTTP

    def test_cache_works(self, classifier):
        classifier.classify("https://example.com/page1")
        # Second call should use cache
        result = classifier.classify("https://example.com/page2")
        assert result == Lane.HTTP

    def test_update_cache(self, classifier):
        classifier.update_cache("example.com", Lane.BROWSER)
        assert classifier.classify("https://example.com/anything") == Lane.BROWSER

    def test_clear_cache(self, classifier):
        classifier.classify("https://example.com/page")
        classifier.clear_cache()
        # Should re-classify
        result = classifier.classify("https://example.com/page")
        assert result == Lane.HTTP
