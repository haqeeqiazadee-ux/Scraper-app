"""MySQL connection (Hostinger) and table initialization."""

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
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Product(Base):
    __tablename__ = "products"
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
    __tablename__ = "vendor_offers"
    __table_args__ = (
        CheckConstraint(
            "region IN ('UK', 'EU', 'USA')",
            name="ck_vendor_offers_region",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
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

    __tablename__ = "master_incomplete_rows"

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

    __tablename__ = "master_products"
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


def _database_url() -> URL:
    """Build DSN from env. Accepts ``DB_USER``/``DB_USERNAME``, ``DB_PASS``/``DB_PASSWORD``, etc."""
    load_dotenv()
    user = (os.environ.get("DB_USER") or os.environ.get("DB_USERNAME") or "").strip()
    password = (os.environ.get("DB_PASS") or os.environ.get("DB_PASSWORD") or "").strip()
    host = (os.environ.get("DB_HOST") or "").strip()
    database = (os.environ.get("DB_NAME") or os.environ.get("DB_DATABASE") or "").strip()
    port_raw = (os.environ.get("DB_PORT") or "").strip()
    port = int(port_raw) if port_raw else None
    if not user or not host or not database:
        raise ValueError(
            "Database env incomplete: set DB_HOST, DB_USER or DB_USERNAME, "
            "DB_NAME or DB_DATABASE, and DB_PASS or DB_PASSWORD.",
        )
    kwargs: dict = dict(
        drivername="mysql+mysqlconnector",
        username=user,
        password=password,
        host=host,
        database=database,
    )
    if port is not None:
        kwargs["port"] = port
    return URL.create(**kwargs)


def get_engine(*, echo: bool = False) -> Engine:
    """Create a SQLAlchemy engine for the configured MySQL database."""
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
