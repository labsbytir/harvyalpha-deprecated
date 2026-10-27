"""Refresh picker: re-queue oldest telegram channels for incremental refresh.

Reads local data/telegram/index.json, picks channels whose
last_scraped_at is oldest (or never), prints queue envelopes.
Stale exhausted flags with short post counts are re-queued first.

Usage:
  python3 v1/scripts/telegram_refresh.py --count 50 --slot 1 | \\
    while read -r line; do curl -s -X POST ... -d "$line"; done
  python3 v1/scripts/telegram_refresh.py --count 50 --slot 1 --enqueue  # direct via Queues REST
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from v1.scrape.telegram import OUT_ROOT, make_envelope  # noqa: E402


def load_registry(base: str) -> dict:
    try:
        return json.loads((Path(base) / "index.json").read_text())
    except Exception:
        return {"channels": {}}


def rank_channels(registry: dict, base: str, count: int) -> list:
    scored = []
    for handle, entry in (registry.get("channels") or {}).items():
        if entry.get("availability") == "unavailable":
            checked = entry.get("last_checked_at", "")
            try:
                age_days = (datetime.now(timezone.utc)
                            - datetime.fromisoformat(checked)).days
            except Exception:
                age_days = 0
            if age_days < 90:
                continue  # skip tombstoned unless 90d old
        last = entry.get("last_scraped_at", "")
        scored.append((last or "", handle))
    scored.sort()
    return [handle for _, handle in scored[:count]]


def enqueue_rest(account: str, queue_id: str, envelopes: list) -> int:
    token = os.environ.get("CF_QUEUE_TOKEN", "")
    url = ("https://api.cloudflare.com/client/v4/accounts/{}/queues/{}/messages/batch"
           .format(account, queue_id))
    body = json.dumps({"messages": [{"body": e} for e in envelopes]}).encode()
    req = urllib.request.Request(
        url, data=body,
        headers={"Authorization": "Bearer " + token,
                 "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=60) as res:
        result = json.loads(res.read().decode())
        return len(result.get("result", {}).get("successful", []))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Telegram refresh picker")
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--slot", default="1")
    parser.add_argument("--base", default=OUT_ROOT)
    parser.add_argument("--limit", type=int, default=0,
                        help="0 = resume from checkpoint (incremental)")
    parser.add_argument("--enqueue", action="store_true",
                        help="POST directly to the queue via REST")
    args = parser.parse_args(argv)

    registry = load_registry(args.base)
    handles = rank_channels(registry, args.base, args.count)
    envelopes = [make_envelope(str(uuid.uuid4()), h, args.limit, args.slot)
                 for h in handles]
    if args.enqueue:
        account = os.environ.get("CF_ACCOUNT_ID", "")
        queue_id = os.environ.get("TELEGRAM_QUEUE_ID", "")
        if not account or not queue_id:
            print("Error: set CF_ACCOUNT_ID and TELEGRAM_QUEUE_ID", file=sys.stderr)
            return 1
        sent = enqueue_rest(account, queue_id, envelopes)
        print(json.dumps({"queued": sent, "requested": len(envelopes)}))
    else:
        for envelope in envelopes:
            print(json.dumps(envelope))
    return 0


if __name__ == "__main__":
    sys.exit(main())
