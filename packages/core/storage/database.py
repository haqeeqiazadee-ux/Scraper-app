"""
Database engine and session management.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).

Supabase connection notes:
- Direct connections (db.<ref>.supabase.co:5432) use **IPv6 only**.
  Most cloud platforms (Railway, Render, Vercel) do NOT support IPv6 outbound.
- Use the Supavisor pooler URL instead for IPv4 compatibility:
    Transaction mode: postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres
    Session mode:     postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:5432/postgres
"""

from __future__ import annotations

import logging
import re
import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.storage.models import Base

logger = logging.getLogger(__name__)


def _convert_supabase_direct_to_pooler(url: str) -> str:
    """Convert a Supabase direct connection URL to a Supavisor pooler URL.

    Direct URLs (db.<ref>.supabase.co:5432) resolve to IPv6 only,
    which fails on platforms like Railway that only support IPv4.

    The pooler URL (aws-0-<region>.pooler.supabase.com:6543) supports IPv4.

    Input:  postgresql+asyncpg://postgres:<pass>@db.<ref>.supabase.co:5432/postgres
    Output: postgresql+asyncpg://postgres.<ref>:<pass>@aws-0-us-east-1.pooler.supabase.com:6543/postgres
    """
    # Match: ...://postgres:<password>@db.<ref>.supabase.co:5432/postgres
    pattern = r"(postgresql\+asyncpg://)postgres:([^@]+)@db\.([^.]+)\.supabase\.co:5432/(\w+)"
    match = re.match(pattern, url)
    if not match:
        return url  # Not a direct Supabase URL, return unchanged

    scheme = match.group(1)
    password = match.group(2)
    ref = match.group(3)
    dbname = match.group(4)

    # Build pooler URL (transaction mode on port 6543)
    # Username becomes "postgres.<ref>" for the pooler
    pooler_url = f"{scheme}postgres.{ref}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/{dbname}"
    logger.info(
        "Converted Supabase direct URL (IPv6-only) to pooler URL (IPv4-compatible). "
        "Host: db.%s.supabase.co → aws-0-us-east-1.pooler.supabase.com:6543",
        ref,
    )
    return pooler_url


class Database:
    """Manages database connections and sessions."""

    def __init__(self, url: str = "sqlite+aiosqlite:///./scraper.db") -> None:
        # Auto-convert Supabase direct URLs to pooler URLs for IPv4 compatibility.
        # Direct URLs use IPv6 which is unreachable from Railway/Render/Vercel.
        if "supabase.co:5432" in url and "pooler.supabase.com" not in url:
            url = _convert_supabase_direct_to_pooler(url)
        self._url = url

        # Build engine kwargs
        engine_kwargs: dict = {
            "echo": False,
            "pool_pre_ping": True,
        }

        connect_args: dict = {}

        if "asyncpg" in url:
            # Supabase Supavisor pooler (port 6543) uses transaction mode.
            # asyncpg prepared statements are incompatible — disable the cache.
            if ":6543" in url:
                connect_args["prepared_statement_cache_size"] = 0

            # SSL context for Supabase connections
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
