# Lessons Learned

## Phase 0 Observations

1. **Existing code is monolithic** — The scraper_pro/ codebase is a single-app scraper with no platform architecture. Refactoring into shared core + multiple runtime shells will require significant restructuring.

2. **Reusable components identified** — proxy_manager.py, AI extraction logic, smart_exporter.py, verticals/templates system, and core/fallback_chain.py contain valuable logic that should be preserved and refactored into shared packages.

3. **API key embedded in code** — README mentions Gemini API key is "embedded in code" — this is a security issue that must be fixed early (move to environment variables / secrets management).

4. **No test infrastructure** — Tests exist but are ad-hoc scripts, not structured test suites. Need proper pytest setup with fixtures and CI integration.

## Phase 1 Observations

5. **Spec writing clarifies architecture** — Writing detailed specs for all 24 sections exposed several implicit decisions that needed to be made explicit (e.g., SQLite for desktop, in-memory queue for desktop mode, native messaging for extension-companion).

6. **AI must be optional** — Deterministic extraction (CSS, JSON-LD, regex) should be the default. AI is expensive and slow — use only for repair, normalization, and routing. This is a key principle.

7. **Storage abstraction is critical** — The platform must work with PostgreSQL+S3+Redis in cloud AND SQLite+filesystem+in-memory on desktop. Design the interfaces first, implementations second.

## Phase 2 Observations

8. **69 tasks is manageable** — Breaking the project into 69 granular tasks across 24 epics gives clear visibility. The critical path has 12 sequential tasks.

9. **Front ends can parallelize** — Web dashboard, Windows EXE, and browser extension development can happen in parallel once the API is working.

10. **Migration should happen early** — Extracting reusable code from scraper_pro/ into new packages should happen alongside architecture scaffolding, not after.

## Phase 3 Observations

11. **Python package naming: no hyphens** — Python cannot import packages with hyphens in directory names (e.g., `services/control-plane`). Resolved with symlink: `services/control_plane` → `services/control-plane`. **Rule:** Always use underscores in Python package directory names, or create symlinks when convention conflicts.

12. **Pydantic v2 model_config replaces Config class** — In Pydantic v2, use `model_config = {"from_attributes": True}` instead of the old `class Config: orm_mode = True`. This is needed for SQLAlchemy ORM integration.

13. **Protocol > ABC for interfaces** — Using `typing.Protocol` with `@runtime_checkable` provides structural subtyping — implementations don't need to explicitly inherit. This is cleaner for a pluggable architecture.

14. **StrEnum for JSON serialization** — Using `StrEnum` instead of plain `Enum` ensures values serialize naturally to/from JSON without needing custom serializers.

15. **In-memory stores for scaffolding** — The control plane uses in-memory dicts for initial scaffolding. This lets us test the API shape before wiring up the database. Replace with real stores in STORAGE tasks.

16. **Lazy initialization pattern** — Both HttpCollector and PlaywrightBrowserWorker use lazy initialization (create client on first request). This avoids startup overhead and import-time side effects.

17. **Fallback chain is reusable everywhere** — The primary → secondary → tertiary pattern from scraper_pro/core/fallback_chain.py applies to: proxies (datacenter → residential → mobile), CAPTCHAs (service A → B → C), AI providers (Gemini → OpenAI → deterministic), execution lanes (HTTP → browser → hard-target). It's a core architectural pattern.

18. **CLAUDE.md is essential** — Having a project context file that documents architecture, conventions, and workflow ensures consistency across coding sessions. Update it after every significant architectural change.

## Phase 4 Observations

19. **Domain matching needs suffix support** — Exact domain matching fails for subdomains (e.g., `mystore.myshopify.com` should match `myshopify.com`). Always implement suffix matching for domain lookups.

20. **Path traversal protection is critical** — Filesystem-based storage must validate that resolved paths stay within the base directory. Use `Path.resolve()` and check prefix. This is a security requirement, not optional.

21. **TTL in cache needs time.time() comparison** — In-memory cache TTL implementation must compare against `time.time()` on every `get()` call, not just during periodic cleanup. Lazy expiry is simpler and more correct.

22. **Queue ack/nack pattern** — Track dequeued messages as "pending" until ack'd. On nack, re-enqueue the message. This matches Redis/RabbitMQ semantics and enables reliable message processing.

23. **Test early, test often** — Writing tests alongside implementation (not after) caught the router domain matching bug immediately. The 103-test suite now validates all contracts, router logic, and storage backends.

24. **SQLite in-memory for fast tests** — Using `sqlite+aiosqlite:///:memory:` gives instant test databases with zero cleanup. Each test gets a fresh database via fixtures. This is much faster than testcontainers for unit tests.

25. **Tenant isolation via repository pattern** — Every repository method takes `tenant_id` as a parameter and includes it in WHERE clauses. This is the single enforcement point for multi-tenant data isolation. Never query without tenant_id.

26. **Symlinks for Python-hyphenated dirs need correct relative paths** — `ln -s control-plane services/control_plane` (relative from parent) not `ln -s services/control-plane services/control_plane` (absolute-ish). Always create symlinks from the parent directory.

27. **AI providers should always have deterministic fallback** — The AIProviderChain always appends DeterministicProvider as the final fallback. This ensures extraction never completely fails — you always get at least JSON-LD/regex results.

28. **Worker should_escalate flag** — HTTP worker sets `should_escalate=True` when extraction fails (HTTP error, empty results). The control plane uses this to automatically route to browser lane. Clean separation of concerns.

29. **Confidence scoring from field fill rate** — Simple but effective: count non-empty fields / total fields across extracted items. This avoids AI-based confidence estimation and works with deterministic extraction too.

30. **Comma disambiguation in prices** — "5,000" vs "29,99": use regex `^\d{1,3}(,\d{3})+$` to detect thousands separator. If it matches, remove commas. Otherwise treat comma as decimal. This handles USD, EUR, PKR formats correctly.

31. **Escalation context must be per-task** — Each task gets its own EscalationContext tracking depth and attempts. Don't use global state — concurrent tasks would interfere with each other.

32. **Session health drives automatic status transitions** — Health score thresholds (0.7 degraded, 0.3 invalid) combined with consecutive failure count give reliable session lifecycle management without manual intervention.

33. **Docker health checks are essential** — Use `pg_isready` for PostgreSQL, `redis-cli ping` for Redis, and HTTP health endpoint for the API. Docker Compose `depends_on: condition: service_healthy` ensures proper startup order.

34. **Use PyJWT not python-jose** — PyJWT (`import jwt`) is the actively maintained library. python-jose is unmaintained and has known CVEs. PyJWT's `jwt.encode`/`jwt.decode` API is clean and sufficient for HS256/RS256.

35. **HTTPBearer with auto_error=False** — Setting `auto_error=False` on FastAPI's `HTTPBearer` security scheme lets you return a custom 401 response instead of the generic one. This gives better error messages for missing vs invalid tokens.

36. **Composition over inheritance for enhanced managers** — `PersistentSessionManager` wraps `SessionManager` via composition rather than subclassing. This keeps the in-memory manager unchanged and testable independently, while the persistent layer adds storage concerns. The pattern works well when adding cross-cutting features (persistence, caching, metrics) to existing classes.

37. **run_in_executor for file I/O in async code** — `asyncio.get_running_loop().run_in_executor(None, sync_fn)` is sufficient for filesystem operations without adding aiofiles as a dependency. The default executor (ThreadPoolExecutor) handles concurrent file reads/writes well for moderate workloads.

38. **Lightweight metrics without prometheus_client** — A simple MetricsCollector with dict-based counters/gauges/histograms and Prometheus text export is sufficient for most use cases. Avoids adding prometheus_client as a hard dependency while remaining compatible with standard Prometheus scraping. Thread safety via `threading.Lock` is essential since FastAPI middleware runs across async contexts.

## Final Verification Observations

39. **Documentation-as-code works** — Keeping ARCHITECTURE.md, DEPLOYMENT.md, and CHANGELOG.md in the repo alongside the code ensures they stay in sync. Separate wikis or Confluence pages drift quickly.

40. **__init__.py audits catch import issues early** — One missing __init__.py in proxy_providers/ would have caused import failures at runtime. Automated checks for package completeness should be part of CI.

41. **Minor TODOs are acceptable at milestone** — The 3 TODO comments found (latency tracking, health check DB probe, CORS restriction) are all enhancement-level. Shipping with known minor TODOs documented is better than blocking release.

42. **Test count as project health metric** — Tracking test counts (436 passing) across milestones gives a concrete measure of project health. The ratio of test files (22) to source files (56) indicates areas where additional coverage would be valuable.

43. **System tracking files provide audit trail** — The execution_trace.md, development_log.md, and final_step_logs.md together create a complete audit trail of every decision and implementation. This is invaluable for onboarding new contributors and understanding why things were built the way they are.

## Phase 4+ Gap Closure Observations

44. **Schema fields without enforcement are technical debt** — Having `rate_limit` on Policy, `callback_url` on Task, and `schedule` on Task without any code that uses them is worse than not having the fields at all. It creates false expectations for API consumers.

45. **Workers without queue consumers are dead code** — A worker that can process tasks but has no consumption loop is useless in production. The consumption loop (dequeue → process → ack/nack) is the actual service; the worker is just a library.

46. **Redis queue needs ack/nack with pending tracking** — Using BRPOP alone loses messages on worker crash. Must RPOPLPUSH to a pending list, then remove on ack. This mirrors the in-memory queue pattern already established.

47. **Hard-target lane is the final escalation** — The escalation chain HTTP → Browser → Hard-target must be the last resort before marking a task as failed. Hard-target uses residential proxies + stealth browser + CAPTCHA solving, which is expensive.

48. **Token bucket > sliding window for rate limiting** — Token bucket allows bursts while maintaining average rate, which is better UX for scraping workloads that tend to be bursty. Implementation is simpler too — just track tokens and refill rate.

49. **Cron parsing should be minimal** — Don't pull in a heavy cron library; 5-field cron parsing (minute hour day month weekday) with basic wildcards and lists covers 95% of use cases. Keep it in a single module.

50. **Parallel agents maximize throughput** — Running 5 independent implementation agents in parallel closes gaps 5x faster than sequential. Key is ensuring zero file overlap between agents.

## QA Session Observations

51. **Brotli support is essential for web scraping** — Many sites serve Brotli-compressed responses. Without the `brotli` Python package, httpx returns garbled content. Always include `brotli` in scraping project dependencies.

52. **"not_configured" ≠ "unhealthy"** — Readiness checks should distinguish between "service not configured" (acceptable in minimal deployments) and "service failed" (actual problem). Using `all(v == "healthy")` incorrectly rejects valid configurations.

53. **CSS selector extraction fills the gap between JSON-LD and regex** — JSON-LD is ideal but rare on listing pages. Regex is too crude for multi-item extraction. BeautifulSoup CSS selectors provide reliable multi-item extraction for common page structures (product grids, quote lists, etc.).

54. **Escalation should be semantic, not blanket** — HTTP 404 means "page not found" — escalating to browser/hard-target won't help. Only escalate on 403 (blocked), 429 (rate limited), or 5xx (server errors). This saves expensive browser/proxy resources.

55. **Python __pycache__ causes stale code** — When modifying Python files during testing, always clear `__pycache__` directories to ensure fresh imports. Otherwise, old bytecode can mask fixes.

56. **Test against real sites early** — Unit tests with mocked responses don't catch real-world issues like Brotli encoding, HTML structure variations, or DNS resolution failures. Testing against books.toscrape.com and httpbin.org caught 3 bugs that unit tests missed.

57. **Chunk complex QA into small, independent tests** — Breaking QA into 9 small chunks (extraction fallback, webhooks, proxy health, sessions, quotas, logging, e-commerce, JSON endpoints) prevents context overload and makes each failure easy to diagnose. Read system memory files first to avoid repeating work.

58. **Weighted proxy selection > strict round-robin** — Using proxy health scores for weighted random selection naturally deprioritizes bad proxies without hard-removing them. A proxy with 10% success rate still gets 7% of traffic (not zero), allowing recovery detection.

59. **Gemini API keys may be geo-restricted** — The Gemini API key returned 403 from this environment. AI provider fallback chains must always include a deterministic provider as the final option. Never depend on a single AI provider in production.

60. **Check for pre-installed browsers before downloading** — Playwright `install` may fail if CDN is blocked, but an older version (chromium-1194) may already be in `~/.cache/ms-playwright/`. Use `executable_path` to point to the existing binary instead of downloading a newer version.

61. **`networkidle` wait strategy hangs on pages with external resources** — If a page loads external assets that are blocked by proxy/firewall, `wait_until='networkidle'` never resolves. Use `domcontentloaded` + explicit `wait_for_timeout()` as a safer alternative for test environments.

62. **Local test servers are better than mocks for browser testing** — Python's `http.server.HTTPServer` in a daemon thread provides a reliable local server for Playwright tests. This avoids network issues, is deterministic, and tests the full browser rendering pipeline without mocking.

63. **`executable_path` should always be an optional parameter** — Browser connectors should accept an optional `executable_path` for environments where Playwright's auto-detection fails. This is a zero-cost addition that prevents hard blocks in CI/container environments.

64. **Never track secret files in git, even as "reference"** — `env.keys` was tracked in git and exposed API keys in commit history. Always add secret files to `.gitignore` from day one. Once a key is in git history, it must be revoked — there's no way to truly scrub it.

65. **Google API 403 can be a network block, not a key issue** — `generativelanguage.googleapis.com` returns 403 at the network level from some environments (sandboxes, CI runners). Always test with `curl` on the root URL first before blaming the API key. Have a fallback provider (OpenAI) ready.

66. **OpenAI chat completions need low temperature for extraction** — Setting `temperature=0.1` with a system prompt enforcing "JSON only" responses produces reliable, parseable extraction results. Higher temperatures cause markdown wrapping, explanatory text, and inconsistent JSON structure.

67. **Lazy client initialization is essential for multi-provider chains** — Creating API clients only on first use (not at import time) prevents failures when one provider's SDK is missing. The factory can safely reference all providers without requiring all SDKs installed.

68. **TLS fingerprinting is the #1 detection layer** — Anti-bot systems (Cloudflare, Akamai, DataDome) check JA3/JA4 TLS fingerprints BEFORE seeing any HTTP data. Python's httpx/requests produce OpenSSL fingerprints instantly identifiable as non-browser. curl_cffi impersonates real browser TLS handshakes and is the standard solution. Standard HTTPS proxies do NOT change your TLS fingerprint — it's end-to-end.

69. **All fingerprint signals must tell a coherent story** — Random spoofing of individual attributes (UA, timezone, locale, screen) creates cross-signal inconsistencies that are trivially detectable. A German locale with a US IP, French timezone, and mobile screen on a desktop UA is an instant flag. Use complete "device profiles" from real-world combinations.

70. **JS-level stealth patches are detectable** — `Object.defineProperty(navigator, 'webdriver', ...)` can be detected by checking prototype chains, property descriptors, stack traces, and error message strings. Camoufox solves this by modifying Firefox at the C++ source level, making patches invisible to any JavaScript inspection. This is the only approach that consistently passes CreepJS and BrowserScan.

71. **Currency symbols are ambiguous across countries** — "Rs" means INR in India but PKR in Pakistan. "$" means USD in America but CAD in Canada. Domain-based disambiguation must take priority over symbol matching. Always resolve the domain first, then use it to disambiguate symbols.

72. **"Just having a name" doesn't make something a product** — Navigation elements (`<a>` tags with text like "Trending Now", "Top Brands") pass through extraction as "products" because they have a name field. Real products need at least one additional signal: price, image, rating, or description. Name-only items are noise.

73. **Confidence should measure data quality, not field coverage** — Measuring `filled_fields / total_fields` gives 100% confidence to a garbage item with `{name: "Shop Now", product_url: "https://..."}`. Weighted quality scoring (name=0.3, price=0.3, image=0.15) correctly reflects that an item missing price is low quality.

74. **The basic fallback is the most dangerous extraction method** — It runs when everything else fails, and if it returns garbage, the system reports "success" with high confidence. A basic fallback that returns `<title>` + first price in HTML is actively harmful. The fallback must validate that the page is actually a product page (h1 + price element + add-to-cart) before returning anything.

75. **Browser resource blocking saves 60-80% bandwidth** — Images, CSS, fonts, and tracking scripts are unnecessary for data extraction. Blocking them via `page.route()` dramatically speeds up page loads and reduces proxy bandwidth costs. This is a free performance win that every pro scraper uses.

76. **API interception beats DOM parsing** — Modern SPAs (React/Next.js) fetch product data via internal APIs. The JSON payload from an XHR/fetch response is 10x cleaner than parsing the rendered DOM. Intercepting network responses should be tried before or alongside DOM extraction.

77. **Sitemap.xml is the fastest URL discovery method** — Before crawling a site, always try `GET /sitemap.xml`. Most e-commerce sites have one, and it gives you every product URL without following links. Also check robots.txt for declared sitemap locations. WordPress uses `wp-sitemap.xml`, WooCommerce uses `wp-sitemap-posts-product-1.xml`.

78. **Circuit breakers prevent resource waste** — A domain that returned 5 consecutive 403s will return a 6th. Without a circuit breaker, the scraper burns proxy bandwidth, CAPTCHA credits, and browser sessions on a site that's actively blocking it. Trip after 5 failures, wait 5 minutes, probe with one request before resuming.

79. **AWS WAF tokens are fingerprint-bound** — The `aws-waf-token` cookie contains a hash of the browser fingerprint used when it was acquired. Changing your device profile (UA, viewport, etc.) mid-session invalidates the token and triggers re-verification. Always pair tokens with a consistent fingerprint.

80. **UA strings must be updated quarterly** — Browser versions from 6 months ago are statistical anomalies that flag bots. Build a version updater that can bump all profiles in one call rather than editing 14 definitions manually. Keep constants (`LATEST_CHROME_VERSION`) at the top for easy updates.

81. **Response caching saves more than bandwidth** — Caching with ETag/If-Modified-Since means the server returns 304 Not Modified (no body) instead of re-sending the full page. This cuts bandwidth, reduces proxy costs, and decreases the chance of triggering rate limits because the request is lighter.

82. **srcset always has the highest-res image** — When an `<img>` has a `srcset` attribute, the largest width descriptor (e.g. `1600w`) is the full product image. The `src` is often a low-res placeholder. Always parse srcset and pick the highest resolution. Same applies to `<picture>` elements with `<source>` tags.

83. **APIs beat scraping when they exist** — Keepa's API returns richer Amazon data (price history, sales rank, buy box, offers, stock levels, monthly sold) than any scraper could extract from HTML, at ~$0.001/token vs ~$0.10+ per browser session. Always check if a data API exists before building a scraper. The API is faster, cheaper, more reliable, and doesn't trigger anti-bot systems.

84. **Smart routing by URL pattern saves resources** — Not all Amazon URLs need the same treatment. Product pages (`/dp/ASIN`) have a clear ASIN → use Keepa API. Search pages (`/s?k=`) have no ASIN → need browser rendering. Routing by URL pattern avoids wasting expensive browser sessions on pages that have a cheaper API path.

85. **Google Sheets as a cache layer saves API costs** — Store API results in a shared Google Sheet. Next time the same data is requested, read from Sheet (free) instead of calling the API again. With 24-hour staleness, you pay for each product only once per day regardless of how many times it's queried.

86. **Multi-tier API fallback is more reliable than any single source** — Google Maps data can come from Places API (reliable, costs money), SerpAPI (cheaper, third-party), or direct browser scraping (free, fragile). Building all three with automatic fallthrough means the system works regardless of which service is available or affordable.

87. **Sandbox environments block Google APIs at the network level** — `sheets.googleapis.com`, `drive.googleapis.com`, and `generativelanguage.googleapis.com` all return 403 from sandboxed environments. The error looks like an auth problem but it's a network firewall. Always verify by checking if the domain is reachable at all (`curl https://sheets.googleapis.com/`). The same code works instantly on Railway, Render, or any real server.

88. **Service accounts need both API enablement AND sheet sharing** — Two separate permissions are required: (1) enable the Sheets/Drive APIs in Google Cloud Console, and (2) share the specific spreadsheet with the service account email as Editor. Missing either one causes a 403. The service account email looks like `name@project.iam.gserviceaccount.com`.

89. **Free official APIs cover more platforms than expected** — eBay, Etsy, Best Buy, MercadoLibre, Steam, Rakuten, Envato, Product Hunt all have FREE official APIs with generous rate limits. Always check for official APIs before paying for third-party scrapers.

90. **Social media all-in-one providers are 5x cheaper than single-platform** — SociaVault covers 25+ platforms for $20/mo vs EnsembleData covering 8 platforms for $100/mo. Xpoz offers 100K free results/month. Always compare all-in-one vs per-platform pricing.

91. **APIs get shut down by lawsuits** — Proxycurl (LinkedIn data) was shut down in July 2026 after LinkedIn sued them for fake accounts. Always have a backup provider and never depend on a single source for legally risky data (LinkedIn, Facebook).

92. **Pay-per-use beats subscriptions for low volume** — ScrapeCreators charges $10 for 5K credits that never expire. Apify charges per successful extract. For platforms you query occasionally, pay-per-use avoids wasted monthly fees.

93. **MCP server is now table stakes for AI integration** — Firecrawl, Browserless, Bright Data, Hyperbrowser, Spider all have MCP servers. Without one, AI agents (Claude, Cursor, VS Code) can't integrate with our platform. This is P0.

94. **Markdown output is the new default for AI/LLM consumption** — The industry has shifted from JSON/HTML to markdown as the primary output format for RAG pipelines and LLM consumption. Firecrawl, Crawl4AI, Jina Reader, Spider all output markdown. We need this.

95. **"AI extraction" is mostly thin wrappers** — Most competitors claiming "AI scraping" are just calling GPT-4 on raw HTML with no proprietary intelligence. Our 8-tier deterministic cascade extracts data without AI 90%+ of the time, which is faster and cheaper.

96. **Nobody has our 4-lane routing** — After analyzing 27 platforms, no competitor implements smart routing between HTTP, browser, stealth browser, and AI lanes with automatic escalation. This is our strongest unique differentiator.

97. **Stealth benchmarks vary wildly** — ScrapeOps fingerprint tests show ScrapingBee at 24.76/100 (worst), Scrapfly at 86.67/100 (best), Zyte at 80.48/100 (3rd). Our Camoufox scores 0% on CreepJS. Stealth is a genuine differentiator, not commodity.

98. **Self-hosted + multi-platform is unoccupied territory** — No competitor offers Web SaaS + Desktop EXE + Chrome Extension + REST API from a single codebase with cloud/desktop abstractions. Octoparse has desktop+cloud but separate codebases.

99. **Market white-space: scraping cost optimization** — The industry catalog identifies "No tool intelligently routes between HTTP-only, JS rendering, and full browser based on actual site requirements to minimize cost" as a gap. Our 4-lane router is EXACTLY this.

100. **Credit-based pricing is opaque and unpredictable** — Most scraping APIs charge 1x for HTTP, 5x for JS rendering, 25x for stealth proxies. Users can't predict costs. Our self-hosted model eliminates per-request billing entirely.

101. **Borrow patterns, don't import frameworks** — Scrapy's crawl patterns and Crawl4AI's adaptive learning are excellent designs, but importing them as dependencies brings architecture conflicts (Twisted vs asyncio), bus-factor risk (solo maintainers), and license headaches (AGPL). Copy the pattern, not the package.

102. **trafilatura beats readability-lxml for content extraction** — Academic-backed (4K+ stars, Apache-2.0), actively maintained, handles boilerplate removal better than Mozilla's readability port. Use it as the cleaning layer before html2text for markdown output.

103. **4 dependencies is the right number for Phase 9** — trafilatura, html2text, rank-bm25, mcp. Each solves one specific problem we shouldn't reinvent. Every dependency beyond this was either architecturally incompatible, license-risky, or solvable with our existing code.

104. **Cost-aware routing is our biggest strategic moat** — No competitor routes intelligently between HTTP ($0.001), browser ($0.01), and stealth ($0.05) based on actual site requirements. This alone makes us 4-10x cheaper than Firecrawl/ScrapingBee/Bright Data at scale.

105. **Response-based reclassification > static domain lists** — Maintaining hardcoded lists of "browser-required" and "hard-target" domains doesn't scale. Better: try HTTP first, check response for Cloudflare markers, auto-reclassify to browser. The router should learn from every request.

106. **10-tier extraction cascade = deterministic first, AI last** — Every deterministic tier we add (adaptive selectors, trafilatura content cleaning) saves $0.01-0.10/page in LLM costs. The goal is to make LLM extraction fire on <5% of pages, not 100%.

107. **Scope discipline wins** — Phase 9 touches ONLY scraping code (packages/core, packages/connectors, services/worker-*). API connectors (Keepa, eBay, Walmart, etc.), frontend apps, and infrastructure are OUT OF SCOPE. This prevents scope creep and keeps the sprint plan achievable.

108. **The market's biggest gap is our strongest feature** — The research report identifies "scraping cost optimization" as a market white-space that no tool fills. Our 4-lane router with automatic escalation IS that tool. Marketing should lead with cost savings, not feature count.

## Phase 9 — HYDRA Execution Observations

109. **Parallel agents = 10x throughput** — Deploying 4-6 agents simultaneously across independent tasks (different files) completed 33 tasks in a single session. Sequential would have taken 5-7x longer. Key: agents must work on non-overlapping files.

110. **Sub-agent output is untrusted until verified** — Agents wrote code that looked correct but had subtle bugs: crawl router passed kwargs instead of CrawlConfig (500 error), Playwright selectors matched multiple elements (strict mode violations). Always run tests after agents finish.

111. **Windows symlinks are broken for Python packages** — `services/control_plane` → `services/control-plane` symlinks don't work on Windows (they become text files containing the target name). Fix: register hyphenated dirs as modules in conftest.py using `types.ModuleType` + `sys.modules`.

112. **Playwright strict mode catches ambiguous selectors** — `get_by_text("Dashboard")` fails when both sidebar and page heading contain "Dashboard". Use `page.locator("nav").get_by_text()` to scope, or `get_by_role("heading", name="...", exact=True)`.

113. **Vite proxy config is critical for full-stack E2E** — Frontend at :5199 must proxy `/api` to backend at :8765. Without `VITE_BACKEND_URL` env var, proxy defaults to :8000 and all API calls fail with "Failed to load".

114. **React Query staleTime=0 for always-fresh data** — Default `staleTime: 30000` serves cached data for 30 seconds. Combined with `refetchOnWindowFocus: false`, users see stale data. Set `staleTime: 0` + `refetchOnMount: true` + `Cache-Control: no-store` for always-server-fresh.

115. **Verify-before-done loop prevents false completion claims** — Added mandatory verification step between Execute and Post-Task: list deliverables → verify each exists+works → run tests → check regressions → only then mark complete. Caught 12 bugs that would have shipped as "done".

116. **npx doesn't work in all shell environments** — `npx` requires `/usr/bin/env bash` which doesn't exist in some Windows sandbox shells. Workaround: run tools directly via `node node_modules/toolname/bin/tool.js`.

117. **`os.setsid` is Unix-only** — Playwright conftest used `preexec_fn=os.setsid` and `os.killpg` for process group management. These don't exist on Windows. Fix: conditional `subprocess.CREATE_NEW_PROCESS_GROUP` + `proc.terminate()` fallback.
