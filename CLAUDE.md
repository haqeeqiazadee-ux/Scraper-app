# CLAUDE.md — Project Context for AI Scraping Platform

> **INHERITS FROM:** `~/.claude/CLAUDE.md` (Global Master Directives)
> All global rules (autonomy mode, agent hierarchy, MCP servers, skills library, session memory, auto-update protocol) apply to this project. This file adds **project-specific** context only.

> This file is the authoritative context document for Claude Code sessions working on this project.

## ⚡ MANDATORY PRE-TASK PROTOCOL (RUNS BEFORE EVERY TASK)

**This is NON-NEGOTIABLE. Every single task — no matter how small — triggers this sequence.**

```
BEFORE ANY WORK:
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 0: READ GLOBAL CONFIG                             │
  │   → Read ~/.claude/CLAUDE.md (or .claude/CLAUDE.md)    │
  │   → Load: agent hierarchy, MCP servers, skills,        │
  │     commands, autonomy rules, session memory protocol   │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 1: CLASSIFY TASK                                  │
  │   → ARCHITECTURE? → architect-1 + architect-2          │
  │   → IMPLEMENTATION? → engineer-1 + engineer-2          │
  │   → RESEARCH/CONTENT? → product-1 + product-2         │
  │   → SECURITY/AUTH? → security-1 + security-2           │
  │   → TESTING/QA? → qa-1 + qa-2                         │
  │   → FULL FEATURE? → ALL agents                        │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 2: SELECT TOOLS                                   │
  │   → MCP servers needed? (context7, exa, firecrawl,     │
  │     github, playwright, claude-mem, ruflo, figma,      │
  │     n8n-mcp, n8n-instance)                             │
  │   → Skills to invoke? (437 available — match to task)  │
  │   → Commands to run? (102 available)                   │
  │   → Python packages? (lightrag, elevenlabs, boto3)     │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 3: READ PROJECT STATE                             │
  │   → system/todo.md (current queue)                     │
  │   → system/execution_trace.md (last 5 entries)         │
  │   → system/lessons.md (avoid past mistakes)            │
  │   → docs/final_specs.md (if architecture-relevant)     │
  │   → docs/tasks_breakdown.md (if task is in backlog)    │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 4: EXECUTE                                        │
  │   → Deploy selected agents in parallel via AgentPool   │
  │   → Use selected MCP servers + skills + commands       │
  │   → Full autonomy: no permission asking, fix forward   │
  │   → Complete fully before stopping                     │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 4b: VERIFY-BEFORE-DONE LOOP (MANDATORY)           │
  │                                                         │
  │   DO NOT claim "done" until this loop passes.           │
  │                                                         │
  │   WHILE not_verified:                                   │
  │     1. LIST all deliverables promised for this task     │
  │     2. CHECK each deliverable exists:                   │
  │        → File created? ls/stat the path                │
  │        → Code written? grep for key function/class     │
  │        → Tests pass? Run pytest on affected files      │
  │        → API works? curl/httpx the endpoint            │
  │        → UI renders? Playwright or manual check        │
  │     3. RUN any relevant test suite (unit, integration,  │
  │        e2e) — at minimum run tests for changed files   │
  │     4. CHECK for regressions — existing tests still    │
  │        pass after changes                               │
  │     5. If ANY check fails:                              │
  │        → DO NOT mark as complete                        │
  │        → Fix the issue                                  │
  │        → GOTO step 1 (re-verify everything)            │
  │     6. If ALL checks pass:                              │
  │        → Log evidence: "Verified: X tests pass,        │
  │          Y files created, Z endpoints responding"       │
  │        → ONLY THEN proceed to STEP 5                   │
  │                                                         │
  │   HARD RULES:                                           │
  │   - "I wrote the code" ≠ done. Code must WORK.         │
  │   - "Agent was deployed" ≠ done. Agent output must     │
  │     be verified (read the file, run the test).          │
  │   - "Tests were written" ≠ done. Tests must PASS.      │
  │   - "File was created" ≠ done. File must be correct    │
  │     (no import errors, no syntax errors).               │
  │   - Sub-agent work is UNTRUSTED until verified.         │
  │     Always spot-check agent outputs before claiming     │
  │     completion.                                         │
  │   - Partial completion = NOT complete. If 8/10 tasks    │
  │     pass, fix the 2 failures before reporting done.     │
  │                                                         │
  │   EVIDENCE FORMAT (include in completion report):       │
  │   ```                                                   │
  │   VERIFIED:                                             │
  │     Files: 12 created, 5 modified (ls confirmed)       │
  │     Tests: 101/101 pass (pytest output attached)       │
  │     API: 18/18 endpoints responding (httpx verified)   │
  │     Build: No errors (ruff/mypy clean)                 │
  │     Regressions: 0 (existing tests unaffected)         │
  │   ```                                                   │
  └──────────────────────┬──────────────────────────────────┘
                         ▼
  ┌─────────────────────────────────────────────────────────┐
  │ STEP 5: POST-TASK AUTO-UPDATE                          │
  │   → Update system/todo.md                              │
  │   → Update system/execution_trace.md                   │
  │   → Update system/development_log.md                   │
  │   → Update system/final_step_logs.md                   │
  │   → Update system/lessons.md (if learned)              │
  │   → Update CLAUDE.md (if architecture changed)         │
  │   → Store findings in claude-mem                       │
  │   → Git commit + push                                  │
  └─────────────────────────────────────────────────────────┘
```

### Global Config Location

| Location | When Used |
|----------|-----------|
| `~/.claude/CLAUDE.md` | Claude Code on local machine (auto-loaded) |
| `.claude/CLAUDE.md` | Fallback copy inside this repo (portable) |

### Inherited Global Directives

- **Owner:** Muhammad Usman — fully autonomous, action-first execution
- **Agent Hierarchy:** Orchestrator → 10-agent pool (2× architect, 2× engineer, 2× product, 2× security, 2× QA)
- **Autonomy:** MAXIMIZED — no permission asking, complete tasks fully, fix forward
- **Session Memory:** claude-mem auto-persist on start/during/end
- **Auto-Updates:** system files update after every major change (see global protocol)

### Project-Specific Tool Mapping

| Task Type | MCP Servers | Key Skills | Commands |
|-----------|-------------|------------|----------|
| **Scraper code** | context7, github | senior-backend, senior-fullstack, focused-fix | /build-fix, /tdd, /verify |
| **Anti-detection** | exa, firecrawl, context7 | security-pen-testing, browser-automation | /code-review, /e2e |
| **Browser automation** | playwright, context7 | playwright-pro, senior-qa | /e2e, /test-coverage |
| **API endpoints** | context7, github | api-design-reviewer, api-test-suite-builder | /build-fix, /verify |
| **Infrastructure** | github | senior-devops, docker-development, terraform-patterns | /checkpoint |
| **Research** | exa, firecrawl | deep-research, competitive-teardown | /plan |
| **Web UI** | figma, context7 | senior-frontend, ui-design-system | /build-fix |
| **n8n workflows** | n8n-mcp, n8n-instance | agent-workflow-designer | /multi-workflow |
| **Documentation** | github, claude-mem | spec-driven-workflow | /docs, /update-docs |

## Repository

**Canonical Remote:** `https://github.com/fahad-scraper/Scraper-app`
Always use this repo for all git operations (fetch, pull, push). Do not use any other remote.

**Authentication:** If git push fails with auth errors, read the GitHub PAT from `.env` (`GITHUB_PAT`) and set the remote URL:
```
git remote set-url origin https://<TOKEN>@github.com/fahad-scraper/Scraper-app.git
```

## Project Overview

**Name:** AI Scraping Platform (formerly Scrapling Pro v3.0)
**Type:** Production-grade, cloud-agnostic AI-powered web scraping platform
**Repo:** fahad-scraper/Scraper-app

## Architecture

This is a **monorepo** with the following structure:

```
/
├── apps/                    # Runtime shells (front ends)
│   ├── web/                 # React + Vite web dashboard
│   ├── desktop/             # Tauri v2 Windows EXE
│   ├── extension/           # Chrome Manifest V3 extension
│   └── companion/           # Native messaging host
├── packages/                # Shared libraries
│   ├── contracts/           # Pydantic data contracts (Task, Policy, Session, Run, Result, Artifact, Billing)
│   ├── core/                # Core engine (router, session manager, AI provider, storage interfaces)
│   └── connectors/          # Connector adapters (HTTP, browser, proxy, CAPTCHA, API)
├── services/                # Backend services
│   ├── control-plane/       # FastAPI control plane
│   ├── worker-http/         # HTTP lane worker
│   ├── worker-browser/      # Browser lane worker (Playwright)
│   └── worker-ai/           # AI normalization worker
├── infrastructure/          # Deployment
│   ├── docker/              # Dockerfiles + docker-compose
│   ├── terraform/           # Cloud IaC (AWS/GCP/Azure)
│   └── helm/                # Kubernetes Helm chart
├── tests/                   # Test suites
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── scripts/                 # Build/deploy/utility scripts
├── docs/                    # Project documentation
│   ├── final_specs.md       # SOURCE OF TRUTH — full platform specification
│   └── tasks_breakdown.md   # 69 tasks across 24 epics
├── system/                  # Project tracking (mandatory, always update)
│   ├── execution_trace.md   # Chronological decision trace
│   ├── development_log.md   # Engineering log
│   ├── todo.md              # Current actionable queue
│   ├── lessons.md           # Persistent learning memory
│   └── final_step_logs.md   # Detailed per-task execution ledger
├── scraper_pro/             # LEGACY — existing v3.0 code (reference only)
└── CLAUDE.md                # THIS FILE
```

## Key Design Principles

1. **One shared platform** — EXE, extension, SaaS, self-hosted share the same core
2. **Cloud-agnostic** — No vendor lock-in; abstractions for storage, queue, secrets
3. **AI as augmentation** — Deterministic parsers first; AI for routing, repair, normalization
4. **Contract-driven** — All components use shared Pydantic schemas
5. **Fallback chains** — Every extraction has primary → secondary → tertiary fallback

## Tech Stack

- **Backend:** Python 3.11+, FastAPI, Pydantic v2
- **Database:** PostgreSQL 15+ (cloud/self-hosted), SQLite (desktop)
- **Cache/Queue:** Redis 7+ / Valkey (cloud), in-memory (desktop)
- **Object Storage:** S3-compatible (cloud), filesystem (desktop)
- **Browser Automation:** Camoufox (primary, C++-level stealth), Playwright (fallback)
- **HTTP Client:** curl_cffi (browser TLS/JA3 impersonation), httpx (fallback)
- **Desktop Shell:** Tauri v2 (Rust + WebView)
- **Extension:** Chrome Manifest V3
- **AI Providers:** Google Gemini (default), OpenAI, Anthropic, Ollama (local)
- **Testing:** pytest + pytest-asyncio + testcontainers
- **Linting:** ruff
- **CI/CD:** GitHub Actions

## Mandatory Workflow

**See `⚡ MANDATORY PRE-TASK PROTOCOL` above — it supersedes this section.**

All pre-task reads and post-task updates are defined in the protocol flowchart. The protocol merges global directives (agent selection, tool matching, autonomy rules) with project-specific state (todo, specs, lessons, execution trace).

## Current Phase

**All Phases COMPLETE — Platform Production-Hardened**

**Phase 3 — Architecture Scaffolding (COMPLETE)**
- Monorepo folder structure created (26 directories)
- Python tooling configured (ruff, pytest, mypy, coverage)
- packages/contracts: 7 Pydantic v2 schemas implemented
- packages/core: 10 Protocol interfaces + ExecutionRouter
- packages/connectors: 6 adapter implementations (HTTP, browser, proxy, CAPTCHA, API, hard-target)
- services/control-plane: FastAPI app with task/policy CRUD + health endpoints

**Phase 4 — Incremental Implementation (COMPLETE)**
- All 69 original tasks completed
- 525 tests passing across 22+ test modules

**Phase 4+ — Production Readiness Gap Closure (COMPLETE)**
- Redis distributed queue consumer + worker consumption loops
- Hard-target execution lane (stealth browser + fingerprint randomization)
- Rate limit enforcement + quota management (token bucket + tenant quotas)
- Callback webhook executor (HMAC-SHA256 signed) + task scheduler (cron/interval)
- Web UI wired to real API (full client, hooks, auth context, login page)
- 648 tests passing, 6 skipped, 0 failed

**Phase 5 — Use-Case QA Testing (COMPLETE)**
- 4 QA sessions covering all 18 phases of qa_strategy.md
- 124 use cases passed, 52 skipped (external services), 5 bugs fixed
- Browser lane verified with Chromium v141 (SPA rendering, screenshots, stealth)
- Hard-target lane verified (fingerprint randomization, CAPTCHA detection, escalation chain)
- E-commerce scenarios verified (25-item PLP, PDP JSON-LD, Shopify detection)
- 706 tests passing, 0 failed

**Phase 6 — Stealth Upgrade (COMPLETE)**
- curl_cffi for browser-matching TLS/JA3/HTTP2 (replaces httpx in HTTP lane)
- 14 coherent device profiles across 8 geo regions (all signals consistent)
- Camoufox C++-level stealth for hard-target lane (0% detection on CreepJS)
- Human behavioral simulation: Bezier mouse curves, log-normal delays, idle jitter
- Warm-up navigation + Google referrer chains

**Phase 7 — Universal Extraction Overhaul (COMPLETE)**
- 6-tier extraction cascade: JSON-LD → Microdata → Open Graph → DOM Discovery → CSS (50+ selectors) → Validated Fallback
- Noise filtering rejects nav labels, section headers, items without product signals
- Quality-based confidence scoring (weighted by name/price/image, not field coverage)
- PKR + 30 other currencies with domain-priority disambiguation

**Phase 8 — Pro-Level Operational Upgrades (COMPLETE)**
- Browser resource blocking (images/CSS/fonts/ads) — 60-80% faster page loads
- API/XHR interception — captures JSON payloads from SPAs
- URL-level deduplication — prevents scraping the same URL twice
- Post-extraction data validation — rejects garbage (zero prices, placeholder names, fake images)

**Phase 9 — HYDRA: Universal Scraper Upgrade (PLANNED)**
- Codename: HYDRA — Hybrid Universal Discovery & Retrieval Architecture
- Spec: `HYDRA_REVISION_SPEC_PROMPT.md` (751 lines, 10 modules, 7 sprints)
- Competitive analysis: `docs/COMPETITIVE_ANALYSIS.md` (308 lines, 27 platforms compared)
- Research source: `docs/WEB_SCRAPERS_INDUSTRY_CATALOG.md` (2466 lines, 35+ commercial + 30+ OSS)
- New modules planned:
  1. CrawlManager — full-site recursive crawling (BUILD)
  2. MarkdownConverter — HTML→markdown via trafilatura + html2text (INTEGRATE)
  3. AdaptiveSelectors — self-healing selectors with fuzzy matching (BUILD)
  4. ContentFilter — BM25 relevance filtering via rank-bm25 (INTEGRATE)
  5. ChangeDetector — content diff between crawl runs (BUILD)
  6. MCP Server — AI agent integration (BUILD with mcp SDK)
  7. SearchScraper — URL-less research via Brave Search API (BUILD)
  8. Extraction cascade upgrade — 8→10 tiers (BUILD)
  9. Stealth upgrades — 14→24 device profiles + fingerprint noise (BUILD)
  10. Smart router — response-based reclassification + cost-aware routing (BUILD)
- New dependencies: trafilatura (Apache-2.0), html2text (BSD), rank-bm25 (Apache-2.0), mcp (MIT)
- Target: $0.005/page weighted average (4-10x cheaper than competitors)
- Scope: Scraping infrastructure ONLY — API connectors (Keepa, eBay, etc.) untouched

## Coding Conventions

- Use Pydantic v2 for all data models
- Use `async def` for all I/O operations
- Use Protocol classes for interfaces (not ABC)
- Use structlog for logging
- Tests go in `tests/` mirroring the source structure
- No hardcoded secrets — always env vars or secrets manager
- No `print()` statements — use logging
- Type hints on all function signatures
- No hyphens in Python package directory names — use underscores or symlinks
- Use lazy initialization for clients (create on first request, not import time)

## Important Files

| File | Purpose |
|------|---------|
| `docs/final_specs.md` | Full platform specification (1233 lines, 24 sections) |
| `docs/tasks_breakdown.md` | 69 tasks across 24 epics with dependency graph |
| `docs/qa_strategy.md` | Use-case-based QA plan (18 phases, 170+ use cases) |
| `docs/qa_execution_log.md` | Chronological record of every QA test run |
| `system/todo.md` | Current task queue |
| `system/execution_trace.md` | Decision audit trail |
| `system/development_log.md` | Engineering log |
| `system/lessons.md` | What we've learned (88 lessons) |
| `system/final_step_logs.md` | Per-task execution evidence |

## Key New Modules (Phase 6-8)

| File | Purpose |
|------|---------|
| `packages/core/device_profiles.py` | 14 coherent browser identity profiles for anti-detection |
| `packages/core/human_behavior.py` | Bezier mouse curves, scroll simulation, idle jitter, warm-up nav |
| `packages/connectors/http_collector.py` | curl_cffi HTTP client with TLS/JA3 browser impersonation |
| `packages/connectors/hard_target_worker.py` | Camoufox stealth browser + Playwright fallback |
| `packages/connectors/browser_worker.py` | Resource blocking, API interception, device profiles, Load More |
| `packages/core/url_discovery.py` | Sitemap.xml parser + robots.txt compliance checker |
| `packages/core/circuit_breaker.py` | Per-domain circuit breaker (CLOSED/OPEN/HALF_OPEN) |
| `packages/core/waf_token_manager.py` | AWS WAF token lifecycle (Amazon cookie management) |
| `packages/core/response_cache.py` | Two-tier HTTP response cache (memory LRU + disk) |
| `packages/connectors/keepa_connector.py` | Keepa API connector for Amazon product data (replaces browser scraping) |
| `packages/connectors/google_sheets_connector.py` | Google Sheets read/write + Keepa cache layer |
| `packages/connectors/google_maps_connector.py` | Google Maps business scraper (Places API + SerpAPI + browser) |

## Legacy Code (scraper_pro/)

The `scraper_pro/` directory contains the original Scrapling Pro v3.0 code. It is **reference only** — do not import from it in new code. Reusable components are being ported to `packages/`.

| Legacy File | Port Destination |
|-------------|-----------------|
| core/fallback_chain.py | packages/core/fallback.py |
| proxy_manager.py | packages/connectors/proxy_adapter.py |
| ai_scraper_v3.py (GeminiAI) | packages/core/ai_providers/gemini.py |
| smart_exporter.py | packages/core/exporter.py |
| engine_v2.py (CaptchaSolver) | packages/connectors/captcha_adapter.py |
| core/smart_extractors.py | packages/contracts/ + packages/core/normalizer.py |
