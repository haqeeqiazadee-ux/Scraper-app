# Claude Phase 1 Reuse Audit Prompt

You are Claude working as a parallel research lane for Codex on the Scraper-app implementation. Do not edit files.

Goal: audit existing code before Phase 1 so we avoid recoding from scratch.

Canonical repo baseline:

- `C:\Users\PC\Scraper-app-verified`
- GitHub repo: `https://github.com/haqeeqiazadee-ux/Scraper-app`
- Main commit: `45bdb35dcfd4764500b4b132dde186cedc767455`

Candidate prior work:

- `C:\Users\PC\Scraper-app-fresh`
- Branch: `saas-repair`
- Purpose: actor catalog/UI work and uncommitted files

Strict boundary:

- Do not inspect or touch `yousell-admin`.
- Do not include any secret values.
- This task is read-only.

Inspect these candidate files if present:

- `services/control-plane/routers/actors.py`
- `packages/core/actor_catalog/registry.py`
- `packages/core/actor_catalog/generated/apify_actor_catalog.json`
- `scripts/generate_actor_catalog.py`
- `tests/unit/test_actor_catalog.py`
- `apps/web/src/pages/ActorsPage.tsx`
- `apps/web/src/pages/ActorDetailPage.tsx`
- `apps/web/src/data/apifyActors.generated.json`
- `apps/web/public/data/actors/*`
- `docs/agent-sync/*` actor catalog docs

Report under 700 words with:

1. Files to reuse as-is, extend, replace, or not use.
2. Existing code gaps before Phase 1 can be committed safely.
3. Test commands that should verify Phase 1.
4. Collision risks when integrating into `C:\Users\PC\Scraper-app-verified`.
