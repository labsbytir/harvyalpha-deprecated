# MediaCloud

Key: `pending — register at https://search.mediacloud.org/` (free for non-commercial academic and research use; commercial use requires a paid partnership).

Endpoint (v3.1.10, the only public API): `https://search.mediacloud.org/api/`
Auth: `Authorization: Token <key>` header
Format: `JSON`

Documentation:
- Main site: https://search.mediacloud.org/
- Sign up: https://search.mediacloud.org/
- Python client: https://pypi.org/project/mediacloud/ (5.1.0; wraps v3.1.10 API)
- Python client source: https://github.com/mediacloud/api-client
- API endpoints reference: in the client `mediacloud/api.py`
- About MediaCloud: https://mediacloud.org/about

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/mediacloud.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

MC_API_KEY = os.environ["MEDIACLOUD_API_KEY"]
BASE = "https://search.mediacloud.org/api"


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=BASE,
            timeout=60.0,
            headers={"Authorization": f"Token {MC_API_KEY}",
                     "User-Agent": "OpenTIR-Data/0.1",
                     "Accept": "application/json"},
        ) as client:
            # 1. Health check + version
            r = await client.get("/version")
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="version",
                source_id="version",
                source_url="https://search.mediacloud.org/",
                bundle_url="/version",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="json",
                metadata={"version": r.json()},
            )

            # 2. Story count for a query (US national collection)
            US_NATIONAL_COLLECTION = 34412234
            for query in ("climate change", "open data", "ai safety", "russia ukraine"):
                r = await client.get("/stories_public/count",
                                     params={"q": query, "fq": f"collection_ids:{US_NATIONAL_COLLECTION}"})
                r.raise_for_status()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="story_counts",
                    source_id=query,
                    source_url=f"https://search.mediacloud.org/search?q={query.replace(' ', '+')}",
                    bundle_url=f"/stories_public/count?q={query}",
                    fetched_at=self.now(),
                    payload=r.content,
                    payload_format="json",
                    metadata={"query": query, "collection": US_NATIONAL_COLLECTION, "result": r.json()},
                )

            # 3. List all collections (sources / media)
            r = await client.get("/collections/list")
            r.raise_for_status()
            for coll in r.json():
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="collections",
                    source_id=str(coll.get("id")),
                    source_url=f"https://search.mediacloud.org/dashboard/sources",
                    bundle_url=f"/collections/{coll.get('id')}",
                    fetched_at=self.now(),
                    payload=b"",  # metadata only
                    payload_format="json",
                    metadata={"collection": coll},
                    is_remote_only=True,
                )
```

## Quick call — verify

```bash
# Version (no auth)
curl -sL "https://search.mediacloud.org/api/version" | head -c 200

# Story count (needs API key)
curl -sL -H "Authorization: Token YOUR_KEY" \
  "https://search.mediacloud.org/api/stories_public/count?q=climate+change&fq=collection_ids:34412234" \
  | head -c 500
```

Expected: version returns `{"GIT_REV": "...", "now": ..., "version": "3.1.10"}`; story count returns `{"count": N}` with a real number of matching stories.

## Endpoints used (verified live 2026-09-04)

```text
GET /api/version                                            # no auth
GET /api/auth/profile                                       # who am I (auth required)
GET /api/stories_public/count?q=&fq=                        # matching-story count
GET /api/stories_public/list?q=&fq=&sort=                  # list of stories (paginated)
GET /api/stories_public/word_matrix?q=&fq=                 # top words in matching stories
GET /api/sentences/count?q=&fq=                            # matching-sentence count
GET /api/sentences/list?q=&fq=                             # sentences (the raw text)
GET /api/collections/list                                   # media sources, by ID
GET /api/collections/single?id=                            # one collection
GET /api/sources/list                                       # individual feeds
GET /api/tags/list?type=                                    # tags (people, organizations, stories)
GET /api/feeds/list                                         # RSS/Atom feed metadata
GET /api/health                                             # no auth
```

Query params:
- `q` — query string (MediaCloud query language, similar to Solr/Elasticsearch)
- `fq` — filter query; `fq=collection_ids:34412234` filters to a collection
- `start_date`, `end_date` — `YYYY-MM-DD`
- `sort` — `processed_stories desc`, `random` (sampling)
- `limit` — max 10,000
- `page` — 0-indexed pagination
- `last_processed_stories_id` — cursor pagination for streams

## Notes

- MediaCloud indexes **billions of stories** from ~100,000+ global media sources, dating back to the early 2000s. It's the most comprehensive open news corpus.
- Free tier: ~2 requests / minute, 50,000 stories per query. Researchers with academic affiliations can get higher limits via the dashboard.
- **Two parallel APIs:** the dashboard at `search.mediacloud.org` and the older API at `api.mediacloud.org` (currently down from this network). The dashboard API is the one in active use; the Python client targets it.
- The Python client is the recommended entry point — it handles the 2-req/min rate limit, the cursor pagination, and the time-range slicing.
- **For OSINT**: most useful for narrative tracking ("how many stories mentioned X this week?"), source coverage analysis ("which media outlets cover X?"), and word co-occurrence ("what words appear near Y in the same story?").
- **Collection IDs are stable**: US National is `34412234`, India National is `34412118`. The full list of ~100,000 collections is in `/api/collections/list`.
- **Cross-source dedup**: MediaCloud story ids are URL-anchored; a story on MediaCloud is the same story as the URL it links to. Dedup against RSS feeds, NewsAPI, etc. is automatic via URL fingerprint.
- **License caveat**: MediaCloud is free for non-commercial use. If you're building a product, talk to the team about a partnership.
- **Common queries worth pulling:** top stories per day per country; "X AND Y" co-mention time series; "X NOT Y" exclusion; "media_id:NNN" to filter to one outlet.


## Migrated Context (From Media_Cloud_Integration.md)

# Media Cloud Ingestion

