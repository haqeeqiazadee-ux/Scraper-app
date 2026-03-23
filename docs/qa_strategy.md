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
- [ ] **UC-1.1.1** — `GET /health` returns `200 OK`
- [ ] **UC-1.1.2** — `GET /ready` returns `200 OK` (confirms DB + Redis connected)
- [ ] **UC-1.1.3** — `GET /metrics` returns Prometheus-format text

### 1.2 Database Connectivity
- [ ] **UC-1.2.1** — `GET /api/v1/tasks` returns `200` with empty list (DB reads work)
- [ ] **UC-1.2.2** — `GET /api/v1/policies` returns `200` with empty list
- [ ] **UC-1.2.3** — Backend logs show no `OperationalError` or `ConnectionRefused`

### 1.3 Frontend Reachability
- [ ] **UC-1.3.1** — Web dashboard loads at deployed URL (HTML renders)
- [ ] **UC-1.3.2** — Login page renders at `/login`
- [ ] **UC-1.3.3** — Browser console shows no CORS errors on API calls
- [ ] **UC-1.3.4** — `API_URL` environment variable points to correct backend

### 1.4 Frontend-Backend Integration
- [ ] **UC-1.4.1** — Login page can reach `POST /api/v1/auth/token` (no network error)
- [ ] **UC-1.4.2** — After login, dashboard loads and calls `GET /api/v1/tasks`
- [ ] **UC-1.4.3** — API errors show user-friendly messages (not raw stack traces)

---

## Phase 2: Authentication & Authorization

### 2.1 Login Flow
- [ ] **UC-2.1.1** — Enter valid credentials → redirected to `/dashboard`
- [ ] **UC-2.1.2** — Enter invalid credentials → error message shown, stays on `/login`
- [ ] **UC-2.1.3** — Access `/dashboard` without login → redirected to `/login`
- [ ] **UC-2.1.4** — JWT token stored in browser after successful login

### 2.2 Session Management
- [ ] **UC-2.2.1** — Refresh page while logged in → stays logged in (token persists)
- [ ] **UC-2.2.2** — Expired token → auto-logout, redirected to `/login`
- [ ] **UC-2.2.3** — `GET /api/v1/auth/me` returns current user profile

### 2.3 Tenant Isolation
- [ ] **UC-2.3.1** — API requests without `Authorization` header → `401`
- [ ] **UC-2.3.2** — Tasks created by tenant A are not visible to tenant B

---

## Phase 3: Task Management (CRUD)

### 3.1 Create Task
- [ ] **UC-3.1.1** — Navigate to Tasks → Click "Create Task" → form renders
- [ ] **UC-3.1.2** — Fill: name="Test Task", url="https://httpbin.org/html", type=scrape → submit → `201 Created`
- [ ] **UC-3.1.3** — New task appears in task list with status `pending`
- [ ] **UC-3.1.4** — Submit with empty URL → validation error shown
- [ ] **UC-3.1.5** — Submit with invalid URL → validation error shown

### 3.2 Read Tasks
- [ ] **UC-3.2.1** — Task list page loads with pagination
- [ ] **UC-3.2.2** — Click a task → task detail page shows name, URL, status, created_at
- [ ] **UC-3.2.3** — Task detail shows run history (initially empty)

### 3.3 Update Task
- [ ] **UC-3.3.1** — Edit task name → save → name updated in list
- [ ] **UC-3.3.2** — Change priority → save → priority reflected

### 3.4 Delete Task
- [ ] **UC-3.4.1** — Delete a task → task removed from list
- [ ] **UC-3.4.2** — Confirm dialog shown before deletion

### 3.5 Cancel Task
- [ ] **UC-3.5.1** — Cancel a `pending` task → status changes to `cancelled`
- [ ] **UC-3.5.2** — Cancel an already `completed` task → error or no-op

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
