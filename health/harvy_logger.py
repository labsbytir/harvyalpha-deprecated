"""Harvy Unified Logging Client for external servers and tools.

Ships structured logs to Cloudflare R2 'harvy-logs' bucket via the Harvy Worker
/api/logs/ingest endpoint or directly via standard logging.Handler.
"""
from datetime import datetime, timezone
import json
import logging
import os
import re
import sys
import threading
import time
import urllib.request


def format_log_record(
    service: str = "external",
    level: str = "INFO",
    message: str = "",
    metadata: dict = None,
    timestamp: str = None,
    environment: str = None,
) -> dict:
    """Format a log entry into Harvy standardized log envelope."""
    clean_service = re.sub(r"[^a-zA-Z0-9_.-]", "_", str(service).strip()) or "external"
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    return {
        "service": clean_service,
        "level": str(level).upper(),
        "message": str(message),
        "timestamp": timestamp,
        "environment": str(environment or os.environ.get("HARVY_ENV", "production")),
        "metadata": metadata if isinstance(metadata, dict) else {},
    }


class HarvyLogHandler(logging.Handler):
    """Python logging.Handler that dispatches logs to Harvy log ingest endpoint."""

    def __init__(
        self,
        service: str = "external",
        ingest_url: str = None,
        api_key: str = None,
        buffer_size: int = 25,
        flush_interval: float = 5.0,
    ):
        super().__init__()
        self.service = service
        self.ingest_url = (ingest_url or os.environ.get("HARVY_LOGS_INGEST_URL", "")).rstrip("/")
        if self.ingest_url and not self.ingest_url.endswith("/api/logs/ingest"):
            self.ingest_url = f"{self.ingest_url}/api/logs/ingest"
        self.api_key = api_key or os.environ.get("HARVY_LOGS_INGEST_KEY") or os.environ.get("HARVY_API_KEY", "")
        self.buffer_size = max(1, buffer_size)
        self.flush_interval = flush_interval
        self._buffer = []
        self._lock = threading.Lock()
        self._last_flush = time.time()

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            metadata = {
                "logger": record.name,
                "module": record.module,
                "func": record.funcName,
                "line": record.lineno,
                "process": record.process,
                "thread": record.threadName,
            }
            if record.exc_info:
                metadata["exc_text"] = self.formatException(record.exc_info)
            if hasattr(record, "metadata") and isinstance(record.metadata, dict):
                metadata.update(record.metadata)

            event = format_log_record(
                service=self.service,
                level=record.levelname,
                message=msg,
                metadata=metadata,
                timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            )

            with self._lock:
                self._buffer.append(event)
                should_flush = len(self._buffer) >= self.buffer_size or (time.time() - self._last_flush >= self.flush_interval)

            if should_flush:
                self.flush()
        except Exception:
            self.handleError(record)

    def flush(self):
        with self._lock:
            if not self._buffer:
                return
            events_to_send = list(self._buffer)
            self._buffer.clear()
            self._last_flush = time.time()

        if not self.ingest_url:
            return

        try:
            payload = json.dumps({"events": events_to_send}).encode("utf-8")
            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "User-Agent": f"HarvyLogger/{self.service}",
            }
            if self.api_key:
                headers["x-api-key"] = self.api_key

            req = urllib.request.Request(self.ingest_url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status not in (200, 201, 202):
                    sys.stderr.write(f"HarvyLogHandler: HTTP {resp.status} on ingest\n")
        except Exception as err:
            # Resilient: never crash the host application on logging failure
            sys.stderr.write(f"HarvyLogHandler dispatch warning: {err}\n")

    def close(self):
        try:
            self.flush()
        finally:
            super().close()


class HarvyLogger:
    """Standalone logging client for external tools and services."""

    def __init__(
        self,
        service: str = "external",
        ingest_url: str = None,
        api_key: str = None,
        buffer_size: int = 1,
    ):
        self.service = service
        self.handler = HarvyLogHandler(
            service=service,
            ingest_url=ingest_url,
            api_key=api_key,
            buffer_size=buffer_size,
        )

    def log(self, level: str, message: str, metadata: dict = None):
        event = format_log_record(
            service=self.service,
            level=level,
            message=message,
            metadata=metadata,
        )
        with self.handler._lock:
            self.handler._buffer.append(event)
        self.handler.flush()

    def info(self, message: str, metadata: dict = None):
        self.log("INFO", message, metadata)

    def warning(self, message: str, metadata: dict = None):
        self.log("WARNING", message, metadata)

    def error(self, message: str, metadata: dict = None):
        self.log("ERROR", message, metadata)

    def flush(self):
        self.handler.flush()
