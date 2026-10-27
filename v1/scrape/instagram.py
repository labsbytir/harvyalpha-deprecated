"""Instagram profile request and extraction adapter."""
def payload(url, proxy=None):
    body = {"url": url, "request": "browser", "return_format": "raw",
            "return_json_data": True, "return_page_links": True, "metadata": True,
            "cache": False, "session": False, "return_cookies": False}
    if proxy:
        body["remote_proxy"] = proxy
    return body


def extract_profile(page, account):
    from v1.scrape.profiles import _extract_social
    return _extract_social(page, account)
