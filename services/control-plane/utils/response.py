"""
Response helper utilities for the Zero Checksum Public API.

Provides functions that build the standard API envelope so every endpoint
returns a consistent shape.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import uuid4

from starlette.requests import Request
from starlette.responses import JSONResponse


def generate_request_id() -> str:
    """Generate a unique request identifier (``req_`` + 20 hex chars)."""
    return "req_" + uuid4().hex[:20]


def _build_meta(request: Request, credits_used: int) -> dict:
    """Build the ``meta`` block for an API response."""
    start_time = getattr(request.state, "start_time", time.time())
    duration_ms = int((time.time() - start_time) * 1000)
    return {
        "credits_used": credits_used,
        "credits_remaining": getattr(request.state, "credits_remaining", None),
        "duration_ms": duration_ms,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def success_response(
    data: dict | list | None,
    request: Request,
    credits_used: int = 0,
) -> dict:
    """Return a *success* envelope as a plain dict (let FastAPI serialise)."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    idempotency_key = getattr(request.state, "idempotency_key", None)
    return {
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "status": "success",
        "data": data,
        "meta": _build_meta(request, credits_used),
        "errors": None,
    }


def accepted_response(
    job_id: str,
    request: Request,
    credits_used: int = 0,
) -> dict:
    """Return an *accepted* envelope for async operations."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    idempotency_key = getattr(request.state, "idempotency_key", None)
    return {
        "request_id": request_id,
        "idempotency_key": idempotency_key,
        "status": "accepted",
        "data": {"job_id": job_id},
        "meta": _build_meta(request, credits_used),
        "errors": None,
    }


def error_response(
    errors: list[dict],
    request: Request,
    status_code: int = 400,
) -> JSONResponse:
    """Return an *error* ``JSONResponse`` with the standard envelope."""
    request_id = getattr(request.state, "request_id", generate_request_id())
    idempotency_key = getattr(request.state, "idempotency_key", None)
    return JSONResponse(
        status_code=status_code,
        content={
            "request_id": request_id,
            "idempotency_key": idempotency_key,
            "status": "error",
            "data": None,
            "meta": _build_meta(request, credits_used=0),
            "errors": errors,
        },
    )
