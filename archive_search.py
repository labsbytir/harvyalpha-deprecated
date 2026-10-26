"""Persistent full-text search across Harvy's saved JSON and text artifacts."""
import hashlib
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sqlite3
import sys

from search_documents import documents_for_job

SEARCHABLE_SUFFIXES = {".html", ".htm", ".json", ".md", ".txt"}
MAX_HTML_CHARS = 2_500_000


class _VisibleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden = 0
        self.title = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.hidden += 1
        elif tag == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.hidden:
            self.hidden -= 1
        elif tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title and not self.title:
            self.title = data.strip()[:240]
        if not self.hidden and data.strip():
            self.parts.append(data.strip())


def _text_documents(root, path):
    relative = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")[:MAX_HTML_CHARS]
    title = path.stem
    if path.suffix.lower() in {".html", ".htm"}:
        parser = _VisibleText()
        parser.feed(text)
        title = parser.title or title
        text = " ".join(parser.parts)
    if not text.strip():
        return []
    return [{"id": relative, "file": relative, "source": path.parent.name,
             "title": title, "url": "", "text": text[:MAX_HTML_CHARS]}]


def _file_documents(root, path):
    if path.suffix.lower() == ".json":
        return documents_for_job(root, [path])["documents"]
    return _text_documents(root, path)


def _connect(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path, timeout=30)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""CREATE TABLE IF NOT EXISTS indexed_files (
        path TEXT PRIMARY KEY, mtime_ns INTEGER NOT NULL, size INTEGER NOT NULL
    )""")
    db.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(
        doc_id UNINDEXED, file UNINDEXED, source UNINDEXED, title, url UNINDEXED, body
    )""")
    return db


def index_files(root, files, db_path, prefix=""):
    root = Path(root).resolve()
    prefix = Path(prefix).as_posix().strip("/")
    indexed = skipped = 0
    with _connect(db_path) as db:
        for path in files:
            path = Path(path)
            try:
                if path.is_symlink():
                    skipped += 1
                    continue
                path = path.resolve(strict=True)
                relative = (Path(prefix) / path.relative_to(root)).as_posix() if prefix else path.relative_to(root).as_posix()
                if path.suffix.lower() not in SEARCHABLE_SUFFIXES:
                    skipped += 1
                    continue
                stat = path.stat()
                previous = db.execute(
                    "SELECT mtime_ns, size FROM indexed_files WHERE path = ?", (relative,)
                ).fetchone()
                if previous == (stat.st_mtime_ns, stat.st_size):
                    continue
                docs = _file_documents(root, path)
            except (OSError, UnicodeError, ValueError, RecursionError):
                skipped += 1
                continue

            with db:
                db.execute("DELETE FROM search_index WHERE file = ?", (relative,))
                for doc in docs:
                    doc_id = hashlib.sha256((relative + "#" + doc["id"]).encode()).hexdigest()
                    db.execute("INSERT INTO search_index VALUES (?, ?, ?, ?, ?, ?)", (
                        doc_id, relative, str(doc.get("source") or "Harvy"),
                        str(doc.get("title") or path.stem)[:240],
                        str(doc.get("url") or "")[:2048], str(doc.get("text") or "")[:MAX_HTML_CHARS],
                    ))
                db.execute("INSERT OR REPLACE INTO indexed_files VALUES (?, ?, ?)",
                           (relative, stat.st_mtime_ns, stat.st_size))
            indexed += 1
    return {"indexed_files": indexed, "skipped_files": skipped}


def index_directory(root, db_path):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError("Archive directory does not exist")
    files = sorted(path for path in root.rglob("*")
                   if path.is_file() and not path.is_symlink() and path.suffix.lower() in SEARCHABLE_SUFFIXES)
    result = index_files(root, files, db_path)
    present = {path.relative_to(root).as_posix() for path in files}
    with _connect(db_path) as db:
        stale = [row[0] for row in db.execute("SELECT path FROM indexed_files") if row[0] not in present]
        for path in stale:
            with db:
                db.execute("DELETE FROM search_index WHERE file = ?", (path,))
                db.execute("DELETE FROM indexed_files WHERE path = ?", (path,))
    result["removed_files"] = len(stale)
    return result


def search(db_path, query, limit=20):
    if not isinstance(query, str) or len(query) > 200:
        raise ValueError("Search terms must be 1–200 characters")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValueError("Search result limit must be between 1 and 50")
    terms = re.findall(r"[\w.-]{2,64}", query, flags=re.UNICODE)[:12]
    if not terms:
        return []
    match = " AND ".join('"{}"'.format(term.replace('"', '""')) for term in terms)
    db = sqlite3.connect(db_path, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        rows = db.execute("""SELECT doc_id, file, source, title, url,
                   snippet(search_index, 5, '', '', ' … ', 24) AS snippet
                   FROM search_index WHERE search_index MATCH ?
                   ORDER BY bm25(search_index) LIMIT ?""", (match, limit)).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("data"))
    parser.add_argument("--db", type=Path, default=Path("data/search-index.sqlite3"))
    args = parser.parse_args()
    try:
        result = index_directory(args.root, args.db)
    except (OSError, sqlite3.Error, ValueError) as error:
        print("Archive indexing failed: {}".format(error), file=sys.stderr)
        return 1
    print("Indexed {} file(s); skipped {}.".format(result["indexed_files"], result["skipped_files"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
