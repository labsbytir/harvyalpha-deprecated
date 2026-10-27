# NOAA NCEI Climate Data Online (CDO) / Access Data Service

Key: `pending — register at https://www.ncdc.noaa.gov/cdo-web/webservices/v2` (free, instant token by email; production rate limits are higher than anonymous).

Endpoint (legacy CDO v2 REST): `https://www.ncei.noaa.gov/cdo-web/api/v2/`
Endpoint (modern Access Data Service): `https://www.ncei.noaa.gov/access/services/data/v1/`
Auth: header `token: <key>` (CDO v2); some Access endpoints are public
Format: `json` (default), `csv`

Documentation:
- CDO v2 docs: https://www.ncdc.noaa.gov/cdo-web/webservices/v2
- Access Data Service: https://www.ncei.noaa.gov/access-services-support
- Sign up: https://www.ncdc.noaa.gov/cdo-web/webservices/v2#getToken
- All CDO datasets: https://www.ncei.noaa.gov/cdo-web/datasets

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/noaa_ncei.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

CDO_TOKEN = os.environ["NCEI_CDO_TOKEN"]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://www.ncei.noaa.gov/cdo-web/api/v2",
            timeout=60.0,
            headers={"token": CDO_TOKEN, "User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. List all datasets
            r = await client.get("/datasets")
            r.raise_for_status()
            for ds in r.json().get("results", []):
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="datasets",
                    source_id=ds["id"],
                    source_url=f"https://www.ncei.noaa.gov/cdo-web/datasets/{ds['id']}",
                    bundle_url=f"/datasets/{ds['id']}",
                    fetched_at=self.now(),
                    payload=b"", payload_format="json",
                    metadata={"dataset": ds},
                    is_remote_only=True,
                )

            # 2. Pull GHCND daily summaries for a few major US stations
            for station in ("GHCND:USW00094728", "GHCND:USW00013743", "GHCND:USW00003017"):
                r = await client.get("/data", params={
                    "datasetid": "GHCND", "stationid": station,
                    "startdate": "2024-01-01", "enddate": "2024-12-31",
                    "limit": 1000, "units": "standard",
                })
                r.raise_for_status()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="ghcnd",
                    source_id=station,
                    source_url="https://www.ncei.noaa.gov/cdo-web/",
                    bundle_url=f"/data?datasetid=GHCND&stationid={station}...",
                    fetched_at=self.now(),
                    payload=orjson.dumps(r.json().get("results", [])),
                    payload_format="json",
                    metadata={"station": station, "year": 2024},
                )
```

## Quick call — verify

```bash
# Replace YOUR_TOKEN after signup
curl -sL -H "token: YOUR_TOKEN" "https://www.ncei.noaa.gov/cdo-web/api/v2/datasets?limit=2" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('datasets:', len(d['results'])); print('first:', d['results'][0])"

# Access Data Service (no token required for some endpoints)
curl -sL "https://www.ncei.noaa.gov/access/services/data/v1?dataset=daily-summaries&stations=USW00094728&startDate=2024-01-01&endDate=2024-01-02&format=json" \
  | head -c 500
```

## Endpoints used (verified live 2026-09-04)

```text
GET /cdo-web/api/v2/datasets?limit=N&offset=N                    # all datasets
GET /cdo-web/api/v2/datasetCategories                            # categories
GET /cdo-web/api/v2/datacategories                              # alias
GET /cdo-web/api/v2/datatypes?datasetid=GHCND                    # data types
GET /cdo-web/api/v2/locationcategories?datasetid=GHCND           # location categories
GET /cdo-web/api/v2/locations?datasetid=GHCND&locationcategoryid=CITY
GET /cdo-web/api/v2/stations?datasetid=GHCND&locationid=FIPS:11  # stations
GET /cdo-web/api/v2/data?datasetid=...&stationid=...&startdate=...&enddate=...
GET /access/services/data/v1?dataset=...&stations=...&startDate=...&endDate=...&format=json
GET /access/services/data/v1?dataset=daily-summaries&bbox=...   # bounding box
```

CDO query params: `datasetid` (required), `stationid`/`locationid`, `startdate`/`enddate` (ISO 8601 YYYY-MM-DD), `units=standard|metric`, `limit` (max 1000), `offset`, `sortfield`, `sortorder`, `includemetadata`, `include stations=false`.

## Notes

- The free CDO token is 5 req/sec, 10k/day. A registered data partner gets 1,000 req/sec.
- The modern Access Data Service (`/access/services/data/v1`) is the **preferred** path for bulk data — it supports more datasets and a more flexible query interface. CDO v2 is being deprecated.
- Datasets include GHCND (daily summaries), GHCNM (monthly), GSOM/GSOY (global summary of the month/year), NORMAL_*, PRECIP_*, ISDH/ISD (integrated surface database).
- For OSINT, the highest-value pull is GHCND daily summaries for the world's weather stations — covers ~120,000 stations, 200+ years.
- Same data is also at NOAA's Big Data Program on AWS S3 (`s3://noaa-ghcn-pds/`) — much faster bulk access if you have AWS credentials.


## Migrated Context (From NOAA Aviation Weather Center (aviationweather.gov) METAR + TAF API.md)

---
tags: [source, climate, tier-1, osint-data, public-no-auth, aviation, global, noaa]
status: proposed
display_name: "NOAA Aviation Weather Center — METAR + TAF API"
source_name: noaa_aviation
---

# NOAA Aviation Weather Center (aviationweather.gov) — METAR + TAF API

US NOAA's public aviation weather API. **Worldwide METAR + TAF**, free, no auth, 30-day history. Includes all major South African airports (FACT, FAOR, FALE, etc.) and ~10,000 stations globally. Same data SAWS publishes locally; pulled from the same upstream ICAO/METAR feed that everyone uses.

> **Why this exists when we already considered SAWS Aviation:** aviation.weathersa.co.za is a JavaScript SPA that requires login and has "Subscription Packages" — not a public API. aviationweather.gov has the same underlying METAR/TAF data, public REST API, no auth, worldwide. This is the free path to the same data.

## Metadata

| Field | Value |
|---|---|
| Source system | `noaa_aviation` |
| Base URL | `https://aviationweather.gov/api/data` |
| API docs | https://aviationweather.gov/data/api/ |
| Auth | **none** (public) |
| Tier | 1 |
| Axis | climate (and a thin slice of "transport"/"security" via SIGMETs) |
| License | Public domain (US Government work) |
| per_tenant_only | false |
| Coverage type | global |
| Update frequency | METARs: ~every minute; TAFs: every 10 min cache (`/data/cache/tafs.cache.xml.gz`) |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `metar` | `ids` (ICAO comma list), `bbox`, `radius` from a point, `taf=false` | Latest METAR (or up to 30-day history) |
| `taf` | `ids`, `bbox`, `radius` | Latest TAF (or history) |
| `airsigmet` | `bbox` | SIGMETs and AIRMETs (significant meteorological information) |
| `airep` | `bbox` | Aircraft reports (PIREPs) |
| `gairmet` | `bbox` | Graphical AIRMETs |

All return **raw text, JSON, GeoJSON, CSV, XML, or IWXXM** on demand.

## Endpoints

```
# METAR — latest from a list of airports
GET https://aviationweather.gov/api/data/metar?ids=FACT,FAOR,FALE&format=json

# METAR — by bounding box (Africa south of the Sahara)
GET https://aviationweather.gov/api/data/metar?bbox=-35,-35,50,15&format=json

# METAR — within 50 NM of a point
GET https://aviationweather.gov/api/data/metar?radial=33.9,18.4,50&format=json

# TAF — same shape
GET https://aviationweather.gov/api/data/taf?ids=FACT,FAOR&format=json

# Last 24 hours of METARs (history)
GET https://aviationweather.gov/api/data/metar?ids=FACT&hours=24&format=json

# Bulk cache (all current TAFs, gzipped XML, refreshed every 10 min)
GET https://aviationweather.gov/data/cache/tafs.cache.xml.gz
```

## Fetcher

Not yet implemented. Pattern:

- **For Africa specifically:** poll a fixed list of South African / Sub-Saharan ICAO codes (FACT, FAOR, FALE, FAPP, FABL, etc. — ~30 stations) on a 5-minute cycle.
- **For bulk backfill:** download `tafs.cache.xml.gz` and the equivalent METAR cache once per fetch cycle.
- **Cache aggressively** — METAR data is small but high-frequency. 30-day history is available for any new pull.

## Storage

ClickHouse `osint.bundles` with `source_name='noaa_aviation'`. Per-METAR rows: `icao_id`, `station_name`, `lat`, `lon`, `observation_time`, `temp_c`, `dewpoint_c`, `wind_dir_deg`, `wind_speed_kt`, `visibility_m`, `altimeter_hpa`, `cloud_layers` (array), `raw_metar`. Per-TAF rows: `icao_id`, `issue_time`, `valid_from`, `valid_to`, `forecast_periods` (nested), `raw_taf`.

## Common queries

```
GET /v1/sources/noaa_aviation
GET /v1/sources/noaa_aviation/bundles?icao=FACT&since=2026-09-01
GET /v1/sources/noaa_aviation/bundles?collection=taf&icao=FACT
```

## Gotchas

- **No API key, but there is rate limiting.** Don't hammer — be polite, cache. Public service.
- **METARs are 1-minute updates, TAFs every 6h or so.** Different cadences. Don't poll TAFs every minute.
- **IWXXM (XML for aviation) is the ICAO standard** but JSON is easier to ingest. Pick one and stick with it.
- **ICAO code vs IATA:** aviationweather.gov uses ICAO (4-letter, e.g., `FACT` for Cape Town). Some other sources use IATA (3-letter, e.g., `CPT`). Convert before cross-referencing.
- **South African airports use `FA` prefix** (FACT, FAOR, FALE, FAPP, etc.). Continental pattern: most of Africa uses `F` prefix; Europe uses `E`; Asia uses `Z`, `R`, `V`; etc.
- **30-day history max** for any one query. For long backfills, page by date.
- **30-day window applies per query** — if you need older data, use a different archive (Iowa State's archive has historical METARs back to 1928 for the US; not free for international though).

## Why I picked this

- **Free, no auth, no key, no contact.** Truly public.
- **Worldwide.** ~10,000 stations including the major South African airports.
- **Same data SAWS publishes locally.** METAR is METAR — pulled from the same upstream ICAO network.
- **30-day history.** Enough for most OSINT analyses.
- **Multiple formats** including raw text (for archival) and JSON (for ingestion).
- **Stable.** US Government service, multi-decade track record.

## Why I didn't pick aviation.weathersa.co.za instead

- **Login required.** The SAWS Aviation portal is a JavaScript SPA with "New User" registration and "Subscription Packages." Not a public API.
- **Old `/aviationold/avmobile.php` direct-URL trick no longer works.** A 2014 avcom.co.za forum post describes direct URLs like `?ypq=Metars` for METAR data; those routes are now login-gated.
- **The underlying data is the same.** METAR/TAF is a global standard. aviationweather.gov has the same data without the paywall.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[AfriGIS Weather / AfricaWeather.com API]] — the South African commercial alternative (if we ever need non-METAR SAWS data)
- [[WMO World Weather Information Service (WWIS) JSON API]] — for city-level observations + climatology (not aviation)

