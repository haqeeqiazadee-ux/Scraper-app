"""
Billing Router — Square-powered subscription and payment endpoints.

Endpoints:
    POST /billing/customers         — Create a Square customer for a tenant
    POST /billing/subscribe         — Subscribe a tenant to a plan
    POST /billing/cancel            — Cancel a subscription
    GET  /billing/subscription/{id} — Get subscription details
    POST /billing/charge-overage    — Charge a one-time overage payment
    POST /billing/webhooks/square   — Receive Square webhook events
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from packages.core.billing import SquareBillingAdapter, PLAN_PRICES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing")

# Module-level adapter (lazy init)
_billing: SquareBillingAdapter | None = None


def _get_billing() -> SquareBillingAdapter:
    global _billing
    if _billing is None:
        _billing = SquareBillingAdapter()
    return _billing


# ── Request / Response Models ────────────────────────────────────────────


class CreateCustomerRequest(BaseModel):
    email: str
    name: str = ""


class SubscribeRequest(BaseModel):
    plan: str = Field(..., description="Plan tier: starter, pro, enterprise")
    plan_catalog_id: str = Field(..., description="Square catalog plan variation ID")
    card_id: Optional[str] = None


class CancelRequest(BaseModel):
    subscription_id: str


class ChargeOverageRequest(BaseModel):
    amount_cents: int = Field(..., gt=0)
    description: str = "Usage overage"
    card_id: Optional[str] = None


# ── Endpoints ────────────────────────────────────────────────────────────


@router.post("/customers")
async def create_customer(
    body: CreateCustomerRequest,
    x_tenant_id: str = Header(...),
):
    """Create a Square customer linked to a tenant."""
    billing = _get_billing()
    result = await billing.create_customer(
        tenant_id=x_tenant_id,
        email=body.email,
        name=body.name,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {"customer_id": result.customer_id}


@router.post("/subscribe")
async def subscribe(
    body: SubscribeRequest,
    x_tenant_id: str = Header(...),
):
    """Subscribe a tenant to a paid plan."""
    if body.plan not in PLAN_PRICES or body.plan == "free":
        raise HTTPException(status_code=400, detail=f"Invalid plan: {body.plan}")

    billing = _get_billing()

    # Look up customer
    customer_id = await billing.get_customer_by_tenant(x_tenant_id)
    if not customer_id:
        raise HTTPException(status_code=404, detail="No Square customer found for this tenant. Create one first.")

    result = await billing.create_subscription(
        customer_id=customer_id,
        plan_catalog_id=body.plan_catalog_id,
        card_id=body.card_id,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "subscription_id": result.subscription_id,
        "customer_id": result.customer_id,
        "plan": body.plan,
    }


@router.post("/cancel")
async def cancel_subscription(body: CancelRequest):
    """Cancel an active subscription."""
    billing = _get_billing()
    result = await billing.cancel_subscription(body.subscription_id)
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)
    return {"status": "canceled", "subscription_id": body.subscription_id}


@router.get("/subscription/{subscription_id}")
async def get_subscription(subscription_id: str):
    """Retrieve subscription details."""
    billing = _get_billing()
    info = await billing.get_subscription(subscription_id)
    if not info:
        raise HTTPException(status_code=404, detail="Subscription not found")
    return {
        "subscription_id": info.subscription_id,
        "customer_id": info.customer_id,
        "plan_id": info.plan_id,
        "status": info.status,
        "start_date": info.start_date,
        "charged_through_date": info.charged_through_date,
    }


@router.post("/charge-overage")
async def charge_overage(
    body: ChargeOverageRequest,
    x_tenant_id: str = Header(...),
):
    """Charge a one-time payment for usage overages."""
    billing = _get_billing()

    customer_id = await billing.get_customer_by_tenant(x_tenant_id)
    if not customer_id:
        raise HTTPException(status_code=404, detail="No Square customer found for this tenant")

    result = await billing.charge_overage(
        customer_id=customer_id,
        amount_cents=body.amount_cents,
        description=body.description,
        card_id=body.card_id,
    )
    if not result.success:
        raise HTTPException(status_code=400, detail=result.error)

    return {
        "payment_id": result.payment_id,
        "amount_cents": result.amount_cents,
    }


@router.get("/plans")
async def list_plans():
    """List available plans and their prices."""
    return {
        "plans": [
            {"tier": tier, "price_cents": price, "price_display": f"${price / 100:.2f}/mo"}
            for tier, price in PLAN_PRICES.items()
        ]
    }


@router.post("/webhooks/square")
async def square_webhook(request: Request):
    """Receive and process Square webhook events (payment confirmations, subscription changes)."""
    body = await request.body()

    # Verify Square webhook signature if key is configured
    signature_key = os.environ.get("SQUARE_WEBHOOK_SIGNATURE_KEY", "")
    if signature_key:
        signature = request.headers.get("X-Square-Hmacsha256-Signature", "")
        notification_url = str(request.url)
        if not SquareBillingAdapter.verify_webhook_signature(
            body=body,
            signature=signature,
            signature_key=signature_key,
            notification_url=notification_url,
        ):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    else:
        logger.warning("SQUARE_WEBHOOK_SIGNATURE_KEY not configured — skipping webhook signature verification")

    import json
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = event.get("type", "")
    logger.info("Square webhook received", extra={"type": event_type})

    # Handle relevant events
    if event_type == "subscription.updated":
        logger.info("Subscription updated", extra={"data": event.get("data", {})})
    elif event_type == "payment.completed":
        logger.info("Payment completed", extra={"data": event.get("data", {})})
    elif event_type == "subscription.created":
        logger.info("Subscription created", extra={"data": event.get("data", {})})

    return {"status": "ok"}
