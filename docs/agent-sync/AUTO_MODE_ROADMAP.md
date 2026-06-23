# Auto Mode Roadmap

Generated for `haqeeqiazadee-ux/Scraper-app`.

## Non-Negotiable Scope

- Canonical repository: `https://github.com/haqeeqiazadee-ux/Scraper-app`
- Working branch: `codex/own-stack-actors`
- Canonical local baseline: `C:\Users\PC\Scraper-app-verified`
- Candidate prior work: `C:\Users\PC\Scraper-app-fresh` branch `saas-repair`
- Forbidden target: `C:\Users\PC\yousell-admin`

Apify URLs may remain source metadata only. Native execution must run through this platform's backend and provider stack.

## Mandatory Pre-Code Reuse Gate

Before coding any task:

1. Search existing code in `services/`, `packages/`, `apps/web/`, `tests/`, `docs/`, and `C:\Users\PC\Scraper-app-fresh`.
2. Classify the task as `reuse_as_is`, `extend_existing`, `replace_existing`, `new_code_required`, or `defer_or_skip`.
3. Prefer reuse, extension, or replacement over duplicate new code.
4. Record inspected files and the decision in `IMPLEMENTATION_LEDGER.md`.
5. Only then edit code.

No phase can be committed unless its ledger entries prove this gate was completed.

## Phase Gates

| Phase | Target | Measurable Gate | Commit Rule |
|---|---|---|---|
| 0 | Repo lock and agent coordination | Branch exists; provenance recorded; Claude/Codex roles documented; reuse gate documented | Commit docs and boundary correction |
| 1 | Catalog foundation | 27,753 actors available through backend/frontend catalog; search/filter/detail work; Apify URL is metadata only | Commit after catalog tests/build checks pass |
| 2 | Actor runtime core | `ActorSpec`, `BaseActorRunner`, provider chain, missing-key states, and run state model exist | Commit after runtime unit tests pass |
| 3 | Native run API | `POST /api/v1/actors/{actor_id}/runs` executes/skips/fails through native backend state machine | Commit after API tests pass |
| 4 | Base families A | `generic_web_page_extraction`, `marketplace_product_catalog`, `commerce_storefront_generic`, `local_maps_serp` | Commit after sampled family tests pass or skip with reason |
| 5 | Base families B | Jobs, real estate, leads, reviews, news/content monitoring | Commit after contract and sampled tests pass |
| 6 | Base families C | Social, media, ads/SEO, documents/feeds, finance, travel | Commit after missing-key ledger proves skipped actors do not block progress |
| 7 | High-risk families | Auth sessions, browser utilities, integration automation | Commit only with explicit safety gates and no surprise external actions |
| 8 | SaaS UI | Apify-style catalog, detail, run button, timeline, results/export, skipped-key states | Commit after frontend build and UI smoke checks |
| 9 | Production gate | Deployment readiness, env docs, sampled live runs, final skipped-key register | Commit final release gate |

## Auto Mode Stop Conditions

Continue automatically after each passing commit unless one of these occurs:

- A destructive git operation would be required.
- A required paid signup/API key blocks an entire family and cannot be skipped safely.
- A policy/security issue makes a workflow family unsafe.
- Repo state risks losing existing user or agent work.

Missing API keys are not global blockers. Mark only the affected actor as `skipped_missing_key`, document the env var name, and continue.
