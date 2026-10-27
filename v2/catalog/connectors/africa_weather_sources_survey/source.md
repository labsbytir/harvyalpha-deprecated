---
tags: [survey, osint-data, climate, africa, planning]
status: active
date: 2026-09-05
---

# Africa Weather Sources — Survey 2026-09-05

User asked us to go through a list of 17 Africa-weather URLs and find which have free APIs usable for OSINT-Data. Methodology: web search + web fetch for each, then categorize as **free API** / **paid with free trial** / **visualization** / **news-or-content** (no API).

**Verdict: 8 confirmed free APIs, 1 paid with free trial, 12 not APIs.** Detailed notes per source below.

## Free APIs (recommended for the 55-source list)

| Source | Tier | Coverage | Auth | Notes |
|---|---|---|---|---|
| [[WMO World Weather Information Service (WWIS) JSON API]] | 1 | Global, WMO member NMHSs | **No auth** | City forecasts + climatology. Easiest win. |
| [[WMO WIS2 Global Broker (MQTT) — Real-Time Weather Push]] | 1 | Global, WMO members | **No auth** (public MQTT `everyone/everyone`) | Real-time push. Most operationally complex (MQTT). |
| [[WMO OSCAR/Surface — Station Metadata REST API]] | 1 | Global station metadata | No auth (read) | Station directory, not weather data per se. |
| [[CHIRPS Rainfall via Digital Earth Africa]] | 1 | Africa, daily+monthly, 1981–present | **No auth** | Public domain. WMS/WCS/S3/ODC. Best for historical rainfall. |
| [[EUMETSAT Meteosat + Metop (EUMETView WMS + Data Store API)]] | 1 | Global (Europe + Africa geostationary; Metop polar) | **No auth for EUMETView WMS** | Satellite imagery + lightning imager. **Only public-domain global lightning feed** I know of. CC-BY-4.0. |
| [[TAHMO — Trans-African Hydro-Meteorological Observatory]] | 1 | Sub-Saharan Africa, ~1,000 stations | HTTP Basic (free for research/gov) | Best live African station data. **Contact required for credentials.** |
| [[UK Met Office Weather DataHub]] | 1 | Global deterministic (10 km) | Free API key (register) | Best global model data. UK + Global. |
| [[NOAA Aviation Weather Center (aviationweather.gov) METAR + TAF API]] | 1 | Global, ~10k airports including SA (FACT, FAOR, FALE…) | **No auth** | METAR + TAF + SIGMET. 30-day history. Same data as SAWS Aviation, free. |

## Paid (free trial only — not for shared warehouse)

| Source | Tier | Coverage | Auth | Notes |
|---|---|---|---|---|
| [[AfriGIS Weather / AfricaWeather.com API]] | 2 | South Africa (SAWS) | OAuth2 (free trial 50 credits/day, 60 days) | After trial: paid. Per-tenant option. |

## Not APIs (visualization, news, content)

For completeness, here's the verdict on the rest of the URL list. These were considered and rejected as data sources.

| URL | Verdict | Why |
|---|---|---|
| zoom.earth/places/africa/ | Visualization | Live satellite imagery, no public API. |
| africanews.com/weather/ | News | Article feed, no structured data. |
| theweather.com/africa.htm | News aggregator | HTML pages. |
| wunderground.com/maps/satellite/infrared/afric | Visualization (IBM) | UI only; WU API is paid. |
| windy.com | Visualization | Windy API is paid; ECMWF/GFS data accessible via WMO/NWS instead. |
| afriwx.co.za | Website (no API) | Displays SAWS data. The plain-text version at `daily-recorded-rainfall-data-figures-south-africa-inc.txt` could be scraped as a daily rainfall fallback, but SAWS itself is more reliable — see [[SAWS Daily Rainfall via afriwx.co.za text dump (scraper fallback)]]. |
| weathersa.co.za | Public website | No public API. Commercial agreement via AfriGIS for data. |
| **aviation.weathersa.co.za** | Login-gated SPA + paid subscriptions | Designated Aeronautical Meteorological Authority for South Africa, but the portal requires a "New User" registration and has "Subscription Packages." A 2014 avcom.co.za forum post describes direct URL access (`?ypq=Metars`) on `/aviationold/avmobile.php` — those routes are now login-gated. **Not a public API.** Use [[NOAA Aviation Weather Center (aviationweather.gov) METAR + TAF API]] instead — same underlying METAR/TAF data, free, no auth. |
| weather.org/africa-weather/ | Content site | No data. |
| weather.metoffice.gov.uk/world/south_africa | Visualization of Met Office data | Use DataHub API instead. |
| shakariconnection.com/weather-in-africa.html | Random blog | Not a data source. |
| v1.africaweather.com | B2B product page (e.g. /products/mining) | Marketing page for AfricaWeather's commercial mining/lightning/storm business. Underlying data: SAWS Vaisala lightning network (commercial) + EUMETSAT (free, see [[EUMETSAT Meteosat + Metop (EUMETView WMS + Data Store API)]]) + on-site Campbell Scientific stations (commercial lease). The free public-domain equivalent of the lightning feed is EUMETSAT's MTG Lightning Imager. |
| wmo.int/publication-series/state-of-climate-africa | Reports | PDF reports, not data. |
| nathab.com/.../south-africa/weather-climate | Tourism copy | Not data. |
| weather.com/maps/satellite/europe-africa | Visualization | No public API. |
| wxmaps.org/pix/prec10 | Static forecast images | PNG images of NOAA/NCEP forecasts. No API, no machine-readable. |

## Recommendation: which to add to the 55-source list

The user's project is already at 55 sources. The map's coverage layer (just fixed) shows Africa is mostly empty. **Eight new Africa/global weather sources are net new and free**. Suggested order of integration (easiest to hardest):

1. **WMO WWIS JSON** — zero auth, zero contact, GET request. Fetch daily.
2. **CHIRPS via Digital Earth Africa** — public domain, S3 hosted, no auth. Pull via WCS for bbox queries.
3. **NOAA Aviation Weather Center** — zero auth, GET, JSON. 30-day history. Pull METAR/TAF on 5-min cycle.
4. **EUMETSAT Meteosat + Metop (EUMETView WMS)** — no auth for WMS, CC-BY-4.0. Satellite imagery + lightning imager. Cache PNGs to object storage; pull lightning events via Data Store API.
5. **WMO WIS2 MQTT** — real-time push, but needs a long-running subscriber. Phase 1.5 work.
6. **UK Met Office DataHub** — global model, free API key with registration. Pull 6-hourly.
7. **TAHMO** — best African coverage, but requires a no-cost research agreement first. Email `info@tahmo.org`.
8. **WMO OSCAR/Surface** — station metadata, useful for cross-referencing which stations exist where.

Total new: **8 free sources**, all weather/climate, all with primary coverage in Africa and globally. That brings the 55 list to 63 and fills the climate/Africa gap.

**Not recommended for shared warehouse:**
- **AfriGIS Weather / AfricaWeather** — paid after 60-day trial. Could be added as `per_tenant_only: true` for orgs that want commercial SAWS data and are willing to pay.

## Status of this survey

- **Done:** research, categorization, per-source notes for the 6 free APIs and 1 paid API.
- **Pending (user decision):** which of the 6 to promote into the active 55-source list, and whether to add `per_tenant_only: true` for AfriGIS.
- **Pending (action):** `sources.yaml` updates, fetcher implementations, Add-a-Source runbook entry for each.

## Related

- [[00 Sources MOC]]
- [[Plan/Source Categorization]]
- [[Fetchers/00 Fetchers MOC]]
- [[Runbooks/Add a New Source]]
