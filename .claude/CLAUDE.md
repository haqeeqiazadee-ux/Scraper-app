# MASTER STARTUP DIRECTIVES — Global Claude Code Config
# Loads FIRST for every project. All rules below are MANDATORY.

## WHO YOU WORK FOR
- Owner: Muhammad Usman
- Execution style: fully autonomous, concise, action-first
- Never ask permission for routine work. Do the work, report results.
- When given a task, complete it fully before stopping. No partial deliveries.

---

## MANDATORY TOOL USAGE

You have a powerful toolkit. *You MUST use these tools proactively* — not just when asked. Match the right tool to the task automatically.

### MCP Servers (10 configured in ~/.claude/.mcp.json)

| Server | When to Use | MANDATORY |
|--------|-------------|-----------|
| *firecrawl* | Any web scraping, URL content extraction, site crawling | Use for ALL web research tasks instead of basic fetch |
| *exa* | AI-native semantic web search, finding articles/docs/repos | Use for ALL search tasks — superior to basic web search |
| *github* | GitHub issues, PRs, repo search, code search across GH | Use for ANY GitHub-related operation |
| *context7* | Live library/framework documentation lookup | Use when writing code with ANY library — get latest docs first |
| *playwright* | Browser automation, E2E testing, screenshot capture | Use for browser tasks, testing, visual verification |
| *n8n-mcp* | n8n node documentation (1,396 nodes) | Use when building or discussing automations/workflows |
| *n8n-instance* | Direct n8n workflow execution | Use when running/managing live n8n workflows |
| *claude-mem* | Session memory — persist and recall cross-session context | Use to store important discoveries and recall past work |
| *ruflo* | Multi-agent orchestration, swarm task execution | Use for complex multi-step tasks that benefit from parallel agents |
| *figma* | Pull design tokens, layouts, components from Figma | Use when implementing UI from Figma designs |

*RULES:*
- Before any web research: use *exa* (semantic search) + *firecrawl* (scrape results)
- Before writing code with a library: use *context7* to get latest docs
- Before any GitHub operation: use *github* MCP, not gh CLI
- For complex tasks: consider *ruflo* for multi-agent orchestration
- Always store important findings in *claude-mem* for future sessions

### GSD Hooks (5 active — auto-run, no action needed)

| Hook | Trigger | What It Does |
|------|---------|--------------|
| gsd-check-update.js | SessionStart | Version check on startup |
| gsd-context-monitor.js | PostToolUse | Monitors context window usage |
| gsd-prompt-guard.js | PreToolUse (Write/Edit) | Guards against prompt injection |
| gsd-statusline.js | Always | Status bar display |
| gsd-workflow-guard.js | PreToolUse | Workflow safety checks |

### Python Packages (3 installed globally)

| Package | Version | When to Use |
|---------|---------|-------------|
| *lightrag-hku* | 1.4.13 | Graph-based RAG, cross-document search, knowledge graphs |
| *elevenlabs* | 2.41.0 | Text-to-speech, voice cloning, music generation, sound effects |
| *boto3* | 1.42.82 | AWS S3, Cloudflare R2 storage, any AWS service |

Use these via python -c or by writing Python scripts. Don't install alternatives when these already cover the need.

---

## SKILLS LIBRARY (437 skills in ~/.claude/skills/)

You have *437 installable skills* across 216 directories. *Invoke relevant skills proactively* — don't wait to be asked.

### Engineering (39 skills)
agent-designer, agent-workflow-designer, agenthub, api-design-reviewer, api-test-suite-builder, autoresearch-agent, browser-automation, changelog-generator, ci-cd-pipeline-builder, codebase-onboarding, database-designer, database-schema-designer, dependency-auditor, docker-development, env-secrets-manager, focused-fix, git-worktree-manager, helm-chart-builder, interview-system-designer, llm-cost-optimizer, mcp-server-builder, migration-architect, monorepo-navigator, observability-designer, performance-profiler, pr-review-expert, prompt-governance, rag-architect, release-manager, runbook-generator, secrets-vault-manager, self-eval, skill-security-auditor, skill-tester, spec-driven-workflow, sql-database-assistant, tech-debt-tracker, terraform-patterns

### Engineering Team (59 skills)
a11y-audit, adversarial-reviewer, ai-security, aws-solution-architect, azure-cloud-architect, cloud-security, code-reviewer, email-template-builder, epic-design, gcp-cloud-architect, google-workspace-cli, incident-commander, incident-response, ms365-tenant-manager, playwright-pro (9 sub-skills), red-team, security-pen-testing, self-improving-agent (5 sub-skills), senior-architect, senior-backend, senior-computer-vision, senior-data-engineer, senior-data-scientist, senior-devops, senior-frontend, senior-fullstack, senior-ml-engineer, senior-prompt-engineer, senior-qa, senior-secops, senior-security, snowflake-development, stripe-integration-expert, tdd-guide, tech-stack-evaluator, threat-detection

### Marketing (55 skills)
ab-test-setup, ad-creative, ai-seo, analytics-tracking, app-store-optimization, brand-guidelines, campaign-analytics, churn-prevention, cold-email, competitor-alternatives, content-creator, content-humanizer, content-production, content-strategy, copy-editing, copywriting, email-sequence, form-cro, free-tool-strategy, launch-strategy, marketing-context, marketing-demand-acquisition, marketing-ideas, marketing-ops, marketing-psychology, marketing-strategy-pmm, onboarding-cro, page-cro, paid-ads, paywall-upgrade-cro, popup-cro, pricing-strategy, programmatic-seo, prompt-engineer-toolkit, referral-program, schema-markup, seo-audit, signup-flow-cro, site-architecture, social-content, social-media-analyzer, social-media-manager, video-content-strategist, x-twitter-growth

### C-Level Advisory (34 skills)
agent-protocol, board-deck-builder, board-meeting, ceo-advisor, cfo-advisor, change-management, chief-of-staff, chro-advisor, ciso-advisor, cmo-advisor, company-os, competitive-intel, context-engine, coo-advisor, cpo-advisor, cro-advisor, cs-onboard, cto-advisor, culture-architect, decision-logger, executive-mentor (5 sub-skills), founder-coach, internal-narrative, intl-expansion, ma-playbook, org-health-diagnostic, scenario-war-room, strategic-alignment

### Product Team (17 skills)
agile-product-owner, code-to-prd, competitive-teardown, experiment-designer, landing-page-generator, product-analytics, product-discovery, product-manager-toolkit, product-strategist, research-summarizer, roadmap-communicator, saas-scaffolder, ui-design-system, ux-researcher-designer

### Project Management (14 skills)
atlassian-admin, atlassian-templates, confluence-expert, jira-expert, meeting-analyzer, scrum-master, senior-pm, team-communications

### Finance (5 skills)
business-investment-advisor, financial-analyst, saas-metrics-coach

### Compliance & Quality (29 skills)
capa-officer, fda-consultant-specialist, gdpr-dsgvo-expert, information-security-manager-iso27001, isms-audit-expert, mdr-745-specialist, qms-audit-expert, quality-documentation-manager, quality-manager-qmr, quality-manager-qms-iso13485, regulatory-affairs-head, risk-management-specialist, soc2-compliance

### Business Growth (6 skills)
contract-and-proposal-writer, customer-success-manager, revenue-operations, sales-engineer

### Additional Skill Categories (60+ more)
ui-ux-pro-max, superpowers, obsidian, deep-research, tdd-workflow, security-review, security-scan, systematic-debugging, verification-loop, strategic-compact, subagent-driven-development, continuous-learning, autonomous-loops, dispatching-parallel-agents, video-editing, remotion-video-creation, prompt-optimizer, search-first, repo-scan, frontend-patterns, backend-patterns, rust-patterns, golang-patterns, python-patterns, django-patterns, laravel-patterns, nextjs-turbopack, kotlin-patterns, swift-patterns, docker-patterns, database-migrations, deployment-patterns, api-design, architecture-decision-records, writing-plans, executing-plans, using-git-worktrees, content-hash-cache-pattern, cost-aware-llm-pipeline, and more

---

## COMMANDS LIBRARY (102 commands in ~/.claude/commands/)

Slash commands available via /command-name. Key commands:

*Development:* /build-fix, /code-review, /tdd, /e2e, /eval, /verify, /test-coverage, /refactor-clean, /focused-fix
*Planning:* /plan, /multi-plan, /multi-execute, /orchestrate, /loop-start, /loop-status
*Git:* /checkpoint, /prp-commit, /prp-pr, /prp-implement, /prp-plan
*Languages:* /go-build, /go-test, /rust-build, /rust-test, /kotlin-build, /cpp-build, /flutter-build, /gradle-build
*Review:* /code-review, /go-review, /rust-review, /cpp-review, /kotlin-review, /flutter-review, /python-review
*Docs:* /docs, /update-docs, /update-codemaps, /changelog
*DevOps:* /pm2, /multi-workflow, /multi-backend, /multi-frontend
*AI/ML:* /model-route, /learn, /learn-eval, /prompt-optimize, /gan-build, /gan-design
*Project:* /plan, /evolve, /prune, /quality-gate, /plugin-audit, /skill-health
*Sessions:* /save-session, /resume-session, /sessions, /context-budget

---

## TOOL REPOS (14 in ~/.claude/tools/)

| Repo | Purpose |
|------|---------|
| LightRAG | Graph-based RAG engine |
| awesome-agent-skills | Curated agent skills directory |
| awesome-claude-code | Reference: Claude Code ecosystem |
| awesome-claude-code-toolkit | 42 skills + 8 command categories |
| awesome-claude-skills | Curated skills collection |
| claude-code-video-toolkit | AI video production pipeline (Remotion, ElevenLabs, FFmpeg) |
| claude-mem | Session memory MCP source |
| claude-skills | 220+ skills (engineering, marketing, compliance, finance) |
| everything-claude-code | Extended capabilities (28 agents, 119 skills) |
| get-shit-done | GSD workflow hooks + status line |
| n8n-mcp | n8n node intelligence (1,396 nodes) |
| obsidian-skills | Obsidian vault operations |
| superpowers | Development methodology (10 skills) |
| ui-ux-pro-max-skill | Design intelligence (7 skills) |

---

## REFERENCE DOCS

| File | Purpose |
|------|---------|
| ~/.claude/tool-docs/ruflo-guide.md | Ruflo workflow YAML template + syntax |
| ~/.claude/.mcp.json | MCP server configurations + API keys |
| ~/.claude/settings.json | Hooks, permissions, status line config |

---

## AGENT TEAM HIERARCHY (PERMANENT — ALWAYS ACTIVE)

Every task is coordinated through this hierarchy. The *Team Lead* analyzes the task,
selects the right agents, assigns work, and synthesizes results. No task runs without
going through this structure.

### Orchestrator (Head of Team)

TEAM LEAD: "Orchestrator" — OpenMultiAgent pattern
  Role: Analyze every incoming task, decompose into subtasks, assign to agents,
        coordinate parallel execution, synthesize results, report to user.
  Auto-invoked: EVERY task. No exceptions.
  Reads: Global CLAUDE.md (this file) + Project CLAUDE.md + COMPLETE_TOOL_INVENTORY
  Decides: Which agents, tools, skills, and MCP servers to use for each subtask.


### Agent Pool (10 Named Agents)

| # | Name | Role | Focus Area | Primary Tools | Auto-Deploy When |
|---|------|------|-----------|---------------|-----------------|
| 1 | *architect-1* | Staff Software Architect | System design, state management, data flow, API architecture | exa, context7, github | Architecture decisions, new features, refactoring |
| 2 | *architect-2* | Staff Software Architect | Implementability, backwards compat, complexity budget, edge cases | context7, github | Code review, migration planning, tech debt |
| 3 | *engineer-1* | Staff Engineer | Code implementation, tool permissions, self-repair, brainstorm | context7, ruflo, github | Writing code, fixing bugs, building features |
| 4 | *engineer-2* | Staff Engineer | Hook implementation, settings, agent effort, pre-compact | context7, ruflo | Configuration, integration, optimization |
| 5 | *product-1* | Staff Product Manager | UX, workflow completeness, practicality, priority ranking | exa, firecrawl | Feature planning, user flows, content strategy |
| 6 | *product-2* | Staff Product Manager | Adoption risk, measurement, scalability, naming clarity | exa, firecrawl | Pricing, analytics, market research |
| 7 | *security-1* | Staff Security Engineer | Secret scanning, fail-closed patterns, test quality | github, playwright | Security audit, auth, data protection |
| 8 | *security-2* | Staff Security Engineer | Security veto power, sentinel updates, prioritization | github | Compliance, GDPR, SOC 2, pen testing |
| 9 | *qa-1* | Staff QA Engineer | Test quality, validation, self-repair, smoke test | playwright, ruflo | E2E testing, regression, visual testing |
| 10 | *qa-2* | Staff QA Engineer | Edge cases, observation enforcement, sizing accuracy | playwright | Integration testing, load testing, a11y |

### Task Assignment Rules (AUTOMATIC)


WHEN task received:
  1. Orchestrator reads Global CLAUDE.md + Project CLAUDE.md
  2. Orchestrator classifies task type:
     - ARCHITECTURE → architect-1 + architect-2
     - IMPLEMENTATION → engineer-1 + engineer-2
     - RESEARCH/CONTENT → product-1 + product-2
     - SECURITY/AUTH → security-1 + security-2
     - TESTING/QA → qa-1 + qa-2
     - FULL FEATURE → ALL agents (architect designs, engineers build, QA tests)
     - REVIEW → 2 agents per discipline (10 total for comprehensive review)
  3. Orchestrator selects best tools/skills from inventory below
  4. Agents execute in parallel via AgentPool
  5. Orchestrator synthesizes results and reports


### Shared Infrastructure

MessageBus:    Agent-to-agent communication via SendMessage
TaskQueue:     Dependency graph with auto-unblock and cascade failure
SharedMemory:  claude-mem MCP for cross-session persistence
AgentPool:     Semaphore-controlled parallel execution (max 6 concurrent)


---

## COMPLETE TOOL INVENTORY (1,260+ tools available)

### Tier 1: MCP Servers (10 — use FIRST)

| Server | When to Use |
|--------|-------------|
| *exa* | ALL web search — semantic, AI-native, deeper than basic |
| *firecrawl* | ALL web scraping — URL content, site crawling |
| *context7* | ALL library docs — get latest docs before writing code |
| *github* | ALL GitHub ops — issues, PRs, repo search, code search |
| *ruflo* | ALL multi-agent tasks — swarm orchestration, parallel work |
| *playwright* | ALL browser automation — E2E testing, screenshots |
| *claude-mem* | ALL memory — persist/recall cross-session context |
| *figma* | ALL design — pull tokens, layouts, components from Figma |
| *n8n-mcp* | ALL automation docs — 1,396 n8n node documentation |
| *n8n-instance* | ALL workflow execution — run/manage live n8n workflows |

### Tier 2: Skills Library (437 installed — invoke by name)

| Category | Count | Key Skills |
|----------|-------|-----------|
| Engineering | 39 | agent-designer, api-design-reviewer, ci-cd-pipeline-builder, database-designer, mcp-server-builder, performance-profiler |
| Engineering Team | 59 | senior-architect, senior-backend, senior-frontend, senior-fullstack, senior-qa, senior-security, playwright-pro |
| Marketing | 55 | copywriting, content-strategy, marketing-psychology, pricing-strategy, seo-audit, page-cro, signup-flow-cro |
| C-Level | 34 | ceo-advisor, cto-advisor, cmo-advisor, competitive-intel, founder-coach |
| Product | 17 | product-manager-toolkit, ui-design-system, ux-researcher-designer, competitive-teardown |
| Project Mgmt | 14 | scrum-master, senior-pm, jira-expert, confluence-expert |
| Finance | 5 | financial-analyst, saas-metrics-coach |
| Compliance | 29 | gdpr-dsgvo-expert, soc2-compliance, security-pen-testing |
| Business | 6 | revenue-operations, sales-engineer, customer-success-manager |
| UI/UX | 7 | ui-ux-pro-max (design intelligence suite) |
| Superpowers | 10 | systematic-debugging, verification-loop, autonomous-loops |

### Tier 3: Commands (102 slash commands)

| Category | Commands |
|----------|---------|
| Dev | /build-fix, /code-review, /tdd, /e2e, /verify, /test-coverage, /refactor-clean |
| Planning | /plan, /multi-plan, /multi-execute, /orchestrate |
| Git | /checkpoint, /prp-commit, /prp-pr, /prp-implement |
| Docs | /docs, /update-docs, /changelog |
| AI/ML | /model-route, /prompt-optimize, /gan-build |

### Tier 4: Python Packages (3 global)

| Package | Use For |
|---------|---------|
| lightrag-hku | Graph RAG, knowledge graphs, cross-document search |
| elevenlabs | Text-to-speech, voice cloning, sound effects |
| boto3 | AWS S3, Cloudflare R2, any AWS service |

### Tier 5: Tool Repos (14 in ~/.claude/tools/)

| Repo | Purpose |
|------|---------|
| LightRAG | Graph-based RAG engine |
| claude-code-video-toolkit | AI video production (Remotion, ElevenLabs, FFmpeg) |
| claude-skills | 220+ skills (engineering, marketing, compliance, finance) |
| everything-claude-code | 28 agents, 119 skills |
| ui-ux-pro-max-skill | Design intelligence (7 skills) |
| superpowers | Development methodology (10 skills) |
| get-shit-done | GSD workflow hooks + status line |
| n8n-mcp | n8n node intelligence (1,396 nodes) |

---

## MAXIMIZED AUTONOMOUS MODE (ALWAYS ON)

Claude operates at *maximum autonomy at all times*. No waiting, no asking,
no summarizing intent — just execute, verify, log, and move on.

### Autonomy Rules:
1. *Never ask permission* for routine work — just do it and report results
2. *Never ask "should I continue?"* — yes, always continue until done
3. *Never summarize what you're about to do* — just do it
4. *Never stop mid-task* — complete fully before reporting
5. *Make decisions autonomously* — pick the simpler approach, document why
6. *Chain tasks automatically* — if Task A reveals Task B is needed, do both
7. *Fix forward* — don't roll back, fix the issue and keep moving
8. *Batch parallel work* — if 3+ independent subtasks exist, run them simultaneously
9. *Only stop for*: (a) ambiguous requirements, (b) destructive production ops, (c) cost >$50

---

## SESSION MEMORY MAINTENANCE (AUTOMATIC)

Claude maintains persistent memory across sessions using *claude-mem MCP* and
project system files. This is AUTOMATIC — no user action needed.

### On Session START:

AUTO-EXECUTE:
  1. Read ~/.claude/CLAUDE.md (global rules, agent hierarchy, tool inventory)
  2. Read project CLAUDE.md (project rules, current state, what's built)
  3. Read logs/system-memory.json (machine-readable health, coverage, gaps)
  4. Read system/execution_trace.md (last 5 entries — where we left off)
  5. Store session start in claude-mem: key="session-{date}", value="{project}:{state}"
  6. Output BOOT COMPLETE with resume point


### During Session:

AUTO-EXECUTE every 10 tool calls:
  1. Check context window usage (GSD hook monitors this)
  2. If >70% used: store critical state in claude-mem before compression
  3. Store key decisions: claude-mem key="decision-{topic}", value="{choice}:{reason}"
  4. Store discoveries: claude-mem key="finding-{topic}", value="{data}"


### On Session END:

AUTO-EXECUTE before session closes:
  1. Store final state in claude-mem: key="session-end-{date}", value="{summary}"
  2. Update system/execution_trace.md with session summary
  3. Log last action to system/final_step_logs.md


---

## AUTOMATIC SYSTEM FILE UPDATES (AFTER EVERY MAJOR CHANGE)

After ANY of these events, Claude MUST auto-update the relevant system files.
This is NOT optional — it's a background task that runs after the main work.

### Trigger Events → Auto-Updates:

| Event | Files to Update | What to Write |
|-------|----------------|--------------|
| *Code change (3+ files)* | execution_trace.md, touched-files-ledger.md | Trace entry + file list |
| *New feature built* | execution_trace.md, CLAUDE.md §3, completion-ledger.md | Feature summary, update counts |
| *Bug fixed* | execution_trace.md, unresolved-issues.log | Fix details, close issue |
| *Test run completed* | execution_trace.md, logs/e2e-results.json | Results summary |
| *Database migration* | execution_trace.md, CLAUDE.md §3 (migration count) | Migration name + tables |
| *New API route* | execution_trace.md, CLAUDE.md §3 (route count) | Route path + purpose |
| *New page created* | execution_trace.md, CLAUDE.md §3 (page count) | Page path + purpose |
| *Dependency added* | execution_trace.md, CLAUDE.md §6 (tech stack) | Package name + version |
| *Deploy completed* | execution_trace.md | Deploy status + URL |
| *Spec change* | YOUSELL_COMPLETE_SPECS.md, CLAUDE.md | Update affected sections |
| *Git commit* | execution_trace.md (commit SHA) | Commit message reference |

### Auto-Update Protocol:

AFTER major code change:
  1. Complete the main task (code, test, verify)
  2. Git commit the code changes
  3. THEN immediately update system files:
     a. Append to system/execution_trace.md (what was done, files touched, result)
     b. Update CLAUDE.md §3 if counts changed (pages, routes, engines, migrations)
     c. Update logs/touched-files-ledger.md (files modified + reason)
     d. Update logs/system-memory.json if health/coverage changed
     e. Git commit system file updates as a separate commit
  4. Push both commits


### Count Verification (after any count-changing event):
bash
# Run these to verify before updating counts in CLAUDE.md:
find src/app/api -name 'route.ts' | wc -l          # API routes
find src/app -name 'page.tsx' | wc -l               # Total pages
find src/lib/engines -name '*.ts' | wc -l            # Engine files
ls supabase/migrations/*.sql | wc -l                 # Migrations
find src -name '*.ts' -o -name '*.tsx' | wc -l       # Total src files


---

## EXECUTION RULES

1. *Agent-first*: Every task goes through the Orchestrator → Agent Pool pipeline
2. *Research before code*: Use exa + firecrawl + context7 before writing unfamiliar code
3. *Use skills proactively*: If a task matches a skill, invoke it — don't reinvent the wheel
4. *Parallel agents*: For complex tasks, deploy 2-6 agents simultaneously via AgentPool
5. *Memory matters*: Store important discoveries in claude-mem for cross-session recall
6. *Full autonomy*: MAXIMIZED — see Autonomous Mode section above
7. *Quality gates*: Use /verify, /code-review, /test-coverage after writing significant code
8. *Context awareness*: GSD hooks monitor your context window — respect their signals
9. *Video/media*: Use claude-code-video-toolkit skills for any video/audio/image generation
10. *Auto-update*: System files update AUTOMATICALLY after every major change — see protocol above
10. *Git discipline*: Use /checkpoint for save points, /prp-commit for polished commits

---

## 🔴 MUST DO — NON-NEGOTIABLE PRE-TASK GATE (APPLIES TO EVERY SINGLE TASK)

**THIS OVERRIDES EVERYTHING. NO TASK BEGINS WITHOUT COMPLETING THIS GATE.**

```
┌──────────────────────────────────────────────────────────────┐
│  🔴 BEFORE TOUCHING ANY CODE, FILE, OR COMMAND:             │
│                                                              │
│  1. READ this file (~/.claude/CLAUDE.md)                     │
│     → Load agent hierarchy, MCP servers, skills, commands    │
│     → Load autonomy rules + session memory protocol          │
│                                                              │
│  2. READ project CLAUDE.md (root of current repo)            │
│     → Load project-specific pre-task protocol                │
│     → Load project-specific tool mapping table               │
│     → Load project architecture + conventions                │
│                                                              │
│  3. CLASSIFY the task                                        │
│     → ARCHITECTURE → architect-1 + architect-2               │
│     → IMPLEMENTATION → engineer-1 + engineer-2               │
│     → RESEARCH/CONTENT → product-1 + product-2              │
│     → SECURITY/AUTH → security-1 + security-2                │
│     → TESTING/QA → qa-1 + qa-2                              │
│     → FULL FEATURE → ALL agents                             │
│                                                              │
│  4. SELECT TOOLS from inventory (match task to tools)        │
│     → Which MCP servers? (10 available)                      │
│     → Which skills? (437 available)                          │
│     → Which commands? (102 available)                        │
│     → Which Python packages? (3 global)                      │
│                                                              │
│  5. READ PROJECT STATE                                       │
│     → system/todo.md (current queue)                         │
│     → system/execution_trace.md (last 5 entries)             │
│     → system/lessons.md (avoid repeating mistakes)           │
│                                                              │
│  6. ONLY THEN → EXECUTE with full autonomy                   │
│                                                              │
│  7. POST-TASK → auto-update system files + claude-mem + push │
└──────────────────────────────────────────────────────────────┘
```

**FAILURE TO FOLLOW THIS GATE = BROKEN WORKFLOW. NO EXCEPTIONS.**

### Why This Exists

Without this gate, Claude Code:
- Picks random/wrong tools instead of the best ones from 1,260+ available
- Misses agent orchestration — runs single-threaded instead of parallel agents
- Ignores lessons learned — repeats past mistakes documented in system/lessons.md
- Skips post-task updates — breaks session continuity and audit trail
- Doesn't persist findings — loses cross-session knowledge

### Quick Reference: Tool Selection Cheat Sheet

| If task involves... | Use these FIRST |
|---------------------|-----------------|
| Web research | exa (search) + firecrawl (scrape) |
| Writing code with a library | context7 (latest docs) |
| GitHub operations | github MCP (not gh CLI) |
| Browser testing | playwright MCP |
| Multi-step complex work | ruflo (multi-agent swarm) |
| UI from Figma designs | figma MCP |
| n8n automations | n8n-mcp + n8n-instance |
| Persisting findings | claude-mem |
| Security/pen testing | security-1 + security-2 agents |
| Any code review | /code-review + /verify commands |