import json
import logging
from unittest.mock import patch, MagicMock
import unittest
import urllib.request

from health.harvy_logger import format_log_record, HarvyLogHandler, HarvyLogger


class TestHarvyLogging(unittest.TestCase):
    def test_format_log_record_sanitizes_service_and_adds_defaults(self):
        record = format_log_record(
            service="test service/@123",
            level="warn",
            message="Test message",
            metadata={"key": "value"},
        )
        self.assertEqual(record["service"], "test_service__123")
        self.assertEqual(record["level"], "WARN")
        self.assertEqual(record["message"], "Test message")
        self.assertEqual(record["metadata"], {"key": "value"})
        self.assertIn("timestamp", record)
        self.assertEqual(record["environment"], "production")

    def test_harvy_log_handler_buffering_and_flush(self):
        handler = HarvyLogHandler(
            service="test_svc",
            ingest_url="https://harvybot.com/api/logs/ingest",
            api_key="test-key",
            buffer_size=2,
            flush_interval=60.0,
        )

        logger = logging.getLogger("test_logger_batch")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)

        mock_resp = MagicMock()
        mock_resp.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            # Emit first record: buffered, not flushed
            logger.info("Message 1")
            self.assertEqual(len(handler._buffer), 1)
            mock_urlopen.assert_not_called()

            # Emit second record: buffer_size reached, flush triggered
            logger.info("Message 2")
            self.assertEqual(len(handler._buffer), 0)
            mock_urlopen.assert_called_once()

            req = mock_urlopen.call_args[0][0]
            self.assertEqual(req.full_url, "https://harvybot.com/api/logs/ingest")
            self.assertEqual(req.headers["X-api-key"], "test-key")
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(len(body["events"]), 2)
            self.assertEqual(body["events"][0]["message"], "Message 1")
            self.assertEqual(body["events"][1]["message"], "Message 2")

    def test_harvy_logger_standalone(self):
        client = HarvyLogger(
            service="standalone_svc",
            ingest_url="https://harvybot.com/api/logs/ingest",
            api_key="standalone-key",
        )

        mock_resp = MagicMock()
        mock_resp.status = 200

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value.__enter__.return_value = mock_resp
            client.info("Standalone event", metadata={"node": "vps1"})
            mock_urlopen.assert_called_once()
            req = mock_urlopen.call_args[0][0]
            body = json.loads(req.data.decode("utf-8"))
            self.assertEqual(body["events"][0]["service"], "standalone_svc")
            self.assertEqual(body["events"][0]["message"], "Standalone event")
            self.assertEqual(body["events"][0]["metadata"]["node"], "vps1")

    def test_network_failure_does_not_raise(self):
        handler = HarvyLogHandler(
            service="fail_svc",
            ingest_url="https://harvybot.com/api/logs/ingest",
            buffer_size=1,
        )
        logger = logging.getLogger("test_logger_fail")
        logger.addHandler(handler)

        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            try:
                logger.error("Should not raise")
            except Exception:
                self.fail("Logging raised an unhandled exception")


if __name__ == "__main__":
    unittest.main()
