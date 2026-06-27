# Apify Workflows External R&D Gap Matrix

Date: 2026-06-27
R&D source: `docs/agent-sync/SCRAPER_APP_APIFY_COMPETITOR_EXTERNAL_RND_2026-06-27.md`
R&D status: current, not stale

## Rule

Apify documentation URLs are competitor metadata and documentation references only. They are not runtime dependencies and must not become live crawl targets for actor execution.

API-first/provider-first is a mandatory product rule. Actor families must prefer official/public APIs, existing internal APIs, provider SDKs, and existing platform connectors before new HTTP scraping, browser automation, or hard-target implementation. New scrape/browser code needs a recorded no-durable-API/provider rationale.

## Gap Matrix

| Gate | Current State | Parity Target | Superiority Target | Initial Status | First Packet |
|---|---|---|---|---|---|
| Actor catalog | 27,753 actors generated and browsable data exists | Stable catalog/search/detail/input metadata | Knowledge and value metrics layered onto actor pages | partial | A1/B1 |
| API-first/provider-first routing | Existing connectors cover Shopify, Keepa/Amazon, Google Maps/Serper, worker HTTP, browser, and some platform APIs, but no per-family provider-ladder matrix exists | Each base family has official/public API, provider SDK, connector, HTTP, browser, authenticated-session fallback order documented and tested | API availability, latency, cost, reliability, and cache-savings drive automatic provider routing | incomplete | B2 |
| Extensible workflow substrate | Actor families exist, but future categories are not yet proven through a no-core-rewrite extension contract | WorkflowSpec, ProviderLadder, WorkflowAdapter, WorkflowProfile, WorkflowUIContract, WorkflowAPISurface, and WorkflowQAGate support new categories without shared runtime/router/storage rewrites | Any future platform category can inherit API-first routing, memory, governance, billing, trace/eval, security, UI, API, and QA contracts by registration | incomplete | B3 |
| Actor execution | Native runtime and run API exist through Phase 5 | Runs, logs, status, artifacts, result rows, retries | Knowledge-backed runtime decisions and self-learning profiles | partial | B1/C1 |
| Self-learning profiles | WorkflowProfile existed as an extension concept; runtime profile promotion was not implemented | Learning events, replay fixtures, profile versioning, and promotion gates | Sanitized learning events and replay-gated strategy patch promotion inherited by all actors | partial | E2 |
| Input schemas | Base actor specs and family schemas exist | Dynamic actor input schema coverage | AI-assisted schema aliases with deterministic replay | partial | B1 |
| Workflow operations | Some schedules/webhooks/public API features exist in broader app | Schedules, webhooks, queues, storage, usage tracking | Freshness-aware background refresh and cache-savings reporting | incomplete | C1/D1 |
| MCP distribution | MCP features exist elsewhere in project context, current actor parity not proven | MCP tools/resources/prompts, dynamic actor discovery, structured outputs | MCP with knowledge/provenance/freshness metadata | incomplete | E1 |
| Knowledge reuse | Not yet implemented as actor-runtime trait | DB/cache/graph/vector/artifact decision path | Tenant-safe memory with partial refresh and replay validation | incomplete | B1 |
| Observability/evals | Actor trace/eval metadata exists and deterministic fixture candidates can be built from failed or low-confidence traces | Typed run traces and deterministic regression fixtures | Trace-to-fixture self-improvement loop with review queue and CI replay | partial | D1/G2 |
| AI security | Secret scan gates exist; actor AI security tests not yet present | Prompt injection/tool misuse/data leakage tests | OWASP-style agent security gate per actor family | incomplete | D1 |
| Pricing/cost | Existing usage/account concepts in app context, actor cost proof not present | Estimated/actual run cost and quotas | Cache savings and compute-adjusted margin by family | incomplete | D1 |
| Customer value proof | Not yet present for actor platform | Basic run success/failure dashboards | Time saved, freshness, data quality, cost/result dashboards | incomplete | D1 |

## Immediate Priority

Completed local packets now cover API-first provider ladders (`B2`), no-core-rewrite workflow extensibility (`B3`), MCP actor parity (`E1`), replay-gated strategy-profile learning (`E2`), and deterministic trace-to-fixture candidates (`G2`). Remaining release-readiness priority is persisted profile APIs, fixture review queues, workflow operations parity, pricing/value dashboards, and full final QA.
