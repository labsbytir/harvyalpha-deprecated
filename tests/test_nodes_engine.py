import sqlite3
from pathlib import Path
import unittest

from v2.ontology.contracts import make_link_record, make_observation_record, make_profile_object
from v2.ontology.nodes_engine import get_object_provenance, query_scoped_graph


class TestNodesEngine(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        for migration in sorted(Path("migrations").glob("*.sql")):
            self.db.executescript(migration.read_text())

        now = 1700000000
        self.db.execute("INSERT INTO harvy_object_types (id, schema_json, created_at) VALUES ('profile', '{}', ?)", (now,))
        self.db.execute("INSERT INTO harvy_object_types (id, schema_json, created_at) VALUES ('post', '{}', ?)", (now,))
        self.db.execute("INSERT INTO harvy_link_types (id, created_at) VALUES ('authored', ?)", (now,))

        p1 = make_profile_object("x", "alice", now=now)
        p2 = make_profile_object("x", "bob", now=now)
        post = {"id": "urn:harvy:post:x:1", "type_id": "post", "display_name": "Post 1", "canonical_url": "https://x.com/alice/1", "attributes_json": "{}", "created_at": now, "updated_at": now}

        for obj in (p1, p2, post):
            self.db.execute(
                "INSERT INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (obj["id"], obj["type_id"], obj["display_name"], obj["canonical_url"], obj["attributes_json"], obj["created_at"], obj["updated_at"]),
            )

        obs_shared = make_observation_record(p1["id"], "x", {"text": "pub"}, r2_object_key="profiles/x/alice.json", environment_id="shared", observed_at=now, now=now)
        obs_private = make_observation_record(p1["id"], "x", {"text": "priv"}, r2_object_key="profiles/x/alice_priv.json", environment_id="tenant_x", observed_at=now, now=now)

        for obs in (obs_shared, obs_private):
            self.db.execute(
                "INSERT INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (obs["id"], obs["object_id"], obs["environment_id"], obs["source"], obs["job_id"], obs["r2_object_key"], obs["content_sha256"], obs["data_json"], obs["observed_at"], obs["created_at"]),
            )

        # Shared link: alice -> post
        lnk_shared = make_link_record(p1["id"], post["id"], "authored", evidence_observation_id=obs_shared["id"], environment_id="shared", now=now)
        # Private link: alice -> bob (only visible in tenant_x)
        lnk_private = make_link_record(p1["id"], p2["id"], "authored", evidence_observation_id=obs_private["id"], environment_id="tenant_x", now=now)

        for lnk in (lnk_shared, lnk_private):
            self.db.execute(
                "INSERT INTO harvy_links (id, environment_id, source_id, target_id, link_type, confidence, evidence_observation_id, properties_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (lnk["id"], lnk["environment_id"], lnk["source_id"], lnk["target_id"], lnk["link_type"], lnk["confidence"], lnk["evidence_observation_id"], lnk["properties_json"], lnk["created_at"]),
            )

    def tearDown(self):
        self.db.close()

    def test_query_scoped_graph_shared_only(self):
        graph = query_scoped_graph(self.db, environment_id="shared")
        self.assertEqual(graph["total_links"], 1)
        self.assertEqual(graph["links"][0]["target"], "urn:harvy:post:x:1")

    def test_query_scoped_graph_tenant_isolation(self):
        graph_tenant = query_scoped_graph(self.db, environment_id="tenant_x")
        self.assertEqual(graph_tenant["total_links"], 2)

        graph_other = query_scoped_graph(self.db, environment_id="tenant_other")
        self.assertEqual(graph_other["total_links"], 1)

    def test_object_provenance(self):
        prov = get_object_provenance(self.db, "urn:harvy:profile:x:alice", environment_id="shared")
        self.assertIsNotNone(prov)
        self.assertEqual(len(prov["observations"]), 1)
        self.assertEqual(prov["observations"][0]["r2_object_key"], "profiles/x/alice.json")

        prov_tenant = get_object_provenance(self.db, "urn:harvy:profile:x:alice", environment_id="tenant_x")
        self.assertEqual(len(prov_tenant["observations"]), 2)


if __name__ == "__main__":
    unittest.main()
