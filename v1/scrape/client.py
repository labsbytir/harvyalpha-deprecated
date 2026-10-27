"""Shared Spider transport used by network adapters and batch tools."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

BASE = "https://api.spider.cloud"
ENDPOINT = BASE + "/unlimited/scrape"


def post(path, payload, key, proxy=None, timeout=150, retries=3):
    body = dict(payload)
    if proxy:
        body["remote_proxy"] = proxy
    req = Request(BASE + path, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
    })
    for attempt in range(retries):
        try:
            with urlopen(req, timeout=timeout) as response:
                return json.load(response), response.headers
        except HTTPError as error:
            headers = getattr(error, "headers", {})
            if error.code in (429, 503) and attempt < retries - 1:
                retry = headers.get("Retry-After", "2")
                time.sleep(min(30, int(retry)) if retry.isdigit() else 2)
                continue
            raise RuntimeError("Spider HTTP {}".format(error.code)) from None
        except URLError:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise RuntimeError("Connection to Spider failed") from None
    raise RuntimeError("Spider request failed")


def request(payload, key, proxy=None, timeout=150):
    result, _ = post("/unlimited/scrape", payload, key, proxy=proxy, timeout=timeout)
    if not isinstance(result, list):
        raise ValueError("Unexpected Spider response")
    return result


def scrape(url, key, proxy=None, **options):
    return request({"url": url, **options}, key, proxy)


def scrape_batch(urls, key, proxy=None, **options):
    return request({"url": ",".join(url.replace(",", "%2C") for url in urls), **options}, key, proxy)


def unlimited(endpoint, payload, key, proxy=None, timeout=150):
    return post("/unlimited/" + endpoint, payload, key, proxy=proxy, timeout=timeout)


def ai(endpoint, payload, key, proxy=None, timeout=150):
    return post("/ai/" + endpoint, payload, key, proxy=proxy, timeout=timeout)
