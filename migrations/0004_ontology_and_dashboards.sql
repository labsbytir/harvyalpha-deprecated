CREATE TABLE IF NOT EXISTS harvy_object_types (
    id TEXT PRIMARY KEY,
    version INTEGER NOT NULL DEFAULT 1,
    schema_json TEXT NOT NULL,
    description TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS harvy_objects (
    id TEXT PRIMARY KEY,
    type_id TEXT NOT NULL REFERENCES harvy_object_types(id),
    display_name TEXT NOT NULL,
    canonical_url TEXT,
    attributes_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_objects_type_id ON harvy_objects(type_id);
CREATE INDEX IF NOT EXISTS harvy_objects_updated_at ON harvy_objects(updated_at);

CREATE TABLE IF NOT EXISTS harvy_observations (
    id TEXT PRIMARY KEY,
    object_id TEXT NOT NULL REFERENCES harvy_objects(id),
    environment_id TEXT NOT NULL DEFAULT 'shared',
    source TEXT NOT NULL,
    job_id TEXT,
    r2_object_key TEXT,
    content_sha256 TEXT NOT NULL,
    data_json TEXT NOT NULL DEFAULT '{}',
    observed_at INTEGER NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_observations_object_env ON harvy_observations(object_id, environment_id);
CREATE INDEX IF NOT EXISTS harvy_observations_env_observed ON harvy_observations(environment_id, observed_at);
CREATE INDEX IF NOT EXISTS harvy_observations_job_id ON harvy_observations(job_id);

CREATE TABLE IF NOT EXISTS harvy_link_types (
    id TEXT PRIMARY KEY,
    inverse_id TEXT,
    description TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS harvy_links (
    id TEXT PRIMARY KEY,
    environment_id TEXT NOT NULL DEFAULT 'shared',
    source_id TEXT NOT NULL REFERENCES harvy_objects(id),
    target_id TEXT NOT NULL REFERENCES harvy_objects(id),
    link_type TEXT NOT NULL REFERENCES harvy_link_types(id),
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_observation_id TEXT REFERENCES harvy_observations(id),
    properties_json TEXT NOT NULL DEFAULT '{}',
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_links_source_env ON harvy_links(source_id, environment_id);
CREATE INDEX IF NOT EXISTS harvy_links_target_env ON harvy_links(target_id, environment_id);
CREATE INDEX IF NOT EXISTS harvy_links_env_type ON harvy_links(environment_id, link_type);

CREATE TABLE IF NOT EXISTS harvy_dashboards (
    id TEXT PRIMARY KEY,
    environment_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    layout_json TEXT NOT NULL DEFAULT '{}',
    queries_json TEXT NOT NULL DEFAULT '[]',
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_dashboards_env_owner ON harvy_dashboards(environment_id, owner_id);
