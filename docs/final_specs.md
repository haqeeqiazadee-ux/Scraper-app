# Final Specs — AI Scraping Platform

> **Status:** IN PROGRESS
> **Last Updated:** 2026-03-22
> **Version:** 1.0-draft

---

## 1. Product Vision

### What the Platform Is

A production-grade, cloud-agnostic AI-powered web scraping platform. It provides a unified routing and extraction engine that can be deployed as:

- A **cloud SaaS** product (multi-tenant, managed)
- A **self-hosted** deployment (single-tenant, on-premise or private cloud)
- A **Windows desktop application** (local or hybrid mode)
- A **browser extension** (cloud-connected or local-companion mode)
- An **API service** for third-party integration

### Who It Is For

- SaaS operators running scraping-as-a-service
- Enterprise teams needing self-hosted data extraction
- Solo users running desktop scraping jobs
- Developers integrating scraping into their own applications
- Browser-extension users doing lightweight assisted scraping

### Why the EXE and Extension Are Alternate Front Ends

The Windows EXE and browser extension are **runtime shells**, not separate products. They share:

- One core extraction engine
- One task schema
- One policy/routing layer
- One result model
- One session model
- One connector contract
- One storage contract
- One observability model

They differ only in runtime privileges, UX surface, and deployment context. This prevents architectural drift and ensures all runtime modes benefit from the same improvements.

### Existing Codebase Assessment

The current codebase ("Scrapling Pro v3.0") is a monolithic Python scraper with valuable components:

| Component | Reusability | Notes |
|-----------|-------------|-------|
| core/fallback_chain.py | HIGH | Pure Python, zero deps, core pattern |
| core/smart_extractors.py | HIGH | Serializable data structures |
| proxy_manager.py | HIGH | Platform-independent |
| scheduler.py | HIGH | Cron parsing, job management |
| smart_exporter.py | HIGH | Excel/JSON export logic |
| integrations.py | HIGH | Modular tool wrappers |
| verticals.py | HIGH | Domain-specific logic |
| templates.py | HIGH | Selector patterns |
| ajax_handler.py | HIGH | Browser automation logic |
| async_scraper.py | HIGH | Threading, progress tracking |
| ai_scraper_v3.py | HIGH | AI extraction (needs provider abstraction) |
| engine_v2.py | MEDIUM | Tightly coupled to Scrapling fetchers |
| engine.py | MEDIUM | Same — needs fetcher abstraction |
| auth_scraper.py | MEDIUM | Playwright-dependent |
| web_dashboard.py | MEDIUM | Flask-specific, needs decoupling |

**Key refactoring needs:**
1. Abstract Scrapling fetcher dependency into a pluggable Fetcher interface
2. Abstract Playwright into a Browser interface
3. Decouple Flask web layer from scraping logic
4. Abstract AI provider (currently hardcoded to Google Gemini)
5. Add storage abstraction (currently file-system only)

---

## 2. Goals and Non-Goals

### Goals

1. **Unified core engine** — One extraction platform powering all runtime modes
2. **Cloud-agnostic deployment** — Run on AWS, GCP, Azure, or bare metal without vendor lock-in
3. **Multi-tenant SaaS** — Tenant isolation, quotas, usage tracking, billing hooks
4. **Self-hosted parity** — Same capabilities as SaaS, minus multi-tenancy overhead
5. **Desktop application** — Windows EXE via Tauri shell over the shared core
6. **Browser extension** — Chrome-compatible extension connected to cloud or local companion
7. **API-first design** — Every capability accessible via REST/GraphQL API
8. **AI-assisted extraction** — AI for routing, repair, normalization — not as default extraction for every page
9. **Production-grade reliability** — Retry logic, fallback chains, health scoring, circuit breakers
10. **Strong observability** — Structured logs, metrics, distributed traces, task lineage

### Non-Goals

1. Building a general-purpose web crawler (focused on structured data extraction)
2. Replacing deterministic engineering with AI for every extraction task
3. Supporting mobile apps as a runtime shell (desktop + browser + cloud only)
4. Building a full e-commerce platform (we extract data, not sell products)
5. Real-time streaming extraction (batch and near-real-time are in scope)
6. Supporting browsers other than Chromium-based for the extension (initially)

---

## 3. Core Architecture Principles

1. **One shared platform** — EXE, extension, SaaS, and self-hosted all share the same core engine, schemas, and contracts
2. **Cloud-agnostic** — No hard dependencies on AWS/GCP/Azure services; use abstractions (e.g., object storage interface, queue interface)
3. **AI as augmentation** — AI handles routing decisions, extraction repair, schema normalization, and deduplication; deterministic parsers handle known patterns
4. **Pluggable connectors** — APIs, HTTP collectors, browser workers, proxy adapters, CAPTCHA adapters are all swappable
5. **Contract-driven** — All components communicate through shared schemas (task, policy, session, run, result, artifact)
6. **Defense in depth** — Fallback chains at every layer (primary → secondary → tertiary)
7. **Observability-first** — Every operation emits structured logs, metrics, and trace spans
8. **Minimal viable abstraction** — Don't abstract until there are two concrete implementations; keep it simple

---

## 4. User Personas

### 4.1 SaaS Operator
- Runs the platform as a managed service
- Needs multi-tenant isolation, billing, usage dashboards
- Manages infrastructure, scaling, and uptime
- Monitors system health and cost

### 4.2 Self-Hosted Enterprise Operator
- Deploys on private infrastructure (on-prem or private cloud)
- Needs single-tenant mode with full admin control
- Requires data residency compliance
- Manages own infrastructure and updates

### 4.3 Solo Desktop User
- Runs Windows EXE for local scraping tasks
- May or may not have internet connectivity
- Needs simple UI, local storage, Excel/JSON export
- May connect to cloud for AI features (hybrid mode)

### 4.4 Browser-Extension-Assisted User
- Uses Chrome extension for lightweight, page-level scraping
- Connected to cloud backend for AI and storage
- OR connected to local companion for offline operation
- Needs one-click extraction from current page

### 4.5 Developer / Integrator
- Integrates scraping into their own application via API
- Needs clear API documentation, SDKs, webhook support
- Cares about reliability, rate limits, and error handling
- May self-host or use SaaS

---

## 5. Runtime Modes

### 5.1 Cloud SaaS
- Full platform running on public cloud
- Multi-tenant with tenant isolation
- Managed browser workers, proxy pools, AI services
- API + web dashboard access
- Usage-based billing

### 5.2 Self-Hosted
- Same platform deployed on customer infrastructure
- Single-tenant (or internal multi-tenant)
- Customer manages infra (Docker Compose or Kubernetes)
- No billing layer; admin-controlled quotas
- Full data sovereignty

### 5.3 Windows EXE — Local Mode
- Tauri-based desktop app wrapping the core engine
- Runs entirely locally (no cloud dependency)
- Local browser automation (bundled Chromium)
- Local storage (SQLite + filesystem)
- AI features require internet (API calls to Gemini/OpenAI)

### 5.4 Windows EXE — Hybrid Mode
- Desktop app connected to cloud backend
- Local browser for fetching, cloud for AI/storage/scheduling
- Syncs tasks and results with cloud account
- Fallback to local-only if cloud unreachable

### 5.5 Browser Extension — Cloud-Connected Mode
- Chrome extension sending tasks to cloud backend
- Extension captures page context, cloud processes extraction
- Results stored in cloud, viewable in dashboard
- Requires cloud account and API key

### 5.6 Browser Extension — Local-Companion Mode
- Chrome extension communicating with local EXE via native messaging
- EXE acts as local processing backend
- No cloud dependency
- Results stored locally

---

## 6. System Architecture

### 6.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        RUNTIME SHELLS                            │
│  ┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────────┐  │
│  │ Web App  │  │ Win EXE  │  │ Extension │  │  API Client   │  │
│  │ (React)  │  │ (Tauri)  │  │ (Chrome)  │  │  (REST/SDK)   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └──────┬────────┘  │
│       └──────────────┼──────────────┼───────────────┘            │
│                      ▼                                           │
├──────────────────────────────────────────────────────────────────┤
│                    CONTROL PLANE (FastAPI)                        │
│  ┌────────────┐  ┌────────────┐  ┌─────────────┐  ┌──────────┐ │
│  │ Task API   │  │ Policy API │  │ Session API  │  │ Admin API│ │
│  └────────────┘  └────────────┘  └─────────────┘  └──────────┘ │
├──────────────────────────────────────────────────────────────────┤
│                    EXECUTION ROUTER                               │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  Route tasks to execution lanes based on policy + site   │    │
│  └──────────────────────────────────────────────────────────┘    │
├──────────────────────────────────────────────────────────────────┤
│                    EXECUTION LANES                                │
│  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌──────────────────┐  │
│  │ API/Feed │ │  HTTP    │ │  Browser  │ │   Hard-Target    │  │
│  │  Lane    │ │  Lane    │ │   Lane    │ │     Lane         │  │
│  └──────────┘ └──────────┘ └───────────┘ └──────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│                    CONNECTOR LAYER                                │
│  ┌────────┐ ┌────────────┐ ┌─────────┐ ┌───────┐ ┌──────────┐ │
│  │  API   │ │    HTTP    │ │ Browser │ │ Proxy │ │ CAPTCHA  │ │
│  │Adapters│ │ Collectors │ │ Workers │ │Adapters│ │ Adapters │ │
│  └────────┘ └────────────┘ └─────────┘ └───────┘ └──────────┘ │
├──────────────────────────────────────────────────────────────────┤
│                 NORMALIZATION LAYER                               │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────────┐   │
│  │ Schema Mapping │  │  AI Repair     │  │  Deduplication   │   │
│  └────────────────┘  └────────────────┘  └──────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                    STORAGE LAYER                                  │
│  ┌────────────┐  ┌────────────────┐  ┌──────────────────────┐   │
│  │ PostgreSQL │  │ Object Storage │  │  Redis/Valkey Cache  │   │
│  │ (metadata) │  │  (artifacts)   │  │  (queue + sessions)  │   │
│  └────────────┘  └────────────────┘  └──────────────────────┘   │
├──────────────────────────────────────────────────────────────────┤
│                    OBSERVABILITY                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐   │
│  │   Logs   │  │ Metrics  │  │  Traces  │  │ Task Lineage  │   │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 6.2 Control Plane

The control plane is a **FastAPI** application that serves as the central coordination layer.

**Responsibilities:**
- Accept task submissions (API, dashboard, extension, EXE)
- Enforce policies (rate limits, allowed domains, quotas)
- Route tasks to appropriate execution lanes
- Manage sessions, proxies, and browser pools
- Serve results and artifacts
- Handle tenant management and auth

**Key endpoints:**
- `POST /api/v1/tasks` — Submit a scraping task
- `GET /api/v1/tasks/{id}` — Get task status/result
- `POST /api/v1/tasks/{id}/cancel` — Cancel a task
- `GET /api/v1/runs/{id}` — Get run details
- `POST /api/v1/policies` — Create/update extraction policy
- `GET /api/v1/sessions` — List active sessions
- `POST /api/v1/export` — Export results
- `GET /api/v1/health` — Health check

**For local/EXE mode:** The control plane runs as an embedded HTTP server (uvicorn) on localhost.

### 6.3 Execution Router

The router decides which execution lane handles a task:

1. **Check for API/feed availability** — If the target has a known API or data feed, use the API lane
2. **Check site profile** — If the site is known to require JavaScript, use browser lane
3. **Default to HTTP lane** — Try lightweight HTTP fetch first
4. **Escalate to browser lane** — If HTTP fails or returns incomplete data
5. **Escalate to hard-target lane** — If browser lane hits anti-bot protection
6. **AI routing** — AI can recommend lane based on URL pattern and historical success

**Routing data sources:**
- Site profiles (stored in DB, updated by operators)
- Historical success rates per site per lane
- AI classifier (URL → likely best lane)

### 6.4 Connector Layer

All external interactions go through connector adapters with a unified interface:

```python
class Connector(Protocol):
    async def fetch(self, request: FetchRequest) -> FetchResponse: ...
    async def health_check(self) -> bool: ...
    def get_metrics(self) -> ConnectorMetrics: ...
```

Connector types:
- **API Connectors** — REST/GraphQL calls to known APIs (Shopify, WooCommerce, etc.)
- **HTTP Collectors** — Lightweight HTTP requests with stealth headers
- **Browser Workers** — Playwright-based browser automation
- **Proxy Adapters** — Route requests through proxy pools
- **CAPTCHA Adapters** — Solve CAPTCHAs via 2Captcha, Anti-Captcha, etc.
- **Unlocker Adapters** — Third-party anti-bot bypass services

### 6.5 Normalization Layer

Raw extraction results are normalized before storage:

1. **Schema mapping** — Map extracted fields to the canonical result schema
2. **AI repair** — Fix malformed data (truncated prices, garbled text, missing fields)
3. **Deduplication** — Detect and merge duplicate records
4. **Validation** — Enforce data type constraints and required fields

Reuses existing: `core/smart_extractors.py` data structures, `core/fallback_chain.py` pattern

### 6.6 Storage Layer

| Store | Technology | Purpose | Local Alternative |
|-------|-----------|---------|-------------------|
| Metadata | PostgreSQL | Tasks, runs, results, tenants, policies | SQLite |
| Artifacts | S3-compatible object storage | HTML snapshots, screenshots, exports | Local filesystem |
| Queue/Cache | Redis / Valkey | Task queue, session cache, rate limiting | In-memory / SQLite |

Storage is accessed through abstract interfaces so that cloud and local modes use the same code paths with different backends.

### 6.7 Runtime Shells

Each runtime shell is a thin wrapper that:
1. Presents a UI appropriate to the context
2. Submits tasks to the control plane (remote or embedded)
3. Displays results

| Shell | Technology | Control Plane | Storage |
|-------|-----------|---------------|---------|
| Web Dashboard | React + Vite | Remote (cloud/self-hosted) | Remote |
| Windows EXE | Tauri (Rust + WebView) | Embedded (localhost) | Local (SQLite + FS) |
| Browser Extension | Chrome Extension API | Remote OR local companion | Remote OR local |
| API Client | REST/SDK | Remote | Remote |

---

## 7. Shared Data Contracts

All components communicate through these shared schemas. They are defined as Pydantic models in `packages/contracts/`.

### 7.1 Task Schema

```python
class Task:
    id: UUID
    tenant_id: str
    url: str                        # Target URL
    task_type: Literal["scrape", "monitor", "extract"]
    policy_id: Optional[UUID]       # Extraction policy to apply
    priority: int                   # 0=low, 10=critical
    schedule: Optional[str]         # Cron expression for recurring
    callback_url: Optional[str]     # Webhook for completion
    metadata: dict                  # User-defined key-value pairs
    created_at: datetime
    status: Literal["pending", "queued", "running", "completed", "failed", "cancelled"]
```

### 7.2 Policy Schema

```python
class Policy:
    id: UUID
    tenant_id: str
    name: str
    target_domains: list[str]       # Domains this policy applies to
    preferred_lane: Optional[str]   # "api", "http", "browser", "hard_target"
    extraction_rules: dict          # Field mappings, selectors, AI instructions
    rate_limit: RateLimit           # Max requests per time window
    proxy_policy: ProxyPolicy       # Proxy requirements (geo, type, rotation)
    session_policy: SessionPolicy   # Session reuse rules
    retry_policy: RetryPolicy       # Max retries, backoff strategy
    timeout_ms: int                 # Max time per request
    robots_compliance: bool         # Respect robots.txt
    created_at: datetime
    updated_at: datetime
```

### 7.3 Session Schema

```python
class Session:
    id: UUID
    tenant_id: str
    domain: str
    session_type: Literal["http", "browser", "authenticated"]
    cookies: dict
    headers: dict
    proxy_id: Optional[UUID]        # Sticky proxy assignment
    browser_profile_id: Optional[str]
    health_score: float             # 0.0 to 1.0
    created_at: datetime
    last_used_at: datetime
    expires_at: Optional[datetime]
    request_count: int
    success_count: int
    failure_count: int
    status: Literal["active", "degraded", "expired", "invalidated"]
```

### 7.4 Run Schema

```python
class Run:
    id: UUID
    task_id: UUID
    tenant_id: str
    lane: str                       # Which execution lane was used
    connector: str                  # Which connector handled it
    session_id: Optional[UUID]
    proxy_used: Optional[str]
    attempt: int                    # Retry attempt number
    started_at: datetime
    completed_at: Optional[datetime]
    duration_ms: int
    status: Literal["running", "success", "failed", "timeout", "blocked"]
    status_code: Optional[int]      # HTTP status code
    error: Optional[str]
    bytes_downloaded: int
    ai_tokens_used: int
```

### 7.5 Result Schema

```python
class Result:
    id: UUID
    task_id: UUID
    run_id: UUID
    tenant_id: str
    url: str
    extracted_data: list[dict]      # List of extracted items
    item_count: int
    schema_version: str
    confidence: float               # Extraction confidence 0.0-1.0
    extraction_method: str          # "deterministic", "ai", "hybrid", "fallback"
    normalization_applied: bool
    dedup_applied: bool
    created_at: datetime
    artifacts: list[UUID]           # References to stored artifacts
```

### 7.6 Artifact Schema

```python
class Artifact:
    id: UUID
    result_id: UUID
    tenant_id: str
    artifact_type: Literal["html_snapshot", "screenshot", "export_xlsx", "export_json", "export_csv"]
    storage_path: str               # Object storage key
    content_type: str               # MIME type
    size_bytes: int
    checksum: str                   # SHA-256
    created_at: datetime
    expires_at: Optional[datetime]  # TTL for auto-cleanup
```

### 7.7 Billing / Quota Schema

```python
class TenantQuota:
    tenant_id: str
    plan: str                       # "free", "starter", "pro", "enterprise"
    max_tasks_per_day: int
    max_concurrent_tasks: int
    max_browser_minutes_per_day: int
    max_ai_tokens_per_day: int
    max_storage_bytes: int
    max_proxy_requests_per_day: int
    current_usage: UsageCounters    # Rolling counters
    billing_cycle_start: date
    billing_cycle_end: date

class UsageCounters:
    tasks_today: int
    browser_minutes_today: float
    ai_tokens_today: int
    storage_bytes_used: int
    proxy_requests_today: int
```

---

## 8. Execution Lanes

### 8.1 API / Feed Lane
- **When:** Target has a known API (Shopify, WooCommerce, RSS feeds, JSON endpoints)
- **How:** Direct API calls using API connectors
- **Advantages:** Fastest, most reliable, structured data
- **Reuse from existing:** `integrations.py` (ShopifyIntegration, WooCommerceIntegration)

### 8.2 HTTP Lane
- **When:** Target serves static or server-rendered HTML
- **How:** HTTP GET with stealth headers, parse HTML with CSS selectors / schema.org extractors
- **Advantages:** Fast, low resource usage, no browser needed
- **Fallback chain:** extruct (JSON-LD) → BeautifulSoup → CSS selectors → regex
- **Reuse from existing:** `core/smart_extractors.py`, `core/fallback_chain.py`, `engine.py` StealthyFetcher

### 8.3 Browser Lane
- **When:** Target requires JavaScript rendering, dynamic content, or interaction
- **How:** Playwright browser automation with stealth plugins
- **Supports:** Infinite scroll, load-more buttons, AJAX pagination, lazy loading, tab switching
- **Reuse from existing:** `ajax_handler.py`, `engine_v2.py` PlayWrightFetcher, `auth_scraper.py`

### 8.4 Hard-Target Lane
- **When:** Target has aggressive anti-bot protection (Cloudflare, DataDome, PerimeterX)
- **How:** Unlocker services, residential proxies, CAPTCHA solving, browser fingerprint rotation
- **Escalation:** Browser lane → add residential proxy → add CAPTCHA solver → use unlocker service
- **Reuse from existing:** `proxy_manager.py`, `engine_v2.py` CaptchaSolver

### 8.5 AI Normalization Lane
- **When:** After extraction, raw data needs repair, normalization, or schema mapping
- **How:** AI models (Gemini, OpenAI, local) process extracted data
- **Tasks:** Fix truncated fields, normalize prices/dates, map to canonical schema, deduplicate
- **Reuse from existing:** `ai_scraper_v3.py` GeminiAI extraction logic

### 8.6 Lane Selection Logic

```
1. Check policy.preferred_lane → if set, use it
2. Check site_profile(url) → if API available, use API lane
3. Try HTTP lane first (fast, cheap)
4. If HTTP returns incomplete/empty → escalate to Browser lane
5. If Browser hits anti-bot → escalate to Hard-Target lane
6. After extraction → run through AI Normalization if confidence < threshold
```

---

## 9. Connector Strategy

### 9.1 API Connectors
- REST and GraphQL adapters for known platforms
- Auto-authentication (API keys, OAuth)
- Rate limit awareness per API
- **Initial targets:** Shopify, WooCommerce, RSS/Atom feeds

### 9.2 HTTP Collectors
- Lightweight HTTP client with stealth headers
- User-agent rotation, header randomization
- Cookie jar management
- Redirect following with loop detection
- Response caching for dedup
- **Implementation:** httpx async client with custom middleware

### 9.3 Browser Workers
- Playwright-based browser pool
- Managed browser profiles with fingerprint rotation
- Page lifecycle management (navigate → wait → interact → extract → close)
- Screenshot capture for debugging
- Console log capture
- **Reuse from existing:** Scrapling's StealthyFetcher, PlayWrightFetcher patterns

### 9.4 Proxy Adapters
- Unified proxy interface supporting HTTP, HTTPS, SOCKS5
- Vendor-agnostic (works with any proxy provider)
- Health checking, scoring, and auto-rotation
- Geo-targeting support
- Session stickiness for stateful scraping
- **Reuse from existing:** `proxy_manager.py` AdvancedProxyManager (highly reusable)

### 9.5 CAPTCHA Adapters
- Support for 2Captcha, Anti-Captcha, CapMonster
- reCAPTCHA v2/v3, hCaptcha, image CAPTCHA
- Cost tracking per solve
- Auto-escalation: try cheaper service first
- **Reuse from existing:** `engine_v2.py` CaptchaSolver

### 9.6 Unlocker Adapters
- Integration with anti-bot bypass services (ScrapingBee, Bright Data, etc.)
- Last resort when browser + proxy + CAPTCHA isn't enough
- Cost-aware routing (only use when cheaper options fail)

---

## 10. Session Model

### 10.1 Session Lifecycle

```
Created → Active → Degraded → Expired/Invalidated
           ↑          │
           └──────────┘ (recovery possible)
```

- **Created:** New session with fresh cookies/headers
- **Active:** Healthy, used for requests, health_score > 0.7
- **Degraded:** Experiencing failures, health_score 0.3-0.7, still usable with caution
- **Expired:** TTL exceeded or manually expired
- **Invalidated:** Detected as blocked/banned, cannot be reused

### 10.2 Proxy Affinity
- Sessions can be bound to a specific proxy (sticky sessions)
- Required for sites that validate IP consistency within a session
- Proxy change triggers session rotation

### 10.3 Cookie Persistence
- Cookies stored in session record (encrypted at rest)
- Refreshed on each successful request
- Expired cookies trigger session refresh or rotation
- **Reuse from existing:** `auth_scraper.py` SessionData

### 10.4 Browser Profile Reuse
- Browser profiles (cookies, localStorage, fingerprint) can be persisted
- Reduces detection risk vs. fresh profiles every time
- Profiles rotated on a schedule or after detection signals

### 10.5 Health Scoring

```
health_score = (success_rate * 0.6) + (response_time_score * 0.2) + (age_score * 0.2)

success_rate = success_count / total_count
response_time_score = 1.0 - (avg_response_ms / max_acceptable_ms)
age_score = 1.0 - (age_hours / max_session_hours)
```

### 10.6 Invalidation Rules
- 3 consecutive failures → mark as degraded
- 5 consecutive failures → invalidate
- HTTP 403/429 with ban indicators → immediate invalidation
- CAPTCHA challenge on previously clean session → degrade
- Session age > max TTL → expire

---

## 11. Proxy and CAPTCHA Strategy

### 11.1 Proxy Vendor Abstraction

```python
class ProxyProvider(Protocol):
    async def get_proxy(self, geo: Optional[str] = None) -> Proxy: ...
    async def mark_success(self, proxy: Proxy) -> None: ...
    async def mark_failure(self, proxy: Proxy) -> None: ...
    async def refresh(self) -> None: ...
```

Supports: file-based lists, API-based providers, inline configuration.
**Reuse:** `proxy_manager.py` ProxyProvider, FileProxyProvider, APIProxyProvider

### 11.2 Proxy Rotation Strategies
- **Round-robin:** Sequential, even distribution
- **Weighted:** Prefer high-success-rate proxies
- **Geo-targeted:** Select proxy by country/region
- **Sticky:** Maintain same proxy for session duration
- **Random:** Random selection from healthy pool

### 11.3 Fallback Model
1. Try without proxy (if site allows)
2. Try datacenter proxy (cheap, fast)
3. Try residential proxy (more expensive, less detectable)
4. Try mobile proxy (most expensive, hardest to detect)
5. Try unlocker service (last resort)

### 11.4 CAPTCHA Strategy
- **When to solve:** CAPTCHA challenge detected in response
- **When to escalate:** Solver fails 2+ times → try different solver → try different proxy → abandon
- **When to abandon:** Cost per solve exceeds configured threshold, or 3 failed attempts across solvers
- **Cost tracking:** Log cost per CAPTCHA solve, alert on spend spikes

---

## 12. AI Strategy

### 12.1 AI for Routing Intelligence
- Classify URLs to predict best execution lane
- Learn from historical success/failure per site
- Suggest optimal proxy type and session strategy
- **Model:** Lightweight classifier, can run locally or via API

### 12.2 AI for Extraction Repair
- Fix truncated or malformed extracted data
- Infer missing fields from context (e.g., currency from domain)
- Clean HTML artifacts from text fields
- **Trigger:** Only when deterministic extraction produces low-confidence results

### 12.3 AI for Schema Normalization
- Map heterogeneous extracted fields to canonical schema
- Handle variations (e.g., "cost" → "price", "product_name" → "name")
- Normalize units, currencies, date formats
- **Reuse from existing:** `ai_scraper_v3.py` extraction prompt patterns

### 12.4 AI for Deduplication / Entity Assistance
- Detect duplicate products across different sources
- Entity resolution (same product, different names/SKUs)
- Merge records with complementary data

### 12.5 What AI Must NOT Be Used For
- **Default extraction for every page** — Deterministic parsers (CSS, JSON-LD, regex) are faster, cheaper, and more reliable for known patterns
- **Real-time decision-making in hot paths** — AI adds latency; routing decisions should be cached
- **Security-sensitive operations** — Auth, session management, credential handling
- **Replacing structured parsing** — If a site has JSON-LD schema, use extruct, not AI

### 12.6 AI Provider Abstraction

```python
class AIProvider(Protocol):
    async def extract(self, html: str, prompt: str) -> dict: ...
    async def classify(self, text: str, labels: list[str]) -> str: ...
    async def normalize(self, data: dict, target_schema: dict) -> dict: ...
```

**Supported providers:**
- Google Gemini (free tier available — current default)
- OpenAI GPT-4o / GPT-4o-mini
- Anthropic Claude
- Local models via Ollama (for self-hosted/offline)

**Fallback order:** Primary provider → secondary provider → deterministic fallback

---

## 13. Storage Design

### 13.1 Relational Metadata (PostgreSQL / SQLite)

Stores all structured metadata:
- Tenants, users, API keys
- Tasks, runs, results (references, not raw data)
- Policies, sessions
- Usage counters, billing records
- Site profiles, routing history

**Cloud/Self-hosted:** PostgreSQL 15+
**Desktop EXE:** SQLite (bundled, zero-config)

**Key tables:**
- `tenants` — Tenant records and settings
- `tasks` — Task definitions and status
- `runs` — Individual execution attempts
- `results` — Extraction result metadata
- `artifacts` — Artifact metadata (storage_path points to object store)
- `policies` — Extraction policies
- `sessions` — Session records with encrypted cookies
- `site_profiles` — Known site characteristics and routing hints
- `usage_events` — Granular usage tracking for billing

**Migration strategy:** Alembic for PostgreSQL, custom lightweight migrator for SQLite

### 13.2 Object / Artifact Storage

Stores large binary artifacts:
- HTML snapshots of scraped pages
- Screenshots (PNG)
- Export files (XLSX, JSON, CSV)
- Browser profiles

**Cloud:** S3-compatible (AWS S3, GCS, MinIO, Cloudflare R2)
**Self-hosted:** MinIO or local filesystem
**Desktop EXE:** Local filesystem (`~/.scraper-app/artifacts/`)

**Interface:**
```python
class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes, content_type: str) -> str: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...
    async def list(self, prefix: str) -> list[str]: ...
    async def get_presigned_url(self, key: str, ttl: int) -> str: ...
```

### 13.3 Queue / Cache (Redis / Valkey)

- **Task queue:** Pending tasks waiting for execution
- **Session cache:** Active session data for fast lookup
- **Rate limit counters:** Per-tenant, per-domain request counters
- **Result cache:** Short-lived cache of recent results for dedup
- **Pub/sub:** Real-time progress notifications to dashboards

**Cloud/Self-hosted:** Redis 7+ or Valkey
**Desktop EXE:** In-memory queue (asyncio.Queue) + SQLite for persistence

### 13.4 Local vs Remote Storage Routes

| Runtime Mode | Metadata | Artifacts | Queue/Cache |
|-------------|----------|-----------|-------------|
| Cloud SaaS | PostgreSQL | S3 | Redis |
| Self-hosted | PostgreSQL | MinIO / FS | Redis |
| Desktop Local | SQLite | Filesystem | In-memory |
| Desktop Hybrid | SQLite (local) + PostgreSQL (cloud) | FS (local) + S3 (sync) | In-memory + Redis |
| Extension Cloud | PostgreSQL (remote) | S3 (remote) | Redis (remote) |
| Extension Local | SQLite (companion) | FS (companion) | In-memory (companion) |

---

## 14. Multi-Tenant Model

### 14.1 Tenant Boundaries
- Each tenant has isolated data (tasks, results, sessions, artifacts)
- Tenants cannot access each other's data
- Row-level security in PostgreSQL enforced by `tenant_id` column on all tables
- Object storage keys prefixed with `tenant_id/`

### 14.2 Quotas
- Defined per plan (free, starter, pro, enterprise)
- Enforced at the control plane before task execution
- Soft limits (warning at 80%) and hard limits (reject at 100%)

| Resource | Free | Starter | Pro | Enterprise |
|----------|------|---------|-----|------------|
| Tasks/day | 50 | 500 | 5,000 | Unlimited |
| Concurrent tasks | 2 | 5 | 20 | 100 |
| Browser min/day | 10 | 60 | 600 | 6,000 |
| AI tokens/day | 10K | 100K | 1M | 10M |
| Storage | 100MB | 1GB | 10GB | 100GB |
| Proxy requests/day | 100 | 1,000 | 10,000 | 100,000 |

### 14.3 Usage Tracking
- Every task execution increments usage counters
- Counters reset on billing cycle boundary
- Usage events stored for billing reconciliation
- Real-time usage visible in dashboard

### 14.4 Deployment Mode Differences
- **SaaS:** Full multi-tenancy, billing, quotas enforced
- **Self-hosted:** Single tenant (or internal multi-tenant), no billing, admin sets quotas
- **Desktop:** No tenant concept, no quotas (local resources only)

---

## 15. Security Model

### 15.1 Secrets Management
- API keys (AI providers, proxy services, CAPTCHA solvers) stored encrypted
- **Cloud:** AWS Secrets Manager, GCP Secret Manager, or HashiCorp Vault
- **Self-hosted:** Environment variables or encrypted config file
- **Desktop:** OS keychain (Windows Credential Manager via Tauri)
- Secrets never logged, never included in API responses

### 15.2 Authentication
- **SaaS/Self-hosted API:** API key authentication (Bearer token)
- **Web dashboard:** Session-based auth (JWT cookies)
- **Extension:** API key stored in extension secure storage
- **Desktop:** Local-only, no auth required (optional PIN lock)
- **Admin:** Separate admin API with elevated privileges

### 15.3 Token Handling
- JWT tokens with short TTL (15 min access, 7 day refresh)
- Token rotation on refresh
- Revocation list for compromised tokens
- Scoped tokens (read-only, write, admin)

### 15.4 Extension Permission Boundaries
- Extension can only scrape the active tab (with user action)
- Extension cannot access arbitrary URLs without user consent
- Extension communicates with backend via HTTPS only
- Extension stores minimal data locally (API key, preferences)
- Content script isolation from page scripts

### 15.5 Local-to-Remote Trust Model
- Desktop EXE authenticates to cloud via API key (same as any API client)
- Browser extension authenticates to cloud via API key
- Extension-to-companion communication uses native messaging (Chrome API)
- Native messaging validates extension ID before accepting connections

### 15.6 Native Messaging Trust Boundary
- Companion service only accepts connections from known extension IDs
- Messages are JSON with schema validation
- No arbitrary code execution from extension messages
- Rate limiting on native messaging channel

---

## 16. Compliance and Policy Controls

### 16.1 Data Retention
- Default retention: 30 days for results, 7 days for artifacts
- Configurable per tenant / per policy
- Automatic cleanup job runs daily
- Tenants can request immediate deletion

### 16.2 Data Deletion
- `DELETE /api/v1/results/{id}` — Delete specific result + artifacts
- `DELETE /api/v1/tenants/{id}/data` — Purge all tenant data
- Deletion is cascading: result → artifacts → object storage
- Deletion logged in audit trail

### 16.3 Export Auditability
- Every data export is logged (who, when, what, format)
- Export artifacts retained for audit period
- Admin can review export history per tenant

### 16.4 Permissioned Actions
- Role-based access: viewer, operator, admin
- Viewers: read results, view dashboards
- Operators: create tasks, manage policies, export data
- Admins: manage tenants, configure system, view audit logs

### 16.5 Logging Boundaries
- **Logged:** Task metadata, execution events, errors, access events
- **NOT logged:** Full scraped content (only metadata), user credentials, proxy credentials
- Structured JSON logs with correlation IDs
- Log retention configurable (default 90 days)

---

## 17. Observability

### 17.1 Structured Logs
- JSON format with: timestamp, level, service, correlation_id, tenant_id, message, context
- Log levels: DEBUG, INFO, WARN, ERROR
- Per-component log configuration
- **Sink:** stdout (containerized) → log aggregator (Loki, ELK, CloudWatch)

### 17.2 Metrics
- **Counters:** tasks_submitted, tasks_completed, tasks_failed, requests_total, captcha_solves
- **Histograms:** task_duration_ms, request_latency_ms, extraction_confidence
- **Gauges:** active_sessions, browser_pool_size, queue_depth, proxy_pool_health
- **Format:** Prometheus-compatible
- **Sink:** Prometheus → Grafana (or cloud equivalent)

### 17.3 Distributed Traces
- OpenTelemetry instrumentation
- Trace spans: task_submission → routing → execution → extraction → normalization → storage
- Trace context propagated across services
- **Sink:** Jaeger, Tempo, or cloud trace service

### 17.4 Task Lineage
- Full lineage from task → runs → results → artifacts
- Queryable: "show me everything that happened for this task"
- Parent-child relationships for paginated tasks
- Retry lineage (which run was a retry of which)

### 17.5 Operator Debugging
- **Task inspector:** View full task lifecycle with all runs, errors, and timing
- **Session inspector:** View session health history
- **Site health dashboard:** Per-domain success rates, common errors
- **Live tail:** Stream logs for a specific task or domain in real-time

---

## 18. Packaging Strategy

### 18.1 Server (Control Plane + Workers)
- Docker images for each service
- Docker Compose for development and simple self-hosted
- Kubernetes Helm chart for production self-hosted and cloud
- Multi-arch: amd64 + arm64

### 18.2 Workers
- Separate Docker images for different worker types:
  - `worker-http` — HTTP lane workers
  - `worker-browser` — Browser lane workers (includes Playwright + Chromium)
  - `worker-ai` — AI normalization workers
- Scalable independently

### 18.3 Windows EXE
- **Tauri** framework (Rust backend + WebView frontend)
- Single-file installer (.msi or .exe via NSIS)
- Bundles: embedded Python runtime, SQLite, Chromium (for browser lane)
- Auto-update support via Tauri's updater
- Code signing for Windows SmartScreen

### 18.4 Browser Extension
- Chrome Web Store package (.crx / .zip)
- Manifest V3 compliant
- Content script + popup + background service worker
- Optional: Firefox add-on (WebExtension API compatible)

### 18.5 Local Companion Service
- Lightweight native service installed alongside EXE
- Registers as Chrome native messaging host
- Handles extension ↔ EXE communication
- Starts on system boot (optional)

### 18.6 Cloud Deployment Package
- Terraform modules for AWS, GCP, Azure
- Cloud-specific adaptations (S3 vs GCS, RDS vs Cloud SQL)
- CI/CD pipeline templates (GitHub Actions)

### 18.7 Self-Hosted Deployment Package
- Docker Compose with all services + dependencies (PostgreSQL, Redis, MinIO)
- `.env` template with all configuration options
- `install.sh` for guided setup
- Documentation for manual configuration

---

## 19. Testing Strategy

### 19.1 Unit Tests
- All shared contracts (Pydantic model validation)
- Execution router logic (lane selection)
- Fallback chain behavior
- Session health scoring
- Proxy rotation strategies
- AI provider abstraction
- Storage interface implementations
- **Framework:** pytest + pytest-asyncio
- **Target:** 80%+ code coverage on packages/

### 19.2 Integration Tests
- Control plane API endpoints (FastAPI TestClient)
- Database operations (PostgreSQL via testcontainers)
- Queue operations (Redis via testcontainers)
- Object storage operations (MinIO via testcontainers)
- End-to-end task lifecycle: submit → route → execute → normalize → store → retrieve

### 19.3 Connector Tests
- HTTP collector against httpbin.org and mock servers
- Browser worker against test HTML pages (local test server)
- Proxy adapter with mock proxy
- CAPTCHA adapter with mock solver
- API connector against mock API endpoints

### 19.4 Browser Tests
- Playwright tests for browser lane
- Infinite scroll handling
- AJAX pagination
- Dynamic content loading
- Authentication flows
- **Reuse from existing:** `test_e2e.py`, `test_final.py` patterns

### 19.5 Extension Tests
- Chrome extension unit tests (Jest + Chrome API mocks)
- Extension ↔ backend integration tests
- Native messaging tests (extension ↔ companion)
- Popup UI tests

### 19.6 Packaging Tests
- Docker image builds successfully
- Docker Compose stack starts and passes health checks
- Windows EXE installs and launches
- Browser extension loads in Chrome
- Tauri build produces valid installer

### 19.7 Deployment Smoke Tests
- Self-hosted deployment: stack up → submit task → get result → stack down
- Cloud deployment: terraform apply → smoke test → terraform destroy
- Desktop: install → run task → verify result → uninstall

---

## 20. Deployment Strategy

### 20.1 Self-Hosted Deployment

```
docker-compose.yml
├── control-plane (FastAPI)
├── worker-http
├── worker-browser (with Chromium)
├── worker-ai
├── postgresql
├── redis
├── minio (object storage)
└── nginx (reverse proxy + TLS)
```

- Single `docker compose up` to start everything
- `.env` file for all configuration
- Optional: Kubernetes Helm chart for larger deployments

### 20.2 Public Cloud Deployment
- **Compute:** ECS/Fargate (AWS), Cloud Run (GCP), Container Apps (Azure)
- **Database:** RDS/Cloud SQL/Azure Database for PostgreSQL
- **Cache:** ElastiCache/Memorystore/Azure Cache for Redis
- **Storage:** S3/GCS/Azure Blob
- **Load balancer:** ALB/Cloud Load Balancing/Azure Front Door
- **Secrets:** Secrets Manager/Secret Manager/Key Vault

### 20.3 Hybrid Deployment
- Desktop EXE runs locally for browser execution
- Cloud backend handles AI, storage, scheduling
- Tasks can be routed to local or cloud workers based on policy
- Results sync between local and cloud

### 20.4 Environment Configuration
- All configuration via environment variables
- Configuration hierarchy: defaults → env file → env vars → CLI flags
- Secrets separated from config (never in env files committed to git)

**Key configuration groups:**
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis connection
- `STORAGE_*` — Object storage (type, endpoint, bucket, credentials)
- `AI_*` — AI provider (type, API key, model)
- `PROXY_*` — Proxy configuration
- `AUTH_*` — Authentication settings
- `BILLING_*` — Billing/quota settings (SaaS only)

### 20.5 Secrets and Config Separation
- Secrets: API keys, database passwords, proxy credentials → Secrets Manager or env vars
- Config: Feature flags, quotas, timeouts, log levels → Config file or env vars
- Never commit secrets to git; `.env.example` with placeholder values only

---

## 21. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Anti-bot detection evolves | Scrapers break | High | Fallback chain, unlocker services, regular connector updates |
| Browser automation instability | Flaky extractions | Medium | Health scoring, automatic retries, headless browser pool management |
| Proxy spend exceeds budget | Cost overrun | Medium | Cost-aware routing, proxy scoring, budget alerts per tenant |
| Chrome extension policy changes | Extension rejected | Medium | Manifest V3 compliance, minimal permissions, review guidelines |
| Tauri/desktop packaging issues | EXE doesn't work | Medium | CI/CD packaging tests on Windows, integration tests |
| Local/remote session transfer | Data sync complexity | High | Clear session ownership model, conflict resolution strategy |
| AI provider rate limits | Extraction delays | Medium | Multi-provider fallback, token budget management, caching |
| PostgreSQL scaling for SaaS | Performance bottleneck | Low | Connection pooling (PgBouncer), read replicas, partitioning |
| Scrapling library breaking changes | Engine regressions | Medium | Pin versions, abstract behind fetcher interface, integration tests |
| Security vulnerabilities (XSS, injection) | Data breach | Low | Input validation, parameterized queries, CSP headers, security audits |

---

## 22. Milestones

### M0 — Foundation (Phase 0-2)
- Repository structure established
- Final specs complete
- Task breakdown complete
- System tracking files initialized

### M1 — Core Platform
- Shared contracts defined and implemented (Pydantic models)
- FastAPI control plane with task CRUD
- PostgreSQL schema + migrations
- Redis queue integration
- HTTP execution lane working end-to-end

### M2 — Browser & AI Lanes
- Browser execution lane (Playwright)
- AI normalization lane
- Fallback chain integrated (HTTP → Browser → AI)
- Session management working
- Proxy integration working

### M3 — Web Dashboard
- React web dashboard
- Task submission, progress tracking, result viewing
- Export functionality (XLSX, JSON, CSV)
- Admin panel (tenants, quotas, site profiles)

### M4 — Desktop Application
- Tauri-based Windows EXE
- Embedded control plane (localhost)
- Local storage (SQLite + filesystem)
- Browser lane working locally
- Installer + auto-update

### M5 — Browser Extension
- Chrome extension (Manifest V3)
- Cloud-connected mode working
- Local companion mode working
- Native messaging bridge
- Chrome Web Store ready

### M6 — Production Hardening
- Multi-tenant isolation verified
- Security audit passed
- Observability stack deployed
- Performance benchmarks met
- Documentation complete

### M7 — Deployment & Launch
- Self-hosted Docker Compose package
- Cloud Terraform modules
- CI/CD pipelines
- Deployment smoke tests passing
- Launch checklist complete

---

## 23. Acceptance Criteria

### 23.1 Technical Acceptance
- [ ] All shared contracts have Pydantic models with validation
- [ ] Control plane API passes all integration tests
- [ ] HTTP lane extracts data from 10+ test sites successfully
- [ ] Browser lane handles JavaScript-rendered pages
- [ ] AI lane normalizes extraction results with >90% accuracy
- [ ] Fallback chain escalates correctly (HTTP → Browser → Hard-target)
- [ ] Session management maintains health scores accurately
- [ ] Proxy rotation works with 3+ proxy providers
- [ ] Database migrations run cleanly (up and down)
- [ ] All unit tests pass, >80% coverage on core packages

### 23.2 Product Acceptance
- [ ] SaaS user can: sign up → create task → get results → export
- [ ] Self-hosted user can: deploy → configure → run tasks → view results
- [ ] Desktop user can: install → scrape URL → export to Excel
- [ ] Extension user can: install → click extract → see results
- [ ] Developer can: get API key → submit task via API → get JSON results
- [ ] Multi-tenant isolation verified (tenant A cannot see tenant B data)

### 23.3 Packaging Acceptance
- [ ] Docker images build on CI (amd64 + arm64)
- [ ] Docker Compose stack passes health checks within 60 seconds
- [ ] Windows EXE installs on Windows 10/11 without admin rights
- [ ] Browser extension passes Chrome Web Store review criteria
- [ ] Tauri auto-updater works for desktop app

### 23.4 Deployment Acceptance
- [ ] Self-hosted: `docker compose up` → functional in under 5 minutes
- [ ] Cloud: Terraform apply → functional in under 15 minutes
- [ ] Desktop: Download → install → first scrape in under 3 minutes
- [ ] Extension: Install → first extraction in under 1 minute

---

## 24. Open Questions and Assumptions

### Open Questions

1. **Billing integration:** Which payment provider for SaaS billing? (Stripe assumed)
2. **AI model hosting:** Should we support local model inference (Ollama) for self-hosted? (Assumed yes)
3. **Extension stores:** Firefox add-on in addition to Chrome? (Deferred to post-M5)
4. **Mac/Linux desktop:** Should we build desktop apps for macOS/Linux? (Deferred — Tauri supports it but not in initial scope)
5. **Real-time WebSocket API:** Should the API support WebSocket for live progress? (Assumed yes for dashboard, REST polling for API clients)
6. **Data residency:** Do we need region-specific data storage? (Assumed configurable per self-hosted, not for SaaS MVP)
7. **Rate limiting strategy:** Per-tenant or per-domain or both? (Assumed both)

### Assumptions

1. Python 3.11+ is the minimum supported Python version
2. PostgreSQL 15+ for metadata storage
3. Redis 7+ (or Valkey) for queue/cache
4. Playwright is the browser automation framework (not Selenium)
5. Tauri v2 for desktop application shell
6. Chrome Manifest V3 for extension
7. Google Gemini free tier is the default AI provider
8. Scrapling library remains a viable dependency (abstracted behind interface)
9. The existing scraper_pro/ code is a reference implementation, not the final architecture
10. Self-hosted deployment targets Docker Compose as the minimum; Kubernetes is optional

---

*This document is the source of truth for the project. All implementation decisions must align with it. Deviations must be documented in system/development_log.md with rationale.*
