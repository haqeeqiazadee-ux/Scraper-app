"""
Twitter/X platform-specific extractor.

Extracts structured data from Twitter/X pages by parsing:
1. __NEXT_DATA__ — Next.js hydration JSON (modern X.com)
2. window.__INITIAL_STATE__ — Redux store snapshot (legacy Twitter)
3. Meta tags — fallback for title, description, images
4. DOM patterns — last resort for rendered pages

Supports: tweet, profile, search, thread, list
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs

from packages.core.ai_providers.social.base import (
    deep_get,
    extract_json_from_script,
    extract_meta_tags,
    extract_title,
    find_key_recursive,
    parse_count,
    parse_timestamp,
)

logger = logging.getLogger(__name__)

# Domains this extractor handles
TWITTER_DOMAINS = ["twitter.com", "x.com", "mobile.twitter.com"]

# Regex for extracting handle from URL path
_HANDLE_PATTERN = re.compile(r"^/@?([A-Za-z0-9_]{1,15})(?:/|$)")

# Regex for extracting hashtags from tweet text
_HASHTAG_PATTERN = re.compile(r"#(\w+)")


class TwitterExtractor:
    """Extract structured data from Twitter/X HTML pages."""

    DOMAINS = TWITTER_DOMAINS

    def extract(self, html: str, url: str) -> list[dict]:
        """Route to the appropriate extraction method based on URL pattern."""
        path = urlparse(url).path.lower()

        if "/status/" in path or "/statuses/" in path:
            return self._extract_tweet(html, url)
        elif "/search" in path:
            return self._extract_search(html, url)
        elif "/i/lists/" in path:
            return self._extract_list(html, url)
        elif "/hashtag/" in path:
            return self._extract_search(html, url)
        else:
            # Check if it's a profile URL (/@username or /username)
            stripped = path.strip("/")
            # Exclude known non-profile paths
            non_profile = {
                "home", "explore", "notifications", "messages",
                "settings", "i", "compose", "login", "signup",
                "tos", "privacy", "about",
            }
            first_segment = stripped.split("/")[0].lstrip("@") if stripped else ""
            if first_segment and first_segment not in non_profile:
                return self._extract_profile(html, url)

            # Fallback: try tweet extraction, then generic
            result = self._extract_tweet(html, url)
            if result and result[0].get("text"):
                return result
            return self._extract_generic(html, url)

    # -------------------------------------------------------------------
    # Tweet extraction
    # -------------------------------------------------------------------

    def _extract_tweet(self, html: str, url: str) -> list[dict]:
        """Extract a single tweet with engagement metrics."""
        next_data = self._get_next_data(html)
        initial_state = self._get_initial_state(html)
        meta = extract_meta_tags(html)

        tweet: dict[str, Any] = {"tweet_url": url}

        # --- Try __NEXT_DATA__ first ---
        if next_data:
            tweet_data = self._find_tweet_in_next_data(next_data, url)
            if tweet_data:
                self._populate_tweet_from_data(tweet, tweet_data)

        # --- Try __INITIAL_STATE__ ---
        if initial_state and not tweet.get("text"):
            tweet_data = self._find_tweet_in_initial_state(initial_state, url)
            if tweet_data:
                self._populate_tweet_from_data(tweet, tweet_data)

        # --- Try embedded JSON blobs ---
        if not tweet.get("text"):
            tweet_result = find_key_recursive(next_data or initial_state or {}, "tweet_results")
            if tweet_result:
                result = deep_get(tweet_result, "result") or tweet_result
                legacy = result.get("legacy") or result
                core = deep_get(result, "core", "user_results", "result", "legacy") or {}
                tweet["text"] = legacy.get("full_text") or legacy.get("text")
                tweet["author"] = core.get("name")
                tweet["handle"] = core.get("screen_name")
                if tweet.get("handle"):
                    tweet["handle"] = f"@{tweet['handle'].lstrip('@')}"
                tweet["timestamp"] = parse_timestamp(legacy.get("created_at"))
                tweet["likes"] = parse_count(str(legacy.get("favorite_count", "")))
                tweet["retweets"] = parse_count(str(legacy.get("retweet_count", "")))
                tweet["replies"] = parse_count(str(legacy.get("reply_count", "")))
                tweet["quotes"] = parse_count(str(legacy.get("quote_count", "")))
                tweet["views"] = parse_count(
                    str(deep_get(result, "views", "count") or "")
                )
                tweet["is_retweet"] = legacy.get("retweeted", False)
                tweet["is_reply"] = bool(legacy.get("in_reply_to_status_id_str"))

                # Media
                media_entities = deep_get(legacy, "extended_entities", "media") or \
                                 deep_get(legacy, "entities", "media") or []
                tweet["media_urls"] = [
                    m.get("media_url_https") or m.get("media_url")
                    for m in media_entities
                    if m.get("media_url_https") or m.get("media_url")
                ]

                # Hashtags
                hashtag_entities = deep_get(legacy, "entities", "hashtags") or []
                tweet["hashtags"] = [
                    h.get("text") for h in hashtag_entities if h.get("text")
                ]

        # --- Fallback to meta tags ---
        if not tweet.get("text"):
            og_desc = meta.get("og:description") or meta.get("description") or ""
            tweet["text"] = og_desc

        if not tweet.get("author"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            # Twitter titles often look like "Author (@handle) on X"
            title_match = re.match(r"(.+?)\s*\(@?(\w+)\)", og_title)
            if title_match:
                tweet["author"] = title_match.group(1).strip()
                tweet["handle"] = f"@{title_match.group(2)}"

        if not tweet.get("media_urls"):
            og_image = meta.get("og:image")
            if og_image and "profile_images" not in og_image:
                tweet["media_urls"] = [og_image]

        if not tweet.get("timestamp"):
            # Try to extract from meta tags
            tweet["timestamp"] = meta.get("article:published_time")

        # Extract handle from URL if still missing
        if not tweet.get("handle"):
            handle = self._extract_handle_from_url(url)
            if handle:
                tweet["handle"] = handle

        # Extract hashtags from text if not populated from entities
        if not tweet.get("hashtags") and tweet.get("text"):
            tweet["hashtags"] = _HASHTAG_PATTERN.findall(tweet["text"])

        # Extract tweet ID from URL
        tweet_id = self._extract_tweet_id(url)
        if tweet_id:
            tweet["tweet_id"] = tweet_id

        # Ensure boolean defaults
        tweet.setdefault("is_retweet", False)
        tweet.setdefault("is_reply", False)

        # Clean None values and empty lists
        tweet = {
            k: v for k, v in tweet.items()
            if v is not None and v != [] and v != ""
        }

        return [tweet] if tweet.get("text") or tweet.get("tweet_id") else []

    # -------------------------------------------------------------------
    # Profile extraction
    # -------------------------------------------------------------------

    def _extract_profile(self, html: str, url: str) -> list[dict]:
        """Extract user profile data."""
        next_data = self._get_next_data(html)
        initial_state = self._get_initial_state(html)
        meta = extract_meta_tags(html)

        profile: dict[str, Any] = {"profile_url": url}

        # --- Try __NEXT_DATA__ ---
        if next_data:
            user_data = self._find_user_in_next_data(next_data)
            if user_data:
                self._populate_profile_from_data(profile, user_data)

        # --- Try __INITIAL_STATE__ ---
        if initial_state and not profile.get("name"):
            user_data = self._find_user_in_initial_state(initial_state)
            if user_data:
                self._populate_profile_from_data(profile, user_data)

        # --- Try user_results from any embedded data ---
        if not profile.get("name"):
            combined = next_data or initial_state or {}
            user_results = find_key_recursive(combined, "user_results")
            if user_results:
                result = deep_get(user_results, "result") or user_results
                legacy = result.get("legacy") or result
                profile["name"] = legacy.get("name")
                handle = legacy.get("screen_name")
                if handle:
                    profile["handle"] = f"@{handle.lstrip('@')}"
                profile["bio"] = legacy.get("description")
                profile["location"] = legacy.get("location")
                profile["followers"] = parse_count(
                    str(legacy.get("followers_count", ""))
                )
                profile["following"] = parse_count(
                    str(legacy.get("friends_count", ""))
                )
                profile["tweet_count"] = parse_count(
                    str(legacy.get("statuses_count", ""))
                )
                profile["joined_date"] = parse_timestamp(legacy.get("created_at"))
                profile["verified"] = (
                    legacy.get("verified", False)
                    or deep_get(result, "is_blue_verified", default=False)
                )
                profile["profile_image"] = (
                    legacy.get("profile_image_url_https")
                    or legacy.get("profile_image_url")
                )
                profile["banner_image"] = legacy.get("profile_banner_url")

        # --- Fallback to meta tags ---
        if not profile.get("name"):
            og_title = meta.get("og:title") or extract_title(html) or ""
            title_match = re.match(r"(.+?)\s*\(@?(\w+)\)", og_title)
            if title_match:
                profile["name"] = title_match.group(1).strip()
                profile["handle"] = f"@{title_match.group(2)}"
            else:
                profile["name"] = og_title

        if not profile.get("bio"):
            profile["bio"] = meta.get("og:description") or meta.get("description")

        if not profile.get("profile_image"):
            profile["profile_image"] = meta.get("og:image")

        if not profile.get("handle"):
            handle = self._extract_handle_from_url(url)
            if handle:
                profile["handle"] = handle

        # Clean None values
        profile = {
            k: v for k, v in profile.items()
            if v is not None and v != "" and v != []
        }

        return [profile] if profile.get("name") or profile.get("handle") else []

    # -------------------------------------------------------------------
    # Search results extraction
    # -------------------------------------------------------------------

    def _extract_search(self, html: str, url: str) -> list[dict]:
        """Extract search results."""
        next_data = self._get_next_data(html)
        initial_state = self._get_initial_state(html)
        meta = extract_meta_tags(html)

        results = []
        combined = next_data or initial_state or {}

        # Find all tweet entries in the search results
        entries = self._find_all_entries(combined)

        for position, entry in enumerate(entries, 1):
            tweet_results = find_key_recursive(entry, "tweet_results")
            if not tweet_results:
                continue

            result = deep_get(tweet_results, "result") or tweet_results
            legacy = result.get("legacy") or result
            core_user = deep_get(result, "core", "user_results", "result", "legacy") or {}

            text = legacy.get("full_text") or legacy.get("text")
            if not text:
                continue

            handle = core_user.get("screen_name") or ""
            item = {
                "text": text,
                "author": core_user.get("name"),
                "handle": f"@{handle}" if handle else None,
                "tweet_id": legacy.get("id_str"),
                "timestamp": parse_timestamp(legacy.get("created_at")),
                "likes": parse_count(str(legacy.get("favorite_count", ""))),
                "retweets": parse_count(str(legacy.get("retweet_count", ""))),
                "replies": parse_count(str(legacy.get("reply_count", ""))),
                "position": position,
                "result_type": "tweet",
            }
            item = {k: v for k, v in item.items() if v is not None and v != ""}
            if item.get("text"):
                results.append(item)

        # Fallback: if no structured results found, return meta info
        if not results:
            search_info: dict[str, Any] = {"url": url, "result_type": "search"}
            search_info["title"] = meta.get("og:title") or extract_title(html)
            search_info["description"] = meta.get("og:description")
            search_info = {k: v for k, v in search_info.items() if v is not None}
            if search_info.get("title"):
                results.append(search_info)

        return results

    # -------------------------------------------------------------------
    # List extraction
    # -------------------------------------------------------------------

    def _extract_list(self, html: str, url: str) -> list[dict]:
        """Extract Twitter list data."""
        next_data = self._get_next_data(html)
        initial_state = self._get_initial_state(html)
        meta = extract_meta_tags(html)

        list_data: dict[str, Any] = {"list_url": url}

        combined = next_data or initial_state or {}
        twitter_list = find_key_recursive(combined, "list")
        if isinstance(twitter_list, dict):
            list_data["name"] = twitter_list.get("name")
            list_data["description"] = twitter_list.get("description")
            list_data["member_count"] = parse_count(
                str(twitter_list.get("member_count", ""))
            )
            list_data["subscriber_count"] = parse_count(
                str(twitter_list.get("subscriber_count", ""))
            )
            creator = deep_get(twitter_list, "user_results", "result", "legacy") or {}
            if creator:
                list_data["creator_name"] = creator.get("name")
                handle = creator.get("screen_name")
                if handle:
                    list_data["creator_handle"] = f"@{handle}"

        # Fallback to meta tags
        if not list_data.get("name"):
            list_data["name"] = meta.get("og:title") or extract_title(html)
        if not list_data.get("description"):
            list_data["description"] = meta.get("og:description")

        list_data = {
            k: v for k, v in list_data.items()
            if v is not None and v != ""
        }

        return [list_data] if list_data.get("name") else []

    # -------------------------------------------------------------------
    # Generic extraction (fallback for any Twitter page)
    # -------------------------------------------------------------------

    def _extract_generic(self, html: str, url: str) -> list[dict]:
        """Fallback extraction using meta tags for any Twitter/X page."""
        meta = extract_meta_tags(html)
        result: dict[str, Any] = {"url": url}

        result["title"] = meta.get("og:title") or extract_title(html)
        result["description"] = meta.get("og:description") or meta.get("description")
        result["image"] = meta.get("og:image")

        result = {k: v for k, v in result.items() if v is not None}
        return [result] if result.get("title") else []

    # -------------------------------------------------------------------
    # Internal helpers — data source extraction
    # -------------------------------------------------------------------

    def _get_next_data(self, html: str) -> dict:
        """Extract __NEXT_DATA__ from page HTML."""
        data = extract_json_from_script(html, script_id="__NEXT_DATA__")
        if data:
            return data
        return {}

    def _get_initial_state(self, html: str) -> dict:
        """Extract window.__INITIAL_STATE__ from page HTML."""
        data = extract_json_from_script(html, var_name="__INITIAL_STATE__")
        if data:
            return data

        # Try alternate patterns used by Twitter
        for var in ("window.__INITIAL_STATE__", "__INITIAL_STATE__"):
            pattern = re.compile(
                rf"{re.escape(var)}\s*=\s*(\{{.+?\}});\s*(?:window\.|</script>|;)",
                re.DOTALL,
            )
            match = pattern.search(html)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    continue

        return {}

    # -------------------------------------------------------------------
    # Internal helpers — tweet data lookup
    # -------------------------------------------------------------------

    def _find_tweet_in_next_data(self, next_data: dict, url: str) -> dict | None:
        """Find tweet data within __NEXT_DATA__ structure."""
        # Next.js page props may contain the tweet
        props = deep_get(next_data, "props", "pageProps") or {}
        tweet = props.get("tweet") or find_key_recursive(props, "tweet")
        if isinstance(tweet, dict):
            return tweet

        # Search deeper in the data
        tweet_results = find_key_recursive(next_data, "tweetResult")
        if tweet_results:
            return deep_get(tweet_results, "result") or tweet_results

        return None

    def _find_tweet_in_initial_state(self, initial_state: dict, url: str) -> dict | None:
        """Find tweet data within __INITIAL_STATE__ structure."""
        # Extract tweet ID from URL
        tweet_id = self._extract_tweet_id(url)

        # Try entities.tweets map
        tweets = deep_get(initial_state, "entities", "tweets", "entities") or {}
        if tweet_id and tweet_id in tweets:
            return tweets[tweet_id]

        # Try first available tweet
        if tweets:
            return next(iter(tweets.values()))

        return None

    def _populate_tweet_from_data(self, tweet: dict, data: dict) -> None:
        """Populate tweet dict from a raw tweet data object."""
        legacy = data.get("legacy") or data
        core = deep_get(data, "core", "user_results", "result", "legacy") or {}

        tweet["text"] = tweet.get("text") or legacy.get("full_text") or legacy.get("text")
        tweet["author"] = tweet.get("author") or core.get("name") or data.get("name")
        handle = core.get("screen_name") or data.get("screen_name")
        if handle and not tweet.get("handle"):
            tweet["handle"] = f"@{handle.lstrip('@')}"

        tweet["timestamp"] = tweet.get("timestamp") or parse_timestamp(
            legacy.get("created_at") or data.get("created_at")
        )

        tweet["likes"] = tweet.get("likes") or parse_count(
            str(legacy.get("favorite_count", ""))
        )
        tweet["retweets"] = tweet.get("retweets") or parse_count(
            str(legacy.get("retweet_count", ""))
        )
        tweet["replies"] = tweet.get("replies") or parse_count(
            str(legacy.get("reply_count", ""))
        )
        tweet["quotes"] = tweet.get("quotes") or parse_count(
            str(legacy.get("quote_count", ""))
        )
        tweet["views"] = tweet.get("views") or parse_count(
            str(deep_get(data, "views", "count") or legacy.get("view_count") or "")
        )

        tweet["is_retweet"] = legacy.get("retweeted", False)
        tweet["is_reply"] = bool(
            legacy.get("in_reply_to_status_id_str")
            or legacy.get("in_reply_to_status_id")
        )

        # Media URLs
        media_entities = (
            deep_get(legacy, "extended_entities", "media")
            or deep_get(legacy, "entities", "media")
            or deep_get(data, "extended_entities", "media")
            or deep_get(data, "entities", "media")
            or []
        )
        if media_entities and not tweet.get("media_urls"):
            tweet["media_urls"] = [
                m.get("media_url_https") or m.get("media_url")
                for m in media_entities
                if m.get("media_url_https") or m.get("media_url")
            ]

        # Hashtags
        hashtag_entities = (
            deep_get(legacy, "entities", "hashtags")
            or deep_get(data, "entities", "hashtags")
            or []
        )
        if hashtag_entities and not tweet.get("hashtags"):
            tweet["hashtags"] = [
                h.get("text") for h in hashtag_entities if h.get("text")
            ]

    # -------------------------------------------------------------------
    # Internal helpers — profile data lookup
    # -------------------------------------------------------------------

    def _find_user_in_next_data(self, next_data: dict) -> dict | None:
        """Find user data within __NEXT_DATA__ structure."""
        props = deep_get(next_data, "props", "pageProps") or {}
        user = props.get("user") or find_key_recursive(props, "user")
        if isinstance(user, dict) and ("screen_name" in user or "name" in user):
            return user

        user_results = find_key_recursive(next_data, "user_results")
        if user_results:
            return deep_get(user_results, "result") or user_results

        return None

    def _find_user_in_initial_state(self, initial_state: dict) -> dict | None:
        """Find user data within __INITIAL_STATE__ structure."""
        users = deep_get(initial_state, "entities", "users", "entities") or {}
        if users:
            return next(iter(users.values()))
        return None

    def _populate_profile_from_data(self, profile: dict, data: dict) -> None:
        """Populate profile dict from a raw user data object."""
        legacy = data.get("legacy") or data

        profile["name"] = profile.get("name") or legacy.get("name")
        handle = legacy.get("screen_name")
        if handle and not profile.get("handle"):
            profile["handle"] = f"@{handle.lstrip('@')}"

        profile["bio"] = profile.get("bio") or legacy.get("description")
        profile["location"] = profile.get("location") or legacy.get("location")

        profile["followers"] = profile.get("followers") or parse_count(
            str(legacy.get("followers_count", ""))
        )
        profile["following"] = profile.get("following") or parse_count(
            str(legacy.get("friends_count", ""))
        )
        profile["tweet_count"] = profile.get("tweet_count") or parse_count(
            str(legacy.get("statuses_count", ""))
        )

        profile["joined_date"] = profile.get("joined_date") or parse_timestamp(
            legacy.get("created_at")
        )

        profile["verified"] = (
            legacy.get("verified", False)
            or data.get("is_blue_verified", False)
        )

        profile["profile_image"] = profile.get("profile_image") or (
            legacy.get("profile_image_url_https")
            or legacy.get("profile_image_url")
        )
        profile["banner_image"] = profile.get("banner_image") or (
            legacy.get("profile_banner_url")
        )

    # -------------------------------------------------------------------
    # Internal helpers — search entries
    # -------------------------------------------------------------------

    def _find_all_entries(self, data: Any, max_depth: int = 15) -> list[dict]:
        """Find all timeline entry objects in nested data."""
        results = []
        if max_depth <= 0:
            return results

        if isinstance(data, dict):
            # Twitter timeline entries have "entryId" and "content"
            if "entryId" in data and "content" in data:
                results.append(data)
            for value in data.values():
                results.extend(self._find_all_entries(value, max_depth - 1))
        elif isinstance(data, list):
            for item in data:
                results.extend(self._find_all_entries(item, max_depth - 1))

        return results

    # -------------------------------------------------------------------
    # Internal helpers — URL parsing
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_tweet_id(url: str) -> str | None:
        """Extract tweet ID from a Twitter status URL."""
        parsed = urlparse(url)
        path = parsed.path

        # /username/status/1234567890
        match = re.search(r"/status(?:es)?/(\d+)", path)
        if match:
            return match.group(1)

        return None

    @staticmethod
    def _extract_handle_from_url(url: str) -> str | None:
        """Extract @handle from a Twitter URL path."""
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        if not path:
            return None

        match = _HANDLE_PATTERN.match(path)
        if match:
            return f"@{match.group(1)}"

        # Try first path segment
        segments = path.split("/")
        if segments:
            candidate = segments[0].lstrip("@")
            if re.match(r"^[A-Za-z0-9_]{1,15}$", candidate):
                non_profile = {
                    "home", "explore", "notifications", "messages",
                    "settings", "i", "compose", "login", "signup",
                    "tos", "privacy", "about", "search", "hashtag",
                }
                if candidate.lower() not in non_profile:
                    return f"@{candidate}"

        return None
