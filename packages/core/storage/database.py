"""
Database engine and session management.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.storage.models import Base


class Database:
    """Manages database connections and sessions."""

    def __init__(self, url: str = "sqlite+aiosqlite:///./scraper.db") -> None:
        self._url = url
        self._engine = create_async_engine(
            url,
            echo=False,
            pool_pre_ping=True,
        )
        self._session_factory = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_tables(self) -> None:
        """Create all tables (for development/SQLite). Use Alembic for production."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def drop_tables(self) -> None:
        """Drop all tables (for testing only)."""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    def session(self) -> AsyncSession:
        """Get a new database session."""
        return self._session_factory()

    async def close(self) -> None:
        """Close the database engine."""
        await self._engine.dispose()
