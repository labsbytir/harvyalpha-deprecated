"""Truth Social profile and status collector adapter."""
import argparse
import json
import os
import re
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


def resolve_account_id(handle, key, proxy=None):
    clean_handle = handle.lstrip("@").strip()
    lookup_url = f"https://truthsocial.com/api/v1/accounts/lookup?acct={clean_handle}"
    pages = spider_request(payload(lookup_url, proxy), key, proxy)
    good = [p for p in pages if p.get("status") == 200 and not p.get("error")]
    if not good:
        raise RuntimeError("Truth Social account lookup failed")
    page = good[0]
    content = page.get("content") or ""
    if "<pre>" in content:
        m = re.search(r"<pre>(.*?)</pre>", content, re.DOTALL)
        if m:
            content = m.group(1)
    if isinstance(content, str) and content.strip():
        try:
            data = json.loads(content.strip())
            if isinstance(data, dict) and data.get("id"):
                return str(data["id"])
        except (json.JSONDecodeError, KeyError):
            pass
    for item in page.get("json_data") or []:
        if isinstance(item, dict) and item.get("id"):
            return str(item["id"])
    raise RuntimeError("Truth Social account ID not found in lookup response")


def fetch_handle(handle, key, proxy, max_posts=25):
    account = profile_link(f"https://truthsocial.com/@{handle.lstrip('@')}")
    if not account or account["platform"] != "truthsocial":
        raise ValueError("Invalid Truth Social handle")
    validate_public_destination(account["url"])

    account_id = resolve_account_id(handle, key, proxy)
    statuses_url = f"https://truthsocial.com/api/v1/accounts/{account_id}/statuses?limit={min(max_posts, 40)}"
    pages = spider_request(payload(statuses_url, proxy), key, proxy)
    good = [page for page in pages if page.get("status") == 200 and not page.get("error")]
    if not good:
        raise RuntimeError("Spider returned no successful Truth Social page")
    profile = extract_profile(good[0], account)
    posts = profile.get("posts", [])[:max_posts]
    return {
        "platform": "truthsocial",
        "handle": "@" + account["url"].rstrip("/").split("/")[-1],
        "url": account["url"],
        "account_id": account_id,
        "profile": profile,
        "posts": posts,
        "complete": False,
        "limitation": "Public timeline capture only; follower lists require user authentication.",
    }, pages


def main():
    parser = argparse.ArgumentParser(description="Truth Social collector")
    parser.add_argument("handles", nargs="+", help="User handle(s) to scrape")
    parser.add_argument("--max-posts", type=int, default=25, help="Maximum posts to extract")
    parser.add_argument("--out", default="truthsocial_accounts.json", help="Output JSON file")
    args = parser.parse_args()

    key = os.environ.get("SPIDER_API_KEY")
    if not key:
        parser.error("SPIDER_API_KEY must be configured in environment")
    try:
        proxy = get_proxy(required=True)
    except ValueError as error:
        parser.error(str(error))

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    results = []
    for handle in args.handles:
        record, _ = fetch_handle(handle, key, proxy, args.max_posts)
        results.append(record)
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Collected {len(results)} account(s) to {out_path}")


if __name__ == "__main__":
    main()
