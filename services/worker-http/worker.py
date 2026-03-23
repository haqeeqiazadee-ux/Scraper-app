"""
HTTP Lane Worker — processes HTTP extraction tasks from the queue.

Pipeline: dequeue task → HTTP fetch → extract data → normalize → store result
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from packages.connectors.http_collector import HttpCollector
from packages.core.ai_providers.deterministic import DeterministicProvider
from packages.core.interfaces import FetchRequest, AIProvider

logger = logging.getLogger(__name__)

# CSS selectors for "next page" links (B3 pagination)
NEXT_PAGE_SELECTORS = [
    'a[rel="next"]',
    ".next a",
    ".pagination .next a",
    'a:contains("next")',  # BeautifulSoup only — no-op with CSS select, handled separately
]


def _find_next_page_url(html: str, current_url: str) -> Optional[str]:
    """Find the next page URL from pagination links in HTML."""
    try:
        from bs4 import BeautifulSoup
        from urllib.parse import urljoin
    except ImportError:
        return None

    soup = BeautifulSoup(html, "html.parser")

    # Try each selector in order
    for selector in ['a[rel="next"]', ".next a", ".pagination .next a"]:
        el = soup.select_one(selector)
        if el and el.get("href"):
            href = el["href"]
            return urljoin(current_url, href) if not href.startswith(("http://", "https://")) else href

    # Fallback: find any <a> whose visible text is "next" (case-insensitive)
    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True).lower()
        if text in ("next", "next page", "»", "›"):
            href = a["href"]
            return urljoin(current_url, href) if not href.startswith(("http://", "https://")) else href

    return None


class HttpWorker:
    """Worker that processes HTTP lane tasks."""

    def __init__(
        self,
        ai_provider: Optional[AIProvider] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self._collector = HttpCollector(proxy=proxy)
        self._ai = ai_provider or DeterministicProvider()

    async def _fetch_with_retry_after(self, request: FetchRequest, max_retries: int = 3) -> object:
        """Fetch a URL, honouring Retry-After headers on 429 responses (B4)."""
        for attempt in range(max_retries + 1):
            response = await self._collector.fetch(request)
            if response.status_code == 429 and attempt < max_retries:
                retry_after_raw = response.headers.get("retry-after") or response.headers.get("Retry-After", "")
                wait_seconds = 0.0
                if retry_after_raw:
                    try:
                        wait_seconds = float(retry_after_raw)
                    except ValueError:
                        # Could be an HTTP-date; default to 5 s
                        wait_seconds = 5.0
                wait_seconds = min(wait_seconds or 5.0, 60.0)  # cap at 60 s
                logger.info(
                    "429 received — waiting Retry-After before retry",
                    extra={"url": request.url, "wait_seconds": wait_seconds, "attempt": attempt + 1},
                )
                await asyncio.sleep(wait_seconds)
                continue
            return response
        return response  # type: ignore[return-value]  # last attempt result

    async def process_task(self, task: dict) -> dict:
        """
        Process a single HTTP extraction task.

        Args:
            task: Dict with at least 'url' and 'tenant_id' keys.
                  Optional keys:
                    - paginate (bool): follow next-page links (B3)
                    - max_pages (int): max pages to follow when paginate=True (B3)
                    - css_selectors (dict): custom field->selector map (B2)

        Returns:
            Dict with extraction results, run metadata, and status.
        """
        url = task["url"]
        tenant_id = task.get("tenant_id", "default")
        task_id = task.get("task_id", str(uuid4()))
        run_id = str(uuid4())
        css_selectors = task.get("css_selectors")  # B2

        logger.info("Processing HTTP task", extra={"task_id": task_id, "url": url})
        start_time = time.time()

        # Step 1: Fetch the page (with Retry-After support — B4)
        request = FetchRequest(
            url=url,
            timeout_ms=task.get("timeout_ms", 30000),
        )

        response = await self._fetch_with_retry_after(request)

        if not response.ok:
            elapsed = int((time.time() - start_time) * 1000)
            logger.warning("HTTP fetch failed", extra={
                "task_id": task_id, "url": url,
                "status_code": response.status_code, "error": response.error,
            })
            # Escalate on server errors (5xx) and anti-bot blocks (403),
            # but NOT on client errors like 404 (page doesn't exist)
            should_escalate = response.status_code in (403, 429) or response.status_code >= 500 or response.status_code == 0
            return {
                "task_id": task_id,
                "run_id": run_id,
                "tenant_id": tenant_id,
                "lane": "http",
                "connector": "http_collector",
                "status": "failed",
                "status_code": response.status_code,
                "error": response.error or f"HTTP {response.status_code}",
                "duration_ms": elapsed,
                "extracted_data": [],
                "item_count": 0,
                "should_escalate": should_escalate,
            }

        # Step 2: Extract data from HTML
        html = response.html or response.text
        total_bytes = len(response.body)

        # Pass custom CSS selectors to the AI provider if supported (B2)
        extract_kwargs: dict = {}
        if css_selectors and isinstance(self._ai, DeterministicProvider):
            extract_kwargs["css_selectors"] = css_selectors

        extracted_data = await self._ai.extract(html, url, **extract_kwargs)

        # B5: Store raw HTML snapshot as artifact metadata
        artifacts = []
        html_snapshot = html  # keep reference for result dict
        artifact_key = f"snapshots/{tenant_id}/{task_id}/{run_id}/page_1.html"
        artifacts.append({
            "key": artifact_key,
            "content_type": "text/html",
            "size_bytes": len(html.encode("utf-8", errors="replace")),
            "page": 1,
            "url": url,
            "captured_at": datetime.now(timezone.utc).isoformat(),
        })

        # B3: Pagination — follow next-page links when requested
        paginate = task.get("paginate", False)
        max_pages = task.get("max_pages", 1)

        # Auto-detect pagination when not explicitly set (UC-6.4.1-2)
        if "paginate" not in task:
            auto_next = _find_next_page_url(html, url)
            if auto_next:
                paginate = True
                max_pages = task.get("max_pages", 10)  # default to 10 pages
                logger.info("Pagination auto-detected", extra={"task_id": task_id, "next_url": auto_next})

        if paginate and max_pages > 1:
            current_url = url
            current_html = html
            page_num = 1

            while page_num < max_pages:
                next_url = _find_next_page_url(current_html, current_url)
                if not next_url or next_url == current_url:
                    break

                logger.info(
                    "Pagination: fetching next page",
                    extra={"task_id": task_id, "page": page_num + 1, "url": next_url},
                )
                next_request = FetchRequest(
                    url=next_url,
                    timeout_ms=task.get("timeout_ms", 30000),
                )
                next_response = await self._fetch_with_retry_after(next_request)
                if not next_response.ok:
                    logger.warning(
                        "Pagination: next page fetch failed",
                        extra={"task_id": task_id, "page": page_num + 1, "url": next_url},
                    )
                    break

                next_html = next_response.html or next_response.text
                total_bytes += len(next_response.body)
                page_num += 1

                next_page_data = await self._ai.extract(next_html, next_url, **extract_kwargs)
                extracted_data.extend(next_page_data)

                # B5: artifact for each additional page
                page_artifact_key = f"snapshots/{tenant_id}/{task_id}/{run_id}/page_{page_num}.html"
                artifacts.append({
                    "key": page_artifact_key,
                    "content_type": "text/html",
                    "size_bytes": len(next_html.encode("utf-8", errors="replace")),
                    "page": page_num,
                    "url": next_url,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                })

                current_url = next_url
                current_html = next_html

        # Step 3: Calculate confidence
        confidence = 0.0
        if extracted_data:
            # Score based on how many fields were extracted
            total_fields = 0
            filled_fields = 0
            for item in extracted_data:
                for key, value in item.items():
                    total_fields += 1
                    if value and str(value).strip():
                        filled_fields += 1
            confidence = filled_fields / total_fields if total_fields > 0 else 0.0

        elapsed = int((time.time() - start_time) * 1000)
        extraction_method = "deterministic" if isinstance(self._ai, DeterministicProvider) else "ai"

        logger.info("HTTP task completed", extra={
            "task_id": task_id, "url": url,
            "items": len(extracted_data), "confidence": f"{confidence:.2f}",
            "duration_ms": elapsed,
        })

        return {
            "task_id": task_id,
            "run_id": run_id,
            "tenant_id": tenant_id,
            "url": url,
            "lane": "http",
            "connector": "http_collector",
            "status": "success",
            "status_code": response.status_code,
            "duration_ms": elapsed,
            "bytes_downloaded": total_bytes,
            "extracted_data": extracted_data,
            "item_count": len(extracted_data),
            "confidence": round(confidence, 4),
            "extraction_method": extraction_method,
            "should_escalate": len(extracted_data) == 0,
            # B5: artifact storage metadata
            "html_snapshot": html_snapshot,
            "artifacts": artifacts,
        }

    async def close(self) -> None:
        """Clean up resources."""
        await self._collector.close()
