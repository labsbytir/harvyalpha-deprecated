CREATE TABLE IF NOT EXISTS harvy_workflow_runs (
    id TEXT PRIMARY KEY,
    workflow_instance_id TEXT NOT NULL UNIQUE,
    task TEXT NOT NULL,
    version INTEGER NOT NULL,
    requested_by TEXT NOT NULL,
    environment_id TEXT NOT NULL DEFAULT 'shared',
    idempotency_key TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'queued',
    result_json TEXT,
    error TEXT,
    updated_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_workflow_runs_owner_created
    ON harvy_workflow_runs(requested_by, environment_id, created_at DESC);

CREATE UNIQUE INDEX IF NOT EXISTS harvy_workflow_runs_idempotency
    ON harvy_workflow_runs(requested_by, environment_id, task, idempotency_key);

CREATE INDEX IF NOT EXISTS harvy_workflow_runs_task_created
    ON harvy_workflow_runs(task, created_at DESC);
