import json
from pathlib import Path
import unittest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "v1"


class V1ContractsTests(unittest.TestCase):
    def test_facebook_fixtures_conform_to_contract(self):
        manifest_path = FIXTURES_DIR / "facebook" / "manifest.json"
        self.assertTrue(manifest_path.exists())
        manifest = json.loads(manifest_path.read_text())
        self.assertIn("target", manifest)
        self.assertIn("sections", manifest)
        self.assertFalse(manifest["complete"])
        self.assertIn("completeness_note", manifest)

        profile_path = FIXTURES_DIR / "facebook" / "profile-details.json"
        self.assertTrue(profile_path.exists())
        profile = json.loads(profile_path.read_text())
        self.assertEqual(profile["platform"], "facebook")
        self.assertIn("url", profile)
        self.assertIn("links", profile)
        self.assertIsInstance(profile["links"], list)

        post_path = FIXTURES_DIR / "facebook" / "posts" / "post-1.json"
        self.assertTrue(post_path.exists())
        post = json.loads(post_path.read_text())
        self.assertEqual(post["platform"], "facebook")
        self.assertIn("url", post)
        self.assertIn("text", post)
        self.assertTrue(post.get("ownership_verified"))

    def test_social_and_network_fixtures_conform_to_contract(self):
        ig_post = json.loads((FIXTURES_DIR / "social" / "instagram_post.json").read_text())
        self.assertEqual(ig_post["platform"], "instagram")
        self.assertIn("shortcode", ig_post)

        threads_post = json.loads((FIXTURES_DIR / "social" / "threads_post.json").read_text())
        self.assertEqual(threads_post["platform"], "threads")

        x_tweet = json.loads((FIXTURES_DIR / "social" / "x_tweet.json").read_text())
        self.assertEqual(x_tweet["platform"], "x")

        network = json.loads((FIXTURES_DIR / "social" / "network.json").read_text())
        self.assertIn("nodes", network)
        self.assertIn("edges", network)
        for edge in network["edges"]:
            self.assertEqual(edge["relation"], "bio_links_to")
            self.assertIn("source", edge)
            self.assertIn("target", edge)

    def test_username_fixtures_conform_to_contract(self):
        username_res = json.loads((FIXTURES_DIR / "username" / "results.json").read_text())
        self.assertIn("username", username_res)
        self.assertIn("checked_count", username_res)
        self.assertIn("matches", username_res)
        for match in username_res["matches"]:
            self.assertIn("name", match)
            self.assertIn("category", match)
            self.assertIn("url", match)
            self.assertEqual(match["status"], "found")

    def test_legal_and_map_research_fixtures_conform_to_contract(self):
        research_res = json.loads((FIXTURES_DIR / "legal" / "research_results.json").read_text())
        sources = {r["source"]: r for r in research_res}
        self.assertIn("courtlistener", sources)
        self.assertIn("case_law", sources)
        self.assertIn("judyrecords", sources)
        self.assertIn("docket_alarm", sources)
        self.assertIn("arrests_org", sources)
        self.assertIn("court_record", sources)
        self.assertIn("google_scholar", sources)

        self.assertEqual(sources["arrests_org"]["status"], "page_captured")
        self.assertEqual(sources["court_record"]["status"], "link_only")
        self.assertEqual(sources["google_scholar"]["status"], "link_only")

        map_res = json.loads((FIXTURES_DIR / "map" / "map_results.json").read_text())
        map_sources = {r["source"]: r for r in map_res}
        self.assertEqual(map_sources["mapillary"]["status"], "ok")
        self.assertEqual(map_sources["zoom_earth"]["status"], "link_only")
        self.assertEqual(map_sources["opensfm"]["status"], "tool_reference")


if __name__ == "__main__":
    unittest.main()