-- Migration 0009: Rate Limits and Full-Text Search (FTS5) for Harvy Documents

-- 1. Atomic Rate Limits table for D1 SQLite
CREATE TABLE IF NOT EXISTS harvy_rate_limits (
    key TEXT PRIMARY KEY,
    count INTEGER NOT NULL DEFAULT 1,
    expires_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_rate_limits_expires ON harvy_rate_limits(expires_at);

-- 2. FTS5 Virtual Table for full-text search over harvy_search_documents
CREATE VIRTUAL TABLE IF NOT EXISTS harvy_search_documents_fts USING fts5(
    id UNINDEXED,
    title,
    snippet,
    body,
    source,
    tokenize='porter unicode61'
);

-- 3. Triggers to keep FTS5 synchronized with harvy_search_documents
CREATE TRIGGER IF NOT EXISTS harvy_search_documents_ai AFTER INSERT ON harvy_search_documents BEGIN
    INSERT INTO harvy_search_documents_fts(rowid, id, title, snippet, body, source)
    VALUES (new.rowid, new.id, new.title, new.snippet, new.body, new.source);
END;

CREATE TRIGGER IF NOT EXISTS harvy_search_documents_ad AFTER DELETE ON harvy_search_documents BEGIN
    DELETE FROM harvy_search_documents_fts WHERE rowid = old.rowid;
END;

CREATE TRIGGER IF NOT EXISTS harvy_search_documents_au AFTER UPDATE ON harvy_search_documents BEGIN
    UPDATE harvy_search_documents_fts
    SET id = new.id, title = new.title, snippet = new.snippet, body = new.body, source = new.source
    WHERE rowid = old.rowid;
END;
