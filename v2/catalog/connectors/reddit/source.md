# Reddit — r/datasets and the wider Reddit API

Key: `none required` for the public JSON endpoints (`.json` after any URL, e.g. `r/datasets.json`). OAuth keys only needed for write actions or high-volume reads. Register an app at https://www.reddit.com/prefs/apps/ if you want OAuth.

Endpoint: `https://www.reddit.com/`
Auth: none (public read); `Authorization: Bearer <token>` (write or higher rate)
Format: `.json` suffix on any URL

Documentation:
- API home: https://www.reddit.com/dev/api/
- OAuth guide: https://github.com/reddit-archive/reddit/wiki/OAuth2
- App registration: https://www.reddit.com/prefs/apps/
- r/datasets subreddit: https://www.reddit.com/r/datasets/
- Data catalog: https://www.reddit.com/r/datasets/wiki

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/reddit.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

REDDIT_UA = "OpenTIR-Data/0.1 (by /u/opentir)"  # Reddit requires a custom UA
REDDIT_TOKEN = os.environ.get("REDDIT_ACCESS_TOKEN", "")


class Fetcher(BaseFetcher):
    async def fetch(self):
        headers = {"User-Agent": REDDIT_UA}
        if REDDIT_TOKEN:
            headers["Authorization"] = f"Bearer {REDDIT_TOKEN}"
        async with httpx.AsyncClient(
            base_url="https://www.reddit.com",
            timeout=60.0,
            headers=headers,
        ) as client:
            # 1. r/datasets — community-curated dataset pointers
            for sort in ("hot", "top", "new", "rising"):
                r = await client.get(f"/r/datasets/{sort}.json?limit=100&t=year")
                r.raise_for_status()
                for child in r.json()["data"]["children"]:
                    d = child["data"]
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection=f"r-datasets-{sort}",
                        source_id=d["id"],
                        source_url=f"https://www.reddit.com{d['permalink']}",
                        bundle_url=f"/r/datasets/{sort}.json?limit=100&t=year",
                        fetched_at=self.now(),
                        payload=orjson.dumps(d),
                        payload_format="json",
                        metadata={"submission": d, "subreddit": "datasets"},
                    )
```

## Quick call — verify

```bash
# r/datasets top of all time (last year)
curl -sL -A "OpenTIR-Data/0.1 (by /u/opentir)" \
  "https://www.reddit.com/r/datasets/top.json?limit=2&t=year" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); [print(c['data']['title'], '->', c['data']['url']) for c in d['data']['children']]"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /r/datasets/{sort}.json?limit=N&t=                 # community dataset pointers
GET /r/all/search.json?q=climate&sort=top&t=year      # cross-reddit search
GET /r/{subreddit}/comments/{id}.json                 # full thread + comments
GET /user/{username}/about.json                      # user profile
GET /api/v1/me                                       # OAuth-authenticated
GET /api/info.json?id=t1,t2,t3                        # bulk lookup by fullname
GET /subreddits/search.json?q=                        # subreddit search
GET /api/trending_subreddits.json                     # trending list
```

Query params on listings: `limit` (max 100), `after`/`before` (cursor), `t=hour|day|week|month|year|all`, `sort=hot|new|top|controversial|rising`.

## Notes

- **Reddit blocks default user agents.** You must send a unique UA like `OpenTIR-Data/0.1 (by /u/opentir)`. The default `python-requests/X.Y` UA gets 429.
- **`r/datasets` is a community-curated pointer list**, not a structured dataset catalog. Posts link to datasets hosted elsewhere (Kaggle, GitHub, government sites). The fetcher should follow the linked URL, not the Reddit post.
- **Public read access** (`.json` endpoints) is anonymous. Rate limit is ~60 requests / minute / IP if you use a custom UA. OAuth gets 600 req / 10 min.
- **For high-volume ingestion**, register a "script" app at https://www.reddit.com/prefs/apps/, get a refresh token, and authenticate with the password grant (deprecated but still works for personal use) or the device flow.
- **Listing endpoints** return up to 100 items per page, paginated by `after` token.
- **Comment threads** can be deeply nested; the JSON collapses to a tree. Use `depth=N` to limit recursion.
- **Cross-source dedup**: r/datasets posts link to data already in our system (Kaggle, GitHub, CKAN, etc.). The `dataset_fingerprint` resolver will merge them when we follow the link and ingest the underlying file.

