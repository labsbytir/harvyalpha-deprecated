#!/usr/bin/env python3
"""Backfill existing Harvy JSON artifacts to a configured Basin stream."""
import argparse
import os
from pathlib import Path
import sys

from health.basin_storage import upload_files
from proxy.config import get_proxy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data"), help="Local data directory")
    args = parser.parse_args()
    endpoint = os.environ.get("BASIN_INGEST_URL", "")
    if not endpoint:
        parser.error("Set BASIN_INGEST_URL to the Basin stream's HTTPS ingestion endpoint")
    root = args.root.expanduser().resolve()
    files = [p for p in sorted(root.rglob("*.json"))
             if p.is_file() and not p.is_symlink() and p.name not in ("whatsmyname-wmn-data.json", "username_targets.json")]
    if not files:
        print("No JSON artifacts found under {}".format(root))
        return 0
    try:
        result = upload_files(
            files, root, endpoint=endpoint,
            token=os.environ.get("BASIN_INGEST_TOKEN", ""),
            proxy=get_proxy(),
        )
    except (OSError, RuntimeError, ValueError) as error:
        print("Basin backfill failed: {}".format(error), file=sys.stderr)
        return 1
    print("Uploaded {} files as {} events in {} batches.".format(
        result["files"], result["events"], result["batches"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
