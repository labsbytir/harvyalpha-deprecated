#!/usr/bin/env python3
"""Save anonymous Facebook profile sections and one JSON file per exposed post.

Uses Spider Unlimited and an optional Webshare proxy. Never opens a local browser,
supplies account cookies, or downloads image/video files.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse
from v1.scrape.client import request as spider_request
from proxy.config import get_proxy

SECTIONS = (
    "about", "about_overview", "about_work_and_education", "about_places",
    "about_contact_and_basic_info", "about_family_and_relationships",
    "about_details", "about_life_events", "friends", "followers", "following",
    "likes", "events", "map", "posts", "reels_tab",
)


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def payload(url, proxy):
    from v1.scrape.facebook_scroll import options
    body = {
        "url": url, "request": "browser", "return_format": "raw",
        "return_json_data": True, "return_page_links": True, "metadata": True,
        "cache": False, "session": False, "return_cookies": False,
        "wait_for": {"delay": {"timeout": {"secs": 5, "nanos": 0}}},
        **options(url),
    }
    if proxy:
        body["remote_proxy"] = proxy
    return body


def fetch(url, key, proxy):
    pages = spider_request(payload(url, proxy), key, proxy)
    if not pages:
        raise ValueError("Unexpected response: expected a nonempty page array")
    return pages


def extract_profile(page, account):
    from v1.scrape.profiles import _extract_social
    return _extract_social(page, account)


def post_records(page, profile_url):
    """Keep posts tied explicitly to this profile, not recommended accounts."""
    profile_path = urlparse(profile_url).path.rstrip("/")
    profile_ids = {n.get("id") for n in walk(page.get("json_data"))
                   if isinstance(n.get("url"), str)
                   and n["url"].rstrip("/") == profile_url.rstrip("/")}
    for node in walk(page.get("json_data")):
        if node.get("__typename") != "Story" or not node.get("post_id"):
            continue
        parts = list(walk(node))
        owned_video = next((p for p in parts if p.get("__typename") == "Video"
                            and isinstance(p.get("owner"), dict)
                            and p["owner"].get("id") in (profile_ids - {None})
                            and p.get("permalink_url")), None)
        url = html.unescape(node.get("permalink_url") or "")
        if not url and owned_video:
            url = html.unescape(owned_video["permalink_url"])
        parsed = urlparse(url)
        if parsed.hostname not in ("www.facebook.com", "facebook.com"):
            continue
        actor_ids = {a.get("id") for a in node.get("actors") or []}
        own_post_path = parsed.path.startswith(profile_path + "/posts/")
        other_post_path = "/posts/" in parsed.path or parsed.path in ("/permalink.php", "/story.php")
        owned_video_path = owned_video and url == html.unescape(owned_video["permalink_url"])
        if not own_post_path and not owned_video_path and not (other_post_path and actor_ids & (profile_ids - {None})):
            continue
        texts = list(dict.fromkeys(
            part["message"]["text"] for part in parts
            if isinstance(part.get("message"), dict)
            and isinstance(part["message"].get("text"), str)
        ))
        feedback = next((p for p in parts if "top_reactions" in p and "reaction_count" in p), None)
        if feedback is None:
            feedback = next((p for p in parts if isinstance(p.get("reaction_count"), dict)), {})
        comments = {}
        for part in parts:
            if not isinstance(part.get("body"), dict) or not part["body"].get("text"):
                continue
            author = part.get("author")
            cid = part.get("id") or part.get("legacy_token")
            if not isinstance(author, dict) or not cid:
                continue
            comments[cid] = {
                "id": cid, "text": part["body"]["text"], "url": part.get("url"),
                "timestamp": part.get("created_time"),
                "author": {"id": author.get("id"), "name": author.get("name"), "url": author.get("url")},
            }
        yield {
            "id": str(node["post_id"]), "url": url,
            "timestamp": node.get("creation_time"), "text_fragments": texts,
            "authors": [{"id": a.get("id"), "name": a.get("name"), "url": a.get("url")}
                        for a in (node.get("actors") or ([owned_video["owner"]] if owned_video else []))],
            "reaction_count": feedback.get("reaction_count"),
            "reaction_breakdown": feedback.get("top_reactions"),
            "share_count": feedback.get("share_count"),
            "comments": list(comments.values()), "sources": [page.get("url")],
            "completeness": "Only records exposed by the anonymous response",
        }


def summarize(page, label):
    from v1.scrape.facebook_scroll import diagnostic
    nodes = list(walk(page.get("json_data")))
    types = Counter(n["__typename"] for n in nodes if isinstance(n.get("__typename"), str))
    pagination = [n["page_info"] for n in nodes if isinstance(n.get("page_info"), dict)]
    return {
        "section": label, "url": page.get("url"), "status": page.get("status"),
        "error": page.get("error"), "description": (page.get("metadata") or {}).get("description"),
        "record_types": dict(types), "pagination": pagination,
        "logged_out_profile_tabs": bool(types.get("ProfileLoggedOutTabsWithJoinCTA")),
        "story_records": sum(n.get("__typename") == "Story" and bool(n.get("post_id")) for n in nodes),
        "scroll": diagnostic(page),
    }


def profile_details(pages, profile_url):
    details = {"url": profile_url, "identity": {}, "fields": [], "external_links": []}
    seen_fields, links = set(), set()
    for page in pages:
        for node in walk(page.get("json_data")):
            if isinstance(node.get("url"), str) and node["url"].rstrip("/") == profile_url.rstrip("/"):
                for key in ("id", "name", "is_verified"):
                    if node.get(key) is not None:
                        details["identity"][key] = node[key]
            typename = node.get("__typename") or ""
            if "ProfileFieldRenderer" in typename or typename in ("ContextItemDefaultRenderer", "WebsiteContextItemRenderer", "ProfileStatus"):
                fields = node.get("field") or node.get("context_item") or node.get("profile_status_text") or node
                texts = list(dict.fromkeys(p["text"] for p in walk(fields) if isinstance(p.get("text"), str)))
                for text in texts:
                    marker = (page.get("url"), text)
                    if marker not in seen_fields:
                        seen_fields.add(marker)
                        details["fields"].append({"text": text, "source": page.get("url"), "renderer": typename})
                for part in walk(fields):
                    if part.get("__typename") == "ExternalUrl" and isinstance(part.get("external_url"), str):
                        links.add(html.unescape(part["external_url"]))
    details["external_links"] = sorted(links)
    return details


def run(profile_url, output, key, proxy, max_posts=100, max_linked_profiles=20):
    parsed = urlparse(profile_url)
    if parsed.scheme != "https" or parsed.hostname not in ("facebook.com", "www.facebook.com"):
        raise ValueError("Expected an https://www.facebook.com/profile URL")
    if parsed.username or parsed.password or not re.fullmatch(r"/[A-Za-z0-9.]+/?", parsed.path):
        raise ValueError("Expected a Facebook profile handle, without credentials or extra path segments")
    profile_url = "https://www.facebook.com/" + parsed.path.strip("/") + "/"
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    raw_dir, posts_dir = output / "raw", output / "posts"
    raw_dir.mkdir(exist_ok=True)
    posts_dir.mkdir(exist_ok=True)
    if any(posts_dir.iterdir()):
        raise ValueError("Posts directory is not empty; choose a new output folder to avoid mixing runs")
    sections, posts, downloaded_pages = [], {}, []

    def download(item):
        label, url = item
        path = raw_dir / (label + ".json")
        try:
            # Reuse evidence from this exact run if the caller downloaded it first.
            if label == "profile" and (output / "profile-response.json").exists():
                pages = json.loads((output / "profile-response.json").read_text())
            else:
                pages = fetch(url, key, proxy)
            path.write_text(json.dumps(pages, ensure_ascii=False))
            return label, pages, None
        except (RuntimeError, ValueError, OSError, TimeoutError) as error:
            return label, [], str(error)

    def ingest(result):
        label, pages, error = result
        if error:
            sections.append({"section": label, "error": error})
            print(label + ": " + error, flush=True)
        for page in pages:
            downloaded_pages.append(page)
            summary = summarize(page, label)
            sections.append(summary)
            if page.get("error") or page.get("status") != 200:
                continue
            for post in post_records(page, profile_url):
                previous = posts.get(post["id"])
                if previous:
                    post["sources"] = list(dict.fromkeys(previous["sources"] + post["sources"]))
                    post["comments"] = list({c["id"]: c for c in previous["comments"] + post["comments"]}.values())
                    for field, value in previous.items():
                        if value and not post.get(field):
                            post[field] = value
                posts[post["id"]] = post
            print(f"{label}: HTTP {page.get('status')}; {summary['story_records']} story records", flush=True)

    initial = [("profile", profile_url)] + [(section, profile_url + section + "/") for section in SECTIONS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for result in pool.map(download, initial):
            ingest(result)
        urls = list(dict.fromkeys(p["url"] for p in posts.values()))
        for summary in sections:
            for url in (summary.get("scroll") or {}).get("postLinks", []):
                parsed_post = urlparse(url)
                if parsed_post.hostname in ("facebook.com", "www.facebook.com") and parsed_post.path.startswith(parsed.path.rstrip("/") + "/posts/"):
                    if url not in urls:
                        urls.append(url)
        targets = [("post-" + hashlib.sha256(url.encode()).hexdigest()[:16], url) for url in urls[:max_posts]]
        for result in pool.map(download, targets):
            ingest(result)
    for post in posts.values():
        safe_id = re.sub(r"[^A-Za-z0-9_-]", "_", post["id"])
        (posts_dir / (safe_id + ".json")).write_text(json.dumps(post, ensure_ascii=False, indent=2))
    details = profile_details(downloaded_pages, profile_url)
    (output / "profile-details.json").write_text(json.dumps(details, ensure_ascii=False, indent=2))
    manifest = {
        "profile_url": profile_url, "captured_at": datetime.now(timezone.utc).isoformat(),
        "provider": "Spider Unlimited", "custom_proxy": bool(proxy),
        "account_cookies_supplied": False, "images_downloaded": 0,
        "post_count": len(posts), "post_permalink_limit": max_posts,
        "all_discovered_permalinks_fetched": len(urls) <= max_posts and all(
            s.get("status") == 200 and not s.get("error")
            for s in sections if s["section"].startswith("post-")
        ),
        "complete": False, "sections": sections,
        "limitations": [
            "All named public sections were attempted; this is not proof of a complete account archive.",
            "Explicit cloud scroll steps were requested; each section reports whether scrolling was observed. Pagination cursors are saved but not replayed.",
            "Missing or login-walled records are not evidence that the account has no posts.",
            "No image/video files downloaded; raw evidence can contain media URL metadata.",
        ],
    }
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    from v1.scrape.profiles import scrape_linked_profiles
    linked = scrape_linked_profiles(profile_url, details["external_links"], output / "linked-profiles",
                                    key, proxy, max_linked_profiles)
    manifest["linked_profiles"] = {"scraped": len(linked["accounts"]), "failed": len(linked["failures"]),
                                   "pending": linked["pending_links"], "manifest": "linked-profiles/manifest.json"}
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile_url")
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-posts", type=int, default=100)
    parser.add_argument("--max-linked-profiles", type=int, default=20)
    args = parser.parse_args()
    key = os.environ.get("SPIDER_API_KEY")
    if not key:
        parser.error("SPIDER_API_KEY is required")
    if args.max_posts < 1:
        parser.error("--max-posts must be positive")
    if args.max_linked_profiles < 0:
        parser.error("--max-linked-profiles must be nonnegative")
    try:
        manifest = run(args.profile_url, args.out, key, get_proxy(), args.max_posts, args.max_linked_profiles)
    except (ValueError, OSError) as error:
        parser.exit(1, f"error: {error}\n")
    print(f"Saved {manifest['post_count']} post JSON files; completeness: partial. See {args.out / 'manifest.json'}")


if __name__ == "__main__":
    main()
