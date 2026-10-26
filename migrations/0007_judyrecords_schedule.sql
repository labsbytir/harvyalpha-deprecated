CREATE TABLE IF NOT EXISTS harvy_judyrecords_schedule (
    id TEXT PRIMARY KEY,
    lease_until INTEGER NOT NULL DEFAULT 0,
    last_success_at INTEGER NOT NULL DEFAULT 0,
    last_run_key TEXT
);

INSERT OR IGNORE INTO harvy_judyrecords_schedule (id, lease_until, last_success_at) VALUES ('default', 0, 0);

INSERT OR IGNORE INTO harvy_object_types (id, version, schema_json, description, created_at)
VALUES ('legal_case', 1, '{}', 'Public legal case', unixepoch());

INSERT OR IGNORE INTO harvy_object_types (id, version, schema_json, description, created_at)
VALUES ('legal_party', 1, '{}', 'Party named in a public legal case', unixepoch());

INSERT OR IGNORE INTO harvy_link_types (id, description, created_at)
VALUES ('party_to_case', 'A named party associated with a legal case', unixepoch());
