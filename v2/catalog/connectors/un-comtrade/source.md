# UN Comtrade (comtradeapi.un.org)

Key: `pending — register at https://comtradeservice.un.org/Data/Login` (free for non-commercial use; production/enterprise needs a paid token).

Endpoint: `https://comtradeapi.un.org/data/v1/`
Auth: `?subscription-key=<key>` query param, OR `Authorization: Bearer <key>` header
Format: `json` (default), `csv`, `tsv` via `?format=`

Documentation:
- API home: https://comtradeservice.un.org/Data
- New API docs: https://unstats.un.org/wiki/UN Comtrade Database (search "comtradeapi")
- Reference data (HS codes, reporter/partner lists): https://comtradeservice.un.org/Data/Reference

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/comtrade.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

SUBSCRIPTION_KEY = os.environ["UN_COMTRADE_KEY"]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://comtradeapi.un.org/data/v1",
            timeout=120.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Authorization": f"Bearer {SUBSCRIPTION_KEY}"},
        ) as client:
            for reporter in ("USA", "CHN", "DEU", "JPN", "GBR", "FRA", "IND", "BRA"):
                # Get all flows × all partners for one year
                r = await client.get("/get", params={
                    "reporterCode": reporter, "period": "2023",
                    "flowCode": "M,X", "cmdCode": "TOTAL",
                    "partnerCode": "all", "format": "JSON",
                })
                r.raise_for_status()
                body = r.json()
                rows = body.get("data", [])
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection=f"trade_{reporter}",
                    source_id=f"{reporter}-2023",
                    source_url=f"https://comtradeplus.un.org/TradeFlow?Flow=ALL&Reporter={reporter}&Period=2023",
                    bundle_url=f"/get?reporterCode={reporter}&period=2023&cmdCode=TOTAL&...",
                    fetched_at=self.now(),
                    payload=orjson.dumps(rows),
                    payload_format="json",
                    metadata={"reporter": reporter, "year": 2023, "rows": len(rows)},
                )
```

## Quick call — verify

```bash
# Replace YOUR_KEY with the real key after signup
curl -sL "https://comtradeapi.un.org/data/v1/get/C/A/HS?reporterCode=USA&period=2023&flowCode=M&partnerCode=0&cmdCode=27&subscription-key=YOUR_KEY" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('rows:', len(d.get('data', []))); print('first:', d['data'][0])"
```

Expected: ~50–100 rows for HS chapter 27 (mineral fuels), each with reporter/partner/cmdCode/value.

## Endpoints used (verified live 2026-09-04)

```text
GET /data/v1/get/{type}/{freq}/{classificationCode}    # main data endpoint
GET /data/v1/get/{reporter}/{period}/{classification}  # shorthand
GET /data/v1/bulk/{type}/{freq}/{classification}/all  # bulk downloads
GET /data/v1/Reference/                                  # metadata: HS, SITC, reporters, etc.
GET /data/v1/summary/{reporter}/{period}                 # rolled-up summary
```

Path params: `type` is `C` (commodity) or `S` (service); `freq` is `A` (annual) or `M` (monthly); `classificationCode` is `HS`, `SITC`, `BEC`, `EBOPS`.

Query params: `reporterCode` (ISO3 or numeric), `period` (year or `YYYYMM`), `flowCode` (`M`, `X`, `RM`, `RX`, `MIX`), `cmdCode` (HS code, `TOTAL`, `AG2-AG6` for aggregates), `partnerCode` (ISO3, `0` for world, `all`), `subscription-key`, `format=JSON|CSV|TSV`, `breakdownMode=classic|plus`.

## Notes

- The new `/data/v1/` API replaced the old `comtrade.un.org/api/` in 2023. The old endpoint is gone.
- Free key is rate-limited to 100,000 requests/day, max 100k rows per request. Use the bulk endpoint (`/bulk/.../all`) for the full-year full-dataset pull.
- The Comtrade team also publishes reference data (HS codes, country lists) via `/data/v1/Reference/`. Always cross-check `cmdCode` against the current HS revision.
- `subscription-key` as query param is deprecated for production; use the `Authorization: Bearer` header instead.
- The dataset is the same as the World Bank's "Trade in Value Added" and UNCTAD's trade series; the existing `dataset_fingerprint` resolver will merge them automatically.

