"""
Content Relevance Filter — BM25-based relevance scoring and multi-criteria filtering.

Uses rank-bm25 to score extracted items against a user query, and provides
keyword, price range, and field-existence filters that can be composed together.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

__all__ = ["ContentFilter"]


def _tokenize(text: str) -> list[str]:
    """Lowercase and split text into word tokens."""
    return re.findall(r"[a-z0-9]+", text.lower())


def _item_to_text(item: dict[str, Any]) -> str:
    """Concatenate all string-valued fields of an item into a single text blob."""
    parts: list[str] = []
    for value in item.values():
        if isinstance(value, str):
            parts.append(value)
        elif isinstance(value, list):
            parts.extend(str(v) for v in value if isinstance(v, str))
    return " ".join(parts)


def _extract_price(item: dict[str, Any]) -> float | None:
    """Try to pull a numeric price from common price fields."""
    for key in ("price", "sale_price", "current_price", "price_amount"):
        raw = item.get(key)
        if raw is None:
            continue
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            # Strip currency symbols and whitespace, keep first number
            cleaned = re.sub(r"[^\d.]", "", raw.split()[0] if raw.split() else "")
            if cleaned:
                try:
                    return float(cleaned)
                except ValueError:
                    continue
    return None


class ContentFilter:
    """BM25-powered content relevance filter with composable criteria.

    Typical usage::

        cf = ContentFilter()
        results = cf.apply_filters(
            items,
            relevance_query="gaming laptop 16 inch",
            keywords=["RTX", "144Hz"],
            price_range=(500.0, 1500.0),
            required_fields=["name", "price"],
        )
    """

    # ------------------------------------------------------------------
    # Relevance (BM25)
    # ------------------------------------------------------------------

    def filter_by_relevance(
        self,
        items: list[dict[str, Any]],
        query: str,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Score items against *query* using BM25Okapi and return them sorted by relevance.

        Items whose score falls strictly below *threshold* are removed.
        Each returned item receives a ``_relevance_score`` float field.
        """
        if not items or not query.strip():
            return items

        corpus = [_tokenize(_item_to_text(item)) for item in items]
        query_tokens = _tokenize(query)

        if not query_tokens:
            return items

        # Guard against an empty corpus (all items yielded no tokens)
        if all(len(doc) == 0 for doc in corpus):
            logger.debug("All items produced empty token lists; skipping BM25 scoring")
            for item in items:
                item["_relevance_score"] = 0.0
            return items

        bm25 = BM25Okapi(corpus)
        scores = bm25.get_scores(query_tokens)

        scored: list[tuple[float, dict[str, Any]]] = []
        for item, score in zip(items, scores):
            item["_relevance_score"] = round(float(score), 6)
            if score >= threshold:
                scored.append((score, item))

        # Sort descending by score
        scored.sort(key=lambda pair: pair[0], reverse=True)
        result = [item for _, item in scored]

        logger.info(
            "BM25 relevance filter applied",
            extra={
                "query": query,
                "input_count": len(items),
                "output_count": len(result),
                "threshold": threshold,
            },
        )
        return result

    # ------------------------------------------------------------------
    # Keyword filtering
    # ------------------------------------------------------------------

    def filter_by_keywords(
        self,
        items: list[dict[str, Any]],
        keywords: list[str],
        fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Keep items that contain *any* of the given keywords.

        If *fields* is provided, only those fields are searched; otherwise all
        string-valued fields are checked.  Matching is case-insensitive.
        """
        if not items or not keywords:
            return items

        lower_keywords = [kw.lower() for kw in keywords]
        result: list[dict[str, Any]] = []

        for item in items:
            text_parts: list[str] = []
            if fields:
                for f in fields:
                    val = item.get(f)
                    if isinstance(val, str):
                        text_parts.append(val.lower())
            else:
                for val in item.values():
                    if isinstance(val, str):
                        text_parts.append(val.lower())

            combined = " ".join(text_parts)
            if any(kw in combined for kw in lower_keywords):
                result.append(item)

        logger.info(
            "Keyword filter applied",
            extra={
                "keywords": keywords,
                "fields": fields,
                "input_count": len(items),
                "output_count": len(result),
            },
        )
        return result

    # ------------------------------------------------------------------
    # Price-range filtering
    # ------------------------------------------------------------------

    def filter_by_price_range(
        self,
        items: list[dict[str, Any]],
        min_price: float | None = None,
        max_price: float | None = None,
    ) -> list[dict[str, Any]]:
        """Keep items whose price falls within [*min_price*, *max_price*].

        Items without a parseable price are excluded when a range is specified.
        """
        if not items or (min_price is None and max_price is None):
            return items

        result: list[dict[str, Any]] = []
        for item in items:
            price = _extract_price(item)
            if price is None:
                continue
            if min_price is not None and price < min_price:
                continue
            if max_price is not None and price > max_price:
                continue
            result.append(item)

        logger.info(
            "Price range filter applied",
            extra={
                "min_price": min_price,
                "max_price": max_price,
                "input_count": len(items),
                "output_count": len(result),
            },
        )
        return result

    # ------------------------------------------------------------------
    # Field-existence filtering
    # ------------------------------------------------------------------

    def filter_by_fields(
        self,
        items: list[dict[str, Any]],
        required_fields: list[str],
    ) -> list[dict[str, Any]]:
        """Keep only items that have non-empty values for every field in *required_fields*."""
        if not items or not required_fields:
            return items

        result: list[dict[str, Any]] = []
        for item in items:
            if all(_has_value(item, f) for f in required_fields):
                result.append(item)

        logger.info(
            "Field-existence filter applied",
            extra={
                "required_fields": required_fields,
                "input_count": len(items),
                "output_count": len(result),
            },
        )
        return result

    # ------------------------------------------------------------------
    # Composite
    # ------------------------------------------------------------------

    def apply_filters(
        self,
        items: list[dict[str, Any]],
        relevance_query: str | None = None,
        keywords: list[str] | None = None,
        price_range: tuple[float | None, float | None] | None = None,
        required_fields: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Apply all specified filters in sequence and return the surviving items.

        Filter order: required_fields -> keywords -> price_range -> relevance.
        Relevance is applied last so BM25 scoring operates on the already-narrowed set.
        """
        result = list(items)

        if required_fields:
            result = self.filter_by_fields(result, required_fields)

        if keywords:
            result = self.filter_by_keywords(result, keywords)

        if price_range is not None:
            min_p, max_p = price_range
            result = self.filter_by_price_range(result, min_price=min_p, max_price=max_p)

        if relevance_query:
            result = self.filter_by_relevance(result, relevance_query)

        logger.info(
            "All filters applied",
            extra={"input_count": len(items), "output_count": len(result)},
        )
        return result


def _has_value(item: dict[str, Any], field: str) -> bool:
    """Return True if *field* exists in *item* and has a non-empty value."""
    val = item.get(field)
    if val is None:
        return False
    if isinstance(val, str) and not val.strip():
        return False
    if isinstance(val, (list, dict)) and len(val) == 0:
        return False
    return True
