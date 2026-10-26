import os
import unittest
from unittest.mock import patch

from proxy.config import get_proxy


class ProxyConfigTests(unittest.TestCase):
    def test_reads_local_environment(self):
        with patch.dict(os.environ, {"WEBSHARE_PROXY_URL": "http://user:pass@proxy.example:8080"}):
            self.assertEqual(get_proxy(), "http://user:pass@proxy.example:8080")

    def test_reads_worker_secret_binding(self):
        self.assertEqual(get_proxy({"WEBSHARE_PROXY_URL": "http://proxy.example:8080"}),
                         "http://proxy.example:8080")

    def test_missing_or_invalid_proxy(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_proxy(), "")
            with self.assertRaises(ValueError):
                get_proxy(required=True)
        for value in ("file:///tmp/proxy", "http://proxy.example", "http://proxy.example:bad"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                get_proxy({"WEBSHARE_PROXY_URL": value})


if __name__ == "__main__":
    unittest.main()
