#!/usr/bin/env python3
"""Check a username against selected public WhatsMyName GET definitions."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import quote, urlsplit

from scrape.client import scrape_batch
from scrape.profiles import validate_public_destination
from proxy.config import get_proxy

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "username_targets.json"
BATCH_SIZE = 10


def make_checks(username, categories, data):
    if not isinstance(username, str) or not re.fullmatch(r"[\w.-]{1,64}", username, re.UNICODE):
        raise ValueError("Use a username of 1–64 letters, numbers, dots, underscores, or hyphens.")
    checks = []
    skipped = []
    for site in data.get("sites", []):
        if site.get("valid", True) is False or site.get("cat") not in categories:
            continue
        template = site.get("uri_check", "")
        if site.get("post_body") or "{account}" not in template:
            skipped.append({"site": site.get("name", "unknown"), "reason": "unsupported_method"})
            continue
        account = username
        strip = site.get("strip_bad_char")
        if isinstance(strip, str) and strip:
            account = account.replace(strip, "")
        url = template.replace("{account}", quote(account, safe=""))
        parsed = urlsplit(url)
        if parsed.scheme != "https" or not parsed.hostname:
            skipped.append({"site": site.get("name", "unknown"), "reason": "unsafe_or_non_https_url"})
            continue
        try:
            validate_public_destination(url)
        except (ValueError, OSError):
            skipped.append({"site": site.get("name", "unknown"), "reason": "host_not_public"})
            continue
        checks.append((site, url))
    return checks, skipped


def fetch_batch(urls, key, proxy):
    return scrape_batch(urls, key, proxy, request="http", return_format="raw", cache=False)


def classify(site, page):
    if page is None:
        return "inconclusive"
    content = page.get("content") or ""
    status = page.get("status")
    expected = site.get("e_string", "")
    missing = site.get("m_string", "")
    found = status == site.get("e_code") and bool(expected) and expected in content
    not_found = status == site.get("m_code") and (
        (bool(missing) and missing in content)
        or (not missing and site.get("e_code") != site.get("m_code"))
    )
    if found and not not_found:
        return "candidate_match"
    if not_found and not found:
        return "not_found"
    return "inconclusive"


def save_report(output, username, categories, checks, skipped, results, complete):
    counts = {state: sum(row["status"] == state for row in results)
              for state in ("candidate_match", "not_found", "inconclusive")}
    report = {
        "username": username,
        "source": "WhatsMyName data (CC BY-SA 4.0)",
        "source_url": "https://github.com/WebBreacher/WhatsMyName",
        "license_url": "https://creativecommons.org/licenses/by-sa/4.0/",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "categories": sorted(categories),
        "requested": len(checks),
        "checked": len(results),
        "skipped": len(skipped),
        "complete": complete,
        "counts": counts,
        "results": results,
        "skipped_sites": skipped,
    }
    temp = output / "username-report.json.tmp"
    temp.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    os.replace(temp, output / "username-report.json")


def run(username, categories, output, key, proxy):
    data = json.loads(DATA.read_text())
    checks, skipped = make_checks(username, categories, data)
    output.mkdir(parents=True, exist_ok=True)
    results = []
    save_report(output, username, categories, checks, skipped, results, False)
    for start in range(0, len(checks), BATCH_SIZE):
        batch = checks[start:start + BATCH_SIZE]
        pages = fetch_batch([url for _, url in batch], key, proxy)
        # Spider returns one page per input URL, in the same order.
        for index, (site, url) in enumerate(batch):
            page = pages[index] if index < len(pages) else None
            state = classify(site, page)
            results.append({
                "site": site.get("name"),
                "category": site.get("cat"),
                "status": state,
                "profile_url": (site.get("uri_pretty") or url).replace("{account}", quote(username, safe="")),
                "http_status": page.get("status") if page else None,
            })
        save_report(output, username, categories, checks, skipped, results, False)
        print("Checked {} of {} sites".format(min(start + len(batch), len(checks)), len(checks)), flush=True)
    save_report(output, username, categories, checks, skipped, results, True)
    counts = {state: sum(row["status"] == state for row in results)
              for state in ("candidate_match", "not_found", "inconclusive")}
    print("{} candidate profiles; {} inconclusive; {} skipped.".format(
        counts["candidate_match"], counts["inconclusive"], len(skipped)), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--category", action="append", required=True)
    args = parser.parse_args()
    key = os.environ.get("SPIDER_API_KEY")
    proxy = get_proxy(required=True)
    if not key or not proxy:
        parser.error("SPIDER_API_KEY and WEBSHARE_PROXY_URL are required")
    try:
        run(args.username, set(args.category), args.out, key, proxy)
    except (OSError, RuntimeError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
