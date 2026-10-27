import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from v1.scrape.username import classify, make_checks, save_report


class UsernameScanTests(unittest.TestCase):
    def test_classifies_only_matching_evidence(self):
        site = {"e_code": 200, "e_string": "profile-card", "m_code": 404, "m_string": "not found"}
        self.assertEqual(classify(site, {"status": 200, "content": "profile-card"}), "candidate_match")
        self.assertEqual(classify(site, {"status": 404, "content": "not found"}), "not_found")
        self.assertEqual(classify(site, {"status": 200, "content": "challenge"}), "inconclusive")

    def test_empty_detection_string_does_not_create_false_not_found(self):
        site = {"e_code": 200, "e_string": "profile", "m_code": 200, "m_string": ""}
        self.assertEqual(classify(site, {"status": 200, "content": "other"}), "inconclusive")

    def test_filters_invalid_post_and_non_https_definitions(self):
        data = {"sites": [
            {"name": "valid", "cat": "social", "uri_check": "https://example.com/{account}", "e_code": 200},
            {"name": "invalid", "cat": "social", "uri_check": "https://example.com/{account}", "valid": False},
            {"name": "post", "cat": "social", "uri_check": "https://example.com", "post_body": "x"},
            {"name": "http", "cat": "social", "uri_check": "http://example.com/{account}"},
        ]}
        with patch("v1.scrape.username.validate_public_destination"):
            checks, skipped = make_checks("sample_name", {"social"}, data)
        self.assertEqual([site["name"] for site, _ in checks], ["valid"])
        self.assertEqual({row["reason"] for row in skipped}, {"unsupported_method", "unsafe_or_non_https_url"})

    def test_rejects_url_injection_in_username(self):
        with self.assertRaises(ValueError):
            make_checks("name/path", {"social"}, {"sites": []})

    def test_progress_report_is_written_atomically_with_partial_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            checks = [({}, "https://example.com/user")]
            save_report(output, "sample", {"social"}, checks, [], [], False)
            report = json.loads((output / "username-report.json").read_text())
            self.assertFalse(report["complete"])
            self.assertEqual(report["requested"], 1)
            self.assertEqual(report["checked"], 0)
            self.assertFalse((output / "username-report.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
