---
tags: [source, climate, tier-1, osint-data, free-cc-by, satellite, global, africa, eumetsat, lightning]
status: proposed
display_name: "EUMETSAT Meteosat + Metop (EUMETView WMS + Data Store API)"
source_name: eumetsat
---

# EUMETSAT Meteosat + Metop (EUMETView WMS + Data Store API)

European Organisation for the Exploitation of Meteorological Satellites. Meteosat geostationary imagery over Europe + Africa (full disc every 10–15 min) + Metop polar-orbit global soundings. **Vast majority of data is free under CC-BY-4.0**, including EUMETView's WMS for viewing/downloading imagery without an account. The free space-based lightning imager (MTG LI) is the only public-domain global lightning data — commercial networks (Vaisala GLD360, Earth Networks) charge for this.

> **Why this exists when we already have CHIRPS:** CHIRPS is rainfall (downstream product). EUMETSAT is the satellite that produces the cloud/lightning observations that feed into rainfall, storms, and many other products. Different layer of the stack.

## Metadata

| Field | Value |
|---|---|
| Source system | `eumetsat` |
| Base URL | `https://view.eumetsat.int/geoserver/wms` (WMS — no auth for viewing) |
| Data Store | `https://user.eumetsat.int/data-access/data-store` (auth, free) |
| EUMETCast | Real-time push, requires reception station hardware |
| Python client | `eumdac` (pip installable) |
| Auth | **No auth for EUMETView WMS viewing/downloading**; registration for Data Store / EUMETCast; both free |
| Tier | 1 |
| Axis | climate |
| License | **CC-BY-4.0** for "Core" data (vast majority); some products are "Recommended" with bespoke licensing |
| per_tenant_only | false |
| Coverage type | global |

## What's available

### Geostationary (Meteosat)
- **MSG (Meteosat Second Generation, current operational)** — Meteosat-10/11 over 0° and Indian Ocean; full disc every 15 min; 12 spectral channels
- **MTG (Meteosat Third Generation, deploying)** — MTG-I1 over 0° (Europe + Africa every 10 min); MTG-S1 with the **Lightning Imager** (LI), the first geostationary lightning detector over Europe/Africa
- **RSS (Rapid Scanning Service)** — every 2.5/5 min over Europe (limited Africa coverage)

### Polar (Metop)
- **Metop-B/C** — global atmospheric soundings, ocean/land parameters, every ~12h per satellite
- **Metop-SG (deploying)** — precipitation, aerosols, ice clouds

### Notable products for OSINT
- **MTG LI (Lightning Imager)** — global lightning from space, near-real-time. The **only public-domain global lightning feed** I know of. (AfricaWeather / SAWS / Vaisala are all commercial.)
- **MSG HRV (High Resolution Visible)** — half-km visible imagery over Europe + Africa
- **MSG SEVIRI IR channels** — every 15 min, full disc, multiple IR bands
- **MTG FCI (Flexible Combined Imager)** — 16 bands, 0.5–2 km resolution

## Endpoints

```
# WMS GetCapabilities (no auth)
GET https://view.eumetsat.int/geoserver/wms?service=WMS&version=1.3.0&request=GetCapabilities

# WMS GetMap — Meteosat IODC infrared
GET https://view.eumetsat.int/geoserver/wms
    ?service=WMS&version=1.3.0&request=GetMap
    &layers=msg_fes:ir108
    &bbox=-6500000,-6500000,6500000,6500000
    &width=1800&height=1800
    &srs=AUTO:97004,9001,0,0
    &format=image/png

# WMS GetMap — MTG Lightning Imager (Africa + Europe)
GET https://view.eumetsat.int/geoserver/wms
    ?service=WMS&version=1.3.0&request=GetMap
    &layers=mtg_fd:ir105_hrfi
    &bbox=-6500000,-6500000,6500000,6500000
    &width=3600&height=3600
    &srs=AUTO:97004,9001,0,0
    &format=image/jpeg

# Time-specific (historical)
&time=2026-05-05T08:40:00.000Z
```

The WMS only returns rendered rasters. For raw NetCDF / BUFR / HDF5, use the **Data Store** (auth) or **EUMETCast** (push, real-time, requires hardware).

## Fetcher

Not yet implemented. Pattern:

- **Imagery** (WMS): pull tile-by-tile for an Africa bbox on 15-min cadence. Store as PNGs in object storage, with the acquisition time and WMS URL in a metadata table.
- **Lightning** (MTG LI): pull event-level data via Data Store API (auth) — NetCDF files. Parse to per-event rows.
- **Python**: use `eumdac` (the official client) or just `requests` against the WMS.

## Storage

ClickHouse `osint.bundles` with `source_name='eumetsat'`. Per-acquisition rows: `satellite`, `product`, `acquisition_time`, `bbox`, `raster_path` (S3 URL to PNG), `lightning_events` (array, for LI product only).

For the lightning feed, store one row per detected lightning event: `time`, `lat`, `lon`, `intensity_ka`, `group_id`, `quality_flag`.

## Common queries

```
GET /v1/sources/eumetsat
GET /v1/sources/eumetsat/bundles?product=ir108&since=2026-09-01
GET /v1/sources/eumetsat/lightning?bbox=-35,-35,50,15&since=2026-09-01
```

## Gotchas

- **WMS is raster, not vector.** Each request is a rendered image. Don't try to extract per-pixel data — use Data Store for that (and accept the auth requirement).
- **MTG deployment is partial.** MTG-I1 is operational; MTG-S1 (with Lightning Imager) has been launched but full operational coverage is being rolled out 2024–2026. Treat LI as "available but growing coverage."
- **EUMETCast = hardware.** Real-time push requires a satellite dish + DVB-S2 receiver. Not for us; we use the WMS / Data Store path.
- **Bespoke licensing for "Recommended" data.** The vast majority is CC-BY-4.0 free, but some products have specific licenses. Check the data policy for each product you use.
- **EUMETView has a "MyViews" feature** that requires login. Ignore — we only need the WMS.

## Why I picked this

- **Free.** CC-BY-4.0 for nearly all products. No payment ever, just (optional) registration.
- **The only public-domain global lightning data.** Commercial networks charge $5k–$50k/year. EUMETSAT LI is the alternative.
- **Africa + Europe coverage out of the box.** Meteosat 0° is positioned specifically for this region.
- **15-min refresh** (or 10-min with MTG, 2.5-min rapid scan over Europe) — enough cadence for storm tracking.
- **Stable.** Intergovernmental agency, multi-decade track record.

## Why I considered it

Surfaced from the v1.africaweather.com mining product page, which describes AfricaWeather's lightning detection as using the "SAWS Vaisala lightning network" — that's commercial. But the **AfricaWeather-equivalent public-domain lightning feed is EUMETSAT's MTG Lightning Imager**, which we're now tracking here.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[AfriGIS Weather / AfricaWeather.com API]] — the commercial alternative (paid, per-tenant only)
- [[NOAA Aviation Weather Center (aviationweather.gov) METAR + TAF API]] — for surface observations, not lightning
- [[CHIRPS Rainfall via Digital Earth Africa]] — downstream rainfall product (uses satellite + gauge)
