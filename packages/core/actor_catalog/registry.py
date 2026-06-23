"""
Actor Catalog Registry — reads the generated hard-coded catalog.

All 27,753 actors are loaded once from the local JSON file.
No Apify API call is required for listing/searching.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

CATALOG_PATH = Path(__file__).parent / "generated" / "apify_actor_catalog.json"


@dataclass(frozen=True)
class ActorEntry:
    """Immutable actor catalog entry."""

    actor_id: str
    name: str
    title: str
    username: str
    developer: str
    url: str
    description: str
    categories: tuple[str, ...]
    pricing_model: str
    total_runs: int
    total_users: int
    rating: float | None
    review_count: int
    bookmarks: int
    created_at: str
    last_run_started_at: str
    implementation_status: str
    native_support_reason: str
    missing_components: str
    route_strategy: str
    source: str
    initials: str
    runnable_status: str

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> ActorEntry:
        return cls(
            actor_id=d["actor_id"],
            name=d["name"],
            title=d["title"],
            username=d.get("username", ""),
            developer=d.get("developer", d.get("username", "")),
            url=d.get("url", ""),
            description=d.get("description", ""),
            categories=tuple(d.get("categories", [])),
            pricing_model=d.get("pricing_model", "unknown"),
            total_runs=int(d.get("total_runs", 0) or 0),
            total_users=int(d.get("total_users", 0) or 0),
            rating=d.get("rating"),
            review_count=int(d.get("review_count", 0) or 0),
            bookmarks=int(d.get("bookmarks", 0) or 0),
            created_at=d.get("created_at", ""),
            last_run_started_at=d.get("last_run_started_at", ""),
            implementation_status=d.get("implementation_status", "mapped"),
            native_support_reason=d.get("native_support_reason", ""),
            missing_components=d.get("missing_components", ""),
            route_strategy=d.get("route_strategy", "unsupported"),
            source=d.get("source", ""),
            initials=d.get("initials", "??"),
            runnable_status=d.get("runnable_status", "blocked"),
        )


class ActorCatalog:
    """In-memory actor catalog backed by local generated JSON."""

    def __init__(self) -> None:
        self._actors: list[ActorEntry] = []
        self._by_id: dict[str, ActorEntry] = {}
        self._loaded = False

    def load(self, path: Path | None = None) -> None:
        """Load the catalog from disk. Idempotent."""
        if self._loaded:
            return
        catalog_path = path or CATALOG_PATH
        if not catalog_path.exists():
            logger.warning("Actor catalog not found at %s", catalog_path)
            self._loaded = True
            return
        with open(catalog_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        for raw in data.get("actors", []):
            entry = ActorEntry.from_dict(raw)
            self._actors.append(entry)
            self._by_id[entry.actor_id] = entry
        self._loaded = True
        logger.info("Loaded %d actors from catalog", len(self._actors))

    @property
    def total(self) -> int:
        self.load()
        return len(self._actors)

    def get(self, actor_id: str) -> ActorEntry | None:
        self.load()
        return self._by_id.get(actor_id)

    def search(
        self,
        *,
        query: str = "",
        category: str = "",
        developer: str = "",
        pricing_model: str = "",
        strategy: str = "",
        runnable: str = "",
        sort: str = "relevant",
        offset: int = 0,
        limit: int = 24,
    ) -> tuple[list[ActorEntry], int]:
        """Search and filter actors. Returns (page, total_matching)."""
        self.load()
        results = self._actors

        if query:
            q = query.lower()
            results = [
                a for a in results
                if q in a.title.lower()
                or q in a.name.lower()
                or q in a.description.lower()
            ]

        if category:
            cat = category.upper()
            results = [a for a in results if cat in a.categories]

        if developer:
            results = [a for a in results if a.developer == developer]

        if pricing_model:
            results = [a for a in results if a.pricing_model == pricing_model]

        if strategy:
            results = [a for a in results if a.route_strategy == strategy]

        if runnable:
            results = [a for a in results if a.runnable_status == runnable]

        if sort == "name":
            results = sorted(results, key=lambda a: a.title.lower())
        elif sort == "popular":
            results = sorted(results, key=lambda a: (a.total_users, a.total_runs), reverse=True)
        elif sort == "runs":
            results = sorted(results, key=lambda a: a.total_runs, reverse=True)
        elif sort == "rating":
            results = sorted(results, key=lambda a: (a.rating or 0, a.review_count), reverse=True)

        total = len(results)
        page = results[offset: offset + limit]
        return page, total

    def stats(self) -> dict[str, Any]:
        """Aggregate catalog statistics."""
        self.load()
        strategy_counts: dict[str, int] = {}
        category_counts: dict[str, int] = {}
        runnable_counts: dict[str, int] = {}
        developer_counts: dict[str, int] = {}
        pricing_counts: dict[str, int] = {}

        for a in self._actors:
            strategy_counts[a.route_strategy] = strategy_counts.get(a.route_strategy, 0) + 1
            runnable_counts[a.runnable_status] = runnable_counts.get(a.runnable_status, 0) + 1
            developer_counts[a.developer or "unknown"] = developer_counts.get(a.developer or "unknown", 0) + 1
            pricing_counts[a.pricing_model] = pricing_counts.get(a.pricing_model, 0) + 1
            for c in a.categories:
                category_counts[c] = category_counts.get(c, 0) + 1

        return {
            "total_actors": len(self._actors),
            "by_strategy": strategy_counts,
            "by_category": dict(sorted(category_counts.items(), key=lambda x: -x[1])),
            "by_runnable": runnable_counts,
            "by_developer": dict(sorted(developer_counts.items(), key=lambda x: (-x[1], x[0]))),
            "by_pricing_model": dict(sorted(pricing_counts.items(), key=lambda x: (-x[1], x[0]))),
        }

    def categories(self) -> list[str]:
        """Return sorted unique categories."""
        self.load()
        cats: set[str] = set()
        for a in self._actors:
            cats.update(a.categories)
        return sorted(cats)

    def developers(self) -> list[str]:
        """Return sorted unique developers."""
        self.load()
        return sorted({a.developer for a in self._actors if a.developer})

    def pricing_models(self) -> list[str]:
        """Return sorted unique pricing models."""
        self.load()
        return sorted({a.pricing_model for a in self._actors if a.pricing_model})


# Singleton instance
actor_catalog = ActorCatalog()
