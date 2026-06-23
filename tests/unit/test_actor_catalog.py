"""Tests for the hard-coded actor catalog generation and registry."""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CATALOG_JSON = REPO_ROOT / "packages" / "core" / "actor_catalog" / "generated" / "apify_actor_catalog.json"
FRONTEND_JSON = REPO_ROOT / "apps" / "web" / "src" / "data" / "apifyActors.generated.json"
PUBLIC_CHUNKS_DIR = REPO_ROOT / "apps" / "web" / "public" / "data" / "actors"
GENERATOR_SCRIPT = REPO_ROOT / "scripts" / "generate_actor_catalog.py"
CSV_PATH = REPO_ROOT / "docs" / "apify_catalog_implementation_mapping.csv"

EXPECTED_ACTOR_COUNT = 27753


SECRET_PATTERNS = [
    re.compile(r"sk_live_[A-Za-z0-9_]+"),
    re.compile(r"sk_test_[A-Za-z0-9_]+"),
    re.compile(r"apify_api_[A-Za-z0-9_]+", re.IGNORECASE),
    re.compile(r"APIFY_API_KEY\s*[:=]\s*['\"][^'\"]+['\"]"),
    re.compile(r"Bearer\s+[A-Za-z0-9._-]{20,}"),
]


def assert_no_secret_patterns(path: Path) -> None:
    content = path.read_text(encoding="utf-8")
    for pattern in SECRET_PATTERNS:
        match = pattern.search(content)
        assert match is None, f"Secret-like pattern {pattern.pattern!r} found in {path}: {match.group(0)[:32]}"


class TestCatalogGeneration:
    """Tests for the catalog generator script output."""

    def test_backend_catalog_exists(self) -> None:
        assert CATALOG_JSON.exists(), f"Backend catalog not found at {CATALOG_JSON}"

    def test_frontend_catalog_exists(self) -> None:
        assert FRONTEND_JSON.exists(), f"Frontend catalog not found at {FRONTEND_JSON}"

    def test_backend_catalog_actor_count(self) -> None:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_actors"] == EXPECTED_ACTOR_COUNT
        assert len(data["actors"]) == EXPECTED_ACTOR_COUNT

    def test_frontend_catalog_actor_count(self) -> None:
        with open(FRONTEND_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total"] == EXPECTED_ACTOR_COUNT
        assert len(data["actors"]) == EXPECTED_ACTOR_COUNT

    def test_public_chunks_actor_count(self) -> None:
        with open(PUBLIC_CHUNKS_DIR / "index.json", "r", encoding="utf-8") as f:
            index = json.load(f)
        assert index["total"] == EXPECTED_ACTOR_COUNT
        assert index["chunk_count"] == 28

        chunk_total = 0
        for chunk in index["chunks"]:
            chunk_path = PUBLIC_CHUNKS_DIR / f"chunk-{chunk['index']}.json"
            with open(chunk_path, "r", encoding="utf-8") as f:
                rows = json.load(f)
            assert len(rows) == chunk["count"]
            chunk_total += len(rows)
        assert chunk_total == EXPECTED_ACTOR_COUNT

    def test_every_actor_has_required_fields(self) -> None:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        required = {
            "actor_id", "name", "title", "developer", "url", "route_strategy",
            "runnable_status", "categories", "pricing_model", "total_runs",
            "total_users", "rating", "review_count", "bookmarks",
        }
        for actor in data["actors"][:100]:  # Sample first 100
            missing = required - set(actor.keys())
            assert not missing, f"Actor {actor.get('actor_id', '?')} missing fields: {missing}"

    def test_store_metadata_is_enriched(self) -> None:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        actors = data["actors"]
        assert sum(1 for actor in actors if actor["url"].startswith("https://apify.com/")) == EXPECTED_ACTOR_COUNT
        assert len({actor["developer"] for actor in actors if actor["developer"]}) > 1000
        assert any(actor["rating"] is not None for actor in actors)

    def test_every_actor_has_valid_strategy(self) -> None:
        valid_strategies = {
            "native_pipeline", "apify_api", "yt_dlp",
            "job_board_schema", "real_estate_schema",
            "blocked_requires_auth_or_manual_review", "unsupported",
        }
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for actor in data["actors"]:
            assert actor["route_strategy"] in valid_strategies, (
                f"Actor {actor['actor_id']} has invalid strategy: {actor['route_strategy']}"
            )

    def test_no_duplicate_actor_ids(self) -> None:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = [a["actor_id"] for a in data["actors"]]
        assert len(ids) == len(set(ids)), "Duplicate actor IDs found"

    def test_actors_sorted_by_id(self) -> None:
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        ids = [a["actor_id"] for a in data["actors"]]
        assert ids == sorted(ids), "Actors should be sorted by actor_id"


class TestCatalogIdempotency:
    """Ensure re-running the generator produces identical output."""

    def test_generator_is_idempotent(self) -> None:
        if not GENERATOR_SCRIPT.exists() or not CSV_PATH.exists():
            pytest.skip("Generator script or CSV not available")

        # Hash current catalog
        with open(CATALOG_JSON, "rb") as f:
            backend_hash_before = hashlib.sha256(f.read()).hexdigest()
        with open(FRONTEND_JSON, "rb") as f:
            frontend_hash_before = hashlib.sha256(f.read()).hexdigest()
        with open(PUBLIC_CHUNKS_DIR / "index.json", "rb") as f:
            index_hash_before = hashlib.sha256(f.read()).hexdigest()

        # Re-run generator
        result = subprocess.run(
            [sys.executable, str(GENERATOR_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        assert result.returncode == 0, f"Generator failed: {result.stderr}"

        # Hash after re-generation — should differ only in generated_at timestamp
        with open(CATALOG_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_actors"] == EXPECTED_ACTOR_COUNT
        with open(CATALOG_JSON, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == backend_hash_before
        with open(FRONTEND_JSON, "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == frontend_hash_before
        with open(PUBLIC_CHUNKS_DIR / "index.json", "rb") as f:
            assert hashlib.sha256(f.read()).hexdigest() == index_hash_before


class TestCatalogSearch:
    """Test the in-memory catalog search/filter logic."""

    def test_registry_loads(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        assert catalog.total == EXPECTED_ACTOR_COUNT

    def test_search_by_query(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        results, total = catalog.search(query="linkedin", limit=10)
        assert total > 0
        assert len(results) <= 10
        for r in results:
            assert "linkedin" in r.title.lower() or "linkedin" in r.name.lower() or "linkedin" in r.description.lower()

    def test_filter_by_category(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        results, total = catalog.search(category="ECOMMERCE", limit=5)
        assert total > 0
        for r in results:
            assert "ECOMMERCE" in r.categories

    def test_filter_by_strategy(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        results, total = catalog.search(strategy="native_pipeline", limit=5)
        assert total > 0
        for r in results:
            assert r.route_strategy == "native_pipeline"

    def test_pagination(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        page1, total1 = catalog.search(offset=0, limit=10)
        page2, total2 = catalog.search(offset=10, limit=10)
        assert total1 == total2
        assert len(page1) == 10
        assert len(page2) == 10
        assert page1[0].actor_id != page2[0].actor_id

    def test_stats(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        s = catalog.stats()
        assert s["total_actors"] == EXPECTED_ACTOR_COUNT
        assert "native_pipeline" in s["by_strategy"]
        assert s["by_strategy"]["native_pipeline"] > 20000

    def test_categories_list(self) -> None:
        from packages.core.actor_catalog.registry import ActorCatalog

        catalog = ActorCatalog()
        catalog.load(CATALOG_JSON)
        cats = catalog.categories()
        assert len(cats) > 10
        assert "ECOMMERCE" in cats


class TestNoSecretLeakage:
    """Ensure generated catalog contains no secrets."""

    def test_no_api_keys_in_catalog(self) -> None:
        assert_no_secret_patterns(CATALOG_JSON)

    def test_no_api_keys_in_frontend_catalog(self) -> None:
        assert_no_secret_patterns(FRONTEND_JSON)
