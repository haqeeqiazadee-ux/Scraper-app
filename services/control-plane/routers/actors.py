"""Actor catalog API — serves the hard-coded 27,753 actor catalog."""
from __future__ import annotations

import logging
from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from packages.core.actor_catalog.registry import actor_catalog

logger = logging.getLogger(__name__)

actors_router = APIRouter(prefix="/actors", tags=["Actors"])


@actors_router.get("")
async def list_actors(
    q: str = Query("", description="Search query"),
    category: str = Query("", description="Filter by category"),
    developer: str = Query("", description="Filter by developer"),
    pricing_model: str = Query("", description="Filter by pricing model"),
    strategy: str = Query("", description="Filter by route strategy"),
    runnable: str = Query("", description="Filter by runnable status"),
    sort: str = Query("relevant", description="Sort: relevant, name, popular, runs, rating"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(24, ge=1, le=100, description="Page size"),
) -> dict[str, Any]:
    """List actors with search, filtering, and pagination."""
    actors, total = actor_catalog.search(
        query=q,
        category=category,
        developer=developer,
        pricing_model=pricing_model,
        strategy=strategy,
        runnable=runnable,
        sort=sort,
        offset=offset,
        limit=limit,
    )
    return {
        "success": True,
        "data": [asdict(a) for a in actors],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


@actors_router.get("/stats")
async def actor_stats() -> dict[str, Any]:
    """Aggregate actor catalog statistics."""
    return {
        "success": True,
        "data": actor_catalog.stats(),
    }


@actors_router.get("/categories")
async def actor_categories() -> dict[str, Any]:
    """List all unique actor categories."""
    return {
        "success": True,
        "data": actor_catalog.categories(),
    }


@actors_router.get("/developers")
async def actor_developers() -> dict[str, Any]:
    """List all unique actor developers."""
    return {
        "success": True,
        "data": actor_catalog.developers(),
    }


@actors_router.get("/pricing-models")
async def actor_pricing_models() -> dict[str, Any]:
    """List all unique actor pricing models."""
    return {
        "success": True,
        "data": actor_catalog.pricing_models(),
    }


@actors_router.get("/{actor_id}")
async def get_actor(actor_id: str) -> dict[str, Any]:
    """Get actor detail by ID."""
    entry = actor_catalog.get(actor_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Actor {actor_id} not found")
    return {
        "success": True,
        "data": asdict(entry),
    }
