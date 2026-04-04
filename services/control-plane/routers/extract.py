"""Extract API endpoint — fetch a URL and extract structured data by schema."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.control_plane.routers.crawl import OutputFormat

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Pydantic v2 request / response models
# ---------------------------------------------------------------------------


class ExtractRequest(BaseModel):
    """Parameters for a schema-driven extraction request."""

    model_config = {"from_attributes": True}

    url: str = Field(..., min_length=1, description="URL to fetch and extract from")
    schema: dict[str, Any] = Field(
        ...,
        alias="schema",
        description=(
            "JSON Schema describing desired fields. "
            "Example: {\"properties\": {\"title\": {\"type\": \"string\"}, \"price\": {\"type\": \"number\"}}}"
        ),
    )
    output_format: OutputFormat = Field(default=OutputFormat.json, description="Output format for results")


class ExtractResponse(BaseModel):
    """Response for the extract endpoint."""

    model_config = {"from_attributes": True}

    url: str
    extracted_data: dict[str, Any]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score (0-1)")
    extraction_method: str


# ---------------------------------------------------------------------------
# Lazy worker helper
# ---------------------------------------------------------------------------

_http_worker: Any = None


def _get_http_worker():
    """Return (or create) a reusable HttpWorker instance."""
    global _http_worker
    if _http_worker is None:
        from services.worker_http.worker import HttpWorker

        _http_worker = HttpWorker()
    return _http_worker


# ---------------------------------------------------------------------------
# Schema matching logic
# ---------------------------------------------------------------------------


def _match_to_schema(
    raw_items: list[dict[str, Any]],
    desired_schema: dict[str, Any],
) -> tuple[dict[str, Any], float]:
    """Map raw extracted items to the requested JSON schema fields.

    Returns (matched_data, confidence) where confidence is the fraction of
    requested fields that were populated.
    """
    # Derive the set of desired field names from the schema
    properties = desired_schema.get("properties", desired_schema)
    desired_fields: set[str] = set(properties.keys())

    if not desired_fields:
        return {}, 0.0

    # Flatten all raw items into one lookup keyed by lowercase field name
    flat: dict[str, Any] = {}
    for item in raw_items:
        if isinstance(item, dict):
            for key, value in item.items():
                flat[key.lower().strip()] = value

    # Try to match each desired field (case-insensitive, underscore/hyphen normalised)
    matched: dict[str, Any] = {}
    for field in desired_fields:
        normalised = field.lower().replace("-", "_").replace(" ", "_").strip()

        # Exact match
        if normalised in flat:
            matched[field] = flat[normalised]
            continue

        # Partial / fuzzy: pick first key that contains the normalised name
        for raw_key, raw_val in flat.items():
            clean_key = raw_key.replace("-", "_").replace(" ", "_")
            if normalised in clean_key or clean_key in normalised:
                matched[field] = raw_val
                break

    populated = sum(1 for v in matched.values() if v is not None and v != "")
    confidence = populated / len(desired_fields) if desired_fields else 0.0

    return matched, round(confidence, 4)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

extract_router = APIRouter(prefix="/extract", tags=["Extract"])


@extract_router.post("", status_code=200)
async def extract_by_schema(request: ExtractRequest) -> ExtractResponse:
    """Fetch a URL and extract structured data matching a JSON schema."""
    logger.info("extract.start", url=request.url, schema_fields=list(request.schema.get("properties", request.schema).keys()))

    worker = _get_http_worker()
    task: dict[str, Any] = {
        "url": request.url,
        "tenant_id": "extract",
        "paginate": False,
    }

    try:
        result = await worker.process_task(task)
    except Exception as exc:
        logger.error("extract.worker_error", url=request.url, error=str(exc))
        raise HTTPException(status_code=502, detail=f"Failed to fetch URL: {exc}") from exc

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=502,
            detail=f"Failed to fetch URL: {result.get('error', 'unknown error')}",
        )

    raw_items = result.get("extracted_data", [])
    extraction_method = "http_worker+deterministic"

    if not raw_items:
        logger.warning("extract.no_data", url=request.url)
        return ExtractResponse(
            url=request.url,
            extracted_data={},
            confidence=0.0,
            extraction_method=extraction_method,
        )

    matched_data, confidence = _match_to_schema(raw_items, request.schema)

    logger.info(
        "extract.complete",
        url=request.url,
        confidence=confidence,
        matched_fields=len(matched_data),
    )

    return ExtractResponse(
        url=request.url,
        extracted_data=matched_data,
        confidence=confidence,
        extraction_method=extraction_method,
    )
