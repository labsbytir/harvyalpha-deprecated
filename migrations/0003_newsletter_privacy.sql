ALTER TABLE harvy_users ADD COLUMN privacy_accepted_at INTEGER;

CREATE TABLE IF NOT EXISTS harvy_newsletter_consents (
    buttondown_subscriber_id TEXT PRIMARY KEY,
    policy_version TEXT NOT NULL,
    consented_at INTEGER NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_newsletter_consents_status
    ON harvy_newsletter_consents(status, consented_at);
