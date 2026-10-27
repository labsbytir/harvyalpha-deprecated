import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from v2.scripts.build_github_pages import main, parse_commits


class GithubPagesBuildTests(unittest.TestCase):
    def test_cli_builds_pages_from_repository_root(self):
        with TemporaryDirectory() as output:
            with patch("sys.argv", ["build_github_pages.py", "--output", output]):
                main()
            self.assertTrue((Path(output) / "index.html").is_file())
            self.assertTrue((Path(output) / "site.css").is_file())

    def test_changelog_rows_use_commit_subjects_and_links(self):
        entries = parse_commits(
            "a" * 40 + "\x1fdocs: add pages\x1f2026-10-26\n" +
            "invalid row\n",
            "https://github.com/labsbytir/harvy",
        )

        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["short_sha"], "a" * 7)
        self.assertEqual(entries[0]["subject"], "docs: add pages")
        self.assertEqual(entries[0]["url"], f"https://github.com/labsbytir/harvy/commit/{'a' * 40}")


if __name__ == "__main__":
    unittest.main()
