# AI Scraping Platform

Production-grade, cloud-agnostic AI-powered web scraping platform. Supports cloud SaaS, self-hosted, Windows desktop, and browser extension deployments — all sharing one core engine.

## Architecture

```
apps/                    # Runtime shells
  web/                   # React + Vite dashboard
  desktop/               # Tauri v2 Windows EXE
  extension/             # Chrome Manifest V3 extension
  companion/             # Native messaging host
packages/                # Shared libraries
  contracts/             # 7 Pydantic v2 data schemas
  core/                  # Engine (router, session, AI, storage, scheduling)
  connectors/            # Adapters (HTTP, browser, proxy, CAPTCHA, hard-target)
services/                # Backend services
  control-plane/         # FastAPI API server
  worker-http/           # HTTP extraction worker
  worker-browser/        # Playwright browser worker
  worker-ai/             # AI normalization worker
  worker-hard-target/    # Stealth browser worker
infrastructure/          # Deployment
  docker/                # Docker Compose stack
  terraform/             # AWS IaC modules
  helm/                  # Kubernetes Helm chart
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ (or SQLite for local dev)
- Redis 7+ (or in-memory for local dev)

### 1. Install Dependencies

```bash
pip install -e ".[all]"
playwright install chromium
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings (database URL, API keys, etc.)
```

### 3. Run the Control Plane

```bash
uvicorn services.control_plane.app:app --host 0.0.0.0 --port 8000
```

### 4. Run Workers (in separate terminals)

```bash
python -m services.worker_http.main
python -m services.worker_browser.main
python -m services.worker_ai.main
```

### 5. Open the Dashboard

```bash
cd apps/web && npm install && npm run dev
```

## Docker Compose (Recommended)

```bash
cd infrastructure/docker
docker compose up -d
```

This starts PostgreSQL, Redis, the control plane, and all workers.

## API Usage

```bash
# Create a task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "X-Tenant-ID: my-tenant" \
  -d '{"url": "https://example.com/products", "task_type": "scrape"}'

# Execute the task
curl -X POST http://localhost:8000/api/v1/tasks/{task_id}/execute \
  -H "X-Tenant-ID: my-tenant"

# Get results
curl http://localhost:8000/api/v1/results?task_id={task_id} \
  -H "X-Tenant-ID: my-tenant"
```

## Runtime Modes

| Mode | Database | Queue | Storage | Browser |
|------|----------|-------|---------|---------|
| Cloud SaaS | PostgreSQL | Redis | S3 | Remote Playwright |
| Self-Hosted | PostgreSQL | Redis | Filesystem | Local Playwright |
| Desktop EXE | SQLite | In-memory | Filesystem | Embedded Playwright |
| Extension | Cloud API | Cloud API | Cloud API | Tab injection |

## Testing

```bash
# Run all tests
python -m pytest tests/ -q

# Run by category
python -m pytest tests/unit -q
python -m pytest tests/integration -q
python -m pytest tests/e2e -q
```

**Current status:** 706 tests passing, 0 failures.

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2
- **Database:** PostgreSQL 15+ / SQLite
- **Cache/Queue:** Redis 7+ / In-memory
- **Browser:** Playwright
- **Desktop:** Tauri v2 (Rust + WebView)
- **Extension:** Chrome Manifest V3
- **AI:** Google Gemini (primary), OpenAI GPT-4o-mini (fallback), deterministic (always available)
- **Infra:** Docker, Terraform (AWS), Helm (K8s)

## Key Features

- Multi-lane execution: API, HTTP, Browser, Hard-Target with automatic escalation
- AI-augmented extraction with deterministic fallback
- Rate limiting (token bucket) and quota enforcement per tenant
- Webhook callbacks with HMAC-SHA256 signatures
- Task scheduling (cron expressions, intervals)
- 4 proxy provider integrations (BrightData, Smartproxy, Oxylabs, free)
- CAPTCHA detection and solving (2Captcha, Anti-Captcha, CapMonster)
- Session management with health scoring
- Prometheus metrics + OpenTelemetry tracing

## Documentation

| Document | Description |
|----------|-------------|
| [docs/final_specs.md](docs/final_specs.md) | Full platform specification |
| [docs/tasks_breakdown.md](docs/tasks_breakdown.md) | 69 tasks across 24 epics |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Architecture overview |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Deployment guide |
| [docs/api_reference.md](docs/api_reference.md) | API reference |
| [docs/developer_setup.md](docs/developer_setup.md) | Developer setup guide |

## License

MIT
