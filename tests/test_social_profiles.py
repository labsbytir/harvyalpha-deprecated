import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest.mock import patch

from scrape.profiles import RECIPES, extract_social, fetch, profile_link, scrape_linked_profiles, validate_public_destination


class SocialProfileTests(unittest.TestCase):
    def test_instagram_adapter_uses_shared_transport_without_facebook_scripts(self):
        with patch("scrape.profiles.spider_request", return_value=[{"status": 200}]) as request:
            self.assertEqual(fetch("https://www.instagram.com/alice/", "secret", "http://proxy"), [{"status": 200}])
        payload = request.call_args.args[0]
        self.assertEqual(payload["url"], "https://www.instagram.com/alice/")
        self.assertEqual(payload["request"], "browser")
        self.assertNotIn("automation_scripts", payload)
        self.assertEqual(request.call_args.args[2], "http://proxy")

    def test_all_requested_recipes_registered(self):
        self.assertEqual(sum(len(v) for v in RECIPES.values()), 21)
        examples = {
            "x": "https://twitter.com/alice", "bluesky": "https://bsky.app/profile/alice.bsky.social",
            "instagram": "https://instagram.com/alice", "sssinstagram": "https://sssinstagram.com/",
            "threads": "https://threads.net/@alice", "linkedin": "https://linkedin.com/in/alice",
            "quora": "https://quora.com/profile/Alice", "mastodon": "https://mastodon.social/@alice",
            "discord": "https://discord.gg/example", "tiktok": "https://tiktok.com/@alice",
            "substack": "https://alice.substack.com/", "medium": "https://medium.com/@alice",
            "twitch": "https://twitch.tv/alice",
            "youtube": "https://youtube.com/@alice", "truthsocial": "https://truthsocial.com/@alice",
            "blogspot": "https://alice.blogspot.com/", "steam": "https://steamcommunity.com/id/alice",
            "github-blog": "https://github.blog/author/alice/", "europefreechat": "https://europefreechat.com/",
        }
        for platform, url in examples.items():
            with self.subTest(platform=platform):
                self.assertEqual(profile_link(url)["platform"], platform)
        self.assertEqual(profile_link("https://threads.com/@alice"), profile_link("https://threads.net/@alice"))
        self.assertEqual(profile_link("https://twitter.com/ALICE"), profile_link("https://x.com/alice"))
        self.assertNotEqual(profile_link("https://discord.gg/ABC"), profile_link("https://discord.gg/abc"))

    def test_added_sites_have_correct_identity_kinds(self):
        self.assertEqual(profile_link("https://bsky.social/")["kind"], "service")
        self.assertEqual(profile_link("https://alice.blogspot.com/")["kind"], "publication")
        self.assertEqual(profile_link("https://github.blog/")["kind"], "publication")
        self.assertEqual(profile_link("https://europefreechat.com/")["kind"], "community")
        self.assertEqual(profile_link("https://steamcommunity.com/groups/alice")["kind"], "community")
        self.assertEqual(profile_link("https://steamcommunity.com/profiles/76561198000000000")["kind"], "profile")
        self.assertEqual(profile_link("https://youtube.com/@Alice/about")["url"], "https://youtube.com/@alice")
        self.assertEqual(profile_link("https://youtube.com/channel/UCAbC/videos")["url"], "https://youtube.com/channel/UCAbC")
        for url in ("https://youtube.com/watch?v=video", "https://steamcommunity.com/sharedfiles/filedetails/?id=1",
                    "https://alice.blogspot.com/2026/01/article.html", "https://europefreechat.com/private/room",
                    "https://bsky.social/xrpc/private", "https://github.blog/developer-skills/article/",
                    "https://alice.blogspot.com.evil.example/", "https://x.com/alice%2Fstatus",
                    "https://x.com/alice%3Fnext=private"):
            self.assertIsNone(profile_link(url), url)

    def test_youtube_video_author_and_truth_social_status(self):
        account = profile_link("https://youtube.com/@alice")
        video = {"videoId": "video123", "title": {"runs": [{"text": "Public video"}]},
                 "ownerText": {"runs": [{"navigationEndpoint": {"browseEndpoint": {"canonicalBaseUrl": "/@Alice"}}}]}}
        page = {"json_data": [{"videoRenderer": video}]}
        result = extract_social(page, account)
        self.assertEqual(result["posts"][0]["title"], "Public video")
        self.assertEqual(result["posts"][0]["url"], "https://www.youtube.com/watch?v=video123")
        video["ownerText"]["runs"][0]["navigationEndpoint"]["browseEndpoint"]["canonicalBaseUrl"] = "/@other"
        self.assertEqual(extract_social(page, account)["posts"], [])
        account = profile_link("https://truthsocial.com/@alice")
        status = {"id": "123", "account": {"url": account["url"]}, "content": "<p>Public truth</p>"}
        self.assertEqual(extract_social({"json_data": [status]}, account)["posts"][0]["platform"], "truthsocial")

    def test_posts_and_lookalike_domains_not_enqueued_as_profiles(self):
        for url in ("https://instagram.com/p/123/", "https://x.com/alice/status/1", "https://x.com.evil.example/alice",
                    "http://127.0.0.1/@alice", "javascript:alert(1)", "https://user:pass@x.com/alice",
                    "https://discord.com/channels/private/server"):
            self.assertIsNone(profile_link(url))
        self.assertEqual(profile_link("https://sssinstagram.com/")["kind"], "utility")
        self.assertEqual(profile_link("https://discord.gg/test")["kind"], "community-invite")

    def test_facebook_redirect_unwrapped(self):
        result = profile_link("https://l.facebook.com/l.php?u=https%3A%2F%2Finstagram.com%2Falice&h=token")
        self.assertEqual(result["url"], "https://instagram.com/alice")

    def test_bio_links_not_post_links_or_recommendation_links(self):
        account = profile_link("https://instagram.com/alice")
        page = {"url": account["url"], "content": '<section class="bio"><a href="https://threads.net/@alice">Threads</a></section><article><a href="https://x.com/stranger">Post link</a></article>',
                "json_data": [{"username": "alice", "external_url": "https://medium.com/@alice",
                               "posts": [{"expanded_url": "https://twitch.tv/stranger"}]}]}
        result = extract_social(page, account)
        self.assertEqual({p["platform"] for p in result["bio_links"]}, {"threads", "medium"})

    def test_x_and_bluesky_posts_need_matching_author(self):
        x = profile_link("https://x.com/alice")
        tweet = {"__typename": "Tweet", "rest_id": "1", "views": {"count": "900"},
                 "legacy": {"full_text": "Public post", "favorite_count": 12, "retweet_count": 3, "reply_count": 4},
                 "core": {"user_results": {"result": {"legacy": {"screen_name": "alice"}}}}}
        result = extract_social({"url": x["url"], "json_data": [tweet]}, x)
        self.assertEqual(result["posts"][0]["url"], "https://x.com/alice/status/1")
        self.assertEqual(result["posts"][0]["like_count"], 12)
        self.assertEqual(result["posts"][0]["repost_count"], 3)
        self.assertEqual(result["posts"][0]["view_count"], "900")
        tweet["core"]["user_results"]["result"]["legacy"]["screen_name"] = "other"
        self.assertEqual(extract_social({"json_data": [tweet]}, x)["posts"], [])
        bsky = profile_link("https://bsky.app/profile/alice.bsky.social")
        post = {"uri": "at://did:plc:abc/app.bsky.feed.post/123", "author": {"handle": "alice.bsky.social"},
                "record": {"$type": "app.bsky.feed.post", "text": "Hello"}}
        self.assertEqual(len(extract_social({"json_data": [post]}, bsky)["posts"]), 1)

    def test_private_destination_rejected(self):
        with patch("scrape.profiles.socket.getaddrinfo", return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", 443))]):
            with self.assertRaises(ValueError):
                validate_public_destination("https://mastodon.social/@alice")

    def test_instagram_threads_and_tiktok_structured_posts(self):
        for platform, url in [("instagram", "https://instagram.com/alice"), ("threads", "https://threads.com/@alice")]:
            account = profile_link(url)
            node = {"id": "1", "shortcode": "code", "taken_at_timestamp": 123,
                    "owner": {"username": "alice"}, "caption": {"text": "Caption"}}
            result = extract_social({"json_data": [node]}, account)
            self.assertEqual(result["posts"][0]["text"], "Caption")
            self.assertEqual(result["posts"][0]["platform"], platform)
        account = profile_link("https://tiktok.com/@alice")
        node = {"id": "2", "desc": "Video caption", "author": {"uniqueId": "alice"}}
        result = extract_social({"json_data": [node]}, account)
        self.assertEqual(result["posts"][0]["url"], "https://www.tiktok.com/@alice/video/2")

    def test_mastodon_owner_and_json_ld_authorship(self):
        account = profile_link("https://mastodon.social/@alice")
        node = {"id": "1", "content": "<p>Public status</p>", "account": {"url": account["url"]},
                "url": account["url"] + "/1"}
        self.assertEqual(extract_social({"json_data": [node]}, account)["posts"][0]["text_html"], "<p>Public status</p>")
        account = profile_link("https://medium.com/@alice")
        data = {"@type": ["Article", "BlogPosting"], "url": "https://medium.com/story", "articleBody": "Article",
                "author": {"url": "https://medium.com/@other"}}
        page = {"content": '<script type="application/ld+json">' + json.dumps(data) + '</script>'}
        post = extract_social(page, account)["posts"][0]
        self.assertFalse(post["ownership_verified"])
        self.assertEqual(post["text"], "Article")

    def test_recursive_discovery_deduplicates_and_writes_separate_post_json(self):
        def fake_fetch(url, key, proxy):
            records = []
            if "x.com" in url:
                content = '<a rel="me" href="https://threads.com/@alice">Threads</a>'
                records = [{"__typename": "Tweet", "rest_id": "1", "legacy": {"full_text": "Public post"},
                            "core": {"user_results": {"result": {"legacy": {"screen_name": "alice"}}}}}]
            else:
                content = '<a rel="me" href="https://twitter.com/alice">X</a>'
            return [{"url": url, "status": 200, "content": content, "json_data": records}]
        with tempfile.TemporaryDirectory() as tmp, patch("scrape.profiles.fetch", side_effect=fake_fetch) as request, patch("scrape.profiles.validate_public_destination"):
            result = scrape_linked_profiles("https://facebook.com/alice", ["https://twitter.com/alice", "https://x.com/alice"], Path(tmp), "key", "proxy", 10)
            self.assertEqual(request.call_count, 2)
            self.assertEqual(len(result["accounts"]), 2)
            self.assertTrue((Path(tmp) / "network.json").exists())
            files = list(Path(tmp).glob("x/*/posts/*.json"))
            self.assertEqual(len(files), 1)
            self.assertEqual(json.loads(files[0].read_text())["text"], "Public post")
            self.assertFalse(result["complete"])

    def test_login_page_is_not_reported_as_empty_profile(self):
        account = profile_link("https://instagram.com/alice")
        result = extract_social({"content": "<body>Log into Instagram</body>"}, account)
        self.assertTrue(result["login_wall_detected"])
        self.assertEqual(result["availability"], "login_wall")
        self.assertFalse(result["complete"])
        result = extract_social({"content": "<body>Instagram</body>"}, account)
        self.assertEqual(result["availability"], "unverified_shell")

    def test_publication_bio_links_followed_but_chat_room_links_not_followed(self):
        def fake_fetch(url, key, proxy):
            link = "https://youtube.com/@alice" if "blogspot" in url else "https://x.com/community-user"
            return [{"url": url, "status": 200, "content": f'<a rel="me" href="{link}">Link</a>'}]
        with tempfile.TemporaryDirectory() as tmp, patch("scrape.profiles.fetch", side_effect=fake_fetch), patch("scrape.profiles.validate_public_destination"):
            result = scrape_linked_profiles("https://facebook.com/alice", ["https://europefreechat.com", "https://alice.blogspot.com"], Path(tmp), "key", "proxy", 3)
            urls = {a["url"] for a in result["accounts"]}
            self.assertIn("https://youtube.com/@alice", urls)
            self.assertNotIn("https://x.com/community-user", urls)
            graph = json.loads((Path(tmp) / "network.json").read_text())
            kinds = {n["id"]: n["type"] for n in graph["nodes"]}
            self.assertEqual(kinds["https://europefreechat.com"], "community")
            self.assertEqual(kinds["https://alice.blogspot.com"], "publication")

    def test_facebook_post_link_is_not_a_bio_account_link(self):
        from scrape.facebook import profile_details
        url = "https://www.facebook.com/test/"
        page = {"url": url, "json_data": [
            {"__typename": "Story", "link": {"__typename": "ExternalUrl", "external_url": "https://x.com/stranger"}},
            {"__typename": "ContextItemDefaultRenderer", "context_item": {"title": {"ranges": [
                {"entity": {"__typename": "ExternalUrl", "external_url": "https://x.com/alice"}}]}}},
        ]}
        self.assertEqual(profile_details([page], url)["external_links"], ["https://x.com/alice"])


if __name__ == "__main__":
    unittest.main()
