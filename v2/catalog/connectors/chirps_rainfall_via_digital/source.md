---
tags: [source, climate, tier-1, osint-data, public-domain, africa, rainfall]
status: proposed
display_name: "CHIRPS Rainfall via Digital Earth Africa"
source_name: chirps_deafrica
---

# CHIRPS Rainfall via Digital Earth Africa

Climate Hazards Group InfraRed Precipitation with Stations — daily and monthly rainfall estimates for Africa, 1981–present, ~5.5 km resolution, **public domain**. Distributed by Digital Earth Africa (DE Africa) via WMS / WCS / S3 / Open Data Cube. Best historical rainfall data for Africa that is fully free and public domain.

## Metadata

| Field | Value |
|---|---|
| Source system | `chirps_deafrica` |
| Base URL | `https://ows.digitalearth.africa` |
| API base (WMS) | `https://ows.digitalearth.africa/wms?version=1.3.0` |
| API base (WCS) | `https://ows.digitalearth.africa/wcs?version=2.1.0` |
| S3 bucket | `s3://deafrica-input-datasets/` in `af-south-1` |
| Auth | **none** (public domain, anonymous read) |
| Tier | 1 |
| Axis | climate |
| License | Public Domain (Creative Commons) |
| per_tenant_only | false |
| Coverage type | global (Africa subset) |
| License note | "CHIRPS data is in the public domain as registered with Creative Commons." |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `rainfall_chirps_daily` | bbox, date | Daily rainfall in mm/day, 1981-01 to present, 0.05° resolution |
| `rainfall_chirps_monthly` | bbox, date | Monthly rainfall in mm/month, 1981-01 to present, 0.05° resolution |

## Endpoints (selected)

```
# WMS GetCapabilities
GET https://ows.digitalearth.africa/wms?version=1.3.0&service=WMS&request=GetCapabilities

# WCS GetCoverage (a bbox over Kenya, single day)
GET https://ows.digitalearth.africa/wcs?version=2.1.0&service=WCS&request=GetCoverage
    &coverageId=rainfall_chirps_daily
    &subset=Long(33.5,42)
    &subset=Lat(-5,5)
    &subset=time("2026-09-01")
    &format=image/tiff

# S3 (anonymous)
aws s3 ls --region af-south-1 --no-sign-request \
    s3://deafrica-input-datasets/rainfall_chirps_daily/2026/09/
```

## Fetcher

Not yet implemented. Pattern: use WCS for per-region queries when a tenant needs a specific bbox; use S3 for bulk backfill. Cache results in ClickHouse `osint.bundles` with `source_name='chirps_deafrica'`, fields: `time`, `lat`, `lon`, `rainfall_mm`.

## Storage

Rasters are ~5.5 km per pixel. For an Africa-wide daily fetch that's ~5M pixels/day. Practical approach: store as raw raster in object storage, materialize per-region summaries on query. ClickHouse has no native raster, so the design is "summary per (date, country/region) → 200+ rows/day total, not 5M."

## Common queries

```
GET /v1/sources/chirps_deafrica
GET /v1/sources/chirps_deafrica/bundles?bbox=33.5,−5,42,5&since=2026-09-01
```

## Gotchas

- **Bulk is huge.** Don't try to fetch all of Africa daily. Use bbox+date filters.
- **WCS 2.1 vs 1.0 syntax differs.** The DE Africa docs cover both; use 2.1 for current best support.
- **AWS S3 in af-south-1** — data transfer costs apply if you read from outside the region. For our Cloudflare-fronted setup, do fetches from a worker in af-south-1 to keep transfer costs at zero (intra-region).
- **The "deafrica" prefix is regional.** CHIRPS itself is global, but DE Africa only hosts the Africa subset. For non-Africa CHIRPS, use the Climate Hazards Center's CHC servers directly (no auth but a different URL).

## Why I picked this

- **Public domain, no auth, no key, no contact.** Genuinely free.
- **Africa is the hard problem for our coverage map.** This is the single best free rainfall dataset for the continent.
- **Multiple access patterns** (WMS for visual, WCS for raw, S3 for bulk, ODC for Python) — pick the cheapest one per query.
- **Backed by US Geological Survey + UC Santa Barbara** — institutional, stable, not going anywhere.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[WMO OSCAR/Surface — Station Metadata REST API]] — for cross-referencing
- [[WMO World Weather Information Service (WWIS) JSON API]] — for city-level forecasts
