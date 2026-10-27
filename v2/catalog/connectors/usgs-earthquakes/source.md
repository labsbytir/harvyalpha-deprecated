# USGS Earthquake Hazards Program (real-time global earthquakes)

Key: `none required` — public, no key, no auth, no rate limit (USGS-published terms; use at reasonable rates)
Endpoint: `https://earthquake.usgs.gov/earthquakes/feed/v1.0/`
Auth: none
Format: `GeoJSON` (default), `CSV` (use the `.csv` suffix instead of `.geojson`)

Documentation:
- API home: https://earthquake.usgs.gov/earthquakes/feed/v1.0/
- GeoJSON spec: https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php
- CSV spec: https://earthquake.usgs.gov/earthquakes/feed/v1.0/csv.php
- Data feeds: https://earthquake.usgs.gov/earthquakes/feed/
- Earthquake catalog API: https://earthquake.usgs.gov/fdsnws/event/1/
- Webhook / push: https://earthquake.usgs.gov/earthquakes/feed/v1.0/push.json (deprecated; use the catalog API)

## What it is

The **USGS Earthquake Hazards Program** is the authoritative source for
global earthquake data. It consolidates seismic readings from ~200 stations
worldwide, processes them in near real-time, and publishes them as a
**GeoJSON feed** that's updated every minute.

Each event is a point with magnitude, depth, location, time, and a link to
the detailed event page. The feed covers ~150+ earthquakes per day globally
(>2.5 magnitude) and ~25,000 per year (>1.0 magnitude). The feed is
**the single most reliable free source for global earthquake data** — used
by everyone from academic seismologists to journalists to the-world-now.com.

This is also **tier 1 OSINT data**: every dashboard and newsroom that covers
disasters needs this feed.

## API endpoints (all verified live 2026-09-05)

```text
# Standard feeds (GeoJSON, updated every minute)
GET /earthquakes/feed/v1.0/summary/all_hour.geojson
GET /earthquakes/feed/v1.0/summary/all_day.geojson
GET /earthquakes/feed/v1.0/summary/all_week.geojson
GET /earthquakes/feed/v1.0/summary/significant_hour.geojson
GET /earthquakes/feed/v1.0/summary/significant_day.geojson
GET /earthquakes/feed/v1.0/summary/significant_week.geojson
GET /earthquakes/feed/v1.0/summary/4.5_hour.geojson       # M4.5+, last hour
GET /earthquakes/feed/v1.0/summary/4.5_day.geojson        # M4.5+, last 24h
GET /earthquakes/feed/v1.0/summary/4.5_week.geojson       # M4.5+, last 7d
GET /earthquakes/feed/v1.0/summary/2.5_hour.geojson       # M2.5+
GET /earthquakes/feed/v1.0/summary/2.5_day.geojson
GET /earthquakes/feed/v1.0/summary/2.5_week.geojson
GET /earthquakes/feed/v1.0/summary/1.0_hour.geojson       # M1.0+
GET /earthquakes/feed/v1.0/summary/1.0_day.geojson
GET /earthquakes/feed/v1.0/summary/1.0_week.geojson

# CSV variants (use .csv instead of .geojson)
GET /earthquakes/feed/v1.0/summary/all_day.csv

# Full FDSN catalog API (advanced queries)
GET /fdsnws/event/1/query?format=geojson&starttime=2026-09-01&endtime=2026-09-05&minmagnitude=4.5
GET /fdsnws/event/1/query?format=csv&starttime=2026-09-01&endtime=2026-09-05&minmagnitude=2.5&maxmagnitude=5.0
```

The FDSN catalog supports queries by:
- `starttime`, `endtime` (ISO 8601 or YYYY-MM-DD)
- `minmagnitude`, `maxmagnitude`
- `mindepth`, `maxdepth`
- `minlatitude`, `maxlatitude`, `minlongitude`, `maxlongitude` (bbox)
- `orderby` ("time" | "magnitude" | "time-asc")
- `limit` (max 20,000 per call)
- `offset` (for pagination)
- `eventtype` ("earthquake" | "quarry" | "explosion" | "landslide" | "ice quake" | "other")

## Quick call — verify (no key, no auth)

```bash
# Last 24 hours, GeoJSON
curl -sL "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('count:', d['metadata']['count'])
print('title:', d['metadata']['title'])
print('first event:')
e = d['features'][0]
p = e['properties']
print('  mag', p['mag'], '|', p['place'], '|', p['time'])
print('  url:', p['url'])
"
# Expected: count: 150-300, mag values typically 1.0-5.0, places like "24 km W of Garden City, Texas"

# Last hour, M2.5+ only (more selective)
curl -sL "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/2.5_hour.geojson" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('M2.5+ last hour:', d['metadata']['count'])
"

# Catalog query: M4.5+ in the last week
curl -sL "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&minmagnitude=4.5&starttime=2026-08-29" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('M4.5+ in last week:', d['metadata']['count'])
"
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/usgs_earthquakes.py
# Daily pull of every M2.5+ earthquake worldwide.
import httpx
from datetime import datetime, timezone, timedelta
from ingest.clickhouse import ch

BASE = "https://earthquake.usgs.gov/earthquakes/feed/v1.0"


def fetch_earthquakes(feed: str = "all_day", min_mag: float = 2.5) -> list[dict]:
    """Fetch earthquakes from one of the standard feeds.

    Valid feeds: all_hour, all_day, all_week, significant_hour, significant_day,
                 significant_week, 2.5_hour, 2.5_day, 2.5_week, etc.
    """
    url = f"{BASE}/summary/{feed}.geojson"
    r = httpx.get(url, timeout=30.0)
    r.raise_for_status()
    d = r.json()
    now = datetime.now(timezone.utc)
    rows = []
    for f in d.get("features", []):
        p = f["properties"]
        geom = f["geometry"]["coordinates"]  # [lon, lat, depth]
        try:
            mag = float(p.get("mag", 0))
        except (TypeError, ValueError):
            mag = 0
        if mag < min_mag:
            continue
        rows.append({
            "as_of": now,
            "usgs_id": f["id"],
            "mag": mag,
            "place": p.get("place", ""),
            "time_ms": p.get("time", 0),
            "time_iso": datetime.fromtimestamp(
                p.get("time", 0) / 1000, tz=timezone.utc
            ).isoformat(),
            "lon": geom[0] if len(geom) > 0 else None,
            "lat": geom[1] if len(geom) > 1 else None,
            "depth_km": geom[2] if len(geom) > 2 else None,
            "url": p.get("url", ""),
            "title": p.get("title", ""),
            "type": p.get("type", "earthquake"),
            "felt": p.get("felt"),
            "tsunami": p.get("tsunami", 0),
            "sig": p.get("sig"),
            "alert": p.get("alert", ""),       # 'green' | 'yellow' | 'orange' | 'red'
            "credibility": 1,                    # USGS = tier 1
            "source_url": p.get("detail", ""),
        })
    return rows


if __name__ == "__main__":
    rows = fetch_earthquakes(feed="all_day", min_mag=2.5)
    if rows:
        ch.insert_observations("earthquakes", rows)
    print(f"inserted {len(rows)} earthquakes (M2.5+, last 24h)")
```

## Notes

- **Free for any use** — no rate limits published; USGS just asks "be reasonable."
  For high-volume automated use (>1 req/sec sustained), contact USGS.
- **Updated every minute** — polling every 5-10 minutes is fine; every minute
  is overkill unless you're pushing real-time alerts.
- **GeoJSON is the canonical format** — every dashboard library (deck.gl,
  MapLibre, Leaflet) consumes it directly.
- **Coverage**: global, with best latency for US, fair for Europe, sometimes
  delayed (10-30 min) for remote regions.
- **Volume**: ~150-300 quakes/day M2.5+, ~25K/year M1.0+. Negligible storage.
- **Used by everyone** — including the-world-now.com, Bellingcat, every
  disaster dashboard, every newsroom. We're going direct to the source.
- **Credibility tier**: 1 (USGS = primary source).
- **License**: USGS data is in the **public domain** (US Government work).
  No attribution required (though academic citation is appreciated).
- **For the world dashboard**: this is the **single highest-value real-time
  feed** for the "natural disaster" axis. Pair with NASA FIRMS for the
  "wildfire" axis and Smithsonian GVP for "volcanoes" and you have the
  complete natural-disaster coverage for free.
- **Comparison to other sources**:
  - **EMSC (European-Mediterranean Seismological Centre)**: faster in Europe
    but less comprehensive. Add as a secondary source if needed.
  - **IRIS**: academic-grade but bulk-only (not real-time).
  - **External APIs events**: includes earthquakes as events, but with 24-48h latency.

## License: USGS-produced data, public domain

The data is produced by the US Geological Survey and is in the public domain
(US Government work, 17 U.S.C. § 105). No copyright, no licensing
restrictions, no attribution requirement. Standard academic citation is
appreciated but not legally required.


## Migrated Context (From U.S. EIA Open Data (Energy Information Administration).md)

---
tags: [source, energy, economic, tier-1, osint-data, mvp, requires-key]
status: active
display_name: "U.S. EIA Open Data (Energy Information Administration)"
fetcher: ingest.fetchers.eia_open_data
source_name: eia_open_data
api_key_env: EIA_API_KEY
---

# U.S. EIA Open Data (Energy Information Administration)

U.S. Energy Information Administration Open Data API (`api.eia.gov/v2`). Public domain (US Government work). 1.3M+ time series across petroleum, natural gas, electricity, coal, renewables, nuclear, consumption, prices, international. Free API key at api.eia.gov (registration, 1-day approval). The right primary US source for the energy axis; pairs with [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (European grid) + [[Ingestion/AEMO NEMWeb (Australian Energy Market Operator)]] (Australian grid).

## Metadata

| Field | Value |
|---|---|
| Source system | `eia_open_data` |
| Base URL | https://www.eia.gov |
| API base | https://api.eia.gov/v2 |
| Schedule (cron) | `0 4 * * *` (daily at 04:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | energy, economic |
| License | Public domain (US Government work) |
| Auth | **Required**: `EIA_API_KEY` (free, 1-day approval) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `electricity` | https://api.eia.gov/v2/electricity | GET | paginated JSON |
| `petroleum` | https://api.eia.gov/v2/petroleum | GET | paginated JSON |
| `natural_gas` | https://api.eia.gov/v2/natural-gas | GET | paginated JSON |
| `international` | https://api.eia.gov/v2/international | GET | paginated JSON |

## Fetcher

`ingest/fetchers/eia_open_data.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='eia_open_data'`. Per-series, per-period rows.

## Common queries

```
GET /v1/sources/eia_open_data
GET /v1/sources/eia_open_data/bundles?route=electricity&frequency=hourly
GET /v1/sources/eia_open_data/aggregates?group_by=series,period
```

## Gotchas

- **1-day approval** for the API key. Build that into onboarding.
- 1.3M+ time series; paginate. Use `frequency=` to filter (`hourly`, `daily`, `weekly`, `monthly`, `annual`).
- `international` endpoint has 200+ countries, 100+ indicators per country.
- The right call for "how much oil is the US producing" and similar.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (energy + economic axes)
- [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (EU grid)
- [[Ingestion/AEMO NEMWeb (Australian Energy Market Operator)]] (AU grid)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (US customer outages)
- [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]] (emissions)


## Migrated Context (From PowerOutage.us Commercial Aggregator [PER-TENANT-ONLY].md)

---
tags: [source, info_environment, climate, tier-1, osint-data, requires-key, per-tenant-only]
status: active
display_name: "PowerOutage.us Commercial Aggregator [PER-TENANT-ONLY]"
fetcher: ingest.fetchers.poweroutage_us
source_name: poweroutage_us
api_key_env: POWEROUTAGE_US_API_KEY
---

# PowerOutage.us Commercial Aggregator [PER-TENANT-ONLY]

PowerOutage.us — commercial aggregator. 96% US, 95% Canada, 89% UK coverage. 1,110+ utilities. REST + GeoJSON + CSV. Refresh ~10 min. The commercial cross-check for ODIN; same data shape as usoutage.com (which scrapes from this). **PER-TENANT-ONLY**: this source is commercial-restricted and was demoted in the [[Plan/4-Pass Audit Loop]] (2026-09-05).

## Metadata

| Field | Value |
|---|---|
| Source system | `poweroutage_us` |
| Base URL | https://poweroutage.us |
| API base | https://api.poweroutage.us/v1 |
| Schedule (cron) | `*/10 * * * *` (every 10 min) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | Commercial (per-tenant license) |
| Auth | **Required**: `POWEROUTAGE_US_API_KEY` (tenant-brings-own) |
| per_tenant_only | **true** |

## Collections

| Name | Endpoint | Format | Auth |
|---|---|---|---|
| `api_national` | https://api.poweroutage.us/v1/national | JSON | key required |
| `api_state` | https://api.poweroutage.us/v1/states | JSON | key required |
| `api_county_geojson` | https://api.poweroutage.us/v1/geojson/counties | GeoJSON | key required |
| `api_utility` | https://api.poweroutage.us/v1/utilities | JSON | key required |

## Fetcher

`ingest/fetchers/poweroutage_us.py`

## Storage

**Not in shared warehouse.** Per-tenant DuckDB slice only. Tenants opt in by bringing their own key.

## Common queries

```
GET /v1/sources/poweroutage_us           # (per-tenant only)
GET /v1/sources/poweroutage_us/bundles?state=TX
```

## Gotchas

- **The only source with `per_tenant_only: true`.** The 5 free public-domain alternatives already wired (ODIN CC0, EAGLE-I CC-BY, DOE OE-417 PD, [[Ingestion/National Grid UK Connected Data Portal — Live Power Cuts]] OGL, [[Ingestion/Hydro-Québec Pannes en cours (Quebec Outages)]] OGL-Quebec) cover the same US + UK + Canada geography. Don't ingest this on the shared warehouse.
- usoutage.com scrapes from this; we don't.
- Tenants can opt in to PowerOutage.us by setting their own key; the shared warehouse does not aggregate this data by default.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (free counterpart, US)
- [[Ingestion/EAGLE-I Historical US Outage Archive (ORNL 2014-2022)]] (free historical)
- [[Ingestion/DOE OE-417 Electric Emergency Incident Reports]] (free major events)
- [[Ingestion/National Grid UK Connected Data Portal — Live Power Cuts]] (free UK)
- [[Ingestion/Hydro-Québec Pannes en cours (Quebec Outages)]] (free Canada)
- [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (EU transmission)
- [[Ingestion/AEMO NEMWeb (Australian Energy Market Operator)]] (AU transmission)
- [[Ingestion/Per-Utility Outage Maps (US Bespoke Scrapes)]] (gap fill)


## Migrated Context (From ENTSO-E Transparency Platform (European Grid).md)

---
tags: [source, info_environment, economic, tier-1, osint-data, requires-key]
status: active
display_name: "ENTSO-E Transparency Platform (European Grid)"
fetcher: ingest.fetchers.entso_e
source_name: entso_e_outages
api_key_env: ENTSOE_SECURITY_TOKEN
---

# ENTSO-E Transparency Platform (European Grid)

ENTSO-E Transparency Platform — European transmission outages + market data. All 61 EU bidding zones. `get_generation_outages` + `get_transmission_outages` for outage tracking; `get_day_ahead_prices` + `get_load` for context. Free security token via transparency@entsoe.eu (1-2 business day). XML (IEC 62325). Transmission-level, not customer-level.

## Metadata

| Field | Value |
|---|---|
| Source system | `entso_e` |
| Base URL | https://transparency.entsoe.eu |
| API base | https://web-api.tp.entsoe.eu/api |
| Schedule (cron) | `0 * * * *` (hourly) |
| Rate limit | 6 req/min |
| Tier | 1 |
| Axis | info_environment, economic |
| License | ENTSO-E terms (free, attribution required) |
| Auth | **Required**: `ENTSOE_SECURITY_TOKEN` (free, 1-2 business day approval) |
| per_tenant_only | false |
| format | xml (IEC 62325) |

## Collections

| Name | Endpoint | Method | Auth |
|---|---|---|---|
| `generation_outages` | https://web-api.tp.entsoe.eu/api | GET | key required |
| `transmission_outages` | https://web-api.tp.entsoe.eu/api | GET | key required |

## Fetcher

`ingest/fetchers/entso_e.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='entso_e_outages'`. Per-asset, per-day rows.

## Common queries

```
GET /v1/sources/entso_e_outages
GET /v1/sources/entso_e_outages/bundles?bidding_zone=DE_LU&since=2026-09-01
```

## Gotchas

- API is XML (IEC 62325 standard); not the friendliest format. Use the `entsoe-py` library or hand-roll the parser.
- Token approval takes 1-2 business days; build that lead time into onboarding.
- 6 req/min is tight; batch by bidding zone.
- **Transmission-level**, not customer-level. Use [[Ingestion/National Grid UK Connected Data Portal — Live Power Cuts]] for UK customer-level.

## Related

- [[Plan/Source Categorization]] (info_environment + economic axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (US customer-level)
- [[Ingestion/National Grid UK Connected Data Portal — Live Power Cuts]] (UK customer-level)
- [[Ingestion/Hydro-Québec Pannes en cours (Quebec Outages)]] (CA customer-level)
- [[Ingestion/AEMO NEMWeb (Australian Energy Market Operator)]] (AU transmission)
- [[Ingestion/U.S. EIA Open Data (Energy Information Administration)]] (US energy context)


## Migrated Context (From Hydro-Québec Pannes en cours (Quebec Outages).md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "Hydro-Québec Pannes en cours (Quebec Outages)"
fetcher: ingest.fetchers.hydro_quebec
source_name: hydro_quebec_pannes
---

# Hydro-Québec Pannes en cours (Quebec Outages)

Hydro-Québec — Pannes en cours (Quebec power outages). Public REST API + KMZ polygons. 3-step pattern: `bisversion.json` → `bismarkers{BIS_VERSION}.json` → `bispoly{BIS_VERSION}.kmz`. Per-panne JSON with `dateHeureDebut`, `nombreClientsAffectes`, `cause`, `coordonnees`, `mrc`, `region`. Planned interruptions (AIP) parallel pattern. OGL-Quebec (attribution required).

## Metadata

| Field | Value |
|---|---|
| Source system | `hydro_quebec` |
| Base URL | https://donnees.hydroquebec.com/explore/dataset/pannes-interruptions/ |
| API base | https://pannes.hydroquebec.com/pannes/donnees/v3_0 |
| Schedule (cron) | `*/5 * * * *` (every 5 min) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | OGL-Quebec (attribution required) |
| Auth | none (public) |
| per_tenant_only | false |
| format | json + kmz |

## Collections

| Name | Endpoint | Format |
|---|---|---|
| `bisversion` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/bisversion.json | JSON |
| `bismarkers` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/bismarkers{BIS_VERSION}.json | JSON |
| `bispoly_kmz` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/bispoly{BIS_VERSION}.kmz | KMZ |
| `aipversion` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipversion.json | JSON |
| `aipmarkers` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipmarkers{AIP_VERSION}.json | JSON |
| `aippoly_kmz` | https://pannes.hydroquebec.com/pannes/donnees/v3_0/aippoly{AIP_VERSION}.kmz | KMZ |

## Fetcher

`ingest/fetchers/hydro_quebec.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='hydro_quebec_pannes'`. Per-panne rows + KMZ polygons in R2.

## Common queries

```
GET /v1/sources/hydro_quebec_pannes
GET /v1/sources/hydro_quebec_pannes/bundles?region=Montréal&since=2026-09-01
```

## Gotchas

- 3-step version-marker-polygon pattern. Always read `bisversion.json` first to get the current `BIS_VERSION`.
- Two parallel sets: `bis*` (active outages) and `aip*` (planned interruptions).
- OGL-Quebec attribution required.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (US counterpart)
- [[Ingestion/National Grid UK Connected Data Portal — Live Power Cuts]] (UK counterpart)
- [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (EU transmission)


## Migrated Context (From USGS Earthquake Hazards Program GeoJSON Feeds.md)

---
tags: [source, climate, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "USGS Earthquake Hazards Program GeoJSON Feeds"
fetcher: ingest.fetchers.usgs_earthquakes
source_name: usgs_earthquakes
---

# USGS Earthquake Hazards Program GeoJSON Feeds

USGS real-time + historical earthquake feeds. 14 GeoJSON feeds at different time windows + magnitude thresholds (`all_hour`, `all_day`, `2.5_day`, `4.5_week`, `significant_week`, etc.). Refresh every 1-5 min.

## Metadata

| Field | Value |
|---|---|
| Source system | `usgs_eq` |
| Base URL | https://earthquake.usgs.gov |
| API base | https://earthquake.usgs.gov/earthquakes/feed/v1.0 |
| Schedule (cron) | `*/5 * * * *` (every 5 min) |
| Rate limit | 12 req/min |
| Tier | 1 |
| Axis | climate (we file seismic events under the hazards axis) |
| License | Public domain (US Government work) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Feed | Notes |
|---|---|---|
| `all_day_m25` | `all_day`, min_magnitude=2.5 | ~150 events/day globally |
| `all_week_m45` | `all_week`, min_magnitude=4.5 | ~30 events/week |

## Fetcher

`ingest/fetchers/usgs_earthquakes.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='usgs_earthquakes'`. Per-event rows: `id`, `magnitude`, `place`, `time`, `updated`, `tz`, `url`, `detail`, `felt`, `cdi`, `mmi`, `alert`, `status`, `tsunami`, `sig`, `net`, `code`, `ids`, `sources`, `types`, `nst`, `dmin`, `rms`, `gap`, `magType`, `type`, `title`, `geometry`.

## Common queries

```
GET /v1/sources/usgs_earthquakes
GET /v1/sources/usgs_earthquakes/bundles?min_mag=4.5&since=2026-09-01
GET /v1/sources/usgs_earthquakes/aggregates?group_by=mag_type,alert
```

## Gotchas

- Refresh is every 5 min on the `*/5` cron; USGS itself updates every 1 min, so we lag by 4 min.
- `all_hour` feed occasionally has duplicate IDs near refresh boundaries; dedupe on `id`.
- Tsunami flag is `0` or `1` (not boolean). `alert` is `null` until magnitude ≥ 5.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]]
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (multi-hazard context)
- [[Ingestion/Smithsonian Global Volcanism Program Weekly Activity]] (companion: volcanic activity)

