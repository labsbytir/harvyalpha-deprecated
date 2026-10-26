"""Classifies Telegram entities in data/telegram_channels.json into:
1. Public Broadcast Channels (public web preview history via t.me/s/)
2. Public Supergroups/Groups (public @handle, message mining via MTProto userbot)
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple


def probe_handle(username: str, timeout: int = 5) -> Tuple[str, str, Dict[str, str]]:
    url = f"https://t.me/s/{username}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return username, "error", {"error": str(e)}

    # Check for broadcast channel messages
    if "tgme_widget_message_wrap" in html:
        sub_m = re.search(r"class=\"tgme_page_extra[^\"]*\"[^>]*>(.*?)</div>", html, re.DOTALL)
        subs = sub_m.group(1).strip() if sub_m else "Channel"
        return username, "channel", {"stats": subs, "url": f"https://t.me/s/{username}"}

    # Check for group
    if "members" in html:
        mem_m = re.search(r"class=\"tgme_page_extra[^\"]*\"[^>]*>(.*?)</div>", html, re.DOTALL)
        mems = mem_m.group(1).strip() if mem_m else "Group"
        return username, "group", {"stats": mems, "url": f"https://t.me/{username}"}

    return username, "other", {"url": f"https://t.me/{username}"}


def main():
    parser = argparse.ArgumentParser(description="Probe and classify Telegram handles")
    parser.add_argument("--input", default="data/telegram_channels.json", help="Input master channels file")
    parser.add_argument("--limit", type=int, default=100, help="Number of handles to probe (default 100)")
    parser.add_argument("--workers", type=int, default=10, help="Concurrent HTTP worker threads")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: {args.input} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.input) as f:
        master = json.load(f)

    usernames = master.get("usernames", [])
    total = len(usernames)
    targets = usernames[: args.limit] if args.limit > 0 else usernames

    print(f"Probing {len(targets)} handles (workers={args.workers})...", file=sys.stderr)

    channels = {}
    groups = {}
    others = {}

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(probe_handle, u): u for u in targets}
        for fut in as_completed(futures):
            u, kind, meta = fut.result()
            if kind == "channel":
                channels[u] = meta
            elif kind == "group":
                groups[u] = meta
            else:
                others[u] = meta

    print(f"\nClassification results for {len(targets)} handles:", file=sys.stderr)
    print(f" - Public Channels (web-scrapable via HTTP): {len(channels)}", file=sys.stderr)
    print(f" - Public Groups (mineable via MTProto bot): {len(groups)}", file=sys.stderr)
    print(f" - Other / Inactive / Inaccessible: {len(others)}", file=sys.stderr)

    out_summary = {
        "total_probed": len(targets),
        "channels_count": len(channels),
        "groups_count": len(groups),
        "others_count": len(others),
        "channels": channels,
        "groups": groups,
    }

    out_path = "data/telegram_classified_sample.json"
    with open(out_path, "w") as fp:
        json.dump(out_summary, fp, indent=2)

    print(f"Sample classification saved to {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
