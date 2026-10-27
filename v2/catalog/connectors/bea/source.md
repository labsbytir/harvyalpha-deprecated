# BEA (Bureau of Economic Analysis)

Key: `pending — register at https://apps.bea.gov/api/signup` (free, instant).

Endpoint: `https://apps.bea.gov/api/data`
Auth: `?Method=...&UserID=<key>` query param
Format: `JSON` (default) or `XML` via `ResultFormat=JSON|XML`

Documentation:
- API home: https://apps.bea.gov/API/
- Sign up: https://apps.bea.gov/api/signup
- Methods reference: https://apps.bea.gov/API/docs#Methods
- All datasets: https://apps.bea.gov/api/data?Method=GetDataSetList

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/bea.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

API_KEY = os.environ["BEA_API_KEY"]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://apps.bea.gov/api",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. List every dataset
            r = await client.get("/data", params={"Method": "GetDataSetList", "UserID": API_KEY})
            r.raise_for_status()
            datasets = r.json()["BEAAPI"]["Results"]["Dataset"]

            for ds in datasets:
                ds_name = ds["DatasetName"]
                # 2. For each, list parameters (years, frequencies, etc.)
                params_meta = (await client.get("/data", params={
                    "Method": "GetParameterList",
                    "UserID": API_KEY,
                    "datasetname": ds_name,
                })).json()["BEAAPI"]["Results"]["Parameter"]

                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="datasets",
                    source_id=ds_name,
                    source_url=f"https://apps.bea.gov/iTable/?reqid=19&step=2&isuri=1&categories=survey",
                    bundle_url=f"/data?Method=GetDataSetList",
                    fetched_at=self.now(),
                    payload=orjson.dumps({"metadata": ds, "parameters": params_meta}),
                    payload_format="json",
                    metadata={"dataset": ds, "parameters": params_meta},
                )
```

## Quick call — verify

```bash
# Replace YOUR_KEY with the real key after signup
curl -sL "https://apps.bea.gov/api/data?Method=GetDataSetList&UserID=YOUR_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('datasets:', len(d['BEAAPI']['Results']['Dataset'])); print('first:', d['BEAAPI']['Results']['Dataset'][0])"

curl -sL "https://apps.bea.gov/api/data?Method=GetData&DataSetName=NIPA&Frequency=A&Year=2020&ShowMillions=N&ResultFormat=JSON&UserID=YOUR_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('NIPA rows:', len(d['BEAAPI']['Results']['Data']))"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/data?Method=GetDataSetList                            # all datasets
GET /api/data?Method=GetParameterList&datasetname=NIPA         # parameters for one dataset
GET /api/data?Method=GetParameterValues&datasetname=NIPA&Parameter=ShowMillions
GET /api/data?Method=GetData&DataSetName=NIPA&...               # actual data
GET /api/data?Method=GetData&DataSetName=Regional&...          # regional data
GET /api/data?Method=GetData&DataSetName=NIPAUnderlying&...    # underlying NIPA detail
```

Parameters shared by all: `Method`, `UserID`, `ResultFormat` (JSON default; XML available). `GetData` also takes `DataSetName`, `Frequency` (A/Q/M), `Year` (single, list, or `YYYY-YYYY`), `ShowMillions` (Y/N), `ShowLabels` (Y/N), `LineCode` (table series id), `GeoFips` (state/county FIPS).

## Notes

- Datasets include NIPA (National Income & Product Accounts), NIUnderlying, Regional, ITA (international transactions), IIP, GDPbyIndustry, GDPbyState, REI (real estate), and ~20 more.
- `Year=2020,2021,2022,2023` is a list; `Year=2018-2023` is a range; you can mix.
- The key is free and instant; no quota, just per-request rate limits.
- The DataSet metadata is ~50 datasets, each with hundreds of LineCodes. Crawl all of them = a few thousand bundles.
- Some datasets (Fixed Assets, REI) are quarterly or annual-only — the API parameter list tells you which.

