"""
Filesystem Object Store — local file-based artifact storage.

Used for desktop mode and development. Implements the ObjectStore protocol.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FilesystemObjectStore:
    """Object store backed by the local filesystem."""

    def __init__(self, base_path: str = "./artifacts") -> None:
        self._base = Path(base_path)
        self._base.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        """Resolve a key to an absolute file path (safe against traversal)."""
        resolved = (self._base / key).resolve()
        if not str(resolved).startswith(str(self._base.resolve())):
            raise ValueError(f"Invalid key: path traversal detected in '{key}'")
        return resolved

    async def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Store data at the given key."""
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.debug("Object stored", extra={"key": key, "size": len(data), "content_type": content_type})
        return key

    async def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        return path.read_bytes()

    async def delete(self, key: str) -> None:
        """Delete an object by key."""
        path = self._resolve(key)
        if path.exists():
            path.unlink()
            logger.debug("Object deleted", extra={"key": key})

    async def list_keys(self, prefix: str = "") -> list[str]:
        """List all keys with the given prefix."""
        search_path = self._resolve(prefix) if prefix else self._base
        if not search_path.exists():
            return []

        if search_path.is_file():
            return [prefix]

        keys = []
        for path in search_path.rglob("*"):
            if path.is_file():
                relative = path.relative_to(self._base)
                keys.append(str(relative))
        return sorted(keys)

    async def get_presigned_url(self, key: str, ttl_seconds: int = 3600) -> str:
        """For filesystem, return the file:// path (no real presigning)."""
        path = self._resolve(key)
        return f"file://{path}"

    async def get_checksum(self, key: str) -> str:
        """Calculate SHA-256 checksum of stored object."""
        data = await self.get(key)
        return f"sha256:{hashlib.sha256(data).hexdigest()}"
