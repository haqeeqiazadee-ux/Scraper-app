# Developer Setup Guide

## Prerequisites

- Python 3.11+
- Node.js 18+ (for web dashboard)
- Docker & Docker Compose (for local services)
- Git

## Quick Start

```bash
# Clone the repository
git clone https://github.com/fahad-scraper/Scraper-app.git
cd Scraper-app

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your configuration

# Run tests
pytest tests/unit/ -v

# Start local services (PostgreSQL + Redis)
docker compose -f infrastructure/docker/docker-compose.yml up -d postgres redis

# Run the control plane
uvicorn services.control_plane.app:app --reload --host 0.0.0.0 --port 8000
```

## Project Structure

```
Scraper-app/
├── packages/           # Shared libraries
│   ├── contracts/      # Pydantic data models
│   ├── core/           # Engine, router, storage, AI
│   └── connectors/     # HTTP, browser, proxy, CAPTCHA
├── services/           # Backend services
│   ├── control-plane/  # FastAPI API server
│   ├── worker-http/    # HTTP extraction worker
│   ├── worker-browser/ # Browser extraction worker
│   └── worker-ai/      # AI normalization worker
├── apps/               # Frontend applications
│   ├── web/            # React dashboard
│   ├── desktop/        # Tauri desktop app
│   └── extension/      # Chrome extension
├── infrastructure/     # Deployment configs
├── tests/              # Test suites
└── docs/               # Documentation
```

## Environment Variables

Key variables (see `.env.example` for full list):

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///./scraper.db` | Database connection |
| `REDIS_URL` | (empty) | Redis URL for queue/cache |
| `STORAGE_TYPE` | `filesystem` | Object storage backend |
| `STORAGE_PATH` | `./artifacts` | Local artifact storage path |
| `GEMINI_API_KEY` | (empty) | Google Gemini API key |
| `OPENAI_API_KEY` | (empty) | OpenAI API key (fallback AI) |
| `SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `LOG_LEVEL` | `INFO` | Logging level |

## Running Tests

```bash
# All unit tests
pytest tests/unit/ -v

# Specific test file
pytest tests/unit/test_contracts.py -v

# With coverage
pytest tests/unit/ --cov=packages --cov=services --cov-report=html

# Integration tests (requires Docker services)
pytest tests/integration/ -v
```

## Linting & Formatting

```bash
# Lint
ruff check .

# Auto-fix lint issues
ruff check --fix .

# Format
ruff format .

# Type checking
mypy packages/ services/
```

## Docker Development

```bash
# Start all services
docker compose -f infrastructure/docker/docker-compose.yml up -d

# View logs
docker compose -f infrastructure/docker/docker-compose.yml logs -f control-plane

# Stop all services
docker compose -f infrastructure/docker/docker-compose.yml down

# Rebuild after code changes
docker compose -f infrastructure/docker/docker-compose.yml up -d --build control-plane
```

## Web Dashboard Development

```bash
cd apps/web
npm install
npm run dev
# Dashboard at http://localhost:5173, proxies API to :8000
```

## Chrome Extension Development

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode"
3. Click "Load unpacked" → select `apps/extension/`
4. The extension icon appears in the toolbar

## Adding a New Feature

1. Read `docs/final_specs.md` for the relevant specification section
2. Check `docs/tasks_breakdown.md` for the task definition
3. Implement in the appropriate package/service
4. Add tests in `tests/unit/` mirroring the source structure
5. Run `ruff check .` and `pytest tests/unit/` before committing
6. Update `system/todo.md` and `system/execution_trace.md`

## Coding Conventions

- **Pydantic v2** for all data models
- **`async def`** for all I/O operations
- **Protocol classes** for interfaces (not ABC)
- **structlog** for logging (no `print()`)
- **Type hints** on all function signatures
- **Underscores** in Python package directory names
- **Lazy initialization** for clients (create on first request)

## AI Providers

The platform supports multiple AI providers with automatic fallback:

```
Gemini (primary) → OpenAI (fallback) → Deterministic (always available)
```

**Configuration:**
- Set `GEMINI_API_KEY` for Google Gemini (gemini-1.5-flash, gemini-2.0-flash)
- Set `OPENAI_API_KEY` for OpenAI (gpt-4o-mini, gpt-4o)
- Deterministic provider requires no API key (uses CSS selectors, JSON-LD, regex)

**Usage in code:**
```python
from packages.core.ai_providers import AIProviderFactory

# Single provider
provider = AIProviderFactory.create("openai", api_key="sk-...", model="gpt-4o-mini")
result = await provider.extract(html, url)

# Fallback chain
chain = AIProviderFactory.create_chain([
    {"provider_type": "gemini", "api_key": gemini_key},
    {"provider_type": "openai", "api_key": openai_key},
    {"provider_type": "deterministic"},
])
result = await chain.extract(html, url)
```

## Troubleshooting

**Import errors with hyphenated directories:**
Services use symlinks (`control_plane` → `control-plane`). If symlinks are broken:
```bash
cd services && ln -sf control-plane control_plane
```

**Database connection errors:**
Ensure PostgreSQL is running or use SQLite for local dev (default).

**Playwright not installed:**
```bash
pip install playwright
playwright install chromium
```
