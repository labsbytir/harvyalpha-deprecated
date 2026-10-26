import unittest
from unittest.mock import patch

from scrape.client import ENDPOINT
from scrape.profiles import adapter_for, profile_link
from scrape.protocol import network_for_url
from scrape.truthsocial import fetch_handle, payload, resolve_account_id


class TruthSocialScraperTests(unittest.TestCase):
    def test_payload_uses_raw_unlimited_endpoint(self):
        req = payload("https://truthsocial.com/@alice", "http://proxy.invalid:8080")
        self.assertTrue(ENDPOINT.endswith("/unlimited/scrape"))
        self.assertEqual(req["return_format"], "raw")
        self.assertTrue(req["return_json_data"])
        self.assertEqual(req["remote_proxy"], "http://proxy.invalid:8080")

    def test_protocol_and_adapter_resolution(self):
        self.assertEqual(network_for_url("https://truthsocial.com/@alice"), "truthsocial")
        adapter = adapter_for("truthsocial")
        self.assertIsNotNone(adapter)
        self.assertEqual(adapter.__name__, "scrape.truthsocial")

    def test_resolve_account_id_from_json(self):
        page = {"status": 200, "content": '{"id": "10823456", "username": "alice"}'}
        with patch("scrape.truthsocial.spider_request", return_value=[page]):
            account_id = resolve_account_id("alice", "test-key", "http://proxy.invalid:8080")
        self.assertEqual(account_id, "10823456")

    def test_fetch_handle_extracts_posts_and_metrics(self):
        status = {
            "id": "11293847291048",
            "created_at": "2026-08-01T14:22:00.000Z",
            "url": "https://truthsocial.com/@alice/posts/11293847291048",
            "content": "<p>Public announcement</p>",
            "account": {
                "id": "10823456",
                "username": "alice",
                "url": "https://truthsocial.com/@alice",
            },
            "favourites_count": 85400,
            "reblogs_count": 18400,
            "replies_count": 12200,
        }
        lookup_page = {"status": 200, "content": '{"id": "10823456", "username": "alice"}'}
        statuses_page = {"status": 200, "content": "", "json_data": [status]}

        def mock_request(body, key, proxy=None):
            if "lookup" in body["url"]:
                return [lookup_page]
            return [statuses_page]

        with patch("scrape.truthsocial.validate_public_destination"), patch("scrape.truthsocial.spider_request", side_effect=mock_request):
            record, pages = fetch_handle("alice", "test-key", "http://proxy.invalid:8080", max_posts=10)

        self.assertEqual(record["platform"], "truthsocial")
        self.assertEqual(record["account_id"], "10823456")
        self.assertEqual(len(record["posts"]), 1)
        post = record["posts"][0]
        self.assertEqual(post["id"], "11293847291048")
        self.assertEqual(post["like_count"], 85400)
        self.assertEqual(post["repost_count"], 18400)
        self.assertEqual(post["reply_count"], 12200)
        self.assertTrue(post["ownership_verified"])


if __name__ == "__main__":
    unittest.main()
