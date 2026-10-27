# ODIN — Outage Data Initiative Nationwide (ORNL + DOE)

Key: `none required to fetch the public OpenEnergyHub dataset; for the **private** real-time subscriber feed, request via email to ODIN@ORNL.GOV (free, ~1-2 week review)`
Endpoint (public): `https://ornl.opendatasoft.com/api/explore/v2.1/catalog/datasets/odin-real-time-outages-county/records`
Endpoint (subscriber): `https://api.odin.ornl.gov/od/...` (issued on approval, CIM IEC 61968-3 or MultiSpeak v4.1+)
Auth: `none` for the public OpenEnergyHub endpoint; `OAuth2 + token` for the ORNL subscriber feed
Format: **JSON (records with GeoJSON geometry)** for the public feed; **CIM IEC 62325 XML** or **MultiSpeak** for the private feed

Documentation:
- Landing: https://odin.ornl.gov/
- About: https://odin.ornl.gov/outages/pages/about.html
- Public dataset on OpenEnergyHub: https://ornl.opendatasoft.com/explore/dataset/odin-real-time-outages-county/
- Public dataset API: https://ornl.opendatasoft.com/api/explore/v2.1/catalog/datasets/odin-real-time-outages-county/
- EAGLE-I companion dataset (historical 2014-2023): https://figshare.com/articles/dataset/The_Environment_for_Analysis_of_Geoocated_Energy_Information_s_Recorded_Electricity_Outages_2014-2022/24237376
- Webinars: https://odin.ornl.gov/downloadables/
- Standards: **CIM IEC 61968-3** (Common Information Model) and **MultiSpeak v4.1+**
- Maintainer: Oak Ridge National Lab + U.S. DOE Office of Electricity
- Coverage: **47 states, 47M+ customers, 155+ utilities, 16 vendor integrators** (as of Feb 2026 deck)
- Refresh: **every 5-15 minutes** (near-real-time)

## What it is

**ODIN** is the federal standard for power outage data interchange in
the United States, run by **Oak Ridge National Laboratory** (ORNL)
under the **U.S. Department of Energy's Office of Electricity**. It
standardizes how electric utilities publish outage data so that
emergency-management agencies, mutual-aid crews, neighbouring
utilities, and the public can all consume the same data shape.

The program is **the right place to start** if you need US
customer-level outage data. The same data shape covers 47 states
and 47M+ customers, updated every 5-15 minutes, with explicit
geometries (per-county polygons, per-utility service territories,
and per-customer-meter points).

## Two access tiers

### 1. Public OpenEnergyHub dataset (free, no signup)

The OpenEnergyHub project (run by ORNL itself) exposes the ODIN
data as a **public Opendatasoft-compatible JSON API** that anyone
can hit. This is the right first step for OSINT-Data v1.

```bash
# Get 5 recent outage records (verified live 2026-09-05)
curl 'https://ornl.opendatasoft.com/api/explore/v2.1/catalog/datasets/odin-real-time-outages-county/records?limit=5'
```

Response (truncated to one record):

```json
{
  "total_count": 691,
  "results": [
    {
      "cause": "Pending Investigation",
      "communitydescriptor": "27043",
      "metersaffected": 1,
      "reportedstarttime": "2026-09-04T20:56:12+00:00",
      "statuskind": "assigned",
      "utilitydisclaimer": "BENCO Electric Cooperative",
      "customersrestored": 0,
      "estimatedrestorationtime": null,
      "causekind": null,
      "name": "BENCO ELECTRIC COOPERATIVE,1884",
      "utility_id": "1884",
      "county": "Faribault",
      "state": "Minnesota",
      "geom": {
        "type": "Feature",
        "geometry": {
          "coordinates": [[[
            [-94.247898, 43.586938],
            [-94.247941, 43.673683],
            ...
            [-94.247898, 43.586938]
          ]]],
          "type": "MultiPolygon"
        },
        "properties": {}
      },
      "geo_point_2d": {"lon": -93.94793196127459, "lat": 43.67391851419451},
      "centroid": {"lon": -93.94799934, "lat": 43.673928316}
    },
    ...
  ]
}
```

Per-record fields (per the OpenEnergyHub schema):
- `cause` (free text) + `causekind` (enum)
- `statuskind` — `assigned` | `investigating` | `restored` | `cancelled` | ...
- `metersaffected` (integer)
- `customersrestored` (integer)
- `reportedstarttime` (ISO 8601)
- `estimatedrestorationtime` (ISO 8601, nullable)
- `name` (utility name + ID)
- `utility_id` (stable string)
- `state`, `county` (FIPS names)
- `geom` (GeoJSON MultiPolygon of the affected service territory)
- `geo_point_2d` (lon, lat)
- `centroid` (lon, lat)
- `utilitydisclaimer` (free text)
- `communitydescriptor` (internal ODIN community code)

**Query filters** the Opendatasoft API supports out of the box:
- `?where=state="Texas"` — by state
- `?where=metersaffected>1000` — large outages only
- `?where=reportedstarttime > '2026-09-04T00:00:00'` — by time
- `?limit=100&offset=0` — pagination
- `?select=uuid,state,county,metersaffected,reportedstarttime` — column selection
- `?group_by=state` — aggregations (e.g. outages per state)

**Total records**: 691 in the live snapshot at 2026-09-05. This is
the **currently active** outages (the dataset is overwritten as
incidents are restored).

### 2. Private ORNL subscriber feed (free, ~1-2 week approval)

For higher fidelity (sub-utility granularity, census-block-group
resolution, per-meter points, no rate limit), apply via email to
`ODIN@ORNL.GOV` with 2 sentences on the use case. Approval is
typically 1-2 weeks. The private feed uses **CIM IEC 61968-3** or
**MultiSpeak v4.1+** — both are IEC/ANSI standards, not proprietary
formats. The private feed also has **historical data** going back
years; the public OpenEnergyHub endpoint only carries the current
snapshot.

## Important caveats

| Caveat | Detail |
|---|---|
| **47 states, not all 50** | The Feb 2026 ORNL deck says "47 states" (up from 38 in 2022). Hawaii, Alaska, and Puerto Rico are not yet covered. |
| **Vendor-mediated for some utilities** | 16 vendor integrators (Milsoft, Bidgely, etc.) push on behalf of IOUs. This is fine; the data shape is the same. |
| **Census-block-group resolution** | The private feed includes per-customer-meter points down to census-block group. The public feed only carries per-utility-service-territory polygons. |
| **Per-record dedup required** | Multiple utilities can report the same incident from overlapping polygons. Resolve by `utility_id + reportedstarttime + communitydescriptor`. |
| **Refresh is "near-real-time" not "real-time"** | The data is published by utilities every 5-15 minutes. The public endpoint reflects the latest snapshot; the private feed includes event timestamps. |
| **No historical archive on the public endpoint** | The public OpenEnergyHub dataset overwrites with the current snapshot. For history, use EAGLE-I (2014-2022) or apply for the private subscriber feed. |
| **Use ODIN + EAGLE-I + OE-417 together** | ODIN is real-time, EAGLE-I is historical, OE-417 is event-level (major disturbances). The three cover the full US power outage timeline. |

## How to wire it up for OpenTIR-Data

1. **First ingest**: hit the public endpoint every 5 minutes via
   cron, store records to `osint.power_outages_us` keyed by
   `(utility_id, reportedstarttime, communitydescriptor)`.
2. **Per-record resolution**: geocode the `geom` polygon (or use
   the `centroid`) to enrich the warehouse with H3 cell, county
   FIPS, state FIPS, and zip.
3. **Per-state rollup**: store a `osint.power_outages_us_state_summary`
   materialized view with `customers_out`, `outage_count`, and
   `last_refresh` per state. Refresh every 5 min.
4. **Historical enrichment**: optionally subscribe to the ORNL
   private feed for historical data, and pull EAGLE-I for the
   2014-2022 backfill.
5. **Correlation with other sources**: join on `state` + `county`
   with EAGLE-I, with `name` to PowerOutage.us utility names, and
   with `utility_id` to per-utility maps (National Grid, Duke,
   ConEd, etc.).

## What we use it for

- **Map view**: per-county outage polygons on the US map, with
  fill opacity proportional to `metersaffected`.
- **Time series**: outages per state per hour, with the ability to
  reconstruct the daily / weekly / seasonal rhythm of grid
  disruptions.
- **Alert pipeline**: real-time alerts when a state's total
  `customers_out` exceeds a threshold (storm response, heat wave,
  cold snap, etc.).
- **Network view**: utility service territory polygons as nodes,
  shared customers as edges — build the US electric grid graph.
- **Story view**: chronicling a single big storm (e.g. Hurricane
  Helene 2024) using the historic per-utility, per-county outage
  timeline.

## See also

- [[eagle_i]] — the historical archive (2014-2022) that ODIN is
  designed to extend
- [[doe-oe417]] — the federal major-event reports (OE-417 form
  submissions) for severe-weather / supply-shortage context
- [[poweroutage_us]] — the commercial 96%-coverage US aggregator
  (cross-check signal)
- [[usoutage_com]] — the WordPress site that scrapes from
  PowerOutage.us; documented as a non-connector reference
- [[national_grid_uk_connected_data]] — the same pattern from
  National Grid UK, also public CKAN API
- [[hydro_quebec_pannes]] — the same pattern from Hydro-Québec,
  also public REST API

## License of this connector note

`connectors/odin.md` is dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

