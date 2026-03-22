"""
SQLite Desktop Adapter — lightweight metadata store for desktop EXE mode.

Wraps the Database class with SQLite-specific configuration.
Auto-creates database file on first run. No external dependencies.
"""

from __future__ import annotations

import logging
from pathlib import Path

from packages.core.storage.database import Database

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "~/.scraper-app/scraper.db"


class SQLiteDesktopStore:
    """SQLite-backed metadata store for desktop/local mode."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        resolved = Path(db_path).expanduser()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        self._path = str(resolved)
        self._db = Database(url=f"sqlite+aiosqlite:///{self._path}")

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        await self._db.create_tables()
        logger.info("SQLite desktop store initialized", extra={"path": self._path})

    @property
    def database(self) -> Database:
        return self._db

    @property
    def path(self) -> str:
        return self._path

    async def close(self) -> None:
        await self._db.close()
