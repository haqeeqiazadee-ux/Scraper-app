"""Google OAuth2 router for authenticated scraping.

Provides OAuth2 flow for Google Account sessions, enabling scraping of
Google Sheets, Drive, Analytics, and Search Console via API tokens
instead of browser cookies.
"""

from __future__ import annotations

import os
import secrets
import time
import uuid
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from services.control_plane.dependencies import get_database, get_tenant_id

logger = structlog.get_logger(__name__)

google_auth_router = APIRouter(tags=["Google Auth"])

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.environ.get(
    "GOOGLE_OAUTH_REDIRECT_URI",
    "https://myscraper.netlify.app/auth-scrape",
)

GOOGLE_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/analytics.readonly",
]

# In-memory state store for CSRF protection (state_token -> metadata)
_oauth_states: dict[str, dict] = {}


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GoogleCallbackRequest(BaseModel):
    code: str
    state: str


class GoogleRefreshRequest(BaseModel):
    session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@google_auth_router.get("/auth-scrape/google/status")
async def google_status() -> dict:
    """Return whether Google OAuth is configured and available scopes."""
    return {
        "configured": bool(GOOGLE_CLIENT_ID),
        "scopes": GOOGLE_SCOPES,
    }


@google_auth_router.get("/auth-scrape/google/auth-url")
async def get_google_auth_url(
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Generate a Google OAuth2 authorization URL with CSRF state token."""
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not configured. Set GOOGLE_CLIENT_ID environment variable.",
        )

    state = secrets.token_urlsafe(32)
    _oauth_states[state] = {
        "tenant_id": tenant_id,
        "created_at": time.time(),
    }

    # Clean up stale states older than 10 minutes
    cutoff = time.time() - 600
    stale_keys = [k for k, v in _oauth_states.items() if v["created_at"] < cutoff]
    for k in stale_keys:
        _oauth_states.pop(k, None)

    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": " ".join(GOOGLE_SCOPES),
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    logger.info("google_auth.auth_url_generated", tenant_id=tenant_id)
    return {"auth_url": auth_url, "state": state}


@google_auth_router.post("/auth-scrape/google/callback")
async def google_callback(
    body: GoogleCallbackRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Exchange OAuth2 authorization code for tokens and create a session."""
    import httpx

    # Validate state
    state_data = _oauth_states.get(body.state)
    if state_data is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    if state_data["tenant_id"] != tenant_id:
        raise HTTPException(status_code=403, detail="State token tenant mismatch")

    # Exchange code for tokens
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not fully configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.",
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": body.code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if token_resp.status_code != 200:
        logger.error(
            "google_auth.token_exchange_failed",
            status=token_resp.status_code,
            body=token_resp.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Google token exchange failed: {token_resp.text[:200]}",
        )

    token_data = token_resp.json()
    access_token = token_data.get("access_token", "")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    token_expiry = time.time() + expires_in

    # Get user info
    user_email = ""
    user_name = ""
    async with httpx.AsyncClient(timeout=10.0) as client:
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    if userinfo_resp.status_code == 200:
        userinfo = userinfo_resp.json()
        user_email = userinfo.get("email", "")
        user_name = userinfo.get("name", "")

    # Create session in DB
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel

        new_session = SessionModel(
            id=session_id,
            tenant_id=tenant_id,
            domain="google.com",
            session_type="google_oauth",
            cookies={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_expiry": token_expiry,
                "scopes": GOOGLE_SCOPES,
                "user_email": user_email,
                "user_name": user_name,
            },
            headers={},
            status="active",
            request_count=0,
            success_count=0,
            failure_count=0,
            created_at=now,
            last_used_at=now,
        )
        session.add(new_session)
        await session.commit()

    # Clean up used state
    _oauth_states.pop(body.state, None)

    logger.info(
        "google_auth.session_created",
        session_id=session_id,
        user_email=user_email,
        tenant_id=tenant_id,
    )

    return {
        "session_id": session_id,
        "domain": "google.com",
        "user_email": user_email,
        "user_name": user_name,
        "status": "active",
        "created_at": now.isoformat(),
    }


@google_auth_router.post("/auth-scrape/google/refresh")
async def refresh_google_token(
    body: GoogleRefreshRequest,
    tenant_id: str = Depends(get_tenant_id),
) -> dict:
    """Refresh an expired Google OAuth2 access token."""
    import httpx

    db = get_database()
    async with db.session() as session:
        from packages.core.storage.models import SessionModel
        from sqlalchemy import select

        stmt = select(SessionModel).where(
            SessionModel.id == body.session_id,
            SessionModel.tenant_id == tenant_id,
        )
        result = await session.execute(stmt)
        session_model = result.scalar_one_or_none()

        if session_model is None:
            raise HTTPException(status_code=404, detail=f"Session {body.session_id} not found")

        if session_model.session_type != "google_oauth":
            raise HTTPException(status_code=400, detail="Session is not a Google OAuth session")

        cookies_data = session_model.cookies or {}
        refresh_token = cookies_data.get("refresh_token", "")

        if not refresh_token:
            raise HTTPException(status_code=400, detail="No refresh token available for this session")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Google OAuth not fully configured.",
        )

    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if token_resp.status_code != 200:
        logger.error(
            "google_auth.refresh_failed",
            status=token_resp.status_code,
            body=token_resp.text[:500],
        )
        raise HTTPException(
            status_code=502,
            detail=f"Google token refresh failed: {token_resp.text[:200]}",
        )

    token_data = token_resp.json()
    new_access_token = token_data.get("access_token", "")
    expires_in = token_data.get("expires_in", 3600)
    new_expiry = time.time() + expires_in

    # Update session in DB
    async with db.session() as session:
        from packages.core.storage.models import SessionModel
        from sqlalchemy import select

        stmt = select(SessionModel).where(SessionModel.id == body.session_id)
        result = await session.execute(stmt)
        sm = result.scalar_one_or_none()
        if sm:
            updated_cookies = dict(sm.cookies) if sm.cookies else {}
            updated_cookies["access_token"] = new_access_token
            updated_cookies["token_expiry"] = new_expiry
            sm.cookies = updated_cookies
            sm.last_used_at = datetime.now(timezone.utc)
            await session.commit()

    logger.info(
        "google_auth.token_refreshed",
        session_id=body.session_id,
        expires_in=expires_in,
    )

    return {
        "refreshed": True,
        "expires_in": expires_in,
    }
