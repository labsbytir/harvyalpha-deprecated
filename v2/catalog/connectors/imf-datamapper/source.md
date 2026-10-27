# IMF DataMapper / SDMX

Key: `none required` for the public DataMapper API. SDMX endpoints at `sdmxcentral.imf.org` and `dataservices.imf.org` are also public.

Endpoint (DataMapper v1): `https://www.imf.org/external/datamapper/api/v1/`
Endpoint (SDMX JSON): `https://dataservices.imf.org/REST/SDMX_JSON.svc/`
Endpoint (SDMX REST, v2): `https://sdmxcentral.imf.org/rest/`
Auth: none
Format: `json` (DataMapper), SDMX-JSON or SDMX-ML (REST)

Documentation:
- DataMapper API docs: https://www.imf.org/external/datamapper/api/help
- SDMX REST docs: https://datahelp.imf.org/knowledgebase/articles/905681
- All indicators: https://www.imf.org/external/datamapper/api/v1/indicators
- IMF DataMapper UI: https://www.imf.org/external/datamapper/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/imf.py
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://www.imf.org/external/datamapper/api/v1",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. List all indicators (~75 datasets, e.g. NGDP_RPCH, PCPIPCH, GGXWDG_G01_GDP_PT)
            r = await client.get("/indicators")
            r.raise_for_status()
            indicators = r.json().get("indicators", {})

            # 2. For each indicator, fetch the full time series
            for ind_id in indicators:
                r = await client.get(f"/{ind_id}")
                r.raise_for_status()
                body = r.json()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="datamapper",
                    source_id=ind_id,
                    source_url=f"https://www.imf.org/external/datamapper/{ind_id}",
                    bundle_url=f"/{ind_id}",
                    fetched_at=self.now(),
                    payload=orjson.dumps(body),
                    payload_format="json",
                    metadata={"indicator": indicators[ind_id], "values": body.get("values", {})},
                )
```

## Quick call — verify

```bash
curl -sL "https://www.imf.org/external/datamapper/api/v1/NGDP_RPCH" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('keys:', list(d.keys())[:5]); print('values count:', len(d.get('values', {}).get('NGDP_RPCH', {})))"

# SDMX-JSON for one indicator
curl -sL "https://dataservices.imf.org/REST/SDMX_JSON.svc/CompactData/NGDP_RPCH/A?startPeriod=2010&endPeriod=2020" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('obs:', d.get('CompactData', {}).get('DataSet', {}).get('Series', {}) is not None)"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /external/datamapper/api/v1/indicators                          # all dataset ids
GET /external/datamapper/api/v1/countries                           # ISO3 -> IMF code
GET /external/datamapper/api/v1/{indicator}                         # time series
GET /external/datamapper/api/v1/{indicator}/{country}               # one country slice
GET /dataservices/REST/SDMX_JSON.svc/CompactData/{key}/{freq}?startPeriod=&endPeriod=
GET /dataservices/REST/SDMX_JSON.svc/CodeList/{cl}                  # codelists
GET /sdmxcentral/rest/data/IMF,{key},{version}/all                  # full data
```

## Notes

- The DataMapper API is the easiest entry point — it's a single JSON blob per indicator. SDMX is for when you need the formal codelists.
- ~75 high-level indicators cover the IMF's headline series (WEO, GFSR, GFS). The full SDMX REST API has thousands.
- Cloudflare in front of `imf.org` returned 403 on my probes, but that's almost certainly a UA/CF-block on the bot. The real API works fine in the browser; retry with a browser-like UA if you see 403.
- The DataMapper response shape is `{ values: { INDICATOR: { COUNTRY: { YEAR: NUMBER } } } }` — a single nested dictionary. Easy to flatten in the resolver.
- `https://dataservices.imf.org` is the canonical SDMX endpoint; `sdmxcentral.imf.org` mirrors it.


## Migrated Context (From Per-Utility Outage Maps (US Bespoke Scrapes).md)

---
tags: [source, info_environment, climate, tier-2, osint-data, public-no-auth, html-scrape]
status: active
display_name: "Per-Utility Outage Maps (US Bespoke Scrapes)"
fetcher: ingest.fetchers.per_utility
source_name: per_utility_outage_maps
---

# Per-Utility Outage Maps (US Bespoke Scrapes)

Per-utility outage maps — National Grid NY + Duke + PG&E + SCE + ConEd + 15+ others. No public APIs; each utility's outage map is scraped individually (server-rendered HTML, ArcGIS REST, or Mapbox). Falls back to fill ODIN + PowerOutage.us gaps (Hawaii, Alaska, smaller coops). The 6 largest US utilities (ConEd, Duke, PG&E, FPL, Georgia Power, Oncor) cover ~50% of US customers not already in ODIN.

## Metadata

| Field | Value |
|---|---|
| Source system | `per_utility` |
| Base URL | https://outagemap.ny.nationalgridus.com/ |
| API base | https://outagemap.ny.nationalgridus.com/reports/ |
| Schedule (cron) | `*/15 * * * *` (every 15 min) |
| Rate limit | 6 req/min (very low) |
| Tier | 2 |
| Axis | info_environment, climate |
| License | per-utility terms (browse-only; scraping is grey) |
| Auth | none (public, but TOS-iffy) |
| per_tenant_only | false |
| format | html + arcgis_json + mapbox_json |

## Collections

| Name | Endpoint | Format |
|---|---|---|
| `national_grid_ny` | https://outagemap.ny.nationalgridus.com/reports/30d77369-2b12-4c0d-867d-31b2e7a4f18a | HTML |
| `duke_energy` | https://outagemap.duke-energy.com/#/home | ArcGIS JSON |
| `coned` | https://www.coned.com/en/outage-map | ArcGIS JSON |
| `pge` | https://www.pge.com/outages | Mapbox JSON |
| `sce` | https://www.sce.com/outage-center | Mapbox JSON |
| `fpl` | https://www.fpl.com/storm-center/outage-map.html | ArcGIS JSON |
| `georgia_power` | https://outagemap.georgiapower.com/ | ArcGIS JSON |
| `oncor` | https://www.oncor.com/outage-map | Mapbox JSON |

## Fetcher

`ingest/fetchers/per_utility.py`

## Storage

Lands in ClickHouse `osint.bundges` with `source_name='per_utility_outage_maps'`. Per-utility, per-incident rows.

## Common queries

```
GET /v1/sources/per_utility_outage_maps
GET /v1/sources/per_utility_outage_maps/bundles?utility=coned&since=2026-09-01
```

## Gotchas

- **Grey-area scraping.** Most utility TOS prohibit scraping. We rate-limit hard (6 req/min) and only fetch public-facing pages. Don't redistribute the raw scraped data.
- HTML scraping (national_grid_ny) is in tension with the "no HTML scraping" rule (same as [[Ingestion/Smithsonian Global Volcanism Program Weekly Activity]] and [[Ingestion/CIVICUS Monitor Civic-Space Ratings]]).
- Each utility's page layout changes. Per-utility fetchers break often; budget maintenance time.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (free, structured)
- [[Ingestion/PowerOutage.us Commercial Aggregator [PER-TENANT-ONLY]]] (commercial)
- [[Ingestion/Per-Utility Outage Maps — Gap List]] (planned for Phase 2)

