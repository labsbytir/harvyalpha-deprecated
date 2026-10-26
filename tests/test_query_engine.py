import sqlite3
from pathlib import Path
import unittest

from ontology.contracts import make_link_record, make_observation_record, make_profile_object
from ontology.query_engine import CATALOG, compile_metric_query, get_query_catalog, get_cube_meta


class TestQueryEngine(unittest.TestCase):
    def test_cube_meta_shape(self):
        meta = get_cube_meta()
        self.assertIn("cubes", meta)
        names = {c["name"] for c in meta["cubes"]}
        self.assertIn("Observations", names)
        self.assertIn("Objects", names)
        self.assertIn("Links", names)

    def test_catalog_public_shape(self):
        cat = get_query_catalog()
        self.assertIn("metrics", cat)
        self.assertIn("dimensions", cat)
        metric_ids = {m["id"] for m in cat["metrics"]}
        self.assertIn("objects.count", metric_ids)
        self.assertIn("observations.timeseries", metric_ids)
        # Ensure raw SQL is not exposed in public catalog
        for m in cat["metrics"]:
            self.assertNotIn("sql", m)

    def test_compile_metric_disallows_arbitrary_metric(self):
        with self.assertRaises(ValueError):
            compile_metric_query("drop.database")

    def test_compile_metric_enforces_scope(self):
        sql, params = compile_metric_query("observations.count", environment_id="shared")
        self.assertIn("obs.environment_id = ?", sql)
        self.assertEqual(params, ["shared"])

        sql, params = compile_metric_query("observations.count", environment_id="tenant_x")
        self.assertIn("obs.environment_id IN (?, ?)", sql)
        self.assertEqual(params, ["shared", "tenant_x"])

    def test_compile_metric_with_filters(self):
        sql, params = compile_metric_query("observations.count", environment_id="shared", filters={"source": "instagram"})
        self.assertIn("obs.source = ?", sql)
        self.assertEqual(params, ["shared", "instagram"])

    def test_execution_against_sqlite(self):
        db = sqlite3.connect(":memory:")
        try:
            for migration in sorted(Path("migrations").glob("*.sql")):
                db.executescript(migration.read_text())

            # Seed object, observation, and link
            now = 1700000000
            db.execute(
                "INSERT INTO harvy_object_types (id, version, schema_json, description, created_at) VALUES ('profile', 1, '{}', 'test', ?)",
                (now,),
            )
            db.execute(
                "INSERT INTO harvy_link_types (id, created_at) VALUES ('authored', ?)",
                (now,),
            )

            p1 = make_profile_object("x", "nasa", now=now)
            db.execute(
                "INSERT INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (p1["id"], p1["type_id"], p1["display_name"], p1["canonical_url"], p1["attributes_json"], p1["created_at"], p1["updated_at"]),
            )

            # Shared observation
            obs1 = make_observation_record(p1["id"], "x", {"text": "hello"}, environment_id="shared", observed_at=now, now=now)
            db.execute(
                "INSERT INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (obs1["id"], obs1["object_id"], obs1["environment_id"], obs1["source"], obs1["job_id"], obs1["r2_object_key"], obs1["content_sha256"], obs1["data_json"], obs1["observed_at"], obs1["created_at"]),
            )

            # Private observation for tenant_a
            obs2 = make_observation_record(p1["id"], "x", {"text": "private_note"}, environment_id="tenant_a", observed_at=now, now=now)
            db.execute(
                "INSERT INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (obs2["id"], obs2["object_id"], obs2["environment_id"], obs2["source"], obs2["job_id"], obs2["r2_object_key"], obs2["content_sha256"], obs2["data_json"], obs2["observed_at"], obs2["created_at"]),
            )

            # Query under 'shared' scope -> should see only 1 observation
            sql, params = compile_metric_query("observations.count", environment_id="shared")
            count = db.execute(sql, params).fetchone()[0]
            self.assertEqual(count, 1)

            # Query under 'tenant_a' scope -> should see 2 observations (shared + tenant_a)
            sql, params = compile_metric_query("observations.count", environment_id="tenant_a")
            count = db.execute(sql, params).fetchone()[0]
            self.assertEqual(count, 2)

            # Query under 'tenant_b' scope -> should see only 1 observation (shared, NOT tenant_a)
            sql, params = compile_metric_query("observations.count", environment_id="tenant_b")
            count = db.execute(sql, params).fetchone()[0]
            self.assertEqual(count, 1)

        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
