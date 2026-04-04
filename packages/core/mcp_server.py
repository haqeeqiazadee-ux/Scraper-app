"""
MCP Server -- Model Context Protocol server for AI agent integration.

Exposes the scraping platform as MCP tools that AI agents (Claude, Cursor,
VS Code Copilot) can use to scrape, crawl, search, and extract data.

Usage:
    python -m packages.core.mcp_server
    # Or via MCP config:
    # { "command": "python", "args": ["-m", "packages.core.mcp_server"] }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import traceback
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# API key authentication -- read from MCP config / environment
# ---------------------------------------------------------------------------
API_KEY = os.environ.get("SCRAPER_API_KEY", "")


def _check_auth() -> str | None:
    """Return an error message if API key is required but missing/invalid."""
    required_key = os.environ.get("SCRAPER_API_KEY_REQUIRED", "")
    if required_key and API_KEY != required_key:
        return "Authentication failed: invalid or missing SCRAPER_API_KEY"
    return None


# ---------------------------------------------------------------------------
# Server instance
# ---------------------------------------------------------------------------
server = Server("scraper-platform")


# ---------------------------------------------------------------------------
# Tool definitions
# ---------------------------------------------------------------------------
@server.list_tools()
async def list_tools() -> list[Tool]:
    """Expose all scraping tools to MCP clients."""
    return [
        Tool(
            name="scrape",
            description=(
                "Extract structured data from a single URL. Returns product data, "
                "article content, or page metadata depending on the page type."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "markdown", "html", "raw"],
                        "default": "json",
                        "description": "Output format for extracted data",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="crawl",
            description=(
                "Recursively crawl a website starting from a seed URL, following "
                "links up to max_depth. Returns extracted data from all pages."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Seed URL to start crawling from",
                    },
                    "max_depth": {
                        "type": "integer",
                        "default": 2,
                        "description": "Maximum link-follow depth (0 = seed only)",
                    },
                    "max_pages": {
                        "type": "integer",
                        "default": 10,
                        "description": "Maximum number of pages to crawl",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "default": "json",
                        "description": "Output format for extracted data",
                    },
                },
                "required": ["url"],
            },
        ),
        Tool(
            name="search",
            description=(
                "Search the web for a query and scrape the top results. Returns "
                "structured data extracted from each search-result page."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query string",
                    },
                    "max_results": {
                        "type": "integer",
                        "default": 5,
                        "description": "Maximum number of search results to scrape",
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "default": "json",
                        "description": "Output format for extracted data",
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="extract",
            description=(
                "Extract specific structured data from a URL using a JSON schema. "
                "Provide a schema describing the fields you want and their types."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to extract data from",
                    },
                    "schema": {
                        "type": "object",
                        "description": (
                            "JSON Schema describing the data to extract. "
                            'Example: {"type": "object", "properties": {"title": {"type": "string"}, "price": {"type": "number"}}}'
                        ),
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["json", "markdown"],
                        "default": "json",
                        "description": "Output format for extracted data",
                    },
                },
                "required": ["url", "schema"],
            },
        ),
        Tool(
            name="route",
            description=(
                "Dry-run: determine which execution lane would handle a given URL "
                "(http, browser, hard_target, or api). Does not fetch the page."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The URL to classify",
                    },
                },
                "required": ["url"],
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Dispatch an incoming tool call to the appropriate handler."""
    # Auth check
    auth_error = _check_auth()
    if auth_error:
        return [TextContent(type="text", text=json.dumps({"error": auth_error}))]

    handlers = {
        "scrape": _handle_scrape,
        "crawl": _handle_crawl,
        "search": _handle_search,
        "extract": _handle_extract,
        "route": _handle_route,
    }

    handler = handlers.get(name)
    if handler is None:
        return [TextContent(
            type="text",
            text=json.dumps({"error": f"Unknown tool: {name}"}),
        )]

    try:
        return await handler(arguments)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"{type(exc).__name__}: {exc}",
                "traceback": traceback.format_exc(),
            }),
        )]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _json_response(data: Any) -> list[TextContent]:
    """Wrap a Python object as a JSON TextContent response."""
    return [TextContent(type="text", text=json.dumps(data, indent=2, default=str))]


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------

async def _handle_scrape(args: dict) -> list[TextContent]:
    """Scrape a single URL using the HTTP worker."""
    from services.worker_http.worker import HttpWorker  # type: ignore[import-untyped]

    url: str = args["url"]
    output_format: str = args.get("output_format", "json")

    worker = HttpWorker()
    try:
        result = await worker.process_task({
            "url": url,
            "output_format": output_format,
            "tenant_id": "mcp",
        })
    finally:
        await worker.close()

    # Return a clean subset -- omit internal fields like html_snapshot
    return _json_response({
        "url": result.get("url", url),
        "status": result.get("status"),
        "status_code": result.get("status_code"),
        "item_count": result.get("item_count", 0),
        "confidence": result.get("confidence"),
        "extracted_data": result.get("extracted_data", []),
        "converted_content": result.get("converted_content"),
        "output_format": output_format,
        "duration_ms": result.get("duration_ms"),
        "error": result.get("error"),
    })


async def _handle_crawl(args: dict) -> list[TextContent]:
    """Recursively crawl a website using the CrawlManager."""
    from packages.core.crawl_manager import CrawlConfig, CrawlManager, CrawlState

    url: str = args["url"]
    max_depth: int = args.get("max_depth", 2)
    max_pages: int = args.get("max_pages", 10)
    output_format: str = args.get("output_format", "json")

    manager = CrawlManager()
    config = CrawlConfig(
        seed_urls=[url],
        max_depth=max_depth,
        max_pages=max_pages,
        output_format=output_format,
    )

    crawl_id = await manager.start_crawl(config)

    # Wait for crawl to finish (poll with timeout)
    timeout = max_pages * 30  # generous: 30s per page
    elapsed = 0.0
    poll_interval = 0.5
    while elapsed < timeout:
        job = await manager.get_crawl(crawl_id)
        if job is None:
            break
        if job.state in (CrawlState.COMPLETED, CrawlState.FAILED, CrawlState.STOPPED):
            break
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

    job = await manager.get_crawl(crawl_id)
    if job is None:
        return _json_response({"error": "Crawl job not found"})

    return _json_response({
        "crawl_id": crawl_id,
        "state": str(job.state),
        "pages_crawled": job.stats.pages_crawled,
        "pages_failed": job.stats.pages_failed,
        "items_extracted": job.stats.items_extracted,
        "elapsed_seconds": round(job.stats.elapsed_seconds, 2),
        "results": job.results,
        "errors": job.errors[:20],  # cap error list
    })


async def _handle_search(args: dict) -> list[TextContent]:
    """Search the web for a query and scrape top results.

    Uses a lightweight approach: fetch a search engine results page,
    extract result URLs, then scrape each with the HTTP worker.
    """
    from services.worker_http.worker import HttpWorker  # type: ignore[import-untyped]

    query: str = args["query"]
    max_results: int = args.get("max_results", 5)
    output_format: str = args.get("output_format", "json")

    # Step 1: Get search result URLs via a search engine scrape
    search_urls = await _fetch_search_results(query, max_results)

    if not search_urls:
        return _json_response({
            "query": query,
            "results": [],
            "error": "No search results found or search engine blocked the request",
        })

    # Step 2: Scrape each result URL
    results: list[dict] = []
    worker = HttpWorker()
    try:
        for result_url in search_urls[:max_results]:
            try:
                result = await worker.process_task({
                    "url": result_url,
                    "output_format": output_format,
                    "tenant_id": "mcp",
                })
                results.append({
                    "url": result.get("url", result_url),
                    "status": result.get("status"),
                    "item_count": result.get("item_count", 0),
                    "extracted_data": result.get("extracted_data", []),
                    "converted_content": result.get("converted_content"),
                    "error": result.get("error"),
                })
            except Exception as exc:
                results.append({
                    "url": result_url,
                    "status": "failed",
                    "error": str(exc),
                })
    finally:
        await worker.close()

    return _json_response({
        "query": query,
        "result_count": len(results),
        "results": results,
    })


async def _fetch_search_results(query: str, max_results: int) -> list[str]:
    """Fetch search result URLs for a query.

    Uses DuckDuckGo HTML (no API key required) as the search backend.
    Falls back to an empty list on failure.
    """
    import re
    from urllib.parse import quote_plus, unquote

    search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        # Use the same HTTP stack the platform relies on
        try:
            from curl_cffi.requests import AsyncSession

            async with AsyncSession() as session:
                resp = await session.get(
                    search_url,
                    timeout=15,
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ScraperBot/1.0)"},
                )
                html = resp.text
        except ImportError:
            import httpx

            async with httpx.AsyncClient(follow_redirects=True, timeout=15.0) as client:
                resp = await client.get(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0 (compatible; ScraperBot/1.0)"},
                )
                html = resp.text

        if not html:
            return []

        # DuckDuckGo HTML wraps result links in //duckduckgo.com/l/?uddg=<encoded_url>
        urls: list[str] = []
        pattern = re.compile(r'uddg=([^&"]+)')
        for match in pattern.finditer(html):
            decoded = unquote(match.group(1))
            if decoded.startswith("http") and "duckduckgo.com" not in decoded:
                urls.append(decoded)
            if len(urls) >= max_results:
                break

        return urls

    except Exception:
        logger.exception("Search fetch failed for query: %s", query)
        return []


async def _handle_extract(args: dict) -> list[TextContent]:
    """Extract structured data from a URL using a caller-provided JSON schema.

    Fetches the page, then maps extracted fields to the requested schema.
    """
    from services.worker_http.worker import HttpWorker  # type: ignore[import-untyped]

    url: str = args["url"]
    schema: dict = args["schema"]
    output_format: str = args.get("output_format", "json")

    worker = HttpWorker()
    try:
        result = await worker.process_task({
            "url": url,
            "output_format": output_format,
            "tenant_id": "mcp",
        })
    finally:
        await worker.close()

    # If extraction failed, return the error
    if result.get("status") != "success":
        return _json_response({
            "url": url,
            "status": "failed",
            "error": result.get("error", "Extraction failed"),
        })

    # Map extracted data to the requested schema fields
    extracted = result.get("extracted_data", [])
    schema_props = schema.get("properties", {})
    requested_fields = set(schema_props.keys())

    mapped_items: list[dict] = []
    for item in extracted:
        mapped: dict[str, Any] = {}
        for field_name in requested_fields:
            # Direct match
            if field_name in item:
                mapped[field_name] = item[field_name]
            else:
                # Try common aliases (e.g., "title" -> "name", "cost" -> "price")
                aliases = _field_aliases(field_name)
                for alias in aliases:
                    if alias in item:
                        mapped[field_name] = item[alias]
                        break
        if mapped:
            mapped_items.append(mapped)

    return _json_response({
        "url": url,
        "status": "success",
        "schema": schema,
        "item_count": len(mapped_items),
        "data": mapped_items,
        "raw_item_count": len(extracted),
    })


def _field_aliases(field_name: str) -> list[str]:
    """Return common aliases for a requested field name."""
    alias_map: dict[str, list[str]] = {
        "title": ["name", "product_name", "heading"],
        "name": ["title", "product_name", "heading"],
        "cost": ["price", "sale_price", "original_price"],
        "price": ["cost", "sale_price", "original_price"],
        "image": ["image_url", "img", "thumbnail", "photo"],
        "image_url": ["image", "img", "thumbnail", "photo"],
        "link": ["url", "product_url", "href"],
        "url": ["link", "product_url", "href"],
        "description": ["summary", "content", "text", "meta_description"],
        "rating": ["score", "stars", "review_score"],
        "brand": ["manufacturer", "vendor", "maker"],
        "category": ["type", "product_type", "department"],
        "sku": ["product_id", "item_number", "model", "asin"],
    }
    return alias_map.get(field_name.lower(), [])


async def _handle_route(args: dict) -> list[TextContent]:
    """Dry-run routing decision: which lane would handle this URL?"""
    from packages.contracts.task import Task
    from packages.core.router import ExecutionRouter

    url: str = args["url"]

    # Build a minimal Task for the router
    task = Task(
        tenant_id="mcp",
        url=url,  # type: ignore[arg-type]
    )

    router = ExecutionRouter()
    decision = router.route(task)

    return _json_response({
        "url": url,
        "lane": str(decision.lane),
        "reason": decision.reason,
        "fallback_lanes": [str(l) for l in decision.fallback_lanes],
        "confidence": decision.confidence,
        "estimated_cost_per_page": decision.estimated_cost,
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    """Run the MCP server over stdio transport."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    logger.info("Starting MCP server: scraper-platform")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())
