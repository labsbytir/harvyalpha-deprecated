CREATE TABLE IF NOT EXISTS harvy_jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    url TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    error TEXT
);

CREATE INDEX IF NOT EXISTS harvy_jobs_updated_at ON harvy_jobs(updated_at);

CREATE TABLE IF NOT EXISTS harvy_search_documents (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    title TEXT NOT NULL,
    snippet TEXT NOT NULL,
    body TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    object_key TEXT NOT NULL,
    created_at INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS harvy_search_documents_job_id ON harvy_search_documents(job_id);
CREATE INDEX IF NOT EXISTS harvy_search_documents_created_at ON harvy_search_documents(created_at);
