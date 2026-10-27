# WHO Global Health Observatory (GHO OData)

Key: `none required` — public OData API.

Endpoint: `https://ghoapi.azureedge.net/api/`
Auth: none
Format: OData v4 JSON

Documentation:
- OData API docs: https://www.who.int/data/gho/info/gho-odata-api
- OData playground: https://ghoapi.azureedge.net/api/$metadata
- GHO UI: https://www.who.int/gho/database/en/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/who_gho.py
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://ghoapi.azureedge.net/api",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1", "Accept": "application/json"},
        ) as client:
            # 1. List every indicator (~2,300)
            r = await client.get("/Indicator")
            r.raise_for_status()
            for ind in r.json().get("value", []):
                code = ind["IndicatorCode"]
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="indicators",
                    source_id=code,
                    source_url=f"https://www.who.int/data/gho/data/indicators/{ind.get('IndicatorCode', code)}",
                    bundle_url=f"/{code}",
                    fetched_at=self.now(),
                    payload=b"", payload_format="json",
                    metadata={"indicator": ind},
                    is_remote_only=True,
                )

            # 2. Pull a few high-value indicators in full
            for code in ("WHOSIS_000001", "MDG_0000000001", "WHS6_0", "SDG_SH_DTH_MORT"):
                r = await client.get(f"/{code}")
                r.raise_for_status()
                rows = r.json().get("value", [])
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="data",
                    source_id=code,
                    source_url=f"https://www.who.int/data/gho/data/indicators/{code}",
                    bundle_url=f"/{code}",
                    fetched_at=self.now(),
                    payload=orjson.dumps(rows),
                    payload_format="json",
                    metadata={"indicator_code": code, "rows": len(rows)},
                )
```

## Quick call — verify

```bash
curl -sL "https://ghoapi.azureedge.net/api/Indicator?$top=2" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:', len(d['value'])); print('first code:', d['value'][0]['IndicatorCode'])"

curl -sL "https://ghoapi.azureedge.net/api/WHOSIS_000001?$top=2" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('rows:', len(d['value'])); print('first:', d['value'][0])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/Indicator                                          # ~2,300 indicator metadata
GET /api/Indicator?$filter=contains(IndicatorName,'malaria')
GET /api/Indicator?$select=IndicatorCode,IndicatorName&$top=50&$skip=200
GET /api/{IndicatorCode}                                    # data for one indicator
GET /api/{IndicatorCode}?$filter=SpatialDim%20eq%20'USA'
GET /api/{IndicatorCode}?$filter=TimeDim%20ge%202010
GET /api/Dim/{DimName}                                      # codelist (countries, sexes, etc.)
GET /api/Metadata/Dataset                                   # dataset-level metadata
GET /api/Metadata/Indicator                                 # indicator-level metadata
```

OData query options: `$filter`, `$select`, `$top`, `$skip`, `$orderby`, `$expand`, `$format`, `$count`, `$inlinecount`.

## Notes

- ~2,300 indicators and ~30 dimensions (countries, sexes, age groups, etc.).
- The dataset is huge when you pull every indicator × every country. Plan for hundreds of MB and dedupe by `NumericValue` + the dimension set.
- The same data is also on the WHO Global Health Estimates page, but the GHO OData API is the canonical programmatic source.
- Cross-source dedup: WHO GHO overlaps with the World Bank's `SH.XPD.CHEX.GD.ZS`-style indicators. The existing `dataset_fingerprint` resolver handles this — same `(title, publisher, period, country, tags)` will merge.
- `AzureEdge.net` is a CDN; the API is hosted on Azure front door. No CORS issues from server-side.

