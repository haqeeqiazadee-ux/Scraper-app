# Repo Provenance And Diff Report V2

Generated: 2026-06-23T14:53:22Z

## Verdict

`C:\Users\PC\Scraper-app-main` is not a reliable local proof of `haqeeqiazadee-ux/Scraper-app`: its Git metadata is incomplete/corrupt and Git commands fail there.

`C:\Users\PC\Scraper-app-verified` is the clean local folder that matches `https://github.com/haqeeqiazadee-ux/Scraper-app` `main` at `45bdb35dcfd4764500b4b132dde186cedc767455`.

`C:\Users\PC\Scraper-app-fresh` is the same GitHub repo, but on branch `saas-repair` at `6802b655194a46abf3f9067f3d8a4b11a110180a` with 5 commits ahead of `origin/main` plus uncommitted actor-catalog work. Treat it as candidate work to review, not canonical production state.

## Folder Evidence

| Folder | Git status / identity | File count |
| --- | --- | --- |
| Scraper-app-verified | ## main...origin/main<br>?? docs/agent-sync/ | 631 |
| Scraper-app-fresh | ## saas-repair...origin/saas-repair | 679 |
| Scraper-app-main | fatal: not a git repository (or any of the parent directories): .git | 906 |

## Remote References

```text
45bdb35dcfd4764500b4b132dde186cedc767455	HEAD
45bdb35dcfd4764500b4b132dde186cedc767455	refs/heads/main
6802b655194a46abf3f9067f3d8a4b11a110180a	refs/heads/saas-repair
```

## saas-repair Tracked Diff Stat

```text
.gitignore                                        |   7 +-
 apps/web/src/components/Layout.tsx                |  60 ++-
 apps/web/src/components/TopBar.tsx                |  79 +++
 apps/web/src/pages/ApiKeysPage.tsx                |   2 +-
 apps/web/src/pages/Dashboard.tsx                  | 494 +++++++++---------
 apps/web/src/styles/globals.css                   | 599 +++++++++++++++++++++-
 docs/agent-sync/CLAUDE_CONTINUATION_PROMPT.md     | 130 +++++
 docs/agent-sync/CLAUDE_STATUS.md                  |  69 +++
 docs/agent-sync/CODEX_RELEASE_GATE.md             |  42 ++
 docs/agent-sync/CURRENT_PHASE.md                  |  45 ++
 docs/agent-sync/SECRETS_ACCESS.md                 |  21 +
 netlify.toml                                      |  18 +-
 packages/core/storage/repositories_public_api.py  |   9 +-
 services/control-plane/middleware/api_key_auth.py |   7 +-
 services/control-plane/routers/api_keys.py        |   7 +-
 services/control-plane/routers/health.py          | 100 +---
 16 files changed, 1308 insertions(+), 381 deletions(-)
```

## saas-repair Uncommitted Diff Stat

```text
apps/web/src/App.tsx                   |  4 +++
 apps/web/src/components/SidebarNav.tsx |  1 +
 docs/agent-sync/CLAUDE_STATUS.md       | 47 +++++++++++++++++++++++++++++++++-
 docs/agent-sync/CODEX_RELEASE_GATE.md  | 13 ++++++++++
 services/control-plane/app.py          |  8 ++++++
 5 files changed, 72 insertions(+), 1 deletion(-)
```
