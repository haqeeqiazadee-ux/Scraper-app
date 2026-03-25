"""
YouTube platform-specific extractor.

Extracts structured data from YouTube pages by parsing:
1. ytInitialPlayerResponse — core video metadata (title, views, duration, description)
2. ytInitialData — engagement data (likes, comments, subscribers, upload date)
3. Meta tags — fallback for title, description, thumbnail
4. DOM selectors — last resort for rendered pages

Supports: video, channel, comments, transcript, shorts, search, trending
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import parse_qs, urlparse

from packages.core.ai_providers.social.base import (
    deep_get,
    extract_json_from_script,
    extract_meta_tags,
    extract_title,
    find_key_recursive,
    parse_count,
    parse_duration,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

# Domains this extractor handles
YOUTUBE_DOMAINS = ["youtube.com", "youtu.be", "m.youtube.com"]


class YouTubeExtractor:
    """Extract structured data from YouTube HTML pages."""

    DOMAINS = YOUTUBE_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower()
        query = parse_qs(urlparse(url).query)

        if "/watch" in path or "youtu.be" in urlparse(url).hostname or "":
            return self._extract_video(html, url)
        elif "/shorts/" in path:
            return self._extract_video(html, url)  # Shorts use same data structure
        elif "/@" in path or "/channel/" in path or "/c/" in path or "/user/" in path:
            return self._extract_channel(html, url)
        elif "/results" in path:
            return self._extract_search(html, url)
        elif "/feed/trending" in path:
            return self._extract_trending(html, url)
        else:
            # Fallback: try video extraction, then generic
            result = self._extract_video(html, url)
            if result and result[0].get("title"):
                return result
            return self._extract_generic(html, url)

    # -------------------------------------------------------------------
    # Video extraction
    # -------------------------------------------------------------------

    def _extract_video(self, html: str, url: str) -> list[dict]:
        """Extract video metadata from a YouTube watch page."""
        player_response = self._get_player_response(html)
        initial_data = self._get_initial_data(html)
        meta = extract_meta_tags(html)

        video: dict[str, Any] = {"video_url": url}

        # --- From ytInitialPlayerResponse.videoDetails ---
        vd = deep_get(player_response, "videoDetails") or {}
        if vd:
            video["title"] = vd.get("title")
            video["video_id"] = vd.get("videoId")
            video["view_count"] = parse_count(vd.get("viewCount"))
            video["channel_name"] = vd.get("author")
            video["channel_id"] = vd.get("channelId")
            video["duration"] = parse_duration(vd.get("lengthSeconds"))
            video["description"] = vd.get("shortDescription")
            video["tags"] = vd.get("keywords", [])
            thumbnails = deep_get(vd, "thumbnail", "thumbnails") or []
            if thumbnails:
                video["thumbnail_url"] = thumbnails[-1].get("url")

        # --- From ytInitialPlayerResponse.microformat ---
        microformat = deep_get(player_response, "microformat", "playerMicroformatRenderer") or {}
        if microformat:
            if not video.get("upload_date"):
                video["upload_date"] = (
                    microformat.get("publishDate")
                    or microformat.get("uploadDate")
                )
            if not video.get("category"):
                video["category"] = microformat.get("category")

        # --- From ytInitialData (engagement metrics) ---
        if initial_data:
            # Like count — nested in button view models
            like_count = self._find_like_count(initial_data)
            if like_count is not None:
                video["like_count"] = like_count

            # Comment count
            comment_count = self._find_comment_count(initial_data)
            if comment_count is not None:
                video["comment_count"] = comment_count

            # Upload date (relative or absolute)
            if not video.get("upload_date"):
                date_text = find_key_recursive(initial_data, "dateText")
                if isinstance(date_text, dict):
                    video["upload_date"] = date_text.get("simpleText")

            # Subscriber count
            sub_text = find_key_recursive(initial_data, "subscriberCountText")
            if isinstance(sub_text, dict):
                video["subscriber_count"] = parse_count(
                    sub_text.get("simpleText") or sub_text.get("accessibility", {}).get("accessibilityData", {}).get("label")
                )

        # --- Fallback to meta tags ---
        if not video.get("title"):
            video["title"] = meta.get("og:title") or meta.get("title") or extract_title(html)
        if not video.get("description"):
            video["description"] = meta.get("og:description") or meta.get("description")
        if not video.get("thumbnail_url"):
            video["thumbnail_url"] = meta.get("og:image")
        if not video.get("video_id"):
            video["video_id"] = self._extract_video_id(url)

        # Clean None values
        video = {k: v for k, v in video.items() if v is not None}

        return [video] if video.get("title") or video.get("video_id") else []

    # -------------------------------------------------------------------
    # Channel extraction
    # -------------------------------------------------------------------

    def _extract_channel(self, html: str, url: str) -> list[dict]:
        """Extract channel metadata from a YouTube channel page."""
        initial_data = self._get_initial_data(html)
        meta = extract_meta_tags(html)

        channel: dict[str, Any] = {"channel_url": url}

        if initial_data:
            # Channel header
            header = find_key_recursive(initial_data, "c4TabbedHeaderRenderer")
            if not header:
                header = find_key_recursive(initial_data, "pageHeaderRenderer")

            if header:
                channel["channel_name"] = header.get("title")
                channel["channel_id"] = header.get("channelId")

                # Subscriber count
                sub_text = deep_get(header, "subscriberCountText", "simpleText")
                if sub_text:
                    channel["subscriber_count"] = parse_count(sub_text)

                # Avatar
                avatar = deep_get(header, "avatar", "thumbnails") or []
                if avatar:
                    channel["avatar_url"] = avatar[-1].get("url")

                # Banner
                banner = deep_get(header, "banner", "thumbnails") or []
                if banner:
                    channel["banner_url"] = banner[-1].get("url")

            # Channel metadata
            metadata = find_key_recursive(initial_data, "channelMetadataRenderer")
            if metadata:
                channel["channel_name"] = channel.get("channel_name") or metadata.get("title")
                channel["channel_id"] = channel.get("channel_id") or metadata.get("externalId")
                channel["description"] = metadata.get("description")
                channel["country"] = metadata.get("country")
                channel["avatar_url"] = channel.get("avatar_url") or deep_get(
                    metadata, "avatar", "thumbnails", "0", "url"
                )

            # Video count and total views from about tab
            about = find_key_recursive(initial_data, "aboutChannelViewModel")
            if about:
                channel["total_views"] = parse_count(
                    deep_get(about, "viewCountText")
                )
                channel["video_count"] = parse_count(
                    deep_get(about, "videoCountText")
                )
                channel["created_date"] = deep_get(about, "joinedDateText", "content")
                channel["country"] = channel.get("country") or deep_get(about, "country")

            # Recent videos from the Videos tab
            recent_videos = self._extract_channel_videos(initial_data)
            if recent_videos:
                channel["recent_videos"] = recent_videos

        # Fallback to meta tags
        if not channel.get("channel_name"):
            channel["channel_name"] = meta.get("og:title") or extract_title(html)
        if not channel.get("description"):
            channel["description"] = meta.get("og:description")
        if not channel.get("avatar_url"):
            channel["avatar_url"] = meta.get("og:image")

        channel = {k: v for k, v in channel.items() if v is not None}
        return [channel] if channel.get("channel_name") else []

    def _extract_channel_videos(self, initial_data: dict) -> list[dict]:
        """Extract recent video list from channel's initial data."""
        videos = []
        # Find video renderers in tabs
        tab_contents = find_key_recursive(initial_data, "richGridRenderer")
        if not tab_contents:
            tab_contents = find_key_recursive(initial_data, "gridRenderer")

        if not tab_contents:
            return []

        contents = tab_contents.get("contents", [])
        for item in contents[:20]:  # Limit to 20 recent videos
            renderer = (
                deep_get(item, "richItemRenderer", "content", "videoRenderer")
                or item.get("gridVideoRenderer")
            )
            if not renderer:
                continue

            vid = {
                "video_id": renderer.get("videoId"),
                "title": deep_get(renderer, "title", "runs", "0", "text"),
                "view_count": parse_count(
                    deep_get(renderer, "viewCountText", "simpleText")
                    or deep_get(renderer, "viewCountText", "runs", "0", "text")
                ),
                "published": deep_get(renderer, "publishedTimeText", "simpleText"),
                "duration": parse_duration(
                    deep_get(renderer, "lengthText", "simpleText")
                ),
            }
            vid = {k: v for k, v in vid.items() if v is not None}
            if vid.get("video_id"):
                videos.append(vid)

        return videos

    # -------------------------------------------------------------------
    # Search results extraction
    # -------------------------------------------------------------------

    def _extract_search(self, html: str, url: str) -> list[dict]:
        """Extract search results from YouTube search page."""
        initial_data = self._get_initial_data(html)
        if not initial_data:
            return []

        results = []
        # Search results are in sectionListRenderer → itemSectionRenderer → contents
        video_renderers = self._find_all_renderers(initial_data, "videoRenderer")

        for position, renderer in enumerate(video_renderers, 1):
            item = {
                "title": deep_get(renderer, "title", "runs", "0", "text"),
                "video_id": renderer.get("videoId"),
                "channel_name": deep_get(renderer, "ownerText", "runs", "0", "text"),
                "view_count": parse_count(
                    deep_get(renderer, "viewCountText", "simpleText")
                ),
                "upload_date": deep_get(renderer, "publishedTimeText", "simpleText"),
                "duration": parse_duration(
                    deep_get(renderer, "lengthText", "simpleText")
                ),
                "description_snippet": self._runs_to_text(
                    deep_get(renderer, "detailedMetadataSnippets", "0", "snippetText", "runs")
                ),
                "thumbnail_url": deep_get(renderer, "thumbnail", "thumbnails", "-1", "url"),
                "url": f"https://www.youtube.com/watch?v={renderer.get('videoId', '')}",
                "position": position,
                "result_type": "video",
            }
            item = {k: v for k, v in item.items() if v is not None}
            if item.get("title"):
                results.append(item)

        return results

    # -------------------------------------------------------------------
    # Trending extraction
    # -------------------------------------------------------------------

    def _extract_trending(self, html: str, url: str) -> list[dict]:
        """Extract trending videos from YouTube trending page."""
        initial_data = self._get_initial_data(html)
        if not initial_data:
            return []

        results = []
        video_renderers = self._find_all_renderers(initial_data, "videoRenderer")

        for position, renderer in enumerate(video_renderers, 1):
            item = {
                "title": deep_get(renderer, "title", "runs", "0", "text"),
                "video_id": renderer.get("videoId"),
                "position": position,
                "view_count": parse_count(
                    deep_get(renderer, "viewCountText", "simpleText")
                    or deep_get(renderer, "shortViewCountText", "simpleText")
                ),
                "channel_name": deep_get(renderer, "ownerText", "runs", "0", "text"),
                "upload_date": deep_get(renderer, "publishedTimeText", "simpleText"),
                "thumbnail_url": deep_get(renderer, "thumbnail", "thumbnails", "-1", "url"),
            }
            item = {k: v for k, v in item.items() if v is not None}
            if item.get("title"):
                results.append(item)

        return results

    # -------------------------------------------------------------------
    # Generic extraction (fallback for any YouTube page)
    # -------------------------------------------------------------------

    def _extract_generic(self, html: str, url: str) -> list[dict]:
        """Fallback extraction using meta tags for any YouTube page."""
        meta = extract_meta_tags(html)
        result: dict[str, Any] = {"url": url}

        result["title"] = meta.get("og:title") or extract_title(html)
        result["description"] = meta.get("og:description") or meta.get("description")
        result["thumbnail_url"] = meta.get("og:image")

        result = {k: v for k, v in result.items() if v is not None}
        return [result] if result.get("title") else []

    # -------------------------------------------------------------------
    # Internal helpers
    # -------------------------------------------------------------------

    def _get_player_response(self, html: str) -> dict:
        """Extract ytInitialPlayerResponse from page HTML."""
        data = extract_json_from_script(html, var_name="ytInitialPlayerResponse")
        if data:
            return data

        # Alternative: embedded in ytcfg
        pattern = re.compile(
            r'ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var\s|</script>|;)',
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return {}

    def _get_initial_data(self, html: str) -> dict:
        """Extract ytInitialData from page HTML."""
        data = extract_json_from_script(html, var_name="ytInitialData")
        if data:
            return data

        # More lenient pattern
        pattern = re.compile(
            r'ytInitialData\s*=\s*(\{.+?\});\s*(?:var\s|window\[|</script>)',
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return {}

    def _find_like_count(self, initial_data: dict) -> int | None:
        """Find like count from ytInitialData's button view models."""
        # Modern YouTube: buttonViewModel with LIKE icon
        like_button = find_key_recursive(initial_data, "topLevelButtons")
        if isinstance(like_button, list):
            for btn in like_button:
                bvm = deep_get(btn, "segmentedLikeDislikeButtonViewModel", "likeButtonViewModel", "likeButtonViewModel", "toggleButtonViewModel", "toggleButtonViewModel", "defaultButtonViewModel", "buttonViewModel")
                if bvm:
                    return parse_count(bvm.get("title"))

        # Fallback: search for toggledText with LIKE
        like_text = find_key_recursive(initial_data, "toggledText")
        if isinstance(like_text, dict):
            accessibility = deep_get(like_text, "accessibility", "accessibilityData", "label")
            if accessibility and "like" in accessibility.lower():
                return parse_count(accessibility)

        # Another fallback: look for factoid containing likes
        factoid = find_key_recursive(initial_data, "factoid")
        if isinstance(factoid, list):
            for f in factoid:
                label = deep_get(f, "factoidRenderer", "label", "simpleText") or ""
                if "like" in label.lower():
                    value = deep_get(f, "factoidRenderer", "value", "simpleText")
                    return parse_count(value)

        return None

    def _find_comment_count(self, initial_data: dict) -> int | None:
        """Find comment count from ytInitialData."""
        # Look for comments header
        header = find_key_recursive(initial_data, "commentsHeaderRenderer")
        if header:
            count_text = deep_get(header, "countText", "runs")
            if isinstance(count_text, list):
                return parse_count(count_text[0].get("text", ""))

        # Contextual info
        contextual = find_key_recursive(initial_data, "contextualInfo")
        if isinstance(contextual, dict):
            runs = contextual.get("runs", [])
            if runs:
                return parse_count(runs[0].get("text", ""))

        return None

    def _find_all_renderers(self, data: Any, renderer_type: str, max_depth: int = 15) -> list[dict]:
        """Find all instances of a specific renderer type in nested data."""
        results = []

        if max_depth <= 0:
            return results

        if isinstance(data, dict):
            if renderer_type in data:
                results.append(data[renderer_type])
            for value in data.values():
                results.extend(self._find_all_renderers(value, renderer_type, max_depth - 1))

        elif isinstance(data, list):
            for item in data:
                results.extend(self._find_all_renderers(item, renderer_type, max_depth - 1))

        return results

    def _runs_to_text(self, runs: list[dict] | None) -> str | None:
        """Convert YouTube 'runs' array to plain text."""
        if not runs or not isinstance(runs, list):
            return None
        return "".join(r.get("text", "") for r in runs) or None

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extract video ID from various YouTube URL formats."""
        parsed = urlparse(url)

        # youtube.com/watch?v=VIDEO_ID
        if "youtube.com" in (parsed.hostname or ""):
            qs = parse_qs(parsed.query)
            if "v" in qs:
                return qs["v"][0]
            # /shorts/VIDEO_ID
            if "/shorts/" in parsed.path:
                parts = parsed.path.split("/shorts/")
                if len(parts) > 1:
                    return parts[1].split("/")[0].split("?")[0]

        # youtu.be/VIDEO_ID
        if parsed.hostname and "youtu.be" in parsed.hostname:
            return parsed.path.lstrip("/").split("/")[0]

        return None
