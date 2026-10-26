from pathlib import Path
import tempfile
import unittest

from scrape.jobs import job_command, redact, research_job_command, username_job_command, validate_credentials


class JobCommandTests(unittest.TestCase):
    def test_facebook_command_has_limits_and_unique_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            command, output = job_command("https://www.facebook.com/example/", tmp, 50, 3)
            self.assertIn("--max-posts", command)
            self.assertEqual(command[-1], "3")
            self.assertEqual(output.parent, Path(tmp).resolve())
            self.assertNotEqual(output, job_command("https://www.facebook.com/example/", tmp, 50, 3)[1])

    def test_social_command_uses_cloud_adapter(self):
        command, _ = job_command("https://youtube.com/@alice", "/tmp/test-output", 100, 0)
        self.assertIn("--url", command)
        self.assertIn("scrape.profiles", command)
        self.assertEqual(command[-1], "1")
        self.assertNotIn("SPIDER_API_KEY", " ".join(command))

    def test_username_scan_command_is_python_and_validates_categories(self):
        command, output = username_job_command("sample_name", ["social", "gaming"], "/tmp/test-output")
        self.assertIn("scrape.username", command)
        self.assertIn("--category", command)
        self.assertIn("username-sample_name-", output.name)
        with self.assertRaises(ValueError):
            username_job_command("sample", ["unknown"], "/tmp/test-output")

    def test_research_job_validates_arrests_fields_and_map_coordinates(self):
        command, output, payload = research_job_command({
            "mode": "legal", "query": "Miranda v Arizona", "sources": ["courtlistener"],
        }, "/tmp/research-output")
        self.assertIn("scrape.research", command)
        self.assertIn("research-legal-", output.name)
        self.assertEqual(payload["query"], "Miranda v Arizona")
        with self.assertRaises(ValueError):
            research_job_command({"mode": "legal", "query": "Smith", "sources": ["arrests_org"]}, "/tmp")
        with self.assertRaises(ValueError):
            research_job_command({"mode": "map", "latitude": 91, "longitude": 0}, "/tmp")

    def test_invalid_targets_and_limits_rejected(self):
        for url in ("http://127.0.0.1/", "file:///etc/passwd", "https://user:pass@x.com/alice", "https://facebook.com/alice/posts/1"):
            with self.assertRaises(ValueError):
                job_command(url, "/tmp/test-output", 100, 1)
        for posts, linked in ((0, 1), (1, -1), (True, 1)):
            with self.assertRaises(ValueError):
                job_command("https://x.com/alice", "/tmp/test-output", posts, linked)

    def test_secrets_redacted_and_proxy_checked(self):
        proxy = "http://user:secret%40pass@proxy.example:1234"
        line = redact("key=private-key proxy=" + proxy + " password=secret@pass", "private-key", proxy)
        self.assertNotIn("private-key", line)
        self.assertNotIn("secret@pass", line)
        self.assertNotIn(proxy, line)
        validate_credentials("key", proxy)
        with self.assertRaises(ValueError):
            validate_credentials("key", "not-a-proxy")


if __name__ == "__main__":
    unittest.main()
