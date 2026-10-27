"""Single Telegram adapter: discover, preview, and MTProto mining.

Subcommands:
  discover --source combot|tgstat --out data/telegram_channels.json
  preview @handle (Spider Unlimited public web preview, no MTProto)
  mine @handle [...] (Telethon MTProto on VPS; needs TELEGRAM_<n>_* env)
  enqueue @handle [...] (print queue envelopes for Cloudflare Queue)

Bucket tree (one JSON per message):
  data/telegram/@<channel>/channel.json
  data/telegram/@<channel>/messages/<id>.json
  data/telegram/@<channel>/posts.json (local convenience export only)
  data/telegram/@<channel>/checkpoint.json
  data/telegram/@<channel>/scheduled.json
  data/telegram/@<channel>/admin_log.json
  data/telegram/@<channel>/media/manifest.json
  data/telegram/@<channel>/media/profiles/<sender_id>_<photo_id>.jpg
  data/telegram/index.json

Data-loss rules:
  - All JSON writes are atomic (tmp file + os.replace).
  - Saved posts are never replaced with an empty list; refreshes merge
    by message id and keep the newest record per id.
  - Unavailable channels update availability fields in channel.json only.
  - History is marked exhausted only after an empty page during
    uninterrupted backward pagination. Server counts are diagnostic.

Chat attachments are metadata-only (type + message id). Sender profile
photos are downloaded once per user/photo id, scanned locally with
NudeNet unless HARVY_NSFW_SCAN=false, retained when approved, deleted
when flagged or when scanning fails closed.
"""
import argparse
import asyncio
import json
import os
import re
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


OUT_ROOT = "data/telegram"
RATE_LIMIT_DELAY = 1.05

from v2.media_safety import scan_image_file


COMBOT_TOP_GROUPS_EN = "https://combot.org/top/telegram/groups/en"
TGSTAT_RATINGS_CHANNELS = "https://tgstat.com/ratings/channels"
TGSTAT_RATINGS_CHATS = "https://tgstat.com/ratings/chats"

FEATURE_STATES = ("complete", "partial", "permission_denied", "failed", "not_requested")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean_handle(username: str) -> str:
    return username.strip().lstrip("@").lower()


def channel_dir(base: str, username: str) -> Path:
    return Path(base) / ("@" + clean_handle(username))


def _json_default(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        try:
            return bytes(value).decode("utf-8")
        except Exception:
            return bytes(value).hex()
    return str(value)


def atomic_write_json(path: Path, obj: Any) -> None:
    """Write JSON atomically: tmp file in same dir + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, indent=2, default=_json_default)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def merge_posts(existing: List[Dict[str, Any]],
                incoming: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge post lists by message id, newest record wins, sorted ascending."""
    by_id: Dict[Any, Dict[str, Any]] = {}
    for post in existing:
        by_id[post.get("id")] = post
    for post in incoming:
        old = by_id.get(post.get("id"))
        if old is None:
            by_id[post.get("id")] = post
            continue
        # Newest record wins: prefer the one with later edit/fetch time.
        old_ts = old.get("edit_unixtime") or old.get("fetched_unixtime") or 0
        new_ts = post.get("edit_unixtime") or post.get("fetched_unixtime") or 0
        if new_ts >= old_ts:
            by_id[post.get("id")] = post
    merged = [post for key, post in by_id.items() if key is not None]
    merged.sort(key=lambda item: item.get("id") or 0)
    return merged


def extract_reactions(message: Any) -> Tuple[List[Dict[str, Any]], Dict[str, int]]:
    """Extract reactions preserving custom-emoji ids. Never raises."""
    reactions: List[Dict[str, Any]] = []
    try:
        results = getattr(getattr(message, "reactions", None), "results", None)
        for reaction in results or []:
            inner = getattr(reaction, "reaction", None)
            emoji = getattr(inner, "emoticon", None)
            custom_id = getattr(inner, "document_id", None)
            reactions.append({"emoji": emoji, "custom_emoji_id": custom_id,
                              "count": getattr(reaction, "count", 0)})
    except Exception:
        pass
    counts = {item["emoji"]: item["count"] for item in reactions if item.get("emoji")}
    return reactions, counts


def extract_poll(message: Any) -> Optional[Dict[str, Any]]:
    """Extract poll question/answers from message.poll or message.media shapes."""
    poll_obj = getattr(message, "poll", None)
    media_poll = getattr(getattr(message, "media", None), "poll", None)
    poll = poll_obj if poll_obj is not None else media_poll
    if poll is None:
        return None
    try:
        inner = getattr(poll, "poll", poll)
        question = getattr(inner, "question", "")
        if hasattr(question, "text"):
            question = question.text
        answers = []
        for opt in getattr(inner, "answers", []) or []:
            text = getattr(opt, "text", "")
            if hasattr(text, "text"):
                text = text.text
            option = getattr(opt, "option", None)
            if isinstance(option, (bytes, bytearray)):
                try:
                    option = bytes(option).decode("utf-8")
                except Exception:
                    option = bytes(option).hex()
            answers.append({"text": str(text),
                            "option": option,
                            "voters": getattr(opt, "voters", None)})
        results = getattr(poll, "results", None)
        total = getattr(results, "total_voters", None) if results else None
        return {"question": str(question), "answers": answers, "total_voters": total}
    except Exception as error:
        return {"error": str(error)}


def extract_entities(message: Any) -> List[Dict[str, Any]]:
    """Preserve full entity spans including custom-emoji document ids."""
    entities: List[Dict[str, Any]] = []
    for entity_obj in getattr(message, "entities", None) or []:
        record: Dict[str, Any] = {"type": type(entity_obj).__name__,
                                  "offset": getattr(entity_obj, "offset", None),
                                  "length": getattr(entity_obj, "length", None)}
        doc_id = getattr(entity_obj, "document_id", None)
        if doc_id is not None:
            record["document_id"] = doc_id
        url = getattr(entity_obj, "url", None)
        if url is not None:
            record["url"] = url
        entities.append(record)
    return entities


def extract_telegram_links(text: str) -> Set[str]:
    """Extract and canonicalize t.me invite/channel URLs from text."""
    if not text:
        return set()
    pattern = r"https?://t\.me/(?:joinchat/[a-zA-Z0-9_-]+|\+[a-zA-Z0-9_-]+|[a-zA-Z0-9_]{4,})"
    cleaned = set()
    for match in re.findall(pattern, text or ""):
        lower = match.lower()
        if lower.endswith((".png", ".jpg", ".jpeg", ".svg", ".css", ".js")):
            continue
        cleaned.add(match)
    return cleaned


def discover_combot(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Deprecated: Spider Telegram integration disabled; runs on VPS via MTProto."""
    return {"source": "combot", "total_unique_links": 0, "links": [], "error": "Spider Telegram disabled"}


def discover_tgstat(*args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Deprecated: Spider Telegram integration disabled; runs on VPS via MTProto."""
    return {"source": "tgstat", "total_unique_links": 0, "links": [], "error": "Spider Telegram disabled"}


def preview_channel(username: str, *args: Any, **kwargs: Any) -> Dict[str, Any]:
    """Deprecated: Spider Telegram integration disabled; runs on VPS via MTProto."""
    handle = clean_handle(username)
    return {"handle": "@" + handle, "url": "https://t.me/" + handle, "posts": [], "error": "Spider Telegram disabled"}


def parse_channel_posts(html: str) -> List[Dict[str, Any]]:
    """Parse t.me/s/ message blocks into structured posts."""
    posts: List[Dict[str, Any]] = []
    blocks = re.findall(
        r'<div class="tgme_widget_message\b[^"]*"[^>]*data-post="([^"]+)"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL)
    for post_attr, block in blocks:
        parts = post_attr.split("/")
        post_id = int(parts[-1]) if len(parts) > 1 and parts[-1].isdigit() else None
        dt_match = re.search(r'<time[^>]*datetime="([^"]+)"', block)
        text_match = re.search(r'class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        raw_text = text_match.group(1) if text_match else ""
        views_match = re.search(r'class="tgme_widget_message_views[^"]*"[^>]*>(.*?)</span>', block)
        posts.append({
            "post_id": post_id,
            "datetime": dt_match.group(1) if dt_match else None,
            "text": re.sub(r"<[^>]+>", " ", raw_text).strip(),
            "views": views_match.group(1).strip() if views_match else None,
            "links": [link for link in re.findall(r'href="([^"]+)"', raw_text) if not link.startswith("tg://")],
        })
    return posts


def split_posts_file(channel_dir: Path) -> int:
    """Split legacy posts.json into messages/<id>.json (one per message)."""
    posts_path = channel_dir / "posts.json"
    messages_dir = channel_dir / "messages"
    if not posts_path.exists():
        return 0
    try:
        saved = json.loads(posts_path.read_text(encoding="utf-8"))
    except Exception:
        return 0
    posts = saved.get("posts", []) if isinstance(saved, dict) else []
    count = 0
    for post in posts:
        msg_id = post.get("id")
        if msg_id is None:
            continue
        atomic_write_json(messages_dir / "{}.json".format(msg_id), post)
        count += 1
    return count


def mark_unavailable(base: str, username: str, reason: str) -> Dict[str, Any]:
    """Tombstone a dead/private channel. Never touches saved posts."""
    handle = "@" + clean_handle(username)
    directory = Path(base) / handle
    directory.mkdir(parents=True, exist_ok=True)
    meta = load_json(directory / "channel.json", {})
    if not isinstance(meta, dict):
        meta = {}
    meta.update({"handle": handle, "type": "unavailable",
                 "availability": "unavailable", "unavailable_reason": reason,
                 "last_checked_at": utcnow()})
    atomic_write_json(directory / "channel.json", meta)
    update_index(base, handle, meta, None)
    return {"handle": handle, "status": "unavailable", "reason": reason}


def update_index(base: str, handle: str, meta: Dict[str, Any],
                 posts_count: Optional[int]) -> None:
    index_path = Path(base) / "index.json"
    registry: Dict[str, Any] = load_json(
        index_path, {"updated_at": utcnow(), "total_channels": 0, "channels": {}})
    if not isinstance(registry.get("channels"), dict):
        registry["channels"] = {}
    entry = registry["channels"].get(handle, {})
    entry.update({"title": meta.get("title"), "type": meta.get("type"),
                  "availability": meta.get("availability", "available"),
                  "last_scraped_at": utcnow()})
    if posts_count is not None:
        entry["posts_scraped"] = posts_count
    registry["channels"][handle] = entry
    registry["total_channels"] = len(registry["channels"])
    registry["updated_at"] = utcnow()
    atomic_write_json(index_path, registry)


def account_slots() -> List[Dict[str, str]]:
    """Read TELEGRAM_<n>_API_ID/HASH/SESSION slots (two VPS accounts)."""
    slots = []
    for num in ("1", "2", ""):
        api_id = os.environ.get("TELEGRAM_" + num + "_API_ID" if num else "TELEGRAM_API_ID")
        api_hash = os.environ.get("TELEGRAM_" + num + "_API_HASH" if num else "TELEGRAM_API_HASH")
        session = os.environ.get("TELEGRAM_" + num + "_SESSION" if num else "TELEGRAM_SESSION",
                                 "harvy" + num if num else "harvy")
        if api_id and api_hash:
            slots.append({"slot": num or "1", "api_id": api_id, "api_hash": api_hash, "session": session})
    return slots


async def mine_channel(username: str, slot: Dict[str, str], limit: int, delay: float,
                       base: str = OUT_ROOT, include_members: bool = False) -> Dict[str, Any]:
    """Mine channel/group history via Telethon MTProto.

    Captures: raw text + entities, timestamps, ids, views/forwards,
    reactions + counts, polls, sender name/handle/id, member count,
    creation date, admins/bots where account permission allows,
    scheduled posts, sender bios/statuses, admin logs (all permission-gated).

    Writes are atomic; refreshes merge by message id. History is marked
    exhausted only after an empty page during uninterrupted backward
    pagination (all history accessible to this account, not a guarantee
    of every message ever posted).
    """
    from telethon import TelegramClient
    from telethon.errors import (ChannelPrivateError, FloodWaitError, UsernameInvalidError,
                                 UsernameNotOccupiedError)
    from telethon.tl.functions.channels import GetFullChannelRequest, GetParticipantsRequest
    from telethon.tl.functions.messages import GetHistoryRequest, GetScheduledHistoryRequest
    from telethon.tl.functions.users import GetFullUserRequest
    from telethon.tl.types import ChannelParticipantsAdmins, ChannelParticipantsBots

    handle = "@" + clean_handle(username)
    directory = Path(base) / handle
    checkpoint_path = directory / "checkpoint.json"
    checkpoint = load_json(checkpoint_path, {})

    client = TelegramClient(slot["session"], int(slot["api_id"]), slot["api_hash"])
    await client.start()
    try:
        try:
            entity = await client.get_entity(handle.lstrip("@"))
        except (UsernameNotOccupiedError, UsernameInvalidError):
            return {**mark_unavailable(base, handle, "not_found"), "slot": slot["slot"]}
        except ChannelPrivateError:
            return {**mark_unavailable(base, handle, "private_no_access"), "slot": slot["slot"]}

        features: Dict[str, str] = {}
        channel_id = getattr(entity, "id", None)

        try:
            full = await client(GetFullChannelRequest(entity))
        except ChannelPrivateError:
            return {**mark_unavailable(base, handle, "private_no_access"), "slot": slot["slot"]}
        except Exception as error:
            return {"handle": handle, "status": "error", "error": str(error), "slot": slot["slot"]}
        full_chat = full.full_chat
        about = getattr(full_chat, "about", "") or ""
        created = getattr(entity, "date", None)

        meta: Dict[str, Any] = {
            "title": getattr(entity, "title", handle),
            "type": "channel" if getattr(entity, "broadcast", False) else "group",
            "description": about,
            "participants": getattr(full_chat, "participants_count", None),
            "admins_count": getattr(full_chat, "admins_count", None),
            "created_at": created.isoformat() if created else None,
            "id": channel_id,
            "availability": "available",
        }

        # Admins + bots where permission allows
        admins: List[Dict[str, Any]] = []
        bots: List[Dict[str, Any]] = []
        try:
            admin_parts = await client(GetParticipantsRequest(
                entity, ChannelParticipantsAdmins(), 0, 100, 0))
            for user in admin_parts.users or []:
                admins.append({"id": user.id, "username": ("@" + user.username) if user.username else None,
                               "name": ((user.first_name or "") + " " + (user.last_name or "")).strip() or None,
                               "bot": bool(user.bot)})
            bot_parts = await client(GetParticipantsRequest(
                entity, ChannelParticipantsBots(), 0, 100, 0))
            for user in bot_parts.users or []:
                bots.append({"id": user.id, "username": ("@" + user.username) if user.username else None})
            features["admins_bots"] = "complete" if admins or bots else "partial"
        except Exception:
            features["admins_bots"] = "permission_denied"
        meta["admins"] = admins
        meta["bots"] = bots

        # Full member roster — opt-in, groups only, permission-gated.
        members: List[Dict[str, Any]] = []
        if include_members and not getattr(entity, "broadcast", False):
            from telethon.tl.types import ChannelParticipantsSearch
            try:
                offset = 0
                while True:
                    parts = await client(GetParticipantsRequest(
                        entity, ChannelParticipantsSearch(""), offset, 200, 0))
                    users = parts.users or []
                    if not users:
                        break
                    for user in users:
                        members.append({
                            "id": user.id,
                            "username": ("@" + user.username) if user.username else None,
                            "name": ((user.first_name or "") + " " + (user.last_name or "")).strip() or None,
                            "bot": bool(user.bot),
                            "verified": bool(getattr(user, "verified", False)),
                        })
                    offset += len(users)
                    await asyncio.sleep(delay)
                features["members"] = "complete"
            except Exception:
                features["members"] = "permission_denied" if not members else "partial"
        else:
            features["members"] = "not_requested" if not include_members else "permission_denied"
        meta["members"] = members
        meta["members_count"] = len(members) if members else None

        # Resume: start from checkpoint cursor. A stale exhausted flag never
        # skips pagination when saved messages look short vs server count.
        messages_dir = directory / "messages"
        existing_ids: Set[int] = set()
        if messages_dir.is_dir():
            for child in messages_dir.glob("*.json"):
                try:
                    existing_ids.add(int(child.stem))
                except ValueError:
                    continue
        offset_id = checkpoint.get("cursor_offset_id", 0) if limit == 0 else 0
        exhausted_before = checkpoint.get("history_exhausted", False) if limit == 0 else False
        if exhausted_before:
            # Distrust a stale exhausted flag without saved message files.
            if not existing_ids:
                exhausted_before = False
                offset_id = 0
            elif checkpoint.get("expected_total") and len(existing_ids) < checkpoint["expected_total"]:
                exhausted_before = False
                offset_id = min(existing_ids, default=0)

        posts: List[Dict[str, Any]] = []
        media_manifest: List[Dict[str, Any]] = []
        expected_total: Any = None
        sender_cache: Dict[Any, Optional[Dict[str, Any]]] = {}
        pages_mined = 0
        empty_page_seen = False
        interrupted = False

        if not (limit == 0 and exhausted_before):
            while True:
                try:
                    history = await client(GetHistoryRequest(
                        peer=entity, limit=min(100, limit - len(posts)) if limit else 100,
                        offset_date=None, offset_id=offset_id, max_id=0, min_id=0,
                        add_offset=0, hash=0))
                except FloodWaitError as error:
                    interrupted = True
                    atomic_write_json(checkpoint_path, {
                        "channel_id": channel_id, "handle": handle, "slot": slot["slot"],
                        "cursor_offset_id": offset_id, "history_exhausted": False,
                        "pages_mined": pages_mined, "pending": len(posts),
                        "status": "flood_wait", "retry_after": error.seconds,
                        "updated_at": utcnow()})
                    return {"handle": handle, "status": "flood_wait",
                            "retry_after": error.seconds, "slot": slot["slot"]}
                if expected_total is None:
                    expected_total = getattr(history, "count", None)
                messages = history.messages or []
                if not messages:
                    empty_page_seen = True
                    break
                fetched_at = utcnow()
                fetched_uni = int(datetime.now(timezone.utc).timestamp())
                for message in messages:
                    if getattr(message, "id", 0) == 0:
                        continue
                    try:
                        sender = await message.get_sender()
                    except Exception:
                        sender = None
                    sender_id = getattr(sender, "id", None)
                    sender_profile = sender_cache.get(sender_id) if sender_id else None
                    if sender_id and sender_id not in sender_cache:
                        sender_profile = None
                        if hasattr(sender, "first_name"):
                            try:
                                full_user = await client(GetFullUserRequest(sender_id))
                                about_text = getattr(full_user, "about", "") or ""
                                status_obj = getattr(sender, "status", None)
                                status = type(status_obj).__name__ if status_obj else None
                                sender_profile = {
                                    "bio": about_text,
                                    "status": status,
                                    "verified": bool(getattr(sender, "verified", False)),
                                    "bot": bool(getattr(sender, "bot", False)),
                                    "has_photo": bool(getattr(sender, "photo", None)),
                                }
                                sender_profile.update(await maybe_save_profile_photo(
                                    client, sender, directory))
                            except Exception as error:
                                sender_profile = {"error": str(error)}
                        sender_cache[sender_id] = sender_profile
                    reactions, reaction_counts = extract_reactions(message)
                    poll = extract_poll(message)
                    media_info = None
                    if message.media:
                        # Metadata only — chat attachments are never downloaded.
                        media_info = {"type": type(message.media).__name__, "downloaded": False}
                        media_manifest.append({"message_id": message.id, **media_info})
                    posts.append({
                        "id": message.id,
                        "channel_id": channel_id,
                        "channel_handle": handle,
                        "date": message.date.isoformat() if message.date else None,
                        "unixtime": int(message.date.timestamp()) if message.date else None,
                        "text": message.text or "",
                        "raw_text": message.raw_text or "",
                        "entities": extract_entities(message),
                        "views": getattr(message, "views", None),
                        "forwards": getattr(message, "forwards", None),
                        "edit_date": message.edit_date.isoformat() if message.edit_date else None,
                        "edit_unixtime": int(message.edit_date.timestamp()) if message.edit_date else None,
                        "pinned": bool(getattr(message, "pinned", False)),
                        "sender_id": sender_id,
                        "sender_name": getattr(sender, "title", None) or ((getattr(sender, "first_name", "") or "") + " " + (getattr(sender, "last_name", "") or "")).strip() or getattr(sender, "username", None),
                        "sender_username": ("@" + sender.username) if getattr(sender, "username", None) else None,
                        "sender_profile": sender_profile,
                        "post_author": getattr(message, "post_author", None),
                        "reactions": reactions,
                        "reaction_counts": reaction_counts,
                        "poll": poll,
                        "media": media_info,
                        "reply_to": getattr(getattr(message, "reply_to", None), "reply_to_msg_id", None),
                        "fetched_at": fetched_at,
                        "fetched_unixtime": fetched_uni,
                    })
                    # One JSON per message: newest record per id wins.
                    atomic_write_json(messages_dir / "{}.json".format(message.id), posts[-1])
                    existing_ids.add(message.id)
                offset_id = min(getattr(message, "id", offset_id) for message in messages)
                pages_mined += 1
                # Checkpoint after every page so an interrupted run resumes.
                atomic_write_json(checkpoint_path, {
                    "channel_id": channel_id, "handle": handle, "slot": slot["slot"],
                    "cursor_offset_id": offset_id, "history_exhausted": False,
                    "pages_mined": pages_mined, "pending": len(posts),
                    "status": "in_progress", "updated_at": utcnow()})
                if limit and len(posts) >= limit:
                    break
                await asyncio.sleep(delay)

        merged_ids = sorted(existing_ids)
        first_id = merged_ids[0] if merged_ids else None
        last_id = merged_ids[-1] if merged_ids else None
        # Exhausted only on uninterrupted backward pagination ending in an
        # empty page — i.e. all history accessible to this account.
        history_exhausted = bool(empty_page_seen and not interrupted and limit == 0)
        if limit != 0:
            history_exhausted = checkpoint.get("history_exhausted", False)
        count_matches = (expected_total is not None and len(merged_ids) >= expected_total)
        atomic_write_json(checkpoint_path, {
            "channel_id": channel_id, "handle": handle, "slot": slot["slot"],
            "cursor_offset_id": offset_id, "history_exhausted": history_exhausted,
            "pages_mined": pages_mined, "expected_total": expected_total,
            "count_matches": count_matches, "first_id": first_id, "last_id": last_id,
            "status": "complete" if history_exhausted else "partial",
            "updated_at": utcnow()})

        # Scheduled posts (admin/owner permission only)
        scheduled: List[Dict[str, Any]] = []
        try:
            sched_history = await client(GetScheduledHistoryRequest(peer=entity, hash=0))
            for message in sched_history.messages or []:
                scheduled.append({
                    "id": getattr(message, "id", None),
                    "date": message.date.isoformat() if message.date else None,
                    "text": message.text or "",
                })
            features["scheduled"] = "complete"
        except Exception:
            features["scheduled"] = "permission_denied" if not scheduled else "partial"

        # Admin log (admin permission only, paginated, capped at 1000 events)
        admin_log: List[Dict[str, Any]] = []
        try:
            from telethon.tl.functions.channels import GetAdminLogRequest
            from telethon.tl.types import ChannelAdminLogEventsFilter
            max_id = 0
            while len(admin_log) < 1000:
                log = await client(GetAdminLogRequest(
                    entity, "", max_id, 0, 100, ChannelAdminLogEventsFilter(
                        join=False, leave=False, invite=False, ban=False, unban=False,
                        kick=False, unkick=False, promote=False, demote=False,
                        info=False, settings=False, pinned=False, edit=False, delete=False,
                        group_call=False, invites=False, send=False, polls=False)))
                events = log.events or []
                if not events:
                    break
                for event in events:
                    admin_log.append({
                        "id": getattr(event, "id", None),
                        "date": event.date.isoformat() if event.date else None,
                        "user_id": getattr(event, "user_id", None),
                        "action": type(event.action).__name__,
                    })
                max_id = min(getattr(event, "id", 0) for event in events)
                if len(events) < 100:
                    break
            features["admin_log"] = "complete" if admin_log else "partial"
        except Exception:
            features["admin_log"] = "permission_denied" if not admin_log else "partial"

        meta.update({
            "expected_total": expected_total,
            "mined_count": len(merged_ids),
            "first_id": first_id,
            "last_id": last_id,
            "history_exhausted": history_exhausted,
            "count_matches": count_matches,
            "last_mined_at": utcnow(),
            "scheduled_count": len(scheduled),
            "admin_log_count": len(admin_log),
            "features": features,
        })
        # Never write an empty posts list over saved history.
        # Per-message JSON is canonical; posts.json is a local export only.
        posts_to_write = [load_json(messages_dir / "{}.json".format(mid), {})
                          for mid in merged_ids] if merged_ids else []
        posts_to_write = [post for post in posts_to_write if post.get("id") is not None]
        scraped_at = utcnow()
        directory.mkdir(parents=True, exist_ok=True)
        atomic_write_json(directory / "channel.json", {**meta, "scraped_at": scraped_at})
        atomic_write_json(directory / "posts.json", {
            "handle": handle, "total_posts": len(posts_to_write),
            "updated_at": scraped_at, "posts": posts_to_write})
        if scheduled:
            atomic_write_json(directory / "scheduled.json", scheduled)
        if admin_log:
            atomic_write_json(directory / "admin_log.json", admin_log)
        if media_manifest:
            atomic_write_json(directory / "media" / "manifest.json", media_manifest)
        update_index(base, handle, meta, len(posts_to_write))
        return {"handle": handle, "type": meta["type"], "posts": len(posts_to_write),
                "expected_total": expected_total, "first_id": first_id, "last_id": last_id,
                "history_exhausted": history_exhausted, "members": len(members),
                "scheduled": len(scheduled), "admin_log": len(admin_log),
                "admins": len(admins), "bots": len(bots), "slot": slot["slot"]}
    except FloodWaitError as error:
        return {"handle": handle, "status": "flood_wait", "retry_after": error.seconds}
    finally:
        await client.disconnect()
        await asyncio.sleep(delay)


async def maybe_save_profile_photo(client: Any, sender: Any, directory: Path) -> Dict[str, Any]:
    """Download a sender profile photo once, scan locally, retain if approved.

    Returns metadata only. Raw bytes stay on the VPS; flagged images and
    scan failures are deleted (fail closed). Chat attachments are never
    downloaded by this function.
    """
    photo = getattr(sender, "photo", None)
    if not photo:
        return {}
    sender_id = getattr(sender, "id", "unknown")
    photo_id = getattr(photo, "photo_id", None) or getattr(photo, "id", "nophoto")
    profiles_dir = directory / "media" / "profiles"
    dest = profiles_dir / "{}_{}.jpg".format(sender_id, photo_id)
    if dest.exists():
        scan = load_json(dest.with_suffix(".json"), None)
        return {"photo_path": str(dest.relative_to(directory)),
                "photo_nsfw": scan}
    profiles_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(suffix=".jpg", dir=str(profiles_dir))
    os.close(fd)
    try:
        await client.download_profile_photo(sender, file=tmp)
        scan = scan_image_file(tmp)
        if scan is None:
            # Scanning disabled: retain the image, record unscanned state.
            shutil.move(tmp, dest)
            record = {"enabled": False, "available": False,
                      "flagged": False, "note": "nsfw scan disabled"}
            atomic_write_json(dest.with_suffix(".json"), record)
            return {"photo_path": str(dest.relative_to(directory)), "photo_nsfw": record}
        if scan.get("flagged"):
            return {"photo_nsfw": scan}
        shutil.move(tmp, dest)
        atomic_write_json(dest.with_suffix(".json"), scan)
        return {"photo_path": str(dest.relative_to(directory)), "photo_nsfw": scan}
    finally:
        try:
            if os.path.exists(tmp):
                os.unlink(tmp)
        except OSError:
            pass


def make_envelope(job_id: str, username: str, limit: int = 0, slot: str = "1") -> Dict[str, Any]:
    """Cloudflare Queue envelope for a telegram channel mine."""
    handle = "@" + clean_handle(username)
    return {"protocol": 2, "job_id": job_id, "kind": "telegram_channel", "network": "telegram",
            "source": "telegram", "channel": handle, "url": "https://t.me/" + handle.lstrip("@"),
            "limit": limit, "account_slot": slot, "environment_id": "shared"}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Telegram adapter: discover, preview, mine, enqueue")
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Find channels via Combot/TGStat")
    discover.add_argument("--source", choices=["combot", "tgstat"], default="combot")
    discover.add_argument("--pages", type=int, default=20)
    discover.add_argument("--out", default="data/telegram_channels.json")

    preview = sub.add_parser("preview", help="Public web preview via Spider Unlimited")
    preview.add_argument("channels", nargs="+")

    mine = sub.add_parser("mine", help="Full history via Telethon MTProto (VPS)")
    mine.add_argument("channels", nargs="+")
    mine.add_argument("--limit-per-channel", type=int, default=0, help="0 = full history")
    mine.add_argument("--slot", default="1", help="Account slot 1 or 2")
    mine.add_argument("--delay", type=float, default=2.0)
    mine.add_argument("--base", default=OUT_ROOT)
    mine.add_argument("--members", action="store_true",
                      help="Dump full member roster (groups only, permission-gated)")

    split = sub.add_parser("split", help="Split legacy posts.json into messages/<id>.json")
    split.add_argument("channels", nargs="+")
    split.add_argument("--base", default=OUT_ROOT)

    enqueue = sub.add_parser("enqueue", help="Print queue envelopes")
    enqueue.add_argument("channels", nargs="+")
    enqueue.add_argument("--limit-per-channel", type=int, default=0)
    enqueue.add_argument("--slot", default="1")

    args = parser.parse_args(argv)

    if args.command == "enqueue":
        import uuid
        for channel in args.channels:
            print(json.dumps(make_envelope(str(uuid.uuid4()), channel, args.limit_per_channel, args.slot)))
        return 0

    if args.command == "split":
        for channel in args.channels:
            handle = "@" + clean_handle(channel)
            count = split_posts_file(Path(args.base) / handle)
            print(json.dumps({"handle": handle, "split": count}), file=sys.stderr)
        return 0

    if args.command in ("discover", "preview"):
        print("Spider Telegram integration disabled; Telegram collection runs via MTProto on VPS.", file=sys.stderr)
        return 1

    slots = {slot["slot"]: slot for slot in account_slots()}
    slot = slots.get(args.slot) or slots.get("1")
    if not slot:
        print("Error: set TELEGRAM_1_API_ID/TELEGRAM_1_API_HASH (and _2_ for second account)", file=sys.stderr)
        return 1

    async def run_all() -> int:
        results = []
        for channel in args.channels:
            try:
                result = await mine_channel(channel, slot, args.limit_per_channel, args.delay, args.base,
                                            include_members=args.members)
            except Exception as error:
                result = {"handle": channel, "status": "error", "error": str(error)}
            print(json.dumps(result), file=sys.stderr)
            results.append(result)
        failed = [result for result in results if result.get("status") in ("error", "flood_wait")]
        return 1 if failed else 0

    return asyncio.run(run_all())


if __name__ == "__main__":
    sys.exit(main())
