"""
TikTok platform-specific extractor.

Extracts structured data from TikTok pages by parsing:
1. __UNIVERSAL_DATA_FOR_REHYDRATION__ — primary data source (modern TikTok)
2. SIGI_STATE — legacy fallback data source
3. __NEXT_DATA__ — additional fallback
4. Meta tags — last resort for basic info

Supports: video, profile, hashtag, sound, trending/discover
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse

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

TIKTOK_DOMAINS = ["tiktok.com", "m.tiktok.com", "www.tiktok.com"]


class TikTokExtractor:
    """Extract structured data from TikTok HTML pages."""

    DOMAINS = TIKTOK_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower()

        if "/@" in path and "/video/" in path:
            return self._extract_video(html, url)
        elif "/@" in path:
            return self._extract_profile(html, url)
        elif "/tag/" in path:
            return self._extract_hashtag(html, url)
        elif "/music/" in path:
            return self._extract_sound(html, url)
        elif "/discover" in path:
            return self._extract_discover(html, url)
        else:
            # Try video first, then profile, then generic
            result = self._extract_video(html, url)
            if result and len(result[0]) > 2:
                return result
            result = self._extract_profile(html, url)
            if result and len(result[0]) > 2:
                return result
            return self._extract_generic(html, url)

    # -------------------------------------------------------------------
    # Data source extraction
    # -------------------------------------------------------------------

    def _get_rehydration_data(self, html: str) -> dict | None:
        """Extract __UNIVERSAL_DATA_FOR_REHYDRATION__ JSON."""
        data = extract_json_from_script(html, script_id="__UNIVERSAL_DATA_FOR_REHYDRATION__")
        if data:
            return deep_get(data, "__DEFAULT_SCOPE__") or data
        return None

    def _get_sigi_state(self, html: str) -> dict | None:
        """Extract SIGI_STATE JSON (legacy fallback)."""
        data = extract_json_from_script(html, script_id="SIGI_STATE")
        if data:
            return data

        # Also try as window variable
        data = extract_json_from_script(html, var_name="SIGI_STATE")
        return data

    def _get_next_data(self, html: str) -> dict | None:
        """Extract __NEXT_DATA__ JSON."""
        return extract_json_from_script(html, script_id="__NEXT_DATA__")

    def _get_all_data(self, html: str) -> dict:
        """Try all data sources and return the first successful one."""
        rehydration = self._get_rehydration_data(html)
        if rehydration:
            return {"source": "rehydration", "data": rehydration}

        sigi = self._get_sigi_state(html)
        if sigi:
            return {"source": "sigi", "data": sigi}

        next_data = self._get_next_data(html)
        if next_data:
            return {"source": "next", "data": next_data}

        return {"source": "none", "data": {}}

    # -------------------------------------------------------------------
    # Video extraction
    # -------------------------------------------------------------------

    def _extract_video(self, html: str, url: str) -> list[dict]:
        """Extract video metadata from a TikTok video page."""
        all_data = self._get_all_data(html)
        source = all_data["source"]
        data = all_data["data"]
        meta = extract_meta_tags(html)

        video: dict[str, Any] = {"video_url": url}

        if source == "rehydration":
            item_struct = deep_get(data, "webapp.video-detail", "itemInfo", "itemStruct")
            if item_struct:
                self._parse_video_item(item_struct, video)

        elif source == "sigi":
            # SIGI_STATE uses ItemModule
            item_module = data.get("ItemModule", {})
            if item_module:
                # First item in the module
                for item_id, item_data in item_module.items():
                    self._parse_video_item(item_data, video)
                    break

        elif source == "next":
            item_struct = deep_get(data, "props", "pageProps", "itemInfo", "itemStruct")
            if item_struct:
                self._parse_video_item(item_struct, video)

        # Fallback to meta tags
        if not video.get("caption"):
            video["caption"] = (
                meta.get("og:description")
                or meta.get("description")
                or extract_title(html)
            )
        if not video.get("thumbnail_url"):
            video["thumbnail_url"] = meta.get("og:image")
        if not video.get("video_id"):
            video["video_id"] = self._extract_video_id(url)

        video = {k: v for k, v in video.items() if v is not None}
        return [video] if video.get("caption") or video.get("video_id") else []

    def _parse_video_item(self, item: dict, video: dict) -> None:
        """Parse a TikTok video item structure into our standard fields."""
        video["video_id"] = item.get("id")
        video["caption"] = item.get("desc")
        video["create_time"] = parse_timestamp(item.get("createTime"))

        # Stats
        stats = item.get("stats", {})
        video["view_count"] = parse_count(str(stats.get("playCount", "")))
        video["like_count"] = parse_count(str(stats.get("diggCount", "")))
        video["comment_count"] = parse_count(str(stats.get("commentCount", "")))
        video["share_count"] = parse_count(str(stats.get("shareCount", "")))

        # Video info
        video_info = item.get("video", {})
        video["duration"] = parse_duration(str(video_info.get("duration", "")))
        video["download_url"] = video_info.get("playAddr") or video_info.get("downloadAddr")
        cover = video_info.get("cover") or video_info.get("dynamicCover")
        if cover:
            video["thumbnail_url"] = cover

        # Author
        author = item.get("author", {})
        if author:
            video["creator_username"] = author.get("uniqueId")
            video["creator_nickname"] = author.get("nickname")
            video["creator_followers"] = parse_count(
                str(deep_get(author, "stats", "followerCount") or "")
            )

        # Music
        music = item.get("music", {})
        if music:
            video["music_title"] = music.get("title")
            video["music_author"] = music.get("authorName")

        # Hashtags from challenges or desc
        challenges = item.get("challenges", [])
        if challenges:
            video["hashtags"] = [c.get("title") for c in challenges if c.get("title")]
        elif video.get("caption"):
            video["hashtags"] = re.findall(r"#(\w+)", video["caption"])

    # -------------------------------------------------------------------
    # Profile extraction
    # -------------------------------------------------------------------

    def _extract_profile(self, html: str, url: str) -> list[dict]:
        """Extract user profile data from a TikTok profile page."""
        all_data = self._get_all_data(html)
        source = all_data["source"]
        data = all_data["data"]
        meta = extract_meta_tags(html)

        profile: dict[str, Any] = {"profile_url": url}

        if source == "rehydration":
            user_info = deep_get(data, "webapp.user-detail", "userInfo")
            if user_info:
                self._parse_profile(user_info, profile)

        elif source == "sigi":
            user_module = data.get("UserModule", {})
            users = user_module.get("users", {})
            stats_module = user_module.get("stats", {})
            if users:
                for username, user_data in users.items():
                    profile["username"] = user_data.get("uniqueId") or username
                    profile["nickname"] = user_data.get("nickname")
                    profile["bio"] = user_data.get("signature")
                    profile["verified"] = user_data.get("verified", False)
                    profile["avatar_url"] = user_data.get("avatarLarger") or user_data.get("avatarMedium")

                    # Stats from separate module
                    user_stats = stats_module.get(username, {})
                    if user_stats:
                        profile["follower_count"] = user_stats.get("followerCount")
                        profile["following_count"] = user_stats.get("followingCount")
                        profile["total_likes"] = user_stats.get("heartCount")
                        profile["video_count"] = user_stats.get("videoCount")
                    break

        elif source == "next":
            user_info = deep_get(data, "props", "pageProps", "userInfo")
            if user_info:
                self._parse_profile(user_info, profile)

        # Fallback to meta tags
        if not profile.get("username"):
            profile["username"] = self._extract_username(url)
        if not profile.get("nickname"):
            profile["nickname"] = meta.get("og:title") or extract_title(html)
        if not profile.get("bio"):
            profile["bio"] = meta.get("og:description") or meta.get("description")
        if not profile.get("avatar_url"):
            profile["avatar_url"] = meta.get("og:image")

        # Extract recent videos if available
        recent = self._extract_profile_videos(data, source)
        if recent:
            profile["recent_videos"] = recent

        profile = {k: v for k, v in profile.items() if v is not None}
        return [profile] if profile.get("username") else []

    def _parse_profile(self, user_info: dict, profile: dict) -> None:
        """Parse TikTok userInfo structure (rehydration/next format)."""
        user = user_info.get("user", {})
        stats = user_info.get("stats", {})

        profile["username"] = user.get("uniqueId")
        profile["nickname"] = user.get("nickname")
        profile["bio"] = user.get("signature")
        profile["verified"] = user.get("verified", False)
        profile["avatar_url"] = user.get("avatarLarger") or user.get("avatarMedium")

        if stats:
            profile["follower_count"] = stats.get("followerCount")
            profile["following_count"] = stats.get("followingCount")
            profile["total_likes"] = stats.get("heartCount")
            profile["video_count"] = stats.get("videoCount")

    def _extract_profile_videos(self, data: dict, source: str) -> list[dict]:
        """Extract recent videos from profile data."""
        videos = []
        items = None

        if source == "rehydration":
            items = deep_get(data, "webapp.user-detail", "itemList")
        elif source == "sigi":
            item_module = data.get("ItemModule", {})
            if item_module:
                items = list(item_module.values())

        if not items:
            return []

        for item in items[:20]:
            vid: dict[str, Any] = {
                "video_id": item.get("id"),
                "caption": item.get("desc"),
            }
            stats = item.get("stats", {})
            if stats:
                vid["view_count"] = stats.get("playCount")
                vid["like_count"] = stats.get("diggCount")
            vid = {k: v for k, v in vid.items() if v is not None}
            if vid.get("video_id"):
                videos.append(vid)

        return videos

    # -------------------------------------------------------------------
    # Hashtag extraction
    # -------------------------------------------------------------------

    def _extract_hashtag(self, html: str, url: str) -> list[dict]:
        """Extract videos from a TikTok hashtag page."""
        all_data = self._get_all_data(html)
        source = all_data["source"]
        data = all_data["data"]
        meta = extract_meta_tags(html)

        results = []

        # Extract hashtag name from URL
        hashtag = self._extract_from_path(url, "/tag/")

        if source == "rehydration":
            challenge_data = deep_get(data, "webapp.hashtag-detail")
            if challenge_data:
                # Challenge info
                challenge_info = challenge_data.get("challengeInfo", {})
                challenge = challenge_info.get("challenge", {})

                header = {
                    "hashtag": challenge.get("title") or hashtag,
                    "view_count": parse_count(str(challenge_info.get("statsV2", {}).get("viewCount", ""))),
                    "video_count": parse_count(str(challenge_info.get("statsV2", {}).get("videoCount", ""))),
                }
                header = {k: v for k, v in header.items() if v is not None}
                results.append(header)

                # Videos in the hashtag
                item_list = challenge_data.get("itemList", [])
                for item in item_list[:20]:
                    vid: dict[str, Any] = {
                        "hashtag": hashtag,
                        "video_id": item.get("id"),
                        "caption": item.get("desc"),
                    }
                    stats = item.get("stats", {})
                    vid["view_count"] = stats.get("playCount")
                    vid["like_count"] = stats.get("diggCount")
                    vid["share_count"] = stats.get("shareCount")

                    author = item.get("author", {})
                    vid["creator_username"] = author.get("uniqueId")

                    music = item.get("music", {})
                    vid["music_title"] = music.get("title")

                    vid["create_time"] = parse_timestamp(item.get("createTime"))
                    vid = {k: v for k, v in vid.items() if v is not None}
                    if vid.get("video_id"):
                        results.append(vid)

        if not results:
            # Fallback to meta tags
            result = {
                "hashtag": hashtag,
                "description": meta.get("og:description") or meta.get("description"),
            }
            result = {k: v for k, v in result.items() if v is not None}
            if result.get("hashtag"):
                results.append(result)

        return results

    # -------------------------------------------------------------------
    # Sound/music extraction
    # -------------------------------------------------------------------

    def _extract_sound(self, html: str, url: str) -> list[dict]:
        """Extract music/sound data from a TikTok sound page."""
        all_data = self._get_all_data(html)
        source = all_data["source"]
        data = all_data["data"]
        meta = extract_meta_tags(html)

        sound: dict[str, Any] = {"sound_url": url}

        if source == "rehydration":
            music_data = deep_get(data, "webapp.music-detail")
            if music_data:
                music_info = music_data.get("musicInfo", {})
                music = music_info.get("music", {})
                sound["music_id"] = str(music.get("id", ""))
                sound["music_title"] = music.get("title")
                sound["music_author"] = music.get("authorName")
                sound["video_count"] = parse_count(
                    str(music_info.get("stats", {}).get("videoCount", ""))
                )

        # Fallback
        if not sound.get("music_title"):
            sound["music_title"] = meta.get("og:title") or extract_title(html)

        sound = {k: v for k, v in sound.items() if v is not None}
        return [sound] if sound.get("music_title") or sound.get("music_id") else []

    # -------------------------------------------------------------------
    # Discover/trending extraction
    # -------------------------------------------------------------------

    def _extract_discover(self, html: str, url: str) -> list[dict]:
        """Extract discover/trending content from TikTok."""
        all_data = self._get_all_data(html)
        source = all_data["source"]
        data = all_data["data"]
        meta = extract_meta_tags(html)

        results = []

        if source == "rehydration":
            # Discover page has trending hashtags, videos, and creators
            discover = deep_get(data, "webapp.discover")
            if discover:
                # Trending videos
                for item in discover.get("itemList", [])[:20]:
                    vid: dict[str, Any] = {
                        "content_type": "video",
                        "title": item.get("desc"),
                        "video_id": item.get("id"),
                    }
                    stats = item.get("stats", {})
                    vid["view_count"] = stats.get("playCount")
                    vid["like_count"] = stats.get("diggCount")
                    author = item.get("author", {})
                    vid["creator_username"] = author.get("uniqueId")
                    vid = {k: v for k, v in vid.items() if v is not None}
                    results.append(vid)

            # Trending keywords/hashtags
            keyword_list = deep_get(data, "webapp.search-detail", "keywordList")
            if keyword_list:
                for rank, kw in enumerate(keyword_list, 1):
                    results.append({
                        "content_type": "keyword",
                        "title": kw if isinstance(kw, str) else kw.get("keyword", ""),
                        "trending_rank": rank,
                    })

        # Fallback: try to find any video items in the data
        if not results and data:
            item_list = find_key_recursive(data, "itemList")
            if isinstance(item_list, list):
                for item in item_list[:20]:
                    if isinstance(item, dict):
                        vid = {
                            "content_type": "video",
                            "title": item.get("desc"),
                            "video_id": item.get("id"),
                        }
                        stats = item.get("stats", {})
                        if stats:
                            vid["view_count"] = stats.get("playCount")
                            vid["like_count"] = stats.get("diggCount")
                        vid = {k: v for k, v in vid.items() if v is not None}
                        if vid.get("title") or vid.get("video_id"):
                            results.append(vid)

        if not results:
            result = {
                "title": meta.get("og:title") or extract_title(html),
                "description": meta.get("og:description"),
            }
            result = {k: v for k, v in result.items() if v is not None}
            if result:
                results.append(result)

        return results

    # -------------------------------------------------------------------
    # Generic extraction (any TikTok page)
    # -------------------------------------------------------------------

    def _extract_generic(self, html: str, url: str) -> list[dict]:
        """Fallback extraction for any TikTok page."""
        meta = extract_meta_tags(html)
        result: dict[str, Any] = {"url": url}

        result["title"] = meta.get("og:title") or extract_title(html)
        result["description"] = meta.get("og:description") or meta.get("description")
        result["thumbnail_url"] = meta.get("og:image")

        result = {k: v for k, v in result.items() if v is not None}
        return [result] if result.get("title") else []

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_video_id(url: str) -> str | None:
        """Extract TikTok video ID from URL."""
        match = re.search(r"/video/(\d+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_username(url: str) -> str | None:
        """Extract username from TikTok URL."""
        match = re.search(r"/@([^/?]+)", url)
        return match.group(1) if match else None

    @staticmethod
    def _extract_from_path(url: str, prefix: str) -> str | None:
        """Extract path segment after a prefix."""
        path = urlparse(url).path
        if prefix in path:
            segment = path.split(prefix)[-1].strip("/").split("/")[0]
            return segment if segment else None
        return None
