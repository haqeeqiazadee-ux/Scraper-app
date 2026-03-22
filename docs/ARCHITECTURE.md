# Architecture — AI Scraping Platform

## System Overview

```
                         +--------------------+
                         |    Runtime Shells   |
                         +---------+----------+
                         |         |          |
                   +-----+   +----+----+  +--+--------+
                   | Web |   | Desktop |  | Extension |
                   | SPA |   | Tauri   |  | MV3       |
                   +--+--+   +----+----+  +-----+-----+
                      |           |              |
                      +-----------+--------------+
                                  |
                          +-------v-------+
                          | Control Plane |  (FastAPI)
                          +---+---+---+---+
                              |   |   |
               +--------------+   |   +--------------+
               |                  |                   |
        +------v------+   +------v------+   +--------v-----+
        | Worker HTTP |   | Worker      |   | Worker AI    |
        | (requests)  |   | Browser     |   | (normalize)  |
        +------+------+   | (Playwright)|   +--------+-----+
               |          +------+------+            |
               +-------------+---+-------------------+
                              |
                    +---------v---------+
                    |   Storage Layer   |
                    +-+---------+-----+-+
                      |         |     |
                +-----v--+ +---v--+ +v--------+
                |Postgres| |Redis | |S3 / FS  |
                |/SQLite | |/Mem  | |artifacts|
                +--------+ +-----+ +---------+
```

## Component Descriptions

### Runtime Shells

All shells share the same core engine. They differ only in hosting context.

| Shell | Technology | Target | API Connection |
|-------|-----------|--------|---------------|
| **Web Dashboard** | React + Vite | Browser (SaaS) | Remote control plane |
| **Desktop App** | Tauri v2 + React | Windows EXE | Embedded local server (port 8321) |
| **Chrome Extension** | Manifest V3 | Chrome/Edge | Remote or local via native messaging |
| **Companion** | Python native host | OS service | Bridges extension to local engine |

### Backend Services

**Control Plane** (`services/control-plane/`)
- FastAPI application serving the REST API
- Routes: tasks, policies, execution, results, auth, health, metrics
- Middleware: JWT authentication, tenant isolation, Prometheus metrics
- Dependency injection for storage backends

**Worker HTTP** (`services/worker-http/`)
- Lightweight HTTP-based extraction using `httpx`
- CSS selector, JSON-LD, and regex extraction strategies
- Sets `should_escalate=True` when extraction fails or confidence is low

**Worker Browser** (`services/worker-browser/`)
- Playwright-based extraction for JavaScript-rendered pages
- Anti-detection: stealth scripts, random delays, viewport randomization
- Handles infinite scroll, pagination, and dynamic content

**Worker AI** (`services/worker-ai/`)
- AI normalization pipeline: schema mapping, field repair, deduplication
- Provider chain: Gemini (default) -> OpenAI -> deterministic fallback
- Confidence scoring based on field fill rate

### Shared Packages

**Contracts** (`packages/contracts/`)
- 7 Pydantic v2 schemas: Task, Policy, Session, Run, Result, Artifact, Billing
- All inter-service communication uses these schemas
- Validation, serialization, and OpenAPI schema generation

**Core** (`packages/core/`)
- ExecutionRouter: URL classification and lane selection
- SessionManager: lifecycle, health scoring, auto-invalidation
- AI providers: Gemini, OpenAI, deterministic, provider chain
- Storage interfaces: Protocol-based abstractions
- Observability: structured logging, metrics, tracing

**Connectors** (`packages/connectors/`)
- HttpCollector: async HTTP with retry, rate limiting, proxy support
- BrowserWorker: Playwright wrapper with stealth and anti-detection
- ProxyAdapter: rotating/sticky/geo-targeted proxy management
- CaptchaAdapter: 2Captcha, Anti-Captcha, CapMonster integration
- ApiAdapter: direct API/feed consumption

## Data Flow

### Scraping Execution Flow

1. Client submits a **Task** via REST API or extension
2. Control plane validates and persists the task
3. **ExecutionRouter** classifies the URL and selects a lane:
   - API/Feed lane (direct structured data)
   - HTTP lane (static HTML)
   - Browser lane (JavaScript-rendered)
   - Hard-target lane (CAPTCHA, anti-bot)
4. Selected **Worker** executes extraction
5. If extraction fails or confidence is low, **EscalationManager** promotes to next lane
6. **AI Worker** normalizes, deduplicates, and scores results
7. **Result** is persisted to storage and returned to client

### Lane Escalation

```
API/Feed -> HTTP -> Browser -> Hard-target -> AI repair
                                                  |
                                         (always runs)
```

Each lane escalation preserves context (partial results, cookies, session state).

## Storage Architecture

| Backend | Cloud/SaaS | Desktop | Purpose |
|---------|-----------|---------|---------|
| PostgreSQL 15 | Primary | -- | Metadata (tasks, policies, results) |
| SQLite | -- | Primary | Metadata (embedded) |
| Redis 7 | Primary | -- | Queue + cache |
| In-memory | -- | Primary | Queue + cache (embedded) |
| S3-compatible | Primary | -- | Artifacts (HTML, screenshots) |
| Filesystem | Fallback | Primary | Artifacts (local storage) |

All storage access goes through Protocol interfaces defined in `packages/core/interfaces.py`.

## Deployment Options

| Option | Stack | Use Case |
|--------|-------|----------|
| **Docker Compose** | PostgreSQL + Redis + control-plane | Development, self-hosted |
| **Kubernetes (Helm)** | Full HA deployment | Production cloud |
| **AWS (Terraform)** | ECS Fargate + RDS + ElastiCache + S3 | AWS production |
| **Desktop** | Tauri + SQLite + filesystem | Single-user local |

## Security Model

- JWT authentication (HS256/RS256) with refresh tokens
- Tenant isolation via `X-Tenant-ID` header on every query
- Repository pattern enforces tenant_id in all WHERE clauses
- Secrets managed via environment variables or pluggable SecretsManager
- CORS, rate limiting, and input validation on all endpoints
- Path traversal protection on filesystem storage

## Tech Stack Summary

| Layer | Technology |
|-------|-----------|
| Language | Python 3.11+ |
| API Framework | FastAPI + Pydantic v2 |
| Database | PostgreSQL 15 / SQLite |
| Cache/Queue | Redis 7 / in-memory |
| Object Storage | S3-compatible / filesystem |
| Browser Automation | Playwright |
| Desktop Shell | Tauri v2 (Rust + WebView) |
| Browser Extension | Chrome Manifest V3 |
| AI Providers | Gemini, OpenAI, Anthropic, Ollama |
| Testing | pytest + pytest-asyncio |
| Linting | ruff |
| CI/CD | GitHub Actions |
| Infrastructure | Docker, Kubernetes (Helm), Terraform (AWS) |
