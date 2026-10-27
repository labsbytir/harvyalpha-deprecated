# Global Energy Monitor (GEM) — 25 open energy trackers

Key: `none required (CC-BY 4.0)`
Endpoint: `https://globalenergymonitor.org/` (per-tracker download pages)
Auth: `none`
Format: **CSV** (per tracker, ~30 columns) + **GEM.wiki** (per-facility fact sheet with footnoted citations)

Documentation:
- Main page: https://globalenergymonitor.org/
- GEM.wiki: https://www.gem.wiki
- API metadata: `https://api.globalenergymonitor.org/catalog/metadata`
- 25 trackers (full list): https://www.gem.wiki/Main_Page
- Specific trackers (per fuel / sector):
  - Global Coal Plant Tracker: https://globalenergymonitor.org/projects/global-coal-plant-tracker
  - Global Oil and Gas Plant Tracker: https://globalenergymonitor.org/projects/global-oil-gas-plant-tracker
  - Global Wind Power Tracker: https://globalenergymonitor.org/projects/global-wind-power-tracker
  - Global Solar Power Tracker: https://globalenergymonitor.org/projects/global-solar-power-tracker
  - Global Geothermal Power Tracker: https://globalenergymonitor.org/projects/global-geothermal-power-tracker
  - Global Bioenergy Power Tracker: https://globalenergymonitor.org/projects/global-bioenergy-power-tracker
  - Global Nuclear Power Tracker: https://globalenergymonitor.org/projects/global-nuclear-power-tracker
  - Global Hydropower Tracker: https://globalenergymonitor.org/projects/global-hydropower-tracker
  - + 17 more (coal mines, gas pipelines, LNG terminals, oil/gas
    extraction, hydrogen, wind/solar/battery manufacturing, etc.)
- License: **CC-BY 4.0** (all trackers)
- Update cadence: **bi-annual** (January and July) for most
  trackers; quarterly for some
- Coverage: **all countries** with significant infrastructure

## What it is

**Global Energy Monitor** is the most active open-source power
plant infrastructure project as of 2026. It maintains **25
trackers** across every energy sector (coal, oil, gas, wind,
solar, hydro, nuclear, geothermal, bioenergy, hydrogen,
transmission, LNG, mines, manufacturing) with **bi-annual
updates** to CSV files, each row linked to a **GEM.wiki fact
sheet** with footnoted citations to news articles, government
reports, and regulatory permits.

The model is "two-level": a structured **database** (the CSV) +
per-facility **wiki pages** (the citations). This is the same
pattern as the [[wri_gppd]] but with a live, active maintainer
and per-fuel / per-sector scope.

## Why GEM is the right primary source

The [[wri_gppd]] has been **frozen since 2022** with no
maintenance. GEM is the right replacement for:

- **Current data**: bi-annual updates
- **Per-fuel detail**: separate trackers for coal, gas, wind,
  solar, hydro, nuclear, geothermal, bioenergy (instead of one
  big "everything" CSV)
- **Status tracking**: each facility has a status (`operating`,
  `under construction`, `announced`, `retired`, `mothballed`,
  `cancelled`)
- **Citations**: every row links to a GEM.wiki page with footnoted
  sources. This is the **right** "show your work" data for
  journalism.
- **Beyond power plants**: GEM also tracks mines, pipelines,
  LNG terminals, hydrogen, transmission, and manufacturing.

## The data shape (per the API metadata)

A coal plant record (per the `coal-plants` API metadata):

```json
{
  "slug": "coal-plants",
  "name": "Global Coal Plant Tracker",
  "field_count": 49,
  "field_categories": [
    "IDs", "Names", "Geography", "Main", "Size", "Age",
    "Details", "Reference", "Ownership", "CO2 estimates"
  ],
  "url": "/catalog/metadata/coal-plants"
}
```

49 fields, 10 categories. Per-plant CSV rows typically include:

- `Plant` (name)
- `Plant ID` (GEM-internal, stable)
- `Country` (3-letter ISO + full name)
- `Subnational unit` (state/province)
- `Latitude`, `Longitude`
- `Status` (`operating`, `construction`, `announced`, `pre-construction`, `retired`, `mothballed`)
- `Year` (commissioning year)
- `Capacity (MW)` (installed)
- `Status` (operating / under construction / announced / retired / mothballed / cancelled)
- `Owner` (operating company)
- `Parent` (parent company)
- `Coal type` (bituminous / sub-bituminous / lignite / anthracite)
- `Wiki URL` (link to GEM.wiki fact sheet)
- `GEM unit ID` (when the plant has multiple units, each has its own row)

The oil & gas plant tracker has similar structure with 50+ fields.

## The 25 trackers

| Tracker | Scope | Update |
|---|---|---|
| Global Coal Plant Tracker | Coal plants ≥ 30 MW | Bi-annual (Jan, Jul) |
| Global Oil and Gas Plant Tracker | Oil/gas plants ≥ 50 MW (≥ 20 MW EU/UK) | Bi-annual (Jan, Aug) |
| Global Wind Power Tracker | Wind farms | Bi-annual |
| Global Solar Power Tracker | Solar farms | Bi-annual |
| Global Geothermal Power Tracker | Geothermal | Annual |
| Global Bioenergy Power Tracker | Biomass / waste-to-energy | Annual |
| Global Nuclear Power Tracker | Nuclear | Bi-annual |
| Global Hydropower Tracker | Hydro | Bi-annual |
| Global Coal Mine Tracker | Coal mines | Bi-annual |
| Global Coal Terminals Tracker | Coal terminals | Annual |
| Global Oil Refinery Tracker | Refineries | Annual |
| Global Gas Plant Tracker | (see Oil and Gas Plant Tracker) | — |
| Global Gas Pipelines Tracker | Gas transmission pipelines | Bi-annual |
| Global LNG Terminals Tracker | LNG import/export terminals | Bi-annual |
| Global Hydrogen Plant Tracker | Hydrogen production | Bi-annual |
| Global Iron and Steel Tracker | Steel plants (sectoral) | Annual |
| Global Cement and Concrete Tracker | Cement plants (sectoral) | Annual |
| Global Wind Turbine Manufacturers Tracker | Turbines | Annual |
| Global Solar Component Manufacturers Tracker | Panels | Annual |
| Global Battery Manufacturers Tracker | Cells + packs | Annual |
| + 5 more (subsidiaries of the above) | | |

## How to wire it up for OpenTIR-Data

1. **First ingest**: download the latest CSV for each of the
   8 power-sector trackers (coal, oil/gas, wind, solar,
   geothermal, bioenergy, nuclear, hydro). One per tracker.
   Total ~30 MB.
2. **Per-plant storage**: write to `osint.power_plants_gem`
   keyed by `(tracker, plant_id)`. Per-record `country`,
   `latitude`, `longitude`, `capacity_mw`, `status`,
   `commissioning_year`, `owner`, `wiki_url`.
3. **Status tracking**: the `status` field lets us filter
   for "operating", "under construction", "announced",
   "retired" — the right filter for journalism ("show me all
   coal plants retired in 2024" or "show me all solar farms
   announced in 2025").
4. **Wiki enrichment**: each `wiki_url` is a deep link to a
   footnoted fact sheet. For journalist-facing views, link
   to the wiki page from the dashboard.
5. **Cross-reference with [[wri_gppd]]** and
   [[wikidata_power_plants]] for plant-level reconciliation.

## Important caveats

| Caveat | Detail |
|---|---|
| **Bi-annual update lag** | Updates happen in January and July. For real-time data, [[odin]] or [[entso_e_outages]] is more current. |
| **Threshold is 30-50 MW, varies by tracker** | Small-scale solar / diesel / biomass are not in the primary trackers. |
| **Per-unit, not per-plant, for some** | Coal plants often have 2-4 units. Each unit has its own row. The `Plant` field is the human name; the `GEM unit ID` is the unique row key. |
| **Status field is curated** | The `status` field is curated by GEM researchers, not scraped. This is high-quality but slow. |
| **GEM.wiki is the citation source** | Every row links to a wiki page with footnotes. The wiki is the *primary* source of truth; the CSV is the *projection*. |
| **GEM is a small non-profit** | ~25 staff. The bi-annual cadence is sustainable but the project is at the mercy of grants. |

## What we use it for

- **Energy infrastructure dashboard**: per-fuel installed
  capacity by country, with operating vs. under-construction
  vs. announced.
- **Climate journalism**: "which countries are still building
  new coal plants?" — answer with GEM's `status` field.
- **Supply chain**: the manufacturers trackers (wind turbines,
  solar panels, batteries) feed our energy-supply dashboards.
- **Citation-grade claims**: every dashboard claim about a
  specific power plant links to a GEM.wiki fact sheet. This is
  the **trust** layer.

## See also

- [[wri_gppd]] — the frozen 2022 baseline
- [[openinframap]] — the live OSM-based power infrastructure
- [[wikidata_power_plants]] — the SPARQL endpoint
- [[entso_e_outages]] + [[aemo_outages]] — generation units in
  EU + Australia
- [[odin]] — for joining with US power outage data

## License of this connector note

`connectors/gem_global_energy_monitor.md` is dedicated to the
public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From Wikidata — Global Power Infrastructure (SPARQL).md)

---
tags: [source, info_environment, tier-1, osint-data, public-no-auth]
status: active
display_name: "Wikidata — Global Power Infrastructure (SPARQL)"
fetcher: ingest.fetchers.wikidata_power_plants
source_name: wikidata_power_plants
---

# Wikidata — Global Power Infrastructure (SPARQL)

Wikidata — global power infrastructure via SPARQL. CC0 1.0 (facts) + CC-BY-SA 4.0 (labels). QIDs: Q159719 (power plant), Q134447 (nuclear), Q194356 (wind farm), Q13293210 (solar farm), Q15911738 (hydroelectric). Properties: P17 (country ISO 3166-1), P210 (installed capacity MW), P625 (coordinate), P619 (commissioning date), P176 (operator), P749 (parent org), P1056 (fuel source), P18 (image), P910 (Wikipedia link), P8947 (Global Power Plant Database ID — the `gppd_idnr` from [[Ingestion/WRI Global Power Plant Database v1.3.0]]). The right cross-reference federation layer joining [[Ingestion/WRI Global Power Plant Database v1.3.0]] + [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] + [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] + [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]].

## Metadata

| Field | Value |
|---|---|
| Source system | `wikidata` |
| Base URL | https://www.wikidata.org |
| API base | https://query.wikidata.org/sparql |
| Schedule (cron) | `0 0 1 * *` (monthly) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment |
| License | CC0 1.0 (facts) + CC-BY-SA 4.0 (labels) |
| Auth | none (public) |
| per_tenant_only | false |
| format | sparql_json + json + gz_jsonl |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `sparql_power_plants` | https://query.wikidata.org/sparql | POST | SPARQL JSON |
| `rest_api_lookup` | https://www.wikidata.org/w/api.php | GET | JSON |
| `bulk_dump` | https://dumps.wikimedia.org/wikidatawiki/entities/latest-all.json.gz | GET | gz JSONL (~80 GB) |

## Fetcher

`ingest/fetchers/wikidata_power_plants.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='wikidata_power_plants'`. Per-QID rows.

## Common queries

```
GET /v1/sources/wikidata_power_plants
GET /v1/sources/wikidata_power_plants/bundles?Q=Q159719&country=Q30
```

## Gotchas

- **~110M total Wikidata items.** Don't `SELECT *` — the 30-second SPARQL timeout will fire. Always filter.
- **User-Agent header required** per the Wikidata User-Agent policy. Include contact email.
- 80 GB bulk dump is for the truly committed; SPARQL is the right call for selective ingestion.
- P8947 is the federation key from [[Ingestion/WRI Global Power Plant Database v1.3.0]]'s `gppd_idnr`.

## Related

- [[Plan/Source Categorization]] (info_environment axis)
- [[Ingestion/WRI Global Power Plant Database v1.3.0]] (joined via P8947)
- [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] (federation)
- [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] (federation)
- [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]] (federation)


## Migrated Context (From Smithsonian Global Volcanism Program Weekly Activity.md)

---
tags: [source, climate, tier-1, osint-data, html-scrape]
status: active
display_name: "Smithsonian Global Volcanism Program Weekly Activity"
fetcher: ingest.fetchers.gvp_scrape
source_name: gvp_weekly
---

# Smithsonian Global Volcanism Program Weekly Activity

Smithsonian Institution's Global Volcanism Program (GVP). Weekly activity reports for the world's volcanoes. **No public API** — we HTML-scrape the weekly report page. ~50 active volcanoes per week on average.

## Metadata

| Field | Value |
|---|---|
| Source system | `gvp` |
| Base URL | https://volcano.si.edu |
| API base | https://volcano.si.edu |
| Schedule (cron) | `0 8 * * 1` (Mondays at 08:00 UTC) |
| Rate limit | 6 req/min |
| Tier | 1 |
| Axis | climate |
| License | Smithsonian GVP terms (free for non-commercial) |
| Auth | none (public HTML) |
| per_tenant_only | false |
| format | html_scrape |

## Collections

| Name | Notes |
|---|---|
| (default) | Weekly report page at https://volcano.si.edu/reports_weekly.cfm |

## Fetcher

`ingest/fetchers/gvp_scrape.py` (HTML scrape — NOT a real API)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='gvp_weekly'`. Per-volcano-week rows: `volcano_name`, `volcano_id` (GVP internal), `country`, `activity_period`, `activity_type`, `report_text`.

## Common queries

```
GET /v1/sources/gvp_weekly
GET /v1/sources/gvp_weekly/bundles?volcano=Kilauea&since=2026-01-01
```

## Gotchas

- **No API** — HTML scraping is the only option. Smithsonian could break the layout at any time.
- `html_scrape` is in tension with our [[Best Practices/Applied Practices]] rule of "no HTML scraping". This source is the **only exception** because there is no other way to get the data.
- GVP `volcano_id` is the Smithsonian internal ID; for cross-source joins, use Wikidata QID.

## Related

- [[Plan/Source Categorization]] (climate axis)
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (multi-hazard context, includes volcanoes)
- [[Ingestion/USGS Earthquake Hazards Program GeoJSON Feeds]] (companion: seismic context for eruptions)


## Migrated Context (From Global Energy Monitor (25 Open Energy Trackers).md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "Global Energy Monitor (25 Open Energy Trackers)"
fetcher: ingest.fetchers.gem
source_name: gem_global_energy_monitor
---

# Global Energy Monitor (GEM) — 25 Open Energy Trackers

Global Energy Monitor. 25 open energy trackers: coal, oil & gas, wind, solar, geothermal, bioenergy, nuclear, hydro, + coal mines, coal terminals, oil refineries, gas pipelines, LNG terminals, hydrogen plants, wind/solar/battery manufacturing, iron & steel, cement. CC-BY 4.0 (attribution required). Bi-annual CSV updates (Jan, Jul). The right primary source for current power infrastructure since [[Ingestion/WRI Global Power Plant Database v1.3.0]] was frozen in 2022. Status tracking (operating/under construction/announced/retired/mothballed/cancelled) is the layer that GPPD never had.

## Metadata

| Field | Value |
|---|---|
| Source system | `gem` |
| Base URL | https://globalenergymonitor.org |
| API base | https://api.globalenergymonitor.org |
| Schedule (cron) | `0 0 15 1,7 *` (Jan 15 + Jul 15) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | CC-BY 4.0 (attribution required) |
| Auth | none (public) |
| per_tenant_only | false |
| format | json + html_scrape_csv |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `catalog_metadata` | api.globalenergymonitor.org/catalog/metadata | GET | JSON |
| `coal_plants_csv` | globalenergymonitor.org/projects/global-coal-plant-tracker | GET | HTML scrape |
| `oil_gas_plants_csv` | globalenergymonitor.org/projects/global-oil-gas-plant-tracker | GET | HTML scrape |
| `wind_tracker_csv` | globalenergymonitor.org/projects/global-wind-power-tracker | GET | HTML scrape |
| `solar_tracker_csv` | globalenergymonitor.org/projects/global-solar-power-tracker | GET | HTML scrape |
| `hydro_tracker_csv` | globalenergymonitor.org/projects/global-hydropower-tracker | GET | HTML scrape |
| `nuclear_tracker_csv` | globalenergymonitor.org/projects/global-nuclear-power-tracker | GET | HTML scrape |
| `geothermal_tracker_csv` | globalenergymonitor.org/projects/global-geothermal-power-tracker | GET | HTML scrape |
| `bioenergy_tracker_csv` | globalenergymonitor.org/projects/global-bioenergy-power-tracker | GET | HTML scrape |

## Fetcher

`ingest/fetchers/gem.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='gem_global_energy_monitor'`. Per-facility rows with status tracking.

## Common queries

```
GET /v1/sources/gem_global_energy_monitor
GET /v1/sources/gem_global_energy_monitor/bundles?tracker=coal_plants&status=operating
GET /v1/sources/gem_global_energy_monitor/aggregates?group_by=country,tracker
```

## Gotchas

- 25 trackers, not all equally detailed. Coal plants alone have 49 fields in 10 categories; others are sparser.
- Per-facility GEM.wiki fact sheet with footnoted citations — the right source for "show me the evidence."
- HTML scraping for most trackers (similar tension to [[Ingestion/Smithsonian Global Volcanism Program Weekly Activity]]).
- Cross-references [[Ingestion/WRI Global Power Plant Database v1.3.0]] via plant-name fuzzy match + [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] via spatial join.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/WRI Global Power Plant Database v1.3.0]] (historical baseline)
- [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] (OSM power data)
- [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] (federation)
- [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]] (emissions)


## Migrated Context (From WRI Global Power Plant Database v1.3.0.md)

---
tags: [source, info_environment, climate, tier-1, osint-data, mvp, public-no-auth, refactored]
status: active
display_name: "WRI Global Power Plant Database v1.3.0"
fetcher: ingest.fetchers.wri_gppd
source_name: wri_gppd
---

# WRI Global Power Plant Database v1.3.0

WRI Global Power Plant Database (REFACTORED 2026-09-05 from WRI datasets-portal ZIP to CartoDB SQL API at wri-rw.carto.com). v1.3.0 current (June 2021). FROZEN upstream since 2022 but the WRI-Resource-Watch CartoDB mirror (table `globalpowerplantdatabasev130`) exposes the same data via SQL. Plus 2 extra years of generation data (2018, 2019) from the `powerwatch_data_20180102` table. CC-BY 4.0. 30-35K plants across 164-167 countries.

## Metadata

| Field | Value |
|---|---|
| Source system | `wri_gppd` |
| Base URL | https://wri-rw.carto.com |
| API base | https://wri-rw.carto.com/api/v2/sql |
| Schedule (cron) | `0 0 1 1 *` (yearly, January 1) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | CC-BY 4.0 |
| Auth | none (public) |
| per_tenant_only | false |
| format | cartodb_sql + zip_csv + csv + json |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `v130_zip` | datasets.wri.org/.../globalpowerplantdatabasev130.zip | GET | zip_csv (legacy) |
| `github_csv` | raw.githubusercontent.com/wri/global-power-plant-database/master/... | GET | CSV (legacy) |
| `datasette_mirror` | datasette.io/global-power-plants.json | GET | JSON (legacy) |
| (NEW) | wri-rw.carto.com/api/v2/sql?q=SELECT * FROM globalpowerplantdatabasev130 | GET | **CartoDB SQL** (refactored) |
| (NEW) | wri-rw.carto.com/api/v2/sql?q=SELECT * FROM powerwatch_data_20180102 | GET | **CartoDB SQL** (+2 years 2018-2019 generation) |

## Fetcher

`ingest/fetchers/wri_gppd.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='wri_gppd'`. Per-plant rows: `country` (3-letter ISO), `name`, `gppd_idnr` (stable join key, also Wikidata P8947), `capacity_mw`, `primary_fuel`, `latitude`, `longitude`, `commissioning_year`, `owner`, `generation_gwh_2013-2017` (+ 2018, 2019 from powerwatch).

## Common queries

```
GET /v1/sources/wri_gppd
GET /v1/sources/wri_gppd/bundles?country=USA&primary_fuel=Solar
GET /v1/sources/wri_gppd/aggregates?group_by=country,primary_fuel
```

## Gotchas

- **FROZEN upstream since 2022.** For current data, use [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]].
- **Required attribution:** "Global Energy Observatory, in Stockholm, Enipedia, World Resources Institute. 2021. Global Power Plant Database version 1.3.0."
- `gppd_idnr` is exposed as Wikidata P8947 for federation with [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] and [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]].
- **Refactored 2026-09-05** to the CartoDB SQL API for faster, more reliable queries.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] (current)
- [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] (OSM power data)
- [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] (federation layer)
- [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]] (emissions per plant)


## Migrated Context (From EAGLE-I Historical US Outage Archive (ORNL 2014-2022).md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "EAGLE-I Historical US Outage Archive (ORNL 2014-2022)"
fetcher: ingest.fetchers.eagle_i
source_name: eagle_i
---

# EAGLE-I Historical US Outage Archive (ORNL 2014-2022)

Environment for Analysis of Geo-Located Energy Information (EAGLE-I) — ORNL. 2014-2022 historical archive. CC-BY 4.0 bulk CSV on figshare. ~2M outage events. Per-utility, per-county, per-outage event. Superseded by [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] going forward, but the only source for pre-2023 per-county history.

## Metadata

| Field | Value |
|---|---|
| Source system | `eagle_i` |
| Base URL | https://figshare.com/articles/dataset/.../24237376 |
| API base | https://openenergyhub.ornl.gov/api/explore/v2.1 |
| Schedule (cron) | `0 0 1 1 *` (yearly, January 1) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | CC-BY 4.0 (attribution to ORNL required) |
| Auth | none (public) |
| per_tenant_only | false |
| format | csv |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `figshare_bulk_csv` | https://figshare.com/ndownloader/files/41264798 | bulk CSV, ~2M events |

## Fetcher

`ingest/fetchers/eagle_i.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='eagle_i'`. Per-event rows: `utility`, `state`, `county`, `customers_out`, `outage_start`, `outage_end`, `cause`.

## Common queries

```
GET /v1/sources/eagle_i
GET /v1/sources/eagle_i/bundles?state=TX&since=2020-01-01
GET /v1/sources/eagle_i/aggregates?group_by=state,year
```

## Gotchas

- **Frozen at 2022.** No new data; use [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] for current data.
- CC-BY 4.0 attribution to ORNL required in any derivative work.
- Figshare download can be slow (~5 min for 2M events).

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (current)
- [[Ingestion/DOE OE-417 Electric Emergency Incident Reports]] (major event context)


## Migrated Context (From CIVICUS Monitor Civic-Space Ratings.md)

---
tags: [source, governance, unrest, tier-1, osint-data, public-no-auth]
status: active
display_name: "CIVICUS Monitor Civic-Space Ratings"
fetcher: ingest.fetchers.civicus_monitor
source_name: civicus_monitor
---

# CIVICUS Monitor Civic-Space Ratings

CIVICUS Monitor — 5-tier civic-space rating (Open / Narrowed / Obstructed / Repressed / Closed) for 198 countries, 0-100 score, history 2018-present. CC-BY-SA 4.0. The real data publisher where Amnesty / HRW publish only press releases.

## Metadata

| Field | Value |
|---|---|
| Source system | `civicus_monitor` |
| Base URL | https://monitor.civicus.org |
| API base | https://monitor.civicus.org |
| Schedule (cron) | `0 */6 * * *` (every 6 hours) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | governance, unrest |
| License | CC-BY-SA-4.0 |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Format |
|---|---|---|
| `rss_press_updates` | https://monitor.civicus.org/feed/ | RSS |
| `country_ratings` | https://monitor.civicus.org/data/ | HTML scrape (per year 2018-current) |

## Fetcher

`ingest/fetchers/civicus_monitor.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='civicus_monitor'`. Per-country, per-year rating rows + per-update RSS rows.

## Common queries

```
GET /v1/sources/civicus_monitor
GET /v1/sources/civicus_monitor/bundles?country=RU&since=2020-01-01
GET /v1/sources/civicus_monitor/aggregates?group_by=country,rating
```

## Gotchas

- Country data is **scraped** from a per-year HTML page. The format changes; `html_scrape` is in tension with the "no HTML scraping" rule (same as [[Ingestion/Smithsonian Global Volcanism Program Weekly Activity]]).
- Rating revisions are rare but do happen; treat 0-100 score as a point-in-time measurement.
- The 5 tiers map to colors: Open (green), Narrowed (yellow), Obstructed (orange), Repressed (red), Closed (black).

## Related

- [[Plan/Source Categorization]] (governance + unrest axes)
- [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] (cross-ref sanctioned states)
- [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] (US protest history)

