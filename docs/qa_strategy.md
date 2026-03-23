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
