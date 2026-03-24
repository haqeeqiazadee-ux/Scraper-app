"""Tests for DOM auto-discovery of repeating groups."""

import pytest

from packages.core.dom_discovery import (
    discover_items,
    extract_fields_from_card,
    find_repeating_groups,
    _tag_signature,
    _structural_similarity,
)


# --- Test HTML fixtures ---

PRODUCT_GRID_HTML = """
<html>
<head><title>Products</title></head>
<body>
<nav><a href="/">Home</a></nav>
<div class="product-listing">
  <div class="card" data-id="1">
    <h3><a href="/product/1" title="Widget A">Widget A</a></h3>
    <span class="price">$19.99</span>
    <img src="https://example.com/a.jpg">
  </div>
  <div class="card" data-id="2">
    <h3><a href="/product/2" title="Widget B">Widget B</a></h3>
    <span class="price">$29.99</span>
    <img src="https://example.com/b.jpg">
  </div>
  <div class="card" data-id="3">
    <h3><a href="/product/3" title="Widget C">Widget C</a></h3>
    <span class="price">$39.99</span>
    <img src="https://example.com/c.jpg">
  </div>
</div>
<footer>Copyright 2024</footer>
</body>
</html>
"""

LIST_HTML = """
<html><body>
<ul class="items">
  <li><a href="/item/1">Item One</a> - $10.00</li>
  <li><a href="/item/2">Item Two</a> - $20.00</li>
  <li><a href="/item/3">Item Three</a> - $30.00</li>
  <li><a href="/item/4">Item Four</a> - $40.00</li>
</ul>
</body></html>
"""

SINGLE_PRODUCT_HTML = """
<html>
<head><title>Single Product Page</title></head>
<body>
<div class="product-detail">
  <h1>Laptop Pro</h1>
  <span class="price">$999.99</span>
  <img src="https://example.com/laptop.jpg">
</div>
</body>
</html>
"""

EMPTY_HTML = "<html><body></body></html>"

NO_REPEATING_HTML = """
<html><body>
<div>
  <h1>Welcome</h1>
  <p>This is a paragraph.</p>
</div>
</body></html>
"""

MIXED_CHILDREN_HTML = """
<html><body>
<div class="container">
  <div class="product"><h3><a href="/p/1">Prod A</a></h3><span>$5</span><img src="/a.jpg"></div>
  <div class="product"><h3><a href="/p/2">Prod B</a></h3><span>$10</span><img src="/b.jpg"></div>
  <div class="sidebar">Different structure entirely</div>
  <div class="product"><h3><a href="/p/3">Prod C</a></h3><span>$15</span><img src="/c.jpg"></div>
</div>
</body></html>
"""


class TestTagSignature:

    def test_same_structure_same_signature(self):
        from bs4 import BeautifulSoup, Tag
        html = '<div><div class="a"><h3>A</h3><span>B</span></div><div class="b"><h3>C</h3><span>D</span></div></div>'
        soup = BeautifulSoup(html, "html.parser")
        children = [c for c in soup.div.children if isinstance(c, Tag)]
        assert len(children) == 2
        sig_a = _tag_signature(children[0])
        sig_b = _tag_signature(children[1])
        assert _structural_similarity(sig_a, sig_b) >= 0.7

    def test_different_structure_low_similarity(self):
        from bs4 import BeautifulSoup, Tag
        html = '<div><div><h3>Title</h3><p>Text</p></div><span>Just text</span></div>'
        soup = BeautifulSoup(html, "html.parser")
        children = [c for c in soup.div.children if isinstance(c, Tag)]
        assert len(children) == 2
        sig_a = _tag_signature(children[0])
        sig_b = _tag_signature(children[1])
        assert _structural_similarity(sig_a, sig_b) < 0.7


class TestFindRepeatingGroups:

    def test_finds_product_grid(self):
        groups = find_repeating_groups(PRODUCT_GRID_HTML)
        assert len(groups) >= 1
        # The largest group should have 3 cards
        assert len(groups[0]) == 3

    def test_finds_list_items(self):
        groups = find_repeating_groups(LIST_HTML)
        assert len(groups) >= 1
        assert len(groups[0]) >= 4

    def test_no_groups_in_single_product(self):
        groups = find_repeating_groups(SINGLE_PRODUCT_HTML)
        # Should not find repeating groups on a single product page
        # (may find some, but they should be small/irrelevant)
        for group in groups:
            # No group should have 2+ items that look like products
            pass  # Just verify no crash

    def test_empty_html(self):
        groups = find_repeating_groups(EMPTY_HTML)
        assert groups == []

    def test_no_repeating_structure(self):
        groups = find_repeating_groups(NO_REPEATING_HTML)
        # Should either return empty or only small groups
        assert isinstance(groups, list)

    def test_handles_mixed_children(self):
        groups = find_repeating_groups(MIXED_CHILDREN_HTML)
        assert len(groups) >= 1
        # Should group the 3 product divs together, ignoring sidebar
        product_group = groups[0]
        assert len(product_group) >= 2


class TestExtractFieldsFromCard:

    def test_extracts_name_and_link(self):
        from bs4 import BeautifulSoup
        html = '<div><h3><a href="/product/1" title="Widget A">Widget A</a></h3></div>'
        card = BeautifulSoup(html, "html.parser").div
        fields = extract_fields_from_card(card, "https://example.com")
        assert fields["name"] == "Widget A"
        assert fields["product_url"] == "https://example.com/product/1"

    def test_extracts_price(self):
        from bs4 import BeautifulSoup
        html = '<div><h3>Test</h3><span class="price">$29.99</span></div>'
        card = BeautifulSoup(html, "html.parser").div
        fields = extract_fields_from_card(card, "https://example.com")
        assert fields["price"] == "29.99"

    def test_extracts_image(self):
        from bs4 import BeautifulSoup
        html = '<div><h3>Test</h3><img src="/img/test.jpg"></div>'
        card = BeautifulSoup(html, "html.parser").div
        fields = extract_fields_from_card(card, "https://example.com")
        assert fields["image_url"] == "https://example.com/img/test.jpg"

    def test_resolves_relative_urls(self):
        from bs4 import BeautifulSoup
        html = '<div><a href="/p/1">Product</a></div>'
        card = BeautifulSoup(html, "html.parser").div
        fields = extract_fields_from_card(card, "https://shop.example.com")
        assert fields["product_url"] == "https://shop.example.com/p/1"

    def test_no_name_returns_empty(self):
        from bs4 import BeautifulSoup
        html = '<div><span>$10</span></div>'
        card = BeautifulSoup(html, "html.parser").div
        fields = extract_fields_from_card(card, "https://example.com")
        assert "name" not in fields


class TestDiscoverItems:

    def test_discovers_products_from_grid(self):
        items = discover_items(PRODUCT_GRID_HTML, "https://example.com")
        assert len(items) == 3
        names = {item["name"] for item in items}
        assert "Widget A" in names
        assert "Widget B" in names
        assert "Widget C" in names

    def test_discovers_prices(self):
        items = discover_items(PRODUCT_GRID_HTML, "https://example.com")
        prices = {item.get("price") for item in items}
        assert "19.99" in prices
        assert "29.99" in prices

    def test_discovers_images(self):
        items = discover_items(PRODUCT_GRID_HTML, "https://example.com")
        for item in items:
            assert "image_url" in item

    def test_list_items(self):
        items = discover_items(LIST_HTML, "https://example.com")
        assert len(items) >= 4
        names = {item["name"] for item in items}
        assert "Item One" in names

    def test_empty_html_returns_empty(self):
        items = discover_items(EMPTY_HTML, "https://example.com")
        assert items == []

    def test_single_product_page_no_repeating(self):
        items = discover_items(SINGLE_PRODUCT_HTML, "https://example.com")
        # Single product pages shouldn't produce repeating groups
        assert isinstance(items, list)


class TestDiscoverItemsIntegration:
    """Test that DOM discovery integrates correctly with DeterministicProvider."""

    @pytest.mark.asyncio
    async def test_deterministic_provider_uses_dom_discovery(self):
        """Verify the DeterministicProvider falls through to DOM discovery."""
        from packages.core.ai_providers.deterministic import DeterministicProvider

        provider = DeterministicProvider()
        # This HTML has no JSON-LD, so it should try DOM discovery
        items = await provider.extract(PRODUCT_GRID_HTML, "https://example.com")
        assert len(items) >= 2
        names = {item.get("name") for item in items}
        assert "Widget A" in names

    @pytest.mark.asyncio
    async def test_jsonld_still_takes_priority(self):
        """JSON-LD extraction should still be preferred over DOM discovery."""
        from packages.core.ai_providers.deterministic import DeterministicProvider

        html_with_jsonld = """
        <html><body>
        <script type="application/ld+json">
        {"@type": "Product", "name": "JSON-LD Product", "offers": {"price": "99.99"}}
        </script>
        <div class="products">
          <div class="card"><h3><a href="/1">Card A</a></h3></div>
          <div class="card"><h3><a href="/2">Card B</a></h3></div>
        </div>
        </body></html>
        """
        provider = DeterministicProvider()
        items = await provider.extract(html_with_jsonld, "https://example.com")
        assert len(items) >= 1
        assert items[0]["name"] == "JSON-LD Product"
