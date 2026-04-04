# REVISION SPEC PROMPT: UNIVERSAL SCRAPER — PHASE 9
## "Build the Most Advanced Scraper on Earth"
### Codename: HYDRA — Hybrid Universal Discovery & Retrieval Architecture

---

## 🔴 MANDATORY PRE-TASK GATE (FROM ~/.claude/CLAUDE.md)

```
STEP 0 → READ ~/.claude/CLAUDE.md + project CLAUDE.md
STEP 1 → CLASSIFY: FULL FEATURE (ALL agents deployed)
STEP 2 → SELECT TOOLS (see below)
STEP 3 → READ PROJECT STATE (todo, trace, lessons, specs)
STEP 4 → EXECUTE with full autonomy
STEP 5 → POST-TASK auto-update all system files + push
```

### Agent Deployment (ALL 10 agents — this is a FULL FEATURE build)

| Agent | Assignment |
|-------|-----------|
| **architect-1** | OSS integration architecture — dependency graph, interface boundaries, module wiring |
| **architect-2** | Build-vs-integrate decision matrix — cost/reliability/maintenance analysis per module |
| **engineer-1** | Core implementation — new modules, OSS integration code, refactoring |
| **engineer-2** | Worker pipeline rewiring — HTTP/Browser/Hard-Target worker upgrades |
| **product-1** | Feature completeness audit — every research gap mapped to implementation |
| **product-2** | Cost model — compute cost per extraction method, routing optimization |
| **security-1** | Stealth audit — verify all integrated OSS doesn't leak fingerprints |
| **security-2** | Dependency security — CVE scan, license compatibility (no GPL in our BSD codebase unless isolated) |
| **qa-1** | Test strategy — integration tests for every new OSS dependency |
| **qa-2** | Regression testing — ensure existing 706+ tests still pass after refactoring |

### MCP Server Priority

| Server | Use |
|--------|-----|
| **context7** | Get latest docs for EVERY library before integrating (Crawl4AI, Scrapling, Scrapy, html2text, rank-bm25, Parsel, markdownify, trafilatura) |
| **exa** | Research each OSS library's production reliability, known issues, real-world adoption |
| **github** | Check star count, last commit, open issues, bus factor for every OSS dependency |
| **firecrawl** | Test our scraper against Firecrawl's output quality on same URLs |
| **claude-mem** | Store every build-vs-integrate decision with rationale for future sessions |

### Skills to Invoke

| Skill | Purpose |
|-------|---------|
| **senior-architect** | System design for OSS integration boundaries |
| **senior-backend** | Python implementation patterns |
| **tech-stack-evaluator** | Evaluate each OSS option objectively |
| **competitive-teardown** | Verify we match/exceed every competitor capability |
| **llm-cost-optimizer** | Minimize AI extraction costs |
| **dependency-auditor** | Audit all new dependencies |
| **spec-driven-workflow** | Structured output for the revision spec |

---

## SCOPE DEFINITION — WHAT TO TOUCH vs NOT TOUCH

### ✅ IN SCOPE (Scraping Infrastructure Only)

```
packages/core/
  ├── ai_providers/deterministic.py    ← UPGRADE extraction cascade
  ├── ai_providers/social/*.py         ← UPGRADE social extractors
  ├── dom_discovery.py                 ← EVALUATE: replace with Crawl4AI adaptive?
  ├── normalizer.py                    ← UPGRADE: add markdown output
  ├── dedup.py                         ← EVALUATE: replace with better algo?
  ├── url_discovery.py                 ← UPGRADE: full recursive crawl
  ├── response_cache.py                ← KEEP (already good)
  ├── circuit_breaker.py               ← KEEP (already unique)
  ├── waf_token_manager.py             ← KEEP (already unique)
  ├── device_profiles.py               ← UPGRADE: more profiles
  ├── human_behavior.py                ← KEEP (already best-in-class)
  ├── router.py                        ← UPGRADE: smarter routing
  ├── escalation.py                    ← UPGRADE: smarter escalation triggers
  ├── selector_cache.py                ← EVALUATE: replace with adaptive selectors?
  ├── session_persistence.py           ← KEEP (already good)
  ├── rate_limiter.py                  ← KEEP
  ├── quota_manager.py                 ← KEEP
  ├── scheduler.py                     ← KEEP
  ├── NEW: crawl_manager.py            ← BUILD: full-site recursive crawling
  ├── NEW: markdown_converter.py       ← BUILD/INTEGRATE: HTML→markdown
  ├── NEW: content_filter.py           ← BUILD/INTEGRATE: BM25 relevance filtering
  ├── NEW: change_detector.py          ← BUILD: content diff between crawl runs
  ├── NEW: adaptive_selectors.py       ← INTEGRATE: from Crawl4AI or Scrapling
  ├── NEW: mcp_server.py               ← BUILD: MCP server wrapper

packages/connectors/
  ├── http_collector.py                ← KEEP (curl_cffi already best-in-class)
  ├── browser_worker.py                ← UPGRADE: better SPA handling
  ├── hard_target_worker.py            ← UPGRADE: more stealth techniques
  ├── proxy_adapter.py                 ← KEEP
  ├── proxy_providers/*.py             ← KEEP
  ├── captcha_adapter.py               ← KEEP

services/
  ├── worker-http/worker.py            ← UPGRADE: integrate new modules
  ├── worker-browser/worker.py         ← UPGRADE: integrate new modules
  ├── worker-hard-target/worker.py     ← UPGRADE: integrate new modules
  ├── worker-ai/worker.py              ← UPGRADE: integrate new modules
  ├── control-plane/routers/           ← ADD: new endpoints (/crawl, /search, /extract)
```

### 🚫 OUT OF SCOPE (DO NOT TOUCH)

```
packages/connectors/keepa_connector.py          ← API connector, not scraping
packages/connectors/ebay_connector.py            ← API connector
packages/connectors/walmart_connector.py         ← API connector
packages/connectors/tiktok_connector.py          ← API connector
packages/connectors/shopify_connector.py         ← API connector
packages/connectors/google_maps_connector.py     ← API connector
packages/connectors/google_sheets_connector.py   ← API connector
packages/connectors/apify_adapter.py             ← API connector
services/control-plane/routers/keepa.py          ← API route
services/control-plane/routers/maps.py           ← API route
apps/*                                           ← Frontend unchanged
infrastructure/*                                 ← Infra unchanged
packages/contracts/*                             ← Contracts stable (extend only, don't break)
packages/core/billing.py                         ← Business logic unchanged
packages/core/webhook.py                         ← Already complete
packages/core/metrics.py                         ← Already complete
packages/core/tracing.py                         ← Already complete
packages/core/logging_config.py                  ← Already complete
```

---

## DECISION FRAMEWORK: BUILD vs INTEGRATE vs KEEP

For EVERY module, apply this decision matrix BEFORE writing code:

```
┌──────────────────────────────────────────────────────────────────┐
│  DECISION MATRIX (apply to each module)                         │
│                                                                  │
│  Q1: Does a battle-tested OSS library exist for this?           │
│    YES → Q2                                                      │
│    NO  → BUILD from scratch                                      │
│                                                                  │
│  Q2: Is the OSS library actively maintained (commits <90 days)? │
│    YES → Q3                                                      │
│    NO  → BUILD (dead libraries = tech debt)                      │
│                                                                  │
│  Q3: Is the license compatible (MIT/BSD/Apache)?                │
│    YES → Q4                                                      │
│    NO  → Q4b (AGPL/GPL = isolate or avoid)                      │
│                                                                  │
│  Q4: Does it match our async Python architecture?               │
│    YES → Q5                                                      │
│    NO  → WRAP in async adapter or BUILD                          │
│                                                                  │
│  Q5: Is our existing code BETTER than the OSS?                  │
│    YES → KEEP our code                                           │
│    NO  → REPLACE with OSS                                        │
│    EQUAL → KEEP (avoid churn)                                    │
│                                                                  │
│  Q4b: Can the AGPL component run as isolated subprocess/service?│
│    YES → INTEGRATE as isolated service                           │
│    NO  → BUILD our own (avoid license contamination)             │
└──────────────────────────────────────────────────────────────────┘
```

**Cost Rule:** Every decision must consider scraping cost. If an OSS library reduces per-page cost (e.g., avoiding browser when HTTP suffices, avoiding LLM when deterministic works), it wins over a "cooler" alternative.

---

## MODULE-BY-MODULE REVISION SPEC

### MODULE 1: Full-Site Recursive Crawl Manager
**Gap:** We can scrape individual URLs and paginated lists, but can't recursively crawl entire sites.
**Competitors who have this:** Scrapy (best), Crawlee, Firecrawl /crawl, Crawl4AI

**Decision Analysis:**

| Option | Pros | Cons | Cost | Verdict |
|--------|------|------|------|---------|
| **Integrate Scrapy** | 17 years battle-tested, 53K stars, best crawl framework ever built | Twisted async model conflicts with our asyncio; heavyweight dependency; would need to rewrite our workers | High integration cost | ❌ REJECT — architectural mismatch |
| **Integrate Crawl4AI crawler** | Async Python, modern, Playwright-based, 58K stars | Solo maintainer (bus factor 1), no crawl-level queue persistence, immature crawl manager | Medium risk | 🟡 PARTIAL — borrow patterns, don't depend |
| **Build CrawlManager on our existing architecture** | Uses our existing queue, router, workers, dedup, circuit breaker; full control | Development time | Low ongoing cost | ✅ BUILD |

**Spec: Build `packages/core/crawl_manager.py`**

```
CrawlManager:
  - Input: seed URL(s), crawl config (max_depth, max_pages, url_patterns, follow_external)
  - Uses: url_discovery.py (sitemaps, robots.txt), dedup.py (URL dedup), router.py (lane selection per URL)
  - Queue: Redis-backed priority queue (reuse packages/core/storage/redis_queue.py)
  - Link extraction: Parse <a href> from every page, filter by scope rules
  - Output: Dataset (JSON/JSONL/CSV) or webhook callback per page
  - Politeness: Respect crawl-delay from robots.txt, configurable per-domain rate
  - Resume: Persist queue state, support stop/resume by crawl_id
  - Depth tracking: BFS with depth counter, respect max_depth
  
  BORROW from Scrapy:
    - URL filtering patterns (allow/deny regex — Scrapy's LinkExtractor approach)
    - Crawl depth tracking pattern
    - Stats collection pattern (pages/sec, items/sec, errors)
  
  BORROW from Crawl4AI:
    - Async-native design
    - Parallel page processing with semaphore
  
  DO NOT import Scrapy or Crawl4AI as dependencies. Implement the patterns in our code.
```

**New API endpoints:**
```
POST /crawl       — start a crawl job (returns crawl_id)
GET  /crawl/{id}  — get crawl status + stats
GET  /crawl/{id}/results — get extracted data
POST /crawl/{id}/stop — stop a running crawl
```

---

### MODULE 2: Markdown Output for LLM/RAG
**Gap:** We output JSON only. Firecrawl, Crawl4AI, Jina Reader, Spider all output clean markdown.
**Competitors who have this:** Firecrawl (best), Crawl4AI, Jina Reader, Spider

**Decision Analysis:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **`html2text`** (pip, BSD) | Fast, lightweight, 1.5K stars, well-maintained | Doesn't clean nav/footer/ads | 🟡 Use as base layer |
| **`markdownify`** (pip, MIT) | Better table/image handling than html2text | Same nav/footer issue | 🟡 Alternative base |
| **`trafilatura`** (pip, Apache-2.0) | Extracts article content, strips boilerplate, 4K+ stars, academic-backed | Best content extraction but slower | ✅ USE for content cleaning |
| **`readability-lxml`** (pip, Apache-2.0) | Mozilla Readability port, strips chrome/nav/ads | Good but less maintained | 🟡 Fallback option |
| **Build custom** | Full control | Reinventing the wheel | ❌ REJECT |

**Spec: Build `packages/core/markdown_converter.py`**

```
MarkdownConverter:
  - Step 1: Clean HTML with trafilatura (strip nav, footer, ads, chrome)
  - Step 2: Convert cleaned HTML to markdown with html2text or markdownify
  - Step 3: Post-process markdown (fix broken links, remove empty sections)
  
  Dependencies:
    - trafilatura (Apache-2.0) — content extraction + boilerplate removal
    - html2text (BSD) — HTML→markdown conversion
  
  Integration point: Add output_format parameter to all workers
    output_format="json" (default, existing behavior)
    output_format="markdown" (new, returns cleaned markdown)
    output_format="html" (returns cleaned HTML via trafilatura)
    output_format="raw" (returns raw HTML, no processing)
  
  LLM-readiness features:
    - Strip all script/style tags
    - Convert tables to markdown tables
    - Preserve heading hierarchy
    - Convert images to ![alt](url) format
    - Max token estimation for LLM context fitting
```

---

### MODULE 3: Adaptive Selectors (Survive Layout Changes)
**Gap:** Our selectors break when sites redesign. Crawl4AI and Scrapling both have adaptive selectors.
**Competitors who have this:** Crawl4AI (Adaptive Intelligence), Scrapling (adaptive selectors with auto_save)

**Decision Analysis:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **Integrate Scrapling's adaptive selectors** | BSD-3, Python, TLS impersonation built-in, 7.1K stars, Scrapy-like API | Solo maintainer, relatively young (2024), brings its own browser stack | 🟡 Borrow pattern, don't import whole lib |
| **Integrate Crawl4AI's adaptive learning** | Apache-2.0, 58K stars, learns selectors over time | Solo maintainer, heavy dependency (Playwright + LLM), immature adaptive feature | 🟡 Borrow pattern |
| **Build our own using selector fingerprinting** | Use our existing selector_cache.py as foundation, add fuzzy matching | Development time but full control | ✅ BUILD (extend existing) |

**Spec: Upgrade `packages/core/selector_cache.py` → `packages/core/adaptive_selectors.py`**

```
AdaptiveSelectorEngine:
  - Extends existing SelectorCache with fuzzy matching
  - Stores: selector → (element_text_sample, structural_fingerprint, last_success_time)
  - On extraction failure:
    1. Load last-known-good selectors for domain
    2. Fuzzy-match against current DOM structure (Levenshtein on tag paths)
    3. If match found (similarity > 0.7): use adapted selector, log drift
    4. If no match: fall through to DOM auto-discovery
    5. If DOM discovery succeeds: store NEW selectors as updated cache
  - Self-healing: selectors auto-update when sites change layout
  - Persistence: JSON files per domain (same pattern as SelectorCache)
  
  BORROW from Scrapling:
    - "Similar" matching — find elements by text/attribute similarity when CSS breaks
    - Auto-save of working selectors after each successful extraction
  
  BORROW from Crawl4AI:
    - Learning loop — track selector success rate over time, decay stale selectors
  
  NO external dependency needed — pure Python with our existing BeautifulSoup stack.
```

---

### MODULE 4: BM25 Content Relevance Filtering
**Gap:** We return everything extracted. Crawl4AI filters by relevance using BM25.
**Competitor who has this:** Crawl4AI (BM25 content filtering)

**Decision Analysis:**

| Option | Pros | Cons | Verdict |
|--------|------|------|---------|
| **`rank-bm25`** (pip, Apache-2.0) | 600+ stars, lightweight, pure Python BM25 | Simple but does the job | ✅ INTEGRATE |
| **Build custom BM25** | Full control | BM25 is a well-defined algorithm, no need to reinvent | ❌ REJECT |

**Spec: Build `packages/core/content_filter.py`**

```
ContentFilter:
  - Uses rank-bm25 library for relevance scoring
  - Input: extracted items + user query/keywords
  - Output: items sorted by relevance, items below threshold removed
  - Integration: Optional parameter on extraction — relevance_query="gaming laptop"
  - Also supports: keyword filtering, price range filtering, field-exists filtering
  
  Dependency: rank-bm25 (Apache-2.0)
```

---

### MODULE 5: Change Detection / Content Diffing
**Gap:** Nobody in the market does this well (identified market white-space).
**Competitors:** None do this well — this is greenfield competitive advantage.

**Spec: Build `packages/core/change_detector.py`**

```
ChangeDetector:
  - Compares two crawl snapshots (by crawl_id or URL + timestamps)
  - Detects: new items, removed items, price changes, field changes
  - Output: diff report (JSON) with change_type per item
  - Storage: Uses response_cache.py for historical snapshots
  - Alerts: Integrates with webhook.py for change notifications
  
  Algorithm:
    1. Match items across snapshots by product_url or (name + domain)
    2. For matched items: field-by-field comparison
    3. Unmatched in new: "added"
    4. Unmatched in old: "removed"
    5. Price changes: absolute + percentage delta
  
  Use cases:
    - Price monitoring (alert when price drops >10%)
    - Competitor tracking (new products added)
    - Content monitoring (article changes)
  
  NO external dependency — pure Python dict comparison + our existing normalizer.
```

---

### MODULE 6: MCP Server for AI Agent Integration
**Gap:** Firecrawl, Browserless, Bright Data, Hyperbrowser, Spider all have MCP servers. We don't.
**This is P0 — without it, AI agents can't use our scraper.**

**Spec: Build `packages/core/mcp_server.py` + `mcp_server/` service**

```
MCP Server:
  - Protocol: Model Context Protocol (MCP) via @modelcontextprotocol/sdk
  - Exposes tools:
    - scrape(url, output_format) → extract data from a single URL
    - crawl(url, max_depth, max_pages) → recursive site crawl
    - search(query) → web search + scrape top results
    - extract(url, schema) → structured extraction with JSON schema
    - route(url) → dry-run routing decision (which lane would handle this?)
  - Auth: API key in MCP config
  - Transport: SSE (Server-Sent Events) for streaming results
  
  Implementation: Python MCP server using mcp library (MIT)
  Deployment: Standalone service or embedded in control-plane
  
  Dependency: mcp (MIT) — official MCP Python SDK
```

---

### MODULE 7: /search Endpoint (URL-less Research)
**Gap:** We require explicit URLs. Firecrawl's /search and /agent enable URL-less research.

**Spec: Add search capability to control-plane**

```
SearchScraper:
  - Input: natural language query (e.g., "best gaming laptops 2026")
  - Step 1: Send query to search API (SerpAPI, Brave Search, or Google Custom Search)
  - Step 2: Extract top N result URLs
  - Step 3: Scrape each URL through our normal pipeline (router → worker → extraction)
  - Step 4: Return aggregated structured data
  
  API options (by cost):
    1. Brave Search API (free tier: 2000 queries/month) — cheapest
    2. SerpAPI ($50/month for 5000 searches) — most reliable
    3. Google Custom Search ($5/1000 queries) — official but expensive
  
  New endpoint:
    POST /search { query, max_results, output_format }
  
  NO new dependency beyond HTTP client — we already have httpx/curl_cffi.
```

---

### MODULE 8: Extraction Pipeline Upgrades

#### 8A: Upgrade Deterministic Extraction Cascade

**Current: 8 tiers. Target: 10 tiers with smarter ordering.**

```
UPGRADED EXTRACTION CASCADE (10 tiers):
  0. Social media platform-specific (KEEP — already best-in-class, 5 platforms)
  0b. Custom CSS selectors from user/policy (KEEP)
  1. JSON-LD (KEEP)
  2. Microdata / RDFa (KEEP)
  3. Open Graph (KEEP)
  4. NEW: Adaptive selectors (from selector cache, fuzzy-matched)
  5. DOM auto-discovery (KEEP — already unique)
  6. CSS pattern extraction with 50+ selectors (KEEP)
  7. NEW: trafilatura content extraction (for article/blog/non-product pages)
  8. Validated basic fallback (KEEP)
  9. NEW: LLM extraction ONLY when all deterministic tiers fail AND confidence < 0.3
```

**Key principle: LLM is the LAST resort, not the first. Every deterministic tier we add saves $0.01-0.10 per page in LLM costs.**

#### 8B: Social Media Extraction Upgrades

**Current: 5 platforms (Amazon, YouTube, TikTok, Instagram, Facebook)**
**Target: 7 platforms (add Twitter/X, LinkedIn)**

```
NEW: packages/core/ai_providers/social/twitter.py
  - Extract tweets, profiles, threads from embedded JSON (__NEXT_DATA__, initial state)
  - Handle both twitter.com and x.com domains
  - No API needed — parse the hydrated HTML

NEW: packages/core/ai_providers/social/linkedin.py
  - Extract profiles, job listings, company pages from embedded JSON
  - Handle li_fat_id cookies for session continuity
  - NOTE: LinkedIn is hard-target — always routes through Camoufox
```

#### 8C: JavaScript SPA Deep Extraction

**Current: Browser worker renders JS but doesn't intelligently wait for data.**
**Gap: Many SPAs load data via XHR after initial render. We need smarter waiting.**

```
UPGRADE browser_worker.py:
  - Smart Wait: Instead of fixed timeout, wait until:
    1. Network idle (no pending XHR/fetch for 2 seconds)
    2. OR specific element appears (product grid, results container)
    3. OR mutation observer detects DOM stability (no new nodes for 1.5 seconds)
  - SPA Router Detection: Detect React/Vue/Angular router, intercept route changes
  - Lazy Load Trigger: Scroll to trigger lazy-loaded images and content
  - Shadow DOM Penetration: Extract from shadow DOM roots (Web Components)
  
  BORROW from Firecrawl:
    - "Smart Wait" pattern — auto-detect when dynamic content has finished loading
  
  BORROW from Crawl4AI:
    - Wait-for-CSS-selector strategy before extraction
```

---

### MODULE 9: Enhanced Stealth Upgrades

#### 9A: More Device Profiles

**Current: 14 profiles. Target: 24+ profiles.**

```
UPGRADE device_profiles.py:
  ADD profiles for:
    - Chrome on Android (3 profiles: Samsung, Pixel, OnePlus)
    - Chrome on iOS (iPad)
    - Safari on iOS (iPhone 15, iPhone 14)
    - Firefox on Linux (Ubuntu, Fedora)
    - Edge on Windows (2 profiles)
    - Brave on Windows
    - Samsung Internet on Android
  
  Each profile must have COHERENT:
    - User-Agent, sec-ch-ua headers
    - Screen resolution, viewport, devicePixelRatio
    - navigator.platform, navigator.userAgent
    - Timezone, locale, language
    - WebGL vendor/renderer strings
    - curl_cffi impersonate target
```

#### 9B: Anti-Bot Bypass Enhancements

```
UPGRADE hard_target_worker.py:
  - Add: Canvas fingerprint noise injection (per-session random offset)
  - Add: WebGL fingerprint noise (vertex shader micro-perturbation)
  - Add: AudioContext fingerprint noise
  - Add: Battery API spoofing (always report "charging, 100%")
  - Add: Timezone spoofing aligned with proxy geo
  - Add: navigator.webdriver = false (already done via Camoufox, verify)
  
  BORROW from Scrapling:
    - Cloudflare Turnstile bypass technique (if documented)
    
  BORROW from puppeteer-extra-plugin-stealth:
    - WebGL vendor/renderer override pattern
    - Chrome.runtime check evasion
```

---

### MODULE 10: Smart Router Upgrades

**Current: Domain-based routing with manual lists.**
**Target: ML-light routing with automatic domain classification.**

```
UPGRADE router.py:
  - Add: Response-based reclassification
    After HTTP fetch, if response contains Cloudflare challenge markers → auto-reclassify domain as BROWSER
    After browser fetch, if still blocked → auto-reclassify as HARD_TARGET
    Store reclassification in _site_profiles (persisted across sessions)
  
  - Add: Content-type routing
    RSS/XML feeds → HTTP (no browser needed)
    JSON APIs → HTTP (no browser needed)  
    PDF/DOC → HTTP + document parser
    HTML with <script src="react/vue/angular"> → BROWSER
    HTML with Cloudflare __cf markers → HARD_TARGET
  
  - Add: Cost-aware routing
    HTTP lane: ~$0.001/page (cheapest)
    Browser lane: ~$0.01/page (10x)
    Hard-target lane: ~$0.05/page (50x)
    LLM extraction: ~$0.03-0.10/page (variable)
    
    Route Decision includes estimated_cost field
    Quota manager tracks actual cost per tenant
```

---

## OSS DEPENDENCY SUMMARY

### New Dependencies to Add

| Package | Version | License | Purpose | Size | Risk |
|---------|---------|---------|---------|------|------|
| `trafilatura` | latest | Apache-2.0 | HTML→clean content extraction (boilerplate removal) | ~5MB | Low — academic-backed, 4K+ stars |
| `html2text` | latest | BSD | HTML→markdown conversion | <1MB | Low — mature, well-maintained |
| `rank-bm25` | latest | Apache-2.0 | BM25 relevance scoring | <100KB | Low — lightweight, focused |
| `mcp` | latest | MIT | MCP server SDK | ~2MB | Low — official SDK |

### Existing Dependencies to KEEP (Already Best-in-Class)

| Package | Why Keep |
|---------|---------|
| `curl_cffi` | No OSS alternative matches its TLS/JA3 impersonation |
| `camoufox` | No alternative for C++-level stealth |
| `playwright` | Industry standard browser automation |
| `beautifulsoup4` | Stable, ubiquitous HTML parser |
| `pydantic` v2 | Our contract system depends on it |
| `fastapi` | Our API framework |
| `httpx` | Fallback HTTP client |

### Dependencies Considered but REJECTED

| Package | License | Why Rejected |
|---------|---------|-------------|
| `scrapy` | BSD | Twisted async model incompatible with our asyncio architecture |
| `crawlee` | Apache-2.0 | TypeScript only — no Python version |
| `crawl4ai` | Apache-2.0 | Too heavy as dependency (bundles Playwright + LLM); we borrow patterns instead |
| `scrapling` | BSD-3 | Too young, solo maintainer; we borrow adaptive selector pattern instead |
| `firecrawl` | AGPL-3.0 | License incompatible with our codebase; we build equivalent |
| `markdownify` | MIT | html2text + trafilatura covers our needs |
| `readability-lxml` | Apache-2.0 | trafilatura is better maintained and more feature-complete |

---

## IMPLEMENTATION PLAN — SPRINT BREAKDOWN

### Sprint 1: Foundation (Week 1)
```
TASK 1.1: Install new dependencies (trafilatura, html2text, rank-bm25, mcp)
TASK 1.2: Build markdown_converter.py (trafilatura + html2text)
TASK 1.3: Build content_filter.py (rank-bm25 integration)
TASK 1.4: Add output_format parameter to all workers
TASK 1.5: Tests for markdown output + BM25 filtering
```

### Sprint 2: Crawl Manager (Week 2)
```
TASK 2.1: Build crawl_manager.py (BFS crawler with queue + dedup)
TASK 2.2: Link extraction from HTML (parse <a href>, filter by scope)
TASK 2.3: Crawl state persistence (Redis-backed, resumable)
TASK 2.4: Add /crawl, /crawl/{id}, /crawl/{id}/results endpoints
TASK 2.5: Tests for recursive crawling (mock sites)
```

### Sprint 3: Adaptive Selectors + Change Detection (Week 3)
```
TASK 3.1: Upgrade selector_cache.py → adaptive_selectors.py
TASK 3.2: Fuzzy selector matching (Levenshtein on tag paths)
TASK 3.3: Selector auto-update on successful extraction
TASK 3.4: Build change_detector.py (diff between crawl snapshots)
TASK 3.5: Tests for selector adaptation + change detection
```

### Sprint 4: Extraction Pipeline Upgrade (Week 4)
```
TASK 4.1: Add trafilatura tier to extraction cascade (tier 7)
TASK 4.2: Add adaptive selector tier to cascade (tier 4)
TASK 4.3: Build twitter.py social extractor
TASK 4.4: Build linkedin.py social extractor
TASK 4.5: Upgrade browser_worker.py with smart wait + shadow DOM
TASK 4.6: Tests for all new extraction tiers
```

### Sprint 5: Stealth + Router Upgrades (Week 5)
```
TASK 5.1: Add 10 new device profiles (mobile, Edge, Brave, Samsung)
TASK 5.2: Add canvas/WebGL/audio fingerprint noise
TASK 5.3: Upgrade router.py with response-based reclassification
TASK 5.4: Add cost-aware routing (estimated_cost in RouteDecision)
TASK 5.5: Tests for new profiles + stealth evasion + routing
```

### Sprint 6: MCP Server + Search (Week 6)
```
TASK 6.1: Build MCP server (scrape, crawl, search, extract, route tools)
TASK 6.2: Build /search endpoint (Brave Search API → scrape results)
TASK 6.3: Add /extract endpoint (structured extraction with JSON schema)
TASK 6.4: Integration tests for MCP + search + extract
TASK 6.5: Full regression test run (all 706+ existing tests must pass)
```

### Sprint 7: Polish + Documentation (Week 7)
```
TASK 7.1: CLI tool (scraper-cli with Click/Typer)
TASK 7.2: Update docs/final_specs.md with all new capabilities
TASK 7.3: Update CLAUDE.md with new module inventory
TASK 7.4: Update system/todo.md, execution_trace.md, lessons.md
TASK 7.5: Final commit + push
```

---

## QUALITY GATES (ENFORCED AT EVERY SPRINT)

```
BEFORE merging any sprint:
  1. ALL existing tests pass (706+ tests — ZERO regressions)
  2. ALL new modules have ≥90% test coverage
  3. ruff lint passes with ZERO warnings
  4. mypy type check passes
  5. No hardcoded secrets
  6. No print() statements (use logging)
  7. All I/O operations are async
  8. Protocol classes for interfaces (not ABC)
  9. Pydantic v2 for any new data models
  10. structlog for all logging
```

---

## COST MODEL — WHY THIS ARCHITECTURE WINS

```
COST PER PAGE (our platform vs competitors):

Our Platform (with smart routing):
  HTTP lane (70% of pages):     $0.001/page  → curl_cffi, no browser
  Browser lane (20% of pages):  $0.010/page  → Playwright, resource blocking
  Hard-target (5% of pages):    $0.050/page  → Camoufox + proxy + human sim
  LLM extraction (5% of pages): $0.030/page  → Gemini/GPT-4o-mini
  WEIGHTED AVERAGE:              $0.005/page

Firecrawl cloud:
  Standard:                     $0.016/page  (1 credit)
  JS rendering:                 $0.080/page  (5 credits)
  AI extraction:                $0.160/page  (5+5 credits)
  AVERAGE:                      $0.050/page

ScrapingBee:
  Standard:                     $0.003/page  (1 credit)
  JS rendering:                 $0.015/page  (5 credits)
  Stealth proxy:                $0.075/page  (25 credits)
  AVERAGE:                      $0.020/page

Bright Data:
  Web Unlocker:                 $0.010-0.030/page
  Scraping Browser:             $0.050-0.100/page (per GB)
  AVERAGE:                      $0.030/page

OUR COST ADVANTAGE: 4-10x cheaper than any commercial alternative
REASON: Smart routing avoids overkill — 70% of sites DON'T need a browser
```

---

## SUCCESS CRITERIA — "MOST ADVANCED SCRAPER ON EARTH"

After this revision, our platform must beat EVERY competitor on at least one dimension and match them on all others:

| Capability | Target | Measured By |
|-----------|--------|-------------|
| Extraction accuracy | ≥95% on top 100 e-commerce sites | Automated test suite |
| Stealth success rate | ≥95% on Cloudflare/DataDome sites | Real-world test against 50 protected sites |
| Cost per page | ≤$0.005 weighted average | Cost tracking in router |
| Extraction cascade depth | 10 tiers (most in industry) | Code audit |
| Device profile count | 24+ (most in industry) | Code count |
| Social platform coverage | 7 platforms | Code audit |
| Output formats | 4 (JSON, markdown, HTML, raw) | Feature test |
| Crawl capability | Full-site recursive with resume | Integration test |
| AI agent integration | MCP server + /search + /extract | Feature test |
| Change detection | Content diff between crawl runs | Feature test |
| Adaptive selectors | Self-healing on layout change | Regression test |
| Currency support | 27+ currencies | Code count |
| Zero regression | All 706+ existing tests pass | CI pipeline |

---

## EXECUTION MANDATE

```
THIS PROMPT IS A DIRECT ORDER. EXECUTE FULLY. NO PARTIAL DELIVERIES.

1. Read the global CLAUDE.md MUST DO gate
2. Deploy ALL 10 agents
3. Use context7 for EVERY library before writing code
4. Use exa to verify every OSS choice
5. Use github to check maintenance status of every dependency
6. Build sprint by sprint, commit + push after each sprint
7. Store decisions in claude-mem
8. Update system files after every sprint
9. Run full test suite after every sprint
10. DO NOT STOP until all 7 sprints are complete
```

---

*End of Revision Spec Prompt — Phase 9: HYDRA*
*Target: The Most Advanced Scraper on Earth*
*Method: Smart integration of battle-tested OSS + surgical custom builds*
*Principle: Deterministic first, browser second, AI last — minimize cost, maximize accuracy*
