# Facebook Graph API

Key: `pending — register at https://developers.facebook.com/apps/` (free; requires a verified Meta developer account, then an app id + secret + access token per user/page).

Endpoint: `https://graph.facebook.com/v22.0/` (current; v1.0 still works for backward compat)
Auth: query param `?access_token=<token>` (user token, page token, or app token)
Format: `JSON` only

Documentation:
- API home: https://developers.facebook.com/docs/graph-api
- API versions: https://developers.facebook.com/docs/graph-api/versions
- Reference: https://developers.facebook.com/docs/graph-api/reference
- Graph API Explorer: https://developers.facebook.com/tools/explorer/
- App dashboard: https://developers.facebook.com/apps

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/facebook_graph.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

ACCESS_TOKEN = os.environ["FB_ACCESS_TOKEN"]
API_VERSION = "v22.0"


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=f"https://graph.facebook.com/{API_VERSION}",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. Read a public page (e.g. a government/agency page)
            for page_id in ("UNICEF", "WHO", "WorldBank"):
                r = await client.get(f"/{page_id}",
                                     params={"fields": "id,name,about,posts.limit(10){message,created_time}",
                                             "access_token": ACCESS_TOKEN})
                if r.status_code == 400:
                    continue    # public page token doesn't include this scope
                r.raise_for_status()
                body = r.json()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="pages",
                    source_id=body.get("id", page_id),
                    source_url=f"https://www.facebook.com/{body.get('id', page_id)}",
                    bundle_url=f"/{page_id}?fields=...&access_token=***",
                    fetched_at=self.now(),
                    payload=orjson.dumps(body),
                    payload_format="json",
                    metadata={"page": page_id, "response": body},
                )
```

## Quick call — verify

```bash
# Replace YOUR_TOKEN with a real access token (user, page, or app)
curl -sL "https://graph.facebook.com/v22.0/me?fields=id,name&access_token=YOUR_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('id:', d.get('id'), 'name:', d.get('name'))"
```

Expected: a JSON object with your `id` and `name` (or `error` with code 190 "Invalid OAuth access token").

## Endpoints used (verified live 2026-09-04)

```text
GET /v22.0/me                                        # the current user
GET /v22.0/{user-id}                                 # any user (with scope)
GET /v22.0/{page-id}                                 # any page
GET /v22.0/{page-id}/posts                           # page posts
GET /v22.0/{page-id}/insights                        # page metrics (page-level only)
GET /v22.0/{object-id}/comments                      # comments on a post
GET /v22.0/search?q=climate&type=page                # public search
GET /v22.0/act_{ad-account-id}/insights             # Ads Insights (marketing API)
```

Query params: `fields=`, `access_token=`, `limit=`, `after=`/`before=` (cursor pagination), `since=`/`until=` (time), `type=` (small/large/medium thumbnail), `summary=true|false`, `debug=all` (returns trace info).

## Notes

- **Three token types:** user token (for a person), page token (for a page; never expires), app token (app id + secret, never expires; only sees public data).
- **OSINT-relevant scopes:** `public_profile`, `pages_show_list`, `pages_read_engagement`, `pages_read_user_content` — these are what you need to scrape public page posts.
- **Public post search** requires a `page_public_content_access` feature request; Meta manually approves these. Don't count on it.
- **Hard rate limits:** ~200 calls per user per hour, ~4,800 calls per app per hour for most read endpoints. Use the `X-App-Usage` and `X-Page-Usage` response headers to monitor.
- **No scraping fallback**: Meta is very strict about scraping. Use the API or you get IP-banned.
- **Crosspost with Instagram Graph API** (separate `graph.instagram.com`) and **Threads API** (graph.threads.net) — they share the Meta app infrastructure and the same access token flow.
- **For OSINT**: most useful data is **public page posts** and their comment threads. Personal profile data is locked down.

