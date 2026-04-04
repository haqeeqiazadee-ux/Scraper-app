"""Full API endpoint E2E tests."""
import pytest
import httpx

BASE = "http://localhost:8765/api/v1"


@pytest.fixture
def api():
    """Simple sync httpx client for API testing."""
    with httpx.Client(base_url=BASE, timeout=30) as client:
        yield client


# --- Health ---
def test_health_endpoint(api):
    r = api.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] in ("healthy", "ok")


def test_ready_endpoint(api):
    r = api.get("/ready")
    assert r.status_code == 200


# --- Tasks CRUD ---
def test_create_task(api):
    r = api.post("/tasks", json={"url": "https://example.com", "tenant_id": "test"})
    assert r.status_code in (200, 201)
    data = r.json()
    assert "id" in data


def test_list_tasks(api):
    r = api.get("/tasks")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data or isinstance(data, list)


def test_get_task(api):
    # Create first
    cr = api.post("/tasks", json={"url": "https://example.com", "tenant_id": "test"})
    task_id = cr.json().get("id")
    if task_id:
        r = api.get(f"/tasks/{task_id}")
        assert r.status_code == 200


# --- Policies CRUD ---
def test_create_policy(api):
    r = api.post("/policies", json={"name": "test-policy", "tenant_id": "test"})
    assert r.status_code in (200, 201)


def test_list_policies(api):
    r = api.get("/policies")
    assert r.status_code == 200


# --- Results ---
def test_list_results(api):
    r = api.get("/results")
    assert r.status_code == 200


# --- Templates ---
def test_list_templates(api):
    r = api.get("/templates")
    assert r.status_code == 200


def test_template_categories(api):
    r = api.get("/templates/categories")
    assert r.status_code == 200


# --- Crawl ---
def test_crawl_start(api):
    r = api.post("/crawl", json={"seed_urls": ["https://example.com"], "max_depth": 1, "max_pages": 1})
    assert r.status_code in (200, 201)


def test_crawl_get_unknown(api):
    r = api.get("/crawl/nonexistent-id")
    assert r.status_code == 404


# --- Search ---
def test_search_endpoint(api):
    r = api.post("/search", json={"query": "test", "max_results": 1})
    # May return 503 if no Brave API key
    assert r.status_code in (200, 503)


# --- Extract ---
def test_extract_endpoint(api):
    r = api.post("/extract", json={"url": "https://example.com"})
    assert r.status_code in (200, 422)


# --- Schedules ---
def test_list_schedules(api):
    r = api.get("/schedules")
    assert r.status_code == 200


# --- Metrics ---
def test_metrics_endpoint(api):
    r = api.get("/metrics")
    assert r.status_code == 200


# --- Sessions ---
def test_list_sessions(api):
    r = api.get("/sessions")
    assert r.status_code == 200


# --- Webhooks ---
def test_list_webhooks(api):
    r = api.get("/webhooks/history")
    assert r.status_code == 200


# --- 404 ---
def test_unknown_endpoint(api):
    r = api.get("/nonexistent")
    assert r.status_code in (404, 405)
