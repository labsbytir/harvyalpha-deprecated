import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "start_judyrecords_bulk.py"
spec = importlib.util.spec_from_file_location("start_judyrecords_bulk", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class StartJudyRecordsBulkTests(unittest.TestCase):
    def test_build_run_validates_and_normalizes(self):
        run = module.build_run(
            [" https://www.judyrecords.com/search/ ", "https://judyrecords.com/"],
            mode="crawl", limit=10, environment_id="shared",
        )
        self.assertEqual(run["connector"], "judyrecords")
        self.assertEqual(run["input"]["seeds"], ["https://www.judyrecords.com/search/", "https://judyrecords.com/"])
        self.assertEqual(run["input"]["mode"], "crawl")
        self.assertEqual(run["input"]["limit"], 10)
        self.assertTrue(run["idempotency_key"].startswith("judy-"))
        with self.assertRaises(ValueError):
            module.build_run(["https://example.com/"])
        with self.assertRaises(ValueError):
            module.build_run(["https://user:pass@judyrecords.com/"])
        with self.assertRaises(ValueError):
            module.build_run(["https://www.judyrecords.com/"], limit=101)
        with self.assertRaises(ValueError):
            module.build_run(["https://www.judyrecords.com/"], environment_id="bad env")

    def test_post_run_sends_bearer_and_json(self):
        run = module.build_run(["https://www.judyrecords.com/"])

        class FakeResponse:
            status = 202

            def read(self, *_args):
                return json.dumps({"run_id": "r1"}).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        with patch("urllib.request.urlopen", return_value=FakeResponse()) as mocked:
            status, data = module.post_run("https://v2.example/", "secret-token", run)
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://v2.example/v2/runs")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(json.loads(request.data.decode("utf-8"))["connector"], "judyrecords")
        self.assertEqual(status, 202)
        self.assertEqual(data["run_id"], "r1")

    def test_post_run_requires_https_and_token(self):
        run = module.build_run(["https://www.judyrecords.com/"])
        with self.assertRaises(ValueError):
            module.post_run("http://v2.example/", "secret-token", run)
        with self.assertRaises(ValueError):
            module.post_run("https://v2.example/", "bad token", run)


if __name__ == "__main__":
    unittest.main()
