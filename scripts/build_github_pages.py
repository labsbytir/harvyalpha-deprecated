"""Build the dependency-free GitHub Pages landing site."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


def parse_commits(output: str, repo_url: str) -> list[dict[str, str]]:
	entries = []
	for line in output.splitlines():
		parts = line.split("\x1f", 2)
		if len(parts) != 3:
			continue
		sha, subject, date = parts
		if not sha or not subject or len(date) != 10:
			continue
		entries.append({
			"sha": sha,
			"short_sha": sha[:7],
			"subject": subject,
			"date": date,
			"url": f"{repo_url.rstrip('/')}/commit/{sha}",
		})
	return entries


def recent_commits(repo_root: Path, repo_url: str) -> list[dict[str, str]]:
	result = subprocess.run(
		["git", "log", "--max-count=10", "--date=short", "--format=%H%x1f%s%x1f%as"],
		cwd=repo_root,
		check=True,
		capture_output=True,
		text=True,
	)
	return parse_commits(result.stdout, repo_url)


def build_site(repo_root: Path, output_dir: Path, repo_url: str) -> int:
	assets = {
		"templates/github-pages.html": "index.html",
		"styles/github-pages.css": "site.css",
		"static/harvy-github-banner.png": "harvy-github-banner.png",
		"static/harvy-logo.png": "harvy-logo.png",
	}
	output_dir.mkdir(parents=True, exist_ok=True)
	for source, destination in assets.items():
		(output_dir / destination).write_bytes((repo_root / source).read_bytes())
	entries = recent_commits(repo_root, repo_url)
	(output_dir / "changelog.json").write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
	return len(entries)


def main() -> None:
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output", type=Path, default=Path("_site"))
	args = parser.parse_args()
	repo_root = Path(__file__).resolve().parents[1]
	repository = os.environ.get("GITHUB_REPOSITORY", "labsbytir/harvy")
	count = build_site(repo_root, args.output, f"https://github.com/{repository}")
	print(f"Built Pages site to {args.output} with {count} recent commits.")


if __name__ == "__main__":
	main()
