"""Copy canonical repository guides into the local Harvy Obsidian vault."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VAULT = Path(os.environ.get("HARVY_OBSIDIAN_VAULT", "/Users/pen/Documents/Notes/harvy"))
DEST = VAULT / "Guides"
SOURCES = [*(ROOT / "guides").glob("*.md"), ROOT / "health" / "BASIN.md"]

if not VAULT.is_dir():
    raise SystemExit(f"Obsidian vault not found: {VAULT}; set HARVY_OBSIDIAN_VAULT")

DEST.mkdir(parents=True, exist_ok=True)
for source in SOURCES:
    text = source.read_text()
    text = text.replace(
        "../health/BASIN.md",
        "file:///Users/pen/Documents/harvy/health/BASIN.md",
    ).replace(
        "../planning/PLAN.md",
        "file:///Users/pen/Documents/Notes/harvy/Planning/PLAN.md",
    ).replace(
        "../platform-v2/",
        "file:///Users/pen/Documents/harvy/platform-v2/",
    )
    marker = f"<!-- Synced from {source.relative_to(ROOT).as_posix()}; edit the repository source and rerun npm run sync:vault-guides. -->\n\n"
    (DEST / source.name).write_text(marker + text)

print(f"Synced {len(SOURCES)} guide files to {DEST}")
