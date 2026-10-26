"""Build a small, job-scoped text index payload from saved JSON artifacts."""
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urlsplit

MAX_DOCUMENTS = 2_000
MAX_TEXT_CHARS = 2_500
MAX_TOTAL_CHARS = 1_500_000
RECORD_LIST_KEYS = {"results", "posts", "search_results", "data", "items", "stories", "events"}


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def _plain(value):
    if "<" in value and ">" in value:
        parser = _Text()
        try:
            parser.feed(value)
            value = " ".join(parser.parts)
        except Exception:
            pass
    return " ".join(value.split())


def _flatten(value, limit):
    parts = []

    def walk(item):
        if sum(map(len, parts)) >= limit:
            return
        if isinstance(item, str):
            text = _plain(item)
            if text:
                parts.append(text[:max(0, limit - sum(map(len, parts)))])
        elif isinstance(item, dict):
            for key, child in item.items():
                if key.lower() in {"image", "images", "video", "videos", "avatar", "thumbnail"}:
                    continue
                if isinstance(child, str) and key.lower() in {"name", "title", "case_name", "caption", "text", "description", "url", "profile_url", "date", "timestamp"}:
                    parts.append("{}: {}".format(key, _plain(child)))
                else:
                    walk(child)
                if sum(map(len, parts)) >= limit:
                    break
        elif isinstance(item, list):
            for child in item:
                walk(child)
                if sum(map(len, parts)) >= limit:
                    break

    walk(value)
    return " ".join(parts)[:limit]


def _first_string(item, keys):
    if isinstance(item, dict):
        for key in keys:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return _plain(value)[:240]
    return ""


def documents_for_job(root, files, kind="", target=""):
    root = Path(root).resolve()
    documents, total_chars, truncated = [], 0, False

    def add(path, node, node_id):
        nonlocal total_chars, truncated
        if len(documents) >= MAX_DOCUMENTS or total_chars >= MAX_TOTAL_CHARS:
            truncated = True
            return
        text = _flatten(node, min(MAX_TEXT_CHARS, MAX_TOTAL_CHARS - total_chars))
        if not text:
            return
        relative = path.resolve().relative_to(root).as_posix()
        parts = Path(relative).parts
        source = Path(parts[1]).stem if len(parts) > 1 and parts[0] == "raw" else (urlsplit(target).hostname or kind or path.parent.name)
        if source == "username":
            source = "whatsmyname"
        documents.append({
            "id": "{}#{}".format(relative, node_id),
            "source": source,
            "title": _first_string(node, ("title", "name", "case_name", "caption", "username")) or path.stem,
            "url": _first_string(node, ("url", "profile_url", "permalink", "frontend_url")),
            "file": relative,
            "text": text,
        })
        total_chars += len(text)

    def visit(path, node, parent_id="root"):
        if len(documents) >= MAX_DOCUMENTS or total_chars >= MAX_TOTAL_CHARS:
            return
        if isinstance(node, list):
            for i, child in enumerate(node):
                visit(path, child, "{}[{}]".format(parent_id, i))
            return
        if isinstance(node, dict):
            record_lists = [(key, value) for key, value in node.items()
                            if key.lower() in RECORD_LIST_KEYS and isinstance(value, list)]
            if record_lists:
                metadata = {k: v for k, v in node.items() if k not in {key for key, _ in record_lists}}
                if metadata:
                    add(path, metadata, parent_id)
                for key, rows in record_lists:
                    visit(path, rows, "{}.{}".format(parent_id, key))
                return
        add(path, node, parent_id)

    for path in files:
        try:
            value = json.loads(path.read_text())
        except (OSError, UnicodeError, ValueError):
            continue
        visit(path, value)
        if len(documents) >= MAX_DOCUMENTS or total_chars >= MAX_TOTAL_CHARS:
            truncated = True
            break
    return {"documents": documents, "truncated": truncated}
