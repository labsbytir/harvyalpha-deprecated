CREATE TABLE IF NOT EXISTS harvy_users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    email TEXT,
    is_anonymous INTEGER NOT NULL DEFAULT 0,
    role TEXT NOT NULL DEFAULT 'user',
    two_factor_enabled INTEGER NOT NULL DEFAULT 0,
    two_factor_secret TEXT,
    two_factor_backup_codes TEXT,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS harvy_passkeys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES harvy_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    credential_id TEXT UNIQUE NOT NULL,
    public_key TEXT NOT NULL,
    counter INTEGER NOT NULL DEFAULT 0,
    transports TEXT,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS harvy_api_keys (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES harvy_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    key_prefix TEXT NOT NULL,
    key_hash TEXT UNIQUE NOT NULL,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 60,
    expires_at INTEGER,
    last_used_at INTEGER,
    created_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS harvy_sessions (
    token TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES harvy_users(id) ON DELETE CASCADE,
    expires_at INTEGER NOT NULL,
    ip_address TEXT,
    user_agent TEXT,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_users_username ON harvy_users(username);
CREATE INDEX IF NOT EXISTS harvy_passkeys_user_id ON harvy_passkeys(user_id);
CREATE INDEX IF NOT EXISTS harvy_api_keys_user_id ON harvy_api_keys(user_id);
CREATE INDEX IF NOT EXISTS harvy_api_keys_key_hash ON harvy_api_keys(key_hash);
CREATE INDEX IF NOT EXISTS harvy_sessions_user_id ON harvy_sessions(user_id);
