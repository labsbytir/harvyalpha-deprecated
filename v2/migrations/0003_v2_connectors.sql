CREATE TABLE IF NOT EXISTS platform_v2_connectors (
    id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
    capability_verified INTEGER NOT NULL DEFAULT 0 CHECK (capability_verified IN (0, 1)),
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
