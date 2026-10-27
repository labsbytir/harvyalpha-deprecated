# World Bank Open Data (api.worldbank.org v2)

Key: `none required` — public, free, no auth. Sign up at https://datacatalog.worldbank.org/ to be listed as a data consumer; not required for API use.

Endpoint: `https://api.worldbank.org/v2/`
Auth: none
Format: `json` (default) or `xml` via `?format=`

Documentation:
- API home: https://datahelpdesk.worldbank.org/knowledgebase/articles/898581
- Indicator API: https://datahelpdesk.worldbank.org/knowledgebase/articles/889392
- All endpoints: https://api.worldbank.org/v2/apidocs
- Catalog: https://datacatalog.worldbank.org/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/worldbank_api.py
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://api.worldbank.org/v2",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. Pull every country
            offset = 0
            while True:
                r = await client.get("/country", params={"format": "json", "per_page": 1000, "offset": offset})
                r.raise_for_status()
                _, rows = r.json()
                for c in rows:
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection="countries",
                        source_id=c["id"],
                        source_url=f"https://data.worldbank.org/country/{c['id']}",
                        bundle_url=f"/country/{c['id']}?format=json",
                        fetched_at=self.now(),
                        payload=b"", payload_format="json",
                        metadata={"country": c},
                        is_remote_only=True,
                    )
                if len(rows) < 1000: break
                offset += 1000

            # 2. Pull every indicator metadata
            offset = 0
            while True:
                r = await client.get("/indicator", params={"format": "json", "per_page": 1000, "offset": offset})
                r.raise_for_status()
                _, rows = r.json()
                for ind in rows:
                    yield RawBundle(
                        source_system=self.source_system,
                        source_collection="indicators",
                        source_id=ind["id"],
                        source_url=f"https://data.worldbank.org/indicator/{ind['id']}",
                        bundle_url=f"/indicator/{ind['id']}?format=json",
                        fetched_at=self.now(),
                        payload=b"", payload_format="json",
                        metadata={"indicator": ind},
                        is_remote_only=True,
                    )
                if len(rows) < 1000: break
                offset += 1000
```

## Quick call — verify

```bash
curl -s "https://api.worldbank.org/v2/country?format=json&per_page=2" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:', d[0]['total']); print('first:', d[1][0]['name'], '(', d[1][0]['id'], ')')"
curl -s "https://api.worldbank.org/v2/indicator/NY.GDP.MKTP.CD?format=json&date=2020" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('GDP 2020:', d[1][0]['value'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /v2/country?format=json&per_page=1000&offset=0            # all countries
GET /v2/indicator?format=json&per_page=1000&offset=0          # all indicators (~17k)
GET /v2/indicator/{id}?format=json&date=2010:2024            # time series
GET /v2/indicator/{id}?format=json&country=USA;CHN;IND        # specific countries
GET /v2/sources?format=json                                   # source list
GET /v2/incomeLevels?format=json                              # income-level groupings
GET /v2/regions?format=json                                   # regional groupings
GET /v2/lendingTypes?format=json                              # lending types
```

URL params: `format=json|xml`, `per_page=1-32500`, `offset=`, `date=YYYY|YYYY:YYYY`, `country=ISO3;ISO3;...` or `all`, `source=`, `incomelevel=`, `region=`, `lendingtype=`, `mrv=` (most recent value), `gap-fill=Y|N`.

## Notes

- Response is a 2-element array: `[metadata, data]`. Always unpack `d[1]` for the rows and `d[0]` for pagination info.
- Hard cap is `per_page=32500`. For more, paginate with `offset`.
- `mrv=N` returns the N most recent non-null values per country — handy for snapshot ingestion.
- `?source=11` is the World Bank's own source; other source ids are other providers (IMF, OECD, etc.).
- No CORS headers for browser access from arbitrary domains; server-side only.
- The indicator metadata (`/v2/indicator`) is the right entry point for a stable indicator catalog; pair it with `/v2/country` for the full matrix.

