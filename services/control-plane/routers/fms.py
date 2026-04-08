"""Feed Management System (FMS) — query B2B product catalog on Supabase.

Uses the SAME Supabase PostgreSQL as the scraper (fms_* prefixed tables).
Tables created via migration: fms_products, fms_vendor_offers, fms_master_products.

Endpoints:
  GET /fms/products       — Search products (MPN, brand, title)
  GET /fms/products/{id}  — Product detail with all vendor offers
  GET /fms/offers         — List vendor offers with filters
  GET /fms/suppliers      — List all suppliers
  GET /fms/health         — Connectivity check
  GET /fms/stats          — Row counts
"""

from __future__ import annotations

import logging
from typing import Any, Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from services.control_plane.dependencies import get_session, get_tenant_id

logger = structlog.get_logger(__name__)

fms_router = APIRouter(prefix="/fms", tags=["Feed Management"])


# ---------------------------------------------------------------------------
# Endpoints — use scraper's existing Supabase connection
# ---------------------------------------------------------------------------

@fms_router.get("/health")
async def fms_health(session: AsyncSession = Depends(get_session)):
    """Check FMS tables exist on Supabase."""
    try:
        result = await session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name LIKE 'fms_%'"
        ))
        count = result.scalar() or 0
        return {"ok": count >= 2, "fms_tables": count, "database": "supabase"}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "database": "supabase"}


@fms_router.get("/stats")
async def fms_stats(session: AsyncSession = Depends(get_session)):
    """Row counts for all FMS tables."""
    counts = {}
    for table in ["fms_products", "fms_vendor_offers", "fms_master_products", "fms_master_incomplete_rows"]:
        try:
            result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar() or 0
        except Exception:
            counts[table] = -1
    return counts


@fms_router.get("/products")
async def fms_list_products(
    session: AsyncSession = Depends(get_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    brand: str | None = Query(None, description="Exact brand match"),
    mpn: str | None = Query(None, description="MPN contains match"),
    ean: str | None = Query(None, description="EAN exact match"),
    asin: str | None = Query(None, description="ASIN exact match"),
    q: str | None = Query(None, description="Search title, MPN, or brand"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Search FMS product catalog."""
    where_clauses = []
    params: dict[str, Any] = {"lim": limit + 1, "off": offset}

    if brand and brand.strip():
        where_clauses.append("TRIM(brand) = :brand")
        params["brand"] = brand.strip()
    if mpn and mpn.strip():
        where_clauses.append("mpn ILIKE :mpn")
        params["mpn"] = f"%{mpn.strip()}%"
    if ean and ean.strip():
        where_clauses.append("ean = :ean")
        params["ean"] = ean.strip()
    if asin and asin.strip():
        where_clauses.append("asin = :asin")
        params["asin"] = asin.strip()
    if q and q.strip():
        where_clauses.append("(title ILIKE :q OR mpn ILIKE :q OR brand ILIKE :q)")
        params["q"] = f"%{q.strip()}%"

    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
    sql = f"SELECT id, mpn, brand, title, category, ean, asin FROM fms_products WHERE {where_sql} ORDER BY id OFFSET :off LIMIT :lim"

    result = await session.execute(text(sql), params)
    rows = [dict(r._mapping) for r in result.fetchall()]
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return {"items": rows, "offset": offset, "limit": limit, "has_more": has_more}


@fms_router.get("/products/{product_id}")
async def fms_get_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Get product detail with all vendor offers (price comparison)."""
    # Product
    result = await session.execute(
        text("SELECT * FROM fms_products WHERE id = :id"),
        {"id": product_id},
    )
    row = result.fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    product = dict(row._mapping)

    # Offers
    offers_result = await session.execute(
        text("SELECT * FROM fms_vendor_offers WHERE product_id = :pid ORDER BY vendor_name, region"),
        {"pid": product_id},
    )
    offers = []
    for o in offers_result.fetchall():
        od = dict(o._mapping)
        # Convert Decimal to float for JSON
        for k in ("price_gbp", "price_eur", "price_usd"):
            if od.get(k) is not None:
                od[k] = float(od[k])
        if od.get("last_updated"):
            od["last_updated"] = od["last_updated"].isoformat()
        offers.append(od)

    product["offers"] = offers
    return product


@fms_router.get("/offers")
async def fms_list_offers(
    session: AsyncSession = Depends(get_session),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    vendor_name: str | None = Query(None),
    product_id: int | None = Query(None, ge=1),
    region: Literal["UK", "EU", "USA"] | None = Query(None),
    min_stock: int | None = Query(None, ge=0),
    min_price_eur: float | None = Query(None, ge=0),
    max_price_eur: float | None = Query(None, ge=0),
    tenant_id: str = Depends(get_tenant_id),
):
    """List vendor offers with filters."""
    where_clauses = []
    params: dict[str, Any] = {"lim": limit + 1, "off": offset}

    if vendor_name:
        where_clauses.append("vendor_name = :vn")
        params["vn"] = vendor_name.strip()
    if product_id is not None:
        where_clauses.append("product_id = :pid")
        params["pid"] = product_id
    if region:
        where_clauses.append("region = :reg")
        params["reg"] = region
    if min_stock is not None:
        where_clauses.append("stock_level IS NOT NULL AND stock_level >= :ms")
        params["ms"] = min_stock
    if min_price_eur is not None:
        where_clauses.append("price_eur >= :minp")
        params["minp"] = min_price_eur
    if max_price_eur is not None:
        where_clauses.append("price_eur <= :maxp")
        params["maxp"] = max_price_eur

    where_sql = " AND ".join(where_clauses) if where_clauses else "TRUE"
    sql = f"SELECT * FROM fms_vendor_offers WHERE {where_sql} ORDER BY id OFFSET :off LIMIT :lim"

    result = await session.execute(text(sql), params)
    rows = []
    for o in result.fetchall():
        od = dict(o._mapping)
        for k in ("price_gbp", "price_eur", "price_usd"):
            if od.get(k) is not None:
                od[k] = float(od[k])
        if od.get("last_updated"):
            od["last_updated"] = od["last_updated"].isoformat()
        rows.append(od)

    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]

    return {"items": rows, "offset": offset, "limit": limit, "has_more": has_more}


@fms_router.get("/suppliers")
async def fms_list_suppliers(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all supplier names in the FMS."""
    result = await session.execute(
        text("SELECT DISTINCT vendor_name FROM fms_vendor_offers ORDER BY vendor_name")
    )
    names = [str(r[0]) for r in result.fetchall() if r[0]]
    return {"vendors": names, "count": len(names)}


# ---------------------------------------------------------------------------
# Feed Sources — manage where supplier data comes from
# ---------------------------------------------------------------------------

@fms_router.get("/feed-sources")
async def fms_list_feed_sources(
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """List all configured feed sources (SFTP/FTP/Email/URL)."""
    result = await session.execute(
        text("SELECT id, vendor_name, protocol, host, enabled, last_fetched_at, last_ingested_at FROM fms_supplier_feed_sources ORDER BY vendor_name")
    )
    sources = []
    for r in result.fetchall():
        d = dict(r._mapping)
        for k in ("last_fetched_at", "last_ingested_at"):
            if d.get(k):
                d[k] = d[k].isoformat()
        sources.append(d)
    return {"sources": sources, "count": len(sources)}


@fms_router.post("/feed-sources")
async def fms_add_feed_source(
    body: dict,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Add a new feed source (SFTP/FTP/Email/URL)."""
    vendor_name = body.get("vendor_name", "").strip()
    protocol = body.get("protocol", "sftp").strip().lower()
    if not vendor_name:
        raise HTTPException(status_code=422, detail="vendor_name is required")

    cols = ["vendor_name", "protocol"]
    vals = [f":vendor_name", f":protocol"]
    params: dict[str, Any] = {"vendor_name": vendor_name, "protocol": protocol}

    for field in ["host", "port", "username", "password_env", "remote_path", "remote_dir",
                   "remote_pattern", "local_basename", "url", "imap_host", "imap_port",
                   "imap_user", "imap_password_env", "imap_folder", "imap_subject_pattern",
                   "col_mpn", "col_ean", "col_title", "col_brand", "col_category",
                   "col_stock", "col_price", "region", "default_currency", "notes"]:
        if field in body and body[field] is not None:
            cols.append(field)
            vals.append(f":{field}")
            params[field] = body[field]

    sql = f"INSERT INTO fms_supplier_feed_sources ({', '.join(cols)}) VALUES ({', '.join(vals)}) RETURNING id"
    result = await session.execute(text(sql), params)
    await session.commit()
    new_id = result.scalar()
    return {"id": new_id, "vendor_name": vendor_name, "protocol": protocol, "status": "created"}


@fms_router.delete("/feed-sources/{source_id}")
async def fms_delete_feed_source(
    source_id: int,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
):
    """Delete a feed source."""
    await session.execute(text("DELETE FROM fms_supplier_feed_sources WHERE id = :id"), {"id": source_id})
    await session.commit()
    return {"status": "deleted", "id": source_id}
