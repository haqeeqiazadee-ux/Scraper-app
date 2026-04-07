"""Smart Scrape — Unified auto-scaling scraper engine.

One endpoint that auto-detects task complexity and escalates:
  URL -> HTTP -> Browser -> HardTarget (based on results)
  Search query -> Serper -> scrape results
  Cookies -> inject into all requests
  Schema -> match fields after extraction
  max_pages > 1 -> crawl with BFS
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import traceback
from typing import Any, Optional
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts.task import Task, TaskStatus
from packages.core.router import ExecutionRouter, RouteDecision, Lane
from packages.core.escalation import EscalationManager
from services.control_plane.dependencies import get_session, get_database, get_tenant_id

logger = structlog.get_logger(__name__)

smart_scrape_router = APIRouter(tags=["Smart Scrape"])

# ---------------------------------------------------------------------------
# Singleton instances — created once, reused across requests
# ---------------------------------------------------------------------------

_router = ExecutionRouter()
_escalation_mgr = EscalationManager(_router)

# Lane -> connector name mapping (mirrors execution.py)
_LANE_CONNECTORS: dict[Lane, str] = {
    Lane.HTTP: "http_collector",
    Lane.BROWSER: "browser_collector",
    Lane.HARD_TARGET: "hard_target_collector",
    Lane.API: "api_collector",
}

# Total timeout — must be under Railway's 120s proxy limit
_MAX_TIMEOUT_S = 90


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class SmartScrapeRequest(BaseModel):
    target: str = Field(min_length=1, description="URL or search query")
    cookies: list[dict[str, Any]] | None = Field(
        default=None,
        description="Browser cookies for auth (list of {name, value, domain, ...})",
    )
    schema_fields: dict[str, Any] | None = Field(
        default=None,
        alias="schema",
        description="JSON schema for field extraction",
    )
    intent: str = Field(
        default="everything",
        description="What to extract: products, content, contacts, links, everything",
    )
    max_pages: int = Field(default=1, ge=1, le=1000)
    max_depth: int = Field(default=0, ge=0, le=10)
    output_format: str = "json"

    model_config = {"populate_by_name": True}


class SmartScrapeStep(BaseModel):
    step: str
    timestamp: float
    duration_ms: int


class SmartScrapeResponse(BaseModel):
    target: str
    detected_as: str  # "url" or "search"
    status: str
    item_count: int
    confidence: float
    lane_used: str
    steps: list[SmartScrapeStep]
    escalation_chain: list[dict[str, Any]]
    extracted_data: list[dict[str, Any]]
    schema_matched: dict[str, Any] | None = None
    saved: bool
    saved_task_id: str
    duration_ms: int


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_url(target: str) -> bool:
    """Return True if target looks like a URL rather than a search query."""
    stripped = target.strip()
    if stripped.startswith(("http://", "https://")):
        return True
    # Contains a dot before any space (e.g., "example.com/page")
    space_idx = stripped.find(" ")
    dot_idx = stripped.find(".")
    if dot_idx != -1 and (space_idx == -1 or dot_idx < space_idx):
        # Further check: the part before the dot doesn't look like a sentence
        if "/" in stripped or not any(c == " " for c in stripped[:dot_idx]):
            return True
    return False


def _cookies_to_simple_dict(cookies: list[dict[str, Any]]) -> dict[str, str]:
    """Convert browser-style cookie list to simple {name: value} dict for HTTP workers."""
    result: dict[str, str] = {}
    for cookie in cookies:
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if name:
            result[name] = value
    return result


def _record_step(
    steps: list[dict[str, Any]], description: str, start_ts: float
) -> float:
    """Append a step to the audit trail. Returns current time for next step."""
    now = time.time()
    steps.append({
        "step": description,
        "timestamp": now,
        "duration_ms": int((now - start_ts) * 1000),
    })
    return now


# ---------------------------------------------------------------------------
# Search path
# ---------------------------------------------------------------------------


async def _handle_search(
    query: str,
    max_results: int,
    steps: list[dict[str, Any]],
    op_start: float,
) -> dict[str, Any]:
    """Execute the search-and-scrape path using Serper + HTTP scraping."""
    import os

    step_ts = time.time()

    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        _record_step(steps, "Search failed: SERPER_API_KEY not configured", step_ts)
        return {
            "status": "failed",
            "error": "SERPER_API_KEY not configured. Set the env var (free at https://serper.dev).",
            "extracted_data": [],
            "item_count": 0,
            "confidence": 0,
            "lane_used": "search",
        }

    # Lazy import to avoid circular deps
    from services.control_plane.routers.search import _serper_search, _scrape_url

    # Step 1 — Serper search
    search_hits = await _serper_search(query, max_results, api_key)
    step_ts = _record_step(
        steps,
        f"Serper search returned {len(search_hits)} results for query",
        step_ts,
    )

    if not search_hits:
        return {
            "status": "success",
            "extracted_data": [],
            "item_count": 0,
            "confidence": 0,
            "lane_used": "search",
        }

    # Step 2 — scrape each URL concurrently
    semaphore = asyncio.Semaphore(3)
    scrape_coros = [_scrape_url(hit["url"], semaphore) for hit in search_hits]
    raw_results = await asyncio.gather(*scrape_coros, return_exceptions=True)
    step_ts = _record_step(
        steps, f"Scraped {len(raw_results)} search result URLs", step_ts
    )

    # Step 3 — aggregate
    all_items: list[dict[str, Any]] = []
    for hit, raw in zip(search_hits, raw_results):
        if isinstance(raw, BaseException):
            all_items.append({
                "url": hit["url"],
                "title": hit.get("title", ""),
                "status": "failed",
                "error": str(raw),
            })
            continue
        extracted = raw.get("extracted_data", [])
        all_items.append({
            "url": hit["url"],
            "title": hit.get("title", ""),
            "status": raw.get("status", "success"),
            "extracted_data": extracted,
            "item_count": len(extracted) if isinstance(extracted, list) else 0,
        })

    return {
        "status": "success",
        "extracted_data": all_items,
        "item_count": len(all_items),
        "confidence": 0.8,
        "lane_used": "search",
    }


# ---------------------------------------------------------------------------
# Helper: save platform API results to DB
# ---------------------------------------------------------------------------

async def task_repo_create_and_save(
    session: Any, tenant_id: str, task_id: str, run_id: str,
    url: str, products: list[dict], steps: list, step_ts: float,
    request: Any,
) -> None:
    """Create task + run + result records for platform API results."""
    from packages.core.storage.repositories import TaskRepository, RunRepository, ResultRepository

    task_repo = TaskRepository(session)
    run_repo = RunRepository(session)
    result_repo = ResultRepository(session)

    await task_repo.create(
        tenant_id=tenant_id, id=task_id, url=url,
        task_type="scrape", status="completed",
        metadata_json={"source": "smart_scrape", "method": "platform_api"},
    )
    await run_repo.create(
        tenant_id=tenant_id, id=run_id, task_id=task_id,
        lane="api", connector="platform_api", status="completed",
    )
    await result_repo.create(
        tenant_id=tenant_id, task_id=task_id, run_id=run_id,
        url=url, extracted_data=products,
        item_count=len(products), confidence=0.95,
        extraction_method="platform_api",
    )
    await session.commit()
    _record_step(steps, "Saved results to database", step_ts)


# ---------------------------------------------------------------------------
# URL scrape path (with escalation)
# ---------------------------------------------------------------------------


async def _handle_url_scrape(
    url: str,
    tenant_id: str,
    cookies: list[dict[str, Any]] | None,
    schema_fields: dict[str, Any] | None,
    max_pages: int,
    max_depth: int,
    output_format: str,
    steps: list[dict[str, Any]],
    op_start: float,
    session: AsyncSession,
    request: SmartScrapeRequest | None = None,
) -> dict[str, Any]:
    """Execute the URL scrape path with lane routing and auto-escalation."""
    # Lazy imports to avoid circular dependencies
    from services.control_plane.routers.execution import _execute_lane
    from packages.core.storage.repositories import (
        TaskRepository, RunRepository, ResultRepository,
    )

    task_id = str(uuid4())
    run_id = str(uuid4())
    step_ts = time.time()

    # ---- Step 0: Try platform APIs FIRST (before any lane execution) ----
    # Amazon → Keepa, Shopify → /products.json, WooCommerce → REST API
    platform_products: list[dict[str, Any]] | None = None

    # Amazon → route ALL queries to Keepa API
    from urllib.parse import urlparse
    parsed_url = urlparse(url)
    domain_lower = parsed_url.netloc.lower()
    is_amazon = "amazon." in domain_lower

    if is_amazon:
        try:
            from services.control_plane.routers.keepa import _get_keepa_connector
            connector = _get_keepa_connector()

            # Detect query type: ASIN, search, bestsellers
            import re as _re
            asin_match = _re.search(r'/dp/([A-Z0-9]{10})', url)
            if not asin_match:
                asin_match = _re.search(r'/product/([A-Z0-9]{10})', url)

            # Extract search keywords from URL
            keyword_match = _re.search(r'[?&]k=([^&]+)', url)
            category_match = _re.search(r'/best-sellers?/([^/?\s]+)', url, _re.I)

            # Map amazon domain to Keepa domain
            keepa_domain = "US"
            if ".co.uk" in domain_lower: keepa_domain = "UK"
            elif ".de" in domain_lower: keepa_domain = "DE"
            elif ".fr" in domain_lower: keepa_domain = "FR"
            elif ".it" in domain_lower: keepa_domain = "IT"
            elif ".es" in domain_lower: keepa_domain = "ES"
            elif ".ca" in domain_lower: keepa_domain = "CA"
            elif ".co.jp" in domain_lower or ".jp" in domain_lower: keepa_domain = "JP"
            elif ".in" in domain_lower: keepa_domain = "IN"
            elif ".com.au" in domain_lower: keepa_domain = "AU"

            if asin_match:
                # Single ASIN lookup
                asin = asin_match.group(1)
                keepa_result = await connector.query(asin, domain=keepa_domain)
                if keepa_result and keepa_result.get("products"):
                    platform_products = []
                    for p in keepa_result["products"]:
                        platform_products.append({
                            "name": p.get("name", ""),
                            "price": p.get("price", p.get("amazon_price", "")),
                            "asin": p.get("asin", ""),
                            "brand": p.get("brand", ""),
                            "rating": p.get("rating", ""),
                            "review_count": p.get("reviews_count", ""),
                            "sales_rank": p.get("sales_rank", 0),
                            "image_url": p.get("image_url", ""),
                            "product_url": p.get("product_url", ""),
                            "category": p.get("category", ""),
                            "stock_status": p.get("stock_status", ""),
                            "_category": "product",
                            "_extraction_method": "keepa_api",
                        })
                    step_ts = _record_step(steps, f"Keepa API: ASIN {asin} — {len(platform_products)} product(s)", step_ts)

            elif keyword_match:
                # Keyword search
                from urllib.parse import unquote_plus
                keywords = unquote_plus(keyword_match.group(1))
                keepa_result = await connector.query(keywords, domain=keepa_domain, max_results=20)
                if keepa_result and keepa_result.get("products"):
                    platform_products = []
                    for p in keepa_result["products"]:
                        platform_products.append({
                            "name": p.get("name", ""),
                            "price": p.get("price", p.get("amazon_price", "")),
                            "asin": p.get("asin", ""),
                            "brand": p.get("brand", ""),
                            "rating": p.get("rating", ""),
                            "review_count": p.get("reviews_count", ""),
                            "sales_rank": p.get("sales_rank", 0),
                            "image_url": p.get("image_url", ""),
                            "product_url": p.get("product_url", ""),
                            "_category": "product",
                            "_extraction_method": "keepa_api",
                        })
                    step_ts = _record_step(steps, f"Keepa API: search '{keywords}' — {len(platform_products)} products", step_ts)

            elif category_match:
                # Bestsellers by category
                category = unquote_plus(category_match.group(1)) if 'unquote_plus' in dir() else category_match.group(1)
                try:
                    from urllib.parse import unquote_plus as _uqp
                    category = _uqp(category)
                except: pass
                keepa_result = await connector.query(f"bestsellers {category}", domain=keepa_domain, max_results=20)
                if keepa_result and keepa_result.get("products"):
                    platform_products = []
                    for p in keepa_result["products"]:
                        platform_products.append({
                            "name": p.get("name", ""),
                            "price": p.get("price", ""),
                            "asin": p.get("asin", ""),
                            "sales_rank": p.get("sales_rank", 0),
                            "rating": p.get("rating", ""),
                            "review_count": p.get("reviews_count", ""),
                            "image_url": p.get("image_url", ""),
                            "product_url": p.get("product_url", ""),
                            "_category": "product",
                            "_extraction_method": "keepa_api",
                        })
                    step_ts = _record_step(steps, f"Keepa API: bestsellers '{category}' — {len(platform_products)} products", step_ts)

            else:
                # Generic Amazon URL — try as keyword search with domain
                keepa_result = await connector.query(url, domain=keepa_domain, max_results=20)
                if keepa_result and keepa_result.get("products"):
                    platform_products = [{
                        "name": p.get("name", ""), "price": p.get("price", ""),
                        "asin": p.get("asin", ""), "brand": p.get("brand", ""),
                        "rating": p.get("rating", ""), "review_count": p.get("reviews_count", ""),
                        "image_url": p.get("image_url", ""), "product_url": p.get("product_url", ""),
                        "_category": "product", "_extraction_method": "keepa_api",
                    } for p in keepa_result["products"]]
                    step_ts = _record_step(steps, f"Keepa API: {len(platform_products)} products", step_ts)

            if platform_products:
                logger.info("smart_scrape.keepa_routed", task_id=task_id, count=len(platform_products), domain=keepa_domain)
        except Exception as keepa_err:
            logger.warning("smart_scrape.keepa_failed", error=str(keepa_err)[:200])

    # Non-Amazon: try Shopify/WooCommerce APIs
    if not platform_products and not is_amazon:
        try:
            import httpx as _httpx
            api_base = f"{parsed_url.scheme}://{parsed_url.netloc}"

            # Shopify: /products.json
            async with _httpx.AsyncClient(timeout=10, follow_redirects=True) as _api_client:
                shopify_resp = await _api_client.get(f"{api_base}/products.json?limit=250")
            if shopify_resp.status_code == 200:
                data = shopify_resp.json()
                sp_list = data.get("products", [])
                if sp_list:
                    platform_products = []
                    for sp in sp_list:
                        v = sp.get("variants", [{}])[0] if sp.get("variants") else {}
                        platform_products.append({
                            "name": sp.get("title", ""),
                            "price": v.get("price", ""),
                            "product_url": f"{api_base}/products/{sp.get('handle', '')}",
                            "image_url": (sp.get("images", [{}])[0].get("src", "") if sp.get("images") else ""),
                            "vendor": sp.get("vendor", ""),
                            "product_type": sp.get("product_type", ""),
                            "_category": "product",
                            "_extraction_method": "shopify_api",
                        })
                    step_ts = _record_step(
                        steps, f"Shopify API: {len(platform_products)} products (skipping HTML extraction)", step_ts
                    )
                    logger.info("smart_scrape.shopify_api_direct", task_id=task_id, count=len(platform_products))

            # WooCommerce: /wp-json/wc/store/v1/products
            if not platform_products:
                woo_resp = await _api_client.get(f"{api_base}/wp-json/wc/store/v1/products?per_page=100")
                if woo_resp.status_code == 200:
                    woo_list = woo_resp.json()
                    if isinstance(woo_list, list) and woo_list:
                        platform_products = []
                        for wp in woo_list:
                            prices = wp.get("prices", {})
                            platform_products.append({
                                "name": wp.get("name", ""),
                                "price": prices.get("price", ""),
                                "product_url": wp.get("permalink", ""),
                                "image_url": (wp.get("images", [{}])[0].get("src", "") if wp.get("images") else ""),
                                "_category": "product",
                                "_extraction_method": "woocommerce_api",
                            })
                        step_ts = _record_step(
                            steps, f"WooCommerce API: {len(platform_products)} products", step_ts
                        )
        except Exception as api_err:
            logger.debug("smart_scrape.platform_api_skip", error=str(api_err)[:100])

    # If platform API returned products, skip lane execution entirely
    if platform_products and len(platform_products) >= 3:
        # Save directly to DB
        await task_repo_create_and_save(
            session, tenant_id, task_id, run_id, url, platform_products, steps, step_ts, request,
        )
        total_elapsed = int((time.time() - op_start) * 1000)
        return {
            "target": url,
            "detected_as": "url",
            "status": "completed",
            "item_count": len(platform_products),
            "confidence": 0.95,
            "lane_used": "api",
            "steps": steps,
            "escalation_chain": [],
            "extracted_data": platform_products[:100],
            "schema_matched": None,
            "saved": True,
            "saved_task_id": task_id,
            "duration_ms": total_elapsed,
        }

    # ---- Step 1: Route the task ----
    task_contract = Task(tenant_id=tenant_id, url=url)
    decision = _router.route(task_contract)
    current_lane = decision.lane
    current_decision = decision
    step_ts = _record_step(
        steps, f"Routed to {current_lane.value} lane (reason: {decision.reason})", step_ts
    )

    # ---- Step 2: Build task payload ----
    task_payload: dict[str, Any] = {
        "task_id": task_id,
        "tenant_id": tenant_id,
        "url": url,
        "timeout_ms": 25000,
        "scroll": True,
        "max_scrolls": 3,
    }

    # Inject cookies
    if cookies:
        if current_lane in (Lane.BROWSER, Lane.HARD_TARGET):
            # Browser workers accept full cookie list
            task_payload["cookies"] = cookies
        else:
            # HTTP workers use simple name:value dict
            task_payload["cookies"] = _cookies_to_simple_dict(cookies)
        _record_step(steps, f"Injected {len(cookies)} cookies into payload", step_ts)

    # ---- Step 3: Create DB records ----
    task_repo = TaskRepository(session)
    run_repo = RunRepository(session)
    result_repo = ResultRepository(session)

    await task_repo.create(
        tenant_id=tenant_id,
        id=task_id,
        url=url,
        task_type="scrape",
        status=TaskStatus.RUNNING.value,
        metadata_json={"source": "smart_scrape"},
    )
    await run_repo.create(
        tenant_id=tenant_id,
        id=run_id,
        task_id=task_id,
        lane=current_lane.value,
        connector=_LANE_CONNECTORS.get(current_lane, "http_collector"),
        status="running",
    )
    await session.flush()
    step_ts = _record_step(steps, "Created task and run DB records", step_ts)

    # ---- Step 4: Escalation loop ----
    escalation_chain: list[dict[str, Any]] = []
    worker_result: dict[str, Any] = {}

    for attempt in range(2):  # Max 2 attempts: HTTP → Browser (skip hard_target on Railway)
        # Check total timeout
        if (time.time() - op_start) > _MAX_TIMEOUT_S:
            logger.warning("smart_scrape.timeout", task_id=task_id, elapsed_s=time.time() - op_start)
            worker_result = {
                "task_id": task_id,
                "status": "failed",
                "error": f"Total timeout exceeded ({_MAX_TIMEOUT_S}s)",
                "extracted_data": [],
                "item_count": 0,
            }
            break

        # Update cookies format if lane changed
        if cookies and attempt > 0:
            if current_lane in (Lane.BROWSER, Lane.HARD_TARGET):
                task_payload["cookies"] = cookies
            else:
                task_payload["cookies"] = _cookies_to_simple_dict(cookies)

        worker_result = await _execute_lane(current_lane, task_payload)

        succeeded = worker_result.get("status") == "success"
        escalation_chain.append({
            "lane": current_lane.value,
            "status": worker_result.get("status"),
            "status_code": worker_result.get("status_code"),
            "item_count": worker_result.get("item_count", 0),
            "confidence": worker_result.get("confidence", 0),
        })
        step_ts = _record_step(
            steps,
            f"Executed {current_lane.value} lane: status={worker_result.get('status')}, items={worker_result.get('item_count', 0)}",
            step_ts,
        )

        # Check escalation — with smart overrides for JS-rendered sites
        needs_escalation = _escalation_mgr.should_escalate(worker_result)

        # Detect if URL is a detail page (not a listing) — don't over-escalate
        detail_signals = ["/product/", "/products/", "/item/", "/dp/", "/catalogue/", "/p/"]
        is_detail_page = any(s in url.lower() for s in detail_signals)

        # Smart override: if HTTP lane returned few items on a LISTING page,
        # check if site is JS-rendered by examining HTML size.
        if (
            not needs_escalation
            and not is_detail_page
            and current_lane == Lane.HTTP
            and succeeded
            and worker_result.get("item_count", 0) <= 10
        ):
            html_snapshot = worker_result.get("html_snapshot", "")
            html_size = len(html_snapshot.encode("utf-8", errors="replace")) if html_snapshot else 0
            bytes_downloaded = worker_result.get("bytes_downloaded", 0)
            effective_size = html_size or bytes_downloaded

            logger.info(
                "smart_scrape.size_check",
                task_id=task_id,
                html_snapshot_size=html_size,
                bytes_downloaded=bytes_downloaded,
                effective_size=effective_size,
                item_count=worker_result.get("item_count", 0),
            )

            # If HTML content is genuinely small (< 10KB), force escalation
            # But skip for sites that return large HTML (eBay = 1.6MB)
            if effective_size < 10_000 and effective_size > 0:
                needs_escalation = True
                logger.info(
                    "smart_scrape.js_detected",
                    task_id=task_id,
                    html_size=bytes_downloaded,
                    item_count=worker_result.get("item_count", 0),
                    reason="Small HTML + few items = likely JS-rendered site",
                )
                step_ts = _record_step(
                    steps,
                    f"JS-rendered site detected ({bytes_downloaded/1024:.1f}KB HTML, only {worker_result.get('item_count',0)} items) — escalating",
                    step_ts,
                )

        if not needs_escalation:
            break

        next_lane = _escalation_mgr.get_escalation(task_id, worker_result, current_decision)
        if next_lane is None:
            logger.info("smart_scrape.escalation_exhausted", task_id=task_id)
            break

        logger.info(
            "smart_scrape.escalating",
            task_id=task_id,
            from_lane=current_lane.value,
            to_lane=next_lane.value,
        )
        step_ts = _record_step(
            steps, f"Escalating: {current_lane.value} -> {next_lane.value}", step_ts
        )

        current_lane = next_lane
        current_decision = RouteDecision(
            lane=current_lane,
            reason="auto-escalation",
            fallback_lanes=_router._get_fallback_lanes(current_lane),
        )

    # Clean up escalation context
    _escalation_mgr.complete(task_id, worker_result)

    # ---- Step 5: Universal product extraction ----
    extracted_data: list[dict[str, Any]] = worker_result.get("extracted_data", [])
    html_snapshot: str = worker_result.get("html_snapshot", "") or worker_result.get("html", "")

    # Step 5a: Shopify API (if detected)
    if html_snapshot and ("shopify" in html_snapshot.lower() or "myshopify" in html_snapshot.lower()):
        try:
            import httpx as _httpx
            shopify_url = f"{url.rstrip('/')}/products.json?limit=250"
            async with _httpx.AsyncClient(timeout=15, follow_redirects=True) as _client:
                shopify_resp = await _client.get(shopify_url)
                if shopify_resp.status_code == 200:
                    shopify_products = shopify_resp.json().get("products", [])
                    if shopify_products:
                        shopify_items = []
                        for sp in shopify_products:
                            variant = sp.get("variants", [{}])[0] if sp.get("variants") else {}
                            shopify_items.append({
                                "name": sp.get("title", ""),
                                "price": variant.get("price", ""),
                                "product_url": f"{url.rstrip('/')}/products/{sp.get('handle', '')}",
                                "image_url": (sp.get("images", [{}])[0].get("src", "") if sp.get("images") else ""),
                                "vendor": sp.get("vendor", ""),
                                "product_type": sp.get("product_type", ""),
                                "_category": "product",
                                "_extraction_method": "shopify_api",
                            })
                        extracted_data = shopify_items
                        step_ts = _record_step(steps, f"Shopify API: {len(shopify_items)} products", step_ts)
        except Exception as shop_err:
            logger.debug("smart_scrape.shopify_api_failed", error=str(shop_err))

    # Step 5b: Generic DOM product extraction (if still few items)
    if html_snapshot and len(extracted_data) < 10:
        try:
            import re as _re
            from bs4 import BeautifulSoup as _BS
            _soup = _BS(html_snapshot, "html.parser")
            _seen: set[str] = set()
            _dom_products: list[dict[str, Any]] = []
            _price_re = _re.compile(r"[\$\u00a3\u20ac][\d,.]+|[\d,.]+\s*(?:Rs|PKR|USD|EUR|GBP)")

            # Find containers that have BOTH a price AND a name element
            for price_text_el in _soup.find_all(string=_price_re):
                parent = price_text_el.parent
                for _ in range(8):
                    if parent is None or parent.name in ("body", "html"):
                        break
                    links = parent.find_all("a", href=True)
                    has_link = any(l["href"] not in ("#", "", "javascript:void(0)") for l in links)
                    name_el = parent.find(["h2", "h3", "h4", "h5"]) or parent.find("img", alt=True)
                    if has_link and name_el:
                        # Extract name
                        _name = ""
                        for h in parent.find_all(["h2", "h3", "h4", "h5"]):
                            t = h.get_text(strip=True)
                            if t and len(t) > 3:
                                _name = t
                                break
                        if not _name:
                            _img = parent.find("img", alt=True)
                            if _img and len(_img["alt"].strip()) > 3:
                                _name = _img["alt"].strip()
                        if not _name:
                            for a in parent.find_all("a"):
                                t = a.get_text(strip=True)
                                if t and 5 < len(t) < 200:
                                    _name = t
                                    break
                        if not _name or len(_name) < 3:
                            parent = parent.parent
                            continue

                        # Extract price
                        _pm = _price_re.search(str(price_text_el))
                        _price = _pm.group() if _pm else ""

                        # Extract URL
                        _link = parent.find("a", href=True)
                        _href = _link["href"] if _link else ""
                        _full_url = _href if _href.startswith("http") else f"{url.rstrip('/')}{_href}" if _href else ""

                        _key = _name[:50]
                        if _key not in _seen:
                            _seen.add(_key)
                            _dom_products.append({
                                "name": _name, "price": _price, "product_url": _full_url,
                                "_category": "product", "_extraction_method": "dom_group",
                            })
                        break
                    parent = parent.parent

            if len(_dom_products) > len(extracted_data):
                extracted_data = _dom_products
                step_ts = _record_step(steps, f"DOM extraction: {len(_dom_products)} products found", step_ts)

        except Exception as dom_err:
            logger.debug("smart_scrape.dom_extract_failed", error=str(dom_err))

    # Step 5c: Enhanced full extraction if still few items
    if html_snapshot and len(extracted_data) < 10:
        try:
            from services.control_plane.routers.execution import _extract_everything
            from packages.core.ai_providers.deterministic import DeterministicProvider
            ai = DeterministicProvider()
            enhanced = await _extract_everything(html_snapshot, url, ai)
            if len(enhanced) > len(extracted_data):
                extracted_data = enhanced
                step_ts = _record_step(
                    steps,
                    f"Enhanced extraction: {len(enhanced)} items (was {worker_result.get('item_count', 0)})",
                    step_ts,
                )
                logger.info(
                    "smart_scrape.enhanced",
                    task_id=task_id,
                    original_items=worker_result.get("item_count", 0),
                    enhanced_items=len(enhanced),
                )
        except Exception as enh_err:
            logger.warning("smart_scrape.enhance_failed", error=str(enh_err))

    html_content: str = html_snapshot

    # ---- Step 5b: Filter by intent ----
    intent = request.intent
    if intent != "everything" and extracted_data:
        filtered: list[dict[str, Any]] = []
        for item in extracted_data:
            cat = item.get("_category", "")
            has_price = item.get("price") is not None
            has_url = bool(item.get("product_url") or item.get("url"))

            if intent == "products":
                # Keep items that look like products (have price, or category=product)
                if has_price or cat == "product" or item.get("currency"):
                    filtered.append(item)
            elif intent == "content":
                # Keep article/heading/testimonial content
                if cat in ("content", "heading", "testimonial", "stat", "metadata", "article"):
                    filtered.append(item)
                elif item.get("content_type") == "article" or item.get("full_content"):
                    filtered.append(item)
                elif item.get("heading_level"):
                    filtered.append(item)
            elif intent == "contacts":
                # Keep items with email, phone, or address patterns
                item_str = str(item).lower()
                if ("@" in item_str or "phone" in item_str or "email" in item_str
                    or "contact" in item_str or "address" in item_str
                    or "tel:" in item_str or "mailto:" in item_str):
                    filtered.append(item)
                # Also keep social links
                if any(s in str(item.get("url", "")).lower() for s in
                       ["linkedin", "twitter", "facebook", "instagram", "github"]):
                    filtered.append(item)
            elif intent == "links":
                # Keep items with URLs
                if has_url or cat in ("link", "cta"):
                    filtered.append(item)

        if filtered:
            step_ts = _record_step(
                steps,
                f"Filtered by intent '{intent}': {len(filtered)} items (from {len(extracted_data)})",
                step_ts,
            )
            extracted_data = filtered

    # ---- Step 6: Schema matching ----
    schema_matched: dict[str, Any] | None = None
    if schema_fields and extracted_data:
        try:
            from services.control_plane.routers.extract import (
                _match_to_schema,
                _extract_from_html,
            )
            matched_data, match_confidence = _match_to_schema(
                extracted_data, schema_fields, html=html_content, url=url
            )
            schema_matched = {
                "matched_fields": matched_data,
                "match_confidence": match_confidence,
            }
            step_ts = _record_step(
                steps,
                f"Schema matched {len(matched_data)} fields (confidence={match_confidence})",
                step_ts,
            )
        except Exception as exc:
            logger.warning("smart_scrape.schema_match_failed", error=str(exc))
            step_ts = _record_step(
                steps, f"Schema matching failed: {str(exc)[:200]}", step_ts
            )

    # ---- Step 7: Multi-page crawl ----
    if max_pages > 1:
        try:
            from packages.core.crawl_manager import CrawlManager, CrawlConfig

            crawl_config = CrawlConfig(
                seed_urls=[url],
                max_depth=max_depth,
                max_pages=max_pages,
                output_format=output_format,
            )
            crawl_mgr = CrawlManager()
            crawl_id = await crawl_mgr.start_crawl(crawl_config)

            # Wait for crawl to finish (with timeout)
            crawl_deadline = min(
                op_start + _MAX_TIMEOUT_S,
                time.time() + 60,  # cap crawl at 60s within the total timeout
            )
            while time.time() < crawl_deadline:
                job = await crawl_mgr.get_crawl(crawl_id)
                if job and job.state in ("completed", "failed", "stopped"):
                    break
                await asyncio.sleep(1.0)

            crawl_results = await crawl_mgr.get_results(crawl_id)
            if crawl_results:
                for cr in crawl_results:
                    if isinstance(cr, dict):
                        items = cr.get("extracted_data", [])
                        if isinstance(items, list):
                            extracted_data.extend(items)

            step_ts = _record_step(
                steps,
                f"Crawl completed: {len(crawl_results) if crawl_results else 0} additional pages",
                step_ts,
            )
            await crawl_mgr.stop_crawl(crawl_id)
        except Exception as exc:
            logger.warning("smart_scrape.crawl_failed", error=str(exc))
            step_ts = _record_step(
                steps, f"Crawl failed: {str(exc)[:200]}", step_ts
            )

    # ---- Step 8: Save results to DB ----
    final_status = "completed" if worker_result.get("status") == "success" else "failed"
    metadata: dict[str, Any] = {
        "escalation_chain": escalation_chain,
        "source": "smart_scrape",
    }
    if final_status == "failed":
        metadata["last_error"] = worker_result.get("error") or "unknown"

    try:
        await task_repo.update(task_id, tenant_id, status=final_status, metadata_json=metadata)
        await run_repo.update(
            run_id,
            tenant_id,
            status="completed" if final_status == "completed" else "failed",
            status_code=worker_result.get("status_code"),
            error=worker_result.get("error"),
            duration_ms=worker_result.get("duration_ms", 0),
        )
        if final_status == "completed" and extracted_data:
            await result_repo.create(
                tenant_id=tenant_id,
                task_id=task_id,
                run_id=run_id,
                url=url,
                extracted_data=extracted_data,
                item_count=len(extracted_data),
                confidence=worker_result.get("confidence", 0.0),
                extraction_method=worker_result.get("extraction_method", "deterministic"),
                normalization_applied=worker_result.get("normalization_applied", False),
                dedup_applied=worker_result.get("dedup_applied", False),
            )
        await session.flush()
        step_ts = _record_step(steps, "Saved results to database", step_ts)
        saved = True
    except Exception as exc:
        logger.error("smart_scrape.db_save_failed", error=str(exc))
        step_ts = _record_step(steps, f"DB save failed: {str(exc)[:200]}", step_ts)
        saved = False

    return {
        "status": final_status,
        "extracted_data": extracted_data,
        "item_count": len(extracted_data),
        "confidence": worker_result.get("confidence", 0),
        "lane_used": current_lane.value,
        "escalation_chain": escalation_chain,
        "schema_matched": schema_matched,
        "saved": saved,
        "saved_task_id": task_id,
    }


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@smart_scrape_router.post("/smart-scrape", status_code=200)
async def smart_scrape(
    request: SmartScrapeRequest,
    session: AsyncSession = Depends(get_session),
    tenant_id: str = Depends(get_tenant_id),
) -> SmartScrapeResponse:
    """Unified scrape endpoint: auto-detects URL vs search, routes, escalates, crawls."""
    op_start = time.time()
    steps: list[dict[str, Any]] = []
    target = request.target.strip()
    task_id = str(uuid4())

    logger.info(
        "smart_scrape.start",
        target=target[:100],
        max_pages=request.max_pages,
        has_cookies=request.cookies is not None,
        has_schema=request.schema_fields is not None,
    )

    try:
        detected_as = "url" if _is_url(target) else "search"
        _record_step(steps, f"Detected target as: {detected_as}", op_start)

        if detected_as == "search":
            # --- Search path ---
            result = await _handle_search(
                query=target,
                max_results=min(request.max_pages, 10),
                steps=steps,
                op_start=op_start,
            )
            lane_used = result.get("lane_used", "search")
            extracted_data = result.get("extracted_data", [])

            # Apply schema matching on search results if requested
            schema_matched = None
            if request.schema_fields and extracted_data:
                try:
                    from services.control_plane.routers.extract import _match_to_schema
                    matched_data, match_confidence = _match_to_schema(
                        extracted_data, request.schema_fields
                    )
                    schema_matched = {
                        "matched_fields": matched_data,
                        "match_confidence": match_confidence,
                    }
                except Exception:
                    pass

            total_elapsed = int((time.time() - op_start) * 1000)
            return SmartScrapeResponse(
                target=target,
                detected_as=detected_as,
                status=result.get("status", "success"),
                item_count=result.get("item_count", 0),
                confidence=result.get("confidence", 0),
                lane_used=lane_used,
                steps=[SmartScrapeStep(**s) for s in steps],
                escalation_chain=[],
                extracted_data=extracted_data[:100],
                schema_matched=schema_matched,
                saved=False,
                saved_task_id=task_id,
                duration_ms=total_elapsed,
            )

        else:
            # --- URL scrape path ---
            # Ensure the target has a scheme
            url = target if target.startswith(("http://", "https://")) else f"https://{target}"

            result = await _handle_url_scrape(
                url=url,
                tenant_id=tenant_id,
                cookies=request.cookies,
                schema_fields=request.schema_fields,
                max_pages=request.max_pages,
                max_depth=request.max_depth,
                output_format=request.output_format,
                steps=steps,
                op_start=op_start,
                session=session,
                request=request,
            )

            total_elapsed = int((time.time() - op_start) * 1000)
            return SmartScrapeResponse(
                target=target,
                detected_as=detected_as,
                status=result.get("status", "failed"),
                item_count=result.get("item_count", 0),
                confidence=result.get("confidence", 0),
                lane_used=result.get("lane_used", "http"),
                steps=[SmartScrapeStep(**s) for s in steps],
                escalation_chain=result.get("escalation_chain", []),
                extracted_data=result.get("extracted_data", [])[:100],
                schema_matched=result.get("schema_matched"),
                saved=result.get("saved", False),
                saved_task_id=result.get("saved_task_id", task_id),
                duration_ms=total_elapsed,
            )

    except Exception:
        error_tb = traceback.format_exc()
        logger.error("smart_scrape.unhandled_error", error=error_tb)
        short_error = error_tb.strip().split("\n")[-1][:500]

        total_elapsed = int((time.time() - op_start) * 1000)
        _record_step(steps, f"Fatal error: {short_error}", time.time())

        return SmartScrapeResponse(
            target=target,
            detected_as="url" if _is_url(target) else "search",
            status="failed",
            item_count=0,
            confidence=0,
            lane_used="none",
            steps=[SmartScrapeStep(**s) for s in steps],
            escalation_chain=[],
            extracted_data=[],
            schema_matched=None,
            saved=False,
            saved_task_id=task_id,
            duration_ms=total_elapsed,
        )
