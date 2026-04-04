# SUPER PROMPT: AI Scraping Platform vs Industry — Comprehensive Comparison Analysis

> **EXECUTION MANDATE:** This prompt triggers the MANDATORY PRE-TASK PROTOCOL from `~/.claude/CLAUDE.md` and `CLAUDE.md`. Follow every step. No shortcuts.

---

## STEP 0: GLOBAL CONFIG LOAD (MANDATORY)

```
READ: ~/.claude/CLAUDE.md OR .claude/CLAUDE.md
LOAD: Agent hierarchy, MCP servers, skills, commands, autonomy rules
```

## STEP 1: TASK CLASSIFICATION

```
TYPE: RESEARCH + ARCHITECTURE + PRODUCT STRATEGY
AGENTS: ALL — this is a FULL FEATURE analysis
  → architect-1 + architect-2 (architecture comparison)
  → engineer-1 + engineer-2 (code audit + capability mapping)
  → product-1 + product-2 (competitive positioning + gap analysis)
  → security-1 + security-2 (anti-bot + stealth comparison)
  → qa-1 + qa-2 (test coverage + observability comparison)
```

## STEP 2: TOOL SELECTION

```
MCP SERVERS:
  → exa: Research competitors' latest features, changelogs, updates
  → firecrawl: Scrape competitor docs for capability verification
  → context7: Look up FastAPI, Pydantic, Playwright, curl_cffi, Camoufox latest docs
  → github: Search our repo for all implemented features, modules, functions
  → claude-mem: Store findings for cross-session recall

SKILLS:
  → competitive-teardown (primary)
  → senior-architect (architecture comparison)
  → senior-backend (code audit)
  → deep-research (industry analysis)
  → product-strategist (positioning)
  → spec-driven-workflow (structured output)

COMMANDS:
  → /plan (decompose this analysis)
  → /docs (generate final document)
```

## STEP 3: READ PROJECT STATE

```
READ these files IN THIS ORDER before starting analysis:

1. CLAUDE.md (project architecture, current phase, tech stack, conventions)
2. docs/final_specs.md (full platform specification — SOURCE OF TRUTH, 1233 lines)
3. docs/tasks_breakdown.md (69 tasks, 24 epics — what was built)
4. system/lessons.md (88 lessons learned)
5. system/execution_trace.md (latest 10 entries)

THEN READ every source file to map actual implemented capabilities:
6. packages/contracts/ → ALL Pydantic schemas (Task, Policy, Session, Run, Result, Artifact, Billing)
7. packages/core/ → ALL core modules:
   - router.py (ExecutionRouter — lane selection logic)
   - device_profiles.py (14 browser identity profiles)
   - human_behavior.py (Bezier mouse, scroll sim, idle jitter)
   - url_discovery.py (sitemap parser + robots.txt)
   - circuit_breaker.py (per-domain CLOSED/OPEN/HALF_OPEN)
   - waf_token_manager.py (AWS WAF token lifecycle)
   - response_cache.py (two-tier: memory LRU + disk)
   - normalizer.py (data normalization)
   - fallback.py (fallback chain)
   - exporter.py (smart export)
   - ai_providers/ (Gemini, OpenAI, Anthropic, Ollama)
8. packages/connectors/ → ALL connectors:
   - http_collector.py (curl_cffi with TLS/JA3 impersonation)
   - hard_target_worker.py (Camoufox stealth + Playwright fallback)
   - browser_worker.py (resource blocking, API intercept, Load More)
   - proxy_adapter.py (proxy rotation)
   - captcha_adapter.py (CAPTCHA solving)
   - api_connector.py (API-based extraction)
   - keepa_connector.py (Amazon product data)
   - google_sheets_connector.py (Sheets read/write)
   - google_maps_connector.py (Places API + SerpAPI)
9. services/control-plane/ → FastAPI endpoints, CRUD, health, auth
10. services/worker-http/ → HTTP lane worker
11. services/worker-browser/ → Browser lane worker
12. services/worker-ai/ → AI normalization worker
13. services/worker-hard-target/ → Hard-target stealth worker
14. apps/web/ → React + Vite web dashboard
15. apps/desktop/ → Tauri v2 Windows EXE
16. apps/extension/ → Chrome Manifest V3 extension
17. apps/companion/ → Native messaging host
18. infrastructure/ → Docker, Terraform, Helm
19. tests/ → unit + integration + e2e (706 tests passing)
```

---

## STEP 4: EXECUTE — THE ANALYSIS

### INPUT DOCUMENTS

**Document A — Industry Research Report:**
File: `WEB_SCRAPERS_INDUSTRY_CATALOG.md` (2,466 lines)
Contains: 35+ commercial products, 30+ OSS projects, detailed capability profiles across 15+ dimensions per platform

**Document B — Our Platform (AI Scraping Platform / Scraper-App):**
Files: All source code in this repo + `docs/final_specs.md` + `CLAUDE.md`

### ANALYSIS FRAMEWORK — 15 Comparison Dimensions

For EACH of the following dimensions, compare our platform against EVERY product/framework in the research report:

#### DIMENSION 1: Acquisition & Crawling
- [ ] Full-site recursive crawling
- [ ] Sitemap parsing + robots.txt compliance
- [ ] URL deduplication
- [ ] Pagination handling (click, scroll, URL patterns)
- [ ] Request queue with priority and dedup
- [ ] Concurrent crawling with rate limiting
- [ ] Incremental / delta crawling
- [ ] Politeness controls (delays, max requests)
- [ ] Frontier management
- [ ] Depth / scope controls

#### DIMENSION 2: Rendering & Browser
- [ ] Headless browser (Chromium/Firefox/WebKit)
- [ ] JS rendering for SPAs
- [ ] Browser pool management
- [ ] Screenshot / PDF capture
- [ ] Resource blocking (images/CSS/fonts/ads)
- [ ] API/XHR interception
- [ ] "Load More" / infinite scroll handling
- [ ] CDP (Chrome DevTools Protocol) access
- [ ] Multi-browser support

#### DIMENSION 3: Anti-Blocking & Stealth
- [ ] Proxy rotation (datacenter, residential, ISP, mobile)
- [ ] TLS/JA3 fingerprint impersonation
- [ ] C++ level stealth (Camoufox vs CDP-based)
- [ ] Device profile coherence (UA + headers + JS fingerprint alignment)
- [ ] CAPTCHA detection and solving
- [ ] Cloudflare / DataDome / Kasada bypass
- [ ] Human behavioral simulation (mouse curves, scroll patterns, typing delays)
- [ ] Warm-up navigation / Google referrer chains
- [ ] Geo-region targeting
- [ ] Blocked request detection + auto-retry
- [ ] Fingerprint randomization per session
- [ ] Browser header spoofing
- [ ] ScrapeOps benchmark score comparison (if available)

#### DIMENSION 4: Extraction & Structuring
- [ ] CSS / XPath selectors
- [ ] JSON-LD extraction
- [ ] Microdata / Open Graph extraction
- [ ] DOM discovery with noise filtering
- [ ] AI/LLM-based extraction (natural language prompts)
- [ ] Schema-bound structured JSON output
- [ ] Adaptive selectors (survive layout changes)
- [ ] 6-tier extraction cascade (our unique feature)
- [ ] Quality-based confidence scoring
- [ ] Currency detection and disambiguation
- [ ] Post-extraction data validation (reject garbage)
- [ ] Markdown output for LLM consumption
- [ ] PDF / DOCX parsing

#### DIMENSION 5: AI & Intelligence
- [ ] Multi-provider AI (Gemini, OpenAI, Anthropic, Ollama)
- [ ] AI as augmentation (deterministic first, AI for repair/routing)
- [ ] AI normalization of extracted data
- [ ] Natural language extraction prompts
- [ ] Knowledge Graph construction
- [ ] Computer vision page-type detection
- [ ] Adaptive learning (selectors learn over time)
- [ ] BM25 content filtering
- [ ] AI routing (auto-select extraction strategy)

#### DIMENSION 6: Orchestration & Architecture
- [ ] Execution lanes (HTTP / Browser / Hard-target / AI)
- [ ] Smart routing between lanes based on site difficulty
- [ ] Fallback chains (primary → secondary → tertiary)
- [ ] Contract-driven architecture (Pydantic schemas)
- [ ] Microservices (control plane + workers)
- [ ] Queue-based task distribution (Redis/BullMQ)
- [ ] Circuit breaker (per-domain)
- [ ] Rate limit enforcement + quota management
- [ ] Webhook callbacks (HMAC-SHA256 signed)
- [ ] Task scheduler (cron/interval)
- [ ] Policy-based scraping rules

#### DIMENSION 7: Session Memory & State
- [ ] Cookie persistence
- [ ] Browser session reuse
- [ ] Storage persistence (localStorage, sessionStorage)
- [ ] Resumable crawls / checkpointing
- [ ] Session pool with rotation
- [ ] Persistent browser profiles
- [ ] WAF token lifecycle management (Amazon cookies)
- [ ] storageState-level session persistence

#### DIMENSION 8: Logging & Observability
- [ ] Run / job history
- [ ] Request/network logs
- [ ] Browser/debug logs
- [ ] Session replay
- [ ] Screenshots on error
- [ ] Trace viewer (HAR, video)
- [ ] Metrics dashboard
- [ ] Alerting / webhooks on failure
- [ ] Structured logging (structlog)
- [ ] Per-domain circuit breaker status

#### DIMENSION 9: Output & Storage
- [ ] JSON / JSONL / CSV / XML / Excel export
- [ ] Cloud storage (S3-compatible)
- [ ] Filesystem (desktop mode)
- [ ] Database (PostgreSQL / SQLite)
- [ ] Webhook delivery
- [ ] Dataset management
- [ ] Google Sheets integration
- [ ] Smart exporter (auto-format selection)

#### DIMENSION 10: Multi-Platform Delivery
- [ ] Web dashboard (SaaS)
- [ ] Desktop application (EXE / native)
- [ ] Browser extension
- [ ] CLI
- [ ] REST API
- [ ] SDKs (Python, Node, etc.)
- [ ] MCP server for AI agents
- [ ] Native messaging host (companion)
- [ ] Self-hosted Docker deployment

#### DIMENSION 11: Integrations
- [ ] Google Sheets
- [ ] Google Maps / Places API
- [ ] Amazon Keepa connector
- [ ] Zapier / Make / n8n
- [ ] LangChain / LlamaIndex / CrewAI
- [ ] Slack / webhooks
- [ ] Snowflake / data warehouse connectors
- [ ] MCP server integration

#### DIMENSION 12: Enterprise & Governance
- [ ] Multi-tenancy
- [ ] RBAC (role-based access control)
- [ ] Usage quotas per tenant
- [ ] Billing / token bucket
- [ ] Audit trails
- [ ] SOC2 / GDPR compliance
- [ ] Self-hosted option
- [ ] Cloud-agnostic (no vendor lock-in)
- [ ] SLA / dedicated support

#### DIMENSION 13: Infrastructure & DevOps
- [ ] Docker / docker-compose
- [ ] Kubernetes / Helm charts
- [ ] Terraform (AWS/GCP/Azure)
- [ ] CI/CD (GitHub Actions)
- [ ] Auto-scaling
- [ ] Distributed queue (Redis)
- [ ] In-memory fallback (desktop mode)

#### DIMENSION 14: E-Commerce Specific
- [ ] Shopify detection + JSON API extraction
- [ ] Amazon product data (Keepa integration)
- [ ] Product listing page (PLP) extraction
- [ ] Product detail page (PDP) extraction
- [ ] Price monitoring
- [ ] Currency handling (30+ currencies)
- [ ] VAT/tax detection (ex/inc VAT label)

#### DIMENSION 15: Pricing & Business Model
- [ ] Open-source / self-hosted option
- [ ] Credit-based pricing
- [ ] Subscription tiers
- [ ] Per-request billing
- [ ] Free tier
- [ ] Enterprise custom pricing
- [ ] Desktop (one-time purchase potential)
- [ ] Cost transparency

---

### OUTPUT REQUIREMENTS

Produce a single comprehensive document with these sections:

#### SECTION 1: Executive Summary (1 page)
- Our platform's competitive position in 3 sentences
- Top 5 unique advantages we have that NO competitor offers
- Top 5 critical gaps we need to fill
- Overall market positioning statement

#### SECTION 2: Feature-by-Feature Comparison Matrix
Create a table with:
- Rows: Every sub-item from all 15 dimensions above (~150+ features)
- Columns: Our Platform | Apify | Bright Data | Browserless | Browserbase | Firecrawl | Crawl4AI | Scrapy | Crawlee | Diffbot | Scrapling | ScrapingBee | ScraperAPI | Scrapfly | Oxylabs | ZenRows | Zyte | Hyperbrowser | Spider | Jina | ScrapeGraphAI | Octoparse | Browse AI | Colly | Katana | Playwright | Puppeteer | Selenium
- Values: ✅ (has it) | ❌ (doesn't have) | 🟡 (partial/basic) | ⭐ (best-in-class)
- Mark OUR features as ⭐ where we're genuinely best-in-class

#### SECTION 3: Detailed Gap Analysis
For each gap identified:
- What the competitor has that we don't
- How critical is it (P0/P1/P2/P3)
- Estimated effort to build (S/M/L/XL)
- Which competitor does it best
- Recommended approach

#### SECTION 4: Our Unique Differentiators (What We Have That They Don't)
For each unique advantage:
- Feature name
- Technical implementation details from our codebase
- Which competitors lack this entirely
- Why it matters for users
- How to message it in marketing

#### SECTION 5: Architecture Comparison
- Compare our monorepo + microservices + multi-platform approach vs each major competitor's architecture
- Identify architectural patterns we use that others don't
- Identify patterns others use that we should consider

#### SECTION 6: Anti-Detection & Stealth Deep Dive
- Detailed comparison of our stealth stack (Camoufox + curl_cffi + 14 device profiles + human behavior sim) vs every competitor
- Map against ScrapeOps benchmark data from the report
- Identify stealth gaps

#### SECTION 7: AI/Intelligence Comparison
- Compare our AI approach (deterministic first, AI as augmentation, multi-provider) vs competitors
- Map our 6-tier extraction cascade vs others' extraction strategies
- Identify AI gaps

#### SECTION 8: Market White-Space Opportunities
- Cross-reference the report's "white-space / underbuilt segments" with our capabilities
- Identify which white-spaces we ALREADY fill
- Identify which we should target next

#### SECTION 9: Strategic Recommendations
- Top 10 features to build next (prioritized)
- Top 5 integrations to add
- Positioning strategy vs each competitor segment
- Go-to-market recommendations based on unique strengths

---

## STEP 5: POST-TASK AUTO-UPDATE

```
AFTER completing the analysis:
1. Save output as: docs/COMPETITIVE_ANALYSIS.md
2. Update system/todo.md with any new tasks identified
3. Update system/execution_trace.md with analysis summary
4. Update system/lessons.md with competitive insights learned
5. Store key findings in claude-mem for future sessions
6. Git commit + push with message: "Add comprehensive competitive analysis vs 28 industry platforms"
```

---

## CONSTRAINTS & QUALITY GATES

1. **NO ASSUMPTIONS** — If a feature isn't found in source code, it's ❌ not 🟡
2. **NO MARKETING LANGUAGE** — Factual capability comparisons only
3. **CITE FILE PATHS** — Every claim about our platform must reference the specific source file and function/class
4. **CITE REPORT LINES** — Every claim about competitors must reference the research report line numbers
5. **EXHAUSTIVE** — Every single platform in the report must appear in the comparison matrix. No platform skipped.
6. **VERIFY BEFORE CLAIMING** — Read actual source code, don't rely on CLAUDE.md descriptions alone
7. **MINIMUM 100 FEATURE ROWS** in the comparison matrix
8. **EVERY GAP gets a priority** (P0 = must have before launch, P1 = competitive disadvantage, P2 = nice to have, P3 = future consideration)

---

## EXECUTION NOTES

- This analysis should take 5-15 tool calls to complete properly
- Use `github` MCP to search our codebase for specific implementations
- Use `exa` to verify competitors' latest capabilities (report may be slightly outdated)
- Use `firecrawl` to scrape competitor docs if needed for verification
- Deploy architect-1 + product-1 + engineer-1 in parallel for maximum coverage
- Store intermediate findings in `claude-mem` in case context runs low
- The final document should be 3,000-8,000 lines for thoroughness
- Output as both `.md` (readable) and `.xlsx` (comparison matrix)
