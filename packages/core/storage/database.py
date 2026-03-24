"""
Database engine and session management.

Supports both PostgreSQL (asyncpg) and SQLite (aiosqlite).

Supabase connection notes:
- Direct connections (db.<ref>.supabase.co:5432) use **IPv6 only**.
  Most cloud platforms (Railway, Render, Vercel) do NOT support IPv6 outbound.
- Use the Supavisor pooler URL instead for IPv4 compatibility:
    Session mode:     postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:5432/postgres
    Transaction mode: postgres.<ref>:<pass>@aws-0-<region>.pooler.supabase.com:6543/postgres
- For persistent servers (Railway, VMs), use SESSION mode (port 5432).
- For serverless (edge functions), use TRANSACTION mode (port 6543).
"""

from __future__ import annotations

import logging
import re

from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from packages.core.storage.models import Base

logger = logging.getLogger(__name__)


def _convert_supabase_direct_to_pooler(url: str) -> str:
    """Convert a Supabase direct connection URL to a Supavisor pooler URL.

    Direct URLs (db.<ref>.supabase.co:5432) resolve to IPv6 only,
    which fails on platforms like Railway that only support IPv4.

    Uses SESSION mode (port 5432) on the pooler, which:
    - Supports IPv4
    - Supports prepared statements (asyncpg default)
    - Is recommended for persistent servers (Railway, VMs)

    Input:  postgresql+asyncpg://postgres:<pass>@db.<ref>.supabase.co:5432/postgres
    Output: postgresql+asyncpg://postgres.<ref>:<pass>@aws-0-us-east-1.pooler.supabase.com:5432/postgres
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

    # Build pooler URL (session mode on port 5432 via Supavisor)
    # Username becomes "postgres.<ref>" for the pooler
    pooler_url = f"{scheme}postgres.{ref}:{password}@aws-0-us-east-1.pooler.supabase.com:5432/{dbname}"
    logger.info(
        "Converted Supabase direct URL (IPv6-only) to Supavisor session mode (IPv4). "
        "Host: db.%s.supabase.co:5432 → aws-0-us-east-1.pooler.supabase.com:5432",
        ref,
    )
    return pooler_url


def _is_supavisor_url(url: str) -> bool:
    """Check if the URL points to Supabase Supavisor pooler."""
    return "pooler.supabase.com" in url


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
