from packages.connectors.search_fallback import marketplace_items_from_hits
from packages.core.secrets import clean_secret_value


def test_clean_secret_value_strips_bom_quotes_and_whitespace():
    assert clean_secret_value('  "\ufeffabc123"  ') == "abc123"
    assert clean_secret_value(" '\ufeffxyz' ") == "xyz"
    assert clean_secret_value("   ") is None


def test_marketplace_items_from_hits_are_product_candidates():
    items = marketplace_items_from_hits(
        [{"title": "Laptop - eBay", "url": "https://www.ebay.com/itm/123"}],
        platform="ebay",
        query="laptop",
        method="serper_ebay_listing_search",
    )

    assert items == [{
        "name": "Laptop - eBay",
        "description": "",
        "product_url": "https://www.ebay.com/itm/123",
        "url": "https://www.ebay.com/itm/123",
        "platform": "ebay",
        "source": "serper_site_search",
        "query": "laptop",
        "_category": "product",
        "_extraction_method": "serper_ebay_listing_search",
    }]
