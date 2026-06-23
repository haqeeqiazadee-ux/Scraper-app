# Claude Phase 2 Runtime Reuse Audit Prompt

You are Claude working as a parallel read-only audit lane for Codex on Scraper-app Phase 2. Do not edit files.

Goal: before Codex adds native actor runtime core, inspect existing code for reusable task/run/provider abstractions so we avoid recoding from scratch.

Repository:

- `C:\Users\PC\Scraper-app-verified`
- Branch: `codex/own-stack-actors`
- Boundary: only this repo; do not inspect or touch `yousell-admin`
- Do not include secret values

Phase 2 target: add runtime core for native actor execution, not actual family implementations yet. Expected concepts:

- `ActorSpec`
- `BaseActorRunner`
- `ProviderChain`
- requirement/missing-key checks
- run state enum
- structured runtime result

This should integrate later with `POST /api/v1/actors/{actor_id}/runs`.

Inspect these existing areas:

- `packages/core/router.py`
- `packages/core/crawl_manager.py`
- `packages/core/task_queue.py` or similar if present
- `packages/core/extractors/*`
- `packages/contracts/*`
- `services/control-plane/routers/execution.py`
- `services/control-plane/routers/smart_scrape.py`
- `services/control-plane/routers/tasks.py`
- `services/control-plane/models.py` or DB models if present
- `services/control-plane/routers/actors.py`
- `packages/core/actor_catalog/*`

Report under 600 words:

1. What should be reused/extended/replaced/new for actor runtime core.
2. Recommended file/module locations.
3. Risks to avoid, especially duplicate task/run models or Apify delegation.
4. Minimal tests Codex should write first for Phase 2.

Read-only. No edits.
