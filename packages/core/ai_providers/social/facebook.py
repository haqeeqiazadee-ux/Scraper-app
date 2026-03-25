"""
Facebook platform-specific extractor.

Extracts structured data from Facebook pages by parsing:
1. Open Graph meta tags — most reliable for public content
2. Embedded JSON (require("ScheduledServerJS").handle) — rich data when available
3. JSON-LD structured data — sometimes present for business pages
4. DOM patterns — last resort for rendered content

Supports: reels, marketplace, pages/profiles

Note: Facebook has the most aggressive anti-bot systems among social platforms.
All extraction requires the hard-target lane with stealth browser + residential
proxies. DOM structure changes every 3-6 weeks, so this extractor prioritizes
meta tags and embedded data over CSS selectors.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from packages.core.ai_providers.social.base import (
    deep_get,
    extract_json_after_key,
    extract_meta_tags,
    extract_title,
    find_key_recursive,
    parse_count,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

FACEBOOK_DOMAINS = [
    "facebook.com", "www.facebook.com", "m.facebook.com",
    "web.facebook.com", "fb.com", "fb.watch",
]


class FacebookExtractor:
    """Extract structured data from Facebook HTML pages."""

    DOMAINS = FACEBOOK_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower()

        if "/reel/" in path or "/reels/" in path or "/reels" in path:
            return self._extract_reel(html, url)
        elif "/marketplace/" in path:
            return self._extract_marketplace(html, url)
        elif "/videos/" in path or "fb.watch" in (urlparse(url).hostname or ""):
            return self._extract_video(html, url)
        else:
            # For non-specific URLs, extract as page/profile
            return self._extract_page(html, url)

    # -------------------------------------------------------------------
    # Embedded data extraction
    # -------------------------------------------------------------------

    def _get_server_js_data(self, html: str) -> list[dict]:
        """Extract data from Facebook's ScheduledServerJS.handle calls.

        Facebook embeds page data in require("ScheduledServerJS").handle(...)
        calls within <script> tags. These contain the actual page data.
        """
        results = []
        pattern = re.compile(
            r'(?:ScheduledServerJS|ServerJS)\.handle(?:WithCustomApplyEach)?\((\{.+?\})\);',
            re.DOTALL,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1))
                results.append(data)
            except json.JSONDecodeError:
                continue
        return results

    def _get_relay_preloader(self, html: str) -> dict | None:
        """Extract data from __d("RelayPrefetchedStreamCache") patterns."""
        pattern = re.compile(
            r'__d\("RelayPrefetchedStreamCache"\).*?(\{.+?\})\s*\)',
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    def _extract_embedded_json(self, html: str) -> dict:
        """Try to find video/reel data embedded in the page.

        Returns a dict of any found data, searching multiple patterns.
        Uses balanced-brace extraction for correct nested JSON parsing.
        """
        data: dict[str, Any] = {}

        # Use balanced-brace extraction for each key
        keys_to_try = [
            ("video", "video"),
            ("short_form_video_context", "reel_context"),
            ("creation_story", "creation_story"),
            ("feedback", "feedback"),
        ]

        for json_key, result_key in keys_to_try:
            result = extract_json_after_key(html, json_key)
            if result:
                data[result_key] = result

        return data

    # -------------------------------------------------------------------
    # Reel extraction
    # -------------------------------------------------------------------

    def _extract_reel(self, html: str, url: str) -> list[dict]:
        """Extract reel data from a Facebook reel page."""
        meta = extract_meta_tags(html)
        embedded = self._extract_embedded_json(html)

        reel: dict[str, Any] = {"reel_url": url}

        # Extract reel ID from URL
        reel["reel_id"] = self._extract_reel_id(url)

        # --- From embedded JSON ---
        reel_ctx = embedded.get("reel_context", {})
        if reel_ctx:
            reel["play_count"] = reel_ctx.get("play_count")
            reel["caption"] = deep_get(reel_ctx, "video_label", "text")

        feedback = embedded.get("feedback", {})
        if feedback:
            # Reactions (likes)
            reaction_count = deep_get(feedback, "reaction_count", "count")
            if reaction_count:
                reel["like_count"] = reaction_count

            # Comments
            comment_count = deep_get(feedback, "comment_count", "total_count")
            if comment_count:
                reel["comment_count"] = comment_count

            # Shares
            share_count = deep_get(feedback, "share_count", "count")
            if share_count:
                reel["share_count"] = share_count

        video_data = embedded.get("video", {})
        if video_data:
            reel["play_count"] = reel.get("play_count") or video_data.get("play_count")
            reel["thumbnail_url"] = reel.get("thumbnail_url") or video_data.get("preferred_thumbnail", {}).get("image", {}).get("uri")

        # --- From meta tags (most reliable) ---
        if not reel.get("caption"):
            reel["caption"] = meta.get("og:title") or meta.get("og:description")
        if not reel.get("thumbnail_url"):
            reel["thumbnail_url"] = meta.get("og:image")

        # Try to extract author from meta
        if not reel.get("author_name"):
            reel["author_name"] = self._extract_author_from_meta(meta, html)

        # Parse engagement from og:description if not found in embedded data
        desc = meta.get("og:description") or ""
        if not reel.get("like_count"):
            like_match = re.search(r"([\d,\.]+[KMB]?)\s*(?:likes?|reactions?)", desc, re.IGNORECASE)
            if like_match:
                reel["like_count"] = parse_count(like_match.group(1))

        if not reel.get("comment_count"):
            comment_match = re.search(r"([\d,\.]+[KMB]?)\s*comments?", desc, re.IGNORECASE)
            if comment_match:
                reel["comment_count"] = parse_count(comment_match.group(1))

        if not reel.get("share_count"):
            share_match = re.search(r"([\d,\.]+[KMB]?)\s*shares?", desc, re.IGNORECASE)
            if share_match:
                reel["share_count"] = parse_count(share_match.group(1))

        # Video URL from meta
        video_url = meta.get("og:video") or meta.get("og:video:url")
        if video_url:
            reel["video_url"] = video_url

        # Timestamp
        timestamp = meta.get("article:published_time")
        if timestamp:
            reel["timestamp"] = timestamp

        reel = {k: v for k, v in reel.items() if v is not None}
        return [reel] if reel.get("caption") or reel.get("reel_id") else []

    # -------------------------------------------------------------------
    # Video extraction
    # -------------------------------------------------------------------

    def _extract_video(self, html: str, url: str) -> list[dict]:
        """Extract video data from a Facebook video page."""
        meta = extract_meta_tags(html)
        embedded = self._extract_embedded_json(html)

        video: dict[str, Any] = {"video_url": url}

        video["title"] = meta.get("og:title") or extract_title(html)
        video["description"] = meta.get("og:description")
        video["thumbnail_url"] = meta.get("og:image")
        video["download_url"] = meta.get("og:video") or meta.get("og:video:url")
        video["timestamp"] = meta.get("article:published_time")

        # From embedded data
        video_data = embedded.get("video", {})
        if video_data:
            video["play_count"] = video_data.get("play_count")

        feedback = embedded.get("feedback", {})
        if feedback:
            video["like_count"] = deep_get(feedback, "reaction_count", "count")
            video["comment_count"] = deep_get(feedback, "comment_count", "total_count")
            video["share_count"] = deep_get(feedback, "share_count", "count")

        # Author
        video["author_name"] = self._extract_author_from_meta(meta, html)

        video = {k: v for k, v in video.items() if v is not None}
        return [video] if video.get("title") else []

    # -------------------------------------------------------------------
    # Marketplace extraction
    # -------------------------------------------------------------------

    def _extract_marketplace(self, html: str, url: str) -> list[dict]:
        """Extract marketplace listing data."""
        meta = extract_meta_tags(html)

        item: dict[str, Any] = {"listing_url": url}

        item["title"] = meta.get("og:title") or extract_title(html)
        item["description"] = meta.get("og:description")
        item["image_url"] = meta.get("og:image")

        # Try to extract price from title or description
        text = f"{item.get('title', '')} {item.get('description', '')}"
        price_match = re.search(r'[\$\£\€\₹]\s*([\d,\.]+)', text)
        if price_match:
            item["price"] = price_match.group(1).replace(",", "")

        # Try embedded JSON for marketplace data
        mp_pattern = re.compile(
            r'"marketplace_listing_renderable_target"\s*:\s*(\{.+?\})\s*[,}]',
            re.DOTALL,
        )
        match = mp_pattern.search(html)
        if match:
            try:
                mp_data = json.loads(match.group(1))
                item["title"] = item.get("title") or mp_data.get("marketplace_listing_title")
                listing_price = mp_data.get("listing_price", {})
                if listing_price:
                    item["price"] = listing_price.get("amount")
                    item["currency"] = listing_price.get("currency")
                item["condition"] = mp_data.get("condition_text")
                item["location"] = deep_get(mp_data, "location", "reverse_geocode", "city_page", "display_name")

                seller = mp_data.get("marketplace_listing_seller", {})
                if seller:
                    item["seller_name"] = seller.get("name")
            except json.JSONDecodeError:
                pass

        item = {k: v for k, v in item.items() if v is not None}
        return [item] if item.get("title") else []

    # -------------------------------------------------------------------
    # Page/profile extraction
    # -------------------------------------------------------------------

    def _extract_page(self, html: str, url: str) -> list[dict]:
        """Extract page/profile data from a Facebook page."""
        meta = extract_meta_tags(html)

        page: dict[str, Any] = {"page_url": url}

        page["name"] = meta.get("og:title") or extract_title(html)
        page["description"] = meta.get("og:description") or meta.get("description")
        page["image_url"] = meta.get("og:image")
        page["page_type"] = meta.get("og:type")

        # Try JSON-LD for business pages
        jsonld = self._extract_jsonld(html)
        if jsonld:
            page["name"] = page.get("name") or jsonld.get("name")
            page["description"] = page.get("description") or jsonld.get("description")
            address = jsonld.get("address", {})
            if isinstance(address, dict):
                page["location"] = address.get("addressLocality")

        # Parse follower/like counts from description
        desc = page.get("description") or ""
        likes_match = re.search(r"([\d,\.]+[KMB]?)\s*(?:likes?|people like)", desc, re.IGNORECASE)
        if likes_match:
            page["like_count"] = parse_count(likes_match.group(1))

        followers_match = re.search(r"([\d,\.]+[KMB]?)\s*followers?", desc, re.IGNORECASE)
        if followers_match:
            page["follower_count"] = parse_count(followers_match.group(1))

        page = {k: v for k, v in page.items() if v is not None}
        return [page] if page.get("name") else []

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    def _extract_jsonld(self, html: str) -> dict | None:
        """Extract JSON-LD structured data from the page."""
        pattern = re.compile(
            r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        for match in pattern.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
                if isinstance(data, dict):
                    return data
                if isinstance(data, list) and data:
                    return data[0]
            except json.JSONDecodeError:
                continue
        return None

    @staticmethod
    def _extract_reel_id(url: str) -> str | None:
        """Extract reel ID from Facebook URL."""
        match = re.search(r"/reel/(\d+)", url)
        if match:
            return match.group(1)
        match = re.search(r"/reels/(\d+)", url)
        if match:
            return match.group(1)
        return None

    @staticmethod
    def _extract_author_from_meta(meta: dict, html: str) -> str | None:
        """Try to determine the content author from meta tags or HTML."""
        # og:title often contains "Author - Caption" for reels
        title = meta.get("og:title") or ""
        if " - " in title:
            return title.split(" - ")[0].strip()

        # article:author
        author = meta.get("article:author")
        if author:
            return author

        # Try page title
        page_title = extract_title(html) or ""
        if " | Facebook" in page_title:
            return page_title.split(" | Facebook")[0].strip()

        return None
