import tempfile
import unittest
import json
from pathlib import Path

from v2.scripts.import_v2_source_catalog import import_catalog


class V2CatalogImportTests(unittest.TestCase):
    def test_catalog_metadata_stays_disabled_and_references_are_not_connectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog = Path(tmp) / "Ingestion" / "Stream Catalog"
            streams = catalog / "Streams" / "AA_Government & Civic"
            streams.mkdir(parents=True)
            (streams / "STR_socrata.md").write_text(
                "# STR_socrata\n"
                "- **Catalog disposition:** Approved (catalog status)\n"
                "- **Civontology implementation status:** Proposed; no live pull\n"
                "- **Rollout horizon:** US initial / candidate\n"
                "- **Source specification:** [spec](https://example.test/socrata)\n",
                encoding="utf-8",
            )
            (streams / "REF_product.md").write_text("# REF_product\n", encoding="utf-8")

            result = import_catalog(catalog, "abc123")

        self.assertEqual(result["upstream"]["commit"], "abc123")
        self.assertEqual(len(result["streams"]), 1)
        self.assertEqual(result["streams"][0]["id"], "stream.socrata")
        self.assertEqual(result["streams"][0]["catalog_disposition"], "approved")
        self.assertFalse(result["streams"][0]["enabled"])
        self.assertFalse(result["streams"][0]["code_copied"])
        self.assertEqual(result["references"][0]["kind"], "reference_only")
        self.assertEqual(len(result["requested_scopes"]), 53)
        self.assertEqual(len(result["data_portals"]), 7)

    def test_checked_in_source_snapshot_is_catalog_only(self):
        path = Path(__file__).resolve().parents[1] / "v2" / "catalog" / "connector-scopes.json"
        catalog = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(catalog["streams"]), 99)
        self.assertEqual(len(catalog["references"]), 11)
        self.assertEqual(len(catalog["requested_scopes"]), 53)
        self.assertTrue(all(entry["enabled"] is False for entry in catalog["streams"]))


if __name__ == "__main__":
    unittest.main()
