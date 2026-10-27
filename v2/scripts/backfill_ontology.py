"""Backfill ontology tables from existing harvy_search_documents."""
from __future__ import annotations

import argparse
from pathlib import Path
import sqlite3
import time
from urllib.parse import urlparse

from v2.ontology.contracts import (
    DEFAULT_ENVIRONMENT,
    make_object_urn,
    make_observation_record,
    make_profile_object,
)


def backfill_search_documents(db: sqlite3.Connection) -> dict[str, int]:
    """Backfill existing search documents into canonical objects and observations."""
    now = int(time.time())
    cursor = db.execute("SELECT id, job_id, title, snippet, body, source, url, object_key, created_at FROM harvy_search_documents")
    rows = cursor.fetchall()

    counts = {"processed": 0, "objects": 0, "observations": 0, "links": 0}

    for row in rows:
        doc_id, job_id, title, snippet, body, source, url, object_key, created_at = row
        created_at = created_at or now
        counts["processed"] += 1

        # Determine platform/source
        platform = (source or "web").lower()
        if url:
            host = urlparse(url).netloc.lower()
            if "instagram" in host:
                platform = "instagram"
            elif "threads" in host:
                platform = "threads"
            elif "x.com" in host or "twitter" in host:
                platform = "x"
            elif "reddit" in host:
                platform = "reddit"
            elif "facebook" in host:
                platform = "facebook"

        if source in ("social", "x", "instagram", "threads", "reddit", "facebook") or not source == "posts":
            # Profile object
            handle = (url.rstrip("/").split("/")[-1] if url else "unknown").lstrip("@")
            obj = make_profile_object(platform, handle, display_name=title, canonical_url=url, attributes={"snippet": snippet}, now=created_at)
            db.execute(
                "INSERT OR IGNORE INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (obj["id"], obj["type_id"], obj["display_name"], obj["canonical_url"], obj["attributes_json"], obj["created_at"], obj["updated_at"]),
            )
            counts["objects"] += 1

            obs = make_observation_record(
                obj["id"],
                platform,
                {"title": title, "snippet": snippet},
                r2_object_key=object_key,
                job_id=job_id,
                environment_id=DEFAULT_ENVIRONMENT,
                observed_at=created_at,
                now=now,
            )
            db.execute(
                "INSERT OR IGNORE INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (obs["id"], obs["object_id"], obs["environment_id"], obs["source"], obs["job_id"], obs["r2_object_key"], obs["content_sha256"], obs["data_json"], obs["observed_at"], obs["created_at"]),
            )
            counts["observations"] += 1

        elif source == "posts":
            # Post object
            post_urn = make_object_urn("post", platform, doc_id)
            db.execute(
                "INSERT OR IGNORE INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (post_urn, "post", title, url, "{}", created_at, created_at),
            )
            counts["objects"] += 1

            obs = make_observation_record(
                post_urn,
                platform,
                {"snippet": snippet, "body": body[:500]},
                r2_object_key=object_key,
                job_id=job_id,
                environment_id=DEFAULT_ENVIRONMENT,
                observed_at=created_at,
                now=now,
            )
            db.execute(
                "INSERT OR IGNORE INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (obs["id"], obs["object_id"], obs["environment_id"], obs["source"], obs["job_id"], obs["r2_object_key"], obs["content_sha256"], obs["data_json"], obs["observed_at"], obs["created_at"]),
            )
            counts["observations"] += 1

    db.commit()
    return counts


backfill_database = backfill_search_documents


def main():
    parser = argparse.ArgumentParser(description="Backfill Harvy ontology tables from search documents")
    parser.add_argument("database", type=Path, help="Path to SQLite database file")
    args = parser.parse_args()

    if not args.database.exists():
        raise SystemExit(f"Database not found: {args.database}")

    conn = sqlite3.connect(args.database)
    try:
        counts = backfill_search_documents(conn)
        print(f"Backfill complete: {counts['objects']} objects, {counts['observations']} observations, {counts['links']} links.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
