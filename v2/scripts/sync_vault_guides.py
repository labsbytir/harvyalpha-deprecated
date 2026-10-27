"""Copy canonical repository documentation into the local Harvy Obsidian vault."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VAULT = Path(os.environ.get("HARVY_OBSIDIAN_VAULT", "/Users/pen/Documents/Notes/harvy"))
DEST = VAULT / "Guides"
SOURCES = sorted((ROOT / "docs").glob("*.md"))

if not VAULT.is_dir():
    raise SystemExit(f"Obsidian vault not found: {VAULT}; set HARVY_OBSIDIAN_VAULT")

DEST.mkdir(parents=True, exist_ok=True)
synced_names = set()
for source in SOURCES:
    text = source.read_text()
    text = text.replace(
        "../v2/health/BASIN.md",
        "file:///Users/pen/Documents/harvy/v2/health/BASIN.md",
    ).replace(
        "../planning/PLAN.md",
        "file:///Users/pen/Documents/Notes/harvy/Planning/PLAN.md",
    ).replace(
        "../v2/",
        "file:///Users/pen/Documents/harvy/v2/",
    )
    marker = f"<!-- Synced from {source.relative_to(ROOT).as_posix()}; edit the repository source and rerun npm run sync:vault-guides. -->\n\n"
    (DEST / source.name).write_text(marker + text)
    synced_names.add(source.name)

for stale in DEST.glob("*.md"):
    if stale.name not in synced_names and stale.read_text().startswith("<!-- Synced from "):
        stale.unlink()

plan_source = ROOT / "docs" / "PLAN.md"
if plan_source.is_file():
    plan_destination = VAULT / "Planning" / "PLAN.md"
    plan_destination.parent.mkdir(parents=True, exist_ok=True)
    plan_destination.write_text(plan_source.read_text())

print(f"Synced {len(SOURCES)} guide files to {DEST}")
