"""Discover bio links and scrape their public pages through Spider Unlimited."""
import argparse
from collections import deque
import hashlib
import html
from html.parser import HTMLParser
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse

from scrape.client import request as spider_request
from scrape.facebook import walk
from proxy.config import get_proxy

# These are Spider recipe references, not separate scraping services.
RECIPES = {
    "x": ["twitter"], "bluesky": ["bluesky", "bsky-social"], "instagram": ["instagram"],
    "sssinstagram": ["sssinstagram-com"], "threads": ["threads", "threads-com"],
    "linkedin": ["linkedin"], "quora": ["quora"], "mastodon": ["mastodon"],
    "discord": ["discord"], "tiktok": ["tiktok-social"], "substack": ["substack"],
    "medium": ["medium"], "twitch": ["twitch-social"],
    "youtube": ["youtube-social"], "truthsocial": ["truth-social"],
    "blogspot": ["blogspot-com"], "steam": ["steamcommunity-com"],
    "github-blog": ["github-blog"], "europefreechat": ["europefreechat-com"],
}
HOSTS = {
    "x.com": "x", "twitter.com": "x", "bsky.app": "bluesky",
    "instagram.com": "instagram", "sssinstagram.com": "sssinstagram",
    "threads.net": "threads", "threads.com": "threads", "linkedin.com": "linkedin",
    "quora.com": "quora", "mastodon.social": "mastodon", "discord.com": "discord",
    "discord.gg": "discord", "tiktok.com": "tiktok", "substack.com": "substack",
    "medium.com": "medium", "twitch.tv": "twitch",
    "youtube.com": "youtube", "truthsocial.com": "truthsocial",
    "blogspot.com": "blogspot", "steamcommunity.com": "steam",
    "github.blog": "github-blog", "bsky.social": "bluesky",
    "europefreechat.com": "europefreechat",
}
URL_PATTERN = re.compile(r"https?://[^\s<>\"']+")


def profile_link(value, base="", federated=False):
    """Recognize profile links, not arbitrary posts, downloads, or lookalike hosts."""
    try:
        url = urljoin(base, html.unescape(value))
        p = urlparse(url)
        if p.scheme not in ("https", "http") or p.username or p.password or p.port not in (None, 80, 443):
            return None
        host = (p.hostname or "").lower().removeprefix("www.")
        if host in ("l.facebook.com", "lm.facebook.com") and p.path == "/l.php":
            return profile_link(parse_qs(p.query).get("u", [""])[0], federated=federated)
        platform = HOSTS.get(host)
        if host.endswith(".substack.com"):
            platform = "substack"
        elif host.endswith(".blogspot.com"):
            platform = "blogspot"
        if not platform and federated and re.fullmatch(r"/@[A-Za-z0-9_.-]+/?", p.path):
            platform = "mastodon"
        if not platform:
            return None
        parts = [unquote(s) for s in p.path.split("/") if s]
        if any(s in (".", "..") or re.search(r"[/\\?#\x00-\x1f]", s) for s in parts):
            return None
        kind = "profile"
        if platform in ("x", "instagram", "threads", "twitch"):
            if len(parts) != 1 or parts[0].lower() in {
                "p", "reel", "reels", "explore", "accounts", "login", "signup",
                "home", "search", "i", "intent", "share", "settings", "directory",
            }:
                return None
        elif platform == "bluesky":
            if host == "bsky.social" and not parts:
                kind = "service"
            elif host != "bsky.app" or len(parts) != 2 or parts[0] != "profile":
                return None
        elif platform == "linkedin":
            if len(parts) != 2 or parts[0] not in ("in", "company", "pub"):
                return None
        elif platform == "quora":
            if len(parts) != 2 or parts[0] != "profile":
                return None
        elif platform in ("mastodon", "tiktok", "medium", "truthsocial"):
            if len(parts) != 1 or not parts[0].startswith("@") or len(parts[0]) < 2:
                return None
        elif platform == "youtube":
            if len(parts) in (2, 3) and parts[-1] in ("about", "videos", "shorts", "streams", "featured"):
                parts = parts[:-1]
            if not ((len(parts) == 1 and parts[0].startswith("@") and len(parts[0]) > 1)
                    or (len(parts) == 2 and parts[0] in ("channel", "c", "user"))):
                return None
            if len(parts) == 1:
                parts[0] = parts[0].lower()
        elif platform == "steam":
            if len(parts) != 2 or parts[0] not in ("id", "profiles", "groups"):
                return None
            if parts[0] == "profiles" and not parts[1].isdigit():
                return None
            if parts[0] == "groups":
                kind = "community"
        elif platform == "blogspot":
            if parts:
                return None
            kind = "publication" if host != "blogspot.com" else "service"
        elif platform == "github-blog":
            if not parts:
                kind = "publication"
            elif len(parts) != 2 or parts[0] != "author":
                return None
        elif platform == "europefreechat":
            if parts:
                return None
            kind = "community"
        elif platform == "substack":
            if host == "substack.com" and (len(parts) != 1 or not parts[0].startswith("@")):
                return None
            if host.endswith(".substack.com") and parts:
                return None
        elif platform == "discord":
            if host == "discord.gg" and len(parts) == 1:
                pass
            elif host == "discord.com" and len(parts) == 2 and parts[0] in ("invite", "users"):
                pass
            else:
                return None
            kind = "community-invite" if host == "discord.gg" or parts[0] == "invite" else "profile"
        elif platform == "sssinstagram":
            if parts:
                return None
            kind = "utility"  # A downloader site, not an Instagram identity.
        if platform == "x":
            host = "x.com"
        elif platform == "threads":
            host = "www.threads.com"
        path = "/" + "/".join(quote(s, safe="@:") for s in parts) if parts else "/"
        if platform in ("x", "instagram", "threads", "twitch", "bluesky", "tiktok", "mastodon", "truthsocial"):
            path = path.lower()
        canonical = "https://" + host + path.rstrip("/")
        return {"url": canonical, "platform": platform, "kind": kind}
    except (ValueError, TypeError):
        return None


def validate_public_destination(url):
    host = urlparse(url).hostname
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError:
        raise ValueError("Cannot resolve linked profile host") from None
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Linked profile host is not publicly routable")


class PageData(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.links = []
        self.json_ld = []
        self.script = None
        self.visible_text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        scope = bool(self.stack and self.stack[-1][1]) or bool(re.search(
            r"\bbio\b|profile[-_]description|profile[-_]bio|about[-_]me|profile[-_]intro",
            attrs.get("class", "") + " " + attrs.get("id", ""), re.I))
        rel_me = "me" in attrs.get("rel", "").split()
        if tag == "a" and attrs.get("href") and (scope or rel_me):
            self.links.append((attrs["href"], rel_me))
        if tag == "script" and attrs.get("type") == "application/ld+json":
            self.script = ""
        if tag not in {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}:
            self.stack.append((tag, scope))

    def handle_endtag(self, tag):
        if tag == "script" and self.script is not None:
            try:
                self.json_ld.append(json.loads(self.script))
            except ValueError:
                pass
            self.script = None
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, text):
        if self.script is not None:
            self.script += text
        elif not any(tag in ("script", "style") for tag, _ in self.stack):
            self.visible_text.append(text)


def page_nodes(page, parsed):
    yield from walk(page.get("json_data"))
    yield from walk(parsed.json_ld)
    content = page.get("content") or ""
    if isinstance(content, str) and content.lstrip().startswith(("{", "[")):
        try:
            yield from walk(json.loads(content))
        except ValueError:
            pass


def _extract_social(page, account):
    parsed = PageData()
    parsed.feed(page.get("content") or "")
    nodes = list(page_nodes(page, parsed))
    handle = unquote(urlparse(account["url"]).path.rstrip("/").split("/")[-1]).lstrip("@").casefold()
    candidates = list(parsed.links)
    posts = {}
    identity_found = False
    for node in nodes:
        # Identity descriptions and sameAs are bio evidence; arbitrary post links are not.
        username = node.get("username") or node.get("handle") or node.get("screen_name")
        legacy = node.get("legacy") or {}
        if not username and isinstance(legacy, dict):
            username = legacy.get("screen_name")
        same_profile = isinstance(username, str) and username.lstrip("@").casefold() == handle
        schema_url = node.get("url")
        schema_types = node.get("@type")
        schema_types = schema_types if isinstance(schema_types, list) else [schema_types]
        if any(t in ("Person", "ProfilePage") for t in schema_types) and isinstance(schema_url, str) and schema_url.rstrip("/") == account["url"]:
            identity_found = True
            same_as = node.get("sameAs") or []
            candidates.extend((u, False) for u in ([same_as] if isinstance(same_as, str) else same_as) if isinstance(u, str))
        if same_profile:
            identity_found = True
            bio_data = {k: node.get(k) for k in ("external_url", "bio_links", "website", "entities")}
            if isinstance(legacy, dict):
                bio_data["legacy_entities"] = legacy.get("entities")
            for part in walk(bio_data):
                for key in ("external_url", "expanded_url", "url"):
                    if isinstance(part.get(key), str):
                        candidates.append((part[key], False))
            if isinstance(node.get("external_url"), str):
                candidates.append((node["external_url"], False))
            for field in (node.get("biography"), node.get("description"), legacy.get("description") if isinstance(legacy, dict) else None):
                if isinstance(field, str):
                    candidates.extend((u, False) for u in URL_PATTERN.findall(field))
        post = None
        video = node.get("videoRenderer")
        if account["platform"] == "youtube" and isinstance(video, dict) and video.get("videoId"):
            owner_runs = (video.get("ownerText") or video.get("longBylineText") or {}).get("runs") or []
            owner_urls = []
            for owner_run in owner_runs:
                endpoint = (owner_run.get("navigationEndpoint") or {}).get("browseEndpoint") or {}
                owner_path = endpoint.get("canonicalBaseUrl")
                if not owner_path and endpoint.get("browseId"):
                    owner_path = "/channel/" + endpoint["browseId"]
                linked = profile_link(owner_path, "https://youtube.com/") if owner_path else None
                if linked:
                    owner_urls.append(linked["url"])
            if account["url"] in owner_urls:
                title = video.get("title") or {}
                description = video.get("descriptionSnippet") or {}
                post = {"id": str(video["videoId"]), "url": "https://www.youtube.com/watch?v=" + video["videoId"],
                        "title": title.get("simpleText") or "".join(r.get("text", "") for r in title.get("runs") or []),
                        "text": "".join(r.get("text", "") for r in description.get("runs") or []),
                        "timestamp_text": (video.get("publishedTimeText") or {}).get("simpleText"),
                        "ownership_verified": True}
        if node.get("__typename") == "Tweet" and isinstance(legacy, dict) and legacy.get("full_text"):
            user = ((node.get("core") or {}).get("user_results") or {}).get("result") or {}
            author = (user.get("legacy") or {}).get("screen_name") or (user.get("core") or {}).get("screen_name")
            if isinstance(author, str) and author.casefold() == handle:
                pid = node.get("rest_id") or legacy.get("id_str")
                if pid:
                    post = {
                        "id": str(pid), "url": f"https://x.com/{author}/status/{pid}",
                        "text": legacy["full_text"], "timestamp": legacy.get("created_at"),
                        "author": "@" + author,
                        "like_count": legacy.get("favorite_count"),
                        "repost_count": legacy.get("retweet_count"),
                        "reply_count": legacy.get("reply_count"),
                        "quote_count": legacy.get("quote_count"),
                        "bookmark_count": legacy.get("bookmark_count"),
                        "view_count": (node.get("views") or {}).get("count"),
                        "ownership_verified": True,
                    }
        record, author = node.get("record"), node.get("author")
        if isinstance(record, dict) and record.get("$type") == "app.bsky.feed.post" and isinstance(author, dict) and str(author.get("handle", "")).casefold() == handle and node.get("uri"):
            post = {"id": node["uri"], "url": f"https://bsky.app/profile/{author['handle']}/post/{node['uri'].split('/')[-1]}", "text": record.get("text"), "timestamp": record.get("createdAt"), "ownership_verified": True}
        owner = node.get("owner") or node.get("user")
        if account["platform"] in ("instagram", "threads") and isinstance(owner, dict) and str(owner.get("username", "")).casefold() == handle:
            code = node.get("shortcode") or node.get("code")
            caption = node.get("caption")
            if code and ("taken_at_timestamp" in node or "taken_at" in node):
                text = caption.get("text") if isinstance(caption, dict) else None
                if not text:
                    text = next((n.get("text") for n in walk(node.get("edge_media_to_caption")) if n.get("text")), None)
                domain, path = ("www.instagram.com", "p") if account["platform"] == "instagram" else ("www.threads.com", f"@{handle}/post")
                post = {"id": str(node.get("id") or code), "url": f"https://{domain}/{path}/{code}/", "text": text, "timestamp": node.get("taken_at_timestamp") or node.get("taken_at"), "ownership_verified": True}
        if account["platform"] == "tiktok" and isinstance(node.get("author"), (str, dict)) and node.get("id") and "desc" in node:
            author = node["author"] if isinstance(node["author"], str) else node["author"].get("uniqueId")
            if isinstance(author, str) and author.casefold() == handle:
                post = {"id": str(node["id"]), "url": f"https://www.tiktok.com/@{author}/video/{node['id']}", "text": node["desc"], "timestamp": node.get("createTime"), "ownership_verified": True}
        mastodon_account = node.get("account")
        if account["platform"] in ("mastodon", "truthsocial") and isinstance(mastodon_account, dict) and node.get("id") and "content" in node:
            author_url = mastodon_account.get("url")
            if isinstance(author_url, str) and author_url.rstrip("/").casefold() == account["url"].casefold():
                post = {"id": str(node["id"]), "url": node.get("url") or f"https://truthsocial.com/@{handle}/posts/{node['id']}",
                        "text_html": node["content"], "timestamp": node.get("created_at"),
                        "like_count": node.get("favourites_count"), "repost_count": node.get("reblogs_count"),
                        "reply_count": node.get("replies_count"), "ownership_verified": True}
        if any(t in ("SocialMediaPosting", "BlogPosting", "Article", "DiscussionForumPosting", "VideoObject") for t in schema_types) and isinstance(node.get("url"), str):
            author = node.get("author") or {}
            owner_url = author.get("url") if isinstance(author, dict) else None
            post = {"id": node.get("@id") or node["url"], "url": node["url"], "text": node.get("articleBody") or node.get("text") or node.get("description"), "title": node.get("headline") or node.get("name"), "timestamp": node.get("datePublished") or node.get("uploadDate"), "ownership_verified": owner_url == account["url"]}
        if post:
            post["platform"] = account["platform"]
            post["source"] = page.get("url")
            posts[post["id"]] = post
    links = {}
    for value, federated in candidates:
        linked = profile_link(value, page.get("url") or account["url"], federated)
        if linked and linked["url"] != account["url"]:
            links[linked["url"]] = linked
    metadata = page.get("metadata") or {}
    login_renderer = any("login" in str(n.get("__typename", "")).lower() and "renderer" in str(n.get("__typename", "")).lower() for n in nodes)
    login_wall = not posts and not identity_found and (login_renderer or bool(re.search(
        r"log into instagram|log in to continue|sign in to continue|sign in to x",
        " ".join(parsed.visible_text), re.I)))
    return {**account, "title": metadata.get("title"), "description": metadata.get("description"),
            "posts": list(posts.values()), "bio_links": list(links.values()),
            "status": page.get("status"), "complete": False, "login_wall_detected": login_wall,
            "availability": "login_wall" if login_wall else ("public_records" if posts or identity_found else "unverified_shell"),
             "limitation": "Only exposed structured records; login walls and missing data are not empty accounts"}


def adapter_for(platform):
    if platform == "facebook":
        from scrape import facebook
        return facebook
    if platform == "instagram":
        from scrape import instagram
        return instagram
    if platform == "threads":
        from scrape import threads
        return threads
    if platform == "x":
        from scrape import x
        return x
    if platform == "truthsocial":
        from scrape import truthsocial
        return truthsocial
    return None


def fetch(url, key, proxy):
    account = profile_link(url)
    adapter = adapter_for(account["platform"]) if account else None
    payload = adapter.payload(url, proxy) if adapter else {
        "url": url, "request": "browser", "return_format": "raw",
        "return_json_data": True, "return_page_links": True, "metadata": True,
        "cache": False, "session": False, "return_cookies": False,
    }
    return spider_request(payload, key, proxy)


def extract_social(page, account):
    adapter = adapter_for(account["platform"])
    return adapter.extract_profile(page, account) if adapter else _extract_social(page, account)


def scrape_linked_profiles(source_url, links, output, key, proxy, max_profiles=20):
    output.mkdir(parents=True, exist_ok=True)
    os.chmod(output, 0o700)
    pending = deque((source_url, url) for url in links)
    visited, accounts, edges, failures = set(), [], [], []
    kinds = {source_url: "account"}
    while pending and len(visited) < max_profiles:
        source, value = pending.popleft()
        account = profile_link(value, source)
        if not account:
            continue
        url = account["url"]
        kinds[url] = account["kind"]
        edge = {"source": source, "target": url, "type": "bio_links_to", "ownership_verified": False}
        if source != url and edge not in edges:
            edges.append(edge)
        if url in visited:
            continue
        visited.add(url)
        folder = output / account["platform"] / hashlib.sha256(url.encode()).hexdigest()[:16]
        folder.mkdir(parents=True, exist_ok=True)
        try:
            validate_public_destination(url)
            pages = fetch(url, key, proxy)
            (folder / "raw.json").write_text(json.dumps(pages, ensure_ascii=False))
            good = [p for p in pages if p.get("status") == 200 and not p.get("error")]
            if not good:
                raise ValueError("Linked page fetch failed")
            result = extract_social(good[0], account)
            (folder / "profile.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
            posts_dir = folder / "posts"
            posts_dir.mkdir(exist_ok=True)
            for post in result["posts"]:
                filename = hashlib.sha256(post["id"].encode()).hexdigest()[:20] + ".json"
                (posts_dir / filename).write_text(json.dumps(post, ensure_ascii=False, indent=2))
            accounts.append({"url": url, "platform": account["platform"], "kind": account["kind"], "posts": len(result["posts"]), "login_wall_detected": result["login_wall_detected"], "availability": result["availability"], "folder": str(folder)})
            if account["kind"] in ("profile", "publication"):
                pending.extend((url, p["url"]) for p in result["bio_links"])
        except (RuntimeError, ValueError, OSError, TimeoutError):
            failures.append({"url": url, "error": "Linked profile unavailable; raw response retained when received"})
    result = {"source": source_url, "accounts": accounts, "links": edges, "failures": failures,
              "profile_limit": max_profiles, "pending_links": len(pending), "complete": False,
              "images_downloaded": 0, "account_cookies_supplied": False,
              "recipes": {k: [f"https://spider.cloud/scrapers/{s}-scraper/" for s in v] for k, v in RECIPES.items()}}
    (output / "manifest.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    graph = {"nodes": [{"id": source_url, "type": kinds.get(source_url, "account")}], "links": edges}
    seen = {source_url}
    for edge in edges:
        for url in (edge["source"], edge["target"]):
            if url not in seen:
                seen.add(url)
                graph["nodes"].append({"id": url, "url": url, "type": kinds.get(url, "linked-profile")})
    (output / "network.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path, nargs="?", help="Existing Facebook snapshot folder")
    parser.add_argument("--url", help="Start directly from a supported public social profile")
    parser.add_argument("--out", type=Path, help="Output folder when starting from --url")
    parser.add_argument("--max-profiles", type=int, default=20)
    args = parser.parse_args()
    if not os.environ.get("SPIDER_API_KEY") or args.max_profiles < 0:
        parser.error("SPIDER_API_KEY and a nonnegative --max-profiles are required")
    if bool(args.snapshot) == bool(args.url):
        parser.error("Provide either a snapshot folder or --url")
    if args.url:
        account = profile_link(args.url)
        if not account or not args.out or args.max_profiles < 1:
            parser.error("--url requires a supported profile URL, --out and --max-profiles >= 1")
        source, links, output = account["url"], [account["url"]], args.out
        if output.exists() and any(output.iterdir()):
            parser.error("Output folder is not empty; choose a new folder")
    else:
        if args.out:
            parser.error("--out is only used with --url")
        details = json.loads((args.snapshot / "profile-details.json").read_text())
        source, links, output = details["url"], details["external_links"], args.snapshot / "linked-profiles"
    result = scrape_linked_profiles(source, links, output,
                                    os.environ["SPIDER_API_KEY"], get_proxy(), args.max_profiles)
    print(f"Saved {len(result['accounts'])} linked profile snapshots; {len(result['failures'])} failed")


if __name__ == "__main__":
    main()
