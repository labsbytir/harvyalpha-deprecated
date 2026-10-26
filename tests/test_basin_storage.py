import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from health.basin_storage import _batches, artifact_events, validate_ingest_url


class BasinStorageTests(unittest.TestCase):
    def test_only_accepts_https_basin_ingest_hosts(self):
        validate_ingest_url("https://stream-123.ingest.cloudflare.com")
        for url in ("http://stream.ingest.cloudflare.com", "https://example.com", "https://u:p@stream.ingest.cloudflare.com"):
            with self.assertRaises(ValueError):
                validate_ingest_url(url)

    def test_small_json_artifact_stays_structured_and_gets_stable_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.json"
            path.write_text('{"count":2}')
            first = list(artifact_events(path, "manifest.json", "job1", "profile", "example.com"))[0]
            second = list(artifact_events(path, "manifest.json", "job1", "profile", "example.com"))[0]
        self.assertEqual(first["payload"], {"count": 2})
        self.assertEqual(first["event_id"], second["event_id"])

    def test_large_json_artifact_is_chunked_without_losing_text(self):
        text = json.dumps({"content": "a-é-🙂-" * 20})
        with tempfile.TemporaryDirectory() as tmp, patch("health.basin_storage.CHUNK_BYTES", 17), patch("health.basin_storage.INLINE_JSON_BYTES", 20):
            path = Path(tmp) / "raw.json"
            path.write_text(text)
            events = list(artifact_events(path, "raw.json", "job1", "profile", "example.com"))
        self.assertGreater(len(events), 1)
        self.assertEqual("".join(e["payload"]["raw_json_chunk"] for e in events), text)
        self.assertEqual([e["chunk_index"] for e in events], list(range(len(events))))

    def test_batches_respect_byte_limit(self):
        events = [{"value": "x" * 20}, {"value": "y" * 20}, {"value": "z" * 20}]
        batches = list(_batches(events, limit=60))
        self.assertTrue(all(len(json.dumps(batch, separators=(",", ":")).encode()) <= 60 for batch in batches))


if __name__ == "__main__":
    unittest.main()
