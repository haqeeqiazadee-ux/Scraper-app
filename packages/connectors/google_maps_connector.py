"""
Google Maps Connector — scrape business data from Google Maps by keyword.

Three-tier approach for maximum reliability:
1. Serper Places API (primary) — free with Serper key, fast and reliable
2. Google Places API (secondary) — official, structured, reliable ($0.032/request)
3. Direct browser scraping (fallback) — free but harder, uses our stealth stack

The user provides a query like "restaurants in Dubai" and gets structured
business data: name, address, phone, rating, reviews, website, hours, etc.

Usage:
    connector = GoogleMapsConnector(google_api_key="your_key")
    results = await connector.search_businesses("plumbers in London", max_results=20)

    # Or free with Serper key
    connector = GoogleMapsConnector()  # uses SERPER_API_KEY env var
    results = await connector.search_businesses("coffee shops in New York")

    # Or free (browser scraping)
    connector = GoogleMapsConnector()
    results = await connector.search_businesses("coffee shops in New York")
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Optional
from urllib.parse import quote_plus

from packages.core.interfaces import ConnectorMetrics

logger = logging.getLogger(__name__)

# Google Places API (New) base URL
PLACES_API_BASE = "https://places.googleapis.com/v1/places"
PLACES_API_SEARCH = f"{PLACES_API_BASE}:searchText"
PLACES_API_NEARBY = f"{PLACES_API_BASE}:searchNearby"

# Fields to request from Places API (controls billing)
PLACES_BASIC_FIELDS = [
    "places.id",
    "places.displayName",
    "places.formattedAddress",
    "places.location",
    "places.types",
    "places.primaryType",
    "places.googleMapsUri",
]

PLACES_CONTACT_FIELDS = [
    "places.nationalPhoneNumber",
    "places.internationalPhoneNumber",
    "places.websiteUri",
]

PLACES_ADVANCED_FIELDS = [
    "places.rating",
    "places.userRatingCount",
    "places.priceLevel",
    "places.businessStatus",
    "places.currentOpeningHours",
    "places.regularOpeningHours",
]

ALL_PLACES_FIELDS = PLACES_BASIC_FIELDS + PLACES_CONTACT_FIELDS + PLACES_ADVANCED_FIELDS


class BusinessResult:
    """Structured business data from Google Maps."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def to_dict(self) -> dict:
        return dict(self._data)

    def __repr__(self) -> str:
        return f"BusinessResult({self._data.get('name', 'Unknown')})"


class GoogleMapsConnector:
    """Google Maps business data connector.

    Three tiers:
    1. Serper Places API (needs SERPER_API_KEY, free)
    2. Google Places API (needs GOOGLE_MAPS_API_KEY)
    3. Direct browser scraping (free, uses our stealth browser stack)

    Falls through tiers automatically if a tier is unavailable or fails.
    """

    def __init__(
        self,
        google_api_key: Optional[str] = None,
        max_results: int = 20,
    ) -> None:
        self._google_api_key = google_api_key or os.environ.get("GOOGLE_MAPS_API_KEY", "")
        self._max_results = max_results
        self._metrics = ConnectorMetrics()
        self._http_client = None

    async def _get_http_client(self) -> Any:
        """Get an async HTTP client (curl_cffi preferred, httpx fallback)."""
        if self._http_client is not None:
            return self._http_client, self._client_type

        try:
            from curl_cffi.requests import AsyncSession
            self._http_client = AsyncSession(timeout=30)
            self._client_type = "curl_cffi"
        except ImportError:
            import httpx
            self._http_client = httpx.AsyncClient(timeout=30.0)
            self._client_type = "httpx"
        return self._http_client, self._client_type

    # ---- Main Search Method -----------------------------------------------

    async def search_businesses(
        self,
        query: str,
        max_results: Optional[int] = None,
        location: Optional[str] = None,
        language: str = "en",
    ) -> list[dict]:
        """Search for businesses on Google Maps.

        Automatically tries tiers in order:
        1. Serper Places API (free, if SERPER_API_KEY configured)
        2. Google Places API (if key configured)
        3. Browser scraping (always available)

        Args:
            query: Search query (e.g., "restaurants in Dubai", "plumbers near me").
            max_results: Maximum results to return (default 20).
            location: Optional location bias (e.g., "Dubai, UAE"). If not in query.
            language: Language code for results (default "en").

        Returns:
            List of business dicts with standardized fields.
        """
        max_results = max_results or self._max_results
        full_query = f"{query} {location}" if location and location.lower() not in query.lower() else query

        # Tier 1: Serper Places API (free)
        logger.info("Google Maps: trying Serper Places for '%s'", full_query)
        results = await self._search_serper_places(full_query, max_results)
        if results:
            return results
        logger.warning("Serper Places returned no results, falling through")

        # Tier 2: Google Places API
        if self._google_api_key:
            logger.info("Google Maps: trying Places API for '%s'", full_query)
            results = await self._search_places_api(full_query, max_results, language)
            if results:
                return results
            logger.warning("Places API returned no results, falling through")

        # Tier 3: Browser scraping
        logger.info("Google Maps: trying browser scraping for '%s'", full_query)
        results = await self._search_browser(full_query, max_results)
        return results

    # ---- Tier 1: Serper Places API (free) ----------------------------------

    async def _search_serper_places(self, query: str, max_results: int) -> list[dict]:
        """Search via Serper.dev Places API (free, included with Serper key)."""
        api_key = os.environ.get("SERPER_API_KEY", "")
        if not api_key:
            return []

        try:
            client, client_type = await self._get_http_client()
            if client_type == "curl_cffi":
                resp = await client.post(
                    "https://google.serper.dev/places",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": min(max_results, 20)},
                )
            else:
                resp = await client.post(
                    "https://google.serper.dev/places",
                    headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
                    json={"q": query, "num": min(max_results, 20)},
                )
            if resp.status_code != 200:
                return []

            data = resp.json() if hasattr(resp, 'json') and callable(resp.json) else json.loads(resp.text)
            places = data.get("places", [])
            results = []
            for p in places[:max_results]:
                results.append({
                    "name": p.get("title", ""),
                    "address": p.get("address", ""),
                    "rating": p.get("rating"),
                    "reviews_count": p.get("ratingCount"),
                    "phone": p.get("phoneNumber", ""),
                    "website": p.get("website", ""),
                    "category": p.get("category", ""),
                    "hours": p.get("openingHours", ""),
                    "latitude": p.get("latitude"),
                    "longitude": p.get("longitude"),
                    "place_id": p.get("cid", ""),
                    "source": "serper_places",
                })
            return results
        except Exception as e:
            logger.warning("Serper Places search failed: %s", e)
            return []

    # ---- Tier 2: Google Places API (New) ----------------------------------

    async def _search_places_api(
        self,
        query: str,
        max_results: int,
        language: str = "en",
    ) -> list[dict]:
        """Search using Google Places API (New) Text Search endpoint.

        Pricing: ~$0.032 per request (Text Search), up to 20 results per page.
        """
        self._metrics.total_requests += 1
        client, client_type = await self._get_http_client()

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self._google_api_key,
            "X-Goog-FieldMask": ",".join(ALL_PLACES_FIELDS),
        }

        body = {
            "textQuery": query,
            "languageCode": language,
            "maxResultCount": min(max_results, 20),  # API max is 20 per page
        }

        all_results: list[dict] = []

        try:
            if client_type == "curl_cffi":
                resp = await client.post(PLACES_API_SEARCH, headers=headers, json=body)
            else:
                resp = await client.post(PLACES_API_SEARCH, headers=headers, json=body)

            if resp.status_code != 200:
                logger.warning("Places API error: %d", resp.status_code)
                self._metrics.failed_requests += 1
                return []

            data = json.loads(resp.text) if isinstance(resp.text, str) else resp.json()
            places = data.get("places", [])

            for place in places:
                business = self._transform_places_api_result(place)
                all_results.append(business)

            # Handle pagination for more results
            next_token = data.get("nextPageToken")
            while next_token and len(all_results) < max_results:
                await asyncio.sleep(2)  # Google requires delay between pages
                body["pageToken"] = next_token
                if client_type == "curl_cffi":
                    resp = await client.post(PLACES_API_SEARCH, headers=headers, json=body)
                else:
                    resp = await client.post(PLACES_API_SEARCH, headers=headers, json=body)

                if resp.status_code != 200:
                    break

                data = json.loads(resp.text) if isinstance(resp.text, str) else resp.json()
                for place in data.get("places", []):
                    if len(all_results) >= max_results:
                        break
                    all_results.append(self._transform_places_api_result(place))
                next_token = data.get("nextPageToken")

            self._metrics.successful_requests += 1
            logger.info("Places API returned %d businesses for '%s'", len(all_results), query)
            return all_results

        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Places API request failed: %s", e)
            return []

    def _transform_places_api_result(self, place: dict) -> dict:
        """Transform Places API (New) response to our standard format."""
        display_name = place.get("displayName", {})
        location = place.get("location", {})

        business: dict[str, Any] = {
            "name": display_name.get("text", "") if isinstance(display_name, dict) else str(display_name),
            "place_id": place.get("id", ""),
            "address": place.get("formattedAddress", ""),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "phone": place.get("nationalPhoneNumber", "") or place.get("internationalPhoneNumber", ""),
            "website": place.get("websiteUri", ""),
            "rating": place.get("rating"),
            "review_count": place.get("userRatingCount"),
            "business_status": place.get("businessStatus", ""),
            "price_level": place.get("priceLevel", ""),
            "types": place.get("types", []),
            "primary_type": place.get("primaryType", ""),
            "google_maps_url": place.get("googleMapsUri", ""),
            "source": "google_places_api",
        }

        # Opening hours
        hours = place.get("currentOpeningHours") or place.get("regularOpeningHours")
        if hours:
            business["open_now"] = hours.get("openNow")
            periods = hours.get("periods", [])
            if periods:
                business["hours"] = self._format_hours(periods)
            weekday_text = hours.get("weekdayDescriptions", [])
            if weekday_text:
                business["hours_text"] = weekday_text

        return business

    def _format_hours(self, periods: list) -> list[dict]:
        """Format opening hours periods."""
        formatted = []
        for period in periods:
            entry: dict[str, Any] = {}
            open_info = period.get("open", {})
            close_info = period.get("close", {})
            if open_info:
                entry["day"] = open_info.get("day", 0)
                entry["open"] = f"{open_info.get('hour', 0):02d}:{open_info.get('minute', 0):02d}"
            if close_info:
                entry["close"] = f"{close_info.get('hour', 0):02d}:{close_info.get('minute', 0):02d}"
            formatted.append(entry)
        return formatted

    # ---- Tier 3: Browser Scraping -----------------------------------------

    async def _search_browser(self, query: str, max_results: int) -> list[dict]:
        """Scrape Google Maps directly using our stealth browser stack.

        Free but slower. Uses Playwright with device profiles, resource
        blocking, and human behavioral simulation.
        """
        self._metrics.total_requests += 1

        try:
            from packages.connectors.browser_worker import PlaywrightBrowserWorker
            from packages.core.interfaces import FetchRequest

            worker = PlaywrightBrowserWorker(
                headless=True,
                block_resources=True,
                intercept_api=True,
            )

            # Build Google Maps search URL
            maps_url = f"https://www.google.com/maps/search/{quote_plus(query)}"

            request = FetchRequest(url=maps_url, timeout_ms=30000)
            response = await worker.fetch(request)

            if not response.ok:
                logger.warning("Browser Maps scrape failed: %s", response.error)
                self._metrics.failed_requests += 1
                await worker.close()
                return []

            # Check if API interception captured JSON data
            api_data = worker.get_captured_api_data()
            if api_data:
                results = self._parse_captured_api_data(api_data, max_results)
                if results:
                    await worker.close()
                    self._metrics.successful_requests += 1
                    logger.info("Browser captured %d businesses from API interception", len(results))
                    return results

            # Fall back to HTML parsing
            html = response.html
            results = self._parse_maps_html(html, max_results)

            await worker.close()
            self._metrics.successful_requests += 1
            logger.info("Browser scraped %d businesses from HTML for '%s'", len(results), query)
            return results

        except Exception as e:
            self._metrics.failed_requests += 1
            self._metrics.last_error = str(e)
            logger.warning("Browser Maps scrape failed: %s", e)
            return []

    def _parse_maps_html(self, html: str, max_results: int) -> list[dict]:
        """Parse business listings from Google Maps HTML."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return self._parse_maps_html_regex(html, max_results)

        soup = BeautifulSoup(html, "html.parser")
        results: list[dict] = []

        # Google Maps renders business cards in divs with specific attributes
        # Try multiple selector strategies
        card_selectors = [
            'div[jsaction*="mouseover:pane"]',
            'div[class*="Nv2PK"]',
            'a[href*="/maps/place/"]',
            'div[role="article"]',
            'div[data-result-index]',
        ]

        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if len(cards) >= 2:
                break

        for card in cards[:max_results]:
            business = self._extract_business_from_card(card)
            if business.get("name"):
                results.append(business)

        return results

    def _extract_business_from_card(self, card: Any) -> dict:
        """Extract business data from a single Maps card element."""
        business: dict[str, Any] = {"source": "browser_scrape"}

        # Name — usually in an aria-label or heading
        name_el = card.select_one('[class*="fontHeadlineSmall"], [class*="qBF1Pd"], h3, [aria-label]')
        if name_el:
            business["name"] = name_el.get("aria-label") or name_el.get_text(strip=True)

        # Rating
        rating_el = card.select_one('[class*="MW4etd"], [role="img"][aria-label*="star"]')
        if rating_el:
            rating_text = rating_el.get("aria-label") or rating_el.get_text(strip=True)
            match = re.search(r"([\d.]+)", rating_text)
            if match:
                business["rating"] = float(match.group(1))

        # Review count
        review_el = card.select_one('[class*="UY7F9"], [aria-label*="review"]')
        if review_el:
            review_text = review_el.get("aria-label") or review_el.get_text(strip=True)
            match = re.search(r"([\d,]+)", review_text.replace(",", ""))
            if match:
                business["review_count"] = int(match.group(1))

        # Address
        addr_el = card.select_one('[class*="W4Efsd"]:nth-of-type(2), [class*="CCi"]')
        if addr_el:
            text = addr_el.get_text(strip=True)
            # Address is usually after the category separator
            parts = text.split("·")
            if len(parts) > 1:
                business["address"] = parts[-1].strip()
            else:
                business["address"] = text

        # Google Maps URL
        link = card.select_one('a[href*="/maps/place/"]')
        if link:
            business["google_maps_url"] = link.get("href", "")

        # Business type/category
        type_el = card.select_one('[class*="W4Efsd"]')
        if type_el:
            type_text = type_el.get_text(strip=True)
            parts = type_text.split("·")
            if parts:
                business["primary_type"] = parts[0].strip()

        return business

    def _parse_maps_html_regex(self, html: str, max_results: int) -> list[dict]:
        """Regex fallback when BeautifulSoup is not available."""
        results: list[dict] = []

        # Extract business names from aria-labels
        names = re.findall(r'aria-label="([^"]{3,80})"', html)
        # Filter likely business names (exclude UI labels)
        ui_labels = {"close", "search", "menu", "directions", "share", "save", "zoom"}
        names = [n for n in names if n.lower() not in ui_labels and len(n) > 3]

        for name in names[:max_results]:
            results.append({"name": name, "source": "browser_scrape_regex"})

        return results

    def _parse_captured_api_data(self, api_data: list, max_results: int) -> list[dict]:
        """Parse business data from captured Google Maps API responses."""
        results: list[dict] = []

        for item in api_data[:max_results]:
            if not isinstance(item, dict):
                continue
            # Google's internal API returns nested arrays, try to extract
            business: dict[str, Any] = {"source": "browser_api_intercept"}

            # Try common field patterns in captured data
            for key in ("name", "title", "displayName"):
                if item.get(key):
                    val = item[key]
                    business["name"] = val.get("text", val) if isinstance(val, dict) else str(val)
                    break

            if item.get("rating"):
                business["rating"] = item["rating"]
            if item.get("userRatingCount") or item.get("reviews"):
                business["review_count"] = item.get("userRatingCount") or item.get("reviews")
            if item.get("formattedAddress") or item.get("address"):
                business["address"] = item.get("formattedAddress") or item.get("address")
            if item.get("phoneNumber") or item.get("phone"):
                business["phone"] = item.get("phoneNumber") or item.get("phone")
            if item.get("website") or item.get("websiteUri"):
                business["website"] = item.get("website") or item.get("websiteUri")

            if business.get("name"):
                results.append(business)

        return results

    # ---- Place Details (single business) ----------------------------------

    async def get_business_details(self, place_id: str) -> Optional[dict]:
        """Get detailed info for a single business by Place ID.

        Uses Places API if available, otherwise returns None.
        """
        if not self._google_api_key:
            logger.warning("Place details requires Google API key")
            return None

        client, client_type = await self._get_http_client()
        url = f"{PLACES_API_BASE}/{place_id}"

        detail_fields = [
            "id", "displayName", "formattedAddress", "location",
            "nationalPhoneNumber", "internationalPhoneNumber",
            "websiteUri", "rating", "userRatingCount",
            "businessStatus", "priceLevel", "types", "primaryType",
            "googleMapsUri", "currentOpeningHours", "regularOpeningHours",
            "reviews", "photos", "editorialSummary",
        ]

        headers = {
            "X-Goog-Api-Key": self._google_api_key,
            "X-Goog-FieldMask": ",".join(detail_fields),
        }

        try:
            if client_type == "curl_cffi":
                resp = await client.get(url, headers=headers)
            else:
                resp = await client.get(url, headers=headers)

            if resp.status_code != 200:
                return None

            data = json.loads(resp.text) if isinstance(resp.text, str) else resp.json()
            business = self._transform_places_api_result(data)

            # Add detail-specific fields
            if data.get("editorialSummary"):
                business["description"] = data["editorialSummary"].get("text", "")
            if data.get("reviews"):
                business["reviews"] = [
                    {
                        "author": r.get("authorAttribution", {}).get("displayName", ""),
                        "rating": r.get("rating"),
                        "text": r.get("text", {}).get("text", "") if isinstance(r.get("text"), dict) else r.get("text", ""),
                        "time": r.get("publishTime", ""),
                    }
                    for r in data["reviews"][:5]
                ]
            if data.get("photos"):
                business["photos"] = [
                    p.get("name", "") for p in data["photos"][:5]
                ]

            return business
        except Exception as e:
            logger.warning("Place details failed: %s", e)
            return None

    # ---- Google Sheets Integration ----------------------------------------

    async def search_and_save_to_sheets(
        self,
        query: str,
        sheets_connector: Any,
        worksheet_name: str = "Maps Results",
        max_results: int = 20,
    ) -> list[dict]:
        """Search for businesses and save results to Google Sheets.

        Args:
            query: Search query.
            sheets_connector: GoogleSheetsConnector instance.
            worksheet_name: Sheet tab name for results.
            max_results: Max results.

        Returns:
            List of business dicts (also written to sheet).
        """
        results = await self.search_businesses(query, max_results=max_results)

        if results and sheets_connector:
            # Create a Maps-specific sheet connector with appropriate headers
            try:
                await sheets_connector.initialize()
                # Write results
                for r in results:
                    r["search_query"] = query
                    r["scraped_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                await sheets_connector.write_products(results)
                logger.info("Saved %d Maps results to Google Sheet", len(results))
            except Exception as e:
                logger.warning("Failed to save Maps results to sheet: %s", e)

        return results

    # ---- Protocol Methods -------------------------------------------------

    def get_metrics(self) -> ConnectorMetrics:
        return self._metrics

    async def health_check(self) -> bool:
        """Check if at least one tier is available."""
        return bool(os.environ.get("SERPER_API_KEY") or self._google_api_key or True)  # Browser always available

    async def close(self) -> None:
        """Clean up resources."""
        if self._http_client:
            if self._client_type == "curl_cffi":
                await self._http_client.close()
            else:
                await self._http_client.aclose()
            self._http_client = None
