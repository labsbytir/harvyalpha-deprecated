#!/usr/bin/env python3
"""Sync canonical Harvy markdown guides and documentation into the Quartz docs repository."""
import argparse
import os
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

def sync_docs(dest_dir: Path) -> int:
    docs_src = REPO_ROOT / "docs"
    basin_src = REPO_ROOT / "v2" / "health" / "BASIN.md"

    if not dest_dir.is_dir():
        print(f"Error: destination directory {dest_dir} does not exist", file=sys.stderr)
        return 1

    content_guides = dest_dir / "content" / "guides"
    content_health = dest_dir / "content" / "health"
    content_notebooks = dest_dir / "content" / "notebooks"

    content_guides.mkdir(parents=True, exist_ok=True)
    content_health.mkdir(parents=True, exist_ok=True)

    # Sync guides / docs
    synced_count = 0
    src_dir = docs_src
    guide_names = {doc.name for doc in src_dir.glob("*.md")}
    for doc in src_dir.glob("*.md"):
        dest_file = content_guides / doc.name
        shutil.copy2(doc, dest_file)
        synced_count += 1
    for stale_name in (
        "PLATFORM_V2_CONNECTORS.md",
        "platform-v2-first-five.md",
        "V1_CONTRACTS.md",
        "SCRAPING.md",
        "RESEARCH.md",
        "site-search-framework.md",
    ):
        stale = content_guides / stale_name
        if stale_name not in guide_names and stale.is_file():
            stale.unlink()

    # Sync Basin guide
    if basin_src.is_file():
        shutil.copy2(basin_src, content_health / "BASIN.md")
        synced_count += 1

    # Sync notebooks (repo documentation)
    notebooks_src = REPO_ROOT / "notebooks"
    if notebooks_src.is_dir():
        content_notebooks.mkdir(parents=True, exist_ok=True)
        notebook_names = {notebook.name for notebook in notebooks_src.glob("*.md")}
        for notebook in notebooks_src.glob("*.md"):
            shutil.copy2(notebook, content_notebooks / notebook.name)
            synced_count += 1
        stale_notebook = content_notebooks / "platform-v2-first-five.md"
        if "platform-v2-first-five.md" not in notebook_names and stale_notebook.is_file():
            stale_notebook.unlink()

    print(f"Synced {synced_count} documentation files to {dest_dir / 'content'}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Sync Harvy guides to harvy-docs repository")
    parser.add_argument("--dest", type=Path, default=Path(os.environ.get("HARVY_DOCS_REPO", "/Users/pen/Documents/harvy-docs")), help="Path to harvy-docs repository clone")
    args = parser.parse_args()
    return sync_docs(args.dest)

if __name__ == "__main__":
    sys.exit(main())
