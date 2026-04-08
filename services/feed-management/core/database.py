"""PostgreSQL connection (Supabase) and table initialization.

Uses DATABASE_URL from env (same Supabase instance as the scraper).
All tables prefixed with fms_ to avoid conflicts with scraper tables.
"""

from __future__ import annotations

import os
from datetime import datetime
from decimal import Decimal

from dotenv import load_dotenv
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "fms_products"
    __table_args__ = (
        UniqueConstraint("mpn", "brand", name="uq_products_mpn_brand"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mpn: Mapped[str] = mapped_column(String(128), nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amazon_monthly_sales: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amazon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    offers: Mapped[list[VendorOffer]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )


class VendorOffer(Base):
    __tablename__ = "fms_vendor_offers"
    __table_args__ = (
        CheckConstraint(
            "region IN ('UK', 'EU', 'USA')",
            name="ck_vendor_offers_region",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("fms_products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    vendor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    region: Mapped[str] = mapped_column(String(8), nullable=False, server_default="EU")
    price_gbp: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_eur: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    price_usd: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    stock_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    product: Mapped[Product] = relationship(back_populates="offers")


class MasterIncompleteRow(Base):
    """Rows from master uploads that still need MPN, Brand, or Title; edited in PHP Master tab."""

    __tablename__ = "fms_master_incomplete_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mpn: Mapped[str | None] = mapped_column(String(128), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(128), nullable=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amazon_monthly_sales: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amazon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class MasterProduct(Base):
    """Canonical datasheet (MPN + brand) used to standardize ``products`` titles, EAN, category."""

    __tablename__ = "fms_master_products"
    __table_args__ = (
        UniqueConstraint("mpn", "brand", name="uq_master_mpn_brand"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mpn: Mapped[str] = mapped_column(String(128), nullable=False)
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    category: Mapped[str | None] = mapped_column(String(256), nullable=True)
    ean: Mapped[str | None] = mapped_column(String(32), nullable=True)
    asin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    amazon_monthly_sales: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    amazon_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


def _database_url() -> str:
    """Get DATABASE_URL from env (same Supabase as the scraper).

    Supports both async (asyncpg) and sync (psycopg2) URLs.
    For the FMS sync ingestion, converts asyncpg URL to psycopg2.
    """
    load_dotenv()
    url = (os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        raise ValueError("DATABASE_URL not set. Use the same Supabase URL as the scraper.")
    # Convert async URL to sync for FMS ingestion scripts
    url = url.replace("postgresql+asyncpg://", "postgresql://")
    url = url.replace("sqlite+aiosqlite://", "sqlite://")
    return url


def get_engine(*, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for Supabase PostgreSQL."""
    return create_engine(_database_url(), echo=echo, pool_pre_ping=True)


def init_db(engine: Engine | None = None) -> None:
    """Create all tables defined on ``Base`` if they do not exist.

    ``create_all`` will not alter existing tables. If you already have the old schema
    (``products.name``, ``vendor_offers.price``), back up data and migrate, e.g.::

        ALTER TABLE products ADD COLUMN ean VARCHAR(32) NULL;
        ALTER TABLE products ADD COLUMN title VARCHAR(512) NOT NULL AFTER brand;
        UPDATE products SET title = name WHERE 1=1;
        ALTER TABLE products DROP COLUMN name;

        ALTER TABLE vendor_offers ADD COLUMN region VARCHAR(8) NOT NULL DEFAULT 'EU';
        ALTER TABLE vendor_offers ADD COLUMN price_gbp DECIMAL(18,4) NULL;
        ALTER TABLE vendor_offers ADD COLUMN price_eur DECIMAL(18,4) NULL;
        ALTER TABLE vendor_offers ADD COLUMN price_usd DECIMAL(18,4) NULL;
        UPDATE vendor_offers SET price_eur = price WHERE price IS NOT NULL;
        ALTER TABLE vendor_offers DROP COLUMN price;
        ALTER TABLE vendor_offers ADD CONSTRAINT ck_vendor_offers_region
            CHECK (region IN ('UK', 'EU', 'USA'));

        Run ``init_db()`` after upgrading the code to create ``master_products`` (or create it from the
        ``MasterProduct`` model / Hostinger php upload which uses ``CREATE TABLE IF NOT EXISTS``).

    (Adjust types/order for your MySQL version; test on a copy first.)
    """
    bind = engine or get_engine()
    Base.metadata.create_all(bind=bind)


__all__ = [
    "Base",
    "MasterIncompleteRow",
    "MasterProduct",
    "Product",
    "VendorOffer",
    "get_engine",
    "init_db",
]
