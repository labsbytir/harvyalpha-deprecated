import unittest
from v1.scrape.telegram import parse_channel_posts


class TestTelegramHistoryScraper(unittest.TestCase):
    def test_parse_channel_posts(self):
        sample_html = """
        <div class="tgme_widget_message" data-post="testchan/42">
          <time datetime="2026-03-01T12:00:00Z"></time>
          <div class="tgme_widget_message_text">Hello world! Check <a href="https://example.com">link</a></div>
          <span class="tgme_widget_message_views">1.5K</span>
        </div>
        </div>
        </div>
        """
        posts = parse_channel_posts(sample_html)
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]["post_id"], 42)
        self.assertEqual(posts[0]["datetime"], "2026-03-01T12:00:00Z")
        self.assertIn("Hello world!", posts[0]["text"])
        self.assertEqual(posts[0]["views"], "1.5K")
        self.assertEqual(posts[0]["links"], ["https://example.com"])


if __name__ == "__main__":
    unittest.main()
