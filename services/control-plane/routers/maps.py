"""Google Maps API endpoints — business data scraping."""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_maps = None


def _get_maps():
    global _maps
    if _maps is None:
        from packages.connectors.google_maps_connector import GoogleMapsConnector
        _maps = GoogleMapsConnector()
    return _maps


class MapsSearchRequest(BaseModel):
    query: str
    max_results: int = 20
    location: Optional[str] = None
    language: str = "en"


class MapsDetailRequest(BaseModel):
    place_id: str


@router.post("/maps/search")
async def maps_search(req: MapsSearchRequest) -> dict[str, Any]:
    """Search Google Maps for businesses."""
    maps = _get_maps()

    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query is required")

    results = await maps.search_businesses(
        query=req.query.strip(),
        max_results=req.max_results,
        location=req.location,
        language=req.language,
    )

    return {
        "query": req.query,
        "results": results,
        "count": len(results),
    }


@router.post("/maps/details")
async def maps_details(req: MapsDetailRequest) -> dict[str, Any]:
    """Get detailed info for a single business."""
    maps = _get_maps()

    details = await maps.get_business_details(req.place_id)
    if not details:
        raise HTTPException(status_code=404, detail="Business not found")

    return {"business": details}


@router.get("/maps/status")
async def maps_status() -> dict[str, Any]:
    """Get Google Maps connector status."""
    maps = _get_maps()
    return {
        "google_api_configured": bool(maps._google_api_key),
        "serpapi_configured": bool(maps._serpapi_key),
        "browser_fallback": True,
        "metrics": {
            "total_requests": maps._metrics.total_requests,
            "successful_requests": maps._metrics.successful_requests,
            "failed_requests": maps._metrics.failed_requests,
        },
    }
