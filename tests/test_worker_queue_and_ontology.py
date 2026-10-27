import asyncio
import base64
import json
import time
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from v1.scrape.protocol import make_job
from src.worker import (
    Default,
    base64url_decode,
    check_and_increment_rate_limit,
    extract_profile_details,
    verify_webauthn_assertion,
)


class MockD1Statement:
    def __init__(self, sql, results=None):
        self.sql = sql
        self._results = results or []
        self._first = self._results[0] if self._results else None
        self.bind_args = []

    def bind(self, *args):
        self.bind_args = list(args)
        return self

    async def first(self):
        return self._first

    async def all(self):
        res = MagicMock()
        res.results = self._results
        res.to_py.return_value = {"results": self._results}
        return res

    async def run(self):
        return {"success": True}


class MockD1Database:
    def __init__(self):
        self.queries = []
        self.custom_results = {}

    def prepare(self, sql):
        self.queries.append(sql)
        for prefix, result in self.custom_results.items():
            if prefix in sql:
                return MockD1Statement(sql, result)
        return MockD1Statement(sql, [])


class MockKV:
    def __init__(self):
        self.store = {}

    async def get(self, key):
        return self.store.get(key)

    async def put(self, key, value, expirationTtl=None):
        self.store[key] = value

    async def delete(self, key):
        self.store.pop(key, None)


class MockR2Bucket:
    def __init__(self):
        self.objects = {}

    async def put(self, key, body):
        self.objects[key] = body

    async def get(self, key):
        if key in self.objects:
            res = MagicMock()
            res.body = self.objects[key]
            res.text = AsyncMock(return_value=self.objects[key])
            return res
        return None


class MockEnv:
    def __init__(self):
        self.HARVY_D1 = MockD1Database()
        self.HARVY_KV = MockKV()
        self.HARVY_BUCKET = MockR2Bucket()
        self.HARVY_QUEUE = MagicMock()
        self.HARVY_QUEUE.send = AsyncMock()
        self.SPIDER_API_KEY = "test_spider_key"
        self.WEBSHARE_PROXY_URL = "http://user:pass@192.0.2.1:8000"


class WorkerQueueAndOntologyTests(unittest.TestCase):
    def setUp(self):
        self.env = MockEnv()
        self.worker = Default(env=self.env)

    def test_base64url_decode(self):
        test_str = "hello-world_test"
        encoded = base64.urlsafe_b64encode(b"test_payload").decode("utf-8").rstrip("=")
        decoded = base64url_decode(encoded)
        self.assertEqual(decoded, b"test_payload")
        self.assertEqual(base64url_decode(""), b"")

    def test_verify_webauthn_assertion(self):
        stored_challenge = "a" * 64
        # Create clientDataJSON with valid type and challenge
        client_data = {"type": "webauthn.get", "challenge": stored_challenge, "origin": "https://harvybot.com"}
        client_data_raw = base64.urlsafe_b64encode(json.dumps(client_data).encode()).decode().rstrip("=")

        # Create authenticatorData with User Present flag (bit 0 of byte 32)
        auth_bytes = bytearray(37)
        auth_bytes[32] = 0x01  # UP flag set
        auth_data_raw = base64.urlsafe_b64encode(bytes(auth_bytes)).decode().rstrip("=")
        signature_raw = base64.urlsafe_b64encode(b"valid_sig").decode().rstrip("=")

        # Valid assertion
        self.assertTrue(verify_webauthn_assertion(stored_challenge, client_data_raw, auth_data_raw, signature_raw))

        # Missing clientData / signature
        self.assertFalse(verify_webauthn_assertion(stored_challenge, "", auth_data_raw, signature_raw))
        self.assertFalse(verify_webauthn_assertion(stored_challenge, client_data_raw, auth_data_raw, ""))

        # Wrong challenge in clientData
        bad_client = {"type": "webauthn.get", "challenge": "wrong_challenge", "origin": "https://harvybot.com"}
        bad_client_raw = base64.urlsafe_b64encode(json.dumps(bad_client).encode()).decode().rstrip("=")
        self.assertFalse(verify_webauthn_assertion(stored_challenge, bad_client_raw, auth_data_raw, signature_raw))

        # UP flag not set
        auth_bytes_no_up = bytearray(37)
        auth_bytes_no_up[32] = 0x00
        bad_auth_raw = base64.urlsafe_b64encode(bytes(auth_bytes_no_up)).decode().rstrip("=")
        self.assertFalse(verify_webauthn_assertion(stored_challenge, client_data_raw, bad_auth_raw, signature_raw))

    def test_atomic_rate_limiting(self):
        async def run_test():
            self.env.HARVY_D1.custom_results["harvy_rate_limits"] = [{"count": 1}]
            allowed, count = await check_and_increment_rate_limit(self.env.HARVY_D1, "user_1", 5, 100000)
            self.assertTrue(allowed)
            self.assertEqual(count, 1)

            # Exceed limit
            self.env.HARVY_D1.custom_results["harvy_rate_limits"] = [{"count": 6}]
            allowed, count = await check_and_increment_rate_limit(self.env.HARVY_D1, "user_1", 5, 100000)
            self.assertFalse(allowed)
            self.assertEqual(count, 6)

        asyncio.run(run_test())

    def test_extract_profile_details_from_raw(self):
        html = """
        <html>
        <head><title>Jane Doe (@janedoe) • Threads</title></head>
        <body>
        <script type="application/json">
        {
            "require": [
                ["RelayPrefetchedStreamCache", "set", [], [
                    {"__bbox": {"require": [
                        ["RelayPrefetchedStreamCache", "set", [], [
                            {},
                            {"__bbox": {"result": {"data": {
                                "user": {"username": "janedoe", "full_name": "Jane Doe", "biography": "Recon agent", "follower_count": 1200},
                                "mediaData": {"edges": [
                                    {"node": {"thread_items": [{"post": {"code": "xyz123", "caption": {"text": "Hello world!"}, "like_count": 42, "reply_count": 5, "taken_at": 1700000000}}]}}
                                ]}
                            }}}}
                        ]]
                    ]}}
                ]]
            ]
        }
        </script>
        </body>
        </html>
        """
        raw = [{"content": html}]
        details = extract_profile_details(raw, "https://www.threads.net/@janedoe")
        self.assertEqual(details["username"], "janedoe")
        self.assertEqual(details["full_name"], "Jane Doe")
        self.assertEqual(len(details["posts"]), 1)
        self.assertEqual(details["posts"][0]["code"], "xyz123")
        self.assertEqual(details["posts"][0]["text"], "Hello world!")

    def test_process_profile_job_and_ontology_ingest(self):
        async def run_test():
            job_id = "test-job-uuid-1"
            url = "https://www.threads.net/@janedoe"
            envelope = make_job(job_id, url)

            # Seed KV with queued job
            job_data = {
                "id": job_id, "token": "tok1", "status": "queued",
                "kind": "profile", "created_at": int(time.time()),
                "logs": [], "files": [], "post_files": 0
            }
            await self.env.HARVY_KV.put("job:" + job_id, json.dumps(job_data))

            mock_spider_html = """
            <html>
            <head><title>Jane Doe (@janedoe) • Threads</title></head>
            <body>
            <script type="application/json">
            {
                "require": [
                    ["RelayPrefetchedStreamCache", "set", [], [
                        {"__bbox": {"require": [
                            ["RelayPrefetchedStreamCache", "set", [], [
                                {},
                                {"__bbox": {"result": {"data": {
                                    "user": {"username": "janedoe", "full_name": "Jane Doe", "biography": "Recon agent", "follower_count": 1200},
                                    "mediaData": {"edges": [
                                        {"node": {"thread_items": [{"post": {"code": "xyz123", "caption": {"text": "Hello world!"}, "like_count": 42, "reply_count": 5, "taken_at": 1700000000}}]}}
                                    ]}
                                }}}}
                            ]]
                        ]}}
                    ]]
                ]
            }
            </script>
            </body>
            </html>
            """
            mock_fetch_res = MagicMock()
            mock_fetch_res.status = 200
            mock_fetch_res.text = AsyncMock(return_value=json.dumps([{"content": mock_spider_html}]))

            with patch("src.worker.get_proxy", return_value="http://user:pass@9.249.21.58:8000"):
                with patch("src.worker.fetch", return_value=mock_fetch_res, create=True):
                    # Mock js fetch in worker module
                    import sys
                    from types import ModuleType
                    js_mock = ModuleType("js")
                    js_mock.fetch = AsyncMock(return_value=mock_fetch_res)
                    js_mock.Object = MagicMock()
                    js_mock.Object.fromEntries = lambda x: x
                    with patch.dict(sys.modules, {"js": js_mock}):
                        await self.worker.process_profile_job(envelope)

            # Check job state in KV
            saved_job = json.loads(await self.env.HARVY_KV.get("job:" + job_id))
            self.assertEqual(saved_job["status"], "finished")
            self.assertEqual(saved_job["post_files"], 1)

            # Check ontology table queries were issued
            queries = self.env.HARVY_D1.queries
            self.assertTrue(any("harvy_search_documents" in q for q in queries))
            self.assertTrue(any("harvy_objects" in q for q in queries))
            self.assertTrue(any("harvy_observations" in q for q in queries))
            self.assertTrue(any("harvy_links" in q for q in queries))

            # Verify R2 bucket received raw payload
            self.assertIn(f"jobs/{job_id}/raw/profile.json", self.env.HARVY_BUCKET.objects)

        asyncio.run(run_test())

    def test_queue_batch_error_handling(self):
        async def run_test():
            job_id = "test-fail-uuid"
            job_data = {
                "id": job_id, "token": "tok2", "status": "queued",
                "kind": "profile", "created_at": int(time.time()),
                "logs": [], "files": [], "post_files": 0
            }
            await self.env.HARVY_KV.put("job:" + job_id, json.dumps(job_data))

            # Simulate queue batch with invalid / failing target
            msg = MagicMock()
            msg.body = {"job_id": job_id, "url": "https://invalid.com/bad"}
            batch = MagicMock()
            batch.messages = [msg]

            with patch.object(self.worker, "process_profile_job", side_effect=RuntimeError("Spider API Down")):
                await self.worker.queue(batch)

            # Verify job marked failed gracefully in KV
            saved_job = json.loads(await self.env.HARVY_KV.get("job:" + job_id))
            self.assertEqual(saved_job["status"], "failed")
            self.assertEqual(saved_job["error"], "RuntimeError")

        asyncio.run(run_test())

    def test_fts5_search_query(self):
        async def run_test():
            self.env.HARVY_D1.custom_results["harvy_search_documents_fts"] = [
                {"id": "doc1", "title": "Jane Doe Profile", "snippet": "Recon agent", "body": "Jane is an agent", "source": "social"}
            ]
            req = MagicMock()
            req.method = "GET"
            req.url = "https://harvybot.com/api/universal-search?q=jane"
            res = await self.worker.handle_api(req, "/api/universal-search", {"q": ["jane"]})
            self.assertEqual(res.status, 200)
            data = json.loads(res.body)
            self.assertEqual(len(data["results"]), 1)
            self.assertEqual(data["results"][0]["title"], "Jane Doe Profile")
            # Verify FTS query was issued
            self.assertTrue(any("harvy_search_documents_fts MATCH" in q for q in self.env.HARVY_D1.queries))

        asyncio.run(run_test())

    def test_passkey_login_verify_rejection(self):
        async def run_test():
            # Seed challenge in KV
            challenge_id = "test-challenge-123"
            await self.env.HARVY_KV.put(f"login_challenge:{challenge_id}", "a" * 64)

            # Request with missing/invalid signature assertion
            req = MagicMock()
            req.method = "POST"
            req.headers = {"Content-Type": "application/json"}
            req.json = AsyncMock(return_value={
                "credentialId": "cred-xyz",
                "challengeId": challenge_id,
                # Missing signature and authData
            })
            res = await self.worker.handle_api(req, "/api/auth/passkey/login-verify", {})
            self.assertEqual(res.status, 401)
            data = json.loads(res.body)
            self.assertIn("Cryptographic passkey verification failed", data["error"])

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
