"""Bounded JudyRecords bulk runner: AI search -> link index -> queued Spider scrapes."""
from __future__ import annotations

import contextlib
import hashlib
import json
import re
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, urlparse

from v1.scrape.client import ai as spider_ai, unlimited as spider_unlimited
from v1.scrape.judyrecords import parse_case_page

JUDY_HOSTS = {"judyrecords.com", "www.judyrecords.com"}
RECORD_PATH = re.compile(r"^/record/([a-z0-9]+)/?$", re.I)
DEFAULT_OUT = Path("data/judyrecords-bulk")
AI_SEARCH_SCHEMA = {
    "name": "judyrecords_search_records",
    "description": "Canonical JudyRecords record links returned by the JudyRecords search bar.",
    "schema": {
        "type": "object",
        "properties": {"records": {"type": "array", "items": {"type": "string"}}},
        "required": ["records"],
    },
}
QUEUE_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    url TEXT NOT NULL,
    source_url TEXT NOT NULL,
    status TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    lease_until INTEGER NOT NULL,
    worker TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL,
    error TEXT NOT NULL,
    raw_path TEXT NOT NULL,
    record_path TEXT NOT NULL,
    content_sha256 TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    received_at INTEGER NOT NULL,
    payload_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_status_run ON jobs(run_id, status);
"""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_record_url(value):
    try:
        url = urlparse(value)
    except ValueError:
        return None
    if url.scheme != "https" or url.hostname not in JUDY_HOSTS or url.username or url.password:
        return None
    match = RECORD_PATH.match(url.path)
    if not match:
        return None
    return "https://www.judyrecords.com/record/" + match.group(1).lower()


def is_judy_seed(value):
    try:
        url = urlparse(value)
    except ValueError:
        return False
    return url.scheme == "https" and url.hostname in JUDY_HOSTS and not url.username and url.password is None


def extract_record_urls(value, output=None):
    found = output if output is not None else []
    if isinstance(value, str):
        for candidate in re.findall(r"https?://[^\s\"'<>\\]+", value):
            record_url = canonical_record_url(candidate.rstrip("),.;"))
            if record_url and record_url not in found:
                found.append(record_url)
    elif isinstance(value, list):
        for item in value:
            extract_record_urls(item, found)
    elif isinstance(value, dict):
        for item in value.values():
            extract_record_urls(item, found)
    return found


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = max(0.0, float(min_interval))
        self._lock = threading.Lock()
        self._next_at = 0.0

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = max(0.0, self._next_at - now)
            self._next_at = max(now, self._next_at) + self.min_interval
        if delay:
            time.sleep(delay)


class BulkQueue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        with self._lock:
            self._conn.executescript(QUEUE_SCHEMA)
            self._conn.commit()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def enqueue_batch(self, items) -> int:
        inserted = 0
        with self._lock, self._conn:
            for item in items:
                cursor = self._conn.execute(
                    "INSERT OR IGNORE INTO jobs (id, run_id, url, source_url, status, attempts, lease_until, worker, created_at, updated_at, error, raw_path, record_path, content_sha256) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item["id"], item["run_id"], item["url"], item["source_url"], item.get("status", "queued"),
                        int(item.get("attempts", 0)), int(item.get("lease_until", 0)), item.get("worker", ""),
                        int(item.get("created_at", int(time.time()))), int(item.get("updated_at", int(time.time()))),
                        item.get("error", ""), item.get("raw_path", ""), item.get("record_path", ""), item.get("content_sha256", ""),
                    ),
                )
                inserted += max(0, cursor.rowcount)
        return inserted

    def claim_batch(self, worker: str, batch_size: int, run_id: str | None = None, lease_seconds: int = 300):
        now = int(time.time())
        with self._lock:
            query = "SELECT * FROM jobs WHERE (status = 'queued' OR (status = 'processing' AND lease_until <= ?))"
            params = [now]
            if run_id:
                query += " AND run_id = ?"
                params.append(run_id)
            query += " ORDER BY created_at, id LIMIT ?"
            params.append(max(1, int(batch_size)))
            rows = self._conn.execute(query, params).fetchall()
            ids = [row["id"] for row in rows]
            if ids:
                self._conn.executemany(
                    "UPDATE jobs SET status = 'processing', lease_until = ?, worker = ?, attempts = attempts + 1, updated_at = ? WHERE id = ?",
                    [(now + int(lease_seconds), worker, now, job_id) for job_id in ids],
                )
            self._conn.commit()
        result = []
        for row in rows:
            data = dict(row)
            data["status"] = "processing"
            data["lease_until"] = now + int(lease_seconds)
            data["worker"] = worker
            data["attempts"] = int(row["attempts"]) + 1
            result.append(data)
        return result

    def complete(self, job_id: str, raw_path: str, record_path: str, content_sha256: str) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE jobs SET status = 'complete', lease_until = 0, error = '', raw_path = ?, record_path = ?, content_sha256 = ?, updated_at = ? WHERE id = ?",
                (raw_path, record_path, content_sha256, int(time.time()), job_id),
            )

    def retry_or_fail(self, job_id: str, error: str, max_attempts: int) -> str:
        with self._lock, self._conn:
            row = self._conn.execute("SELECT attempts FROM jobs WHERE id = ?", (job_id,)).fetchone()
            attempts = int(row["attempts"]) if row else 0
            status = "failed" if attempts >= max(1, int(max_attempts)) else "queued"
            self._conn.execute(
                "UPDATE jobs SET status = ?, lease_until = 0, error = ?, updated_at = ? WHERE id = ?",
                (status, error[:300], int(time.time()), job_id),
            )
        return status

    def counts(self, run_id: str | None = None):
        query = "SELECT status, COUNT(*) AS count FROM jobs"
        params = []
        if run_id:
            query += " WHERE run_id = ?"
            params.append(run_id)
        query += " GROUP BY status"
        with self._lock:
            rows = self._conn.execute(query, params).fetchall()
        return {row["status"]: int(row["count"]) for row in rows}

    def record_event(self, payload) -> None:
        event_id = hashlib.sha256((utc_now() + "\0" + json.dumps(payload, sort_keys=True)).encode("utf-8")).hexdigest()
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO events (id, received_at, payload_json) VALUES (?, ?, ?)",
                (event_id, int(time.time()), json.dumps(payload, ensure_ascii=False)),
            )

    def event_count(self) -> int:
        with self._lock:
            row = self._conn.execute("SELECT COUNT(*) AS count FROM events").fetchone()
        return int(row["count"]) if row else 0


class _WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):  # noqa: N802 - stdlib handler name
        if not self.path.startswith(self.server.token_path):
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(min(length, 1_000_000)) if length else b""
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except (UnicodeDecodeError, json.JSONDecodeError):
            payload = {"raw": body.decode("utf-8", "replace")[:1000]}
        self.server.queue.record_event(payload)
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):  # keep bulk logs single-line JSON from the runner
        return


def start_webhook_listener(queue: BulkQueue, token: str, listen: str = "127.0.0.1:0"):
    host, _, port = listen.partition(":")
    server = ThreadingHTTPServer((host, int(port or "0")), _WebhookHandler)
    server.queue = queue
    server.token_path = "/spider-webhook/" + token
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    return server, server.token_path


def ai_search_judyrecords(query, key, proxy, rate_limiter: RateLimiter, limit=50, webhook=None, ai_lock=None):
    rate_limiter.wait()
    if ai_lock:
        ai_lock.acquire()
    try:
        prompt = (
            "Use the JudyRecords search bar at https://www.judyrecords.com/ to search for "
            + json.dumps(query)
            + ". Submit the search, wait for results, and return only canonical "
            "https://www.judyrecords.com/record/<id> links as {\"records\": [...]}."
        )
        payload = {
            "url": "https://www.judyrecords.com/",
            "prompt": prompt,
            "request": "browser",
            "return_format": "raw",
            "metadata": True,
            "cache": False,
            "limit": max(1, int(limit)),
            "extraction_schema": AI_SEARCH_SCHEMA,
        }
        if webhook:
            payload["webhook"] = webhook
        result, _ = spider_ai("browser", payload, key, proxy)
        return extract_record_urls(result)
    finally:
        if ai_lock:
            ai_lock.release()


def discover_record_urls(seed, mode, key, proxy, limit, semaphore, webhook=None):
    payload = {"url": seed, "limit": max(1, int(limit)), "request": "http", "cache": False, "metadata": True}
    if mode == "crawl":
        payload["depth"] = 1
    if webhook:
        payload["webhook"] = webhook
    with semaphore or contextlib.nullcontext():
        result, headers = spider_unlimited(mode, payload, key, proxy)
    return extract_record_urls(result), headers


def validate_page(pages):
    if not isinstance(pages, list) or not pages:
        return False, "empty Spider response", ""
    page = next((item for item in pages if isinstance(item, dict) and item.get("status") == 200 and not item.get("error") and item.get("content")), None)
    if not page:
        return False, "no successful Spider page", ""
    html = str(page.get("content") or "")
    if len(html) < 200:
        return False, "page content too small", html
    if not re.search(r"<html|oscn-content|record page|caseInformationDiv", html, re.I):
        return False, "page does not look like a JudyRecords record", html
    return True, "", html


def build_record(html: str, record_url: str, proxy_requested: bool):
    data = parse_case_page(html, record_url)
    complete = bool(data.get("case_number") and data.get("case_type"))
    limitations = []
    if not data.get("case_number"):
        limitations.append("No case number extracted")
    if not data.get("case_type"):
        limitations.append("No case type extracted")
    record_id = canonical_record_url(record_url).rsplit("/", 1)[-1]
    return {
        "schema_version": 1,
        "connector": "judyrecords",
        "record_id": record_id,
        "source_url": record_url,
        "collected_at": utc_now(),
        "parser_version": "1.0.0",
        "complete": complete,
        "limitations": limitations,
        "provenance": {"method": "spider_unlimited_scrape", "proxy_requested": proxy_requested},
        "data": data,
    }


def store_record(out_dir, run_id: str, job, html: str, record):
    base = Path(out_dir) / run_id
    raw_path = base / "raw" / (record["record_id"] + ".html")
    record_path = base / "records" / (record["record_id"] + ".json")
    write_text_atomic(raw_path, html)
    write_text_atomic(record_path, json.dumps(record, indent=2, ensure_ascii=False))
    return raw_path, record_path, sha256_bytes(record_path.read_bytes())


def process_job(job, key, proxy, out_dir, queue: BulkQueue, webhook=None, max_attempts=5, semaphore=None):
    try:
        payload = {
            "url": job["url"],
            "request": "http",
            "return_format": "raw",
            "metadata": True,
            "cache": False,
        }
        if webhook:
            payload["webhook"] = webhook
        with semaphore or contextlib.nullcontext():
            pages, _ = spider_unlimited("scrape", payload, key, proxy)
        ok, reason, html = validate_page(pages)
        if not ok:
            status = queue.retry_or_fail(job["id"], reason, max_attempts)
            return {"job_id": job["id"], "url": job["url"], "status": status, "error": reason}
        record = build_record(html, job["url"], bool(proxy))
        raw_path, record_path, content_sha256 = store_record(out_dir, job["run_id"], job, html, record)
        queue.complete(job["id"], str(raw_path), str(record_path), content_sha256)
        return {
            "job_id": job["id"],
            "url": job["url"],
            "status": "complete",
            "record_id": record["record_id"],
            "complete": record["complete"],
            "raw_path": str(raw_path),
            "record_path": str(record_path),
            "sha256": content_sha256,
        }
    except Exception as error:
        status = queue.retry_or_fail(job["id"], type(error).__name__ + ": " + str(error)[:240], max_attempts)
        return {"job_id": job["id"], "url": job["url"], "status": status, "error": type(error).__name__}


def _job_item(run_id: str, url: str, source_url: str):
    return {
        "id": hashlib.sha256((run_id + "\0" + url).encode("utf-8")).hexdigest(),
        "run_id": run_id,
        "url": url,
        "source_url": source_url,
        "status": "queued",
        "attempts": 0,
        "lease_until": 0,
        "worker": "",
        "created_at": int(time.time()),
        "updated_at": int(time.time()),
        "error": "",
        "raw_path": "",
        "record_path": "",
        "content_sha256": "",
    }


def run_bulk(*, key, proxy, out_dir=DEFAULT_OUT, target=10, concurrency=3, batch_size=50,
             enqueue_batch=500, queries=(), seeds=(), discovery_mode="links", limit_per_query=50,
             ai_per_second=1.0, max_attempts=5, lease_seconds=300, rounds=1, run_id=None,
             webhook_listen=None, webhook_url=None, webhook_token=None, progress_every=100,
             allow_partial=False, stop_event=None):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    semaphore = threading.BoundedSemaphore(max(1, int(concurrency)))
    ai_rate = RateLimiter(ai_per_second)
    ai_lock = threading.Lock()
    summaries = []
    for round_index in range(1, max(1, int(rounds)) + 1):
        current_run_id = run_id if (rounds == 1 and run_id) else "{}-{}-{}".format(run_id or "judy", round_index, uuid.uuid4().hex[:8])
        queue = BulkQueue(out_dir / (current_run_id + ".sqlite3"))
        server = None
        webhook = None
        if webhook_listen and webhook_token:
            server, token_path = start_webhook_listener(queue, webhook_token, webhook_listen)
            if webhook_url:
                webhook = {"url": webhook_url, "on_find": True, "on_website_status": True}
            elif not webhook_listen.startswith(("127.0.0.1", "localhost")):
                webhook = {"url": "http://" + webhook_listen.rstrip("/") + token_path, "on_find": True, "on_website_status": True}
            else:
                print(json.dumps({"run_id": current_run_id, "warning": "webhook listener is local; set --webhook-url for Spider delivery"}))
        discovery_done = threading.Event()
        stop = threading.Event()
        workers = []

        def worker_loop(worker_id):
            processed = 0
            while not stop.is_set() and not (stop_event and stop_event.is_set()):
                jobs = queue.claim_batch(worker_id, batch_size, current_run_id, lease_seconds)
                if not jobs:
                    counts = queue.counts(current_run_id)
                    if discovery_done.is_set() and counts.get("queued", 0) == 0 and counts.get("processing", 0) == 0:
                        break
                    if counts.get("complete", 0) >= target and counts.get("queued", 0) == 0 and counts.get("processing", 0) == 0:
                        break
                    time.sleep(0.1)
                    continue
                for job in jobs:
                    process_job(job, key, proxy, out_dir, queue, webhook=webhook, max_attempts=max_attempts, semaphore=semaphore)
                    processed += 1
                    if progress_every and processed % max(1, int(progress_every)) == 0:
                        print(json.dumps({"run_id": current_run_id, "worker": worker_id, "processed": processed, "counts": queue.counts(current_run_id)}), flush=True)

        for worker_index in range(max(1, int(concurrency))):
            thread = threading.Thread(target=worker_loop, args=("w{}".format(worker_index + 1),), daemon=True)
            thread.start()
            workers.append(thread)

        discovery_error = ""
        started_at = utc_now()
        started = time.monotonic()
        enqueued = 0
        query_iter = iter(queries)
        seed_index = 0
        try:
            while enqueued < target:
                urls = []
                source_url = "https://www.judyrecords.com/"
                if queries:
                    try:
                        query = next(query_iter)
                    except StopIteration:
                        break
                    source_url = "https://www.judyrecords.com/search?" + urlencode({"search": query})
                    urls = ai_search_judyrecords(query, key, proxy, ai_rate, limit=limit_per_query, webhook=webhook, ai_lock=ai_lock)
                elif seeds:
                    seed = seeds[seed_index % len(seeds)]
                    seed_index += 1
                    source_url = seed
                    urls, _ = discover_record_urls(seed, discovery_mode, key, proxy, limit_per_query, semaphore, webhook=webhook)
                    if not urls:
                        break
                else:
                    break
                unique_urls = list(dict.fromkeys(urls))
                items = [_job_item(current_run_id, url, source_url) for url in unique_urls[: max(0, target - enqueued)]]
                inserted = 0
                for start in range(0, len(items), max(1, int(enqueue_batch))):
                    inserted += queue.enqueue_batch(items[start:start + max(1, int(enqueue_batch))])
                enqueued += inserted
                if inserted == 0 and not queries:
                    break
        except Exception as error:
            discovery_error = type(error).__name__ + ": " + str(error)[:300]
            print(json.dumps({"run_id": current_run_id, "status": "discovery_failed", "error": discovery_error}), flush=True)
        finally:
            discovery_done.set()
        for thread in workers:
            thread.join()
        counts = queue.counts(current_run_id)
        summary = {
            "run_id": current_run_id,
            "round": round_index,
            "target": target,
            "counts": counts,
            "started_at": started_at,
            "discovery_error": discovery_error,
            "finished_at": utc_now(),
            "duration_seconds": round(time.monotonic() - started, 3),
            "complete": counts.get("complete", 0) >= target,
        }
        write_text_atomic(out_dir / current_run_id / "summary.json", json.dumps(summary, indent=2, ensure_ascii=False))
        print(json.dumps({"run_id": current_run_id, "summary": summary}, ensure_ascii=False), flush=True)
        summaries.append(summary)
        if server:
            server.shutdown()
            server.server_close()
        queue.close()
        if counts.get("complete", 0) < target and not allow_partial:
            return 1, summaries
        if stop_event and stop_event.is_set():
            break
    return 0, summaries
