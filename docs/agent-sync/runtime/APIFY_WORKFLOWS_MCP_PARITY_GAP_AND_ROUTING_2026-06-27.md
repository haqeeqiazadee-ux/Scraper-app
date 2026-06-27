# Apify Workflows MCP Parity Gap And Routing

Date: 2026-06-27
Repo: `C:\Users\PC\Scraper-app-verified`
Branch: `codex/own-stack-actors`
Packet: `E1-mcp-parity-gap-and-routing`
Status: `accepted_local_validation_passed`

## Reuse Decision

Decision: `extend_existing`

The repo already had a stdio MCP server at `packages/core/mcp_server.py` with generic scrape, crawl, search, extract, and route tools. E1 extends that server with actor-catalog and native actor-runtime tools instead of creating a second MCP stack.

## Implemented MCP Actor Tools

- `actor_search`: searches the local generated actor catalog without Apify execution.
- `actor_get`: returns one actor with base family, provider ladder, and public API surface.
- `actor_route`: dry-runs actor routing and exposes blocked-policy status for unsupported ladders.
- `actor_run`: executes supported actors through the native actor runtime; unsupported routes are blocked locally.

## Routing Contract

MCP actor tools now inherit the same API-first provider ladder introduced in B2:

- Provider ladders expose `tier`, `connector`, `priority`, required env names, and rationale.
- Unsupported route strategies return a machine-readable `blocked_policy` state rather than falling back to Apify.
- MCP results include the public actor API surface: `/api/v1/actors/{actor_id}/runs`, run detail, results, and export endpoints.
- `actor_run` accepts `options.knowledge_context` and forwards it into the native runner payload, preserving the B1 knowledge-memory trait.

## Frontend MCP Docs

`apps/web/src/pages/McpPage.tsx` now lists the actor MCP tools alongside the existing generic tools so the UI documentation matches the server surface.

## Validation

Commands run:

- `python C:\Users\PC\second-brain\tools\reuse_gate.py --project C:\Users\PC\Scraper-app-verified --task "E1 MCP parity gap and routing" --terms "MCP tools/list tools/call jsonrpc actor run route public api"`
- `python -m pytest tests/unit/test_mcp_actor_tools.py -q`
- `python -m pytest tests/unit/test_actor_provider_ladder.py tests/unit/test_workflow_extension_contract.py tests/unit/test_actor_runtime.py -q`
- `python -m compileall -q packages/core/mcp_server.py tests/unit/test_mcp_actor_tools.py`
- `npm.cmd run build` from `apps/web`

Result:

- Reuse gate: `extend_existing`
- MCP actor tests: `5 passed`
- Actor provider/workflow/runtime regression: `15 passed`
- Compileall: passed
- Web build: passed

## Remaining Work

E1 closes the MCP actor-discovery and native-run routing gap for stdio MCP clients. It does not add a streamed HTTP/SSE MCP gateway or persist MCP actor runs through the database-backed FastAPI actor-run endpoint. Those remain future release-readiness improvements.
