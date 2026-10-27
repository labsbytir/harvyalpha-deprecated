# OpenDataSoft connector

Key: `none required` — public ODS Explore API v2.1 works without a key. For higher rate limits, the portal operator can issue an API key; it's passed as `?apikey=<key>`.

Endpoint (catalog): `<base>/api/explore/v2.1/catalog/datasets?limit=50&offset=0`
Endpoint (data):    `<base>/api/explore/v2.1/catalog/datasets/<slug>/records?limit=50&offset=0&select=...&where=...`
Endpoint (export):  `<base>/api/explore/v2.1/catalog/datasets/<slug>/exports/csv` (max 65k rows)
Domain discovery:   `<base>/api/explore/v2.1/catalog/datasets?where=...`

Documentation:
- ODS Explore API v2.1: https://help.opendatasoft.com/apis/ods-explore-v2/
- Catalog endpoints: https://help.opendatasoft.com/apis/ods-explore-v2/explore_v2.1/02-catalog-endpoints/
- Records endpoints: https://help.opendatasoft.com/apis/ods-explore-v2/explore_v2.1/03-records-endpoints/
- Where clause (ODSQL): https://help.opendatasoft.com/apis/ods-explore-v2/#section/Opendata-Soft-Query-Language-(ODSQL)

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/opendatasoft.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

API_KEY = os.environ.get("OPENDATASOFT_API_KEY", "")


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
                params = {"limit": page_size, "offset": offset}
                if API_KEY:
                    params["apikey"] = API_KEY
                r = await client.get("/api/explore/v2.1/catalog/datasets", params=params)
                r.raise_for_status()
                body = r.json()
                for ds in body.get("results", []):
                    ds_id = ds["dataset_id"]
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection=self.source_collection,
                        source_id=ds_id,
                        source_url=f"{self.base_url}/explore/dataset/{ds_id}",
                        bundle_url=f"/api/explore/v2.1/catalog/datasets/{ds_id}/records?limit=100",
                        fetched_at=self.now(),
                        payload=b"",
                        payload_format="json",
                        metadata={"dataset": ds},
                        is_remote_only=True,
                    )
                total = body.get("total_count", 0)
                if offset + page_size >= total or not body.get("results"):
                    break
                offset += page_size
```

## Quick call — verify

```bash
# List 1 dataset from any ODS portal
curl -sL "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets?limit=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:',d['total_count']); print('first:',d['results'][0]['dataset']['metas']['title'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/explore/v2.1/catalog/datasets?limit=&offset=                  # catalog
GET /api/explore/v2.1/catalog/datasets/<id>                          # one dataset
GET /api/explore/v2.1/catalog/datasets/<id>/records?limit=&offset=    # records
GET /api/explore/v2.1/catalog/datasets/<id>/exports/csv              # CSV export
GET /api/explore/v2.1/catalog/datasets/<id>/exports/json             # JSON export
GET /api/explore/v2.1/catalog/datasets/<id>/attachments/<n>          # file attachment
```

ODSQL `where` examples: `where=country like '%France%'`, `where=population > 1000000`.

## Notes

- The user supplied a list of 130+ international portals. Most of the French municipal data portals in that list (Paris, Rennes, Nantes, Toulouse, Bordeaux, Montpellier, Lyon, Grenoble, Nice, Lille, etc.) are OpenDataSoft. So are a few non-French portals (Rotterdam, Barcelona, Amsterdam, Luxembourg, several Swiss and Belgian cities). One connector covers them all.
- ODS uses OD-SQL (similar to SoQL but different syntax). The fetcher passes it through as `?where=...` with no translation needed.
- The `/exports/csv` endpoint caps at 65,535 rows by default. For larger datasets the fetcher uses the `/records` endpoint with `limit`/`offset`.
- Some ODS portals require a trailing slash; the fetcher normalises that.
- The `total_count` field in the catalog response gives the exact size; the fetcher's pagination loop reads it once and then never asks again.

