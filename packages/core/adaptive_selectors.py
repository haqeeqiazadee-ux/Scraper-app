"""
Adaptive selector engine — self-healing CSS selectors with fuzzy matching.

Extends the existing SelectorCache with structural fingerprinting and
similarity-based selector recovery.  When a cached selector breaks because
a site changed its layout, the engine attempts to find the "same" element
by comparing tag paths, text samples, and attribute signatures against the
current DOM.

Borrows ideas from:
  * Scrapling  — "similar" matching (find elements by text/attribute similarity
    when CSS breaks) and auto-save of working selectors after each extraction.
  * Crawl4AI   — learning loop (track selector success rate over time, decay
    stale selectors that keep failing).

No external dependencies beyond BeautifulSoup (already a project dep) and
the stdlib ``difflib.SequenceMatcher``.
"""

from __future__ import annotations

import dataclasses
import json
import logging
import os
import time
from difflib import SequenceMatcher
from typing import Optional
from urllib.parse import urlparse

from packages.core.selector_cache import SelectorCache, _domain_key

logger = logging.getLogger(__name__)

__all__ = [
    "SelectorFingerprint",
    "AdaptiveSelectorEngine",
]

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_SIMILARITY_THRESHOLD = 0.7
STALE_DAYS = 30
STALE_SECONDS = STALE_DAYS * 24 * 60 * 60
TEXT_SAMPLE_LEN = 100
# Attributes worth tracking for similarity comparison
_TRACKED_ATTRS = frozenset({"class", "id", "data-testid", "data-id", "role", "type", "name", "itemprop"})


# ---------------------------------------------------------------------------
# SelectorFingerprint
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class SelectorFingerprint:
    """Structural fingerprint of a selector's target element."""

    selector: str
    tag_path: str = ""
    text_sample: str = ""
    attributes: dict[str, str] = dataclasses.field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    last_success: float = 0.0
    created_at: float = dataclasses.field(default_factory=time.time)

    # -- Serialisation helpers ------------------------------------------------

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> SelectorFingerprint:
        return cls(**{
            k: v for k, v in data.items()
            if k in {f.name for f in dataclasses.fields(cls)}
        })


# ---------------------------------------------------------------------------
# AdaptiveSelectorEngine
# ---------------------------------------------------------------------------

class AdaptiveSelectorEngine:
    """Self-healing CSS selector engine with fuzzy matching.

    Wraps :class:`SelectorCache` and adds per-domain fingerprint storage so
    that selectors can be *adapted* when a site changes its layout instead of
    discarded.
    """

    def __init__(
        self,
        cache_dir: str,
        ttl_seconds: int,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> None:
        self._cache = SelectorCache(cache_dir, ttl_seconds)
        self._cache_dir = cache_dir
        self._similarity_threshold = similarity_threshold
        # domain-key -> list[SelectorFingerprint]
        self._fingerprints: dict[str, list[SelectorFingerprint]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_selectors(self, url: str) -> Optional[dict]:
        """Return cached selectors for *url*, or ``None`` if not cached."""
        return self._cache.get(url)

    def adapt_selectors(self, url: str, html: str) -> Optional[dict]:
        """Try to adapt stale/broken selectors to the current DOM.

        Algorithm:
        1. Load fingerprints for the URL's domain key.
        2. For each fingerprint, search the current DOM for a similar element.
        3. If found (similarity > threshold), build an adapted selector dict
           and return it.
        4. Otherwise return ``None`` — caller should fall through to DOM
           auto-discovery.
        """
        domain_key = _domain_key(url)
        fingerprints = self._load_fingerprints(domain_key)
        if not fingerprints:
            return None

        adapted_card: Optional[str] = None
        adapted_fields: dict[str, str] = {}

        for fp in fingerprints:
            new_selector = self._find_similar_element(fp, html)
            if new_selector is None:
                continue

            # Decide whether this fingerprint was the card selector or a field
            if fp.selector == fp.selector:  # always true — classify below
                # Heuristic: fingerprints whose tag_path is longer (deeper nesting)
                # are typically field selectors; the shortest one is the card.
                pass

            adapted_fields[fp.selector] = new_selector
            logger.info(
                "Selector drift detected — adapted '%s' -> '%s' (similarity ok)",
                fp.selector,
                new_selector,
            )

        if not adapted_fields:
            return None

        # Try to reconstruct the cache entry shape.  The original cache stores
        # "card_selector" + "field_selectors".  We recover whatever we can.
        cached = self._cache.get(url)
        card_selector = (cached or {}).get("card_selector", "")
        field_selectors: dict[str, str] = dict((cached or {}).get("field_selectors", {}))

        for original_sel, new_sel in adapted_fields.items():
            if original_sel == card_selector:
                adapted_card = new_sel
            else:
                # Replace the field selector whose value matches the original
                for field_name, field_sel in list(field_selectors.items()):
                    if field_sel == original_sel:
                        field_selectors[field_name] = new_sel
                        break

        result_card = adapted_card or card_selector
        if not result_card:
            return None

        # Persist the adapted selectors so future requests use them directly.
        self._cache.put(url, result_card, field_selectors, source="adaptive")
        return {
            "card_selector": result_card,
            "field_selectors": field_selectors,
            "discovered_at": time.time(),
            "source": "adaptive",
            "url": url,
        }

    def record_success(self, url: str, selectors: dict, html: str) -> None:
        """Record that *selectors* successfully extracted data.

        Updates fingerprints (creating new ones if needed) and refreshes the
        underlying selector cache.
        """
        domain_key = _domain_key(url)
        fingerprints = self._load_fingerprints(domain_key)
        fp_map: dict[str, SelectorFingerprint] = {fp.selector: fp for fp in fingerprints}

        now = time.time()

        # Collect every concrete selector string from the dict.
        all_selectors = self._selectors_from_dict(selectors)

        for sel in all_selectors:
            if sel in fp_map:
                fp_map[sel].success_count += 1
                fp_map[sel].last_success = now
            else:
                fp = self._build_fingerprint(sel, html)
                if fp is not None:
                    fp.success_count = 1
                    fp.last_success = now
                    fp_map[sel] = fp

        self._fingerprints[domain_key] = list(fp_map.values())
        self._save_fingerprints(domain_key)

        # Also refresh the plain selector cache.
        card = selectors.get("card_selector", "")
        fields = selectors.get("field_selectors", {})
        source = selectors.get("source", "adaptive")
        if card:
            self._cache.put(url, card, fields, source=source)

    def record_failure(self, url: str, selectors: dict) -> None:
        """Record that *selectors* failed — increment failure counts."""
        domain_key = _domain_key(url)
        fingerprints = self._load_fingerprints(domain_key)
        fp_map: dict[str, SelectorFingerprint] = {fp.selector: fp for fp in fingerprints}

        all_selectors = self._selectors_from_dict(selectors)
        for sel in all_selectors:
            if sel in fp_map:
                fp_map[sel].failure_count += 1

        self._fingerprints[domain_key] = list(fp_map.values())
        self._decay_stale(domain_key)
        self._save_fingerprints(domain_key)

    # ------------------------------------------------------------------
    # Fingerprint construction
    # ------------------------------------------------------------------

    def _build_fingerprint(self, selector: str, html: str) -> Optional[SelectorFingerprint]:
        """Build a structural fingerprint from *selector* matched against *html*."""
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            logger.warning("BeautifulSoup not available — cannot build fingerprint")
            return None

        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one(selector)
        if el is None:
            return None

        tag_path = self._tag_path(el)
        text_sample = (el.get_text(" ", strip=True) or "")[:TEXT_SAMPLE_LEN]
        attributes = self._tracked_attributes(el)

        return SelectorFingerprint(
            selector=selector,
            tag_path=tag_path,
            text_sample=text_sample,
            attributes=attributes,
            created_at=time.time(),
        )

    # ------------------------------------------------------------------
    # Similarity search
    # ------------------------------------------------------------------

    def _find_similar_element(self, fingerprint: SelectorFingerprint, html: str) -> Optional[str]:
        """Find an element in *html* structurally similar to *fingerprint*.

        Walks every element in the DOM, computes a combined similarity score
        from tag path, text sample, and attribute overlap, and returns a
        freshly-built CSS selector for the best match above the threshold.

        Returns ``None`` if no suitable match is found.
        """
        try:
            from bs4 import BeautifulSoup, Tag
        except ImportError:
            return None

        soup = BeautifulSoup(html, "html.parser")

        best_score: float = 0.0
        best_element = None

        # First, try the original selector — it may still work.
        direct = soup.select_one(fingerprint.selector)
        if direct is not None:
            score = self._element_similarity(fingerprint, direct)
            if score >= self._similarity_threshold:
                return fingerprint.selector

        # Walk the DOM looking for a similar element.
        # Limit to the same base tag to keep it fast.
        base_tag = fingerprint.tag_path.split(" > ")[-1].split(".")[0] if fingerprint.tag_path else None

        candidates = soup.find_all(base_tag) if base_tag else soup.find_all(True)

        for el in candidates:
            if not isinstance(el, Tag):
                continue
            score = self._element_similarity(fingerprint, el)
            if score > best_score:
                best_score = score
                best_element = el

        if best_score < self._similarity_threshold or best_element is None:
            return None

        return self._build_css_selector(best_element)

    def _element_similarity(self, fingerprint: SelectorFingerprint, element) -> float:
        """Combined similarity between a fingerprint and a live DOM element."""
        tag_path = self._tag_path(element)
        text = (element.get_text(" ", strip=True) or "")[:TEXT_SAMPLE_LEN]
        attrs = self._tracked_attributes(element)

        # Tag-path similarity (most important — structural match)
        path_sim = self._similarity(fingerprint.tag_path, tag_path)

        # Text-sample similarity
        text_sim = self._similarity(fingerprint.text_sample, text) if fingerprint.text_sample and text else 0.0

        # Attribute-key overlap (Jaccard)
        fp_keys = set(fingerprint.attributes.keys())
        el_keys = set(attrs.keys())
        if fp_keys or el_keys:
            attr_sim = len(fp_keys & el_keys) / len(fp_keys | el_keys) if (fp_keys | el_keys) else 0.0
        else:
            attr_sim = 1.0  # both empty — trivially equal

        # Weighted combination.  Tag path matters most for structural identity.
        return 0.50 * path_sim + 0.25 * text_sim + 0.25 * attr_sim

    # ------------------------------------------------------------------
    # Helper: build a CSS selector for a matched element
    # ------------------------------------------------------------------

    @staticmethod
    def _build_css_selector(element) -> str:
        """Construct a reasonable CSS selector for *element*.

        Strategy: use tag + id if available, else tag + classes, else
        tag + nth-of-type for disambiguation.
        """
        tag = element.name or "div"

        el_id = element.get("id")
        if el_id:
            return f"{tag}#{el_id}"

        classes = element.get("class", [])
        if classes:
            cls_str = ".".join(classes)
            return f"{tag}.{cls_str}"

        # Fall back to structural path: parent > tag:nth-of-type(n)
        parent = element.parent
        if parent is not None and hasattr(parent, "name") and parent.name:
            siblings = [
                c for c in parent.children
                if hasattr(c, "name") and c.name == tag
            ]
            idx = 1
            for i, sib in enumerate(siblings, 1):
                if sib is element:
                    idx = i
                    break
            parent_sel = ""
            parent_id = parent.get("id") if hasattr(parent, "get") else None
            parent_classes = parent.get("class", []) if hasattr(parent, "get") else []
            if parent_id:
                parent_sel = f"{parent.name}#{parent_id}"
            elif parent_classes:
                parent_sel = f"{parent.name}.{'.'.join(parent_classes)}"
            else:
                parent_sel = parent.name

            return f"{parent_sel} > {tag}:nth-of-type({idx})"

        return tag

    # ------------------------------------------------------------------
    # Tag-path utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _tag_path(element) -> str:
        """Build a tag-path string from *element* up to the root.

        Example: ``"html > body > div.container > ul.products > li.card"``
        """
        parts: list[str] = []
        node = element
        depth = 0
        while node is not None and hasattr(node, "name") and node.name and depth < 20:
            classes = node.get("class", []) if hasattr(node, "get") else []
            if classes:
                part = f"{node.name}.{'.'.join(classes)}"
            else:
                part = node.name
            parts.append(part)
            node = node.parent
            depth += 1
        parts.reverse()
        return " > ".join(parts)

    @staticmethod
    def _tracked_attributes(element) -> dict[str, str]:
        """Return the subset of element attributes we track for fingerprinting."""
        if not hasattr(element, "attrs") or not element.attrs:
            return {}
        result: dict[str, str] = {}
        for attr_name in _TRACKED_ATTRS:
            val = element.get(attr_name)
            if val is not None:
                if isinstance(val, list):
                    result[attr_name] = " ".join(val)
                else:
                    result[attr_name] = str(val)
        return result

    @staticmethod
    def _similarity(a: str, b: str) -> float:
        """Similarity ratio (0.0-1.0) via :class:`SequenceMatcher`."""
        if not a and not b:
            return 1.0
        if not a or not b:
            return 0.0
        return SequenceMatcher(None, a, b).ratio()

    # ------------------------------------------------------------------
    # Decay / pruning
    # ------------------------------------------------------------------

    def _decay_stale(self, domain_key: str) -> None:
        """Remove fingerprints with high failure rate or no success in 30 days."""
        fps = self._fingerprints.get(domain_key, [])
        now = time.time()
        kept: list[SelectorFingerprint] = []
        for fp in fps:
            # Rule 1: failure_count > success_count * 2  -> remove
            if fp.success_count > 0 and fp.failure_count > fp.success_count * 2:
                logger.debug(
                    "Decaying fingerprint '%s' — failure rate too high (%d/%d)",
                    fp.selector, fp.failure_count, fp.success_count,
                )
                continue
            # Rule 2: no success in STALE_DAYS -> remove
            if fp.last_success > 0 and (now - fp.last_success) > STALE_SECONDS:
                logger.debug(
                    "Decaying fingerprint '%s' — no success in %d days",
                    fp.selector, STALE_DAYS,
                )
                continue
            # Rule 3: never succeeded and failure_count > 0 -> remove
            if fp.success_count == 0 and fp.failure_count > 0:
                logger.debug(
                    "Decaying fingerprint '%s' — never succeeded, %d failures",
                    fp.selector, fp.failure_count,
                )
                continue
            kept.append(fp)
        self._fingerprints[domain_key] = kept

    # ------------------------------------------------------------------
    # Persistence (fingerprints stored as JSON alongside selector cache)
    # ------------------------------------------------------------------

    def _fingerprint_path(self, domain_key: str) -> str:
        return os.path.join(self._cache_dir, f"{domain_key}.fingerprints.json")

    def _load_fingerprints(self, domain_key: str) -> list[SelectorFingerprint]:
        """Load fingerprints from memory or disk."""
        if domain_key in self._fingerprints:
            return self._fingerprints[domain_key]

        path = self._fingerprint_path(domain_key)
        if not os.path.exists(path):
            return []

        try:
            with open(path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            fps = [SelectorFingerprint.from_dict(entry) for entry in raw]
            self._fingerprints[domain_key] = fps
            return fps
        except (json.JSONDecodeError, OSError, TypeError) as exc:
            logger.debug("Failed to load fingerprints from %s: %s", path, exc)
            return []

    def _save_fingerprints(self, domain_key: str) -> None:
        """Persist fingerprints to disk."""
        fps = self._fingerprints.get(domain_key, [])
        path = self._fingerprint_path(domain_key)
        try:
            os.makedirs(self._cache_dir, exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump([fp.to_dict() for fp in fps], fh, indent=2)
        except OSError as exc:
            logger.debug("Failed to save fingerprints to %s: %s", path, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _selectors_from_dict(selectors: dict) -> list[str]:
        """Extract all concrete selector strings from a selectors dict."""
        result: list[str] = []
        card = selectors.get("card_selector", "")
        if card:
            result.append(card)
        for sel in (selectors.get("field_selectors") or {}).values():
            if sel:
                result.append(sel)
        return result
