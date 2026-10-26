"""Capture public Google Maps pages with Spider Unlimited and normalize exposed JSON-LD."""
import argparse
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

from proxy.config import get_proxy
from scrape.client import request as spider_request

ALLOWED_HOSTS = {"google.com", "www.google.com", "maps.google.com"}


def validate_maps_url(url):
    parsed = urlparse(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or not parsed.path.startswith("/maps") or parsed.username or parsed.password):
        raise ValueError("Provide a credential-free HTTPS Google Maps page URL")
    return url


def payload(url):
    return {
        "url": validate_maps_url(url),
        "request": "browser",
        "return_format": "raw",
        "return_json_data": True,
        "return_page_links": True,
        "metadata": True,
        "session": False,
        "return_cookies": False,
        "cache": False,
    }


def walk(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def _schema_nodes(content):
    pattern = re.compile(
        r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.I | re.S
    )
    for match in pattern.finditer(content or ""):
        try:
            data = json.loads(html.unescape(match.group(1)))
        except (TypeError, ValueError):
            continue
        yield from walk(data)


def extract(page, source_url):
    metadata = page.get("metadata") or {}
    content = page.get("content") or ""
    businesses, reviews = [], {}
    for node in _schema_nodes(content):
        types = node.get("@type") or []
        types = types if isinstance(types, list) else [types]
        if any(isinstance(kind, str) and kind in {"LocalBusiness", "Place", "Organization"} for kind in types):
            rating = node.get("aggregateRating") or {}
            geo = node.get("geo") or {}
            businesses.append({
                "name": node.get("name"),
                "url": node.get("url") or source_url,
                "telephone": node.get("telephone"),
                "address": node.get("address"),
                "latitude": geo.get("latitude") if isinstance(geo, dict) else None,
                "longitude": geo.get("longitude") if isinstance(geo, dict) else None,
                "rating": rating.get("ratingValue") if isinstance(rating, dict) else None,
                "review_count": rating.get("reviewCount") if isinstance(rating, dict) else None,
                "source_type": types,
            })
        items = node.get("review") or []
        items = items if isinstance(items, list) else [items]
        for item in items:
            if not isinstance(item, dict):
                continue
            author = item.get("author") or {}
            rating = item.get("reviewRating") or {}
            review_id = item.get("@id") or item.get("url") or json.dumps(item, sort_keys=True)
            reviews[review_id] = {
                "author": author.get("name") if isinstance(author, dict) else author,
                "rating": rating.get("ratingValue") if isinstance(rating, dict) else None,
                "date": item.get("datePublished"),
                "text": item.get("reviewBody") or item.get("description"),
            }

    if not businesses and (metadata.get("title") or metadata.get("description")):
        businesses.append({
            "name": metadata.get("title"),
            "description": metadata.get("description"),
            "url": source_url,
            "source_type": ["page_metadata"],
        })
    return {
        "source": "google_maps",
        "url": source_url,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "http_status": page.get("status"),
        "businesses": businesses,
        "reviews": list(reviews.values()),
        "review_count": len(reviews),
        "links": page.get("links") or [],
        "complete": False,
        "limitation": "Unlimited scrape captures exposed page data; it does not use Spider's metered /fetch Maps extractor or guarantee full review pagination.",
    }


def scrape(url, output, key, proxy):
    url = validate_maps_url(url)
    pages = spider_request(payload(url), key, proxy)
    if not pages:
        raise RuntimeError("Spider returned no Google Maps page")
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError("Output folder is not empty; choose a new folder")
    raw_dir = output / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    page = pages[0]
    (raw_dir / "maps-page.json").write_text(json.dumps(page, ensure_ascii=False, indent=2))
    result = extract(page, url)
    (output / "google-maps.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    (output / "manifest.json").write_text(json.dumps({
        "url": url,
        "status": "captured" if page.get("status") == 200 else "inconclusive",
        "complete": False,
        "raw_file": "raw/maps-page.json",
        "result_file": "google-maps.json",
        "limitation": result["limitation"],
    }, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", help="A public Google Maps place or search URL")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    key = os.environ.get("SPIDER_API_KEY", "")
    if not key:
        parser.error("SPIDER_API_KEY is required")
    try:
        result = scrape(args.url, args.out, key, get_proxy(required=True))
    except (OSError, RuntimeError, ValueError) as error:
        parser.exit(1, "error: {}\n".format(error))
    print("Captured Maps page; {} structured businesses and {} exposed reviews. See {}".format(
        len(result["businesses"]), result["review_count"], args.out / "manifest.json"))


if __name__ == "__main__":
    main()
