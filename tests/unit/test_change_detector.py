"""Tests for the ChangeDetector."""

from copy import deepcopy

import pytest

from packages.core.change_detector import (
    ChangeDetector,
    ChangeType,
    DiffReport,
    ItemChange,
)


# ---------------------------------------------------------------------------
# Sample product data
# ---------------------------------------------------------------------------

def _product(name, price, url=None, **extra):
    item = {
        "name": name,
        "price": price,
        "product_url": url or f"https://shop.com/{name.lower().replace(' ', '-')}",
        "image_url": f"https://shop.com/img/{name.lower().replace(' ', '-')}.jpg",
    }
    item.update(extra)
    return item


SNAPSHOT_A = [
    _product("Wireless Mouse", "$29.99"),
    _product("Mechanical Keyboard", "$89.99"),
    _product("USB-C Hub", "$49.99"),
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def detector():
    return ChangeDetector()


# ---------------------------------------------------------------------------
# No-change scenario
# ---------------------------------------------------------------------------

class TestNoChanges:

    def test_no_changes(self, detector):
        report = detector.compare(SNAPSHOT_A, deepcopy(SNAPSHOT_A))
        assert len(report.added) == 0
        assert len(report.removed) == 0
        assert len(report.price_changes) == 0
        assert len(report.field_changes) == 0
        assert report.unchanged_count == len(SNAPSHOT_A)


# ---------------------------------------------------------------------------
# Added / removed items
# ---------------------------------------------------------------------------

class TestAddRemove:

    def test_added_items(self, detector):
        new_snapshot = deepcopy(SNAPSHOT_A) + [
            _product("Webcam HD", "$59.99"),
        ]
        report = detector.compare(SNAPSHOT_A, new_snapshot)
        assert len(report.added) == 1
        assert report.added[0].new_values["name"] == "Webcam HD"

    def test_removed_items(self, detector):
        new_snapshot = [SNAPSHOT_A[0], SNAPSHOT_A[2]]  # remove Keyboard
        report = detector.compare(SNAPSHOT_A, new_snapshot)
        assert len(report.removed) == 1
        assert report.removed[0].old_values["name"] == "Mechanical Keyboard"


# ---------------------------------------------------------------------------
# Price changes
# ---------------------------------------------------------------------------

class TestPriceChanges:

    def test_price_increase(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        new_snap[0]["price"] = "$39.99"  # Mouse was $29.99
        report = detector.compare(SNAPSHOT_A, new_snap)
        assert len(report.price_changes) >= 1
        mouse_change = [
            c for c in report.price_changes
            if c.new_values and c.new_values.get("name") == "Wireless Mouse"
        ]
        assert len(mouse_change) == 1
        assert mouse_change[0].price_delta > 0

    def test_price_decrease(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        new_snap[1]["price"] = "$69.99"  # Keyboard was $89.99
        report = detector.compare(SNAPSHOT_A, new_snap)
        assert len(report.price_changes) >= 1
        kb_change = [
            c for c in report.price_changes
            if c.new_values and c.new_values.get("name") == "Mechanical Keyboard"
        ]
        assert len(kb_change) == 1
        assert kb_change[0].price_delta < 0

    def test_price_delta_percentage(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        new_snap[2]["price"] = "$54.99"  # Hub was $49.99
        report = detector.compare(SNAPSHOT_A, new_snap)
        hub_change = [
            c for c in report.price_changes
            if c.new_values and c.new_values.get("name") == "USB-C Hub"
        ]
        assert len(hub_change) == 1
        assert hub_change[0].price_delta_pct is not None
        expected_pct = round(((54.99 - 49.99) / 49.99) * 100.0, 2)
        assert abs(hub_change[0].price_delta_pct - expected_pct) < 0.5


# ---------------------------------------------------------------------------
# Field changes
# ---------------------------------------------------------------------------

class TestFieldChanges:

    def test_field_change_detected(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        new_snap[0]["image_url"] = "https://shop.com/img/new-mouse.jpg"
        report = detector.compare(SNAPSHOT_A, new_snap)
        assert len(report.field_changes) >= 1
        img_change = [
            c for c in report.field_changes
            if "image_url" in c.changed_fields
        ]
        assert len(img_change) == 1

    def test_multiple_change_types(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        # Modify the mouse price
        new_snap[0]["price"] = "$24.99"
        # Remove the keyboard
        new_snap = [new_snap[0], new_snap[2]]
        # Add a new product
        new_snap.append(_product("Monitor 27in", "$399.99"))
        report = detector.compare(SNAPSHOT_A, new_snap)
        assert len(report.added) == 1
        assert len(report.removed) == 1
        assert len(report.price_changes) == 1


# ---------------------------------------------------------------------------
# Matching strategies
# ---------------------------------------------------------------------------

class TestMatching:

    def test_match_by_product_url(self, detector):
        old = [_product("Mouse", "$29.99", url="https://shop.com/mouse-1")]
        new = [_product("Mouse Updated", "$29.99", url="https://shop.com/mouse-1")]
        report = detector.compare(old, new)
        # Same URL => matched, not added/removed
        assert len(report.added) == 0
        assert len(report.removed) == 0
        # Name changed => field_change
        assert len(report.field_changes) >= 1

    def test_match_by_name_fallback(self, detector):
        """When no product_url is present, matching falls back to name."""
        old = [{"name": "Widget", "price": "$10"}]
        new = [{"name": "Widget", "price": "$15"}]
        report = detector.compare(old, new, key_fields=["name"])
        assert len(report.price_changes) == 1
        assert len(report.added) == 0
        assert len(report.removed) == 0


# ---------------------------------------------------------------------------
# Meta fields
# ---------------------------------------------------------------------------

class TestMetaFields:

    def test_ignore_meta_fields(self, detector):
        old = [
            _product(
                "Mouse", "$29.99",
                _relevance_score=0.9, _confidence=0.8,
            ),
        ]
        new = [
            _product(
                "Mouse", "$29.99",
                _relevance_score=0.7, _confidence=0.5,
            ),
        ]
        report = detector.compare(old, new)
        assert len(report.field_changes) == 0
        assert len(report.price_changes) == 0
        assert report.unchanged_count == 1


# ---------------------------------------------------------------------------
# Price alerts
# ---------------------------------------------------------------------------

class TestPriceAlerts:

    def test_price_alert_threshold(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        # ~1% change — below default 10% threshold
        new_snap[0]["price"] = "$30.29"
        # ~20% change — above threshold
        new_snap[1]["price"] = "$107.99"
        report = detector.compare(SNAPSHOT_A, new_snap)
        alerts = detector.get_price_alerts(report, threshold_pct=5.0)
        # Only the keyboard change (~20%) should trigger an alert
        assert len(alerts) == 1
        assert alerts[0].new_values["name"] == "Mechanical Keyboard"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:

    def test_empty_snapshots(self, detector):
        report = detector.compare([], [])
        assert len(report.added) == 0
        assert len(report.removed) == 0
        assert len(report.price_changes) == 0
        assert report.summary["added"] == 0
        assert report.summary["removed"] == 0

    def test_summary_counts(self, detector):
        new_snap = deepcopy(SNAPSHOT_A)
        new_snap[0]["price"] = "$39.99"
        new_snap.append(_product("New Item", "$9.99"))
        new_snap = [s for s in new_snap if s["name"] != "USB-C Hub"]
        report = detector.compare(SNAPSHOT_A, new_snap)
        s = report.summary
        assert s["added"] == 1
        assert s["removed"] == 1
        assert s["price_changes"] == 1
