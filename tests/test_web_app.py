from collections import deque
import io
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import Mock, patch
import zipfile

from web_app import create_app


class WebsiteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.token = "test-access-token-with-at-least-32-characters"
        self.app = create_app({"TESTING": True, "SPIDER_API_KEY": "sk-private-test-key",
                               "WEBSHARE_PROXY_URL": "http://user:proxy-password@proxy.example:1234",
                               "ACCESS_TOKEN": self.token, "DATA_DIR": self.root,
                               "ARCHIVE_DIR": self.root, "SEARCH_DB": self.root / "search-index.sqlite3"})
        self.client = self.app.test_client()
        self.manager = self.app.extensions["jobs"]

    def tearDown(self):
        self.manager.shutdown()
        self.tmp.cleanup()

    def headers(self, job_token=None):
        headers = {"Authorization": "Bearer " + self.token}
        if job_token:
            headers["X-Job-Token"] = job_token
        return headers

    def seed_job(self, running=False):
        output = self.root / "job-output"
        output.mkdir(exist_ok=True)
        (output / "manifest.json").write_text('{"complete":false}')
        (output / "posts").mkdir(exist_ok=True)
        (output / "posts" / "1.json").write_text('{"text":"Public post"}')
        process = Mock()
        process.poll.return_value = None if running else 0
        job = {"id": "job-a", "token": "job-owner-secret", "output": output,
               "process": process, "status": "running" if running else "finished",
               "kind": "profile", "url": "https://example.com/profile", "started": time.time(),
               "logs": deque(["Profile fetched\n"]), "returncode": 0, "basin_status": "not_configured"}
        self.manager.items[job["id"]] = job
        return job

    def test_home_has_no_provider_secrets_and_is_not_cached(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Follow the public trail", response.data)
        self.assertNotIn(b"sk-private-test-key", response.data)
        self.assertNotIn(b"proxy-password", response.data)
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertIn("frame-ancestors 'none'", response.headers["Content-Security-Policy"])

    def test_platform_route_renders_app(self):
        for route in ("/platform", "/platform/"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Target Specification", response.data)
            self.assertIn(b"username-form", response.data)
            self.assertNotIn(b"sk-private-test-key", response.data)
            self.assertNotIn(b"proxy-password", response.data)

    def test_privacy_page_is_served_from_template(self):
        response = self.client.get("/privacy/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"id=\"policy-doc\"", response.data)
        self.assertIn(b"/static/policy.js", response.data)

    def test_legal_pages_serve_vault_policies(self):
        for route, heading, doc in (
            ("/terms/", b"Terms of Service", b"/static/terms.md"),
            ("/acceptable-use/", b"Acceptable Use Policy", b"/static/acceptable-use.md"),
        ):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn(heading, response.data)
            self.assertIn(doc, response.data)

    def test_home_footer_lists_address_and_legal_links(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"2 Route 37 W STE F #1084", response.data)
        self.assertIn(b"Toms River, NJ 08753", response.data)
        self.assertIn(b'href="/privacy/"', response.data)
        self.assertIn(b'href="/terms/"', response.data)
        self.assertIn(b'href="/acceptable-use/"', response.data)

    def test_research_page_and_source_job_validation(self):
        response = self.client.get("/research/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Public Case Records", response.data)
        self.assertNotIn(b"JudyRecords", response.data)
        self.assertNotIn(b"Spider", response.data)
        self.assertNotIn(b"Webshare", response.data)
        self.assertNotIn(b"Mapillary", response.data)
        self.assertNotIn(b"Docket Alarm", response.data)
        self.assertNotIn(b"Basin", response.data)
        with patch("web_app.subprocess.Popen") as launch:
            bad_consent = self.client.post("/api/research-jobs", headers=self.headers(), json={
                "mode": "legal", "query": "Miranda", "sources": ["courtlistener"], "consent": False,
            })
            bad_source = self.client.post("/api/research-jobs", headers=self.headers(), json={
                "mode": "legal", "query": "Miranda", "sources": ["unknown"], "consent": True,
            })
        self.assertEqual(bad_consent.status_code, 400)
        self.assertEqual(bad_source.status_code, 400)
        launch.assert_not_called()

    def test_example_dossiers_use_shared_template_and_json_data(self):
        for relative in ("natgeo", "leaders/trump"):
            folder = self.root / relative
            folder.mkdir(parents=True)
            (folder / "report.json").write_text(json.dumps({"target": {"name": relative}, "posts": []}))

        response = self.client.get("/report/natgeo")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/static/dossier.js", response.data)
        self.assertIn(b"/api/reports/natgeo.json", response.data)
        self.assertEqual(self.client.get("/api/reports/natgeo.json").json["target"]["name"], "natgeo")

        response = self.client.get("/report/leaders/trump")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"/api/reports/leaders/trump.json", response.data)
        self.assertEqual(self.client.get("/api/reports/leaders/trump.json").json["target"]["name"], "leaders/trump")

    def test_universal_search_indexes_all_saved_artifacts_and_requires_workspace_token(self):
        (self.root / "old-report.json").write_text(json.dumps({"caseName": "Miranda v Arizona", "summary": "Searchable record"}))
        response = self.client.post("/api/universal-search", headers=self.headers(), json={"query": "Miranda"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Miranda", response.json["results"][0]["title"] + response.json["results"][0]["snippet"])
        page = self.client.get("/search/")
        self.assertEqual(page.status_code, 200)
        self.assertIn(b"HARVY SEARCH", page.data)

    def test_map_route_renders(self):
        for route in ("/map", "/map/"):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            self.assertIn(b"Geospatial Intelligence Map", response.data)

    def test_api_requires_workspace_token(self):
        response = self.client.post("/api/jobs", json={"url": "https://x.com/alice", "consent": True})
        self.assertEqual(response.status_code, 401)

    def test_job_requires_both_tokens(self):
        self.seed_job()
        self.assertEqual(self.client.get("/api/jobs/job-a", headers=self.headers("wrong-job-token")).status_code, 404)
        response = self.client.get("/api/jobs/job-a", headers=self.headers("job-owner-secret"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json["post_files"], 1)
        self.assertNotIn("token", response.json)
        self.assertFalse(response.json["complete"])

    def test_validation_prevents_worker_launch(self):
        with patch("web_app.subprocess.Popen") as launch:
            for body in ({"consent": False}, {"consent": True, "url": "file:///etc/passwd"},
                         {"consent": True, "url": "https://x.com/alice", "max_posts": 99999},
                         {"consent": True, "url": "https://x.com/alice", "max_linked": True}):
                self.assertEqual(self.client.post("/api/jobs", json=body, headers=self.headers()).status_code, 400)
            launch.assert_not_called()

    def test_worker_secrets_only_in_environment(self):
        process = Mock()
        process.poll.return_value = 0
        with patch("web_app.subprocess.Popen", return_value=process) as launch, patch("web_app.threading.Thread"):
            response = self.client.post("/api/jobs", headers=self.headers(), json={"url": "https://x.com/alice", "consent": True})
        self.assertEqual(response.status_code, 202)
        command = launch.call_args.args[0]
        env = launch.call_args.kwargs["env"]
        self.assertNotIn("sk-private-test-key", " ".join(command))
        self.assertNotIn("proxy-password", " ".join(command))
        self.assertNotIn("HARVY_ACCESS_TOKEN", env)
        self.assertEqual(env["SPIDER_API_KEY"], "sk-private-test-key")
        self.assertTrue(response.json["job_token"])

    def test_username_job_requires_consent_and_launches_python_worker(self):
        body = {"username": "sample_name", "categories": ["social"], "consent": True}
        with patch("web_app.subprocess.Popen") as launch, patch("web_app.threading.Thread"):
            launch.return_value.poll.return_value = 0
            response = self.client.post("/api/username-jobs", headers=self.headers(), json=body)
        self.assertEqual(response.status_code, 202)
        command = launch.call_args.args[0]
        self.assertIn("scrape.username", command)
        self.assertNotIn("sk-private-test-key", " ".join(command))
        self.assertEqual(response.json["kind"], "username")

    def test_username_job_rejects_bad_categories(self):
        with patch("web_app.subprocess.Popen") as launch:
            response = self.client.post("/api/username-jobs", headers=self.headers(), json={
                "username": "sample", "categories": ["bogus"], "consent": True,
            })
        self.assertEqual(response.status_code, 400)
        launch.assert_not_called()

    def test_concurrent_scrape_rejected(self):
        self.manager.slot.acquire()
        try:
            response = self.client.post("/api/jobs", headers=self.headers(), json={"url": "https://x.com/alice", "consent": True})
            self.assertEqual(response.status_code, 409)
        finally:
            self.manager.slot.release()

    def test_download_confined_to_job_and_archive_is_json(self):
        self.seed_job()
        outside = self.root / "outside.json"
        outside.write_text('{"secret":"another job"}')
        headers = self.headers("job-owner-secret")
        response = self.client.get("/api/jobs/job-a/files/../outside.json", headers=headers)
        self.assertEqual(response.status_code, 404)
        (self.root / "job-output" / "link.json").symlink_to(outside)
        self.assertEqual(self.client.get("/api/jobs/job-a/files/link.json", headers=headers).status_code, 404)
        response = self.client.get("/api/jobs/job-a/download", headers=headers)
        self.assertEqual(response.status_code, 200)
        with zipfile.ZipFile(io.BytesIO(response.data)) as bundle:
            self.assertEqual(set(bundle.namelist()), {"manifest.json", "posts/1.json"})
        response.close()

    def test_no_download_while_worker_writes_and_stop_requires_owner(self):
        job = self.seed_job(running=True)
        headers = self.headers("job-owner-secret")
        self.assertEqual(self.client.get("/api/jobs/job-a/download", headers=headers).status_code, 409)
        self.assertEqual(self.client.post("/api/jobs/job-a/stop", headers=self.headers("wrong")).status_code, 404)
        response = self.client.post("/api/jobs/job-a/stop", headers=headers)
        self.assertEqual(response.json["status"], "stopped")
        job["process"].terminate.assert_called_once()
        job["process"].poll.return_value = 0

    def test_weak_workspace_token_rejected(self):
        with self.assertRaises(ValueError):
            create_app({"SPIDER_API_KEY": "key", "ACCESS_TOKEN": "weak"})

    def test_worker_output_redacted_and_slot_released(self):
        job = self.seed_job()
        job["status"] = "running"
        job["process"].stdout = io.StringIO("sk-private-test-key proxy-password\n")
        job["process"].wait.return_value = 0
        self.manager.slot.acquire()
        self.manager.read(job)
        self.assertEqual(job["status"], "finished")
        self.assertNotIn("sk-private-test-key", "".join(job["logs"]))
        self.assertNotIn("proxy-password", "".join(job["logs"]))
        self.assertTrue(self.manager.slot.acquire(blocking=False))
        self.manager.slot.release()

    def test_finished_job_archives_json_artifacts_to_basin_when_configured(self):
        job = self.seed_job()
        job["status"] = "running"
        job["process"].stdout = io.StringIO("done\n")
        job["process"].wait.return_value = 0
        self.manager.config["BASIN_INGEST_URL"] = "https://stream.ingest.cloudflare.com"
        self.manager.slot.acquire()
        with patch("web_app.upload_directory", return_value={"files": 2, "events": 3, "batches": 1}) as upload:
            self.manager.read(job)
        self.assertEqual(job["basin_status"], "stored")
        self.assertEqual(job["status"], "finished")
        upload.assert_called_once()


if __name__ == "__main__":
    unittest.main()
