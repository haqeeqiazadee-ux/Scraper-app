# SESSION RESUME PROMPT — HYDRA Phase 9 Execution
## Paste this ENTIRE prompt to start a new session with full context

---

## STEP 0: CONTEXT LOAD (MANDATORY — DO THIS FIRST, NO EXCEPTIONS)

You are resuming work on the AI Scraping Platform (Scraper-App). Before doing ANYTHING, read these files IN THIS EXACT ORDER:

```
1. cat ~/.claude/CLAUDE.md           # Global rules, agent hierarchy, 10 MCP servers, 437 skills, autonomy mode
2. cat CLAUDE.md                     # Project architecture, Phase 1-9 status, coding conventions, pre-task protocol
3. cat HYDRA_REVISION_SPEC_PROMPT.md # THE SPEC — 751 lines, 10 modules, 7 sprints, 33 tasks, build-vs-integrate decisions
4. cat system/todo.md                # Current task queue — 33 HYDRA tasks (0/33 complete)
5. cat system/execution_trace.md | tail -80   # Last 2 work cycles (competitive analysis + HYDRA planning)
6. cat system/lessons.md | tail -40           # Lessons 93-108 (competitive + HYDRA insights)
7. cat docs/COMPETITIVE_ANALYSIS.md           # 27-platform comparison, gaps, differentiators
```

After reading all 7 files, output:

```
BOOT COMPLETE
  Project: AI Scraping Platform (Scraper-App)
  Repo: https://github.com/fahad-scraper/Scraper-app
  Phase: 9 — HYDRA (Hybrid Universal Discovery & Retrieval Architecture)
  Status: [X/33 tasks complete]
  Next Sprint: [Sprint N]
  Next Task: [HYDRA-X.X]
  Resume Point: [description]
```

---

## WHAT WAS COMPLETED (Previous Session — April 4, 2026)

### Session Output (9 git commits: 446d732 → c6e80dc)

1. **Global ↔ Project CLAUDE.md linked** — MUST DO pre-task protocol enforced with 5-step flowchart, agent classification, tool selection, project state read before every task

2. **Industry Research Analyzed** — Read 2,466-line `WEB_SCRAPERS_INDUSTRY_CATALOG.md` covering 35+ commercial products and 30+ OSS scraping frameworks. Every platform profiled across 15+ dimensions.

3. **Competitive Analysis Produced** — `docs/COMPETITIVE_ANALYSIS.md` (308 lines) + `docs/COMPETITIVE_ANALYSIS_MATRIX.xlsx` (3 sheets). Compared our platform against 27 competitors across 55+ features. Every claim verified by reading full source code line by line.

4. **Key Findings:**
   - 8 features NO competitor has (8-tier extraction cascade, Camoufox C++ stealth, Bezier human simulation, 4-lane routing, WAF token management, multi-platform delivery, per-domain circuit breaker, 14 coherent device profiles)
   - 3 P0 gaps: MCP server, markdown output, full-site recursive crawl
   - We fill 3 of 7 market white-spaces identified in the research
   - Our cost advantage: $0.005/page vs $0.020-0.050 competitors (4-10x cheaper)

5. **HYDRA Revision Spec Created** — `HYDRA_REVISION_SPEC_PROMPT.md` (751 lines) with:
   - 10 modules, each with build-vs-integrate decision
   - 7 sprints, 33 tasks
   - 4 new OSS deps: trafilatura (Apache-2.0), html2text (BSD), rank-bm25 (Apache-2.0), mcp (MIT)
   - 5 OSS deps rejected: Scrapy (Twisted mismatch), Crawl4AI (too heavy), Scrapling (too young), Firecrawl (AGPL), markdownify (redundant)

6. **All system files updated** — CLAUDE.md, todo.md, execution_trace.md, lessons.md (108 total), development_log.md, final_step_logs.md

---

## WHAT TO DO NEXT

Execute the HYDRA spec sprint by sprint. The spec is in `HYDRA_REVISION_SPEC_PROMPT.md`. Start with whatever sprint has incomplete tasks.

### SCOPE RULES (CRITICAL — DO NOT VIOLATE)

**IN SCOPE — Scraping infrastructure only:**
```
packages/core/           ← All scraping core modules
packages/connectors/     ← http_collector, browser_worker, hard_target_worker, proxy_*, captcha_*
services/worker-*/       ← All 4 workers
services/control-plane/  ← New endpoints only (/crawl, /search, /extract)
```

**OUT OF SCOPE — DO NOT TOUCH:**
```
packages/connectors/keepa_connector.py        ← API, not scraping
packages/connectors/ebay_connector.py         ← API
packages/connectors/walmart_connector.py      ← API
packages/connectors/tiktok_connector.py       ← API
packages/connectors/shopify_connector.py      ← API
packages/connectors/google_maps_connector.py  ← API
packages/connectors/google_sheets_connector.py ← API
packages/connectors/apify_adapter.py          ← API
apps/*                                        ← Frontend unchanged
infrastructure/*                              ← Infra unchanged
packages/core/billing.py                      ← Business logic
```

### QUALITY GATES (ENFORCE AFTER EVERY SPRINT)

```
1. ALL existing 706+ tests pass (ZERO regressions)
2. ALL new modules have ≥90% test coverage
3. ruff lint passes with ZERO warnings
4. No hardcoded secrets, no print(), all async I/O
5. Protocol classes for interfaces, Pydantic v2 for models
6. Update system files after every sprint
7. Git commit + push after every sprint
```

### KEY ARCHITECTURAL DECISIONS (ALREADY MADE — DO NOT RE-DEBATE)

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Full-site crawl | BUILD on our queue | Scrapy's Twisted conflicts with our asyncio |
| Markdown output | INTEGRATE trafilatura + html2text | Battle-tested, correct licenses |
| Adaptive selectors | BUILD (extend selector_cache.py) | Borrow patterns from Scrapling/Crawl4AI, avoid their deps |
| BM25 filtering | INTEGRATE rank-bm25 | Apache-2.0, lightweight, no reason to reinvent |
| Change detection | BUILD | Market white-space, nobody does this well |
| MCP server | BUILD with mcp SDK | MIT SDK, thin wrapper over our REST API |
| /search endpoint | BUILD | Brave Search API (free tier) → scrape results |
| Social extractors | BUILD twitter.py + linkedin.py | Platform-specific HTML parsing, no external dep |
| Stealth upgrades | BUILD | 14→24 profiles, fingerprint noise, no external dep |
| Smart router | BUILD | Response-based reclassification, cost-aware routing |

### GIT AUTHENTICATION

```bash
git remote set-url origin https://<YOUR_GITHUB_PAT>@github.com/fahad-scraper/Scraper-app.git
```

*(Generate PAT at GitHub → Settings → Developer settings → Personal access tokens → needs `repo` scope)*

---

## EXECUTION MANDATE

```
Follow the HYDRA_REVISION_SPEC_PROMPT.md exactly.
Execute sprint by sprint.
Commit + push after each sprint.
Update system files after each sprint.
Do NOT ask permission for routine work.
Do NOT stop mid-sprint.
Complete each sprint fully before reporting.
If a sprint reveals additional work needed — do it, log it, continue.
```
