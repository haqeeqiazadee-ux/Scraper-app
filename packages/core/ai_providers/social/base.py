"""
Shared utilities for social media platform extractors.

Provides common helpers for:
- Parsing abbreviated counts (13K, 1.5M, 2.3B)
- Extracting Open Graph / meta tags
- Parsing embedded JSON from <script> tags
- Timestamp conversion
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Count parsing (e.g., "13K views" → 13000)
# ---------------------------------------------------------------------------

_MULTIPLIERS = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
    "t": 1_000_000_000_000,
}

_COUNT_PATTERN = re.compile(
    r"([\d,\.]+)\s*([kmbt])?(?:\s*(?:views?|likes?|subscribers?|followers?|comments?|shares?|plays?))?",
    re.IGNORECASE,
)


def parse_count(text: str | None) -> int | None:
    """Parse an abbreviated count string into an integer.

    Examples:
        "13K" → 13000
        "1.5M views" → 1500000
        "2,345" → 2345
        "1.2B" → 1200000000
        "No views" → None
    """
    if not text:
        return None

    from html import unescape
    text = unescape(text).strip().replace("\xa0", " ")

    # Try direct integer parse first
    cleaned = text.replace(",", "").replace(" ", "")
    try:
        return int(cleaned)
    except ValueError:
        pass

    match = _COUNT_PATTERN.search(text)
    if not match:
        return None

    num_str = match.group(1).replace(",", "")
    suffix = (match.group(2) or "").lower()

    try:
        num = float(num_str)
    except ValueError:
        return None

    multiplier = _MULTIPLIERS.get(suffix, 1)
    return int(num * multiplier)


# ---------------------------------------------------------------------------
# Duration parsing
# ---------------------------------------------------------------------------

_DURATION_HMS = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})")
_DURATION_ISO = re.compile(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


def parse_duration(text: str | None) -> str | None:
    """Parse duration from various formats to HH:MM:SS or MM:SS.

    Handles:
        "PT1H2M3S" → "1:02:03"
        "125" (seconds) → "2:05"
        "1:23:45" → "1:23:45"
    """
    if not text:
        return None

    text = text.strip()

    # ISO 8601 duration
    iso_match = _DURATION_ISO.match(text)
    if iso_match:
        h = int(iso_match.group(1) or 0)
        m = int(iso_match.group(2) or 0)
        s = int(iso_match.group(3) or 0)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    # HH:MM:SS or MM:SS
    hms_match = _DURATION_HMS.match(text)
    if hms_match:
        return text

    # Plain seconds
    try:
        total = int(text)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    except ValueError:
        return text


# ---------------------------------------------------------------------------
# Timestamp conversion
# ---------------------------------------------------------------------------

def parse_timestamp(value: str | int | None) -> str | None:
    """Convert a Unix timestamp or ISO date string to ISO 8601 format."""
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
        except (OSError, ValueError):
            return None

    if isinstance(value, str):
        value = value.strip()
        # Try Unix timestamp as string
        try:
            ts = int(value)
            return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()
        except (ValueError, OSError):
            pass
        # Already an ISO string or human-readable date
        return value

    return None


# ---------------------------------------------------------------------------
# Meta tag extraction
# ---------------------------------------------------------------------------

def extract_meta_tags(html: str) -> dict[str, str]:
    """Extract Open Graph and standard meta tags from HTML.

    Returns a flat dict like:
        {"og:title": "...", "og:description": "...", "description": "...", ...}
    """
    tags: dict[str, str] = {}

    # <meta property="og:title" content="...">
    og_pattern = re.compile(
        r'<meta\s+(?:[^>]*?\s+)?property=["\']([^"\']+)["\']\s+(?:[^>]*?\s+)?content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for match in og_pattern.finditer(html):
        tags[match.group(1)] = match.group(2)

    # Also match reversed attribute order: content before property
    og_rev = re.compile(
        r'<meta\s+(?:[^>]*?\s+)?content=["\']([^"\']*?)["\']\s+(?:[^>]*?\s+)?property=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for match in og_rev.finditer(html):
        tags[match.group(2)] = match.group(1)

    # <meta name="description" content="...">
    name_pattern = re.compile(
        r'<meta\s+(?:[^>]*?\s+)?name=["\']([^"\']+)["\']\s+(?:[^>]*?\s+)?content=["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for match in name_pattern.finditer(html):
        tags[match.group(1)] = match.group(2)

    # Reversed order for name-based tags
    name_rev = re.compile(
        r'<meta\s+(?:[^>]*?\s+)?content=["\']([^"\']*?)["\']\s+(?:[^>]*?\s+)?name=["\']([^"\']+)["\']',
        re.IGNORECASE,
    )
    for match in name_rev.finditer(html):
        tags[match.group(2)] = match.group(1)

    return tags


# ---------------------------------------------------------------------------
# JSON extraction from <script> tags
# ---------------------------------------------------------------------------

def extract_json_from_script(
    html: str,
    *,
    var_name: str | None = None,
    script_id: str | None = None,
) -> dict | None:
    """Extract JSON data from a <script> tag by variable name or script ID.

    Args:
        html: Raw HTML content.
        var_name: JavaScript variable name (e.g., "ytInitialData").
        script_id: Script tag ID (e.g., "__UNIVERSAL_DATA_FOR_REHYDRATION__").

    Returns:
        Parsed JSON dict, or None if extraction fails.
    """
    if script_id:
        pattern = re.compile(
            rf'<script[^>]*id=["\']?{re.escape(script_id)}["\']?[^>]*>(.*?)</script>',
            re.DOTALL | re.IGNORECASE,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON from script id=%s", script_id)

    if var_name:
        # Pattern: var ytInitialData = {...};
        pattern = re.compile(
            rf"(?:var\s+)?{re.escape(var_name)}\s*=\s*(\{{.+?\}});\s*(?:var\s|</script>)",
            re.DOTALL,
        )
        match = pattern.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                logger.debug("Failed to parse JSON from var %s", var_name)

        # Fallback: more lenient pattern
        pattern2 = re.compile(
            rf"{re.escape(var_name)}\s*=\s*(\{{.*?\}});\s*$",
            re.DOTALL | re.MULTILINE,
        )
        match = pattern2.search(html)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

    return None


# ---------------------------------------------------------------------------
# Nested dict access
# ---------------------------------------------------------------------------

def deep_get(data: dict | list | Any, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts/lists by key path.

    Example:
        deep_get(data, "videoDetails", "title") → data["videoDetails"]["title"]
        deep_get(data, "items", "0", "snippet") → data["items"][0]["snippet"]
    """
    current = data
    for key in keys:
        if current is None:
            return default
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, (list, tuple)):
            try:
                current = current[int(key)]
            except (IndexError, ValueError):
                return default
        else:
            return default
    return current if current is not None else default


def find_key_recursive(data: Any, target_key: str, max_depth: int = 15) -> Any:
    """Recursively search for a key in nested dicts/lists.

    Returns the first value found, or None.
    """
    if max_depth <= 0:
        return None

    if isinstance(data, dict):
        if target_key in data:
            return data[target_key]
        for value in data.values():
            result = find_key_recursive(value, target_key, max_depth - 1)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = find_key_recursive(item, target_key, max_depth - 1)
            if result is not None:
                return result

    return None


# ---------------------------------------------------------------------------
# URL domain matching
# ---------------------------------------------------------------------------

def matches_domain(url: str, domains: list[str]) -> bool:
    """Check if a URL matches any of the given domains."""
    try:
        host = urlparse(url).hostname or ""
        host = host.lower().removeprefix("www.")
        for domain in domains:
            domain = domain.lower().removeprefix("www.")
            if host == domain or host.endswith("." + domain):
                return True
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# HTML title extraction
# ---------------------------------------------------------------------------

def extract_title(html: str) -> str | None:
    """Extract <title> tag content."""
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else None


def extract_json_after_key(html: str, key: str) -> dict | None:
    """Extract a JSON object that appears after a specific key in the HTML.

    Uses balanced-brace matching to handle arbitrarily nested JSON objects,
    which regex-based approaches (e.g., \\{.+?\\}) cannot handle correctly.

    Args:
        html: Raw HTML content.
        key: The JSON key to search for (e.g., "shortcode_media").

    Returns:
        Parsed JSON dict, or None if extraction fails.
    """
    search_str = f'"{key}":'
    idx = html.find(search_str)
    if idx == -1:
        # Try with single quotes
        search_str = f"'{key}':"
        idx = html.find(search_str)
    if idx == -1:
        return None

    # Find the opening brace
    start = html.find("{", idx + len(search_str))
    if start == -1:
        return None

    # Balanced-brace matching
    depth = 0
    in_string = False
    escape_next = False
    end = start

    for i in range(start, min(start + 500_000, len(html))):
        ch = html[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\":
            if in_string:
                escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    else:
        return None

    try:
        return json.loads(html[start:end])
    except json.JSONDecodeError:
        return None
