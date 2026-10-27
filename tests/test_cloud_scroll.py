import json
import unittest

from v1.scrape.facebook_scroll import diagnostic, options


class CloudScrollTests(unittest.TestCase):
    def test_native_scroll_and_wait_steps_are_requested(self):
        steps = options("https://example.com/profile")["automation_scripts"]["https://example.com/profile"]
        self.assertEqual(sum("ScrollY" in s for s in steps), 18)
        self.assertEqual(sum("Wait" in s for s in steps), 19)
        self.assertTrue(any("harvy-scroll-diagnostic" in s.get("Evaluate", "") for s in steps))

    def test_200_without_scroll_proof_is_not_verified(self):
        self.assertFalse(diagnostic({"status": 200, "content": "<body>Profile</body>"})["verified"])

    def test_positions_must_change(self):
        data = {"harvy_scroll": {"samples": [{"y": 0}, {"y": 900}], "postLinks": ["https://example.com/post"]}}
        content = '<script id="harvy-scroll-diagnostic" type="application/json">' + json.dumps(data) + '</script>'
        result = diagnostic({"content": content})
        self.assertTrue(result["verified"])
        self.assertEqual(result["postLinks"], ["https://example.com/post"])
        data["harvy_scroll"]["samples"] = [{"y": 0}, {"y": 0}]
        self.assertFalse(diagnostic({"json_data": data})["verified"])


if __name__ == "__main__":
    unittest.main()
