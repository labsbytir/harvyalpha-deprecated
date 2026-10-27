# National Grid UK — Connected Data Portal (Live Power Cuts)

Key: `none required (CKAN API, public)`
Endpoint: `https://connecteddata.nationalgrid.co.uk/api/3/action/datastore_search?resource_id=292f788f-4339-455b-8cc0-153e14509d4d`
Auth: `none` (CKAN DataStore)
Format: **CSV** (download) + **JSON** (CKAN API)

Documentation:
- Landing: https://connecteddata.nationalgrid.co.uk/
- Live Power Cuts dataset: https://connecteddata.nationalgrid.co.uk/dataset/live-power-cuts
- Live Detailed Power Cuts: https://connecteddata.nationalgrid.co.uk/dataset/live-power-cuts (second resource)
- Live GSP data: https://connecteddata.nationalgrid.co.uk/dataset/ (multiple by region)
- CKAN API guide: https://docs.ckan.org/en/latest/api/index.html
- License: **OGL 3.0** (UK Open Government Licence) — derivative
  use OK with attribution
- Coverage: **National Grid Electricity Distribution** areas —
  East Midlands, West Midlands, South Wales, South West (former
  Western Power Distribution). ~7.7M customers.
- Refresh: **~4 minutes** (last-modified stamp on CSV)

## What it is

**National Grid's Connected Data Portal** is the public CKAN
data portal for the UK's largest distribution network operator.
National Grid Electricity Distribution (NGED) is the legal
successor to **Western Power Distribution** (WPD) — covering
**East Midlands, West Midlands, South Wales, and South West
England** — and serves about 7.7 million customers.

The portal publishes **real-time live data** including:

- **Live Power Cuts** (per-incident, with location, customers
  affected, ETR)
- **Live Detailed Power Cuts** (with per-circuit detail)
- **Live GSP Data** per licence area (Grid Supply Point demand
  at 5-minute intervals)
- **Live Primary Data** (per primary substation)

All under OGL 3.0 (UK Open Government Licence). The CKAN API is
the same one used by data.gov.uk — mature, well-documented, and
public.

## The data shape (Live Power Cuts)

The `power_outage_ext.csv` resource has the following columns (per
the CKAN DataStore schema):

- `Incident ID` (stable identifier)
- `Status` (one of `LIVE`, `PLANNED`, `RESTORED`, `CANCELLED`)
- `Incident Type` (one of `UNPLANNED_INCIDENT`,
  `PLANNED_INCIDENT`, `MAJOR_INCIDENT`)
- `Substation Group` (GSP / primary / circuit)
- `Postcode Area`, `Postcode District`
- `Local Authority`
- `Customers Affected` (integer)
- `Restoration Time Estimated` (ISO 8601)
- `Time Reported` (ISO 8601)
- `Voltage Level` (kV)
- `Fault Type`
- `Incident Notes` (free text)
- `Last Updated` (ISO 8601)

There are ~5-50 records per refresh depending on weather events.
Verified live 2026-09-05: the dataset was last updated 4 minutes
ago (the system updates every ~4 min).

## The other UK DNO (Distribution Network Operator) patterns

National Grid is one of 6 large DNOs in the UK + 1 in Northern
Ireland. The others are:

| DNO | Region | Public outage data |
|---|---|---|
| **National Grid** | East Midlands, West Midlands, South Wales, South West | **Yes — CKAN API on Connected Data Portal** |
| **UK Power Networks** | London, South East, East | partial — `https://www.ukpowernetworks.co.uk/power-cut-map` (no public API documented) |
| **SSE Networks** | North Scotland, Central Southern England | partial — outage map only |
| **SP Energy Networks** | Central & Southern Scotland, Merseyside, Cheshire | partial — outage map only |
| **Northern Powergrid** | North East England, Yorkshire | partial — `https://www.northernpowergrid.com/power-cuts` (no public API documented) |
| **Electricity North West** | North West England | partial — outage map only |
| **NIE Networks** | Northern Ireland | partial — outage map only |

For the **non-National-Grid** UK DNOs, the data is per-utility
outage maps with no documented public API. The pragmatic path is
**PowerOutage.us** (commercial, 89% UK coverage) or **manual
scraping** of the per-utility outage maps.

## How to wire it up for OpenTIR-Data

1. **First ingest**: CKAN API call to `datastore_search` with
   `resource_id=292f788f-4339-455b-8cc0-153e14509d4d` and
   `limit=100`. Refresh every 5 minutes.
2. **Per-incident storage**: write to
   `osint.power_outages_uk` keyed by `Incident ID`. Per-record
   `Customers Affected` + `Status` + `Last Updated`.
3. **Geo-enrichment**: per-incident `Postcode Area` +
   `Postcode District` → ONS Code-Point Open or postcodes.io
   geocoding → H3 cell.
4. **Cross-check with PowerOutage.us UK**: for incidents present
   in both, flag any disagreement.
5. **Per-tenant key (optional)**: the CKAN DataStore is public,
   so no key. For higher rate limits, contact
   `connecteddata@nationalgrid.co.uk`.

## Important caveats

| Caveat | Detail |
|---|---|
| **Covers 4 of 7 UK DNO areas** | ~7.7M of ~33M UK customers. PowerOutage.us covers 27.4M (89%). The gap is the 5 smaller DNOs. |
| **OGL 3.0 (not CC0)** | UK Open Government Licence requires attribution. Track this in per-org audit logs. |
| **Live status is on the web, not just the API** | `https://powercuts.nationalgrid.co.uk/` shows the same data on a public map. |
| **Some incidents are sub-1-hour and don't appear in summaries** | The CKAN endpoint is live; historical snapshots need to be polled. |
| **Per-postcode geocoding is required** | The data has UK postcodes, not lat/lon. Use the free `https://api.postcodes.io/postcodes/{POSTCODE}` for geocoding. |

## What we use it for

- **UK Map view**: per-postcode outage markers on the UK map.
- **Real-time alerting**: 5-min cron → PagerDuty when a single
  incident affects >1,000 customers.
- **Network reliability scoring**: per-DNO SAIDI/CAIDI metrics.
- **Weather correlation**: cross-reference with Met Office
  weather warnings for storm-response journalism.

## See also

- [[odin]] — the US federal standard, same pattern
- [[hydro_quebec_pannes]] — Canada (Quebec), same REST pattern
- [[entso_e_outages]] — Europe transmission-level outages
- [[poweroutage_us]] — commercial 89% UK coverage
- [[usoutage_com]] — the US WordPress scraper, documented as a
  non-connector

## License of this connector note

`connectors/national_grid_uk_connected_data.md` is dedicated to the
public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From National Grid UK Connected Data Portal — Live Power Cuts.md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "National Grid UK Connected Data Portal — Live Power Cuts"
fetcher: ingest.fetchers.nguk_connected_data
source_name: national_grid_uk_connected_data
---

# National Grid UK Connected Data Portal — Live Power Cuts

National Grid UK Connected Data Portal — Live Power Cuts + Live Detailed Power Cuts. CKAN DataStore API, public, OGL 3.0 (UK Open Government Licence). National Grid Electricity Distribution = East Midlands + West Midlands + South Wales + South West = ~7.7M customers. Per-incident, per-postcode. Refresh ~4 min. Attribution required for OGL.

## Metadata

| Field | Value |
|---|---|
| Source system | `national_grid_uk` |
| Base URL | https://connecteddata.nationalgrid.co.uk |
| API base | https://connecteddata.nationalgrid.co.uk/api/3/action |
| Schedule (cron) | `*/5 * * * *` (every 5 min) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | OGL 3.0 (UK Open Government Licence) |
| Auth | none (public) |
| per_tenant_only | false |
| format | ckan_json + csv |

## Collections

| Name | Endpoint | Format | Notes |
|---|---|---|---|
| `live_power_cuts` | https://connecteddata.nationalgrid.co.uk/api/3/action/datastore_search?resource_id=292f788f-4339-455b-8cc0-153e14509d4d | CKAN JSON | summary |
| `live_detailed_power_cuts` | https://connecteddata.nationalgrid.co.uk/api/3/action/datastore_search?resource_id=a1365982-4e05-463c-8304-8323a2ba0ccd | CKAN JSON | detailed |
| `csv_bulk` | https://connecteddata.nationalgrid.co.uk/dataset/d6672e1e-c684-4cea-bb78-c7e5248b62a2/resource/292f788f-4339-455b-8cc0-153e14509d4d/download/power_outage_ext.csv | CSV | bulk download |

## Fetcher

`ingest/fetchers/nguk_connected_data.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='national_grid_uk_connected_data'`. Per-incident rows: `postcode`, `incident_id`, `customers_affected`, `incident_start`, `etr`, `cause`, `voltage`.

## Common queries

```
GET /v1/sources/national_grid_uk_connected_data
GET /v1/sources/national_grid_uk_connected_data/bundles?region=EM&since=2026-09-01
```

## Gotchas

- **OGL 3.0 attribution required.** "Contains public sector information licensed under the Open Government Licence v3.0" in any tenant-facing UI.
- National Grid Electricity Distribution = ~7.7M customers in 4 regions. Not all UK customers.
- ~4 min refresh is from the source; we poll every 5 min so we're at most 9 min behind.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (US counterpart)
- [[Ingestion/Hydro-Québec Pannes en cours (Quebec Outages)]] (Canada counterpart)
- [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (EU transmission)
- [[Ingestion/DOE OE-417 Electric Emergency Incident Reports]] (US major events)


## Migrated Context (From UK Met Office Weather DataHub.md)

---
tags: [source, climate, tier-1, osint-data, free-with-registration, global, model-data]
status: proposed
display_name: "UK Met Office Weather DataHub"
source_name: ukmo_datahub
---

# UK Met Office Weather DataHub

UK Met Office's public-data API for global and UK numerical weather model output. **Free with API key registration** (no payment, just sign up). Best free global model dataset. Replaced the older DataPoint API.

## Metadata

| Field | Value |
|---|---|
| Source system | `ukmo_datahub` |
| Base URL | `https://data.hub.api.metoffice.gov.uk` |
| API docs | https://www.metoffice.gov.uk/services/data/met-office-weather-datahub |
| Auth | API key (free registration) |
| Tier | 1 |
| Axis | climate |
| License | UK Open Government Licence (OGL) for public task data; CC-BY-SA 4.0 for derived redistribution |
| per_tenant_only | false |
| Coverage type | global |

## What's available

- **Global deterministic model** — 10 km resolution, hourly to 54h, 3-hourly to 144h, 6-hourly beyond. 7-day forecast horizon. Updated every 6 hours.
- **UK deterministic model (UKV)** — 2 km resolution, hourly, 2-day forecast. Updated every hour.
- **Global ensemble (MOGREPS-G)** — probabilistic forecasts
- **Site-specific (Global Spot)** — single lat/lon forecast, GeoJSON, three cadences (hourly / 3-hourly / daily)
- **Land Observations** — historical observations from UK ground stations

## Auth

```
# Register at metoffice.gov.uk → get API key
# Then send as header:
subscription-key: {your-key}
```

## Endpoints (selected)

```
# Global Spot (single point, hourly)
GET https://data.hub.api.metoffice.gov.uk/global-spot/1.0.2/spot-data/hourly
    ?latitude=−1.29&longitude=36.82
    &subscription-key={your-key}

# Global Spot (3-hourly)
GET https://data.hub.api.metoffice.gov.uk/global-spot/1.0.2/spot-data/three-hourly
    ?latitude=−1.29&longitude=36.82
    &subscription-key={your-key}

# Global Spot (daily)
GET https://data.hub.api.metoffice.gov.uk/global-spot/1.0.2/spot-data/daily
    ?latitude=−1.29&longitude=36.82
    &subscription-key={your-key}
```

For GRIB2 gridded data (full model output), the download is via a separate ordering flow — see the DataHub docs.

## Fetcher

Not yet implemented. Pattern: for a tenant's bbox, sample on a regular grid (e.g., 0.5° spacing) using the Global Spot endpoint, then store per-point per-step. For pure text forecasts, 100 points per region per day is plenty.

## Storage

ClickHouse `osint.bundles` with `source_name='ukmo_datahub'`. Per-point per-step rows. Fields: `lat`, `lon`, `forecast_step`, `valid_time`, `temp_c`, `wind_speed_mps`, `wind_dir_deg`, `precip_mm`, `pressure_hpa`, `humidity_pct`.

## Common queries

```
GET /v1/sources/ukmo_datahub
GET /v1/sources/ukmo_datahub/bundles?lat=−1.29&lon=36.82&since=2026-09-01
```

## Gotchas

- **DataHub ≠ DataPoint.** DataPoint is being deprecated; new code should target DataHub. URL structure is completely different.
- **UKMO open-data has a 4-hour delay** vs. the model's "official" run. Fine for OSINT, just don't promise real-time.
- **API key in URL vs header:** some endpoints use `?subscription-key=` (Global Spot), others use `Ocp-Apim-Subscription-Key` header. Read the endpoint docs.
- **Rate limits:** unstated in public docs but reasonable. Don't hammer.
- **UK + Global ≠ all of Europe.** Global is global; UK is just UK.

## Why I picked this

- **Free, no payment.** Just an email and a key.
- **Official national meteorological service data** — same quality as commercial weather APIs.
- **Global, including Africa.** Most "free" weather APIs are US-centric.
- **3 cadences of spot data** cover most use cases without needing to download GRIB2.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[WMO World Weather Information Service (WWIS) JSON API]] — for city-level observations + climatology
- [[CHIRPS Rainfall via Digital Earth Africa]] — historical rainfall

