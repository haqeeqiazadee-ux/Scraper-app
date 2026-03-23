"""
Database engine and session management.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).
"""

from __future__ import annotations

import logging
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.storage.models import Base

logger = logging.getLogger(__name__)


class Database:
    """Manages database connections and sessions."""

    def __init__(self, url: str = "sqlite+aiosqlite:///./scraper.db") -> None:
        self._url = url

        # Build engine kwargs
        engine_kwargs: dict = {
            "echo": False,
            "pool_pre_ping": True,
        }

        connect_args: dict = {}

        if "asyncpg" in url:
            # Supabase pooler (port 6543) uses pgbouncer in transaction mode.
            # asyncpg prepared statements are incompatible — disable the cache.
            if ":6543" in url:
                connect_args["prepared_statement_cache_size"] = 0

            # Supabase requires SSL for direct connections on port 5432.
            # Create a permissive SSL context (Supabase uses self-signed certs
            # behind their proxy, so we must not verify the certificate).
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_ctx

            # Connection timeout — helps fail faster than the OS default
            connect_args["timeout"] = 30

            engine_kwargs["connect_args"] = connect_args

            # Pool settings for cloud deployments
            engine_kwargs["pool_size"] = 5
            engine_kwargs["max_overflow"] = 10
            engine_kwargs["pool_timeout"] = 30
            engine_kwargs["pool_recycle"] = 300  # recycle connections every 5 min

            logger.info("PostgreSQL engine configured with SSL and connection pooling")

        self._engine = create_async_engine(url, **engine_kwargs)
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
