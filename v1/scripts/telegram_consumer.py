"""VPS consumer: lease telegram_channel jobs, mine, upload to R2/D1.

Flow per job:
  mine via v1.scrape.telegram -> R2 PUT (channel.json, posts.json, ...)
  -> D1 ontology upsert (harvy_objects, harvy_observations)
  -> ack via Queues REST delete.

Usage:
  set -a; source /opt/harvy/.env; set +a
  python3 v1/scripts/telegram_consumer.py --batch 50 --slot 1
  python3 v1/scripts/telegram_consumer.py --batch 50 --slot 2

One process per slot. Ctrl-C stops cleanly (message stays visible,
reappears after visibility timeout).
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from v1.scrape.telegram import OUT_ROOT, mine_channel, account_slots  # noqa: E402

QUEUE_BASE = "https://api.cloudflare.com/client/v4/accounts/{acct}/queues/{qid}"
LEASE_SECONDS = 300


def _headers() -> dict:
    token = os.environ.get("CF_QUEUE_TOKEN", "")
    return {"Authorization": "Bearer " + token, "Content-Type": "application/json"}


def queue_pull(account: str, queue_id: str, batch: int) -> list:
    url = QUEUE_BASE.format(acct=account, qid=queue_id) + "/messages/pull"
    body = json.dumps({"visibility_timeout_ms": LEASE_SECONDS * 1000,
                       "batch_size": batch}).encode()
    req = urllib.request.Request(url, data=body, headers=_headers(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            payload = json.loads(res.read().decode())
            return payload.get("result", {}).get("messages", []) or []
    except Exception as error:
        print("pull error: {}".format(error), file=sys.stderr)
        return []


def queue_ack(account: str, queue_id: str, lease_ids: list) -> None:
    if not lease_ids:
        return
    url = QUEUE_BASE.format(acct=account, qid=queue_id) + "/messages/ack"
    body = json.dumps({"acks": [{"lease_id": lid} for lid in lease_ids]}).encode()
    req = urllib.request.Request(url, data=body, headers=_headers(), method="POST")
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except Exception as error:
        print("ack error: {}".format(error), file=sys.stderr)


def r2_put(key: str, data: bytes) -> None:
    """Upload via wrangler r2 (uses ambient Cloudflare login on VPS)."""
    import subprocess
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    try:
        subprocess.run(["npx", "wrangler", "r2", "object", "put",
                        "harvy/" + key, "--file", tmp_path, "--remote"],
                       cwd=str(PROJECT_ROOT), check=True, capture_output=True)
    finally:
        os.unlink(tmp_path)


def d1_exec(sql: str, params: list) -> None:
    import subprocess
    cmd = ["npx", "wrangler", "d1", "execute", "harvy", "--remote",
           "--command", sql, "--json"]
    for _ in params:
        pass  # params are inlined below; wrangler CLI has no bind flags
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True, capture_output=True)


def upload_channel(handle: str, base: str = OUT_ROOT) -> dict:
    """PUT one JSON per message to R2 under raw/telegram/<handle>/messages/."""
    prefix = "raw/telegram/" + handle.lstrip("@") + "/"
    keys = []
    for name in ("channel.json", "checkpoint.json",
                 "scheduled.json", "admin_log.json"):
        path = Path(base) / handle / name
        if path.exists():
            r2_put(prefix + name, path.read_bytes())
            keys.append(prefix + name)
    messages_dir = Path(base) / handle / "messages"
    if messages_dir.is_dir():
        for msg_file in sorted(messages_dir.glob("*.json")):
            key = prefix + "messages/" + msg_file.name
            r2_put(key, msg_file.read_bytes())
            keys.append(key)
    manifest = Path(base) / handle / "media" / "manifest.json"
    if manifest.exists():
        r2_put(prefix + "media/manifest.json", manifest.read_bytes())
        keys.append(prefix + "media/manifest.json")
    profiles = Path(base) / handle / "media" / "profiles"
    if profiles.is_dir():
        for photo in profiles.glob("*.jpg"):
            r2_put(prefix + "media/profiles/" + photo.name, photo.read_bytes())
            keys.append(prefix + "media/profiles/" + photo.name)
    # Local posts.json export (convenience only, not canonical).
    posts_path = Path(base) / handle / "posts.json"
    if posts_path.exists():
        r2_put(prefix + "posts.json", posts_path.read_bytes())
        keys.append(prefix + "posts.json")
    return {"keys": keys, "count": len(keys)}


def d1_upsert(handle: str, job_id: str, base: str = OUT_ROOT) -> None:
    """Upsert channel object + one observation row per message into D1."""
    import subprocess
    channel = json.loads((Path(base) / handle / "channel.json").read_text())
    messages_dir = Path(base) / handle / "messages"
    msg_files = sorted(messages_dir.glob("*.json")) if messages_dir.is_dir() else []
    now = int(time.time())
    obj_id = "telegram:{}".format(handle.lstrip("@").lower())
    statements = [
        "INSERT OR REPLACE INTO harvy_objects (id, type_id, display_name, canonical_url, attributes_json, created_at, updated_at) "
        "VALUES ('{}', 'telegram_channel', {}, '{}', '{}', {}, {});".format(
            obj_id.replace("'", "''"),
            json.dumps(channel.get("title") or handle).replace("'", "''"),
            ("https://t.me/" + handle.lstrip("@")).replace("'", "''"),
            json.dumps({"channel_id": channel.get("id"),
                        "participants": channel.get("participants")}).replace("'", "''"),
            channel.get("created_at_epoch", now), now),
    ]
    for msg_file in msg_files:
        try:
            msg = json.loads(msg_file.read_text())
        except Exception:
            continue
        msg_id = msg.get("id")
        if msg_id is None:
            continue
        statements.append(
            "INSERT OR REPLACE INTO harvy_observations (id, object_id, environment_id, source, job_id, r2_object_key, content_sha256, data_json, observed_at, created_at) "
            "VALUES ('{}', '{}', 'shared', 'telegram_mtproto', '{}', '{}', '{}', '{}', {}, {});".format(
                ("tg-{}-{}".format(obj_id, msg_id)).replace("'", "''"),
                obj_id.replace("'", "''"),
                (job_id or "").replace("'", "''"),
                ("raw/telegram/" + handle.lstrip("@") + "/messages/" + str(msg_id) + ".json").replace("'", "''"),
                hashlib.sha256(msg_file.read_bytes()).hexdigest(),
                json.dumps({"message_id": msg_id,
                            "unixtime": msg.get("unixtime"),
                            "views": msg.get("views")}).replace("'", "''"),
                msg.get("unixtime") or now, now))
    for sql in statements:
        subprocess.run(["npx", "wrangler", "d1", "execute", "harvy",
                        "--remote", "--command", sql],
                       cwd=str(PROJECT_ROOT), check=True, capture_output=True)


async def run_batch(slot: dict, messages: list, delay: float, base: str) -> list:
    done_lease_ids = []
    for msg in messages:
        lease_id = msg.get("lease_id") or msg.get("id")
        try:
            body = msg.get("body")
            envelope = json.loads(body) if isinstance(body, str) else (body or {})
        except Exception:
            envelope = {}
        channel = envelope.get("channel") or envelope.get("handle") or ""
        job_id = envelope.get("job_id", "")
        if not channel:
            queue_ack(os.environ["CF_ACCOUNT_ID"],
                      os.environ["TELEGRAM_QUEUE_ID"], [lease_id])
            continue
        try:
            result = await mine_channel(channel, slot, envelope.get("limit", 0),
                                        delay, base, include_members=False)
        except Exception as error:
            print(json.dumps({"handle": channel, "status": "error",
                              "error": str(error)}))
            continue  # no ack -> reappears after visibility timeout
        status = result.get("status")
        if status in ("flood_wait", "error"):
            print(json.dumps(result))
            continue  # no ack -> retry later
        handle = result.get("handle", channel)
        try:
            upload = upload_channel(handle, base)
            d1_upsert(handle, job_id, base)
            print(json.dumps({"handle": handle, "status": "mined_uploaded",
                              "posts": result.get("posts"),
                              "r2_keys": upload["count"]}))
        except Exception as error:
            print(json.dumps({"handle": handle, "status": "upload_failed",
                              "error": str(error)}))
            continue
        done_lease_ids.append(lease_id)
    return done_lease_ids


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Telegram queue consumer (VPS)")
    parser.add_argument("--batch", type=int, default=50)
    parser.add_argument("--slot", default="1")
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--base", default=OUT_ROOT)
    parser.add_argument("--once", action="store_true",
                        help="Pull one batch and exit (for cron/systemd).")
    args = parser.parse_args(argv)

    account = os.environ.get("CF_ACCOUNT_ID", "")
    queue_id = os.environ.get("TELEGRAM_QUEUE_ID", "")
    if not account or not queue_id:
        print("Error: set CF_ACCOUNT_ID and TELEGRAM_QUEUE_ID", file=sys.stderr)
        return 1
    slots = {s["slot"]: s for s in account_slots()}
    slot = slots.get(args.slot) or slots.get("1")
    if not slot:
        print("Error: set TELEGRAM_1_API_ID/TELEGRAM_1_API_HASH", file=sys.stderr)
        return 1

    while True:
        messages = queue_pull(account, queue_id, args.batch)
        if not messages:
            print("queue empty, exiting" if args.once else "queue empty, waiting 60s")
            if args.once:
                return 0
            time.sleep(60)
            continue
        done = asyncio.run(run_batch(slot, messages, args.delay, args.base))
        queue_ack(account, queue_id, done)
        if args.once:
            return 0
        time.sleep(5)


if __name__ == "__main__":
    sys.exit(main())
