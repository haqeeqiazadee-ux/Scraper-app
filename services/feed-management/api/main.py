"""B2B catalog read API. Run: ``uvicorn api.main:app --host 0.0.0.0 --port 8080``"""

from __future__ import annotations

import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import Select, func, or_, select, text
from sqlalchemy.orm import Session, selectinload

load_dotenv()

from api.deps import get_db, verify_api_key
from api.schemas import (
    HealthResponse,
    OfferListResponse,
    ProductDetail,
    ProductListResponse,
    ProductSummary,
    SupplierListResponse,
    VendorOfferPublic,
)
from core.database import Product, VendorOffer

_MAX_PAGE = 200


def _cors_origins() -> list[str]:
    raw = (os.environ.get("B2B_CORS_ORIGINS") or "*").strip()
    if raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


app = FastAPI(
    title="B2B Data Aggregator API",
    description="Read-only access to catalog ``products`` and ``vendor_offers`` (same MySQL as Streamlit / PHP).",
    version="1.0.0",
)
_cors = _cors_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors,
    allow_credentials=_cors != ["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        db.execute(text("SELECT 1"))
        return HealthResponse(ok=True, database="connected")
    except Exception:
        return HealthResponse(ok=False, database="error")


@app.get("/v1/products", response_model=ProductListResponse, dependencies=[Depends(verify_api_key)], tags=["products"])
def list_products(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=_MAX_PAGE),
    brand: str | None = Query(None, description="Exact match (trimmed)"),
    mpn: str | None = Query(None, description="Contains match"),
    q: str | None = Query(None, description="Search title, MPN, or brand (contains)"),
) -> ProductListResponse:
    stmt: Select[tuple[Product]] = select(Product).order_by(Product.id)
    if flags := (brand or "").strip():
        stmt = stmt.where(func.trim(Product.brand) == flags)
    if mpn_pat := (mpn or "").strip():
        stmt = stmt.where(Product.mpn.contains(mpn_pat))
    if q_pat := (q or "").strip():
        stmt = stmt.where(
            or_(
                Product.title.contains(q_pat),
                Product.mpn.contains(q_pat),
                Product.brand.contains(q_pat),
            ),
        )
    stmt = stmt.offset(offset).limit(limit + 1)
    rows = list(db.scalars(stmt).all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    return ProductListResponse(
        items=[ProductSummary.model_validate(r) for r in rows],
        offset=offset,
        limit=limit,
        has_more=has_more,
    )


@app.get(
    "/v1/products/{product_id}",
    response_model=ProductDetail,
    dependencies=[Depends(verify_api_key)],
    tags=["products"],
)
def get_product(product_id: int, db: Session = Depends(get_db)) -> ProductDetail:
    stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.offers))
    )
    row = db.scalars(stmt).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")
    offers_sorted = sorted(row.offers, key=lambda o: (o.vendor_name, o.region, o.id))
    return ProductDetail(
        id=row.id,
        mpn=row.mpn,
        brand=row.brand,
        title=row.title,
        category=row.category,
        ean=row.ean,
        asin=row.asin,
        amazon_monthly_sales=row.amazon_monthly_sales,
        amazon_url=row.amazon_url,
        offers=[VendorOfferPublic.model_validate(o) for o in offers_sorted],
    )


@app.get("/v1/offers", response_model=OfferListResponse, dependencies=[Depends(verify_api_key)], tags=["offers"])
def list_offers(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=_MAX_PAGE),
    vendor_name: str | None = Query(None),
    product_id: int | None = Query(None, ge=1),
    region: Literal["UK", "EU", "USA"] | None = Query(None),
    min_stock: int | None = Query(None, ge=0),
) -> OfferListResponse:
    stmt: Select[tuple[VendorOffer]] = select(VendorOffer).order_by(VendorOffer.id)
    if vendor_name:
        stmt = stmt.where(VendorOffer.vendor_name == vendor_name.strip())
    if product_id is not None:
        stmt = stmt.where(VendorOffer.product_id == product_id)
    if region:
        stmt = stmt.where(VendorOffer.region == region)
    if min_stock is not None:
        stmt = stmt.where(VendorOffer.stock_level.is_not(None)).where(VendorOffer.stock_level >= min_stock)
    stmt = stmt.offset(offset).limit(limit + 1)
    rows = list(db.scalars(stmt).all())
    has_more = len(rows) > limit
    if has_more:
        rows = rows[:limit]
    return OfferListResponse(
        items=[VendorOfferPublic.model_validate(r) for r in rows],
        offset=offset,
        limit=limit,
        has_more=has_more,
    )


@app.get(
    "/v1/suppliers",
    response_model=SupplierListResponse,
    dependencies=[Depends(verify_api_key)],
    tags=["suppliers"],
)
def list_suppliers(db: Session = Depends(get_db)) -> SupplierListResponse:
    stmt = select(VendorOffer.vendor_name).group_by(VendorOffer.vendor_name).order_by(
        VendorOffer.vendor_name,
    )
    names = [str(n) for n in db.scalars(stmt).all() if n]
    return SupplierListResponse(vendors=names)


if __name__ == "__main__":
    import uvicorn

    from dotenv import load_dotenv

    load_dotenv()
    port = int((os.environ.get("B2B_API_PORT") or "8080").strip() or "8080")
    uvicorn.run("api.main:app", host="0.0.0.0", port=port, reload=False)
