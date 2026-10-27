import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class V2PortalShellTests(unittest.TestCase):
    def test_shell_uses_v2_auth_and_does_not_claim_local_scope(self):
        source = (ROOT / "v2" / "portal" / "saas-shell.js").read_text()

        self.assertIn("window.harvyAuthClient?.getSession()", source)
        self.assertIn("window.openHarvyAuthModal?.()", source)
        self.assertNotIn("/api/auth/me", source)
        self.assertNotIn("harvy_environment", source)

    def test_pages_using_shell_load_the_v2_auth_client(self):
        for page in (ROOT / "pages").glob("*.html"):
            source = page.read_text()
            if "saas-shell.js" in source:
                with self.subTest(page=page.name):
                    self.assertIn("auth-client.js", source)
                    self.assertIn("auth-modal.js", source)

    def test_query_ui_uses_v2_routes_only(self):
        api = (ROOT / "v2" / "graph" / "src" / "api.ts").read_text()
        app = (ROOT / "v2" / "graph" / "src" / "App.tsx").read_text()

        self.assertIn("/api/v2/query/catalog", api)
        self.assertIn("/api/v2/dashboards", api)
        self.assertNotIn("/api/query/", api)
        self.assertNotIn("/api/dashboards", api)
        self.assertIn("/api/v2/cube", app)
        self.assertNotIn("/cubejs-api/v1", app)


if __name__ == "__main__":
    unittest.main()
