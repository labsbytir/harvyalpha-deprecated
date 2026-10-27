import unittest
from unittest.mock import patch

from v1.scrape.client import ENDPOINT
from v1.scrape.x import fetch_handle, payload


class XSpiderScraperTests(unittest.TestCase):
    def test_recipe_uses_plain_http_options_on_unlimited_endpoint(self):
        request = payload("https://x.com/NASA", "http://proxy.invalid:8080")
        self.assertTrue(ENDPOINT.endswith("/unlimited/scrape"))
        self.assertEqual(request["return_format"], "raw")
        self.assertTrue(request["return_json_data"])
        self.assertNotIn("request", request)  # Spider's X capture uses plain HTTP, not browser rendering.
        self.assertEqual(request["remote_proxy"], "http://proxy.invalid:8080")

    def test_extracts_only_target_authored_posts_and_public_engagement(self):
        tweet = {
            "__typename": "Tweet",
            "rest_id": "123",
            "legacy": {"full_text": "Public X post", "favorite_count": 8, "retweet_count": 2},
            "core": {"user_results": {"result": {"legacy": {"screen_name": "NASA"}}}},
        }
        page = {"status": 200, "url": "https://x.com/NASA", "content": "", "json_data": [tweet], "metadata": {}}
        with patch("v1.scrape.x.validate_public_destination"), patch("v1.scrape.x.spider_request", return_value=[page]):
            account, raw = fetch_handle("NASA", "test-key", "http://proxy.invalid:8080", 10)
        self.assertEqual(len(account["posts"]), 1)
        self.assertEqual(account["posts"][0]["like_count"], 8)
        self.assertEqual(account["posts"][0]["repost_count"], 2)
        self.assertEqual(raw, [page])


if __name__ == "__main__":
    unittest.main()
