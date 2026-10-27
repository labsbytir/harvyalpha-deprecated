# Climate TRACE — global emissions inventory

Key: `none required (CC-BY 4.0)`
Endpoint: `https://climatetrace.org/` (downloads page)
Auth: `none` for bulk downloads; optional API key for higher-rate live queries
Format: **CSV** (per-sector, per-country) + **GeoJSON** (per-asset)

Documentation:
- Landing: https://climatetrace.org/
- Data download portal: https://climatetrace.org/data
- API documentation: https://climatetrace.org/inventory
- Sectors covered: **power, oil & gas, waste, agriculture,
  buildings, transport, mineral extraction, fugitive emissions,
  shipping, aviation**
- License: **CC-BY 4.0** (attribution required)
- Coverage: **global**, all 195+ countries, sector-by-asset
- Refresh: **annual** (vintage-year; 2024 release in late 2025)
- Lead: **Rocky Mountain Institute** (RMI) + WattTime + 20+
  contributing orgs (NASA, ESA, Google Earth Engine, etc.)

## What it is

**Climate TRACE** (Tracking Real-time Atmospheric Carbon
Emissions) is the most comprehensive open-source global
emissions inventory as of 2026. It uses **satellite data +
remote sensing + machine learning** to estimate emissions from
**individual assets** — every power plant, every oil refinery,
every cargo ship, every cattle herd, every building — and
**releases the inventory as open data** under CC-BY 4.0.

The power sector is one of **9 sectors** covered. For each
power plant, Climate TRACE provides:

- **Annual emissions** (tonnes CO₂e) for the most recent year
  and the historical back-cast
- **Capacity factor** (utilization)
- **Emission factor** (tCO₂e per MWh)
- **Geographic location** (often sub-asset, e.g. per-unit)
- **Source attribution** (which satellite / asset / model the
  estimate is from)

The model is: **satellite observations + asset-level inventory
+ physical emission models = per-asset emissions estimates**. The
result is a per-asset CO₂e number for every power plant in the
world, updated annually.

## Why Climate TRACE is the right primary for OSINT-Data v1

WRI's GPPD is frozen 2022. GEM is bi-annual. Wikidata is
community-curated. **Climate TRACE is the only global, recent,
per-asset emissions dataset** with satellite-validated estimates.

The killer feature is **per-asset attribution**: we can take a
specific power plant (matched on `gppd_idnr` from [[wri_gppd]] or
on Wikidata QID) and ask "how much CO₂ did this plant emit in
2024?" — the answer is in Climate TRACE.

## The data shape (per the Climate TRACE download portal)

A power sector CSV row:

```csv
source_name,source_type,asset_id,asset_name,asset_type,
iso3_country,lat,lon,year,emissions_quantity,emissions_unit,
emissions_factor,capacity,capacity_unit,capacity_factor,
sector,subsector
```

Where:

- `source_name` / `source_type` — e.g. `wri_gppd` (joined to
  WRI GPPD), `gem` (joined to GEM), `wikidata` (joined to
  Wikidata), `osm` (joined to OSM)
- `asset_id` — the source's stable ID (`gppd_idnr`, GEM plant
  ID, Wikidata QID, OSM way ID)
- `asset_name` — human-readable plant name
- `asset_type` — `power_plant`, `oil_refinery`, `coal_mine`,
  `passenger_vehicle`, etc.
- `iso3_country` — ISO 3166-1 alpha-3
- `lat`, `lon` — sub-asset resolution
- `year` — vintage year
- `emissions_quantity` + `emissions_unit` — typically
  `tonnes CO₂e / year` (some sectors use kg)
- `emissions_factor` — tCO₂e per MWh (electricity) or per
  barrel (oil) etc.
- `capacity` + `capacity_unit` — typically `MW` for power
- `capacity_factor` — `0.0` to `1.0`
- `sector` + `subsector` — `power` + `electricity_generation`
  for power plants; `power` + `heat` for CHP; etc.

The full schema is documented at `https://climatetrace.org/data`.

## How to wire it up for OpenTIR-Data

1. **First ingest**: download the Climate TRACE **vintage year
   snapshot** (the most recent annual release). Per-sector CSVs
   are ~50-500 MB each depending on sector.
2. **Per-asset storage**: write to `osint.emissions_power` keyed
   by `(source_name, source_type, asset_id, year)`. Per-record
   `emissions_quantity`, `emissions_factor`, `capacity`,
   `capacity_factor`, `lat`, `lon`.
3. **Cross-reference**: for each power plant in
   [[gem_global_energy_monitor]] and [[wri_gppd]], join on
   `asset_id` to attach the emissions data.
4. **Year-over-year deltas**: the annual refresh lets us
   compute emissions deltas per plant, per country, per fuel.
   The "right" trend analysis for climate journalism.
5. **Sector rollups**: per-country, per-sector annual emissions
   for the energy dashboard's "climate" tab.

## Important caveats

| Caveat | Detail |
|---|---|
| **Annual cadence** | Climate TRACE is annual, not real-time. For real-time emissions, use WattTime's API (commercial). |
| **Some sectors are estimates, not measurements** | Climate TRACE is **modeled**, not directly measured for most assets. The satellite-based estimates have ~10-20% uncertainty. Power sector estimates are the most accurate (well-monitored stacks + known fuels). |
| **Some countries/years are sparse** | For sanctioned countries or pre-2018 years, the data is gappy. |
| **Attribution requirements** | Climate TRACE is CC-BY 4.0. Each per-asset claim in our dashboard needs to link back to the source. |
| **Per-asset vs per-country aggregations** | The "right" per-asset number is in the file; per-country aggregates are computed by summing. Don't use the per-country published aggregates for journalism — use the per-asset + sum. |
| **The download portal changes URL patterns** | Climate TRACE reorganizes their download portal occasionally. Use the Wayback Machine for old URLs. |

## What we use it for

- **Climate journalism**: "Top 10 CO₂-emitting power plants in
  2024" — answer with the per-asset data + per-country rollup.
- **Asset-level pollution stories**: "this specific plant emitted
  X tonnes of CO₂ in 2024" — per-asset attribution is the
  right level of detail.
- **Country-level trend analysis**: "China's power sector
  emissions, 2018-2024" — per-year, per-country aggregation.
- **Verification layer**: when [[gem_global_energy_monitor]]
  says a coal plant is "operating", Climate TRACE's annual
  emissions is a sanity check (an "operating" plant with
  emissions of 0 tCO₂e is suspicious).

## See also

- [[wri_gppd]] — the frozen 2022 plant-location baseline
- [[gem_global_energy_monitor]] — the bi-annual status tracker
- [[openinframap]] — the live OSM-based power infrastructure
- [[wikidata_power_plants]] — the SPARQL endpoint for
  cross-references
- [[entso_e_outages]] + [[aemo_outages]] — generation units
  in EU + Australia

## License of this connector note

`connectors/climate_trace.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From Climate TRACE — Global Per-Asset Emissions Inventory.md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "Climate TRACE — Global Per-Asset Emissions Inventory"
fetcher: ingest.fetchers.climate_trace
source_name: climate_trace
---

# Climate TRACE — Global Per-Asset Emissions Inventory

Climate TRACE (Tracking Real-time Atmospheric Carbon Emissions) — global per-asset emissions inventory. CC-BY 4.0 (attribution required). 9 sectors: power, oil & gas, waste, agriculture, buildings, transport, mineral extraction, fugitive emissions, shipping, aviation. Per-asset annual emissions (tCO₂e/yr), emission factor (tCO₂e/MWh), capacity (MW), capacity_factor (0-1). Annual vintage-year refresh; the v.2024 release landed late 2025. Lead: Rocky Mountain Institute + WattTime + 20+ contributing orgs (NASA, ESA, Google Earth Engine). The only global, recent, per-asset emissions dataset with satellite-validated estimates. Power sector estimates have ~10-20% uncertainty.

## Metadata

| Field | Value |
|---|---|
| Source system | `climate_trace` |
| Base URL | https://climatetrace.org |
| API base | https://climatetrace.org/inventory |
| Schedule (cron) | `0 0 1 11 *` (annually, Nov 1) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | CC-BY 4.0 (attribution required) |
| Auth | none (public) |
| per_tenant_only | false |
| format | csv_gz + json |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `emissions_inventory` | https://climatetrace.org/data | GET | CSV gz |
| `emissions_api` | https://climatetrace.org/inventory | GET | JSON |

## Fetcher

`ingest/fetchers/climate_trace.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='climate_trace'`. Per-asset, per-year rows.

## Common queries

```
GET /v1/sources/climate_trace
GET /v1/sources/climate_trace/bundles?sector=power&year=2024
GET /v1/sources/climate_trace/aggregates?group_by=country,sector
```

## Gotchas

- **Per-row cross-reference fields** are `source_name` (wri_gppd / gem / wikidata / osm) + `source_type` + `asset_id` — joins with [[Ingestion/WRI Global Power Plant Database v1.3.0]] + [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] + [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] + [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]].
- **~10-20% uncertainty** on power sector estimates; treat as order of magnitude, not point precision.
- Annual release in Nov/Dec; don't expect intra-year updates.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/WRI Global Power Plant Database v1.3.0]] (joined via source_name/asset_id)
- [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] (joined)
- [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] (joined)
- [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] (joined)
- [[Ingestion/U.S. EIA Open Data (Energy Information Administration)]] (US emissions context)

