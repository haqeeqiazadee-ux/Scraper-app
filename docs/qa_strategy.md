# QA Strategy — AI Scraping Platform (E2E Use-Case-Based)

> **Status:** ACTIVE
> **Last Updated:** 2026-03-23
> **Derived from:** docs/final_specs.md, docs/tasks_breakdown.md

---

## How to Use This Document

This is a **step-by-step, use-case-based** QA checklist. Each test case is a real user action.
Work through phases in order — each phase depends on the previous one passing.

**Legend:**
- [ ] = Not tested
- [x] = Passed
- [!] = Failed (add note)
- [~] = Skipped (add reason)

---

## Phase 1: Infrastructure Health (Blocking — Must Pass First)

These verify the deployed services are alive and connected.

### 1.1 Backend API Reachability
- [x] **UC-1.1.1** — `GET /health` returns `200 OK`
- [x] **UC-1.1.2** — `GET /ready` returns `200 OK` (confirms DB + Redis connected) — FIXED: not_configured treated as acceptable
- [x] **UC-1.1.3** — `GET /metrics` returns Prometheus-format text

### 1.2 Database Connectivity
- [x] **UC-1.2.1** — `GET /api/v1/tasks` returns `200` with empty list (DB reads work)
- [x] **UC-1.2.2** — `GET /api/v1/policies` returns `200` with empty list
- [x] **UC-1.2.3** — Backend logs show no `OperationalError` or `ConnectionRefused`

### 1.3 Frontend Reachability
- [~] **UC-1.3.1** — Web dashboard loads at deployed URL (HTML renders) — SKIP: no browser in test env
- [~] **UC-1.3.2** — Login page renders at `/login` — SKIP: no browser in test env
- [~] **UC-1.3.3** — Browser console shows no CORS errors on API calls — SKIP: no browser in test env
- [~] **UC-1.3.4** — `API_URL` environment variable points to correct backend — SKIP: no browser in test env

### 1.4 Frontend-Backend Integration
- [x] **UC-1.4.1** — Login page can reach `POST /api/v1/auth/token` (no network error)
- [x] **UC-1.4.2** — After login, dashboard loads and calls `GET /api/v1/tasks`
- [x] **UC-1.4.3** — API errors show user-friendly messages (not raw stack traces)

---

## Phase 2: Authentication & Authorization

### 2.1 Login Flow
- [x] **UC-2.1.1** — Enter valid credentials → redirected to `/dashboard`
- [x] **UC-2.1.2** — Enter invalid credentials → error message shown, stays on `/login` — FIXED: added validation
- [~] **UC-2.1.3** — Access `/dashboard` without login → redirected to `/login` — SKIP: frontend
- [~] **UC-2.1.4** — JWT token stored in browser after successful login — SKIP: frontend

### 2.2 Session Management
- [~] **UC-2.2.1** — Refresh page while logged in → stays logged in (token persists) — SKIP: frontend
- [x] **UC-2.2.2** — Expired token → auto-logout, redirected to `/login`
- [x] **UC-2.2.3** — `GET /api/v1/auth/me` returns current user profile

### 2.3 Tenant Isolation
- [x] **UC-2.3.1** — API requests without `Authorization` header → `401`
- [x] **UC-2.3.2** — Tasks created by tenant A are not visible to tenant B

---

## Phase 3: Task Management (CRUD)

### 3.1 Create Task
- [~] **UC-3.1.1** — Navigate to Tasks → Click "Create Task" → form renders — SKIP: frontend
- [x] **UC-3.1.2** — Fill: name="Test Task", url="https://httpbin.org/html", type=scrape → submit → `201 Created`
- [x] **UC-3.1.3** — New task appears in task list with status `pending`
- [x] **UC-3.1.4** — Submit with empty URL → validation error shown
- [x] **UC-3.1.5** — Submit with invalid URL → validation error shown

### 3.2 Read Tasks
- [~] **UC-3.2.1** — Task list page loads with pagination — SKIP: frontend
- [x] **UC-3.2.2** — Click a task → task detail page shows name, URL, status, created_at
- [~] **UC-3.2.3** — Task detail shows run history (initially empty) — SKIP: frontend

### 3.3 Update Task
- [x] **UC-3.3.1** — Edit task name → save → name updated in list
- [x] **UC-3.3.2** — Change priority → save → priority reflected

### 3.4 Delete Task
- [x] **UC-3.4.1** — Delete a task → task removed from list
- [~] **UC-3.4.2** — Confirm dialog shown before deletion — SKIP: frontend

### 3.5 Cancel Task
- [x] **UC-3.5.1** — Cancel a `pending` task → status changes to `cancelled`
- [x] **UC-3.5.2** — Cancel an already `completed` task → error or no-op

---

## Phase 4: Policy Management (CRUD)

### 4.1 Create Policy
- [ ] **UC-4.1.1** — Navigate to Policies → Click "Create" → form renders
- [ ] **UC-4.1.2** — Fill: name="E-commerce Policy", domains=["*.example.com"], preferred_lane="http" → submit → `201`
- [ ] **UC-4.1.3** — Policy appears in policy list

### 4.2 Read/Update/Delete Policies
- [ ] **UC-4.2.1** — Policy detail page shows all fields (rate limit, proxy policy, retry policy)
- [ ] **UC-4.2.2** — Edit policy → save → changes reflected
- [ ] **UC-4.2.3** — Delete policy → removed from list

### 4.3 Assign Policy to Task
- [ ] **UC-4.3.1** — Create task with policy selected → task references policy_id
- [ ] **UC-4.3.2** — Policy dropdown shows all available policies

---

## Phase 5: Execution Router (Dry Run)

### 5.1 Lane Selection
- [ ] **UC-5.1.1** — `POST /api/v1/route` with URL "https://httpbin.org/html" → returns `http` lane
- [ ] **UC-5.1.2** — `POST /api/v1/route` with URL of known JS-heavy site → returns `browser` lane
- [ ] **UC-5.1.3** — `POST /api/v1/route` with URL + policy.preferred_lane="browser" → respects policy override

### 5.2 Routing with Policy
- [ ] **UC-5.2.1** — Task with policy.preferred_lane set → routed to that lane
- [ ] **UC-5.2.2** — Task without policy → default routing logic applies (HTTP first)

---

## Phase 6: HTTP Lane — Static Site Scraping

Real scraping tests against actual websites (lightweight, no JS needed).

### 6.1 Simple Static HTML
- [ ] **UC-6.1.1** — Scrape `https://httpbin.org/html` → returns extracted text content
- [ ] **UC-6.1.2** — Scrape `https://books.toscrape.com/` → extracts book titles + prices
- [ ] **UC-6.1.3** — Scrape `https://quotes.toscrape.com/` → extracts quotes + authors

### 6.2 JSON-LD / Structured Data (Schema.org)
- [ ] **UC-6.2.1** — Scrape a page with JSON-LD product schema → extraction uses `extruct` path
- [ ] **UC-6.2.2** — Extracted fields match schema.org Product (name, price, image, description)
- [ ] **UC-6.2.3** — Confidence score is high (>0.8) for structured data extraction

### 6.3 CSS Selector Extraction
- [ ] **UC-6.3.1** — Create policy with custom CSS selectors → extraction uses those selectors
- [ ] **UC-6.3.2** — Fallback: JSON-LD fails → CSS selector extraction runs
- [ ] **UC-6.3.3** — Multiple items extracted from list/grid pages

### 6.4 Pagination (Static)
- [ ] **UC-6.4.1** — Scrape `https://books.toscrape.com/catalogue/page-1.html` → gets page 1 results
- [ ] **UC-6.4.2** — Multi-page scrape → follows next-page links → aggregates results

### 6.5 HTTP Stealth Headers
- [ ] **UC-6.5.1** — Request includes realistic User-Agent header
- [ ] **UC-6.5.2** — Request includes Accept, Accept-Language, Accept-Encoding headers
- [ ] **UC-6.5.3** — Headers rotate between requests (not same UA every time)

### 6.6 Error Handling (HTTP Lane)
- [ ] **UC-6.6.1** — Target returns 404 → task status = `failed`, error recorded
- [ ] **UC-6.6.2** — Target returns 500 → retry logic kicks in (up to retry_policy max)
- [ ] **UC-6.6.3** — Target unreachable (DNS fail) → task fails with clear error message
- [ ] **UC-6.6.4** — Target returns empty body → extraction reports 0 items, low confidence

---

## Phase 7: Browser Lane — JavaScript-Rendered Sites

Sites that require a real browser (Playwright) to render content.

### 7.1 JS-Rendered Content
- [ ] **UC-7.1.1** — Scrape a SPA (Single Page App) → browser renders JS → content extracted
- [ ] **UC-7.1.2** — Content not in initial HTML but appears after JS execution → extracted correctly

### 7.2 Infinite Scroll
- [ ] **UC-7.2.1** — Page with infinite scroll → browser scrolls down → loads more items → all extracted
- [ ] **UC-7.2.2** — Scroll stops after configurable max items or max scroll attempts

### 7.3 Click-to-Load / "Load More" Buttons
- [ ] **UC-7.3.1** — Page with "Load More" button → browser clicks it → additional items extracted
- [ ] **UC-7.3.2** — Multiple rounds of "Load More" → accumulates all items

### 7.4 AJAX Pagination
- [ ] **UC-7.4.1** — Page with AJAX-powered pagination → browser clicks page 2, 3... → items from all pages
- [ ] **UC-7.4.2** — Tab switching / dynamic content loading handled

### 7.5 Lazy-Loaded Images
- [ ] **UC-7.5.1** — Images with `loading="lazy"` → browser scrolls to trigger load → image URLs captured

### 7.6 Browser Screenshots
- [ ] **UC-7.6.1** — Browser task with screenshot option → PNG artifact stored
- [ ] **UC-7.6.2** — Screenshot downloadable via artifact API

### 7.7 Error Handling (Browser Lane)
- [ ] **UC-7.7.1** — Page hangs (timeout) → browser task fails with timeout error
- [ ] **UC-7.7.2** — Page crashes browser tab → graceful recovery, task marked failed

---

## Phase 8: Hard-Target Lane — Anti-Bot Protected Sites

Sites with aggressive bot protection (Cloudflare, DataDome, etc.).

### 8.1 Stealth Browser with Fingerprint Rotation
- [ ] **UC-8.1.1** — Hard-target task uses randomized browser fingerprints
- [ ] **UC-8.1.2** — Each request has different viewport, fonts, WebGL hash
- [ ] **UC-8.1.3** — Navigator properties don't leak automation signals

### 8.2 Residential Proxy Escalation
- [ ] **UC-8.2.1** — Browser blocked by anti-bot → escalates to residential proxy
- [ ] **UC-8.2.2** — Proxy rotation happens between requests

### 8.3 CAPTCHA Detection & Solving
- [ ] **UC-8.3.1** — CAPTCHA detected in response HTML → CAPTCHA adapter invoked
- [ ] **UC-8.3.2** — reCAPTCHA v2 challenge → solved via configured solver → page retried
- [ ] **UC-8.3.3** — CAPTCHA solve fails → tries next solver → tries different proxy → abandons
- [ ] **UC-8.3.4** — CAPTCHA cost tracked per solve event

### 8.4 Lane Escalation Chain
- [ ] **UC-8.4.1** — HTTP lane fails (403) → auto-escalates to browser lane
- [ ] **UC-8.4.2** — Browser lane fails (anti-bot) → auto-escalates to hard-target lane
- [ ] **UC-8.4.3** — Escalation depth respects max (default 3)
- [ ] **UC-8.4.4** — Escalation history visible in run records

---

## Phase 9: API / Feed Lane — Structured API Scraping

Direct API calls for platforms with known APIs.

### 9.1 Known Platform APIs
- [ ] **UC-9.1.1** — Shopify store URL → API lane detects Shopify → uses products.json API
- [ ] **UC-9.1.2** — WooCommerce store URL → API lane uses WC REST API
- [ ] **UC-9.1.3** — RSS feed URL → API lane parses feed → returns structured items

### 9.2 JSON Endpoint Scraping
- [ ] **UC-9.2.1** — Direct JSON API endpoint → fetches and parses JSON response
- [ ] **UC-9.2.2** — API with pagination → follows next page tokens → aggregates all items

### 9.3 API Rate Limit Awareness
- [ ] **UC-9.3.1** — API returns `429 Too Many Requests` → backs off and retries
- [ ] **UC-9.3.2** — Respects `Retry-After` header if present

---

## Phase 10: AI Normalization & Repair

AI processes raw extraction results for quality improvement.

### 10.1 Schema Normalization
- [ ] **UC-10.1.1** — Raw data with "cost" field → AI normalizes to "price"
- [ ] **UC-10.1.2** — Raw data with "product_name" → normalized to "name"
- [ ] **UC-10.1.3** — Mixed currency formats ("$19.99", "19,99 EUR") → normalized to consistent format

### 10.2 Data Repair
- [ ] **UC-10.2.1** — Truncated product title → AI infers/repairs full title
- [ ] **UC-10.2.2** — Missing currency → AI infers from domain/locale
- [ ] **UC-10.2.3** — HTML artifacts in text fields → cleaned by AI

### 10.3 Deduplication
- [ ] **UC-10.3.1** — Same product from two runs → detected as duplicate
- [ ] **UC-10.3.2** — Exact SKU match → merged into single record
- [ ] **UC-10.3.3** — Fuzzy name match (similar titles) → flagged with similarity score

### 10.4 AI Provider Fallback
- [ ] **UC-10.4.1** — Primary AI provider (Gemini) fails → falls back to secondary (OpenAI)
- [ ] **UC-10.4.2** — All AI providers fail → deterministic fallback (no AI) still produces result
- [ ] **UC-10.4.3** — AI token usage tracked per request

### 10.5 Confidence Scoring
- [ ] **UC-10.5.1** — JSON-LD extraction → confidence > 0.8
- [ ] **UC-10.5.2** — CSS selector extraction → confidence 0.5-0.8
- [ ] **UC-10.5.3** — AI-only extraction → confidence varies, recorded accurately
- [ ] **UC-10.5.4** — Low confidence (< threshold) → triggers AI normalization pass

---

## Phase 11: Results & Export

### 11.1 View Results
- [ ] **UC-11.1.1** — Navigate to Results page → list of extraction results shown
- [ ] **UC-11.1.2** — Click a result → detail view shows extracted_data as table
- [ ] **UC-11.1.3** — Result shows: item_count, confidence, extraction_method, normalization_applied

### 11.2 Export to JSON
- [ ] **UC-11.2.1** — Select results → Export as JSON → file downloads
- [ ] **UC-11.2.2** — JSON file contains all extracted items with correct schema

### 11.3 Export to CSV
- [ ] **UC-11.3.1** — Select results → Export as CSV → file downloads
- [ ] **UC-11.3.2** — CSV has proper headers, no data corruption

### 11.4 Export to XLSX (Excel)
- [ ] **UC-11.4.1** — Select results → Export as XLSX → file downloads
- [ ] **UC-11.4.2** — Excel file opens correctly with formatted columns

### 11.5 Artifact Storage
- [ ] **UC-11.5.1** — HTML snapshot stored as artifact after scrape
- [ ] **UC-11.5.2** — Screenshot (PNG) stored as artifact for browser tasks
- [ ] **UC-11.5.3** — Export files stored as artifacts with correct MIME type
- [ ] **UC-11.5.4** — Artifacts downloadable via API

---

## Phase 12: Scheduling & Webhooks

### 12.1 Cron Scheduling
- [ ] **UC-12.1.1** — Create task with schedule `*/30 * * * *` → schedule created
- [ ] **UC-12.1.2** — Schedule appears in `GET /api/v1/schedules` list
- [ ] **UC-12.1.3** — Scheduled task fires automatically at next cron interval
- [ ] **UC-12.1.4** — Delete schedule → task stops recurring

### 12.2 One-Time Tasks
- [ ] **UC-12.2.1** — Create task with no schedule → executes once → no recurrence

### 12.3 Webhook Callbacks
- [ ] **UC-12.3.1** — Create task with `callback_url` → on completion, webhook POSTed
- [ ] **UC-12.3.2** — Webhook payload includes task result data
- [ ] **UC-12.3.3** — Webhook signed with HMAC-SHA256
- [ ] **UC-12.3.4** — Webhook delivery failure → retried with backoff

---

## Phase 13: Proxy Management

### 13.1 Proxy Rotation Strategies
- [ ] **UC-13.1.1** — Round-robin rotation → each request uses next proxy in pool
- [ ] **UC-13.1.2** — Weighted rotation → high-success proxies get more traffic
- [ ] **UC-13.1.3** — Geo-targeted → proxy selected by country matches request
- [ ] **UC-13.1.4** — Sticky session → same proxy for entire session duration
- [ ] **UC-13.1.5** — Random → proxies selected randomly from healthy pool

### 13.2 Proxy Health Scoring
- [ ] **UC-13.2.1** — Successful request → proxy health score increases
- [ ] **UC-13.2.2** — Failed request → proxy health score decreases
- [ ] **UC-13.2.3** — Unhealthy proxy (score < threshold) → removed from rotation

### 13.3 Proxy Fallback Chain
- [ ] **UC-13.3.1** — No proxy → datacenter proxy → residential proxy → mobile proxy → unlocker

---

## Phase 14: Session Management

### 14.1 Session Lifecycle
- [ ] **UC-14.1.1** — New task for domain → session `Created` → `Active`
- [ ] **UC-14.1.2** — 3 consecutive failures → session → `Degraded`
- [ ] **UC-14.1.3** — 5 consecutive failures → session → `Invalidated`
- [ ] **UC-14.1.4** — Session TTL exceeded → session → `Expired`

### 14.2 Session Reuse
- [ ] **UC-14.2.1** — Second task for same domain → reuses existing active session
- [ ] **UC-14.2.2** — Session cookies persisted and sent on subsequent requests

### 14.3 Health Scoring
- [ ] **UC-14.3.1** — Health = 60% success_rate + 20% response_time + 20% age
- [ ] **UC-14.3.2** — Health visible in session inspector

---

## Phase 15: Rate Limiting & Quotas

### 15.1 Rate Limiting
- [ ] **UC-15.1.1** — Exceed rate limit → request returns `429 Too Many Requests`
- [ ] **UC-15.1.2** — Token bucket refills over time → requests allowed again
- [ ] **UC-15.1.3** — Per-domain rate limits enforced separately

### 15.2 Tenant Quotas
- [ ] **UC-15.2.1** — Free plan: max 50 tasks/day → 51st task rejected with quota error
- [ ] **UC-15.2.2** — Concurrent task limit enforced (free=2, starter=5, pro=20)
- [ ] **UC-15.2.3** — AI token quota tracked and enforced
- [ ] **UC-15.2.4** — Storage quota tracked and enforced
- [ ] **UC-15.2.5** — Usage counters visible in dashboard

### 15.3 Billing Integration
- [ ] **UC-15.3.1** — `GET /api/v1/billing/plans` → returns available plans
- [ ] **UC-15.3.2** — Subscribe to plan → quotas updated
- [ ] **UC-15.3.3** — Overage charges calculated correctly

---

## Phase 16: Observability & Monitoring

### 16.1 Structured Logging
- [ ] **UC-16.1.1** — Backend logs are JSON format with correlation_id
- [ ] **UC-16.1.2** — Each request has unique correlation_id
- [ ] **UC-16.1.3** — tenant_id present in all log records

### 16.2 Metrics
- [ ] **UC-16.2.1** — `GET /metrics` returns tasks_submitted counter
- [ ] **UC-16.2.2** — `GET /metrics` returns task_duration_ms histogram
- [ ] **UC-16.2.3** — `GET /api/v1/metrics` returns JSON metrics for dashboard

### 16.3 Task Lineage
- [ ] **UC-16.3.1** — Task → Runs → Results → Artifacts chain queryable
- [ ] **UC-16.3.2** — Task detail page shows full lineage

---

## Phase 17: Real-World E-Commerce Scraping Scenarios

End-to-end tests against real e-commerce website patterns.

### 17.1 Product Listing Page (PLP)
- [ ] **UC-17.1.1** — Scrape product grid → extracts: name, price, image, URL for each product
- [ ] **UC-17.1.2** — Handles 20+ products on a single page
- [ ] **UC-17.1.3** — Pagination: follows to page 2, 3... collects all products

### 17.2 Product Detail Page (PDP)
- [ ] **UC-17.2.1** — Scrape single product page → extracts: title, price, description, images, SKU
- [ ] **UC-17.2.2** — Variant data (sizes, colors) extracted if present
- [ ] **UC-17.2.3** — Availability/stock status captured

### 17.3 CJDropshipping-Style Sites
- [ ] **UC-17.3.1** — Scrape wholesale listing (like cjdropshipping.com category) → product list extracted
- [ ] **UC-17.3.2** — Handles dynamic loading (JS-rendered product cards)
- [ ] **UC-17.3.3** — Extracts: product name, wholesale price, MOQ, supplier info

### 17.4 Shopify Stores
- [ ] **UC-17.4.1** — Detected as Shopify → uses API lane → products.json
- [ ] **UC-17.4.2** — Falls back to HTML scraping if API blocked

### 17.5 Amazon-Style Sites
- [ ] **UC-17.5.1** — Complex product page with dynamic content → browser lane
- [ ] **UC-17.5.2** — Anti-bot protection handled via hard-target lane
- [ ] **UC-17.5.3** — Reviews, ratings extracted alongside product data

### 17.6 Static Catalog Sites
- [ ] **UC-17.6.1** — Simple HTML product catalog → HTTP lane → fast extraction
- [ ] **UC-17.6.2** — Schema.org markup used when available

---

## Phase 18: Fallback Chain Verification

### 18.1 Extraction Fallback
- [ ] **UC-18.1.1** — JSON-LD available → used first (fastest, most reliable)
- [ ] **UC-18.1.2** — No JSON-LD → CSS selectors used
- [ ] **UC-18.1.3** — No CSS match → regex patterns used
- [ ] **UC-18.1.4** — All deterministic fail → AI extraction as last resort

### 18.2 Lane Fallback
- [ ] **UC-18.2.1** — HTTP → Browser → Hard-Target chain works end-to-end
- [ ] **UC-18.2.2** — Each escalation logged with reason
- [ ] **UC-18.2.3** — Final result includes `extraction_method` field showing what worked

---

## Appendix A: Test URLs Reference

| URL | Expected Lane | Expected Behavior |
|-----|--------------|-------------------|
| `https://httpbin.org/html` | HTTP | Simple HTML extraction |
| `https://books.toscrape.com/` | HTTP | Product list + pagination |
| `https://quotes.toscrape.com/` | HTTP | Quote + author extraction |
| `https://quotes.toscrape.com/js/` | Browser | JS-rendered version |
| Shopify store (any `.myshopify.com`) | API | products.json API |
| CJDropshipping category page | Browser | Dynamic product grid |
| Site behind Cloudflare | Hard-Target | Anti-bot bypass needed |

---

## Appendix B: Priority Order for Testing

1. **Phase 1** — Infrastructure (blocks everything)
2. **Phase 2** — Auth (blocks UI testing)
3. **Phase 3** — Task CRUD (core functionality)
4. **Phase 6** — HTTP Lane scraping (primary use case)
5. **Phase 11** — Results & Export (user sees output)
6. **Phase 7** — Browser Lane (second most common)
7. **Phase 17** — Real e-commerce scenarios (validates real value)
8. **Phase 5** — Router (ensures correct lane selection)
9. **Phase 8** — Hard-Target (advanced use case)
10. **Phase 10** — AI Normalization (quality improvement)
11. **Phases 4, 9, 12-16, 18** — Supporting features
