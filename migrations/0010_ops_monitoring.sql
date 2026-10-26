-- Migration 0010: VPS and pipeline operational telemetry for the ops dashboard.

CREATE TABLE IF NOT EXISTS harvy_ops_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT NOT NULL,
    collected_at INTEGER NOT NULL,
    cpu_pct REAL,
    mem_pct REAL,
    mem_used_mb REAL,
    disk_pct REAL,
    load1 REAL,
    uptime_sec INTEGER,
    bridge_status TEXT,
    bridge_latency_ms INTEGER
);

CREATE INDEX IF NOT EXISTS harvy_ops_metrics_host_collected
    ON harvy_ops_metrics(host, collected_at DESC);

CREATE TABLE IF NOT EXISTS harvy_ops_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    host TEXT,
    source TEXT,
    level TEXT,
    message TEXT NOT NULL,
    observed_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_ops_events_observed
    ON harvy_ops_events(observed_at DESC);
