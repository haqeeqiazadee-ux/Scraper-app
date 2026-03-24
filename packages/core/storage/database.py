"""
Database engine and session management.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).

Supabase connection notes:
- Direct connections (db.<ref>.supabase.co:5432) use **IPv6 only**.
  Most cloud platforms (Railway, Render, Vercel) do NOT support IPv6 outbound.
- Use the Supavisor session pooler URL instead for IPv4 compatibility:
    postgresql+asyncpg://postgres.<ref>:<pass>@aws-N-<region>.pooler.supabase.com:5432/postgres
  Get the exact URL from Supabase dashboard → Connect → Session pooler.
"""

from __future__ import annotations

import logging

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.storage.models import Base

logger = logging.getLogger(__name__)


def _is_supavisor_url(url: str) -> bool:
    """Check if the URL points to Supabase Supavisor pooler."""
    return "pooler.supabase.com" in url


def _is_supabase_direct_url(url: str) -> bool:
    """Check if URL is a Supabase direct connection (IPv6-only)."""
    return "supabase.co:5432" in url and "pooler.supabase.com" not in url


class Database:
    """Manages database connections and sessions."""

    def __init__(self, url: str = "sqlite+aiosqlite:///./scraper.db") -> None:
        # Detect Supabase direct URLs and warn — they use IPv6 which fails on
        # Railway/Render/Vercel. The pooler URL cluster (aws-0, aws-1, etc.)
        # varies per project, so we can't auto-convert reliably.
        if _is_supabase_direct_url(url):
            logger.error(
                "DATABASE_URL uses a Supabase direct connection (IPv6-only). "
                "This will FAIL on Railway/Render/Vercel which only support IPv4. "
                "Use the Session pooler URL instead: Supabase dashboard → Connect → Session pooler. "
                "Format: postgresql+asyncpg://postgres.<ref>:<pass>@aws-N-<region>.pooler.supabase.com:5432/postgres"
            )
        self._url = url

        # Build engine kwargs
        engine_kwargs: dict = {
            "echo": False,
            "pool_pre_ping": True,
        }

        connect_args: dict = {}

        if "asyncpg" in url:
            is_supavisor = _is_supavisor_url(url)
            is_transaction_mode = ":6543" in url

            # Supavisor transaction mode (port 6543) does NOT support
            # prepared statements — disable asyncpg's statement cache.
            if is_transaction_mode:
                connect_args["prepared_statement_cache_size"] = 0

            # SSL: use simple "require" mode for Supavisor connections.
            # A custom SSLContext can interfere with Supavisor's SNI-based
            # tenant routing. The string "require" tells asyncpg to use TLS
            # without certificate verification.
            connect_args["ssl"] = "require"

            # Connection timeout
            connect_args["timeout"] = 30

            engine_kwargs["connect_args"] = connect_args

            if is_supavisor:
                # Supabase docs recommend NullPool when using Supavisor,
                # since connection pooling is handled server-side.
                engine_kwargs["poolclass"] = NullPool
                logger.info(
                    "PostgreSQL via Supavisor (%s mode, NullPool)",
                    "transaction" if is_transaction_mode else "session",
                )
            else:
                # Non-Supavisor PostgreSQL: use application-side pool
                engine_kwargs["pool_size"] = 5
                engine_kwargs["max_overflow"] = 10
                engine_kwargs["pool_timeout"] = 30
                engine_kwargs["pool_recycle"] = 300
                logger.info("PostgreSQL engine configured with connection pooling")

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
