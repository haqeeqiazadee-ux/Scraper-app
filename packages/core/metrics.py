"""
Lightweight metrics collector with Prometheus text exposition export.

Cloud-agnostic — no dependency on prometheus_client. Supports counters,
gauges, and histograms with optional labels. Metrics can be exported in
Prometheus text format (for /metrics scraping) or as a JSON dict (for
the web dashboard API).

Standard platform metrics are pre-registered at module level so that
any component can import ``metrics`` and start recording.
"""

from __future__ import annotations

import math
import threading
import time
from typing import Any


def _label_key(name: str, labels: dict[str, str] | None) -> str:
    """Return a unique key combining metric name and sorted label pairs."""
    if not labels:
        return name
    parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{name}{{{parts}}}"


def _label_suffix(labels: dict[str, str] | None) -> str:
    """Return the Prometheus label suffix (e.g. ``{status="ok"}``)."""
    if not labels:
        return ""
    parts = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
    return f"{{{parts}}}"


# Default histogram bucket boundaries (similar to Prometheus defaults).
DEFAULT_BUCKETS: tuple[float, ...] = (
    5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, float("inf"),
)


class MetricsCollector:
    """Lightweight metrics collector with Prometheus export format.

    Thread-safe — all mutations are protected by a lock.
    """

    def __init__(self, buckets: tuple[float, ...] | None = None) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, float] = {}
        self._gauges: dict[str, float] = {}
        # Histogram internals: observations, bucket counts, sum, count
        self._hist_observations: dict[str, list[float]] = {}
        self._hist_sum: dict[str, float] = {}
        self._hist_count: dict[str, int] = {}
        self._hist_buckets: dict[str, dict[float, int]] = {}
        # Metric name -> set of label key strings (for enumeration)
        self._counter_keys: dict[str, set[str]] = {}
        self._gauge_keys: dict[str, set[str]] = {}
        self._hist_keys: dict[str, set[str]] = {}
        # label key -> labels dict
        self._labels: dict[str, dict[str, str] | None] = {}
        # label key -> base name
        self._key_to_name: dict[str, str] = {}
        self._buckets = buckets or DEFAULT_BUCKETS

    # ------------------------------------------------------------------
    # Counter
    # ------------------------------------------------------------------

    def counter_inc(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a counter."""
        key = _label_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
            self._counter_keys.setdefault(name, set()).add(key)
            self._labels[key] = labels
            self._key_to_name[key] = name

    # ------------------------------------------------------------------
    # Gauge
    # ------------------------------------------------------------------

    def gauge_set(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Set a gauge value."""
        key = _label_key(name, labels)
        with self._lock:
            self._gauges[key] = value
            self._gauge_keys.setdefault(name, set()).add(key)
            self._labels[key] = labels
            self._key_to_name[key] = name

    def gauge_inc(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        """Increment a gauge."""
        key = _label_key(name, labels)
        with self._lock:
            self._gauges[key] = self._gauges.get(key, 0) + value
            self._gauge_keys.setdefault(name, set()).add(key)
            self._labels[key] = labels
            self._key_to_name[key] = name

    def gauge_dec(self, name: str, value: float = 1, labels: dict[str, str] | None = None) -> None:
        """Decrement a gauge."""
        self.gauge_inc(name, -value, labels)

    # ------------------------------------------------------------------
    # Histogram
    # ------------------------------------------------------------------

    def histogram_observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation.

        Bucket counts are cumulative — each bucket stores the total number
        of observations that are ``<= bound``.
        """
        key = _label_key(name, labels)
        with self._lock:
            self._hist_observations.setdefault(key, []).append(value)
            self._hist_sum[key] = self._hist_sum.get(key, 0.0) + value
            self._hist_count[key] = self._hist_count.get(key, 0) + 1
            if key not in self._hist_buckets:
                self._hist_buckets[key] = {b: 0 for b in self._buckets}
            for bound in self._buckets:
                if value <= bound:
                    self._hist_buckets[key][bound] += 1
            self._hist_keys.setdefault(name, set()).add(key)
            self._labels[key] = labels
            self._key_to_name[key] = name

    # ------------------------------------------------------------------
    # Export — Prometheus text format
    # ------------------------------------------------------------------

    def export_prometheus(self) -> str:
        """Export all metrics in Prometheus text exposition format."""
        lines: list[str] = []
        with self._lock:
            # Counters
            seen_counter_names: set[str] = set()
            for name, keys in sorted(self._counter_keys.items()):
                if name not in seen_counter_names:
                    lines.append(f"# HELP {name} Counter metric")
                    lines.append(f"# TYPE {name} counter")
                    seen_counter_names.add(name)
                for key in sorted(keys):
                    suffix = _label_suffix(self._labels.get(key))
                    lines.append(f"{name}{suffix} {self._counters[key]}")

            # Gauges
            seen_gauge_names: set[str] = set()
            for name, keys in sorted(self._gauge_keys.items()):
                if name not in seen_gauge_names:
                    lines.append(f"# HELP {name} Gauge metric")
                    lines.append(f"# TYPE {name} gauge")
                    seen_gauge_names.add(name)
                for key in sorted(keys):
                    suffix = _label_suffix(self._labels.get(key))
                    lines.append(f"{name}{suffix} {self._gauges[key]}")

            # Histograms
            seen_hist_names: set[str] = set()
            for name, keys in sorted(self._hist_keys.items()):
                if name not in seen_hist_names:
                    lines.append(f"# HELP {name} Histogram metric")
                    lines.append(f"# TYPE {name} histogram")
                    seen_hist_names.add(name)
                for key in sorted(keys):
                    labels = self._labels.get(key)
                    # Bucket counts are already cumulative from histogram_observe
                    for bound in sorted(b for b in self._buckets if not math.isinf(b)):
                        le_labels = dict(labels) if labels else {}
                        le_labels["le"] = str(int(bound) if bound == int(bound) else bound)
                        suffix = _label_suffix(le_labels)
                        lines.append(f"{name}_bucket{suffix} {self._hist_buckets[key].get(bound, 0)}")
                    # +Inf bucket
                    le_labels_inf = dict(labels) if labels else {}
                    le_labels_inf["le"] = "+Inf"
                    suffix_inf = _label_suffix(le_labels_inf)
                    lines.append(f"{name}_bucket{suffix_inf} {self._hist_count[key]}")
                    # sum and count
                    base_suffix = _label_suffix(labels)
                    lines.append(f"{name}_sum{base_suffix} {self._hist_sum[key]}")
                    lines.append(f"{name}_count{base_suffix} {self._hist_count[key]}")

        lines.append("")  # trailing newline
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Export — JSON
    # ------------------------------------------------------------------

    def export_json(self) -> dict[str, Any]:
        """Export all metrics as JSON."""
        result: dict[str, Any] = {"counters": {}, "gauges": {}, "histograms": {}}
        with self._lock:
            for key, val in sorted(self._counters.items()):
                result["counters"][key] = {
                    "value": val,
                    "labels": self._labels.get(key),
                }
            for key, val in sorted(self._gauges.items()):
                result["gauges"][key] = {
                    "value": val,
                    "labels": self._labels.get(key),
                }
            for key in sorted(self._hist_observations.keys()):
                obs = self._hist_observations[key]
                result["histograms"][key] = {
                    "count": self._hist_count[key],
                    "sum": self._hist_sum[key],
                    "labels": self._labels.get(key),
                }
                if obs:
                    result["histograms"][key]["min"] = min(obs)
                    result["histograms"][key]["max"] = max(obs)
                    result["histograms"][key]["avg"] = self._hist_sum[key] / self._hist_count[key]
        return result

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._hist_observations.clear()
            self._hist_sum.clear()
            self._hist_count.clear()
            self._hist_buckets.clear()
            self._counter_keys.clear()
            self._gauge_keys.clear()
            self._hist_keys.clear()
            self._labels.clear()
            self._key_to_name.clear()


# ---------------------------------------------------------------------------
# Global singleton
# ---------------------------------------------------------------------------
metrics = MetricsCollector()
