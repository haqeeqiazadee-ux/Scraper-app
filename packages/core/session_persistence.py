"""
Session Persistence — stores and retrieves session cookies, browser profiles,
and headers from the filesystem.

Storage layout:
    {storage_path}/{session_id}/cookies.json
    {storage_path}/{session_id}/profile.json
    {storage_path}/{session_id}/headers.json
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
from functools import partial
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SessionPersistence:
    """Persists session cookies and browser profiles to storage."""

    COOKIES_FILE = "cookies.json"
    PROFILE_FILE = "profile.json"
    HEADERS_FILE = "headers.json"

    def __init__(self, storage_path: str = "./session_data") -> None:
        self._storage_path = Path(storage_path)

    # ------------------------------------------------------------------
    # Cookies
    # ------------------------------------------------------------------

    async def save_cookies(self, session_id: str, cookies: dict) -> None:
        """Save session cookies to disk."""
        await self._write_json(session_id, self.COOKIES_FILE, cookies)
        logger.debug("Cookies saved", extra={"session_id": session_id})

    async def load_cookies(self, session_id: str) -> Optional[dict]:
        """Load session cookies from disk."""
        return await self._read_json(session_id, self.COOKIES_FILE)

    # ------------------------------------------------------------------
    # Browser profile
    # ------------------------------------------------------------------

    async def save_browser_profile(self, session_id: str, profile_data: dict) -> None:
        """Save browser profile (viewport, user-agent, etc.)."""
        await self._write_json(session_id, self.PROFILE_FILE, profile_data)
        logger.debug("Browser profile saved", extra={"session_id": session_id})

    async def load_browser_profile(self, session_id: str) -> Optional[dict]:
        """Load browser profile."""
        return await self._read_json(session_id, self.PROFILE_FILE)

    # ------------------------------------------------------------------
    # Headers
    # ------------------------------------------------------------------

    async def save_headers(self, session_id: str, headers: dict) -> None:
        """Save custom headers for session reuse."""
        await self._write_json(session_id, self.HEADERS_FILE, headers)
        logger.debug("Headers saved", extra={"session_id": session_id})

    async def load_headers(self, session_id: str) -> Optional[dict]:
        """Load custom headers."""
        return await self._read_json(session_id, self.HEADERS_FILE)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def delete_session_data(self, session_id: str) -> None:
        """Delete all persisted data for a session."""
        session_dir = self._session_dir(session_id)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None, partial(shutil.rmtree, session_dir, ignore_errors=True)
            )
            logger.info("Session data deleted", extra={"session_id": session_id})
        except Exception:
            logger.exception(
                "Failed to delete session data", extra={"session_id": session_id}
            )

    async def list_sessions(self) -> list[str]:
        """List all persisted session IDs."""
        loop = asyncio.get_running_loop()

        def _list() -> list[str]:
            if not self._storage_path.exists():
                return []
            return sorted(
                entry.name
                for entry in self._storage_path.iterdir()
                if entry.is_dir()
            )

        return await loop.run_in_executor(None, _list)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _session_dir(self, session_id: str) -> Path:
        return self._storage_path / session_id

    async def _write_json(self, session_id: str, filename: str, data: dict) -> None:
        """Write a JSON file inside the session directory."""
        loop = asyncio.get_running_loop()
        session_dir = self._session_dir(session_id)

        def _write() -> None:
            session_dir.mkdir(parents=True, exist_ok=True)
            path = session_dir / filename
            path.write_text(json.dumps(data, default=str, indent=2), encoding="utf-8")

        await loop.run_in_executor(None, _write)

    async def _read_json(self, session_id: str, filename: str) -> Optional[dict]:
        """Read a JSON file from the session directory, returning None if absent."""
        loop = asyncio.get_running_loop()
        path = self._session_dir(session_id) / filename

        def _read() -> Optional[dict]:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        return await loop.run_in_executor(None, _read)
