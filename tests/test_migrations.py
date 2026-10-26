from pathlib import Path
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parent.parent


class MigrationTests(unittest.TestCase):
    def test_migrations_add_privacy_and_newsletter_consent_storage(self):
        db = sqlite3.connect(":memory:")
        try:
            for migration in sorted((ROOT / "migrations").glob("*.sql")):
                db.executescript(migration.read_text())
            user_columns = {row[1] for row in db.execute("PRAGMA table_info(harvy_users)")}
            consent_columns = {row[1] for row in db.execute("PRAGMA table_info(harvy_newsletter_consents)")}
            self.assertIn("privacy_accepted_at", user_columns)
            self.assertIn("buttondown_subscriber_id", consent_columns)
            self.assertNotIn("email", consent_columns)

            # 0004 ontology & dashboards migration verification
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            expected_tables = {
                "harvy_object_types",
                "harvy_objects",
                "harvy_observations",
                "harvy_link_types",
                "harvy_links",
                "harvy_dashboards",
                "user",
                "session",
                "account",
                "verification",
                "passkey",
                "apikey",
                "organization",
                "member",
                "invitation",
                "two_factor",
                "referrals",
                "harvy_auth_privacy_consents",
            }
            self.assertTrue(expected_tables.issubset(tables))

            obs_columns = {row[1] for row in db.execute("PRAGMA table_info(harvy_observations)")}
            self.assertIn("environment_id", obs_columns)
            self.assertIn("r2_object_key", obs_columns)
            self.assertIn("content_sha256", obs_columns)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
