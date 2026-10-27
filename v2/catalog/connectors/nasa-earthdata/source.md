# NASA Earthdata (CMR)

Key: `none required` for the catalog search API. Downloading the actual granules requires a free NASA Earthdata Login — register at https://urs.earthdata.nasa.gov/.

Endpoint (catalog): `https://cmr.earthdata.nasa.gov/search/`
Auth: Earthdata Login token via `Authorization: Bearer <token>` for data downloads
Format: JSON (`application/vnd.nasa.cmr.umm_results+json`)

Documentation:
- CMR API docs: https://cmr.earthdata.nasa.gov/search/site/docs/search/api.html
- Earthdata Login: https://urs.earthdata.nasa.gov/
- Earthdata portal: https://search.earthdata.nasa.gov/
- API root: https://cmr.earthdata.nasa.gov/search/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/nasa_cmr.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

EARTHDATA_TOKEN = os.environ.get("EARTHDATA_TOKEN", "")   # needed for downloads


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://cmr.earthdata.nasa.gov/search",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Authorization": f"Bearer {EARTHDATA_TOKEN}" if EARTHDATA_TOKEN else ""},
        ) as client:
            # 1. Enumerate every collection
            offset = 0
            page_size = 2000
            while True:
                r = await client.get("/collections", params={
                    "has_granules": "true",
                    "page_size": page_size,
                    "offset": offset,
                })
                r.raise_for_status()
                body = r.json()
                hits = body.get("hits", 0)
                entries = body.get("items", body.get("feed", {}).get("entry", []))
                for e in entries:
                    coll_id = e.get("id", e.get("short_name"))
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection="collections",
                        source_id=coll_id,
                        source_url=f"https://search.earthdata.nasa.gov/search/collections/{coll_id}",
                        bundle_url=f"/collections/{coll_id}",
                        fetched_at=self.now(),
                        payload=b"", payload_format="json",
                        metadata={"collection": e},
                        is_remote_only=True,
                    )
                if offset + page_size >= hits or not entries:
                    break
                offset += page_size
```

## Quick call — verify

```bash
# Catalog (no auth)
curl -sL "https://cmr.earthdata.nasa.gov/search/collections?has_granules=true&page_size=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total collections:', d['hits']); print('first:', d['items'][0]['id'])"

# Granule search
curl -sL "https://cmr.earthdata.nasa.gov/search/granules?collection_concept_id=C1443528508-LAADS&page_size=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('granules:', d['hits'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /search/collections?has_granules=true&page_size=N&offset=N    # catalog
GET /search/collections.json?{short_name}                         # one collection
GET /search/granules?collection_concept_id=...&page_size=N        # granule index
GET /search/granules.umm_json?concept_id=...                       # one granule UMM
GET /data-access/                                                # tool to get download URLs
```

Query params: `concept_id`, `short_name`, `collection_concept_id`, `provider`, `processing_level_id`, `temporal[]=start,end`, `bounding_box[]=west,south,east,north`, `point[]=lon,lat`, `platform`, `instrument`, `page_size` (max 2000), `offset`, `sort_key=start_date|usage_score`.

## Notes

- CMR (Common Metadata Repository) is the catalog; data lives on various DAACs (Distributed Active Archive Centers) — MODIS on LAADS, Sentinel on Copernicus, etc. Downloads need a separate Earthdata Login token.
- The 200 OK on `cmr.earthdata.nasa.gov/search/granules?page_size=1` returned 400 in my probe because that endpoint requires a `collection_concept_id` — the 400 is fine, it's not a server error.
- For OSINT, the **collection catalog** is the high-value target (~50,000 collections, full provenance, free). Actual data ingestion is a separate problem.
- NASA also has a separate `api.nasa.gov` with non-CMR endpoints (APOD, NeoWs, etc.); these use a different key — get one at https://api.nasa.gov/.
- Cross-source dedup: NASA Earthdata collection ids are unique to NASA. No overlap with other sources.


## Migrated Context (From NASA FIRMS Active Fire Detection.md)

---
tags: [source, climate, tier-1, osint-data, mvp, requires-key]
status: active
display_name: "NASA FIRMS Active Fire Detection"
fetcher: ingest.fetchers.nasa_firms
source_name: nasa_firms
api_key_env: FIRMS_MAP_KEY
---

# NASA FIRMS Active Fire Detection

Fire Information for Resource Management System (FIRMS) — NASA satellite-detected active fires. 5 sensors: MODIS NRT, VIIRS S-NPP NRT, VIIRS NOAA-20 NRT, VIIRS NOAA-21 NRT. Global coverage. Free with MAP_KEY (open registration).

## Metadata

| Field | Value |
|---|---|
| Source system | `nasa_firms` |
| Base URL | https://firms.modaps.eosdis.nasa.gov |
| API base | https://firms.modaps.eosdis.nasa.gov/api |
| Schedule (cron) | `0 4 * * *` (daily at 04:00 UTC) |
| Rate limit | 6 req/min |
| Tier | 1 |
| Axis | climate |
| License | Public domain (US Government work) |
| Auth | **Required**: `FIRMS_MAP_KEY` |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `global_daily` | area=world, 4 VIIRS + MODIS sensors, day_range=1 | global daily fires |

## Fetcher

`ingest/fetchers/nasa_firms.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='nasa_firms'`. Per-detection rows: `latitude`, `longitude`, `bright_ti4`, `bright_ti5`, `scan`, `track`, `acq_date`, `acq_time`, `satellite`, `instrument`, `confidence`, `version`, `brightness`, `frp`, `daynight`.

## Common queries

```
GET /v1/sources/nasa_firms
GET /v1/sources/nasa_firms/bundles?bbox=-10,35,40,75&since=2026-09-01
GET /v1/sources/nasa_firms/aggregates?group_by=country,sensor
```

## Gotchas

- 4 sensors × 1 day = ~150k-300k rows globally. Use a bbox or country filter to reduce.
- `confidence` is per-sensor: VIIRS uses `n` (nominal) or `h` (high); MODIS uses 0-100.
- MAP_KEY is free; sign up at https://firms.modaps.eosdis.nasa.gov/api/.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (climate axis)
- [[Ingestion/EFFIS European Forest Fire Information System]] (higher-res for Europe)
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (multi-hazard context)

