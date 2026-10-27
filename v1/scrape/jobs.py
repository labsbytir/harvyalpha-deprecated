"""Build scraper subprocess commands without putting credentials in arguments."""
from datetime import datetime
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlparse
import uuid

from proxy.config import get_proxy
from v1.scrape.profiles import profile_link

HERE = Path(__file__).resolve().parent.parent
WMN_CATEGORIES = {
    "archived", "art", "blog", "business", "dating", "finance", "gaming",
    "health", "hobby", "images", "misc", "music", "news", "political",
    "search", "shopping", "social", "tech", "video", "xx NSFW xx",
}
RESEARCH_SOURCES = {
    "case_law", "courtlistener", "docket_alarm", "judyrecords", "arrests_org",
    "court_record", "google_scholar",
}
ARREST_STATE_SLUGS = {
    "AL": "alabama", "AR": "arkansas", "AZ": "arizona", "CA": "california",
    "CO": "colorado", "FL": "florida", "GA": "georgia", "ID": "idaho",
    "IL": "illinois", "IN": "indiana", "IA": "iowa", "KS": "kansas",
    "KY": "kentucky", "LA": "louisiana", "ME": "maine", "MD": "maryland",
    "MI": "michigan", "MN": "minnesota", "MS": "mississippi", "MO": "missouri",
    "MT": "montana", "NE": "nebraska", "NV": "nevada", "NH": "newhampshire",
    "NJ": "newjersey", "NM": "newmexico", "NY": "newyork", "NC": "northcarolina",
    "ND": "northdakota", "OH": "ohio", "OK": "oklahoma", "OR": "oregon",
    "PA": "pennsylvania", "SC": "southcarolina", "TN": "tennessee", "TX": "texas",
    "UT": "utah", "VA": "virginia", "WV": "westvirginia", "WI": "wisconsin",
    "WY": "wyoming",
}


def job_command(url, parent, max_posts, max_linked):
    if not isinstance(url, str) or not url.strip() or len(url) > 2048:
        raise ValueError("Enter a public profile URL")
    url = url.strip()
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("Profile URLs must not contain credentials")
    if type(max_posts) is not int or type(max_linked) is not int or max_posts < 1 or max_linked < 0:
        raise ValueError("Post limit must be positive; linked-profile limit may be zero")
    facebook = parsed.scheme == "https" and parsed.hostname in ("facebook.com", "www.facebook.com")
    if facebook:
        if parsed.port not in (None, 443) or not re.fullmatch(r"/[A-Za-z0-9.]+/?", parsed.path) or parsed.query or parsed.fragment:
            raise ValueError("Use the Facebook profile's main URL, without extra paths or query parameters")
        seed = url
    else:
        account = profile_link(url)
        if not account:
            raise ValueError("Enter a Facebook profile URL or a supported public social-profile link")
        seed = account["url"]
    parent = Path(parent).expanduser().resolve()
    label = re.sub(r"[^A-Za-z0-9._-]", "_", parsed.path.strip("/") or parsed.hostname or "profile")[:60]
    output = parent / (label + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    command = [sys.executable, "-u"]
    if facebook:
        command += ["-m", "v1.scrape.facebook", seed, "--out", str(output),
                    "--max-posts", str(max_posts), "--max-linked-profiles", str(max_linked)]
    else:
        command += ["-m", "v1.scrape.profiles", "--url", seed, "--out", str(output),
                    "--max-profiles", str(max_linked + 1)]
    return command, output


def username_job_command(username, categories, parent):
    if not isinstance(username, str) or not re.fullmatch(r"[\w.-]{1,64}", username, re.UNICODE):
        raise ValueError("Use a username of 1–64 letters, numbers, dots, underscores, or hyphens")
    if (not isinstance(categories, list) or not categories
            or any(not isinstance(c, str) or c not in WMN_CATEGORIES for c in categories)):
        raise ValueError("Select one or more supported WhatsMyName categories")
    parent = Path(parent).expanduser().resolve()
    label = re.sub(r"[^A-Za-z0-9._-]", "_", username)[:60]
    output = parent / ("username-" + label + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    command = [sys.executable, "-u", "-m", "v1.scrape.username", "--username=" + username, "--out", str(output)]
    for category in categories:
        command += ["--category", category]
    return command, output


def research_job_command(payload, parent):
    if not isinstance(payload, dict) or payload.get("mode") not in ("legal", "map"):
        raise ValueError("Choose a legal-record search or a map image search")
    mode = payload["mode"]
    clean = {"mode": mode}
    if mode == "legal":
        query = payload.get("query", "")
        if not isinstance(query, str) or len(query.strip()) < 2 or len(query) > 200:
            raise ValueError("Enter a search query between 2 and 200 characters")
        sources = payload.get("sources")
        if (not isinstance(sources, list) or not sources
                or any(not isinstance(source, str) or source not in RESEARCH_SOURCES for source in sources)):
            raise ValueError("Select one or more supported legal sources")
        first, last = payload.get("first_name", ""), payload.get("last_name", "")
        state = payload.get("state", "")
        if not isinstance(first, str) or len(first) > 80 or not isinstance(last, str) or len(last) > 80:
            raise ValueError("First and last names must be 80 characters or fewer")
        if not isinstance(state, str) or (state and state not in ARREST_STATE_SLUGS):
            raise ValueError("Select a supported state")
        if "arrests_org" in sources and (not first.strip() or not last.strip() or not state):
            raise ValueError("Arrests.org requires first name, last name, and state")
        clean.update(query=query.strip(), first_name=first.strip(), last_name=last.strip(), state=state,
                     sources=list(dict.fromkeys(sources)))
        label = "legal"
    else:
        try:
            latitude, longitude = float(payload.get("latitude")), float(payload.get("longitude"))
        except (TypeError, ValueError):
            raise ValueError("Enter valid latitude and longitude coordinates") from None
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Coordinates are outside valid latitude/longitude ranges")
        clean.update(latitude=latitude, longitude=longitude)
        label = "map"
    parent = Path(parent).expanduser().resolve()
    output = parent / ("research-" + label + "-" + datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8])
    command = [sys.executable, "-u", "-m", "v1.scrape.research", "--input", str(output / "request.json"), "--out", str(output)]
    return command, output, clean


def validate_credentials(key, proxy):
    if not isinstance(key, str) or not key.strip():
        raise ValueError("SPIDER_API_KEY is required on the server")
    get_proxy({"WEBSHARE_PROXY_URL": proxy})


def redact(text, key, proxy, extra=()):
    secrets = [key, proxy, *extra]
    if proxy:
        parsed = urlparse(proxy)
        secrets.extend([parsed.password or "", unquote(parsed.password or "")])
    for secret in sorted(set(secrets), key=len, reverse=True):
        if secret:
            text = text.replace(secret, "[redacted]")
    return text
