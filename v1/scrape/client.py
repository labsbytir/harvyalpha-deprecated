"""Shared Spider transport used by network adapters and batch tools."""
import json
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ENDPOINT = "https://api.spider.cloud/unlimited/scrape"


def request(payload, key, proxy=None, timeout=150):
    body = dict(payload)
    if proxy:
        body["remote_proxy"] = proxy
    req = Request(ENDPOINT, data=json.dumps(body).encode(), headers={
        "Authorization": "Bearer " + key, "Content-Type": "application/json",
    })
    for attempt in range(3):
        try:
            with urlopen(req, timeout=timeout) as response:
                result = json.load(response)
            if not isinstance(result, list):
                raise ValueError("Unexpected Spider response")
            return result
        except HTTPError as error:
            if error.code in (429, 503) and attempt < 2:
                retry = error.headers.get("Retry-After", "2")
                time.sleep(min(30, int(retry)) if retry.isdigit() else 2)
                continue
            raise RuntimeError("Spider HTTP {}".format(error.code)) from None
        except URLError:
            if attempt < 2:
                time.sleep(2)
                continue
            raise RuntimeError("Connection to Spider failed") from None


def scrape(url, key, proxy=None, **options):
    return request({"url": url, **options}, key, proxy)


def scrape_batch(urls, key, proxy=None, **options):
    return request({"url": ",".join(url.replace(",", "%2C") for url in urls), **options}, key, proxy)
