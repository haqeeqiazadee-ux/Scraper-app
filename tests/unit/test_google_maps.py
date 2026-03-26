"""Tests for Google Maps connector.

Covers:
- Connector initialization and tier detection
- Places API response transformation
- SerpAPI response transformation
- Browser HTML parsing
- Tier fallback logic
- Business data standardization
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.connectors.google_maps_connector import GoogleMapsConnector


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestGoogleMapsInit:

    def test_creates_with_no_keys(self) -> None:
        """Connector works without any API keys (browser fallback)."""
        connector = GoogleMapsConnector()
        assert connector._google_api_key == ""
        assert connector._serpapi_key == ""
        assert connector._max_results == 20

    def test_creates_with_google_key(self) -> None:
        connector = GoogleMapsConnector(google_api_key="test_google_key")
        assert connector._google_api_key == "test_google_key"

    def test_creates_with_serpapi_key(self) -> None:
        connector = GoogleMapsConnector(serpapi_key="test_serpapi_key")
        assert connector._serpapi_key == "test_serpapi_key"

    def test_creates_with_both_keys(self) -> None:
        connector = GoogleMapsConnector(google_api_key="gk", serpapi_key="sk")
        assert connector._google_api_key == "gk"
        assert connector._serpapi_key == "sk"

    def test_custom_max_results(self) -> None:
        connector = GoogleMapsConnector(max_results=50)
        assert connector._max_results == 50

    @pytest.mark.asyncio
    async def test_health_check_always_true(self) -> None:
        """Health check returns True (browser fallback always available)."""
        connector = GoogleMapsConnector()
        assert await connector.health_check() is True


# ---------------------------------------------------------------------------
# Places API Transformation
# ---------------------------------------------------------------------------


class TestPlacesAPITransform:

    def test_transforms_basic_place(self) -> None:
        """Places API response transforms to standard format."""
        connector = GoogleMapsConnector()
        place = {
            "id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "displayName": {"text": "Joe's Pizza"},
            "formattedAddress": "123 Main St, New York, NY",
            "location": {"latitude": 40.7128, "longitude": -74.0060},
            "nationalPhoneNumber": "(212) 555-0100",
            "websiteUri": "https://joespizza.com",
            "rating": 4.5,
            "userRatingCount": 1234,
            "businessStatus": "OPERATIONAL",
            "priceLevel": "PRICE_LEVEL_MODERATE",
            "types": ["restaurant", "food"],
            "primaryType": "restaurant",
            "googleMapsUri": "https://maps.google.com/?cid=123",
        }

        result = connector._transform_places_api_result(place)

        assert result["name"] == "Joe's Pizza"
        assert result["place_id"] == "ChIJN1t_tDeuEmsRUsoyG83frY4"
        assert result["address"] == "123 Main St, New York, NY"
        assert result["latitude"] == 40.7128
        assert result["longitude"] == -74.0060
        assert result["phone"] == "(212) 555-0100"
        assert result["website"] == "https://joespizza.com"
        assert result["rating"] == 4.5
        assert result["review_count"] == 1234
        assert result["business_status"] == "OPERATIONAL"
        assert result["primary_type"] == "restaurant"
        assert result["source"] == "google_places_api"

    def test_transforms_minimal_place(self) -> None:
        """Handles place with minimal fields."""
        connector = GoogleMapsConnector()
        place = {
            "displayName": {"text": "Mystery Shop"},
            "formattedAddress": "Somewhere",
        }

        result = connector._transform_places_api_result(place)

        assert result["name"] == "Mystery Shop"
        assert result["address"] == "Somewhere"
        assert result["phone"] == ""
        assert result["website"] == ""
        assert result["rating"] is None

    def test_transforms_place_with_hours(self) -> None:
        """Handles opening hours."""
        connector = GoogleMapsConnector()
        place = {
            "displayName": {"text": "Cafe"},
            "formattedAddress": "456 Oak Ave",
            "currentOpeningHours": {
                "openNow": True,
                "weekdayDescriptions": [
                    "Monday: 8:00 AM – 10:00 PM",
                    "Tuesday: 8:00 AM – 10:00 PM",
                ],
                "periods": [
                    {"open": {"day": 1, "hour": 8, "minute": 0},
                     "close": {"day": 1, "hour": 22, "minute": 0}},
                ],
            },
        }

        result = connector._transform_places_api_result(place)

        assert result["open_now"] is True
        assert len(result["hours_text"]) == 2
        assert result["hours"][0]["open"] == "08:00"
        assert result["hours"][0]["close"] == "22:00"


# ---------------------------------------------------------------------------
# SerpAPI Transformation
# ---------------------------------------------------------------------------


class TestSerpAPITransform:

    def test_transforms_serpapi_result(self) -> None:
        connector = GoogleMapsConnector()
        item = {
            "title": "Bob's Burgers",
            "place_id": "serp_place_123",
            "address": "789 Elm St, LA",
            "gps_coordinates": {"latitude": 34.0522, "longitude": -118.2437},
            "phone": "+1-310-555-0199",
            "website": "https://bobsburgers.com",
            "rating": 4.2,
            "reviews": 567,
            "type": "Restaurant",
            "link": "https://maps.google.com/place/bobs",
            "thumbnail": "https://img.com/bobs.jpg",
        }

        result = connector._transform_serpapi_result(item)

        assert result["name"] == "Bob's Burgers"
        assert result["address"] == "789 Elm St, LA"
        assert result["latitude"] == 34.0522
        assert result["phone"] == "+1-310-555-0199"
        assert result["rating"] == 4.2
        assert result["review_count"] == 567
        assert result["primary_type"] == "Restaurant"
        assert result["source"] == "serpapi"


# ---------------------------------------------------------------------------
# Browser HTML Parsing
# ---------------------------------------------------------------------------


class TestBrowserParsing:

    def test_parse_maps_html_regex_fallback(self) -> None:
        """Regex fallback extracts business names from aria-labels."""
        connector = GoogleMapsConnector()
        html = '''
        <div aria-label="Joe's Coffee Shop"></div>
        <div aria-label="close"></div>
        <div aria-label="Best Pizza NYC"></div>
        <div aria-label="menu"></div>
        <div aria-label="Fancy Restaurant Downtown"></div>
        '''

        results = connector._parse_maps_html_regex(html, max_results=10)

        names = [r["name"] for r in results]
        assert "Joe's Coffee Shop" in names
        assert "Best Pizza NYC" in names
        assert "Fancy Restaurant Downtown" in names
        # UI labels should be filtered
        assert "close" not in names
        assert "menu" not in names

    def test_parse_captured_api_data(self) -> None:
        """Captured API data is parsed correctly."""
        connector = GoogleMapsConnector()
        api_data = [
            {
                "name": "Test Business",
                "rating": 4.8,
                "userRatingCount": 200,
                "formattedAddress": "100 Test Blvd",
                "phoneNumber": "+1-555-0000",
                "website": "https://test.com",
            },
            {
                "title": "Another Biz",
                "rating": 3.9,
                "address": "200 Demo St",
            },
        ]

        results = connector._parse_captured_api_data(api_data, max_results=10)

        assert len(results) == 2
        assert results[0]["name"] == "Test Business"
        assert results[0]["rating"] == 4.8
        assert results[0]["review_count"] == 200
        assert results[0]["address"] == "100 Test Blvd"
        assert results[1]["name"] == "Another Biz"


# ---------------------------------------------------------------------------
# Tier Fallback Logic
# ---------------------------------------------------------------------------


class TestTierFallback:

    @pytest.mark.asyncio
    async def test_tries_google_api_first(self) -> None:
        """With Google API key, tries Places API first."""
        connector = GoogleMapsConnector(google_api_key="test_key")

        with patch.object(connector, "_search_places_api", new_callable=AsyncMock) as mock_api:
            mock_api.return_value = [{"name": "From API", "source": "google_places_api"}]

            results = await connector.search_businesses("test query")

            mock_api.assert_called_once()
            assert len(results) == 1
            assert results[0]["source"] == "google_places_api"

    @pytest.mark.asyncio
    async def test_falls_through_to_serpapi(self) -> None:
        """If Places API returns empty, tries SerpAPI."""
        connector = GoogleMapsConnector(google_api_key="gk", serpapi_key="sk")

        with patch.object(connector, "_search_places_api", new_callable=AsyncMock) as mock_places:
            mock_places.return_value = []  # Empty — trigger fallthrough
            with patch.object(connector, "_search_serpapi", new_callable=AsyncMock) as mock_serp:
                mock_serp.return_value = [{"name": "From SerpAPI", "source": "serpapi"}]

                results = await connector.search_businesses("test query")

                mock_places.assert_called_once()
                mock_serp.assert_called_once()
                assert results[0]["source"] == "serpapi"

    @pytest.mark.asyncio
    async def test_falls_through_to_browser(self) -> None:
        """If both APIs fail, falls through to browser."""
        connector = GoogleMapsConnector(google_api_key="gk", serpapi_key="sk")

        with patch.object(connector, "_search_places_api", new_callable=AsyncMock) as mock_p:
            mock_p.return_value = []
            with patch.object(connector, "_search_serpapi", new_callable=AsyncMock) as mock_s:
                mock_s.return_value = []
                with patch.object(connector, "_search_browser", new_callable=AsyncMock) as mock_b:
                    mock_b.return_value = [{"name": "From Browser", "source": "browser_scrape"}]

                    results = await connector.search_businesses("test query")

                    mock_p.assert_called_once()
                    mock_s.assert_called_once()
                    mock_b.assert_called_once()
                    assert results[0]["source"] == "browser_scrape"

    @pytest.mark.asyncio
    async def test_no_keys_goes_straight_to_browser(self) -> None:
        """Without any API keys, goes directly to browser."""
        connector = GoogleMapsConnector()

        with patch.object(connector, "_search_browser", new_callable=AsyncMock) as mock_b:
            mock_b.return_value = [{"name": "Direct Browser"}]

            results = await connector.search_businesses("test query")

            mock_b.assert_called_once()

    @pytest.mark.asyncio
    async def test_location_appended_to_query(self) -> None:
        """Location param is appended to query if not already present."""
        connector = GoogleMapsConnector()

        with patch.object(connector, "_search_browser", new_callable=AsyncMock) as mock_b:
            mock_b.return_value = []

            await connector.search_businesses("restaurants", location="Dubai")

            call_args = mock_b.call_args[0]
            assert "Dubai" in call_args[0]

    @pytest.mark.asyncio
    async def test_location_not_duplicated(self) -> None:
        """Location not appended if already in query."""
        connector = GoogleMapsConnector()

        with patch.object(connector, "_search_browser", new_callable=AsyncMock) as mock_b:
            mock_b.return_value = []

            await connector.search_businesses("restaurants in Dubai", location="Dubai")

            call_args = mock_b.call_args[0]
            # Should NOT have "Dubai" twice
            assert call_args[0].count("Dubai") == 1


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:

    def test_initial_metrics_zero(self) -> None:
        connector = GoogleMapsConnector()
        metrics = connector.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
