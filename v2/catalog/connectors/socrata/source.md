# Socrata (SODA) connector

Key: `none required` — public SODA endpoints work without a key. App tokens are free at https://data.<portal>/profile/app_tokens and raise the rate limit from anonymous (~1 req/sec per IP) to 5,000 req/hr per token.

Endpoint (catalog): `<base>/api/catalog/v1` (returns dataset metadata for the whole portal)
Endpoint (data):     `<base>/resource/<4x4-xxxx>.json?$query=...` (SODA Query Language)
Discovery:           `<base>/api/views.json?limit=50` (older discovery format, still works)
Domain find:         `<base>/api/domain.json` (returns the portal's "domain id" used internally)

Documentation:
- SODA reference: https://dev.socrata.com/docs/endpoints.html
- Query language (SoQL): https://dev.socrata.com/docs/queries/
- Discovery API: https://dev.socrata.com/docs/discovery.html
- App tokens: https://dev.socrata.com/docs/authentication.html

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/socrata.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

APP_TOKEN = os.environ.get("SOCRATA_APP_TOKEN", "")  # optional but recommended


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1", "X-App-Token": APP_TOKEN},
        ) as client:
            # 1. Catalog discovery — get every dataset id + name on the portal
            r = await client.get("/api/catalog/v1",
                                 params={"limit": 1000, "offset": 0,
                                         "domains": self.base_url.split("//")[1]})
            r.raise_for_status()
            catalog = r.json()
            for ds in catalog.get("results", []):
                resource_id = ds["resource"]["id"]
                yield RawBundle(
                    source_system=self.source_system,         # e.g. "socrata"
                    source_collection=self.source_collection, # e.g. "data.cityofnewyork.us"
                    source_id=resource_id,
                    source_url=ds["landingPage"],
                    bundle_url=f"/resource/{resource_id}.json?$limit=10000",
                    fetched_at=self.now(),
                    payload=b"",                              # streamed by resolver
                    payload_format="json",
                    metadata={"dataset": ds["resource"],
                              "classification": ds.get("classification", {}),
                              "tags": [t for t in ds.get("tags", []) if isinstance(t, str)]},
                    is_remote_only=True,
                )
            # Resolver will paginate the actual data with $offset.
```

## Quick call — verify

```bash
# Find the portal's dataset catalog
curl -sL "https://data.cityofnewyork.us/api/catalog/v1?limit=2" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:', len(d['results'])); print('first:', d['results'][0]['resource']['name'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/catalog/v1?limit=1000&offset=0&domains=...        # catalog discovery (v1, new)
GET /api/views.json?limit=50                                # catalog discovery (legacy, still works)
GET /api/domain.json                                        # portal metadata
GET /resource/<4x4-xxxx>.json?$query=...                    # SODA data endpoint
GET /api/assets?.....                                       # file assets (SHP, PDF, etc.)
```

`$query` is SoQL: `$select=col1,col2`, `$where=...`, `$group`, `$order`, `$limit`, `$offset`, `$q=full text`.

## Notes

- The user supplied a list of 130+ US state/city portals — most `data.<x>.gov`, `data.<city>.<state>.gov`, and `opendata.<city>.gov` URLs are Socrata. One connector handles them all.
- App tokens are free and per-portal; you register once at the portal's `/profile/app_tokens` page. The fetcher reads `SOCRATA_APP_TOKEN` from the environment.
- Socrata pagination uses `$offset`/`$limit`, max `$limit=50000` per request.
- The CSV attached lists every known Socrata portal — see `sources-registry.md` for the full map.

