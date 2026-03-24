"""
Tests for API/JSON pagination — next page token following.

Covers:
  UC-9.2.2 — API with pagination → follows next page tokens
"""

from __future__ import annotations

import json
import pytest

from services.worker_http.worker import _find_api_next_page, _find_next_page_url


class TestAPINextPage:
    """Find next page URL from JSON API responses."""

    def test_direct_next_url(self):
        body = json.dumps({"data": [], "next": "https://api.example.com/items?page=2"})
        result = _find_api_next_page(body, "https://api.example.com/items")
        assert result == "https://api.example.com/items?page=2"

    def test_next_url_field(self):
        body = json.dumps({"results": [], "next_url": "/api/items?offset=20"})
        result = _find_api_next_page(body, "https://api.example.com/api/items")
        assert result == "https://api.example.com/api/items?offset=20"

    def test_nested_pagination_next(self):
        body = json.dumps({
            "data": [],
            "pagination": {"next": "https://api.example.com/v2/products?page=3"},
        })
        result = _find_api_next_page(body, "https://api.example.com/v2/products")
        assert result == "https://api.example.com/v2/products?page=3"

    def test_nested_links_next(self):
        body = json.dumps({
            "items": [],
            "links": {"next": "/v1/items?cursor=abc123"},
        })
        result = _find_api_next_page(body, "https://api.example.com/v1/items")
        assert result == "https://api.example.com/v1/items?cursor=abc123"

    def test_page_token(self):
        body = json.dumps({
            "data": [],
            "next_page_token": "eyJwYWdlIjogMn0=",
        })
        result = _find_api_next_page(body, "https://api.example.com/items")
        assert result is not None
        assert "page_token=eyJwYWdlIjogMn0%3D" in result

    def test_cursor_based(self):
        body = json.dumps({
            "results": [],
            "cursor": "cursor_xyz",
            "has_more": True,
        })
        result = _find_api_next_page(body, "https://api.example.com/search")
        assert result is not None
        assert "page_token=cursor_xyz" in result

    def test_cursor_has_more_false(self):
        """When has_more is false, no next page."""
        body = json.dumps({
            "results": [],
            "cursor": "cursor_xyz",
            "has_more": False,
        })
        result = _find_api_next_page(body, "https://api.example.com/search")
        assert result is None

    def test_nested_cursor_in_pagination(self):
        body = json.dumps({
            "data": [],
            "pagination": {
                "cursor": "next_abc",
            },
        })
        result = _find_api_next_page(body, "https://api.example.com/feed")
        assert result is not None
        assert "page_token=next_abc" in result

    def test_no_pagination(self):
        body = json.dumps({"data": [1, 2, 3]})
        result = _find_api_next_page(body, "https://api.example.com/items")
        assert result is None

    def test_invalid_json(self):
        result = _find_api_next_page("not json", "https://api.example.com")
        assert result is None

    def test_empty_string(self):
        result = _find_api_next_page("", "https://api.example.com")
        assert result is None

    def test_array_response(self):
        body = json.dumps([{"id": 1}, {"id": 2}])
        result = _find_api_next_page(body, "https://api.example.com/items")
        assert result is None

    def test_relative_next_url(self):
        body = json.dumps({"next": "/page/2"})
        result = _find_api_next_page(body, "https://example.com/page/1")
        assert result == "https://example.com/page/2"

    def test_nextPageUrl_camelcase(self):
        body = json.dumps({"items": [], "nextPageUrl": "https://api.example.com/v2?page=2"})
        result = _find_api_next_page(body, "https://api.example.com/v2")
        assert result == "https://api.example.com/v2?page=2"


class TestHTMLPagination:
    """Existing HTML pagination detection."""

    def test_rel_next_link(self):
        html = '<html><body><a rel="next" href="/page/2">Next</a></body></html>'
        result = _find_next_page_url(html, "https://example.com/page/1")
        assert result == "https://example.com/page/2"

    def test_next_class_link(self):
        html = '<html><body><div class="pagination"><a class="next" href="/items?p=3">Next</a></div></body></html>'
        result = _find_next_page_url(html, "https://example.com/items?p=2")
        assert result is not None

    def test_text_next_link(self):
        html = '<html><body><a href="/p3">Next</a></body></html>'
        result = _find_next_page_url(html, "https://example.com/p2")
        assert result == "https://example.com/p3"

    def test_no_next_link(self):
        html = '<html><body><p>No links here</p></body></html>'
        result = _find_next_page_url(html, "https://example.com")
        assert result is None

    def test_arrow_next(self):
        html = '<html><body><a href="/next">\u00bb</a></body></html>'
        result = _find_next_page_url(html, "https://example.com")
        assert result == "https://example.com/next"
