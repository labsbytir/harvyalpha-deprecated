import unittest

from v1.scrape.facebook import payload, post_records, profile_details, summarize


class ScrapeProfileTests(unittest.TestCase):
    def test_anonymous_custom_proxy_request(self):
        body = payload("https://www.facebook.com/test/", "http://example.com:1234")
        self.assertEqual(body["remote_proxy"], "http://example.com:1234")
        self.assertFalse(body["session"])
        self.assertFalse(body["return_cookies"])
        self.assertNotIn("cookies", body)
        steps = body["automation_scripts"]["https://www.facebook.com/test/"]
        self.assertEqual(sum("ScrollY" in s for s in steps), 18)

    def test_own_post_extracted_without_pictures_or_recommended_posts(self):
        story = {"__typename": "Story", "post_id": "1",
                 "permalink_url": "https://www.facebook.com/test/posts/1",
                 "message": {"text": "Public post"},
                 "actors": [{"name": "Test", "profile_picture": {"uri": "image"}}],
                 "comment": {"id": "c1", "body": {"text": "Reply"},
                             "author": {"name": "Reader", "profile_picture": {"uri": "image"}}}}
        recommendation = dict(story, post_id="2", permalink_url="https://www.facebook.com/other/posts/2")
        page = {"url": "https://www.facebook.com/test/", "json_data": [story, recommendation]}
        posts = list(post_records(page, page["url"]))
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["text_fragments"], ["Public post"])
        self.assertEqual(posts[0]["comments"][0]["text"], "Reply")
        self.assertNotIn("profile_picture", posts[0]["authors"][0])
        self.assertNotIn("profile_picture", posts[0]["comments"][0]["author"])

    def test_logged_out_surface_not_treated_as_complete_feed(self):
        page = {"json_data": [{"__typename": "ProfileLoggedOutTabsWithJoinCTA"}]}
        result = summarize(page, "profile")
        self.assertTrue(result["logged_out_profile_tabs"])
        self.assertEqual(result["story_records"], 0)

    def test_numeric_permalink_needs_matching_profile_author(self):
        url = "https://www.facebook.com/test/"
        page = {"url": url, "json_data": [
            {"id": "123", "name": "Test", "url": url},
            {"__typename": "Story", "post_id": "4", "permalink_url": "https://www.facebook.com/123/posts/4",
             "actors": [{"id": "123"}]},
            {"__typename": "Story", "post_id": "5", "permalink_url": "https://www.facebook.com/other/posts/5",
             "actors": [{"id": "999"}]},
        ]}
        self.assertEqual([p["id"] for p in post_records(page, url)], ["4"])

    def test_profile_fields_keep_evidence_but_not_image_fields(self):
        url = "https://www.facebook.com/test/"
        page = {"url": url, "json_data": [
            {"id": "123", "name": "Test", "url": url, "profile_picture": {"uri": "image"}},
            {"__typename": "DetailedProfileFieldRenderer", "field": {"title": {"text": "Public field"}}},
        ]}
        result = profile_details([page], url)
        self.assertEqual(result["identity"], {"id": "123", "name": "Test"})
        self.assertEqual(result["fields"][0]["source"], url)
        self.assertEqual(result["fields"][0]["text"], "Public field")

    def test_reel_permalink_requires_matching_video_owner(self):
        url = "https://www.facebook.com/test/"
        story = {"__typename": "Story", "post_id": "4", "message": {"text": "Reel caption"},
                 "video": {"__typename": "Video", "id": "456", "owner": {"id": "123"},
                           "permalink_url": "https://www.facebook.com/reel/456/"}}
        page = {"url": url, "json_data": [{"id": "123", "url": url}, story]}
        records = list(post_records(page, url))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["url"], "https://www.facebook.com/reel/456/")
        self.assertEqual(records[0]["authors"][0]["id"], "123")
        story["video"]["owner"]["id"] = "999"
        self.assertEqual(list(post_records(page, url)), [])


if __name__ == "__main__":
    unittest.main()
