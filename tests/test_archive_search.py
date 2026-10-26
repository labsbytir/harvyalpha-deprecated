import json
from pathlib import Path
import tempfile
import unittest

from archive_search import index_directory, search


class ArchiveSearchTests(unittest.TestCase):
    def test_indexes_json_and_html_and_updates_changed_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "data"
            root.mkdir()
            (root / "case.json").write_text(json.dumps({
                "caseName": "Miranda v Arizona", "snippet": "constitutional rights"
            }))
            (root / "profile.html").write_text(
                "<html><title>Public profile</title><script>hidden word</script><p>Visible place record</p></html>"
            )
            db = Path(tmp) / "search.sqlite3"
            first = index_directory(root, db)
            self.assertEqual(first["indexed_files"], 2)
            self.assertEqual(index_directory(root, db)["indexed_files"], 0)
            results = search(db, "Miranda constitutional")
            self.assertEqual(len(results), 1)
            self.assertIn("Miranda", results[0]["title"] + results[0]["snippet"])
            self.assertEqual(len(search(db, "hidden")), 0)
            self.assertEqual(len(search(db, "Visible place")), 1)
            (root / "case.json").write_text(json.dumps({"caseName": "Different topic"}))
            index_directory(root, db)
            self.assertEqual(len(search(db, "Miranda")), 0)
            self.assertEqual(len(search(db, "Different")), 1)

    def test_search_rejects_blank_and_overlong_queries(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "search.sqlite3"
            index_directory(Path(tmp), db)
            self.assertEqual(search(db, "***"), [])
            with self.assertRaises(ValueError):
                search(db, "x" * 201)


if __name__ == "__main__":
    unittest.main()
