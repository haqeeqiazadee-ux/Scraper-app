# API Reference — AI Scraping Platform Control Plane

**Base URL:** `http://localhost:8000/api/v1`
**Authentication:** Bearer JWT token via `Authorization` header
**Tenant Isolation:** `X-Tenant-ID` header (default: `default`)

---

## Health

### GET /health
Health check endpoint.

**Response 200:**
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "database": "connected"
}
```

---

## Authentication

### POST /api/v1/auth/token
Issue a JWT access token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response 200:**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 900
}
```

### GET /api/v1/auth/me
Get current authenticated user.

**Headers:** `Authorization: Bearer <token>`

**Response 200:**
```json
{
  "sub": "user@example.com",
  "tenant_id": "default",
  "roles": ["admin"]
}
```

---

## Tasks

### POST /api/v1/tasks
Create a new scraping task.

**Request Body:**
```json
{
  "url": "https://example.com/products",
  "task_type": "scrape",
  "policy_id": "uuid (optional)",
  "priority": 5,
  "schedule": "*/30 * * * * (optional cron)",
  "callback_url": "https://webhook.example.com (optional)",
  "metadata": {}
}
```

**Response 201:**
```json
{
  "id": "uuid",
  "tenant_id": "default",
  "url": "https://example.com/products",
  "task_type": "scrape",
  "priority": 5,
  "status": "pending",
  "created_at": "2026-03-22T00:00:00"
}
```

### GET /api/v1/tasks
List tasks with optional filtering.

**Query Parameters:**
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| status | string | null | Filter by status |
| limit | int | 50 | Page size |
| offset | int | 0 | Page offset |

**Response 200:**
```json
{
  "items": [{"id": "...", "url": "...", "status": "pending", ...}],
  "total": 100,
  "limit": 50,
  "offset": 0
}
```

### GET /api/v1/tasks/{task_id}
Get a single task by ID.

**Response 200:**
```json
{
  "id": "uuid",
  "tenant_id": "default",
  "url": "https://example.com/products",
  "task_type": "scrape",
  "policy_id": "uuid",
  "priority": 5,
  "schedule": null,
  "callback_url": null,
  "metadata": {},
  "status": "completed",
  "created_at": "2026-03-22T00:00:00",
  "updated_at": "2026-03-22T00:01:00"
}
```

### PATCH /api/v1/tasks/{task_id}
Update a task.

**Request Body (all fields optional):**
```json
{
  "status": "cancelled",
  "priority": 8,
  "schedule": "0 */6 * * *"
}
```

### POST /api/v1/tasks/{task_id}/cancel
Cancel a pending or running task.

**Response 200:**
```json
{"id": "uuid", "status": "cancelled"}
```

**Error 400:** Task already completed or cancelled.

### POST /api/v1/tasks/{task_id}/execute
Execute a task through the routing pipeline.

**Response 200:**
```json
{
  "task_id": "uuid",
  "route_decision": {
    "lane": "http",
    "reason": "Default: try HTTP lane first",
    "fallback_lanes": ["browser", "hard_target"],
    "confidence": 0.5
  }
}
```

---

## Routing

### POST /api/v1/route
Dry-run routing — determine which lane a URL would be routed to.

**Request Body:**
```json
{
  "url": "https://example.com/products",
  "policy_id": "uuid (optional)"
}
```

**Response 200:**
```json
{
  "lane": "http",
  "reason": "Default: try HTTP lane first",
  "fallback_lanes": ["browser", "hard_target"],
  "confidence": 0.5
}
```

---

## Policies

### POST /api/v1/policies
Create an extraction policy.

**Request Body:**
```json
{
  "name": "E-commerce Default",
  "target_domains": ["example.com"],
  "preferred_lane": "auto",
  "extraction_rules": {},
  "rate_limit": {
    "max_requests_per_minute": 60,
    "max_requests_per_hour": 1000,
    "max_concurrent": 5
  },
  "proxy_policy": {
    "enabled": true,
    "rotation_strategy": "weighted"
  },
  "session_policy": {
    "reuse_sessions": true,
    "max_session_age_minutes": 30
  },
  "retry_policy": {
    "max_retries": 3,
    "backoff_base_seconds": 2.0,
    "retry_on_status_codes": [429, 500, 502, 503, 504]
  },
  "timeout_ms": 30000,
  "robots_compliance": true
}
```

### GET /api/v1/policies
List policies.

### GET /api/v1/policies/{policy_id}
Get a policy by ID.

### PATCH /api/v1/policies/{policy_id}
Update a policy.

### DELETE /api/v1/policies/{policy_id}
Delete a policy.

---

## Results

### GET /api/v1/results?task_id={task_id}
Get extraction results for a task.

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "task_id": "uuid",
      "url": "https://example.com/products",
      "extracted_data": [
        {
          "name": "Product A",
          "price": "29.99",
          "image_url": "https://...",
          "product_url": "https://..."
        }
      ],
      "item_count": 1,
      "confidence": 0.85,
      "extraction_method": "deterministic",
      "created_at": "2026-03-22T00:01:00"
    }
  ]
}
```

### GET /api/v1/results/{result_id}/artifacts
Get artifacts (HTML snapshots, screenshots, exports) for a result.

**Response 200:**
```json
{
  "items": [
    {
      "id": "uuid",
      "artifact_type": "html_snapshot",
      "storage_path": "artifacts/...",
      "content_type": "text/html",
      "size_bytes": 45000,
      "created_at": "2026-03-22T00:01:00"
    }
  ]
}
```

---

## Metrics

### GET /metrics
Prometheus text format metrics.

### GET /api/v1/metrics
JSON format metrics for dashboard.

**Response 200:**
```json
{
  "counters": {"scraper_tasks_total": 150},
  "gauges": {"scraper_tasks_active": 3},
  "histograms": {"scraper_request_duration_ms": [120, 340, 500]}
}
```

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Human-readable error message"
}
```

| Status | Meaning |
|--------|---------|
| 400 | Bad request (invalid input) |
| 401 | Unauthorized (invalid/expired token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 422 | Validation error (Pydantic) |
| 429 | Rate limited |
| 500 | Internal server error |

---

## Rate Limiting

Rate limits are enforced per-tenant based on the policy configuration.
Default: 60 requests/minute, 1000 requests/hour.

## Pagination

List endpoints support `limit` and `offset` query parameters.
Response includes `total` count for client-side pagination.
