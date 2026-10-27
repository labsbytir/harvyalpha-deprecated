# TransitWiki — Publicly-accessible public transportation data (STALE, 2022 snapshot)

Key: `none required`
Endpoint: `https://www.transitwiki.org/TransitWiki/index.php/Publicly-accessible_public_transportation_data`
Auth: `none`
Format: HTML (MediaWiki)
License: **CC-BY-SA 4.0** (per the TransitWiki footer)
Last meaningful edit: **2022-02-08** (4+ years stale at time of writing)

Documentation:
- The page: https://www.transitwiki.org/TransitWiki/index.php/Publicly-accessible_public_transportation_data
- TransitWiki: https://www.transitwiki.org/TransitWiki/
- TransitWiki About: https://www.transitwiki.org/TransitWiki/index.php/TransitWiki:About
- TransitWiki License: https://www.transitwiki.org/TransitWiki/index.php/TransitWiki:License
- Maintained by: Caltrans Division of Rail and Mass Transportation + UCLA Institute of Transportation Studies
- MediaWiki 1.42.3, last-parsed 2026-09-05

## ⚠️ This page is stale

This TransitWiki page was last meaningfully edited on **2022-02-08**
by user SamGreenwood. As of 2026-09-05, it is **4+ years out of date**
and has been superseded by:

| Newer registry | What it adds | Our connector |
|---|---|---|
| **Mobility Database** (`mobilitydatabase.org`) | 6000+ feeds, 99+ countries, validated daily, with OAuth2 API | [[mobility-database]] |
| **Transitland** (`transit.land`) | thousands of GTFS/GTFS-RT/GBFS/MDS feeds, GraphQL API, Onestop IDs, daily fetches | [[transitland]] |
| **OpenStreetMap wiki's `List of GTFS feeds`** | another community list, partial overlap | (not yet in vault) |
| **gtfs.org/resources/sharing-data** | the canonical pointer page maintained by the GTFS community | (not yet in vault) |
| **OpenMobilityData / TransitFeeds.com** | **DEPRECATED 2022**, archive only | n/a |

If you need to find a GTFS feed for a specific agency in 2026, **do
not use this page** — start with [[mobility-database]] (the API has
freshness metadata) or [[transitland]] (per-feed `fetched_at` and
import status).

We document this page in the vault as a **reference** for the same
reason we document the deprecated NYPL Repo API: so future
contributors don't waste time re-discovering the same dead list.

## What it is (historically)

The page was the de-facto community-maintained list of publicly-
accessible GTFS and GTFS-realtime feeds worldwide, originally
maintained at the "Public Feeds wiki page on Google Transit Data
Feed Google Code project" before being forked to TransitWiki.

It was organized into two tables:

1. **Static GTFS feeds** (schedules, stops, routes, shapes) —
   regional tables: Australia & New Zealand, British Isles, Canada,
   France, Germany, Italy, Spain, USA, and others. Each row was
   `(Agency, Area, Feed Location, Notes)` with the agency's
   download URL.
2. **Dynamic / real-time data and others** (NextBus XML, GTFS-RT,
   proprietary agency APIs like BART, MBTA/EOT, WMATA, CTA, etc.)
   with format + API key requirements per row.

The page also pointed at the **US National Transit Map** as a
multi-agency consolidated resource. That's still live at
`http://www.rita.dot.gov/bts/ntm` (managed by USDOT/BTS) but the
raw GTFS data behind it is also published on the Socrata path at
`https://data.bts.gov/` (see the `railroads.dot.gov` / FRA / BTS
probes in earlier loops).

## Why we don't ingest this

- **It's a wiki page, not a structured feed catalog.** The feeds are
  in HTML tables, not GTFS-spec JSON. Parsing it would require
  wiki-text scraping with high maintenance.
- **It's stale.** Many of the listed URLs have rotted (404s,
  redirects to agency homepages, moved to Socrata/ArcGIS portals,
  gone behind email-signup walls). About 30-40% of the URLs are
  expected to be dead as of 2026.
- **It's been superseded by Mobility Database + Transitland**, both
  of which provide structured JSON APIs with daily freshness
  metadata.
- **The license is CC-BY-SA 4.0**, which is **share-alike**: any
  derivative registry we build would also need to be CC-BY-SA 4.0.
  Our OpenTIR-Data is AGPL-3.0, and AGPL-3.0 is one-way
  compatible with CC-BY-SA 4.0 (we can ingest CC-BY-SA content and
  publish our own additions under any license, but if we *verbatim
  copied* the TransitWiki table to our docs, those rows would have
  to be CC-BY-SA 4.0 too). This is a real consideration when
  quoting or mirroring the page.

## License note (the share-alike question)

CC-BY-SA 4.0 is a "copyleft" license. The three relevant cases:

| Use case | OK? | Why |
|---|---|---|
| Read the page to find an agency URL, then wire that URL to a generic GTFS fetcher | **Yes** | The agency's GTFS data is governed by the agency's own license (usually ODbL, CC-BY, or a custom ToS). TransitWiki is just the discovery layer. |
| Verbatim copy the HTML table to a docs page | **No, requires CC-BY-SA 4.0** | The table is a "Collection" under CC-BY-SA 4.0. Verbatim copy with attribution is allowed; derivative works must be CC-BY-SA 4.0. |
| Quote a small excerpt with attribution + link | **Yes** | The page is freely quotable; share-alike is on the *collection*, not the *facts*. |
| Re-derive the same feed list by crawling the same agencies | **Yes** | Facts aren't copyrightable. The resulting list is your work. |

We chose to **not** mirror the table in our docs, and instead
**reference the actively-maintained alternatives**. The
TransitWiki page is mentioned in the vault only for discoverability.

## What to use instead (the modern registry stack)

| Path | Best for | License | Connector |
|---|---|---|---|
| **Mobility Database Catalogs** (GitHub) | Bulk snapshot of all feeds, CC0 metadata, parse locally | **CC0 metadata** + **Apache 2.0** code | [[mobility-database]] |
| **Mobility Database REST API** | Live query (by country, bounding box, feature, status) with daily freshness | **CC0** for catalog data; OAuth2 key required for the live API | [[mobility-database]] |
| **Transitland GraphQL + REST** | Per-feed state, import status, Onestop ID, with daily fetches | **public**, with optional API token for higher rate limits | [[transitland]] |
| **gtfs.org/resources/sharing-data** | Pointer page to the above + regional lists | (no data; just a wiki) | (not yet in vault) |
| **Transitland `feeds.csv` export** | Single CSV of every feed with `country`, `subdivision`, `feed_id`, `urls` | **public download** | [[transitland]] |

For OpenTIR-Data v1, the right wiring is:

1. **Add [[mobility-database]] as a first-class source** in
   `sources.yaml`. Bulk-load the GitHub catalog once; use the API
   for incremental updates.
2. **Add [[transitland]] as a first-class source** for cross-
   validation (Transitland tracks per-feed import success, which is
   a different signal than Mobility Database's GTFS Validator pass).
3. The shared warehouse then has `osint.datasets` rows for every
   known GTFS feed in the world (~10,000 rows after dedup). Per
   tenant, the `geops_realtime` fetcher (or a generic GTFS-RT
   fetcher) can subscribe to the specific feeds the tenant wants.

## See also

- [[mobility-database]] — the primary replacement, with OAuth2 API
- [[transitland]] — the secondary replacement, with GraphQL API
- [[gtfs-de]] — already in our vault; one specific national feed
  (Patrick Brosi, U. Freiburg)
- [[geops]] — geOps Realtime, an aggregator over many of these
  same GTFS feeds
- [[liveuamap]] — same "documented but not for ingestion" pattern

## License of this connector note

`connectors/transitwiki.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From TAHMO — Trans-African Hydro-Meteorological Observatory.md)

---
tags: [source, climate, tier-1, osint-data, free-research, africa, stations]
status: proposed
display_name: "TAHMO — Trans-African Hydro-Meteorological Observatory"
source_name: tahmo
---

# TAHMO — Trans-African Hydro-Meteorological Observatory

Network of ~1,000 weather stations across 20+ Sub-Saharan African countries, mostly hosted at schools and universities. **Free for research, government, and NMHS use** (per their FAQ); commercial use is paid. The single best free live-station dataset for Africa — but requires a no-cost research agreement via email first.

## Metadata

| Field | Value |
|---|---|
| Source system | `tahmo` |
| Base URL | `https://tahmoapi.mybluemix.net/v1` |
| API docs | https://tahmo.org/docs/TAHMO_API_documentation_latest.pdf |
| Python examples | https://github.com/TAHMO/API-V2-Python-examples |
| Auth | HTTP Basic (`id:secret`) — **must email `info@tahmo.org` first** |
| Tier | 1 |
| Axis | climate |
| License | Free for research/peer-reviewed use; free for government and NMHSs; paid for commercial |
| per_tenant_only | false (research) or true (commercial) |
| Coverage type | global (Africa subset) |

## License / access specifics

From TAHMO's own FAQ:

> **Do National Meteorological Agencies get the data for free?** YES! National Meteorological agencies get the data for free as long as the station is functioning.
>
> **Who else can get the data freely?** Any researcher seeking to develop peer-reviewed publications that would benefit from the data collected, can get any and all of the data for their use. They simply contact info@tahmo.org with the description of their need, and as long as it satisfies this basic requirement, a no-cost agreement is completed.
>
> **When do I have to pay for the data?** A fee is incurred for commercial use of the data, including the development of new services. Fees depend on geographical coverage and level of exclusiveness.

So: **email `info@tahmo.org` with a research use case, get credentials, plug in the API.** No cost, no key, no token — just an agreement email.

## Collections

| Name | Filter | Notes |
|---|---|---|
| `stations` | `active=true` | Station list with location, variables, last measurement date |
| `station` | `:stationId` | One station's metadata (e.g., `TA00002`) |
| `timeseries_hourly` | `:stationId`, date range | Hourly aggregated observations |
| `timeseries` | `:stationId`, date range | 5-min or 10-min processed + quality-controlled |
| `timeseries_rawmeasurements` | `:stationId`, date range | 5-min or 10-min raw, no QC |

## Endpoints

```
# All stations you have access to
GET https://tahmoapi.mybluemix.net/v1/stations?active=true

# One station
GET https://tahmoapi.mybluemix.net/v1/stations/TA00002

# Hourly timeseries
GET https://tahmoapi.mybluemix.net/v1/timeseries/TA00002/hourly?startDate=2026-01-01&endDate=2026-01-31

# 5-min processed
GET https://tahmoapi.mybluemix.net/v1/timeseries/TA00002/?startDate=2026-01-01

# Raw measurements
GET https://tahmoapi.mybluemix.net/v1/timeseries/TA00002/rawmeasurements?startDate=2026-01-01
```

Variables (per TAHMO public data page): Temperature (°F), Mean pressure (inHg), Relative humidity (%), Mean visibility (mi), Average dew point (°F), Wind direction, Wind speed (mph). Note: **units are imperial in the public viewer; check the API for metric equivalents.**

## Fetcher

Not yet implemented. Pattern: 1-time pull of full station list, then poll each station on hourly cadence (per the API's hourly aggregation). Auth via HTTP Basic.

## Storage

ClickHouse `osint.bundles` with `source_name='tahmo'`. Per-station per-hour rows. Fields: `station_id`, `time`, `temp_c`, `humidity_pct`, `pressure_hpa`, `wind_speed_mps`, `wind_dir_deg`, `dew_point_c`, `visibility_m`.

## Common queries

```
GET /v1/sources/tahmo
GET /v1/sources/tahmo/bundles?station=TA00002&since=2026-09-01
```

## Gotchas

- **No public self-service signup.** Must email `info@tahmo.org` with a research use case. Don't promise a deadline on the email — their turnaround is unclear from public docs.
- **Imperial units in the public viewer.** API likely returns raw sensor values; verify the unit on first response.
- **Stations are at schools.** Some have intermittent connectivity; expect gaps in the time series.
- **Coverage is Sub-Saharan Africa only.** No North Africa (Egypt, Morocco, Algeria, Tunisia, Libya). For those, use WMO WWIS.

## Why I picked this

- **Africa-specific**, not just "happens to include Africa" like most global datasets.
- **Live observations**, not just forecasts or climatology — this is real-time data.
- **Free for research** under a clear, low-friction agreement.
- **Stations are dense in some regions** (Kenya, Uganda, Ethiopia) and sparse in others (Central Africa). The map will show that distribution honestly.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[CHIRPS Rainfall via Digital Earth Africa]] — historical rainfall (raster, not stations)
- [[WMO OSCAR/Surface — Station Metadata REST API]] — for cross-referencing which stations exist

