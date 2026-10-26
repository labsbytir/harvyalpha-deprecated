import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

from email_shield import extract_emails, mask_email, mask_emails_in_text
from web_app import create_app


class EmailShieldTests(unittest.TestCase):
    def test_mask_email_patterns(self):
        self.assertEqual(mask_email("john@acme.com"), "j***n@acme.com")
        self.assertEqual(mask_email("j@acme.com"), "j***@acme.com")
        self.assertEqual(mask_email("jo@acme.com"), "j***o@acme.com")
        self.assertEqual(mask_email("sarah.connor@cyberdyne.org"), "s***r@cyberdyne.org")
        self.assertEqual(mask_email("j***n@acme.com"), "j***n@acme.com")

    def test_mask_emails_in_text(self):
        raw = "Reach out to john@acme.com or support@harvy.ai for intelligence."
        expected = "Reach out to j***n@acme.com or s***t@harvy.ai for intelligence."
        self.assertEqual(mask_emails_in_text(raw), expected)

    def test_extract_emails_ignores_masked_tokens(self):
        mixed = "Real: target@corp.com, Masked: t***t@corp.com, Another: admin@harvy.io"
        found = extract_emails(mixed)
        self.assertEqual(found, ["target@corp.com", "admin@harvy.io"])


class RecordEmailRevealApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.token = "test-operator-auth-token-32-chars-long"
        self.db_path = self.root / "search-index.sqlite3"

        # Initialize mock search_index DB
        db = sqlite3.connect(self.db_path)
        db.execute("""CREATE TABLE IF NOT EXISTS indexed_files (
            path TEXT PRIMARY KEY, mtime_ns INTEGER NOT NULL, size INTEGER NOT NULL
        )""")
        db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
            doc_id UNINDEXED, file UNINDEXED, source UNINDEXED, title, url UNINDEXED, body
        )""")
        db.execute(
            "INSERT INTO search_index (doc_id, file, source, title, url, body) VALUES (?, ?, ?, ?, ?, ?)",
            ("rec-123", "data/targets.json", "dossier", "Executive Target", "https://example.com/target", "Direct inquiries to target.exec@enterprise.com regarding the docket.")
        )
        db.execute(
            "INSERT INTO search_index (doc_id, file, source, title, url, body) VALUES (?, ?, ?, ?, ?, ?)",
            ("rec-empty", "data/empty.json", "dossier", "No Email Target", "https://example.com/none", "No email mentioned anywhere in this dossier.")
        )
        db.commit()
        db.close()

        self.app = create_app({
            "TESTING": True,
            "ACCESS_TOKEN": self.token,
            "DATA_DIR": self.root,
            "ARCHIVE_DIR": self.root,
            "SEARCH_DB": self.db_path,
            "SPIDER_API_KEY": "sk-test",
            "WEBSHARE_PROXY_URL": "http://user:pass@proxy:1234",
        })
        self.client = self.app.test_client()

    def tearDown(self):
        self.app.extensions["jobs"].shutdown()
        self.tmp.cleanup()

    def test_universal_search_masks_emails_in_results(self):
        res = self.client.post("/api/universal-search", json={"query": "target.exec"})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(len(data["results"]) >= 1)
        snippet = data["results"][0]["snippet"]
        self.assertIn("t***c@enterprise.com", snippet)
        self.assertNotIn("target.exec@enterprise.com", snippet)

    def test_reveal_record_returns_unmasked_email(self):
        res = self.client.post("/api/records/rec-123/reveal", json={})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["id"], "rec-123")
        self.assertEqual(data["email"], "target.exec@enterprise.com")
        self.assertFalse(data["authenticated"])

    def test_reveal_record_not_found_or_no_email(self):
        res404 = self.client.post("/api/records/rec-missing/reveal", json={})
        self.assertEqual(res404.status_code, 404)

        res_no_email = self.client.post("/api/records/rec-empty/reveal", json={})
        self.assertEqual(res_no_email.status_code, 404)
        self.assertIn("No email on file", res_no_email.get_json()["error"])

    def test_anonymous_rate_limiting_max_3_per_hour(self):
        ip = "192.168.10.55"
        headers = {"X-Forwarded-For": ip}

        for i in range(3):
            res = self.client.post("/api/records/rec-123/reveal", json={}, headers=headers)
            self.assertEqual(res.status_code, 200)

        # 4th request must be rate limited
        res4 = self.client.post("/api/records/rec-123/reveal", json={}, headers=headers)
        self.assertEqual(res4.status_code, 429)
        self.assertTrue(res4.get_json().get("rate_limited"))

    def test_authenticated_operator_bypasses_ip_rate_limit(self):
        ip = "192.168.10.77"
        headers = {"X-Forwarded-For": ip}

        # Exhaust 3 anonymous reveals
        for _ in range(3):
            self.client.post("/api/records/rec-123/reveal", json={}, headers=headers)

        res_anon = self.client.post("/api/records/rec-123/reveal", json={}, headers=headers)
        self.assertEqual(res_anon.status_code, 429)

        # Authenticated user can continue within daily quota
        auth_headers = {"X-Forwarded-For": ip, "Authorization": f"Bearer {self.token}"}
        res_auth = self.client.post("/api/records/rec-123/reveal", json={}, headers=auth_headers)
        self.assertEqual(res_auth.status_code, 200)
        data = res_auth.get_json()
        self.assertTrue(data["authenticated"])
        self.assertEqual(data["email"], "target.exec@enterprise.com")

    def test_turnstile_challenge_enforced_when_configured(self):
        self.app.config["TURNSTILE_SECRET_KEY"] = "0x4AAAAAAtestsecret"

        # Missing turnstile token -> 403
        res = self.client.post("/api/records/rec-123/reveal", json={}, headers={"X-Forwarded-For": "10.0.0.99"})
        self.assertEqual(res.status_code, 403)
        self.assertTrue(res.get_json().get("needs_challenge"))

        # Invalid turnstile token -> 403
        res_bad = self.client.post("/api/records/rec-123/reveal", json={"turnstileToken": "bad-token"}, headers={"X-Forwarded-For": "10.0.0.99"})
        self.assertEqual(res_bad.status_code, 403)
        self.assertIn("bot check failed", res_bad.get_json().get("error", "").lower())

        # Valid turnstile token -> 200
        res_ok = self.client.post("/api/records/rec-123/reveal", json={"turnstileToken": "valid-turnstile-token"}, headers={"X-Forwarded-For": "10.0.0.99"})
        self.assertEqual(res_ok.status_code, 200)


if __name__ == "__main__":
    unittest.main()
