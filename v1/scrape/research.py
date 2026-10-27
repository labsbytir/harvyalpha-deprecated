#!/usr/bin/env python3
"""Run a bounded legal-record or public Mapillary lookup."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import ProxyHandler, Request, build_opener, urlopen

from v1.scrape.jobs import ARREST_STATE_SLUGS
from proxy.config import get_proxy

HERE = Path(__file__).resolve().parent
SPIDER_ENDPOINT = "https://api.spider.cloud/unlimited/scrape"
MAX_SOURCE_BYTES = 4_000_000


def spider_get(url, spider_key, proxy, headers=None):
    body = {
        "url": url,
        "request": "http",
        "return_format": "raw",
        "cache": False,
        "remote_proxy": proxy,
    }
    if headers:
        body["headers"] = headers
    req = Request(SPIDER_ENDPOINT, data=json.dumps(body).encode("utf-8"), headers={
        "Authorization": "Bearer " + spider_key,
        "Content-Type": "application/json",
    })
    try:
        with urlopen(req, timeout=120) as response:
            pages = json.load(response)
    except HTTPError as error:
        raise RuntimeError("Spider request failed (HTTP {}).".format(error.code)) from None
    except (URLError, TimeoutError):
        raise RuntimeError("Could not connect to Spider.") from None
    if not isinstance(pages, list) or not pages:
        raise RuntimeError("Spider returned no page data.")
    return pages[0]


def direct_request(url, proxy, token=None, method="GET", body=None, headers=None):
    request_headers = {"Accept": "application/json", **(headers or {})}
    if token:
        request_headers["Authorization"] = token
    request = Request(url, data=body, headers=request_headers, method=method)
    opener = build_opener(ProxyHandler({"http": proxy, "https": proxy}))
    try:
        with opener.open(request, timeout=45) as response:
            content = response.read(MAX_SOURCE_BYTES + 1)
            status = response.status
            content_type = response.headers.get("Content-Type", "")
    except HTTPError as error:
        content = error.read(MAX_SOURCE_BYTES + 1)
        status = error.code
        content_type = error.headers.get("Content-Type", "")
    except (URLError, TimeoutError):
        raise RuntimeError("Could not connect to source.") from None
    if len(content) > MAX_SOURCE_BYTES:
        raise RuntimeError("Source response exceeded the 4 MB per-source limit.")
    text = content.decode("utf-8", "replace")
    try:
        parsed = json.loads(text) if "json" in content_type.lower() or text.lstrip().startswith(("{", "[")) else None
    except json.JSONDecodeError:
        parsed = None
    return status, content_type, text, parsed


def save_raw(raw_dir, source, value):
    path = raw_dir / (source + ".json")
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False))
    return path.name


def source_result(name, status, count=0, **extra):
    return {"source": name, "status": status, "result_count": count, **extra}


def run_legal(config, out):
    proxy = get_proxy(required=True)
    spider_key = os.environ["SPIDER_API_KEY"]
    query = config["query"]
    first, last, state_code = config.get("first_name", ""), config.get("last_name", ""), config.get("state", "")
    selected = set(config["sources"])
    raw_dir = out / "raw"
    raw_dir.mkdir(exist_ok=True)
    results = []

    # CourtListener permits unauthenticated experiments; use a configured token when present.
    if "courtlistener" in selected:
        url = "https://www.courtlistener.com/api/rest/v4/search/?" + urlencode({"q": query, "type": "o", "page_size": 10})
        try:
            headers = {}
            if os.environ.get("COURTLISTENER_API_TOKEN"):
                headers["Authorization"] = "Token " + os.environ["COURTLISTENER_API_TOKEN"]
            status, content_type, text, data = direct_request(url, proxy, headers=headers)
            save_raw(raw_dir, "courtlistener", {"status": status, "content_type": content_type,
                                                  "body": data if data is not None else text})
            rows = (data or {}).get("results", []) if isinstance(data, dict) else []
            results.append(source_result("courtlistener", "ok" if status == 200 and data is not None else "inconclusive",
                                         len(rows), url="https://www.courtlistener.com/", api_status=status))
        except (OSError, RuntimeError, ValueError) as error:
            results.append(source_result("courtlistener", "error", error=type(error).__name__))

    # CAP's legacy API host currently responds with HTML in this environment; retain the
    # official search link and only mark API results available if JSON is returned.
    if "case_law" in selected:
        url = "https://api.case.law/v1/cases/?" + urlencode({"search": query, "page_size": 10, "format": "json"})
        token = os.environ.get("CASELAW_API_TOKEN")
        try:
            headers = {"Accept": "application/json"}
            status, content_type, text, data = direct_request(
                url, proxy, token=("Token " + token) if token else None, headers=headers)
            if data is not None:
                save_raw(raw_dir, "case_law", {"status": status, "content_type": content_type, "body": data})
                rows = data.get("results", []) if isinstance(data, dict) else []
                case_law_status = "ok" if status == 200 else "inconclusive"
                results.append(source_result("case_law", case_law_status, len(rows), url="https://case.law/", api_status=status))
            else:
                results.append(source_result("case_law", "api_unavailable", url="https://case.law/",
                                             note="The API endpoint returned a non-JSON response."))
        except (OSError, RuntimeError, ValueError) as error:
            results.append(source_result("case_law", "error", error=type(error).__name__))

    if "judyrecords" in selected:
        api_key = os.environ.get("JUDYRECORDS_API_KEY")
        if api_key:
            # Spider fetches JudyRecords' documented API endpoint; the key is supplied only in a server-side request header.
            params = {"search": query + (" " + state_code if state_code else ""), "maxWaitSec": 10}
            url = "https://www.judyrecords.com/search?" + urlencode(params)
            try:
                page = spider_get(url, spider_key, proxy,
                                  {"X-Api-Key": api_key, "Accept": "application/json"})
                content = page.get("content") or ""
                status = page.get("status")
                try:
                    data = json.loads(content)
                except json.JSONDecodeError:
                    data = None
                save_raw(raw_dir, "judyrecords", {"url": "https://www.judyrecords.com/search", "status": status,
                                                    "body": data if data is not None else content})
                count = (data.get("results") or data.get("data") or []) if isinstance(data, dict) else []
                results.append(source_result("judyrecords", "ok" if status == 200 and data is not None else "inconclusive",
                                             len(count) if isinstance(count, list) else 0,
                                             url="https://www.judyrecords.com/", api_status=status))
            except (OSError, RuntimeError, ValueError) as error:
                results.append(source_result("judyrecords", "error", error=type(error).__name__))
        elif proxy:
            try:
                from v1.scrape.judyrecords import search_judyrecords
                res = search_judyrecords(query, first_name=first, last_name=last, state=state_code, max_records=10, proxy_url=proxy)
                save_raw(raw_dir, "judyrecords", res)
                status = "ok" if res.get("status") == "ok" else "inconclusive"
                results.append(source_result("judyrecords", status, res.get("result_count", 0),
                                             url="https://www.judyrecords.com/",
                                             note=f"Mined {res.get('result_count', 0)} cases; {len(res.get('candidate_terms', []))} candidate terms."))
            except (OSError, RuntimeError, ValueError) as error:
                results.append(source_result("judyrecords", "error", error=type(error).__name__))
        else:
            results.append(source_result("judyrecords", "not_configured", url="https://www.judyrecords.com/api"))

    if "docket_alarm" in selected:
        user, password = os.environ.get("DOCKETALARM_USERNAME"), os.environ.get("DOCKETALARM_PASSWORD")
        if not user or not password:
            results.append(source_result("docket_alarm", "not_configured", url="https://www.docketalarm.com/api/"))
        else:
            try:
                credentials = urlencode({"username": user, "password": password}).encode()
                status, _, _, login = direct_request(
                    "https://www.docketalarm.com/api/v1/login/", proxy,
                    method="POST", body=credentials,
                    headers={"Content-Type": "application/x-www-form-urlencoded"})
                login_token = login.get("login_token") if isinstance(login, dict) else None
                if status != 200 or not login_token:
                    raise RuntimeError("Docket Alarm login failed.")
                search_url = "https://www.docketalarm.com/api/v1/search/?" + urlencode({
                    "login_token": login_token, "q": query, "limit": 10, "offset": 0,
                })
                status, content_type, text, data = direct_request(search_url, proxy)
                save_raw(raw_dir, "docket_alarm", {"status": status, "content_type": content_type,
                                                    "body": data if data is not None else text})
                rows = (data or {}).get("search_results", []) if isinstance(data, dict) else []
                results.append(source_result("docket_alarm", "ok" if status == 200 and data is not None else "inconclusive",
                                             len(rows), url="https://www.docketalarm.com/", api_status=status,
                                             retrieval="indexed search only; no live PACER fetch"))
            except (OSError, RuntimeError, ValueError) as error:
                results.append(source_result("docket_alarm", "error", error=type(error).__name__))

    if "arrests_org" in selected:
        slug = ARREST_STATE_SLUGS[state_code]
        url = "https://{}.arrests.org/search.php?{}".format(slug, urlencode({
            "fname": first, "lname": last, "fpartial": "",
        }))
        try:
            page = spider_get(url, spider_key, proxy)
            save_raw(raw_dir, "arrests_org", {"url": url, "status": page.get("status"),
                                               "error": page.get("error"), "content": page.get("content", "")})
            results.append(source_result("arrests_org", "page_captured" if page.get("status") == 200 else "inconclusive",
                                         url="https://www.arrests.org/", page_status=page.get("status"),
                                         note="Raw page preserved; verify each result against the linked court record."))
        except (OSError, RuntimeError, ValueError) as error:
            results.append(source_result("arrests_org", "error", error=type(error).__name__))

    if "court_record" in selected:
        results.append(source_result("court_record", "link_only", url="https://www.courtrecord.net/search?" + urlencode({"q": query}),
                                     note="Linked only; site terms restrict copying and commercial reuse."))
    if "google_scholar" in selected:
        results.append(source_result("google_scholar", "link_only", url="https://scholar.google.com/scholar?" + urlencode({"q": query}),
                                     note="No official public API was verified."))

    return results


def run_map(config, out):
    token = os.environ.get("MAPILLARY_ACCESS_TOKEN")
    if not token:
        results = [source_result("mapillary", "not_configured", url="https://www.mapillary.com/developer")]
    else:
        params = {
            "lat": config["latitude"], "lng": config["longitude"], "radius": 50,
            "limit": 10, "fields": "id,geometry,captured_at,is_pano",
        }
        url = "https://graph.mapillary.com/images?" + urlencode(params)
        try:
            status, content_type, text, data = direct_request(
                url, get_proxy(required=True), token="OAuth " + token)
            raw_dir = out / "raw"
            raw_dir.mkdir(exist_ok=True)
            save_raw(raw_dir, "mapillary", {"status": status, "content_type": content_type,
                                             "body": data if data is not None else text})
            rows = data.get("data", []) if isinstance(data, dict) else []
            results = [source_result("mapillary", "ok" if status == 200 and data is not None else "inconclusive",
                                     len(rows), url="https://www.mapillary.com/developer", api_status=status)]
        except (OSError, RuntimeError, ValueError) as error:
            results = [source_result("mapillary", "error", error=type(error).__name__)]
    results.extend([
        source_result("zoom_earth", "link_only", url="https://zoom.earth/",
                      note="No public data API was verified; the site uses multiple satellite/weather providers."),
        source_result("opensfm", "tool_reference", url="https://opensfm.org/",
                      note="Photogrammetry toolkit for user-supplied images; not a hosted API."),
    ])
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if not os.environ.get("SPIDER_API_KEY"):
        parser.error("SPIDER_API_KEY and WEBSHARE_PROXY_URL are required")
    try:
        get_proxy(required=True)
    except ValueError as error:
        parser.error(str(error))
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / "raw"
    raw_dir.mkdir(exist_ok=True)
    config = json.loads(args.input.read_text())
    results = run_legal(config, out) if config["mode"] == "legal" else run_map(config, out)
    report = {
        "mode": config["mode"],
        "query": config.get("query"),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "results": results,
        "caveat": "Search results are candidate records. Names alone do not establish identity or guilt; independently verify each result with the originating court.",
    }
    (out / "research-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print("Research complete: {} sources checked; {} raw result files saved.".format(
        len(results), len(list(raw_dir.glob("*.json")))), flush=True)


if __name__ == "__main__":
    raise SystemExit(main())
