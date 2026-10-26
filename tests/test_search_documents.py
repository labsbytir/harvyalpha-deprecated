import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from search_documents import documents_for_job


class SearchDocumentsTests(unittest.TestCase):
    def test_builds_job_scoped_documents_from_records_and_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "raw").mkdir()
            (root / "raw" / "courtlistener.json").write_text(json.dumps({
                "results": [
                    {"caseName": "Miranda v Arizona", "absolute_url": "https://example.com/case", "snippet": "constitutional law"},
                    {"caseName": "Another Case", "snippet": "docket entry"},
                ]
            }))
            (root / "raw" / "arrests.json").write_text(json.dumps({
                "content": "<html><script>do not index</script><p>Visible record text</p></html>"
            }))
            files = sorted(root.rglob("*.json"))
            result = documents_for_job(root, files, "research", "query")
        self.assertFalse(result["truncated"])
        self.assertTrue(any(doc["source"] == "courtlistener" and "Miranda v Arizona" in doc["text"] for doc in result["documents"]))
        self.assertTrue(any("Visible record text" in doc["text"] for doc in result["documents"]))
        self.assertFalse(any("do not index" in doc["text"] for doc in result["documents"]))

    def test_caps_document_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "many.json"
            source.write_text(json.dumps([{"name": str(i)} for i in range(12)]))
            with patch("search_documents.MAX_DOCUMENTS", 5):
                result = documents_for_job(root, [source])
        self.assertEqual(len(result["documents"]), 5)
        self.assertTrue(result["truncated"])


if __name__ == "__main__":
    unittest.main()
