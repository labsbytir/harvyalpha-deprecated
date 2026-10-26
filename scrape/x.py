#!/usr/bin/env python3
"""Consent-gated X profile collector using Spider Unlimited + Webshare.

The app's shared profile pipeline uses these same adapter functions. The Spider
recipe is plain HTTP; no metered endpoint or alternate provider is used.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from proxy.config import get_proxy
from scrape.client import request as spider_request
from scrape.profiles import profile_link, validate_public_destination


def payload(url, proxy=None):
    body = {
        "url": url,
        "return_format": "raw",
        "return_json_data": True,
        "return_page_links": True,
        "metadata": True,
        "cache": False,
        "session": False,
        "return_cookies": False,
    }
    if proxy:
        body["remote_proxy"] = proxy
    return body


def extract_profile(page, account):
    from scrape.profiles import _extract_social
    return _extract_social(page, account)


def fetch_handle(handle, key, proxy, max_posts):
    account = profile_link(f"https://x.com/{handle.lstrip('@')}")
    if not account or account["platform"] != "x":
        raise ValueError("Invalid X handle")
    validate_public_destination(account["url"])
    pages = spider_request(payload(account["url"], proxy), key, proxy)
    good = [page for page in pages if page.get("status") == 200 and not page.get("error")]
    if not good:
        raise RuntimeError("Spider returned no successful X page")
    profile = extract_profile(good[0], account)
    posts = profile.get("posts", [])[:max_posts]
    return {
        "platform": "x",
        "handle": "@" + account["url"].rstrip("/").split("/")[-1],
        "url": account["url"],
        "profile": profile,
        "posts": posts,
        "complete": False,
        "limitation": "Unlimited page capture only; X timeline pagination is not inferred from missing posts.",
    }, pages


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("handles", nargs="+")
    parser.add_argument("--consent", required=True)
    parser.add_argument("--max-posts", type=int, default=25)
    parser.add_argument("--merge")
    parser.add_argument("--out", default="accounts.json")
    args = parser.parse_args()
    if not 1 <= args.max_posts <= 100:
        parser.error("--max-posts must be between 1 and 100")

    key = os.environ.get("SPIDER_API_KEY")
    if not key:
        parser.error("SPIDER_API_KEY must be configured in the environment")
    try:
        proxy = get_proxy(required=True)
    except ValueError as error:
        parser.error(str(error))

    with open(args.consent, encoding="utf-8") as consent_file:
        consent = json.load(consent_file)
    allowed_handles = consent if isinstance(consent, list) else consent.get("handles", [])
    allowed = {h.lstrip("@").casefold() for h in allowed_handles if isinstance(h, str)}
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    raw_dir = output.parent / (output.stem + "-raw")
    raw_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(raw_dir, 0o700)

    results = []
    for handle in args.handles:
        normalized = handle.lstrip("@").casefold()
        if normalized not in allowed:
            parser.error(f"@{handle} is not in the consent registry ({args.consent})")
        try:
            record, raw_pages = fetch_handle(handle, key, proxy, args.max_posts)
            raw_file = raw_dir / (hashlib.sha256(record["url"].encode()).hexdigest()[:16] + ".json")
            raw_file.write_text(json.dumps(raw_pages, ensure_ascii=False), encoding="utf-8")
            os.chmod(raw_file, 0o600)
            record["raw_file"] = str(raw_file)
            results.append(record)
            print(f"captured {len(record['posts'])} exposed post(s) for {record['handle']}")
        except (RuntimeError, ValueError, OSError, TimeoutError) as error:
            print(f"capture failed for @{handle}: {error}", file=sys.stderr)

    output.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    os.chmod(output, 0o600)
    print(f"wrote {output}")
    if args.merge and results:
        with open(args.merge, encoding="utf-8") as graph_file:
            graph = json.load(graph_file)
        graph.setdefault("nodes", [])
        graph.setdefault("links", [])
        for account in results:
            node_id = "x:" + account["handle"].lstrip("@")
            if not any(node.get("id") == node_id for node in graph["nodes"]):
                graph["nodes"].append({"id": node_id, "name": account["handle"], "type": "account", "url": account["url"]})
                graph["links"].append({"source": "you", "target": node_id, "dashed": True})
            for post in account["posts"]:
                if post.get("text"):
                    graph["nodes"].append({"type": "social-post", "person": account["handle"], "text": post["text"][:200], "date": post.get("timestamp")})
        Path(args.merge).write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"merged into {args.merge}")


if __name__ == "__main__":
    main()
