import unittest

from v1.scrape.protocol import (
    from_v1_job,
    from_v1_result,
    make_job,
    make_legal_job,
    make_result,
    to_v1_job,
    to_v1_result,
    validate_job,
)


class ScrapeProtocolTests(unittest.TestCase):
    def test_job_round_trips_with_normalized_network(self):
        job = make_job("j1", "https://www.instagram.com/alice/", options={"max_posts": 5})
        self.assertEqual(job["network"], "instagram")
        self.assertEqual(job["source"], "instagram")
        self.assertEqual(job["environment_id"], "shared")
        self.assertEqual(validate_job(job), job)
        self.assertEqual(make_result(job, "partial")["protocol"], 1)

    def test_rejects_unsafe_or_malformed_jobs(self):
        with self.assertRaises(ValueError):
            make_job("j1", "http://instagram.com/alice")
        with self.assertRaises(ValueError):
            validate_job({"protocol": 99})
        with self.assertRaises(ValueError):
            make_job("j1", "https://instagram.com/alice", options=[])
        with self.assertRaises(ValueError):
            make_job("j1", "https://instagram.com/alice", limits="invalid")
        with self.assertRaises(ValueError):
            make_job("j1", "https://instagram.com/alice", environment_id="bad env name!")

    def test_extended_operations_and_environment_scope(self):
        job = make_job(
            "j2",
            "https://www.courtlistener.com/search/",
            operation="legal",
            environment_id="tenant_alpha",
            limits={"max_records": 10},
            source="courtlistener",
            protocol=2,
        )
        self.assertEqual(job["protocol"], 2)
        self.assertEqual(job["operation"], "legal")
        self.assertEqual(job["environment_id"], "tenant_alpha")
        self.assertEqual(job["source"], "courtlistener")
        self.assertEqual(job["limits"]["max_records"], 10)
        self.assertEqual(validate_job(job), job)

    def test_make_legal_job_validates_and_constructs_envelope(self):
        # Valid legal job
        job = make_legal_job(
            "leg_1",
            query="State v. Sample",
            sources=["courtlistener", "judyrecords"],
            state="TX",
            environment_id="env_court",
            limits={"max_records": 15},
            protocol=2,
        )
        self.assertEqual(job["protocol"], 2)
        self.assertEqual(job["operation"], "legal")
        self.assertEqual(job["environment_id"], "env_court")
        self.assertEqual(job["options"]["query"], "State v. Sample")
        self.assertEqual(job["options"]["state"], "TX")
        self.assertEqual(job["limits"]["max_records"], 15)
        self.assertEqual(validate_job(job), job)

        # Arrests.org validation requires first, last, state
        with self.assertRaises(ValueError):
            make_legal_job("leg_err", query="Sample", sources=["arrests_org"])

        # Invalid query length
        with self.assertRaises(ValueError):
            make_legal_job("leg_err", query="x", sources=["courtlistener"])

    def test_result_completeness_and_provenance(self):
        job = make_job("j3", "https://threads.net/@alice", environment_id="env_x")
        completeness = {"complete": False, "reason": "pagination_truncated"}
        provenance = {"source_url": "https://threads.net/@alice", "parser": "threads.py@1.0"}
        result = make_result(
            job,
            "inconclusive",
            records=[{"post": 1}],
            completeness=completeness,
            provenance=provenance,
        )
        self.assertEqual(result["status"], "inconclusive")
        self.assertEqual(result["environment_id"], "env_x")
        self.assertFalse(result["completeness"]["complete"])
        self.assertEqual(result["completeness"]["reason"], "pagination_truncated")
        self.assertEqual(result["provenance"]["parser"], "threads.py@1.0")

    def test_v1_compatibility_adapters(self):
        # Strict legacy v1 message shape
        v1_raw = {
            "protocol": 1,
            "job_id": "legacy_1",
            "network": "facebook",
            "operation": "profile",
            "target": "https://facebook.com/someone",
            "options": {"max_posts": 10},
        }
        validated = validate_job(v1_raw)
        self.assertEqual(validated, v1_raw)

        # Upgrade to extended envelope
        upgraded = from_v1_job(v1_raw, environment_id="env_beta")
        self.assertEqual(upgraded["protocol"], 2)
        self.assertEqual(upgraded["environment_id"], "env_beta")
        self.assertEqual(upgraded["limits"]["max_posts"], 10)

        # Downgrade back to strict v1
        downgraded = to_v1_job(upgraded)
        self.assertEqual(downgraded, v1_raw)

        # Result roundtrip
        v1_res = {
            "protocol": 1,
            "job_id": "legacy_1",
            "network": "facebook",
            "operation": "profile",
            "target": "https://facebook.com/someone",
            "status": "partial",
            "records": [{"id": 1}],
            "error": None,
        }
        upgraded_res = from_v1_result(v1_res, completeness={"complete": False})
        self.assertEqual(upgraded_res["protocol"], 2)
        self.assertFalse(upgraded_res["completeness"]["complete"])
        downgraded_res = to_v1_result(upgraded_res)
        self.assertEqual(downgraded_res, v1_res)


if __name__ == "__main__":
    unittest.main()
