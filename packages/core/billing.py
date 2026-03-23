"""
Square Billing Adapter — subscription management and payment processing.

Uses the Square Subscriptions API for plan management and the Payments API
for one-time charges (usage overages).  Maps platform PlanTiers to Square
catalog subscription plans.

Environment variables:
    SQUARE_ACCESS_TOKEN    — Square API access token
    SQUARE_LOCATION_ID     — Square location ID
    SQUARE_APPLICATION_ID  — Square application ID
    SQUARE_ENVIRONMENT     — "sandbox" or "production" (default: sandbox)
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Square API base URLs
SQUARE_SANDBOX_URL = "https://connect.squareupsandbox.com/v2"
SQUARE_PRODUCTION_URL = "https://connect.squareup.com/v2"


@dataclass
class PaymentResult:
    """Result of a payment or subscription operation."""

    success: bool
    payment_id: str = ""
    subscription_id: str = ""
    customer_id: str = ""
    error: Optional[str] = None
    amount_cents: int = 0
    currency: str = "USD"


@dataclass
class SubscriptionInfo:
    """Current subscription state for a tenant."""

    subscription_id: str
    customer_id: str
    plan_id: str
    status: str  # ACTIVE, CANCELED, PAUSED, PENDING
    start_date: str = ""
    charged_through_date: str = ""


# Plan tier -> monthly price in cents
PLAN_PRICES: dict[str, int] = {
    "free": 0,
    "starter": 2900,      # $29/mo
    "pro": 9900,           # $99/mo
    "enterprise": 49900,   # $499/mo
}


class SquareBillingAdapter:
    """Handles subscription management and payments via Square API.

    Uses lazy initialization — the httpx client is created on first use.
    """

    def __init__(
        self,
        access_token: Optional[str] = None,
        location_id: Optional[str] = None,
        application_id: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> None:
        self._access_token = access_token or os.environ.get("SQUARE_ACCESS_TOKEN", "")
        self._location_id = location_id or os.environ.get("SQUARE_LOCATION_ID", "")
        self._application_id = application_id or os.environ.get("SQUARE_APPLICATION_ID", "")
        env = environment or os.environ.get("SQUARE_ENVIRONMENT", "sandbox")
        self._base_url = SQUARE_PRODUCTION_URL if env == "production" else SQUARE_SANDBOX_URL
        self._client = None

    async def _get_client(self):
        """Lazy-init httpx client."""
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                    "Square-Version": "2024-12-18",
                },
                timeout=30,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── Customer Management ──────────────────────────────────────────────

    async def create_customer(
        self,
        tenant_id: str,
        email: str,
        name: str = "",
    ) -> PaymentResult:
        """Create a Square customer for a tenant."""
        from uuid import uuid4

        client = await self._get_client()
        payload = {
            "idempotency_key": str(uuid4()),
            "email_address": email,
            "reference_id": tenant_id,
        }
        if name:
            parts = name.split(" ", 1)
            payload["given_name"] = parts[0]
            if len(parts) > 1:
                payload["family_name"] = parts[1]

        resp = await client.post("/customers", json=payload)
        data = resp.json()

        if resp.status_code == 200 and "customer" in data:
            customer_id = data["customer"]["id"]
            logger.info("Square customer created", extra={"tenant_id": tenant_id, "customer_id": customer_id})
            return PaymentResult(success=True, customer_id=customer_id)

        error_msg = _extract_error(data)
        logger.error("Square customer creation failed", extra={"tenant_id": tenant_id, "error": error_msg})
        return PaymentResult(success=False, error=error_msg)

    async def get_customer_by_tenant(self, tenant_id: str) -> Optional[str]:
        """Look up Square customer ID by tenant reference_id."""
        client = await self._get_client()
        resp = await client.post("/customers/search", json={
            "query": {
                "filter": {
                    "reference_id": {"exact": tenant_id}
                }
            }
        })
        data = resp.json()
        customers = data.get("customers", [])
        if customers:
            return customers[0]["id"]
        return None

    # ── Catalog (Plan Setup) ─────────────────────────────────────────────

    async def create_subscription_plan(
        self,
        plan_name: str,
        amount_cents: int,
        currency: str = "USD",
    ) -> Optional[str]:
        """Create a subscription plan in the Square catalog.

        Returns the catalog object ID, or None on failure.
        """
        from uuid import uuid4

        client = await self._get_client()
        payload = {
            "idempotency_key": str(uuid4()),
            "object": {
                "type": "SUBSCRIPTION_PLAN",
                "id": f"#plan_{plan_name}",
                "subscription_plan_data": {
                    "name": f"Scraper Platform — {plan_name.title()}",
                    "phases": [
                        {
                            "cadence": "MONTHLY",
                            "recurring_price_money": {
                                "amount": amount_cents,
                                "currency": currency,
                            },
                        }
                    ],
                },
            },
        }
        resp = await client.post("/catalog/object", json=payload)
        data = resp.json()

        if resp.status_code == 200 and "catalog_object" in data:
            obj_id = data["catalog_object"]["id"]
            logger.info("Subscription plan created", extra={"plan": plan_name, "catalog_id": obj_id})
            return obj_id

        logger.error("Failed to create plan", extra={"plan": plan_name, "error": _extract_error(data)})
        return None

    # ── Subscriptions ────────────────────────────────────────────────────

    async def create_subscription(
        self,
        customer_id: str,
        plan_catalog_id: str,
        card_id: Optional[str] = None,
    ) -> PaymentResult:
        """Subscribe a customer to a plan."""
        from uuid import uuid4

        client = await self._get_client()
        payload = {
            "idempotency_key": str(uuid4()),
            "location_id": self._location_id,
            "plan_variation_id": plan_catalog_id,
            "customer_id": customer_id,
        }
        if card_id:
            payload["card_id"] = card_id

        resp = await client.post("/subscriptions", json=payload)
        data = resp.json()

        if resp.status_code == 200 and "subscription" in data:
            sub = data["subscription"]
            logger.info("Subscription created", extra={
                "customer_id": customer_id,
                "subscription_id": sub["id"],
            })
            return PaymentResult(
                success=True,
                subscription_id=sub["id"],
                customer_id=customer_id,
            )

        error_msg = _extract_error(data)
        logger.error("Subscription creation failed", extra={"error": error_msg})
        return PaymentResult(success=False, error=error_msg)

    async def cancel_subscription(self, subscription_id: str) -> PaymentResult:
        """Cancel an active subscription."""
        client = await self._get_client()
        resp = await client.post(f"/subscriptions/{subscription_id}/cancel")
        data = resp.json()

        if resp.status_code == 200 and "subscription" in data:
            logger.info("Subscription canceled", extra={"subscription_id": subscription_id})
            return PaymentResult(success=True, subscription_id=subscription_id)

        return PaymentResult(success=False, error=_extract_error(data))

    async def get_subscription(self, subscription_id: str) -> Optional[SubscriptionInfo]:
        """Retrieve subscription details."""
        client = await self._get_client()
        resp = await client.get(f"/subscriptions/{subscription_id}")
        data = resp.json()

        if resp.status_code == 200 and "subscription" in data:
            sub = data["subscription"]
            return SubscriptionInfo(
                subscription_id=sub["id"],
                customer_id=sub.get("customer_id", ""),
                plan_id=sub.get("plan_variation_id", ""),
                status=sub.get("status", "UNKNOWN"),
                start_date=sub.get("start_date", ""),
                charged_through_date=sub.get("charged_through_date", ""),
            )
        return None

    # ── One-Time Payments (Usage Overages) ───────────────────────────────

    async def charge_overage(
        self,
        customer_id: str,
        amount_cents: int,
        description: str = "Usage overage",
        card_id: Optional[str] = None,
    ) -> PaymentResult:
        """Charge a one-time payment for usage overages."""
        from uuid import uuid4

        client = await self._get_client()
        payload = {
            "idempotency_key": str(uuid4()),
            "amount_money": {
                "amount": amount_cents,
                "currency": "USD",
            },
            "location_id": self._location_id,
            "customer_id": customer_id,
            "note": description,
            "autocomplete": True,
        }
        if card_id:
            payload["source_id"] = card_id

        resp = await client.post("/payments", json=payload)
        data = resp.json()

        if resp.status_code == 200 and "payment" in data:
            payment = data["payment"]
            logger.info("Overage charged", extra={
                "customer_id": customer_id,
                "amount_cents": amount_cents,
                "payment_id": payment["id"],
            })
            return PaymentResult(
                success=True,
                payment_id=payment["id"],
                customer_id=customer_id,
                amount_cents=amount_cents,
            )

        return PaymentResult(success=False, error=_extract_error(data))

    # ── Webhook Verification ─────────────────────────────────────────────

    @staticmethod
    def verify_webhook_signature(
        body: bytes,
        signature: str,
        signature_key: str,
        notification_url: str,
    ) -> bool:
        """Verify a Square webhook signature."""
        import hashlib
        import hmac
        import base64

        combined = notification_url.encode() + body
        expected = base64.b64encode(
            hmac.new(signature_key.encode(), combined, hashlib.sha256).digest()
        ).decode()
        return hmac.compare_digest(expected, signature)


def _extract_error(data: dict) -> str:
    """Extract error message from Square API response."""
    errors = data.get("errors", [])
    if errors:
        return "; ".join(e.get("detail", e.get("code", "unknown")) for e in errors)
    return "Unknown Square API error"
