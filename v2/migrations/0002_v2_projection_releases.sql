CREATE TABLE IF NOT EXISTS platform_v2_progress_events (
    event_id TEXT PRIMARY KEY,
    connector TEXT NOT NULL,
    event_type TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    occurred_at INTEGER NOT NULL,
    item_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS platform_v2_progress_events_scope_time
    ON platform_v2_progress_events(environment_id, occurred_at DESC);

CREATE TABLE IF NOT EXISTS platform_v2_build_events (
    build_uuid TEXT NOT NULL,
    event_type TEXT NOT NULL,
    worker_name TEXT NOT NULL,
    status TEXT NOT NULL,
    branch TEXT NOT NULL DEFAULT '',
    commit_hash TEXT NOT NULL DEFAULT '',
    occurred_at INTEGER NOT NULL,
    duration_ms INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (build_uuid, event_type)
);

CREATE TABLE IF NOT EXISTS platform_v2_dataset_releases (
    dataset TEXT NOT NULL,
    release TEXT NOT NULL,
    environment_id TEXT NOT NULL,
    visibility TEXT NOT NULL CHECK (visibility IN ('public', 'private')),
    record_count INTEGER NOT NULL,
    manifest_path TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    PRIMARY KEY (environment_id, dataset, release)
);
