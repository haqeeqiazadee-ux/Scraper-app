-- =============================================================================
-- AI Scraping Platform — Initial Schema for Supabase
-- =============================================================================
-- Run this in the Supabase SQL Editor:
--   Dashboard → SQL Editor → New query → Paste & Run
-- =============================================================================

-- ─── Policies ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS policies (
    id              VARCHAR(36) PRIMARY KEY,
    tenant_id       VARCHAR(255) NOT NULL,
    name            VARCHAR(255) NOT NULL,
    target_domains  JSONB NOT NULL DEFAULT '[]',
    preferred_lane  VARCHAR(50) NOT NULL DEFAULT 'auto',
    extraction_rules JSONB NOT NULL DEFAULT '{}',
    rate_limit      JSONB NOT NULL DEFAULT '{}',
    proxy_policy    JSONB NOT NULL DEFAULT '{}',
    session_policy  JSONB NOT NULL DEFAULT '{}',
    retry_policy    JSONB NOT NULL DEFAULT '{}',
    timeout_ms      INTEGER NOT NULL DEFAULT 30000,
    robots_compliance BOOLEAN NOT NULL DEFAULT true,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_policies_tenant_id ON policies (tenant_id);

-- ─── Sessions ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sessions (
    id                  VARCHAR(36) PRIMARY KEY,
    tenant_id           VARCHAR(255) NOT NULL,
    domain              VARCHAR(255) NOT NULL,
    session_type        VARCHAR(50) NOT NULL DEFAULT 'http',
    cookies             JSONB NOT NULL DEFAULT '{}',
    headers             JSONB NOT NULL DEFAULT '{}',
    proxy_id            VARCHAR(36),
    browser_profile_id  VARCHAR(255),
    status              VARCHAR(50) NOT NULL DEFAULT 'active',
    request_count       INTEGER NOT NULL DEFAULT 0,
    success_count       INTEGER NOT NULL DEFAULT 0,
    failure_count       INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_sessions_tenant_id ON sessions (tenant_id);
CREATE INDEX IF NOT EXISTS ix_sessions_domain ON sessions (domain);

-- ─── Tasks ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
    id              VARCHAR(36) PRIMARY KEY,
    tenant_id       VARCHAR(255) NOT NULL,
    url             TEXT NOT NULL,
    task_type       VARCHAR(50) NOT NULL DEFAULT 'scrape',
    policy_id       VARCHAR(36),
    priority        INTEGER NOT NULL DEFAULT 5,
    schedule        VARCHAR(255),
    callback_url    TEXT,
    metadata_json   JSONB NOT NULL DEFAULT '{}',
    status          VARCHAR(50) NOT NULL DEFAULT 'pending',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);
CREATE INDEX IF NOT EXISTS ix_tasks_tenant_id ON tasks (tenant_id);
CREATE INDEX IF NOT EXISTS ix_tasks_tenant_status ON tasks (tenant_id, status);
CREATE INDEX IF NOT EXISTS ix_tasks_tenant_created ON tasks (tenant_id, created_at);

-- ─── Runs ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS runs (
    id              VARCHAR(36) PRIMARY KEY,
    task_id         VARCHAR(36) NOT NULL REFERENCES tasks(id),
    tenant_id       VARCHAR(255) NOT NULL,
    lane            VARCHAR(50) NOT NULL,
    connector       VARCHAR(100) NOT NULL,
    session_id      VARCHAR(36),
    proxy_used      VARCHAR(255),
    attempt         INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(50) NOT NULL DEFAULT 'running',
    status_code     INTEGER,
    error           TEXT,
    duration_ms     INTEGER NOT NULL DEFAULT 0,
    bytes_downloaded INTEGER NOT NULL DEFAULT 0,
    ai_tokens_used  INTEGER NOT NULL DEFAULT 0,
    started_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at    TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_runs_task_id ON runs (task_id);
CREATE INDEX IF NOT EXISTS ix_runs_tenant_id ON runs (tenant_id);

-- ─── Results ─────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS results (
    id                      VARCHAR(36) PRIMARY KEY,
    task_id                 VARCHAR(36) NOT NULL REFERENCES tasks(id),
    run_id                  VARCHAR(36) NOT NULL REFERENCES runs(id),
    tenant_id               VARCHAR(255) NOT NULL,
    url                     TEXT NOT NULL,
    extracted_data          JSONB NOT NULL DEFAULT '{}',
    item_count              INTEGER NOT NULL DEFAULT 0,
    schema_version          VARCHAR(20) NOT NULL DEFAULT '1.0',
    confidence              FLOAT NOT NULL DEFAULT 0.0,
    extraction_method       VARCHAR(50) NOT NULL DEFAULT 'deterministic',
    normalization_applied   BOOLEAN NOT NULL DEFAULT false,
    dedup_applied           BOOLEAN NOT NULL DEFAULT false,
    created_at              TIMESTAMP NOT NULL DEFAULT NOW(),
    artifacts_json          JSONB NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS ix_results_task_id ON results (task_id);
CREATE INDEX IF NOT EXISTS ix_results_tenant_id ON results (tenant_id);

-- ─── Artifacts ───────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS artifacts (
    id              VARCHAR(36) PRIMARY KEY,
    result_id       VARCHAR(36) NOT NULL REFERENCES results(id),
    tenant_id       VARCHAR(255) NOT NULL,
    artifact_type   VARCHAR(50) NOT NULL,
    storage_path    TEXT NOT NULL,
    content_type    VARCHAR(100) NOT NULL,
    size_bytes      INTEGER NOT NULL DEFAULT 0,
    checksum        VARCHAR(255) NOT NULL,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_artifacts_result_id ON artifacts (result_id);
CREATE INDEX IF NOT EXISTS ix_artifacts_tenant_id ON artifacts (tenant_id);

-- ─── Alembic version tracking ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);
INSERT INTO alembic_version (version_num) VALUES ('590780df3897')
ON CONFLICT (version_num) DO NOTHING;
