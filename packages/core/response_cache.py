"""
Response Cache — avoid re-fetching unchanged pages.

Caches HTTP response bodies with ETag/Last-Modified support.
On subsequent requests, sends conditional headers (If-None-Match,
If-Modified-Since) to get a 304 Not Modified instead of re-downloading.

Two cache tiers:
1. In-memory LRU (fast, limited size)
2. Disk (persistent across restarts, larger capacity)

Usage:
    cache = ResponseCache(max_memory_items=500)

    # Check cache before fetching
    entry = cache.get(url)
    if entry and not entry.is_expired:
        return entry.body  # Cache hit

    # Fetch with conditional headers
    headers = cache.get_conditional_headers(url)
    response = await fetch(url, headers=headers)

    if response.status_code == 304:
        return cache.get(url).body  # Not modified, use cached

    # Store new response
    cache.put(url, response.body, response.headers)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached HTTP response."""

    url: str
    body: bytes
    etag: str = ""
    last_modified: str = ""
    content_type: str = ""
    cached_at: float = 0.0
    ttl: float = 3600.0  # Default 1 hour
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.cached_at > self.ttl

    @property
    def age_seconds(self) -> float:
        return time.time() - self.cached_at

    @property
    def size_bytes(self) -> int:
        return len(self.body)


class ResponseCache:
    """Two-tier response cache with conditional request support.

    Tier 1: In-memory LRU cache (fast access, limited size)
    Tier 2: Disk cache (persistent, larger capacity)

    Supports HTTP caching headers:
    - ETag / If-None-Match
    - Last-Modified / If-Modified-Since
    - Cache-Control (respects max-age and no-cache)
    """

    def __init__(
        self,
        max_memory_items: int = 500,
        disk_cache_dir: Optional[str] = None,
        default_ttl: float = 3600.0,
    ) -> None:
        self._memory: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_memory = max_memory_items
        self._default_ttl = default_ttl
        self._disk_dir: Optional[Path] = None

        if disk_cache_dir:
            self._disk_dir = Path(disk_cache_dir)
            self._disk_dir.mkdir(parents=True, exist_ok=True)

        self._hits = 0
        self._misses = 0

    def _url_key(self, url: str) -> str:
        """Normalize URL to a cache key."""
        return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:32]

    def get(self, url: str) -> Optional[CacheEntry]:
        """Get a cached response. Returns None on miss."""
        key = self._url_key(url)

        # Check memory first
        if key in self._memory:
            entry = self._memory[key]
            if not entry.is_expired:
                # Move to end (LRU)
                self._memory.move_to_end(key)
                entry.hit_count += 1
                self._hits += 1
                return entry
            else:
                del self._memory[key]

        # Check disk
        if self._disk_dir:
            entry = self._load_from_disk(key)
            if entry and not entry.is_expired:
                # Promote to memory
                self._memory[key] = entry
                self._evict_memory()
                entry.hit_count += 1
                self._hits += 1
                return entry

        self._misses += 1
        return None

    def put(
        self,
        url: str,
        body: bytes,
        response_headers: Optional[dict[str, str]] = None,
        ttl: Optional[float] = None,
    ) -> None:
        """Store a response in the cache.

        Automatically extracts ETag and Last-Modified from response headers.
        Respects Cache-Control: no-cache and max-age directives.
        """
        headers = response_headers or {}
        headers_lower = {k.lower(): v for k, v in headers.items()}

        # Respect Cache-Control: no-cache / no-store
        cache_control = headers_lower.get("cache-control", "")
        if "no-store" in cache_control or "no-cache" in cache_control:
            return  # Don't cache

        # Parse max-age from Cache-Control
        effective_ttl = ttl or self._default_ttl
        if "max-age=" in cache_control:
            try:
                max_age = int(cache_control.split("max-age=")[1].split(",")[0].strip())
                effective_ttl = float(max_age)
            except (ValueError, IndexError):
                pass

        key = self._url_key(url)
        entry = CacheEntry(
            url=url,
            body=body,
            etag=headers_lower.get("etag", ""),
            last_modified=headers_lower.get("last-modified", ""),
            content_type=headers_lower.get("content-type", ""),
            cached_at=time.time(),
            ttl=effective_ttl,
        )

        # Store in memory
        self._memory[key] = entry
        self._evict_memory()

        # Store on disk
        if self._disk_dir:
            self._save_to_disk(key, entry)

    def get_conditional_headers(self, url: str) -> dict[str, str]:
        """Get conditional request headers for a URL.

        If we have a cached version with ETag or Last-Modified, return
        headers that let the server respond with 304 Not Modified.
        """
        key = self._url_key(url)
        entry = self._memory.get(key)

        if not entry and self._disk_dir:
            entry = self._load_from_disk(key)

        if not entry:
            return {}

        headers: dict[str, str] = {}
        if entry.etag:
            headers["If-None-Match"] = entry.etag
        if entry.last_modified:
            headers["If-Modified-Since"] = entry.last_modified
        return headers

    def invalidate(self, url: str) -> None:
        """Remove a URL from the cache."""
        key = self._url_key(url)
        self._memory.pop(key, None)
        if self._disk_dir:
            meta_path = self._disk_dir / f"{key}.meta"
            body_path = self._disk_dir / f"{key}.body"
            meta_path.unlink(missing_ok=True)
            body_path.unlink(missing_ok=True)

    def clear(self) -> None:
        """Clear all cached entries."""
        self._memory.clear()
        if self._disk_dir:
            for f in self._disk_dir.glob("*"):
                f.unlink(missing_ok=True)

    @property
    def stats(self) -> dict:
        """Cache statistics."""
        return {
            "memory_entries": len(self._memory),
            "memory_max": self._max_memory,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self._hits / max(self._hits + self._misses, 1),
            "disk_enabled": self._disk_dir is not None,
        }

    # ---- memory management -----------------------------------------------

    def _evict_memory(self) -> None:
        """Evict oldest entries when memory cache is full."""
        while len(self._memory) > self._max_memory:
            self._memory.popitem(last=False)

    # ---- disk persistence ------------------------------------------------

    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Save a cache entry to disk."""
        if not self._disk_dir:
            return
        try:
            meta = {
                "url": entry.url,
                "etag": entry.etag,
                "last_modified": entry.last_modified,
                "content_type": entry.content_type,
                "cached_at": entry.cached_at,
                "ttl": entry.ttl,
            }
            meta_path = self._disk_dir / f"{key}.meta"
            body_path = self._disk_dir / f"{key}.body"
            meta_path.write_text(json.dumps(meta))
            body_path.write_bytes(entry.body)
        except Exception as e:
            logger.debug("Failed to save cache entry to disk: %s", e)

    def _load_from_disk(self, key: str) -> Optional[CacheEntry]:
        """Load a cache entry from disk."""
        if not self._disk_dir:
            return None
        try:
            meta_path = self._disk_dir / f"{key}.meta"
            body_path = self._disk_dir / f"{key}.body"
            if not meta_path.exists() or not body_path.exists():
                return None
            meta = json.loads(meta_path.read_text())
            body = body_path.read_bytes()
            return CacheEntry(
                url=meta["url"],
                body=body,
                etag=meta.get("etag", ""),
                last_modified=meta.get("last_modified", ""),
                content_type=meta.get("content_type", ""),
                cached_at=meta.get("cached_at", 0),
                ttl=meta.get("ttl", self._default_ttl),
            )
        except Exception as e:
            logger.debug("Failed to load cache entry from disk: %s", e)
            return None
