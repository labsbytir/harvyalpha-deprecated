#!/usr/bin/env python3
"""Sync canonical Harvy markdown guides and documentation into the Quartz docs repository."""
import argparse
import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def sync_docs(dest_dir: Path) -> int:
    guides_src = ROOT / "guides"
    basin_src = ROOT / "health" / "BASIN.md"

    if not dest_dir.is_dir():
        print(f"Error: destination directory {dest_dir} does not exist", file=sys.stderr)
        return 1

    content_guides = dest_dir / "content" / "guides"
    content_health = dest_dir / "content" / "health"
    content_notebooks = dest_dir / "content" / "notebooks"

    content_guides.mkdir(parents=True, exist_ok=True)
    content_health.mkdir(parents=True, exist_ok=True)

    # Sync guides
    synced_count = 0
    for guide in guides_src.glob("*.md"):
        dest_file = content_guides / guide.name
        shutil.copy2(guide, dest_file)
        synced_count += 1

    # Sync Basin guide
    if basin_src.is_file():
        shutil.copy2(basin_src, content_health / "BASIN.md")
        synced_count += 1

    # Sync notebooks (repo documentation)
    notebooks_src = ROOT / "notebooks"
    if notebooks_src.is_dir():
        content_notebooks.mkdir(parents=True, exist_ok=True)
        for notebook in notebooks_src.glob("*.md"):
            shutil.copy2(notebook, content_notebooks / notebook.name)
            synced_count += 1

    print(f"Synced {synced_count} documentation files to {dest_dir / 'content'}")
    return 0

def main():
    parser = argparse.ArgumentParser(description="Sync Harvy guides to harvy-docs repository")
    parser.add_argument("--dest", type=Path, default=Path(os.environ.get("HARVY_DOCS_REPO", "/Users/pen/Documents/harvy-docs")), help="Path to harvy-docs repository clone")
    args = parser.parse_args()
    return sync_docs(args.dest)

if __name__ == "__main__":
    sys.exit(main())
