"""
DOM auto-discovery — find repeating product groups on any page without selectors.

Uses tag-path fingerprinting and sibling subtree comparison to identify
repeating data records (product cards, search results, list items, etc.)
without any site-specific configuration.

KEY INSIGHT: Navigation links are always the largest repeating group on any
site. The algorithm must score groups by "product-likeness" (has price? image?
structured data?) not just count.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin

logger = logging.getLogger(__name__)

# Minimum number of similar siblings to consider a repeating group
MIN_REPEATING_COUNT = 3

# Tags that are never data containers
SKIP_TAGS = frozenset({
    "script", "style", "noscript", "link", "meta", "head",
    "iframe", "svg", "path",
})

# Tags that are navigation containers — deprioritized
NAV_TAGS = frozenset({"nav", "header", "footer"})

# Tags commonly used as repeating-group containers
CONTAINER_TAGS = frozenset({
    "ul", "ol", "div", "section", "main", "tbody", "article",
})

# Price regex for field extraction
PRICE_PATTERN = re.compile(
    r"(?:[\$£€¥₹₽₩]|Rs\.?)\s*(\d{1,3}(?:[,\.]\d{3})*(?:[,\.]\d{2})?)"
)

# Simpler price pattern for detection (any number with currency context)
HAS_PRICE = re.compile(
    r"[\$£€¥₹₽₩]|(?:Rs|USD|EUR|GBP|PKR|price|Price)\s*[\d,.]"
)


def _tag_signature(element) -> str:
    """Create a structural signature for a DOM element."""
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

    if parts_a[0] != parts_b[0]:
        return 0.0

    score = 0.3

    if len(parts_a) > 1 and len(parts_b) > 1:
        children_a = set(parts_a[1].split("_")) if parts_a[1] else set()
        children_b = set(parts_b[1].split("_")) if parts_b[1] else set()
        if children_a and children_b:
            intersection = children_a & children_b
            union = children_a | children_b
            score += 0.4 * (len(intersection) / len(union))
        elif not children_a and not children_b:
            score += 0.4

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


def _is_inside_nav(element) -> bool:
    """Check if element is inside a nav/header/footer."""
    parent = element.parent
    depth = 0
    while parent and depth < 10:
        if hasattr(parent, "name") and parent.name in NAV_TAGS:
            return True
        # Also check for nav-like class names
        if hasattr(parent, "attrs"):
            classes = " ".join(parent.get("class", []))
            if any(kw in classes.lower() for kw in ["nav", "menu", "header", "footer", "breadcrumb", "sidebar"]):
                return True
        parent = parent.parent
        depth += 1
    return False


def _score_group(group: list) -> float:
    """Score a group of elements by how product-like they are.

    Higher score = more likely to be actual product/data cards.
    Navigation links score low; cards with prices/images score high.
    """
    if not group:
        return 0.0

    score = 0.0
    sample_size = min(len(group), 5)
    sample = group[:sample_size]

    has_price_count = 0
    has_image_count = 0
    has_heading_count = 0
    avg_text_len = 0
    avg_child_count = 0
    inside_nav_count = 0

    for el in sample:
        text = el.get_text(" ", strip=True) if hasattr(el, "get_text") else ""
        avg_text_len += len(text)

        # Check for price
        if HAS_PRICE.search(text):
            has_price_count += 1

        # Check for image
        if el.select_one("img") if hasattr(el, "select_one") else False:
            has_image_count += 1

        # Check for heading
        if el.select_one("h1, h2, h3, h4, h5, h6") if hasattr(el, "select_one") else False:
            has_heading_count += 1

        # Count child elements (richer cards have more children)
        children = [c for c in el.children if hasattr(c, "name") and c.name is not None] if hasattr(el, "children") else []
        avg_child_count += len(children)

        # Check if inside nav
        if _is_inside_nav(el):
            inside_nav_count += 1

    avg_text_len /= sample_size
    avg_child_count /= sample_size

    # Scoring rules:
    # +3 per item with price (strongest product signal)
    score += (has_price_count / sample_size) * 3.0

    # +2 per item with image
    score += (has_image_count / sample_size) * 2.0

    # +1 per item with heading
    score += (has_heading_count / sample_size) * 1.0

    # +1 for rich cards (>3 child elements avg)
    if avg_child_count > 3:
        score += 1.0
    elif avg_child_count > 1:
        score += 0.5

    # +0.5 for longer text (product descriptions vs nav labels)
    if avg_text_len > 50:
        score += 0.5

    # -3 if most items are inside nav/header/footer
    if inside_nav_count > sample_size * 0.5:
        score -= 3.0

    # +0.5 for larger groups (more products = more confidence)
    if len(group) >= 5:
        score += 0.5
    if len(group) >= 10:
        score += 0.5

    # Penalty for very simple elements (just a single <a> with text — likely nav)
    if avg_child_count < 1.5 and avg_text_len < 30:
        score -= 2.0

    return score


def find_repeating_groups(html: str) -> list[list]:
    """Find groups of structurally similar sibling elements in the DOM.

    Returns groups sorted by product-likeness score (best first),
    not just by size.
    """
    try:
        from bs4 import BeautifulSoup, Tag
    except ImportError:
        return []

    soup = BeautifulSoup(html, "html.parser")
    found_groups: list[tuple[float, list]] = []  # (score, group)

    for container in soup.find_all(CONTAINER_TAGS):
        # Skip containers inside nav/header/footer
        if _is_inside_nav(container):
            continue

        children = [
            c for c in container.children
            if isinstance(c, Tag) and c.name not in SKIP_TAGS
        ]

        if len(children) < MIN_REPEATING_COUNT:
            continue

        sigs = [(child, _tag_signature(child)) for child in children]
        sigs = [(child, sig) for child, sig in sigs if sig]

        if len(sigs) < MIN_REPEATING_COUNT:
            continue

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

        for sig, group in groups.items():
            if len(group) >= MIN_REPEATING_COUNT:
                first_el_id = id(group[0])
                already_found = any(
                    id(g[0]) == first_el_id for _, g in found_groups
                )
                if not already_found:
                    group_score = _score_group(group)
                    found_groups.append((group_score, group))

    # Sort by score (highest first), not size
    found_groups.sort(key=lambda x: x[0], reverse=True)
    return [group for _, group in found_groups]


def extract_fields_from_card(element, url: str = "") -> dict:
    """Extract common product/item fields from a single card element."""
    result: dict = {}

    try:
        # --- Name: prefer headings over links ---
        name_el = element.select_one("h1, h2, h3, h4, h5, h6")
        if not name_el:
            name_el = element.select_one("a[title]")
        if not name_el:
            name_el = element.select_one("a")

        if name_el:
            name = (
                (name_el.get("title") or "").strip()
                or (name_el.get_text(strip=True) or "").strip()
            )
            if name and len(name) > 1:
                result["name"] = name

            link_el = name_el if name_el.get("href") else name_el.select_one("a[href]")
            if link_el:
                href = link_el.get("href", "")
                if href and href != "#":
                    if url and not href.startswith(("http://", "https://")):
                        from html import unescape
                        href = urljoin(url, unescape(href))
                    if href.startswith(("http://", "https://")):
                        result["product_url"] = href

        # --- Price: find text matching price pattern ---
        # Prefer .a-offscreen, [itemprop=price], or dedicated price elements
        price_el = element.select_one(
            ".a-price .a-offscreen, [itemprop='price'], "
            "[class*='price'] .amount, [class*='price']"
        )
        if price_el:
            price_text = price_el.get("content") or price_el.get_text(strip=True)
            if price_text:
                price_match = PRICE_PATTERN.search(price_text)
                if price_match:
                    result["price"] = price_match.group(0)

        if "price" not in result:
            card_text = element.get_text(" ", strip=True)
            price_match = PRICE_PATTERN.search(card_text)
            if price_match:
                result["price"] = price_match.group(0)

        # --- Image ---
        img_el = element.select_one("img")
        if img_el:
            src = img_el.get("src") or img_el.get("data-src") or img_el.get("data-lazy-src", "")
            if src and "sprite" not in src and "icon" not in src and "pixel" not in src:
                if url and not src.startswith(("http://", "https://", "data:")):
                    src = urljoin(url, src)
                if src.startswith(("http://", "https://", "data:")):
                    result["image_url"] = src

        # --- Rating ---
        rating_el = element.select_one(
            "[class*='star-rating'], [class*='rating'], "
            "[itemprop='ratingValue'], [class*='stars']"
        )
        if rating_el:
            rating_text = rating_el.get("content") or rating_el.get("aria-label") or rating_el.get_text(strip=True)
            if rating_text:
                rating_match = re.search(r"(\d+(?:\.\d+)?)", rating_text)
                if rating_match:
                    result["rating"] = rating_match.group(1)

        if not result.get("product_url") and url:
            result["product_url"] = url

    except Exception as exc:
        logger.debug("Field extraction failed for card: %s", exc)

    return result


def _is_noise_item(item: dict) -> bool:
    """Check if an extracted item is likely a navigation element or section header.

    Returns True if the item should be filtered out. Items like "Trending Now",
    "Top Brands", "Superdrugs" are noise — they have a name but no product signals.
    """
    name = (item.get("name") or "").strip()
    if not name:
        return True

    # Very short names with no other fields are likely nav labels
    has_price = bool(item.get("price"))
    has_image = bool(item.get("image_url"))
    has_rating = bool(item.get("rating"))
    has_description = bool(item.get("description"))

    # Must have at least ONE product signal beyond just a name
    if not any([has_price, has_image, has_rating, has_description]):
        return True

    # Common section header / nav patterns
    NOISE_NAMES = {
        "trending", "trending now", "top brands", "new arrivals",
        "best sellers", "bestsellers", "sale", "shop now", "view all",
        "see all", "learn more", "read more", "load more", "show more",
        "categories", "collections", "brands", "featured", "popular",
        "home", "about", "contact", "login", "sign up", "sign in",
        "cart", "wishlist", "account", "search", "menu", "close",
    }
    if name.lower() in NOISE_NAMES:
        return True

    # Names that are just 1-2 words with no price are likely section labels
    if len(name.split()) <= 2 and not has_price and not has_rating:
        # But allow if they have an image (could be a product card with short name)
        if not has_image:
            return True

    return False


def discover_items(html: str, url: str = "") -> list[dict]:
    """Main entry point: discover repeating product items on a page.

    Finds the highest-scoring repeating group (by product-likeness)
    and extracts fields from each card. Filters out navigation elements,
    section headers, and other noise items.
    """
    groups = find_repeating_groups(html)
    if not groups:
        return []

    # Try top 3 groups — pick the one that yields the most items with prices
    best_items: list[dict] = []

    for group in groups[:3]:
        items = []
        for card in group:
            fields = extract_fields_from_card(card, url)
            if fields.get("name") and not _is_noise_item(fields):
                items.append(fields)

        # Score: items with prices are worth more
        items_with_price = sum(1 for i in items if i.get("price"))
        score = len(items) + items_with_price * 2

        if score > len(best_items) + sum(1 for i in best_items if i.get("price")) * 2:
            best_items = items

    logger.debug(
        "DOM discovery found %d items (url=%s, filtered noise)",
        len(best_items), url,
    )
    return best_items
