"""
Instagram platform-specific extractor.

Extracts structured data from Instagram pages by parsing:
1. window._sharedData — legacy but still sometimes present
2. window.__additionalDataLoaded — supplementary data
3. Embedded JSON-LD — structured data (limited)
4. Meta tags (og:*) — most reliable fallback for public pages
5. DOM data attributes — for rendered page content

Supports: reel, profile (stories), generic posts

Note: Instagram aggressively blocks scrapers. Most useful data requires
the hard-target lane with residential proxies. The GraphQL API endpoints
(doc_id based) change every 2-4 weeks and require session cookies, so this
extractor focuses on what can be parsed from the HTML response.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

from packages.core.ai_providers.social.base import (
    deep_get,
    extract_json_after_key,
    extract_json_from_script,
    extract_meta_tags,
    extract_title,
    find_key_recursive,
    parse_count,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

INSTAGRAM_DOMAINS = ["instagram.com", "www.instagram.com", "m.instagram.com"]


class InstagramExtractor:
    """Extract structured data from Instagram HTML pages."""

    DOMAINS = INSTAGRAM_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower().rstrip("/")

        if "/reel/" in path or "/reels/" in path:
            return self._extract_reel(html, url)
        elif "/p/" in path:
            return self._extract_post(html, url)
        elif "/stories/" in path:
            return self._extract_stories(html, url)
        elif path.startswith("/@") or self._is_profile_url(path):
            return self._extract_profile(html, url)
        else:
            # Try reel extraction first (reels listing page), then generic
            result = self._extract_reel(html, url)
            if result and len(result[0]) > 2:
                return result
            return self._extract_generic(html, url)

    # -------------------------------------------------------------------
    # Data sources
    # -------------------------------------------------------------------

    def _get_shared_data(self, html: str) -> dict | None:
        """Extract window._sharedData from Instagram page."""
        # Pattern: window._sharedData = {...};
        pattern = re.compile(
            r"window\._sharedData\s*=\s*(\{.+?\});\s*</script>",
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    def _get_additional_data(self, html: str) -> dict | None:
        """Extract window.__additionalDataLoaded from Instagram page."""
        pattern = re.compile(
            r"window\.__additionalDataLoaded\s*\(\s*['\"].*?['\"]\s*,\s*(\{.+?\})\s*\)\s*;",
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return None

    def _get_relay_data(self, html: str) -> dict | None:
        """Extract __relay_data or similar React/Relay hydration payloads."""
        # Instagram sometimes uses require("ScheduledServerJS").handle patterns
        pattern = re.compile(
            r'"xdt_api__v1__media__shortcode__web_info":\s*(\{.+?\})\s*[,}]',
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # Also try for user profile data
        pattern2 = re.compile(
            r'"xdt_api__v1__users__web_profile_info":\s*(\{.+?\})\s*[,}]',
            re.DOTALL,
        )
        match = pattern2.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    def _get_graphql_data(self, html: str) -> dict | None:
        """Try to find embedded GraphQL response data in the page."""
        # Use balanced-brace extraction for nested JSON objects
        for key in ("shortcode_media", "xdt_shortcode_media"):
            result = extract_json_after_key(html, key)
            if result:
                return result
        return None

    # -------------------------------------------------------------------
    # Reel extraction
    # -------------------------------------------------------------------

    def _extract_reel(self, html: str, url: str) -> list[dict]:
        """Extract reel data from an Instagram reel page."""
        shared = self._get_shared_data(html)
        additional = self._get_additional_data(html)
        graphql = self._get_graphql_data(html)
        meta = extract_meta_tags(html)

        reel: dict[str, Any] = {"reel_url": url}

        # Try GraphQL embedded data first
        media = None
        if graphql:
            media = graphql
        elif shared:
            media = deep_get(shared, "entry_data", "PostPage", "0", "graphql", "shortcode_media")
        elif additional:
            media = deep_get(additional, "graphql", "shortcode_media")

        if media:
            self._parse_media(media, reel)

        # Relay data fallback
        if not reel.get("caption"):
            relay = self._get_relay_data(html)
            if relay:
                items = deep_get(relay, "items")
                if isinstance(items, list) and items:
                    self._parse_api_item(items[0], reel)

        # Meta tag fallbacks
        if not reel.get("caption"):
            desc = meta.get("og:description") or meta.get("description") or ""
            # Instagram descriptions often have format: "X likes, Y comments - Author..."
            reel["caption"] = self._clean_ig_description(desc)

        if not reel.get("reel_id"):
            reel["reel_id"] = self._extract_shortcode(url)

        if not reel.get("thumbnail_url"):
            reel["thumbnail_url"] = meta.get("og:image")

        if not reel.get("author_username"):
            # Try to extract from og:title or description
            title = meta.get("og:title") or ""
            username_match = re.search(r"@(\w+)", title)
            if username_match:
                reel["author_username"] = username_match.group(1)
            elif " on Instagram" in title:
                reel["author_username"] = title.split(" on Instagram")[0].strip()

        # Parse engagement from description if not found
        if not reel.get("like_count"):
            desc = meta.get("og:description") or ""
            like_match = re.search(r"([\d,\.]+[KMB]?)\s*likes?", desc, re.IGNORECASE)
            if like_match:
                reel["like_count"] = parse_count(like_match.group(1))

        if not reel.get("comment_count"):
            desc = meta.get("og:description") or ""
            comment_match = re.search(r"([\d,\.]+[KMB]?)\s*comments?", desc, re.IGNORECASE)
            if comment_match:
                reel["comment_count"] = parse_count(comment_match.group(1))

        # Extract hashtags and mentions from caption
        if reel.get("caption"):
            if not reel.get("hashtags"):
                reel["hashtags"] = re.findall(r"#(\w+)", reel["caption"])
            if not reel.get("mentions"):
                reel["mentions"] = re.findall(r"@(\w+)", reel["caption"])

        reel = {k: v for k, v in reel.items() if v is not None}
        return [reel] if reel.get("caption") or reel.get("reel_id") else []

    # -------------------------------------------------------------------
    # Post extraction
    # -------------------------------------------------------------------

    def _extract_post(self, html: str, url: str) -> list[dict]:
        """Extract post data — shares same structure as reels for single media."""
        return self._extract_reel(html, url)

    # -------------------------------------------------------------------
    # Stories extraction
    # -------------------------------------------------------------------

    def _extract_stories(self, html: str, url: str) -> list[dict]:
        """Extract stories data from an Instagram stories page.

        Note: Stories require authentication to view. This extracts whatever
        metadata is available from the page HTML (usually just the username).
        """
        meta = extract_meta_tags(html)
        shared = self._get_shared_data(html)

        story: dict[str, Any] = {"url": url}

        # Extract username from URL (/stories/username/)
        match = re.search(r"/stories/([^/?]+)", url)
        if match:
            story["username"] = match.group(1)

        story["title"] = meta.get("og:title") or extract_title(html)
        story["description"] = meta.get("og:description")
        story["thumbnail_url"] = meta.get("og:image")

        # If sharedData has story items
        if shared:
            story_data = deep_get(shared, "entry_data", "StoriesPage", "0")
            if story_data:
                user = deep_get(story_data, "user")
                if user:
                    story["username"] = user.get("username")
                    story["author_followers"] = user.get("edge_followed_by", {}).get("count")

        story = {k: v for k, v in story.items() if v is not None}
        return [story] if story.get("username") or story.get("title") else []

    # -------------------------------------------------------------------
    # Profile extraction
    # -------------------------------------------------------------------

    def _extract_profile(self, html: str, url: str) -> list[dict]:
        """Extract profile data from an Instagram profile page."""
        shared = self._get_shared_data(html)
        relay = self._get_relay_data(html)
        meta = extract_meta_tags(html)

        profile: dict[str, Any] = {"profile_url": url}

        # From _sharedData
        if shared:
            user = deep_get(shared, "entry_data", "ProfilePage", "0", "graphql", "user")
            if user:
                profile["username"] = user.get("username")
                profile["full_name"] = user.get("full_name")
                profile["bio"] = user.get("biography")
                profile["follower_count"] = deep_get(user, "edge_followed_by", "count")
                profile["following_count"] = deep_get(user, "edge_follow", "count")
                profile["post_count"] = deep_get(user, "edge_owner_to_timeline_media", "count")
                profile["verified"] = user.get("is_verified", False)
                profile["avatar_url"] = user.get("profile_pic_url_hd") or user.get("profile_pic_url")

        # From relay data
        if relay and not profile.get("username"):
            user_data = deep_get(relay, "data", "user")
            if user_data:
                profile["username"] = user_data.get("username")
                profile["full_name"] = user_data.get("full_name")
                profile["bio"] = user_data.get("biography")
                profile["verified"] = user_data.get("is_verified", False)

        # Fallback to meta tags
        if not profile.get("username"):
            # Try to extract from URL
            profile["username"] = self._extract_username(url)
        if not profile.get("full_name"):
            title = meta.get("og:title") or ""
            if "(" in title and ")" in title:
                profile["full_name"] = title.split("(")[0].strip()
        if not profile.get("bio"):
            profile["bio"] = meta.get("og:description") or meta.get("description")
        if not profile.get("avatar_url"):
            profile["avatar_url"] = meta.get("og:image")

        # Parse follower counts from meta description
        desc = meta.get("og:description") or meta.get("description") or ""
        if not profile.get("follower_count"):
            follower_match = re.search(r"([\d,\.]+[KMB]?)\s*Followers?", desc, re.IGNORECASE)
            if follower_match:
                profile["follower_count"] = parse_count(follower_match.group(1))
        if not profile.get("following_count"):
            following_match = re.search(r"([\d,\.]+[KMB]?)\s*Following", desc, re.IGNORECASE)
            if following_match:
                profile["following_count"] = parse_count(following_match.group(1))
        if not profile.get("post_count"):
            post_match = re.search(r"([\d,\.]+[KMB]?)\s*Posts?", desc, re.IGNORECASE)
            if post_match:
                profile["post_count"] = parse_count(post_match.group(1))

        profile = {k: v for k, v in profile.items() if v is not None}
        return [profile] if profile.get("username") else []

    # -------------------------------------------------------------------
    # Generic extraction
    # -------------------------------------------------------------------

    def _extract_generic(self, html: str, url: str) -> list[dict]:
        """Fallback extraction for any Instagram page."""
        meta = extract_meta_tags(html)
        result: dict[str, Any] = {"url": url}

        result["title"] = meta.get("og:title") or extract_title(html)
        result["description"] = meta.get("og:description") or meta.get("description")
        result["thumbnail_url"] = meta.get("og:image")

        # Try to extract any engagement metrics from description
        desc = result.get("description") or ""
        like_match = re.search(r"([\d,\.]+[KMB]?)\s*likes?", desc, re.IGNORECASE)
        if like_match:
            result["like_count"] = parse_count(like_match.group(1))

        result = {k: v for k, v in result.items() if v is not None}
        return [result] if result.get("title") else []

    # -------------------------------------------------------------------
    # Parsing helpers
    # -------------------------------------------------------------------

    def _parse_media(self, media: dict, result: dict) -> None:
        """Parse GraphQL shortcode_media into our standard fields."""
        result["reel_id"] = media.get("shortcode")
        result["view_count"] = media.get("video_view_count")
        result["like_count"] = deep_get(media, "edge_media_preview_like", "count")
        result["comment_count"] = deep_get(media, "edge_media_to_parent_comment", "count")

        # Caption
        caption_edges = deep_get(media, "edge_media_to_caption", "edges")
        if caption_edges and isinstance(caption_edges, list) and caption_edges:
            result["caption"] = deep_get(caption_edges, "0", "node", "text")

        # Author
        owner = media.get("owner", {})
        if owner:
            result["author_username"] = owner.get("username")
            result["author_followers"] = deep_get(owner, "edge_followed_by", "count")

        # Timestamps
        result["timestamp"] = parse_timestamp(media.get("taken_at_timestamp"))

        # Thumbnail
        result["thumbnail_url"] = media.get("display_url") or media.get("thumbnail_src")

        # Video URL (if available)
        if media.get("is_video"):
            result["download_url"] = media.get("video_url")

        # Music
        music = media.get("clips_music_attribution_info")
        if music:
            result["music_name"] = music.get("song_name") or music.get("artist_name")

    def _parse_api_item(self, item: dict, result: dict) -> None:
        """Parse Instagram API v1 media item format."""
        result["reel_id"] = item.get("code") or item.get("pk")

        # Caption
        caption = item.get("caption", {})
        if isinstance(caption, dict):
            result["caption"] = caption.get("text")

        # Counts
        result["like_count"] = item.get("like_count")
        result["comment_count"] = item.get("comment_count")
        result["view_count"] = item.get("play_count") or item.get("view_count")

        # Author
        user = item.get("user", {})
        if user:
            result["author_username"] = user.get("username")

        # Media
        image_versions = item.get("image_versions2", {})
        candidates = image_versions.get("candidates", [])
        if candidates:
            result["thumbnail_url"] = candidates[0].get("url")

        video_versions = item.get("video_versions", [])
        if video_versions:
            result["download_url"] = video_versions[0].get("url")

        result["timestamp"] = parse_timestamp(item.get("taken_at"))

    @staticmethod
    def _clean_ig_description(desc: str) -> str:
        """Clean Instagram meta description to extract actual caption."""
        if not desc:
            return ""
        # Remove "X likes, Y comments - Username: " prefix
        cleaned = re.sub(
            r"^[\d,\.]+[KMB]?\s*likes?,?\s*[\d,\.]+[KMB]?\s*comments?\s*-\s*\w+:\s*",
            "",
            desc,
            flags=re.IGNORECASE,
        )
        # Remove "on Instagram: " prefix
        cleaned = re.sub(r"^.*?on Instagram:\s*", "", cleaned, flags=re.IGNORECASE)
        return cleaned.strip(' "\'')

    @staticmethod
    def _extract_shortcode(url: str) -> str | None:
        """Extract post/reel shortcode from Instagram URL."""
        patterns = [
            r"/reel/([^/?]+)",
            r"/reels?/([^/?]+)",
            r"/p/([^/?]+)",
            r"/tv/([^/?]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract username from Instagram profile URL."""
        path = urlparse(url).path.strip("/")
        # Ignore known non-profile paths
        non_profile = {"explore", "reels", "stories", "p", "reel", "tv", "accounts", "direct"}
        segments = path.split("/")
        if segments and segments[0] not in non_profile:
            return segments[0]
        return None

    @staticmethod
    def _is_profile_url(path: str) -> bool:
        """Check if a URL path looks like a profile URL."""
        path = path.strip("/")
        if not path:
            return False
        non_profile = {"explore", "reels", "stories", "p", "reel", "tv", "accounts", "direct"}
        segments = path.split("/")
        return len(segments) <= 2 and segments[0] not in non_profile
