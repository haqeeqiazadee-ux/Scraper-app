# Claude Handoff

Claude is the parallel implementation/review partner. Codex remains coordinator, integrator, QA gate, and commit owner.

## Repository Boundary

- Work only in `C:\Users\PC\Scraper-app-verified`.
- Compare prior work in `C:\Users\PC\Scraper-app-fresh` when assigned.
- Do not edit `C:\Users\PC\yousell-admin`.
- Do not print or commit secret values.

## Collaboration Rules

1. Every Claude task receives a narrow scope and explicit owned files.
2. Claude must inspect existing code before proposing or writing code.
3. Claude must report `reuse_as_is`, `extend_existing`, `replace_existing`, `new_code_required`, or `defer_or_skip`.
4. Claude must not create duplicate modules when existing code can be adapted.
5. Claude must include test commands or verification evidence in every task result.
6. Codex reviews actual diffs before committing.

## Active Claude Lane

Phase 1 reuse audit:

- Scope: catalog foundation only.
- Expected output: `docs/agent-sync/CLAUDE_REUSE_AUDIT_PHASE1.md`
- Editing permission: read-only for audit.

## Future Lanes

- Backend runtime lane: actor specs, base runner, provider chain, run API.
- Catalog/spec lane: actor family matrix, generated specs, missing-key ledger.
- Frontend lane: Apify-style actor catalog/detail/run/results UI.
