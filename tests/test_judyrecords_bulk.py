import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

import v1.scrape.client as spider_client
from v1.scrape import judyrecords_bulk as bulk

OSCN_HTML = """<article class="record page"><div id="oscn-content">
<h2 class="styletop"><span class="styletop">In the District Court in and for Garfield County, Oklahoma</span></h2>
<table class="caseStyle"><tr><td>STATE OF OKLAHOMA,<br> Plaintiff,<br> v.<br> ANDY ANDY,<br> Defendant.</td>
<td><strong>No. CM-2020-260<br>(Criminal Misdemeanor)</strong><br>Filed: 04/22/2020<br>Closed: 09/17/2020</td></tr></table>
<h2 class="section party">Parties</h2><p>ANDY, Defendant<br>STATE OF OKLAHOMA, Plaintiff</p>
</div></article>"""


class FakeResponse:
    def __init__(self, payload, headers=None):
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = headers or {}

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class SpiderClientTests(unittest.TestCase):
    def test_unlimited_and_ai_use_their_paths_and_proxy(self):
        with patch.object(spider_client, "urlopen", return_value=FakeResponse([{"ok": True}], {"X-Concurrency-Limit": "3"})) as mocked:
            result, headers = spider_client.unlimited("links", {"url": "https://www.judyrecords.com/"}, "key", proxy="http://proxy:8080")
        request = mocked.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.spider.cloud/unlimited/links")
        self.assertEqual(json.loads(request.data)["remote_proxy"], "http://proxy:8080")
        self.assertEqual(headers["X-Concurrency-Limit"], "3")
        self.assertEqual(result, [{"ok": True}])
        with patch.object(spider_client, "urlopen", return_value=FakeResponse([{"ok": True}])) as mocked:
            spider_client.ai("browser", {"url": "https://www.judyrecords.com/", "prompt": "search"}, "key", proxy="http://proxy:8080")
        self.assertEqual(mocked.call_args.args[0].full_url, "https://api.spider.cloud/ai/browser")


class JudyRecordsBulkHelperTests(unittest.TestCase):
    def test_canonical_record_urls_and_extraction(self):
        self.assertEqual(bulk.canonical_record_url("https://judyrecords.com/record/ABC123?x=1"), "https://www.judyrecords.com/record/abc123")
        self.assertIsNone(bulk.canonical_record_url("https://example.com/record/abc123"))
        self.assertEqual(bulk.extract_record_urls({"metadata": {"extracted_data": {"records": ["https://www.judyrecords.com/record/a1", "https://example.com/no"]}}}), ["https://www.judyrecords.com/record/a1"])

    def test_validate_page_and_build_record(self):
        ok, reason, html = bulk.validate_page([{"status": 200, "content": OSCN_HTML}])
        self.assertTrue(ok, reason)
        record = bulk.build_record(html, "https://www.judyrecords.com/record/0dkk2dkd6452", True)
        self.assertEqual(record["record_id"], "0dkk2dkd6452")
        self.assertTrue(record["complete"])
        self.assertEqual(record["provenance"]["method"], "spider_unlimited_scrape")
        bad_ok, bad_reason, _ = bulk.validate_page([{"status": 404, "error": "not found"}])
        self.assertFalse(bad_ok)
        self.assertEqual(bad_reason, "no successful Spider page")

    def test_store_record_writes_raw_and_normalized_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = bulk.build_record(OSCN_HTML, "https://www.judyrecords.com/record/abc123", False)
            raw_path, record_path, digest = bulk.store_record(tmp, "run1", {"run_id": "run1"}, OSCN_HTML, record)
            self.assertTrue(raw_path.exists())
            self.assertTrue(record_path.exists())
            self.assertEqual(digest, bulk.sha256_bytes(record_path.read_bytes()))
            self.assertEqual(json.loads(record_path.read_text())["record_id"], "abc123")


class BulkQueueTests(unittest.TestCase):
    def test_enqueue_dedupes_claims_with_leases_and_tracks_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = bulk.BulkQueue(Path(tmp) / "queue.sqlite3")
            item = bulk._job_item("run1", "https://www.judyrecords.com/record/a1", "https://www.judyrecords.com/")
            self.assertEqual(queue.enqueue_batch([item, dict(item)]), 1)
            claimed = queue.claim_batch("w1", 10, "run1")
            self.assertEqual(len(claimed), 1)
            self.assertEqual(claimed[0]["status"], "processing")
            self.assertEqual(claimed[0]["attempts"], 1)
            self.assertEqual(queue.claim_batch("w2", 10, "run1"), [])
            queue.complete(item["id"], "raw", "record", "sha")
            self.assertEqual(queue.counts("run1"), {"complete": 1})
            queue.retry_or_fail(item["id"], "boom", 2)
            self.assertEqual(queue.counts("run1")["queued"], 1)
            queue.close()

    def test_retry_or_fail_marks_failed_after_max_attempts(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = bulk.BulkQueue(Path(tmp) / "queue.sqlite3")
            item = bulk._job_item("run1", "https://www.judyrecords.com/record/b2", "https://www.judyrecords.com/")
            queue.enqueue_batch([item])
            queue.claim_batch("w1", 1, "run1")
            status = queue.retry_or_fail(item["id"], "boom", 1)
            self.assertEqual(status, "failed")
            self.assertEqual(queue.counts("run1"), {"failed": 1})
            queue.close()


class ProcessJobTests(unittest.TestCase):
    def test_process_job_stores_a_complete_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = bulk.BulkQueue(Path(tmp) / "queue.sqlite3")
            job = bulk._job_item("run1", "https://www.judyrecords.com/record/abc123", "https://www.judyrecords.com/")
            queue.enqueue_batch([job])
            with patch.object(bulk, "spider_unlimited", return_value=([{"status": 200, "content": OSCN_HTML}], {})):
                result = bulk.process_job(job, "key", "http://proxy:8080", tmp, queue)
            self.assertEqual(result["status"], "complete")
            self.assertEqual(queue.counts("run1"), {"complete": 1})
            queue.close()

    def test_process_job_retries_then_fails_invalid_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = bulk.BulkQueue(Path(tmp) / "queue.sqlite3")
            job = bulk._job_item("run1", "https://www.judyrecords.com/record/bad1", "https://www.judyrecords.com/")
            queue.enqueue_batch([job])
            claimed = queue.claim_batch("w1", 1, "run1")[0]
            with patch.object(bulk, "spider_unlimited", return_value=([{"status": 404, "error": "not found"}], {})):
                result = bulk.process_job(claimed, "key", "http://proxy:8080", tmp, queue, max_attempts=1)
            self.assertEqual(result["status"], "failed")
            self.assertEqual(queue.counts("run1"), {"failed": 1})
            queue.close()


class RunBulkTests(unittest.TestCase):
    def test_run_bulk_completes_target_with_batched_queue_and_workers(self):
        with tempfile.TemporaryDirectory() as tmp:
            urls = ["https://www.judyrecords.com/record/r1", "https://www.judyrecords.com/record/r2"]

            def fake_process(job, key, proxy, out_dir, queue, **kwargs):
                queue.complete(job["id"], "raw", "record", "sha")
                return {"status": "complete"}

            with patch.object(bulk, "ai_search_judyrecords", return_value=urls), patch.object(bulk, "process_job", side_effect=fake_process):
                code, summaries = bulk.run_bulk(
                    key="key", proxy="http://proxy:8080", out_dir=tmp, target=2, concurrency=2,
                    batch_size=1, enqueue_batch=1, queries=["breach of contract"], ai_per_second=1000,
                    progress_every=0, rounds=1, run_id="test",
                )
            self.assertEqual(code, 0)
            self.assertEqual(summaries[0]["counts"]["complete"], 2)
            self.assertTrue((Path(tmp) / "test" / "summary.json").exists())


class WebhookListenerTests(unittest.TestCase):
    def test_webhook_listener_records_spider_events(self):
        with tempfile.TemporaryDirectory() as tmp:
            queue = bulk.BulkQueue(Path(tmp) / "queue.sqlite3")
            server, token_path = bulk.start_webhook_listener(queue, "secret", "127.0.0.1:0")
            port = server.server_address[1]
            request = urllib.request.Request(
                "http://127.0.0.1:{}{}".format(port, token_path),
                data=json.dumps({"crawl_id": "c1", "mode": "complete"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(queue.event_count(), 1)
            server.shutdown()
            server.server_close()
            queue.close()


if __name__ == "__main__":
    unittest.main()
