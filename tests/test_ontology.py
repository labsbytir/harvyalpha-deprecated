import json
import unittest

from v2.ontology.contracts import (
    DEFAULT_ENVIRONMENT,
    build_scope_filter,
    make_link_id,
    make_link_record,
    make_object_urn,
    make_observation_id,
    make_observation_record,
    make_profile_object,
    normalize_identifier,
)


class TestOntologyContracts(unittest.TestCase):
    def test_normalize_identifier(self):
        self.assertEqual(normalize_identifier("@NatGeo "), "natgeo")
        self.assertEqual(normalize_identifier("user_123"), "user_123")

    def test_make_object_urn(self):
        urn = make_object_urn("profile", "x", "@natgeo")
        self.assertEqual(urn, "urn:harvy:profile:x:natgeo")

    def test_deterministic_observation_id(self):
        obs1 = make_observation_id("x", "urn:harvy:profile:x:natgeo", "hash123", 1700000000)
        obs2 = make_observation_id("x", "urn:harvy:profile:x:natgeo", "hash123", 1700000000)
        self.assertEqual(obs1, obs2)
        self.assertTrue(obs1.startswith("obs_"))

    def test_deterministic_link_id(self):
        lnk1 = make_link_id("urn:a", "authored", "urn:b", "shared")
        lnk2 = make_link_id("urn:a", "authored", "urn:b", "shared")
        self.assertEqual(lnk1, lnk2)

        lnk_tenant = make_link_id("urn:a", "authored", "urn:b", "env_tenant1")
        self.assertNotEqual(lnk1, lnk_tenant)

    def test_build_scope_filter(self):
        clause, params = build_scope_filter(None, "o.environment_id")
        self.assertEqual(clause, "o.environment_id = ?")
        self.assertEqual(params, ["shared"])

        clause, params = build_scope_filter("shared", "o.environment_id")
        self.assertEqual(clause, "o.environment_id = ?")
        self.assertEqual(params, ["shared"])

        clause, params = build_scope_filter("org_acme", "o.environment_id")
        self.assertEqual(clause, "o.environment_id IN (?, ?)")
        self.assertEqual(params, ["shared", "org_acme"])

    def test_make_profile_object(self):
        obj = make_profile_object(
            platform="instagram",
            handle="@nasa",
            display_name="NASA",
            attributes={"followers": 1000},
            now=1700000000,
        )
        self.assertEqual(obj["id"], "urn:harvy:profile:instagram:nasa")
        self.assertEqual(obj["type_id"], "profile")
        self.assertEqual(obj["display_name"], "NASA")
        attrs = json.loads(obj["attributes_json"])
        self.assertEqual(attrs["followers"], 1000)

    def test_make_observation_and_link_record(self):
        obs = make_observation_record(
            object_id="urn:harvy:profile:x:nasa",
            source="x",
            payload={"bio": "Explore the universe"},
            r2_object_key="profiles/x/nasa.json",
            job_id="job_123",
            environment_id="shared",
            observed_at=1700000000,
            now=1700000001,
        )
        self.assertEqual(obs["environment_id"], "shared")
        self.assertEqual(obs["job_id"], "job_123")
        self.assertEqual(obs["r2_object_key"], "profiles/x/nasa.json")

        link = make_link_record(
            source_id="urn:harvy:profile:x:nasa",
            target_id="urn:harvy:post:x:9999",
            link_type="authored",
            evidence_observation_id=obs["id"],
            now=1700000002,
        )
        self.assertEqual(link["source_id"], "urn:harvy:profile:x:nasa")
        self.assertEqual(link["target_id"], "urn:harvy:post:x:9999")
        self.assertEqual(link["evidence_observation_id"], obs["id"])

        from v2.ontology.contracts import make_basin_observation_event, make_basin_link_event
        obs_event = make_basin_observation_event(obs)
        self.assertEqual(obs_event["kind"], "ontology_observation")
        self.assertEqual(obs_event["target"], "urn:harvy:profile:x:nasa")
        self.assertEqual(obs_event["payload"]["observation_id"], obs["id"])

        link_event = make_basin_link_event(link)
        self.assertEqual(link_event["kind"], "ontology_link")
        self.assertEqual(link_event["source"], "urn:harvy:profile:x:nasa")
        self.assertEqual(link_event["target"], "urn:harvy:post:x:9999")
        self.assertEqual(link_event["payload"]["link_id"], link["id"])

    def test_backfill_search_documents(self):
        import sqlite3
        from pathlib import Path
        from v2.scripts.backfill_ontology import backfill_search_documents

        db = sqlite3.connect(":memory:")
        try:
            for migration in sorted(Path("migrations").glob("*.sql")):
                db.executescript(migration.read_text())

            # Insert sample search document
            db.execute(
                """
                INSERT INTO harvy_search_documents
                (id, job_id, title, snippet, body, source, url, object_key, created_at)
                VALUES ('doc_1', 'job_1', '@nasa official', 'Space agency', 'Full body text', 'x', 'https://x.com/nasa', 'jobs/1/file.json', 1700000000)
                """
            )
            stats = backfill_search_documents(db)
            self.assertEqual(stats["processed"], 1)
            self.assertEqual(stats["objects"], 1)
            self.assertEqual(stats["observations"], 1)

            # Check created object
            row = db.execute("SELECT id, type_id, display_name FROM harvy_objects WHERE id = 'urn:harvy:profile:x:nasa'").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[1], "profile")

            # Check created observation
            obs_row = db.execute("SELECT object_id, source, r2_object_key FROM harvy_observations WHERE object_id = 'urn:harvy:profile:x:nasa'").fetchone()
            self.assertIsNotNone(obs_row)
            self.assertEqual(obs_row[2], "jobs/1/file.json")
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
