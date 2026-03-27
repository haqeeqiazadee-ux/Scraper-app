"""Keepa API endpoints — Amazon product data via Keepa."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

# Lazy-initialized connector
_keepa = None


def _get_keepa():
    """Lazy-initialize the KeepaConnector."""
    global _keepa
    if _keepa is None:
        try:
            from packages.connectors.keepa_connector import KeepaConnector
            _keepa = KeepaConnector()
        except ImportError as e:
            raise HTTPException(status_code=503, detail=f"Keepa module not available: {e}")
    return _keepa


class KeepaQueryRequest(BaseModel):
    """Request body for Keepa product query."""
    query: str  # ASIN, Amazon URL, or keyword
    domain: str = "US"
    include_offers: bool = False
    include_buybox: bool = False
    max_results: int = 10


class KeepaSearchRequest(BaseModel):
    """Request body for Keepa product search."""
    title: Optional[str] = None
    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    author: Optional[str] = None
    min_price: Optional[int] = None  # cents
    max_price: Optional[int] = None  # cents
    min_rating: Optional[int] = None  # 0-50 scale
    domain: str = "US"
    max_results: int = 20


class KeepaDealsRequest(BaseModel):
    """Request body for Keepa deals."""
    min_discount_percent: int = 20
    min_price: Optional[int] = None  # cents
    max_price: Optional[int] = None  # cents
    min_rating: int = 0
    domain: str = "US"
    categories: Optional[list[int]] = None


def _extract_asin(text: str) -> Optional[str]:
    """Extract ASIN from input (could be ASIN, URL, or other)."""
    # Direct ASIN (10 alphanumeric chars)
    if re.match(r'^[A-Z0-9]{10}$', text.strip()):
        return text.strip()
    # Amazon URL with ASIN
    match = re.search(r'/(?:dp|gp/product|ASIN)/([A-Z0-9]{10})', text)
    if match:
        return match.group(1)
    return None


def _extract_asins(text: str) -> list[str]:
    """Extract multiple ASINs from input (comma-separated or space-separated)."""
    asins = []
    parts = re.split(r'[,\s]+', text.strip())
    for part in parts:
        asin = _extract_asin(part.strip())
        if asin:
            asins.append(asin)
    return asins


@router.post("/keepa/query")
async def keepa_query(req: KeepaQueryRequest) -> dict[str, Any]:
    """Query Keepa for product data.

    Accepts:
    - Single ASIN: B0088PUEPK
    - Multiple ASINs: B0088PUEPK, B09V3KXJPB
    - Amazon URL: https://www.amazon.com/dp/B0088PUEPK
    - Keyword search: wireless mouse (uses product_finder)
    """
    keepa = _get_keepa()
    query = req.query.strip()

    if not query:
        raise HTTPException(status_code=400, detail="Query is required")

    # Try to extract ASINs first
    asins = _extract_asins(query)

    if asins:
        # Direct ASIN lookup
        products = await keepa.query_products(
            asins=asins[:100],
            domain=req.domain,
            include_offers=req.include_offers,
            include_buybox=req.include_buybox,
            include_rating=True,
            stats_days=90,
            history_days=30,
        )
        return {
            "query": query,
            "query_type": "asin_lookup",
            "domain": req.domain,
            "asins": asins,
            "products": products,
            "count": len(products),
            "tokens_left": keepa.tokens_left,
        }
    else:
        # Keyword search via product_finder
        found_asins = await keepa.search_products(
            domain=req.domain,
            n_products=req.max_results,
            title=query,
        )

        products = []
        if found_asins:
            products = await keepa.query_products(
                asins=found_asins[:req.max_results],
                domain=req.domain,
                include_rating=True,
                stats_days=90,
                history_days=7,
            )

        return {
            "query": query,
            "query_type": "keyword_search",
            "domain": req.domain,
            "asins": found_asins[:req.max_results],
            "products": products,
            "count": len(products),
            "tokens_left": keepa.tokens_left,
        }


@router.post("/keepa/search")
async def keepa_search(req: KeepaSearchRequest) -> dict[str, Any]:
    """Advanced Keepa product search with filters."""
    keepa = _get_keepa()

    params: dict[str, Any] = {}
    if req.title:
        params["title"] = req.title
    if req.brand:
        params["brand"] = req.brand
    if req.manufacturer:
        params["manufacturer"] = req.manufacturer
    if req.author:
        params["author"] = req.author
    if req.min_price is not None:
        params["current_NEW_gte"] = req.min_price
    if req.max_price is not None:
        params["current_NEW_lte"] = req.max_price
    if req.min_rating is not None:
        params["current_RATING_gte"] = req.min_rating

    if not params:
        raise HTTPException(status_code=400, detail="At least one search parameter required")

    asins = await keepa.search_products(
        domain=req.domain,
        n_products=req.max_results,
        **params,
    )

    products = []
    if asins:
        products = await keepa.query_products(
            asins=asins[:req.max_results],
            domain=req.domain,
            include_rating=True,
            stats_days=90,
        )

    return {
        "query_type": "advanced_search",
        "params": params,
        "domain": req.domain,
        "asins": asins,
        "products": products,
        "count": len(products),
        "tokens_left": keepa.tokens_left,
    }


@router.post("/keepa/deals")
async def keepa_deals(req: KeepaDealsRequest) -> dict[str, Any]:
    """Find current Amazon deals (price drops)."""
    keepa = _get_keepa()

    price_range = None
    if req.min_price is not None or req.max_price is not None:
        price_range = (req.min_price or 0, req.max_price or 999999)

    deals = await keepa.find_deals(
        domain=req.domain,
        min_discount_percent=req.min_discount_percent,
        price_range=price_range,
        min_rating=req.min_rating,
        categories=req.categories,
    )

    return {
        "query_type": "deals",
        "domain": req.domain,
        "deals": deals[:50],
        "count": len(deals),
        "tokens_left": keepa.tokens_left,
    }


@router.get("/keepa/bestsellers/{category}")
async def keepa_bestsellers(
    category: str,
    domain: str = Query("US"),
) -> dict[str, Any]:
    """Get best seller ASINs for a category."""
    keepa = _get_keepa()

    asins = await keepa.best_sellers(category=category, domain=domain)

    return {
        "query_type": "bestsellers",
        "category": category,
        "domain": domain,
        "asins": asins[:100],
        "count": len(asins),
        "tokens_left": keepa.tokens_left,
    }


@router.get("/keepa/categories")
async def keepa_categories(
    term: str = Query(...),
    domain: str = Query("US"),
) -> dict[str, Any]:
    """Search Amazon categories by keyword."""
    keepa = _get_keepa()

    categories = await keepa.search_categories(term=term, domain=domain)

    return {
        "query_type": "category_search",
        "term": term,
        "domain": domain,
        "categories": categories,
        "count": len(categories),
    }


@router.get("/keepa/status")
async def keepa_status() -> dict[str, Any]:
    """Get Keepa API status and token balance."""
    keepa = _get_keepa()
    return {
        "tokens_left": keepa.tokens_left,
        "api_key_set": bool(keepa._api_key),
        "metrics": {
            "total_requests": keepa._metrics.total_requests,
            "successful_requests": keepa._metrics.successful_requests,
            "failed_requests": keepa._metrics.failed_requests,
        },
    }
