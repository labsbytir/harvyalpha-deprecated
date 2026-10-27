# data.gov / api.data.gov (apis.data.gov, College Scorecard, ED, etc.)

Key: `DEMO_KEY` works for prototyping; **pending** for production — register at https://api.data.gov/signup/ (instant, free, per-key limits).

Endpoint: `https://api.data.gov/...` (multiple sub-APIs)
Auth: query param `?api_key=<key>`
Format: `JSON` (default)

Documentation:
- Main: https://api.data.gov/
- Sign up: https://api.data.gov/signup/
- All sub-APIs: https://api.data.gov/#categories

The api.data.gov gateway is a single sign-on for many US-government open-data APIs. From one key, you can hit:

| Sub-API | Base path | Purpose |
|---|---|---|
| [[api.data.gov]] (FBI CDE) | `/crime/fbi/cde/...` | Crime data (already a credential) |
| College Scorecard | `/ed/collegescorecard/v1/schools?...` | US college data |
| Education Grants | `/ed/grants/v1/...` | US Dept of Ed grants |
| EPA | `/epa/...` | Air quality, superfund, etc. |
| NASA | `/nasa/...` | (separate from CMR) |
| NOAA | `/noaa/...` | Weather alerts |
| USGS | `/usgs/...` | Water, earthquake, elevation |

## How it's used in OpenTIR-Data (College Scorecard example)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/data_gov.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

DEMO_KEY = os.environ.get("DATA_GOV_DEMO_KEY", "DEMO_KEY")


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://api.data.gov",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # College Scorecard: list every US college
            for year in range(2017, 2025):
                offset = 0
                while True:
                    r = await client.get("/ed/collegescorecard/v1/schools", params={
                        "api_key": DEMO_KEY,
                        "year": year,
                        "per_page": 100,
                        "page": offset // 100,
                        "school.operating": 1,   # currently operating
                    })
                    if r.status_code == 429:
                        await asyncio.sleep(1); continue
                    r.raise_for_status()
                    body = r.json()
                    metadata = body.get("metadata", {})
                    results = body.get("results", [])
                    for s in results:
                        yield RawBundle(
                            source_system=self.source_system,
                            source_collection=f"scorecard_{year}",
                            source_id=str(s.get("id")),
                            source_url=f"https://collegescorecard.ed.gov/school/?{s.get('id')}",
                            bundle_url=f"/ed/collegescorecard/v1/schools?id={s.get('id')}&year={year}",
                            fetched_at=self.now(),
                            payload=orjson.dumps(s),
                            payload_format="json",
                            metadata={"school": s, "year": year},
                        )
                    total = metadata.get("total", 0)
                    if offset + 100 >= total or not results:
                        break
                    offset += 100
```

## Quick call — verify

```bash
# DEMO_KEY (limited; ~30 req/hour, 50/day)
curl -sL "https://api.data.gov/ed/collegescorecard/v1/schools?api_key=DEMO_KEY&school.name=Harvard&per_page=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('results:', len(d['results'])); print('first name:', d['results'][0]['school']['name'])"

# Or with the real key (replace YOUR_KEY)
curl -sL "https://api.data.gov/ed/collegescorecard/v1/schools?api_key=YOUR_KEY&per_page=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total US schools:', d['metadata']['total'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /ed/collegescorecard/v1/schools?api_key=&year=&per_page=&page=
GET /ed/collegescorecard/v1/schools?id=
GET /ed/grants/v1/federal?api_key=
GET /epa/outdoor-air-quality?api_key=
GET /nasa/planetary/apod?api_key=
GET /usgs/water-quality?api_key=
```

All sub-APIs share the same key. The College Scorecard has the most data (~6,500 schools × 9 years × dozens of fields).

## Notes

- **One key, many APIs.** This is the most efficient US government data source for the connector pattern.
- `DEMO_KEY` works for 30 requests/hour, 50/day. The real key raises that to 1,000/hour.
- The College Scorecard by itself has ~6,500 schools × 9 years of data (~60k records).
- The same key works for the FBI CDE (see `api.data.gov.md`).
- Cross-source dedup: the College Scorecard school ids are IPEDS — the same ids appear in NCES datasets (CCD, IPEDS), so the resolver merges them automatically.
- `page` is 0-indexed; `metadata.total` is the unfiltered total.
- The full endpoint catalog is at https://api.data.gov/#/ — dozens of sub-APIs not listed above.

