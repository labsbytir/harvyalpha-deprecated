"""Upload JSON scrape artifacts to a Basin Pipelines HTTP stream."""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import ProxyHandler, Request, build_opener

BATCH_BYTES = 4_000_000  # Basin's hard HTTP ingestion request limit is 5 MB.
CHUNK_BYTES = 1_000_000
INLINE_JSON_BYTES = 2_000_000


def validate_ingest_url(url):
    parsed = urlsplit(url or "")
    if (parsed.scheme != "https" or not parsed.hostname
            or not parsed.hostname.endswith(".ingest.cloudflare.com")
            or parsed.username or parsed.password or parsed.path not in ("", "/")
            or parsed.query or parsed.fragment):
        raise ValueError("BASIN_INGEST_URL must be an HTTPS Basin stream endpoint")


def _text_chunks(text, limit=None):
    limit = CHUNK_BYTES if limit is None else limit
    chunk, used = [], 0
    for char in text:
        size = len(char.encode("utf-8"))
        if chunk and used + size > limit:
            yield "".join(chunk)
            chunk, used = [], 0
        chunk.append(char)
        used += size
    if chunk:
        yield "".join(chunk)


def _event(file_path, rel_path, job_id, kind, source, target, digest, collected_at,
           payload, chunk_index=0, chunk_count=1):
    event_id = hashlib.sha256(
        (job_id + "\0" + rel_path + "\0" + digest + "\0" + str(chunk_index)).encode()
    ).hexdigest()
    return {
        "event_id": event_id,
        "job_id": job_id,
        "kind": kind,
        "source": source,
        "target": target or "",
        "artifact_path": rel_path,
        "collected_at": collected_at,
        "file_sha256": digest,
        "chunk_index": chunk_index,
        "chunk_count": chunk_count,
        "payload": payload,
    }


def artifact_events(path, relative_path, job_id, kind, source, target=""):
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    collected_at = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()
    try:
        payload = json.loads(raw)
        compact_size = len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        payload = None
        compact_size = len(raw)

    # Keep normal artifacts as structured JSON. Split oversized source payloads
    # into UTF-8 text chunks so a single record cannot exceed Basin's request cap.
    if payload is not None and compact_size <= INLINE_JSON_BYTES:
        yield _event(path, relative_path, job_id, kind, source, target, digest, collected_at, payload)
        return

    text = raw.decode("utf-8", errors="replace")
    chunks = list(_text_chunks(text))
    total = len(chunks)
    for index, chunk in enumerate(chunks):
        yield _event(path, relative_path, job_id, kind, source, target, digest, collected_at,
                     {"raw_json_chunk": chunk}, index, total)


def _batches(events, limit=BATCH_BYTES):
    batch = []
    size = 2  # JSON array brackets
    for event in events:
        event_size = len(json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
        added = event_size + (1 if batch else 0)
        if event_size + 2 > limit:
            raise ValueError("Basin event exceeds the configured batch size")
        if batch and size + added > limit:
            yield batch
            batch, size = [], 2
            added = event_size
        batch.append(event)
        size += added
    if batch:
        yield batch


def _send(url, token, proxy, records):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = Request(url, data=json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), headers=headers)
    opener = build_opener(ProxyHandler({"https": proxy, "http": proxy})) if proxy else build_opener()
    for attempt in range(3):
        try:
            with opener.open(request, timeout=60) as response:
                if response.status not in (200, 202, 204):
                    raise RuntimeError("Basin ingestion returned HTTP {}".format(response.status))
                return
        except HTTPError as error:
            if error.code in (429, 500, 502, 503, 504) and attempt < 2:
                retry = error.headers.get("Retry-After", "2")
                time.sleep(min(30, int(retry)) if retry.isdigit() else 2)
                continue
            raise RuntimeError("Basin ingestion failed (HTTP {}).".format(error.code)) from None
        except URLError:
            if attempt < 2:
                time.sleep(2)
                continue
            raise RuntimeError("Could not connect to Basin ingestion.") from None


def upload_files(files, root, *, endpoint, token="", proxy="", job_id="backfill", kind="backfill", source="local"):
    validate_ingest_url(endpoint)
    files = list(files)
    root = Path(root).resolve()
    def iter_events():
        for path in files:
            rel = Path(path).resolve().relative_to(root).as_posix()
            path_source = rel.split("/", 1)[0] or source
            yield from artifact_events(path, rel, job_id, kind, path_source)
    events = iter_events()
    sent_events = batches = 0
    for batch in _batches(events):
        _send(endpoint, token, proxy, batch)
        sent_events += len(batch)
        batches += 1
    return {"files": len(files), "events": sent_events, "batches": batches}


def upload_directory(output, *, endpoint, token="", proxy="", job_id="", kind="scrape", target=""):
    root = Path(output).resolve()
    paths = [p for p in sorted(root.rglob("*.json")) if p.is_file() and not p.is_symlink() and root in p.resolve().parents]
    source = urlsplit(target).hostname or ("whatsmyname" if kind == "username" else kind)
    events = (
        event
        for path in paths
        for event in artifact_events(path, path.relative_to(root).as_posix(), job_id, kind, source, target)
    )
    sent_events = batches = 0
    for batch in _batches(events):
        _send(endpoint, token, proxy, batch)
        sent_events += len(batch)
        batches += 1
    return {"files": len(paths), "events": sent_events, "batches": batches}


def basin_configured():
    return bool(os.environ.get("BASIN_INGEST_URL"))
