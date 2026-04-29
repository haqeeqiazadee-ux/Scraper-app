"""Provider-wiring regression tests for the smart scrape router."""

from pathlib import Path


SMART_SCRAPE_SOURCE = Path(__file__).resolve().parents[2] / "services" / "control-plane" / "routers" / "smart_scrape.py"


def test_smart_scrape_does_not_embed_scrapecreators_secret() -> None:
    source = SMART_SCRAPE_SOURCE.read_text(encoding="utf-8")

    assert 'os.environ.get("SCRAPECREATORS_API_KEY", "").strip()' in source
    assert "0FQ0veBBGJSlr3z3yQToiDJQVRZ2" not in source


def test_smart_scrape_uses_keepa_router_factory_and_public_methods() -> None:
    source = SMART_SCRAPE_SOURCE.read_text(encoding="utf-8")

    assert "from services.control_plane.routers.keepa import _get_keepa" in source
    assert "_get_keepa_connector" not in source
    assert "connector.query_products(" in source
    assert "connector.search_products(" in source
    assert "connector.query(" not in source


def test_amazon_branch_fails_closed_without_keepa_credentials() -> None:
    source = SMART_SCRAPE_SOURCE.read_text(encoding="utf-8")

    assert 'is_amazon and not os.environ.get("KEEPA_API_KEY", "").strip()' in source
    assert "falling back to scraper" in source
