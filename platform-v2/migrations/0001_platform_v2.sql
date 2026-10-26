CREATE TABLE IF NOT EXISTS platform_v2_runs (
    id TEXT PRIMARY KEY,
    connector TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    input_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'running', 'dispatched', 'complete', 'failed', 'cancelled')),
    error TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (connector, environment_id, idempotency_key)
);

CREATE TABLE IF NOT EXISTS platform_v2_work_items (
    id TEXT PRIMARY KEY,
    connector TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    run_id TEXT NOT NULL REFERENCES platform_v2_runs(id),
    url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('record', 'document', 'profile', 'api_page')),
    status TEXT NOT NULL DEFAULT 'queued'
        CHECK (status IN ('queued', 'processing', 'complete', 'failed')),
    attempts INTEGER NOT NULL DEFAULT 0,
    lease_until INTEGER NOT NULL DEFAULT 0,
    artifact_path TEXT,
    last_error TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    UNIQUE (run_id, url)
);

CREATE INDEX IF NOT EXISTS platform_v2_runs_environment_created
    ON platform_v2_runs(environment_id, created_at DESC);

CREATE INDEX IF NOT EXISTS platform_v2_items_state_lease
    ON platform_v2_work_items(status, lease_until);
