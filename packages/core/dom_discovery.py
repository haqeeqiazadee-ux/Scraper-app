"""
DOM auto-discovery — find repeating groups on any page without selectors.

Uses tag-path fingerprinting and sibling subtree comparison to identify
repeating data records (product cards, search results, list items, etc.)
without any site-specific configuration.

This is the "Layer 1" extraction strategy: deterministic, zero-cost,
works on any site that uses template-generated repeating structures.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Minimum number of similar siblings to consider a repeating group
MIN_REPEATING_COUNT = 2

# Tags that are never data containers
SKIP_TAGS = frozenset({
    "script", "style", "noscript", "link", "meta", "head",
    "nav", "footer", "header", "iframe", "svg", "path",
})

# Tags commonly used as repeating-group containers
CONTAINER_TAGS = frozenset({
    "ul", "ol", "div", "section", "main", "tbody",
})

# Price regex for field extraction
PRICE_PATTERN = re.compile(
    r"[\$\£\€\₹]?\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)"
)


def _tag_signature(element) -> str:
    """Create a structural signature for a DOM element.

    The signature captures: tag name, child tag sequence, and attribute names.
    Two elements with the same signature are structurally identical.
    """
    try:
        children = [
            c.name for c in element.children
            if hasattr(c, "name") and c.name is not None
        ]
        attr_names = sorted(element.attrs.keys()) if element.attrs else []
        return f"{element.name}|{'_'.join(children)}|{'_'.join(attr_names)}"
    except Exception:
        return ""


def _structural_similarity(sig_a: str, sig_b: str) -> float:
    """Compare two tag signatures. Returns 0.0–1.0."""
    if not sig_a or not sig_b:
        return 0.0
    if sig_a == sig_b:
        return 1.0

    parts_a = sig_a.split("|")
    parts_b = sig_b.split("|")

    # Same tag name is required
    if parts_a[0] != parts_b[0]:
        return 0.0

    score = 0.3  # same tag name

    # Compare child tag sequences
    if len(parts_a) > 1 and len(parts_b) > 1:
        children_a = set(parts_a[1].split("_")) if parts_a[1] else set()
        children_b = set(parts_b[1].split("_")) if parts_b[1] else set()
        if children_a and children_b:
            intersection = children_a & children_b
            union = children_a | children_b
            score += 0.4 * (len(intersection) / len(union))
        elif not children_a and not children_b:
            score += 0.4

    # Compare attribute names
    if len(parts_a) > 2 and len(parts_b) > 2:
        attrs_a = set(parts_a[2].split("_")) if parts_a[2] else set()
        attrs_b = set(parts_b[2].split("_")) if parts_b[2] else set()
        if attrs_a and attrs_b:
            intersection = attrs_a & attrs_b
            union = attrs_a | attrs_b
            score += 0.3 * (len(intersection) / len(union))
        elif not attrs_a and not attrs_b:
            score += 0.3

    return score


def find_repeating_groups(html: str) -> list[list]:
    """Find groups of structurally similar sibling elements in the DOM.

    Returns a list of groups, where each group is a list of BeautifulSoup
    elements that form a repeating pattern (e.g., product cards).
    Groups are sorted by size (largest first).
    """
    try:
        from bs4 import BeautifulSoup, Tag
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    found_groups: list[list] = []

    # Find all container elements that could hold repeating children
    for container in soup.find_all(CONTAINER_TAGS):
        # Get direct child elements (not text nodes)
        children = [
            c for c in container.children
            if isinstance(c, Tag) and c.name not in SKIP_TAGS
        ]

        if len(children) < MIN_REPEATING_COUNT:
            continue

        # Compute signature for each child
        sigs = [(child, _tag_signature(child)) for child in children]
        sigs = [(child, sig) for child, sig in sigs if sig]

        if len(sigs) < MIN_REPEATING_COUNT:
            continue

        # Group children by similar signatures
        groups: dict[str, list] = {}
        for child, sig in sigs:
            placed = False
            for existing_sig in list(groups.keys()):
                if _structural_similarity(sig, existing_sig) >= 0.7:
                    groups[existing_sig].append(child)
                    placed = True
                    break
            if not placed:
                groups[sig] = [child]

        # Keep groups with enough members
        for sig, group in groups.items():
            if len(group) >= MIN_REPEATING_COUNT:
                # Avoid duplicates — check that this group's elements
                # aren't already in a found group
                first_el_id = id(group[0])
                already_found = any(
                    id(g[0]) == first_el_id for g in found_groups
                )
                if not already_found:
                    found_groups.append(group)

    # Sort by group size (most items first)
    found_groups.sort(key=len, reverse=True)
    return found_groups


def extract_fields_from_card(element, url: str = "") -> dict:
    """Extract common product/item fields from a single card element.

    Uses heuristics: headings → name, price patterns → price,
    img tags → image_url, links → product_url.
    """
    result: dict = {}

    try:
        # --- Name: first heading or first link text ---
        name_el = element.select_one(
            "h1, h2, h3, h4, h5, h6, a[title], a"
        )
        if name_el:
            name = (
                name_el.get("title")
                or name_el.get_text(strip=True)
            )
            if name and len(name) > 1:
                result["name"] = name

            # Product URL from the link — check the element itself or a
            # child <a> (headings often wrap a link)
            link_el = name_el if name_el.get("href") else name_el.select_one("a[href]")
            if link_el:
                href = link_el.get("href", "")
                if href and href != "#":
                    if url and not href.startswith(("http://", "https://")):
                        href = urljoin(url, href)
                    if href.startswith(("http://", "https://")):
                        result["product_url"] = href

        # --- Price: find text matching price pattern ---
        card_text = element.get_text(" ", strip=True)
        price_match = PRICE_PATTERN.search(card_text)
        if price_match:
            result["price"] = price_match.group(1).replace(",", "")

        # --- Image ---
        img_el = element.select_one("img")
        if img_el:
            src = img_el.get("src") or img_el.get("data-src", "")
            if src:
                if url and not src.startswith(("http://", "https://")):
                    src = urljoin(url, src)
                if src.startswith(("http://", "https://", "data:")):
                    result["image_url"] = src

        # --- Rating ---
        rating_el = element.select_one("[class*='star-rating'], [class*='rating'], [itemprop='ratingValue']")
        if rating_el:
            rating_text = rating_el.get("content") or rating_el.get_text(strip=True)
            if rating_text:
                # Try to extract numeric rating
                rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
                if rating_match:
                    result["rating"] = rating_match.group(1)
                else:
                    # Handle word-based ratings (e.g., "Three" CSS class)
                    rating_map = {"one": "1", "two": "2", "three": "3", "four": "4", "five": "5"}
                    for cls in rating_el.get("class", []):
                        if cls.lower() in rating_map:
                            result["rating"] = rating_map[cls.lower()]
                            break

        if not result.get("product_url") and url:
            result["product_url"] = url

    except Exception as exc:
        logger.debug("Field extraction failed for card: %s", exc)

    return result


def discover_items(html: str, url: str = "") -> list[dict]:
    """Main entry point: discover repeating items on a page.

    Finds the largest repeating group and extracts fields from each card.
    Returns a list of dicts with extracted fields, or empty list if
    no repeating structure is detected.
    """
    groups = find_repeating_groups(html)
    if not groups:
        return []

    # Use the largest group (most likely the main content list)
    best_group = groups[0]
    items = []
    for card in best_group:
        fields = extract_fields_from_card(card, url)
        # Only include cards that have at least a name
        if fields.get("name"):
            items.append(fields)

    logger.debug(
        "DOM discovery found %d items from %d candidates (url=%s)",
        len(items), len(best_group), url,
    )
    return items
