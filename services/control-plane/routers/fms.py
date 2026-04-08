"""Feed Management System (FMS) proxy — query B2B product catalog.

Proxies requests to the FMS API running on Hostinger MySQL.
Exposes FMS data through the scraper's API for YOUSELL integration.

Endpoints:
  GET /fms/products       — Search products (MPN, brand, title)
  GET /fms/products/{id}  — Get product detail with all vendor offers
  GET /fms/offers         — List vendor offers with filters
  GET /fms/suppliers      — List all suppliers
  GET /fms/health         — FMS connectivity check
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

from services.control_plane.dependencies import get_tenant_id

logger = structlog.get_logger(__name__)

fms_router = APIRouter(prefix="/fms", tags=["Feed Management"])

# ---------------------------------------------------------------------------
# FMS Database connection (separate from scraper's Supabase)
# ---------------------------------------------------------------------------

_fms_engine = None


def _get_fms_engine():
    """Lazy-init MySQL engine for FMS (Hostinger)."""
    global _fms_engine
    if _fms_engine is not None:
        return _fms_engine

    from dotenv import load_dotenv
    load_dotenv()

    host = os.environ.get("FMS_DB_HOST", os.environ.get("DB_HOST", ""))
    port = int(os.environ.get("FMS_DB_PORT", os.environ.get("DB_PORT", "3306")))
    database = os.environ.get("FMS_DB_DATABASE", os.environ.get("DB_DATABASE", ""))
    username = os.environ.get("FMS_DB_USERNAME", os.environ.get("DB_USERNAME", ""))
    password = os.environ.get("FMS_DB_PASSWORD", os.environ.get("DB_PASSWORD", ""))

    if not all([host, database, username, password]):
        logger.warning("fms.db_not_configured", hint="Set FMS_DB_HOST, FMS_DB_DATABASE, FMS_DB_USERNAME, FMS_DB_PASSWORD")
        return None

    from sqlalchemy import create_engine
    from urllib.parse import quote_plus

    url = f"mysql+mysqlconnector://{username}:{quote_plus(password)}@{host}:{port}/{database}"
    _fms_engine = create_engine(url, pool_size=5, pool_recycle=3600, echo=False)
    logger.info("fms.db_connected", host=host, database=database)
    return _fms_engine


def _get_fms_session():
    """Yield a FMS database session."""
    engine = _get_fms_engine()
    if engine is None:
        raise HTTPException(status_code=503, detail="FMS database not configured")
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------------
# Import FMS models (lazy to avoid import errors if MySQL driver missing)
# ---------------------------------------------------------------------------

def _get_models():
    """Lazy import FMS database models."""
    try:
        from services.feed_management.core.database import Product, VendorOffer
        return Product, VendorOffer
    except ImportError:
        # Try with hyphenated path
        import importlib
        import sys
        fms_path = os.path.join(os.path.dirname(__file__), "..", "..", "feed-management")
        if fms_path not in sys.path:
            sys.path.insert(0, os.path.abspath(fms_path))
        from core.database import Product, VendorOffer
        return Product, VendorOffer


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@fms_router.get("/health")
def fms_health():
    """Check FMS database connectivity."""
    engine = _get_fms_engine()
    if engine is None:
        return {"ok": False, "database": "not_configured"}
    try:
        with Session(engine) as session:
            session.execute(text("SELECT 1"))
        return {"ok": True, "database": "connected"}
    except Exception as e:
        return {"ok": False, "database": "error", "detail": str(e)[:200]}


@fms_router.get("/products")
def fms_list_products(
    db: Session = Depends(_get_fms_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand: str | None = Query(None, description="Exact brand match"),
    mpn: str | None = Query(None, description="MPN contains match"),
    q: str | None = Query(None, description="Search title, MPN, or brand"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Search FMS product catalog."""
    Product, VendorOffer = _get_models()

    stmt: Select = select(Product).order_by(Product.id)
    if brand and brand.strip():
        stmt = stmt.where(func.trim(Product.brand) == brand.strip())
    if mpn and mpn.strip():
        stmt = stmt.where(Product.mpn.contains(mpn.strip()))
    if q and q.strip():
        pat = q.strip()
        stmt = stmt.where(
            or_(
                Product.title.contains(pat),
                Product.mpn.contains(pat),
                Product.brand.contains(pat),
            )
        )
    stmt = stmt.offset(offset).limit(limit + 1)
    rows = list(db.scalars(stmt).all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return {
        "items": [
            {
                "id": r.id,
                "mpn": r.mpn,
                "brand": r.brand,
                "title": r.title,
                "category": getattr(r, "category", None),
                "ean": getattr(r, "ean", None),
            }
            for r in rows
        ],
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
    }


@fms_router.get("/products/{product_id}")
def fms_get_product(
    product_id: int,
    db: Session = Depends(_get_fms_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get product detail with all vendor offers (price comparison)."""
    Product, VendorOffer = _get_models()

    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.offers))
    )
    row = db.scalars(stmt).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    offers = sorted(row.offers, key=lambda o: (o.vendor_name, o.region, o.id))
    return {
        "id": row.id,
        "mpn": row.mpn,
        "brand": row.brand,
        "title": row.title,
        "category": getattr(row, "category", None),
        "ean": getattr(row, "ean", None),
        "asin": getattr(row, "asin", None),
        "amazon_monthly_sales": getattr(row, "amazon_monthly_sales", None),
        "amazon_url": getattr(row, "amazon_url", None),
        "offers": [
            {
                "id": o.id,
                "vendor_name": o.vendor_name,
                "region": o.region,
                "price_gbp": float(o.price_gbp) if o.price_gbp else None,
                "price_eur": float(o.price_eur) if o.price_eur else None,
                "price_usd": float(o.price_usd) if o.price_usd else None,
                "stock_level": o.stock_level,
                "last_updated": o.last_updated.isoformat() if o.last_updated else None,
            }
            for o in offers
        ],
    }


@fms_router.get("/offers")
def fms_list_offers(
    db: Session = Depends(_get_fms_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    vendor_name: str | None = Query(None),
    product_id: int | None = Query(None, ge=1),
    region: Literal["UK", "EU", "USA"] | None = Query(None),
    min_stock: int | None = Query(None, ge=0),
    tenant_id: str = Depends(get_tenant_id),
):
    """List vendor offers with filters."""
    Product, VendorOffer = _get_models()

    stmt: Select = select(VendorOffer).order_by(VendorOffer.id)
    if vendor_name:
        stmt = stmt.where(VendorOffer.vendor_name == vendor_name.strip())
    if product_id is not None:
        stmt = stmt.where(VendorOffer.product_id == product_id)
    if region:
        stmt = stmt.where(VendorOffer.region == region)
    if min_stock is not None:
        stmt = stmt.where(VendorOffer.stock_level.is_not(None))
        stmt = stmt.where(VendorOffer.stock_level >= min_stock)
    stmt = stmt.offset(offset).limit(limit + 1)
    rows = list(db.scalars(stmt).all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return {
        "items": [
            {
                "id": o.id,
                "vendor_name": o.vendor_name,
                "product_id": o.product_id,
                "region": o.region,
                "price_gbp": float(o.price_gbp) if o.price_gbp else None,
                "price_eur": float(o.price_eur) if o.price_eur else None,
                "price_usd": float(o.price_usd) if o.price_usd else None,
                "stock_level": o.stock_level,
                "last_updated": o.last_updated.isoformat() if o.last_updated else None,
            }
            for o in rows
        ],
        "offset": offset,
        "limit": limit,
        "has_more": has_more,
    }


@fms_router.get("/suppliers")
def fms_list_suppliers(
    db: Session = Depends(_get_fms_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all supplier names in the FMS."""
    Product, VendorOffer = _get_models()

    stmt = (
        select(VendorOffer.vendor_name)
        .group_by(VendorOffer.vendor_name)
        .order_by(VendorOffer.vendor_name)
    )
    names = [str(n) for n in db.scalars(stmt).all() if n]
    return {"vendors": names, "count": len(names)}
