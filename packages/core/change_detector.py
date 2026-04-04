"""
Change Detector — compare crawl snapshots to detect new, removed, and changed items.

Compares two sets of extracted items (old vs new snapshot) and produces a
structured diff report with per-item change classification:

- **added**: item exists only in the new snapshot
- **removed**: item exists only in the old snapshot
- **price_change**: matched item with a different price (includes absolute + percentage delta)
- **field_change**: matched item with non-price field differences
- **unchanged**: matched item with no differences

Matching algorithm:
    1. Build a lookup key per item using ``key_fields`` (default: ``product_url``,
       fallback: ``name``).  Keys are lowercased and stripped before comparison.
    2. Items present in both snapshots are compared field-by-field, ignoring
       internal meta fields (``_relevance_score``, ``_confidence``, ``extracted_at``,
       ``crawl_id``).
    3. Unmatched items in the new snapshot are classified as *added*; unmatched
       items in the old snapshot are classified as *removed*.

Price parsing reuses :func:`packages.core.normalizer.clean_price` so the same
formats (``$1,234.56``, ``29,99 €``, ``¥19800``, etc.) are handled consistently.

Usage::

    detector = ChangeDetector()
    report   = detector.compare(old_items, new_items)

    # Price drops > 10 %
    alerts = detector.get_price_alerts(report, threshold_pct=10.0)
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from packages.core.normalizer import clean_price

logger = logging.getLogger(__name__)

__all__ = [
    "ChangeType",
    "ItemChange",
    "DiffReport",
    "ChangeDetector",
]

# ---- Meta fields excluded from field-by-field comparison --------------------

_IGNORE_FIELDS: set[str] = {
    "_relevance_score",
    "_confidence",
    "extracted_at",
    "crawl_id",
}

# ---- Regex for extracting a bare numeric value from a cleaned price string --

_NUMERIC_RE = re.compile(r"[\d.]+")


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class ChangeType(StrEnum):
    """Classification of a detected change."""

    ADDED = "added"
    REMOVED = "removed"
    PRICE_CHANGE = "price_change"
    FIELD_CHANGE = "field_change"
    UNCHANGED = "unchanged"


@dataclass
class ItemChange:
    """A detected change for a single item."""

    change_type: ChangeType
    item_key: str
    old_values: dict | None = None
    new_values: dict | None = None
    changed_fields: list[str] = field(default_factory=list)
    price_delta: float | None = None
    price_delta_pct: float | None = None


@dataclass
class DiffReport:
    """Full diff report between two snapshots."""

    old_snapshot_id: str
    new_snapshot_id: str
    timestamp: datetime
    total_old: int
    total_new: int
    added: list[ItemChange] = field(default_factory=list)
    removed: list[ItemChange] = field(default_factory=list)
    price_changes: list[ItemChange] = field(default_factory=list)
    field_changes: list[ItemChange] = field(default_factory=list)
    unchanged_count: int = 0
    summary: dict = field(default_factory=dict)

    # -- serialisation helpers ------------------------------------------------

    def to_dict(self) -> dict:
        """Return a JSON-serialisable dictionary."""
        return {
            "old_snapshot_id": self.old_snapshot_id,
            "new_snapshot_id": self.new_snapshot_id,
            "timestamp": self.timestamp.isoformat(),
            "total_old": self.total_old,
            "total_new": self.total_new,
            "added": [_item_change_to_dict(c) for c in self.added],
            "removed": [_item_change_to_dict(c) for c in self.removed],
            "price_changes": [_item_change_to_dict(c) for c in self.price_changes],
            "field_changes": [_item_change_to_dict(c) for c in self.field_changes],
            "unchanged_count": self.unchanged_count,
            "summary": self.summary,
        }


def _item_change_to_dict(change: ItemChange) -> dict:
    """Serialise an :class:`ItemChange` to a plain dict."""
    return {
        "change_type": change.change_type.value,
        "item_key": change.item_key,
        "old_values": change.old_values,
        "new_values": change.new_values,
        "changed_fields": change.changed_fields,
        "price_delta": change.price_delta,
        "price_delta_pct": change.price_delta_pct,
    }


# ---------------------------------------------------------------------------
# Core detector
# ---------------------------------------------------------------------------


class ChangeDetector:
    """Detect changes between two crawl snapshots.

    All methods are synchronous (CPU-bound dict comparison, no I/O).
    """

    def __init__(
        self,
        ignore_fields: set[str] | None = None,
    ) -> None:
        self._ignore_fields = ignore_fields if ignore_fields is not None else _IGNORE_FIELDS

    # -- public API -----------------------------------------------------------

    def compare(
        self,
        old_items: list[dict],
        new_items: list[dict],
        key_fields: list[str] | None = None,
        old_snapshot_id: str = "",
        new_snapshot_id: str = "",
    ) -> DiffReport:
        """Compare two sets of extracted items and return a :class:`DiffReport`.

        Parameters
        ----------
        old_items:
            Items from the previous crawl snapshot.
        new_items:
            Items from the current crawl snapshot.
        key_fields:
            Fields used to match items across snapshots.  Defaults to
            ``["product_url"]``; falls back to ``["name"]`` when no item
            in *old_items* contains any of the requested key fields.
        old_snapshot_id:
            Identifier for the old snapshot (for reporting).
        new_snapshot_id:
            Identifier for the new snapshot (for reporting).
        """
        effective_keys = self._resolve_key_fields(key_fields, old_items, new_items)

        matched, added_raw, removed_raw = self._match_items(
            old_items, new_items, effective_keys,
        )

        added: list[ItemChange] = []
        removed: list[ItemChange] = []
        price_changes: list[ItemChange] = []
        field_changes: list[ItemChange] = []
        unchanged_count = 0

        # -- added items ------------------------------------------------------
        for item in added_raw:
            key = self._item_key(item, effective_keys)
            added.append(ItemChange(
                change_type=ChangeType.ADDED,
                item_key=key,
                old_values=None,
                new_values=item,
            ))

        # -- removed items ----------------------------------------------------
        for item in removed_raw:
            key = self._item_key(item, effective_keys)
            removed.append(ItemChange(
                change_type=ChangeType.REMOVED,
                item_key=key,
                old_values=item,
                new_values=None,
            ))

        # -- matched items: field-by-field comparison -------------------------
        for old_item, new_item in matched:
            key = self._item_key(new_item, effective_keys)
            changed = self._compare_fields(old_item, new_item, self._ignore_fields)
            abs_delta, pct_delta = self._compute_price_delta(old_item, new_item)

            has_price_change = abs_delta is not None and abs_delta != 0.0
            has_field_change = bool(changed)

            if has_price_change:
                # Separate price from the rest of the changed fields for clarity
                non_price_changed = [f for f in changed if f != "price"]
                change = ItemChange(
                    change_type=ChangeType.PRICE_CHANGE,
                    item_key=key,
                    old_values=old_item,
                    new_values=new_item,
                    changed_fields=changed,
                    price_delta=abs_delta,
                    price_delta_pct=pct_delta,
                )
                price_changes.append(change)

                # If there are also non-price field changes, record separately
                if non_price_changed:
                    field_changes.append(ItemChange(
                        change_type=ChangeType.FIELD_CHANGE,
                        item_key=key,
                        old_values=old_item,
                        new_values=new_item,
                        changed_fields=non_price_changed,
                    ))
            elif has_field_change:
                field_changes.append(ItemChange(
                    change_type=ChangeType.FIELD_CHANGE,
                    item_key=key,
                    old_values=old_item,
                    new_values=new_item,
                    changed_fields=changed,
                ))
            else:
                unchanged_count += 1

        report = DiffReport(
            old_snapshot_id=old_snapshot_id,
            new_snapshot_id=new_snapshot_id,
            timestamp=datetime.now(timezone.utc),
            total_old=len(old_items),
            total_new=len(new_items),
            added=added,
            removed=removed,
            price_changes=price_changes,
            field_changes=field_changes,
            unchanged_count=unchanged_count,
            summary={
                "added": len(added),
                "removed": len(removed),
                "price_changes": len(price_changes),
                "field_changes": len(field_changes),
                "unchanged": unchanged_count,
            },
        )

        logger.info(
            "Change detection complete",
            extra={
                "old_snapshot": old_snapshot_id,
                "new_snapshot": new_snapshot_id,
                "summary": report.summary,
            },
        )
        return report

    def get_price_alerts(
        self,
        report: DiffReport,
        threshold_pct: float = 10.0,
    ) -> list[ItemChange]:
        """Return items whose price changed by more than *threshold_pct* percent.

        Both price increases and decreases are returned if their absolute
        percentage change exceeds the threshold.
        """
        alerts: list[ItemChange] = []
        for change in report.price_changes:
            if change.price_delta_pct is not None and abs(change.price_delta_pct) >= threshold_pct:
                alerts.append(change)
        return alerts

    # -- internal helpers -----------------------------------------------------

    @staticmethod
    def _resolve_key_fields(
        key_fields: list[str] | None,
        old_items: list[dict],
        new_items: list[dict],
    ) -> list[str]:
        """Determine the effective key fields to use for matching.

        Falls back to ``["name"]`` when the requested key fields are not
        present in *any* of the items.
        """
        candidates = key_fields if key_fields else ["product_url"]
        all_items = old_items + new_items
        if all_items and any(
            any(k in item for k in candidates) for item in all_items
        ):
            return candidates
        # Fallback
        logger.debug(
            "Key fields %s not found in items, falling back to ['name']",
            candidates,
        )
        return ["name"]

    @staticmethod
    def _item_key(item: dict, key_fields: list[str]) -> str:
        """Generate a normalised matching key for an item.

        Concatenates the values of all *key_fields* (lowercased, stripped)
        with ``"|"`` as separator.
        """
        parts: list[str] = []
        for kf in key_fields:
            val = item.get(kf, "")
            if val is None:
                val = ""
            parts.append(str(val).strip().lower())
        return "|".join(parts)

    def _match_items(
        self,
        old: list[dict],
        new: list[dict],
        key_fields: list[str],
    ) -> tuple[list[tuple[dict, dict]], list[dict], list[dict]]:
        """Match items across snapshots by *key_fields*.

        Returns
        -------
        matched :
            List of ``(old_item, new_item)`` pairs.
        added :
            Items present only in the new snapshot.
        removed :
            Items present only in the old snapshot.
        """
        old_index: dict[str, dict] = {}
        for item in old:
            key = self._item_key(item, key_fields)
            if key and key not in old_index:
                old_index[key] = item

        matched: list[tuple[dict, dict]] = []
        added: list[dict] = []
        seen_old_keys: set[str] = set()

        for item in new:
            key = self._item_key(item, key_fields)
            if key and key in old_index:
                matched.append((old_index[key], item))
                seen_old_keys.add(key)
            else:
                added.append(item)

        removed = [
            item for key, item in old_index.items()
            if key not in seen_old_keys
        ]

        return matched, added, removed

    @staticmethod
    def _compare_fields(
        old: dict,
        new: dict,
        ignore_fields: set[str],
    ) -> list[str]:
        """Compare all fields between two items, returning changed field names.

        Fields listed in *ignore_fields* are skipped.  A field is considered
        changed when its string representation differs after stripping
        whitespace (to avoid false positives from trailing spaces).
        """
        all_keys = (set(old.keys()) | set(new.keys())) - ignore_fields
        changed: list[str] = []
        for key in sorted(all_keys):
            old_val = old.get(key)
            new_val = new.get(key)
            # Normalise to comparable form
            if _normalised_eq(old_val, new_val):
                continue
            changed.append(key)
        return changed

    @staticmethod
    def _compute_price_delta(
        old: dict,
        new: dict,
    ) -> tuple[float | None, float | None]:
        """Compute absolute and percentage price change between two items.

        Uses :func:`clean_price` from the normalizer to parse string prices.
        Returns ``(None, None)`` if either side lacks a parseable price.
        """
        old_price = _parse_price(old.get("price"))
        new_price = _parse_price(new.get("price"))

        if old_price is None or new_price is None:
            return None, None

        abs_delta = round(new_price - old_price, 4)

        if old_price == 0.0:
            pct_delta = None
        else:
            pct_delta = round((abs_delta / old_price) * 100.0, 2)

        return abs_delta, pct_delta


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_price(value: object) -> float | None:
    """Extract a float price from a raw value (numeric or string).

    Delegates string cleaning to :func:`packages.core.normalizer.clean_price`.
    """
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        return float(value)

    cleaned = clean_price(str(value))
    if not cleaned:
        return None

    match = _NUMERIC_RE.search(cleaned)
    if not match:
        return None

    try:
        return float(match.group())
    except (ValueError, TypeError):
        return None


def _normalised_eq(a: object, b: object) -> bool:
    """Return ``True`` when *a* and *b* are semantically equal.

    - Both ``None`` → equal
    - Strings are compared after stripping whitespace
    - Lists / dicts compared directly
    - Otherwise fallback to ``==``
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        # Treat None vs empty-string as equal to reduce noise
        if (a is None and b == "") or (b is None and a == ""):
            return True
        return False
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    return a == b
