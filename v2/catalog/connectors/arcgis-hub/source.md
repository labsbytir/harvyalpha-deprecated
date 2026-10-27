# ArcGIS Hub connector

Key: `none required` — public Hub Open Data API works without a key. For higher rate limits or private content, register a free ArcGIS Developer account at https://developers.arcgis.com/ and pass `?token=<token>`.

Endpoint (catalog): `<base>/api/v3/datasets` (new Hub v3) — or `<base>/api/v2/datasets` (older)
Endpoint (data):    `<base>/api/v3/datasets/<id>/featureserver/0/query?...`
Endpoint (item):    `<base>/api/v3/datasets/<id>` returns metadata + layer count.
Tile service:       `<base>/api/v3/datasets/<id>/tiles/<z>/<y>/<x>`
Domain discovery:   `https://hub.arcgis.com/api/v3/datasets?filter[domains]=<host>&page[size]=1`

Documentation:
- Hub v3 Open Data API: https://developers.arcgis.com/rest/enterprise-administration/portal/portal-self/
- Hub Open Data spec: https://dev.to/esri/introducing-the-new-hub-open-data-api
- Service URLs reference: https://developers.arcgis.com/rest/services-reference/enterprise/get-started-services/
- ArcGIS REST API: https://developers.arcgis.com/rest/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/arcgis_hub.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

TOKEN = os.environ.get("ARCGIS_HUB_TOKEN", "")


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            offset = 0
            page_size = 100
            while True:
                params = {
                    "fields[datasets]": "name,url,slug,id,attributes,data.category,"
                                        "data.spatialExtent,recordCount,searchDescription",
                    "page[size]": page_size,
                    "page[offset]": offset,
                }
                if TOKEN:
                    params["token"] = TOKEN
                r = await client.get("/api/v3/datasets", params=params)
                r.raise_for_status()
                body = r.json()
                datasets = body.get("data", [])
                for ds in datasets:
                    ds_id = ds["id"]
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection=self.source_collection,
                        source_id=ds_id,
                        source_url=ds.get("url") or f"{self.base_url}/datasets/{ds.get('slug', ds_id)}",
                        bundle_url=f"/api/v3/datasets/{ds_id}",
                        fetched_at=self.now(),
                        payload=b"",                       # resolver streams feature server
                        payload_format="geojson",
                        metadata={"dataset": ds},
                        is_remote_only=True,
                    )
                total = body.get("meta", {}).get("totalCount", 0)
                if offset + page_size >= total or not datasets:
                    break
                offset += page_size
```

## Quick call — verify

```bash
# List 1 dataset from a Hub
curl -sL "https://data-avl.opendata.arcgis.com/api/v3/datasets?fields[datasets]=name,url&page[size]=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:',d['meta']['totalCount']); print('first:',d['data'][0]['attributes']['name'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/v3/datasets?fields[datasets]=...&page[size]=N&page[offset]=N
GET /api/v3/datasets/<id>                                  # dataset metadata
GET /api/v3/datasets/<id>/featureserver/0/query            # data rows
GET /api/v3/datasets/<id>/featureserver/0?f=json           # layer info
GET /api/v3/datasets/<id>/tiles/<z>/<y>/<x>                # raster tiles
GET /api/v3/datasets?filter[domains]=<host>                # discover all datasets for a domain
```

## Notes

- The user supplied a list of 130+ US portals. Many `<city>.opendata.arcgis.com` and `<city>.hub.arcgis.com` URLs are ArcGIS Hub instances. One connector covers them all.
- The Hub v3 API uses square-bracket query params (`fields[datasets]=...`); not all HTTP clients handle these — `httpx` does.
- Each dataset has a `recordCount` field, so the fetcher knows up front how many rows to expect.
- Many ArcGIS Hubs are misconfigured (return 200 HTML, no `data:` field). The fetcher's resolver catches that and marks the bundle as `failed` with a useful error.
- The `filter[domains]` parameter is the way to discover a Hub's catalogue from a third-party `hub.arcgis.com` root — useful for `hub.arcgis.com` itself.

