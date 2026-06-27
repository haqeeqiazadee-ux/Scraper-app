"""Search-provider fallbacks for marketplace URLs that block direct scraping."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

import httpx

from packages.core.secrets import get_env_secret

SERPER_SEARCH_URL = "https://google.serper.dev/search"


async def serper_site_search(
    *,
    site: str,
    query: str,
    max_results: int = 10,
    api_key: str | None = None,
    extra_terms: str = "",
) -> list[dict[str, Any]]:
    """Return organic search hits for a marketplace site."""
    key = api_key or get_env_secret("SERPER_API_KEY", "")
    if not key:
        return []

    q = f"site:{site} {query}".strip()
    if extra_terms:
        q = f"{q} {extra_terms.strip()}"

    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.post(
            SERPER_SEARCH_URL,
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": q, "num": min(max_results, 10)},
        )
    if response.status_code != 200:
        return []

    data = response.json()
    return [
        {
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "position": item.get("position"),
        }
        for item in data.get("organic", [])
        if item.get("link")
    ][:max_results]


def marketplace_items_from_hits(
    hits: list[dict[str, Any]],
    *,
    platform: str,
    query: str,
    method: str,
) -> list[dict[str, Any]]:
    """Normalize search hits as source-backed marketplace listing candidates."""
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for hit in hits:
        url = str(hit.get("url") or "")
        title = str(hit.get("title") or "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        items.append({
            "name": title or f"{platform.title()} listing for {query}",
            "description": hit.get("snippet", ""),
            "product_url": url,
            "url": url,
            "platform": platform,
            "source": "serper_site_search",
            "query": query,
            "_category": "product",
            "_extraction_method": method,
        })
    return items


async def amazon_search_fallback(query: str, max_results: int = 10) -> list[dict[str, Any]]:
    hits = await serper_site_search(
        site="amazon.com/dp",
        query=query,
        max_results=max_results,
        extra_terms="Amazon product",
    )
    return marketplace_items_from_hits(
        hits,
        platform="amazon",
        query=query,
        method="serper_amazon_product_search",
    )


async def ebay_search_fallback(
    query: str,
    max_results: int = 10,
    *,
    completed: bool = False,
) -> list[dict[str, Any]]:
    extra = "eBay sold completed listings" if completed else "eBay listing"
    hits = await serper_site_search(
        site="ebay.com/itm",
        query=query,
        max_results=max_results,
        extra_terms=extra,
    )
    return marketplace_items_from_hits(
        hits,
        platform="ebay",
        query=query,
        method="serper_ebay_listing_search",
    )


def amazon_search_url(query: str, domain: str = "US") -> str:
    host_by_domain = {
        "US": "www.amazon.com",
        "GB": "www.amazon.co.uk",
        "DE": "www.amazon.de",
        "FR": "www.amazon.fr",
        "IT": "www.amazon.it",
        "ES": "www.amazon.es",
        "CA": "www.amazon.ca",
        "JP": "www.amazon.co.jp",
        "IN": "www.amazon.in",
        "MX": "www.amazon.com.mx",
        "BR": "www.amazon.com.br",
    }
    host = host_by_domain.get(domain.upper(), "www.amazon.com")
    return f"https://{host}/s?k={quote_plus(query)}"
