from pathlib import Path
import sqlite3
import unittest

from scripts.backfill_ontology import backfill_database


class TestBackfill(unittest.TestCase):
    def test_backfill_idempotent(self):
        db = sqlite3.connect(":memory:")
        try:
            for migration in sorted(Path("migrations").glob("*.sql")):
                db.executescript(migration.read_text())

            # Insert sample search documents
            now = 1700000000
            db.execute("INSERT INTO harvy_jobs (id, kind, status, url, created_at, updated_at) VALUES ('j1', 'profile', 'finished', 'https://instagram.com/natgeo', ?, ?)", (now, now))
            db.execute(
                "INSERT INTO harvy_search_documents (id, job_id, title, snippet, body, source, url, object_key, created_at) "
                "VALUES ('d1', 'j1', 'National Geographic', 'Photos and stories', 'Full bio text', 'social', 'https://instagram.com/natgeo', 'jobs/j1/raw/profile.json', ?)",
                (now,),
            )
            db.execute(
                "INSERT INTO harvy_search_documents (id, job_id, title, snippet, body, source, url, object_key, created_at) "
                "VALUES ('d2', 'j1', 'Post by @natgeo', 'Wild animals in Africa', 'Wild animals in Africa text', 'posts', 'https://instagram.com/p/123', 'jobs/j1/raw/profile.json', ?)",
                (now,),
            )

            counts1 = backfill_database(db)
            self.assertEqual(counts1["objects"], 2)
            self.assertEqual(counts1["observations"], 2)

            # Rerun backfill - should be idempotent
            counts2 = backfill_database(db)
            self.assertEqual(counts2["objects"], 2)

            total_objs = db.execute("SELECT count(*) FROM harvy_objects").fetchone()[0]
            self.assertEqual(total_objs, 2)

            total_obs = db.execute("SELECT count(*) FROM harvy_observations").fetchone()[0]
            self.assertEqual(total_obs, 2)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
