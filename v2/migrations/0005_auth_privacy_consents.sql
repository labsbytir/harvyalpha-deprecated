CREATE TABLE IF NOT EXISTS harvy_auth_privacy_consents (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    accepted_at INTEGER NOT NULL,
    policy_version TEXT NOT NULL,
    source TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_auth_privacy_consents_user_id
    ON harvy_auth_privacy_consents(user_id, accepted_at);
