# WRI Global Power Plant Database (FROZEN 2022)

Key: `none required (CC-BY 4.0)`
Endpoint: `https://datasets.wri.org/datasets/global-power-plant-database`
Auth: `none`
Format: **CSV** (one row per plant) + **GeoJSON** + **shapefile** + **SQLite** (third-party mirror)

Documentation:
- WRI dataset page: https://datasets.wri.org/datasets/global-power-plant-database
- GitHub (canonical source): https://github.com/wri/global-power-plant-database
- Resource Watch layer (live API):
  - `https://api.resourcewatch.org/v1/dataset/a86d906d-9862-4783-9e30-cdb68cd808b8/layer/2a694289-fec9-4bfe-a6d2-56c3864ec349`
- Datasette instance: https://datasette.io/global-power-plants (11.1 MB SQLite)
- Third-party mirror: https://data.clawrxiv.org/sources/global-power-plant-database
- Bulk downloads:
  - v1.1.0 (deprecated, June 2018): `https://datasets.wri.org/private-admin/dataset/53623dfd-3df6-4f15-a091-67457cdb571f/resource/26669133-9493-4f38-a32f-ce35d5ea6ab9/download/globalpowerplantdatabasev110.zip`
  - v1.2.0 (deprecated, June 2019): same path, `9a7587a6-964e-4bfc-8c09-0ba1f611f18b` resource id
  - v1.3.0 (current, June 2021): same path, `66bcdacc-3d0e-46ad-9271-a5a76b1853d2` resource id, 4.18 MB
- License: **CC-BY 4.0** (attribution required: "Global Energy Observatory, Google, KTH Royal Institute of Technology in Stockholm, Enipedia, World Resources Institute. 2021. Global Power Plant Database version 1.3.0.")
- Coverage: **~30,000-35,000 power plants, 164-167 countries** (depending on version)
- Status: **FROZEN — no updates since 2022.** The GitHub README says: "This project is not currently maintained by WRI. There are no planned updates as of this time (early 2022)."

## What it is

The **Global Power Plant Database** (GPPD) is the most-cited
**historical reference** for global power plant infrastructure.
Compiled by WRI + Google Earth Outreach + KTH Royal Institute of
Technology + Enipedia, it centralizes power plant data from
**600+ open sources** into one downloadable CSV.

**Critical caveat**: the dataset has been **frozen since 2022**.
For any use case that needs current data (post-2022), use one of:

- **[[gem_global_energy_monitor]]** — the 25 active trackers, bi-annual
  updates, CC-BY 4.0
- **[[openinframap]]** — live OSM-based, with power lines + plants
  + telecoms
- **[[wikidata_power_plants]]** — SPARQL endpoint for all Wikidata
  power plant items
- **EIA Form 860** (US only) — annual update, public domain
- **[[entso_e_outages]]** + **[[aemo_outages]]** — for generation
  units in EU + Australia

The WRI GPPD is still the right starting point for **historical
baselines** (2013-2017 generation data, 2018-2021 plant
locations). For current data, layer it on top of the live sources.

## The data shape

Per-plant fields (per the v1.3.0 README):

- `country` (3-letter ISO code, e.g. `USA`, `CHN`, `DEU`)
- `country_long` (full name)
- `name` (plant name)
- `gppd_idnr` (stable GPPD identifier, 6-character alphanumeric)
- `capacity_mw` (installed capacity, MW)
- `latitude`, `longitude` (WGS84)
- `primary_fuel` (`Coal`, `Gas`, `Hydro`, `Nuclear`, `Oil`, `Solar`,
  `Wind`, `Geothermal`, `Biomass`, `Waste`, `Other`)
- `other_fuel1`, `other_fuel2`, `other_fuel3` (additional fuels)
- `commissioning_year` (year of first operation)
- `owner` (parent company or operator)
- `source` (data source — e.g. `GEO`, `CARMA`, `EIA`, `ENTSO-E`,
  `GEM`, etc.)
- `url` (source URL for the record)
- `geolocation_source` (how the lat/lon was determined)
- `wri_dataset` (always `v1.3.0`)
- Generation by year, 2013-2017:
  `generation_gwh_2013`, `generation_gwh_2014`, `generation_gwh_2015`,
  `generation_gwh_2016`, `generation_gwh_2017`
- Estimated generation (from `gppd-ai4earth-api`, an ML model):
  `estimated_generation_gwh_2013` through `_2017`
- `year_of_capacity_data` (when the capacity was last verified)
- `generation_data_source`

## How to wire it up for OpenTIR-Data

1. **First ingest**: download v1.3.0 ZIP (4.18 MB) from
   `https://datasets.wri.org/.../resource/66bcdacc-3d0e-46ad-9271-a5a76b1853d2/download/globalpowerplantdatabasev130.zip`.
   One-time load.
2. **Per-plant storage**: write to `osint.power_plants` keyed by
   `gppd_idnr`. Per-record `country`, `name`, `capacity_mw`,
   `primary_fuel`, `latitude`, `longitude`, `owner`.
3. **Geo-enrichment**: H3 cell + ISO 3166 country + GADM
   administrative region per plant.
4. **Cross-reference with [[gem_global_energy_monitor]]**: GEM's
   coal + gas + hydro + wind + solar trackers have newer
   status data (operating / under construction / announced /
   retired). Join on `country` + plant-name fuzzy match.
5. **Cross-reference with [[wikidata_power_plants]]**:
   SPARQL `SELECT ?plant ?plantLabel ?country ?capacity WHERE
   { ?plant wdt:P31 wd:Q159719 . ?plant wdt:P17 ?country .
   ?plant wdt:P210 ?capacity }` — get the full Wikidata view
   for plants we have a `gppd_idnr` for.
6. **Cross-reference with OSM**: Overpass query
   `power=plant` in the same bounding box — see
   [[openinframap]] for the pattern.

## Important caveats

| Caveat | Detail |
|---|---|
| **Frozen since 2022** | The GPPD is a historical baseline, not a current feed. New plants, retirements, and ownership changes are not reflected. |
| **30-50 MW threshold, varies by country** | The dataset is "comprehensive" for plants ≥ 50 MW in some countries, ≥ 30 MW in others. Many small-scale solar / diesel are missing. |
| **Capacity ≠ generation** | Plants often run below nameplate capacity. The dataset has capacity (MW) and historical generation (GWh/year for 2013-2017). |
| **Country codes are 3-letter ISO, but old format** | Some early rows use `ROM` instead of `ROU` (Romania), `ZAR` instead of `COD`. Post-process. |
| **Per-fuel aggregation, not unit-level** | A coal plant with 4 units shows as one row with `capacity_mw` summed. For unit-level (matters for generation forecasting), use GEM or EIA-860 instead. |
| **Generation data is 2013-2017** | Beyond 2017, only estimated generation is available (from the `gppd-ai4earth-api` ML model). For post-2017 actuals, use [[gem_global_energy_monitor]] + [[entso_e_outages]] + [[aemo_outages]]. |
| **The Resource Watch layer is gated** | The `api.resourcewatch.org` endpoint is now part of WRI's migrated infrastructure. The GitHub CSV is the canonical source. |

## What we use it for

- **Historical baseline (2013-2017)**: per-country, per-fuel
  installed capacity and generation. The right baseline for
  trend analysis ("how has the global solar fleet grown since
  2013?").
- **Cross-source reconciliation**: the GPPD's `gppd_idnr` is a
  stable identifier we can use to join against [[gem_global_energy_monitor]]
  + [[wikidata_power_plants]] + [[openinframap]].
- **Country-level rollups**: per-country installed capacity by
  fuel, per-country generation by fuel — feeds the energy
  dashboard's Map view.
- **Theft / loss analytics**: cross-reference GPPD with ODIN
  outage data to identify high-loss power plants
  (theft-prone regions in South Asia, Latin America, etc.).

## See also

- [[gem_global_energy_monitor]] — the live, bi-annual tracker
  (CC-BY 4.0)
- [[openinframap]] — the live OSM-based power infrastructure
  (ODbL)
- [[wikidata_power_plants]] — the SPARQL endpoint for all
  Wikidata power plant items (CC0)
- [[entso_e_outages]] + [[aemo_outages]] — generation units in
  EU + Australia
- [[odin]] — for joining with US power outage data

## License of this connector note

`connectors/wri_gppd.md` is dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

