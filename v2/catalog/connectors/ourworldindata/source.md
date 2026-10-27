# Our World in Data (OWID)

Key: `none required` — data is CC-BY-4.0, the ETL codebase is read-only (no longer MIT).

> ⚠️ **License change (2024+):** the `owid/owid-grapher` visualization platform repo is **no longer MIT-licensed** — you may read and study it but cannot copy, modify, or distribute it without written permission. **Do not fork `owid-grapher`.** The DATA is still CC-BY-4.0, and the ETL pipeline code (`owid/etl`) is still openly readable. Build your own visualization layer with the open alternatives (Apache ECharts, MapLibre, deck.gl, Plotly).

Endpoint (chart data): `https://ourworldindata.org/grapher/{slug}?v=N&csvType=full&useColumnShortNames=false`
Endpoint (CSV via /explorers/): `https://ourworldindata.org/explorers/{slug}.csv?facet=none&country=...`
Endpoint (Algolia search): `https://ourworldindata.org/search?q=`
Endpoint (admin API, behind auth): `https://owid.cloud/admin/api/charts.json`
Auth: none (read)
Format: `CSV`, `JSON` (Algolia), HTML

Documentation:
- Site: https://ourworldindata.org/
- Search: https://ourworldindata.org/search
- GitHub org: https://github.com/owid
- ETL repo: https://github.com/owid/etl (★ — the canonical reference for 200+ source connectors)
- ETL docs: https://docs.owid.io/projects/etl/
- `owid-catalog` PyPI: https://pypi.org/project/owid-catalog/ (`pip install owid-catalog`)
- `owid-grapher-py` PyPI: https://pypi.org/project/owid-grapher-py/ (build OWID-style charts in Jupyter)
- Data API: https://github.com/owid/data-api
- Walden catalog: https://github.com/owid/walden
- License note: https://github.com/owid/owid-grapher#-licence

## The OWID org: 53 repos

The most relevant for OpenTIR-Data connector work:

| Repo | What it is | Useful for us? |
|---|---|---|
| `owid/etl` ★ | Compute graph + 200+ source-specific snapshot folders | **YES — this is the reference catalog** |
| `owid/data-api` | Experimental REST API for the catalog (DuckDB-backed, supports SQL) | YES — could replace our catalog access |
| `owid/owid-catalog` | `pip install owid-catalog` — Python client for the data catalog | YES — the recommended entry point |
| `owid/owid-grapher-py` | Python lib to make OWID-style charts in Jupyter | YES — for our dashboard layer |
| `owid/owid-mcp` (in `etl/owid_mcp/`) | MCP server exposing OWID to AI agents | YES — see below |
| `owid/owid-grapher` ★ | The visualization platform | **NO — license no longer permits fork** |
| `owid/walden` | "Prototype catalog of data sources that OWID's datasets are built from" | YES — meta-catalog |
| `owid/co2-data` ★ | CO2 emissions CSV (CC-BY) | YES — direct CSV |
| `owid/energy-data` ★ | Energy CSV (CC-BY) | YES — direct CSV |
| `owid/covid-19-data` ★ | COVID-19 CSV (CC-BY) | YES — direct CSV |
| `owid/poverty-data` | Poverty CSV (CC-BY) | YES — direct CSV |
| `owid/owid-datasets` ★ | Legacy dataset collection | YES — backup for chart data |

## The gold mine: `etl/snapshots/`

The `owid/etl` repo has a `snapshots/` directory with **200+ source-specific folders**, each containing the working Python code for pulling data from that source. This is the canonical reference catalog for building connectors — every major open data source we identified is here:

```text
snapshots/fbi/                  FBI CDE (matches our [[connectors/api.data.gov]])
snapshots/covid/                COVID-19 data
snapshots/eia/                  US Energy Information Administration
snapshots/eurostat/             EU statistics
snapshots/fao/                  UN Food and Agriculture
snapshots/who/                  WHO (matches our [[connectors/who-gho]])
snapshots/worldbank_wdi/        World Bank World Development Indicators
snapshots/worldbank_icp/        World Bank International Comparison Program
snapshots/imf/                  IMF (matches our [[connectors/imf-datamapper]])
snapshots/nasa/                 NASA (matches our [[connectors/nasa-earthdata]])
snapshots/noaa_ncei/            NOAA NCEI (matches our [[connectors/noaa-ncei]])
snapshots/iea/                  IEA (paid, matches our [[connectors/no-public-api]])
snapshots/iea_co2/              IEA CO2 emissions
snapshots/oecd/                 OECD
snapshots/un/                   UN overall
snapshots/unodc/                UNODC (matches our [[connectors/unodc-dataportal]])
snapshots/unece/                UNECE
snapshots/unep/                 UNEP
snapshots/unesco/               UNESCO
snapshots/unicef/               UNICEF (matches our [[connectors/no-public-api]])
snapshots/unctad/               UNCTAD
snapshots/wb/                   World Bank
snapshots/media_cloud/          MediaCloud (matches our [[connectors/mediacloud]])
snapshots/pew/                  Pew Research
snapshots/ihme/                 IHME health
snapshots/ihme_gbd/             IHME Global Burden of Disease
snapshots/ihme_lifetable/       IHME life tables
snapshots/cancer/               Cancer registries
snapshots/cedlas/               CEDLAS inequality
snapshots/owid/                 OWID-derived datasets
snapshots/emdat/                EM-DAT international disasters
snapshots/gallup/                Gallup World Poll
snapshots/gapminder/            Gapminder
snapshots/harvard/              Harvard dataverse
snapshots/ggdc/                 Groningen Growth and Development Centre
snapshots/gfs/                  Global Financial Statistics
snapshots/happiness/            World Happiness Report
snapshots/health_expenditure/   WHO health expenditure
snapshots/hmd/                  Human Mortality Database
snapshots/homicide/             Homicide data
snapshots/housing/              Housing data
snapshots/human_rights/         Human rights indices
snapshots/idmc/                 Internal Displacement Monitoring Centre
snapshots/irena/                IRENA renewable energy
snapshots/labor/                Labor statistics
snapshots/light/                Our World in Data energy access
snapshots/lis/                  Luxembourg Income Study
snapshots/migration/            Migration data
snapshots/neglected_tropical_diseases/  NTD data
snapshots/news/                 News media
snapshots/oecd/                 OECD
snapshots/ophi/                 Oxford Poverty and Human Development Initiative
snapshots/plastic_pollution/    Plastic pollution
snapshots/poverty_inequality/   Poverty and inequality
snapshots/project_tycho/        Project Tycho (disease surveillance)
snapshots/research_development/ R&D
snapshots/sdgs/                 UN SDGs
snapshots/shift/                Shift project (energy)
snapshots/sipri/                SIPRI (arms transfers, military expenditure)
snapshots/smoking/              Smoking prevalence
snapshots/social_expenditure/   Social expenditure
snapshots/statins/              Statins data
snapshots/statistics_canada/    Statistics Canada
snapshots/survey/               Survey data
snapshots/tax/                  Tax data
snapshots/technology/           Tech adoption
snapshots/terrorism/            Terrorism data
snapshots/tourism/              Tourism
snapshots/trade/                Trade data
snapshots/transport/            Transport
snapshots/uk_beis/              UK Department for Business, Energy & Industrial Strategy
snapshots/uk_desnz/             UK Department for Energy Security and Net Zero
snapshots/un_peacekeeping/      UN Peacekeeping
snapshots/unu_wider/            UNU-WIDER
snapshots/urbanization/         UN-Habitat urbanization
snapshots/us_census_bureau/     US Census Bureau
snapshots/usda_ers/             USDA Economic Research Service
snapshots/usda_fs/              USDA Forest Service
snapshots/usda_nass/            USDA National Agricultural Statistics Service
snapshots/usgs/                 US Geological Survey
snapshots/vcp/                  VCP (Voter Characteristics Project)
snapshots/violence/             Violence data
snapshots/war/                  War data
snapshots/wash/                 WHO/UNICEF water and sanitation
snapshots/wid/                  World Inequality Database
snapshots/working_hours/        Working hours
snapshots/worldbank_icp/        World Bank ICP
snapshots/worldbank_wdi/        World Bank WDI
snapshots/wpf/                  World Pension Foundation
snapshots/wri/                  World Resources Institute
snapshots/wvs/                  World Values Survey
snapshots/ai/                   AI data
snapshots/abs/                  Australian Bureau of Statistics
snapshots/animal_welfare/       Animal welfare
snapshots/antibiotics/          Antibiotic use
snapshots/archaeology/          Archaeology
snapshots/atmosphere/           Atmospheric composition
snapshots/atus/                 American Time Use Survey
snapshots/aviation/             Aviation
snapshots/bank_of_england/      Bank of England
snapshots/bgs/                  British Geological Survey
snapshots/biotech/              Biotech
snapshots/cbc_taiwan/           Taiwan CBC
snapshots/cbpp/                 Center on Budget and Policy Priorities
snapshots/ccia/                 Climate Change in Africa
snapshots/cdiac/                Carbon Dioxide Information Analysis Center
snapshots/cedlas/               Centro de Estudios Distributivos, Laborales y Sociales
snapshots/clio_infra/           Clio Infra (economic history)
snapshots/core_econ/            CORE Econ
snapshots/democracy/            V-Dem, Freedom House, Polity
snapshots/education/            Education data
snapshots/ember/                Ember energy think tank
snapshots/excess_mortality/     Excess mortality (COVID, etc.)
snapshots/fasttrack/            Fast Track
snapshots/fda/                   FDA data
snapshots/fisheries/             Fisheries
snapshots/food/                 Food data
snapshots/forest_research/      Forest research
snapshots/forests/              Forest data
snapshots/gavi/                 Gavi vaccine alliance
snapshots/gcp/                  Global Carbon Project
snapshots/geography/            Geographic data
snapshots/hyde/                 HYDE historical population
snapshots/iea_co2/              IEA CO2 emissions (sister to iea/)
snapshots/ifr/                  International Federation of Robotics
snapshots/igh/                  Income and wealth inequality
snapshots/iija/                 Inequality data
snapshots/ilostat/              ILO labor statistics
snapshots/imbie/                 IMBIE energy data
snapshots/imf/                  IMF (matches our [[connectors/imf-datamapper]])
snapshots/insee/                France INSEE
snapshots/itopf/                International Tanker Owners Pollution Federation
snapshots/iucn/                 IUCN Red List
snapshots/ivs/                  Integrated Values Survey
snapshots/iwc/                  International Whaling Commission
snapshots/journalism/           Journalism data
snapshots/lazard/               Lazard (cost of energy)
snapshots/lgbt_rights/          LGBT rights
snapshots/lund_university/      Lund University
snapshots/macrosecurity/        Macrosecurity
snapshots/met_office_hadley_centre/  UK Met Office Hadley Centre
snapshots/military_expenditure/ Military expenditure (matches sipri)
snapshots/moatsos/              Moatsos
snapshots/ophi/                 OPHI Multidimensional Poverty Index
snapshots/pew/                  Pew Research
snapshots/papers/                Academic papers
snapshots/plastic_waste/        Plastic waste
snapshots/postnatal_care/       Postnatal care
snapshots/poverty_inequality/   Poverty and inequality
snapshots/pwt/                  Penn World Table
snapshots/rff/                  RFF (Resources for the Future)
snapshots/shift/                Shift project
snapshots/sipri/                SIPRI
snapshots/smoking/              Smoking
snapshots/social_expenditure/   Social expenditure
snapshots/space/                 Space data
snapshots/state_capacity/       State capacity (V-Dem, etc.)
snapshots/statfin/              Statistics Finland
snapshots/statins/              Statins
snapshots/statistics_canada/    Statistics Canada
snapshots/survey/                Survey data
snapshots/tax/                   Tax
snapshots/technology/            Technology adoption
snapshots/terrorism/             Terrorism (GTD)
snapshots/tourism/               Tourism
snapshots/trade/                 Trade
snapshots/transport/             Transport
snapshots/tsmc/                  TSMC data
snapshots/tuberculosis/          TB
snapshots/uk_beis/               UK BEIS
snapshots/uk_desnz/              UK DESNZ
snapshots/un_peacekeeping/       UN Peacekeeping
snapshots/unctad/                UNCTAD
snapshots/unece/                 UNECE
snapshots/unep/                  UNEP
snapshots/unesco/                UNESCO
snapshots/unicef/                UNICEF
snapshots/unodc/                 UNODC
snapshots/unu_wider/             UNU-WIDER
snapshots/urbanization/          UN-Habitat
snapshots/us_census_bureau/      US Census
snapshots/usda_ers/              USDA ERS
snapshots/usda_fs/               USDA Forest Service
snapshots/usda_nass/             USDA NASS
snapshots/usgs/                  US Geological Survey
snapshots/vcp/                   Voter Characteristics Project
snapshots/violence/              Violence
snapshots/war/                   War
snapshots/wash/                  WASH (water/sanitation/hygiene)
snapshots/washu/                 WASH Urban
snapshots/waste/                 Waste
snapshots/wb/                    World Bank
snapshots/wdi/                   World Development Indicators
snapshots/who/                    WHO
snapshots/wid/                   WID (World Inequality Database)
snapshots/working_hours/         Working hours
snapshots/worldbank_icp/         WB ICP
snapshots/worldbank_wdi/         WB WDI
snapshots/wpf/                   World Pension Foundation
snapshots/wri/                   World Resources Institute
snapshots/wvs/                   World Values Survey
```

The full list is in `https://github.com/owid/etl/tree/master/snapshots`. For OpenTIR-Data, the most valuable to add next (and the most distinctive from what we already have):

- **eia** (US Energy Information Administration) — free, ~600k series
- **eurostat** (EU statistics) — free, ~5000 datasets
- **fao** (UN food/agriculture) — free, FAOSTAT
- **oecd** (OECD) — free for most series
- **sipri** (arms transfers) — high OSINT value
- **gallup** (World Poll) — public microdata
- **emdat** (international disasters) — public
- **us_census_bureau**, **usda_ers**, **usda_nass** — US-specific
- **ihme_gbd** (Global Burden of Disease) — high value
- **wvs** (World Values Survey) — public microdata
- **ophi** (Multidimensional Poverty Index) — public

## How it's used in OpenTIR-Data (3 layers)

### Layer 1: Direct CSV (the simplest path)

```bash
# Chart data CSV
curl -sL "https://ourworldindata.org/grapher/life-expectancy?v=1&csvType=full&useColumnShortNames=false" \
  | head -3
# → Day,Entity,Code,Year,Life expectancy at birth (historical)
# → 2023-01-01,Afghanistan,AFG,1950,27.7
```

### Layer 2: `owid-catalog` Python library

```python
# pip install owid-catalog
from owid.catalog import fetch, search

# Fetch a chart
tb = fetch("life-expectancy")

# Semantic search
results = search("renewable energy", kind="indicator")
for r in results[:5]:
    print(r.title, r.uri)
```

### Layer 3: OWID's experimental data API (DuckDB-backed, supports SQL)

The `owid/data-api` repo is a thin REST + DuckDB wrapper over the same catalog. Sample queries:

```bash
# Health check
curl -sL https://ourworldindata.org/data-api/health

# Single variable time series
curl -sL https://ourworldindata.org/data-api/v1/variableById/data/42539

# Full dataset CSV
curl -sL https://ourworldindata.org/data-api/v1/dataset/data/garden/owid/latest/covid/covid.csv

# Arbitrary SQL via DuckDB
curl -sL -X POST https://ourworldindata.org/data-api/v1/sql \
  -H "Content-Type: application/json" \
  -d '{"sql":"SELECT * FROM garden__owid__latest__covid__covid LIMIT 5", "type":"csv"}'
```

⚠️ This API is marked `experimental` in the README and may change. Use the CSV download path as the production fallback.

### Layer 4: OWID MCP server (for AI agents)

OWID publishes an MCP server at `owid/etl/owid_mcp/`:

```python
# The MCP server exposes these tools to AI agents:
#   search_indicator(query, limit?)        — find indicators by name
#   run_sql(query, max_rows?)              — read-only SQL on the public Datasette
#   fetch_post(identifier, include_metadata?)  — markdown content of an OWID article
#   search_posts(query, limit?)            — search articles

# And these resources:
#   ind://{indicator_id}                   — all entities for one indicator
#   ind://{indicator_id}/{entity}          — one country/region slice
```

This is the cleanest way to expose OWID to AI agents. The OpenTIR-Data platform should consider running its own MCP server with the same interface for our own catalog.

## Quick call — verify

```bash
# Direct chart CSV
curl -sL "https://ourworldindata.org/grapher/life-expectancy?v=1&csvType=full&useColumnShortNames=false" \
  | head -1

# Algolia search (returns JSON)
curl -sL "https://ourworldindata.org/search?q=climate" | head -c 200

# owid-catalog from PyPI
pip install owid-catalog
python3 -c "from owid.catalog import fetch; print(fetch('life-expectancy').head())"
```

## Notes for OpenTIR-Data

- OWID indexes **3,000+ indicators** across 200+ topics. It's the highest-quality "data already cleaned" source in the OSINT world.
- The `owid/etl/snapshots/` directory is the **canonical reference catalog** for 200+ source-specific data connectors. When building a new connector for OpenTIR-Data, **read the corresponding `snapshots/{source}/` directory first** — it has the working Python code for that source, including edge cases and historical quirks.
- The `owid-catalog` Python library is the recommended entry point. It handles versioned snapshots, channel selection (garden/meadow/backport), and metadata.
- The `data-api` repo (DuckDB-backed) is the canonical data API. If/when it goes GA, it's a direct replacement for the per-chart CSV downloads.
- The `owid/owid-mcp` (in `etl/owid_mcp/`) is the **MCP server pattern** — building one for OpenTIR-Data's own catalog would let AI agents query our data without writing fetchers.
- **License caveat**: the data is CC-BY-4.0 with attribution required. Always cite "Our World in Data" and link to the original chart.
- **Cross-source dedup**: OWID's life-expectancy CSV is the same as World Bank's `SP.DYN.LE00.IN` and WHO GHO's `WHOSIS_000001`. The `dataset_fingerprint` resolver will merge all three into one logical dataset.


## Migrated Context (From WMO World Weather Information Service (WWIS) JSON API.md)

---
tags: [source, climate, tier-1, osint-data, public-no-auth, wmo, africa, global]
status: proposed
display_name: "WMO World Weather Information Service (WWIS) JSON API"
source_name: wmo_wwis
---

# WMO World Weather Information Service (WWIS) JSON API

Official city forecasts and climatological normals contributed by WMO member national meteorological and hydrological services. **No authentication.** Has African cities (Algeria, Egypt, Morocco, South Africa, Kenya, Nigeria, Ethiopia, etc.). Easiest free win on the list.

## Metadata

| Field | Value |
|---|---|
| Source system | `wmo_wwis` |
| Base URL | `https://worldweather.wmo.int` |
| API base | `https://worldweather.wmo.int/en/json/` |
| Auth | **none** (public) |
| Tier | 1 |
| Axis | climate |
| License | Public (per WMO terms: must acknowledge WMO WWIS as source) |
| per_tenant_only | false |
| Coverage type | global |
| License note | "Acknowledgement must be given to the WMO World Weather Information Service (https://worldweather.wmo.int) as the source of information. The forecast and climatological information of the WWIS website must be reproduced accurately." |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `city_forecasts` | city id | Per-city 5-day forecast: temp, wind, humidity, precipitation |
| `city_climatology` | city id | Monthly climatological normals |
| `city_list` | n/a | Full city list with IDs (for enumeration) |

## Endpoints

```
# City forecast
GET https://worldweather.wmo.int/en/json/{city_id}_en.json

# Climatology
GET https://worldweather.wmo.int/en/json/{city_id}_climat_en.json

# Full city list (enumeration)
GET https://worldweather.wmo.int/en/json/full_city_list.txt
```

Example: Singapore = `https://worldweather.wmo.int/en/json/234_en.json`, New York = `.../278_en.json`.

## Fetcher

Not yet implemented. Pattern: pull `full_city_list.txt` once, then poll each city on a daily cycle (forecasts are typically updated twice daily per NMHS).

## Storage

Likely ClickHouse `osint.bundles` with `source_name='wmo_wwis'`, per-city per-day rows. Fields: `city_id`, `city_name`, `country`, `forecast_time`, `temp_max`, `temp_min`, `wind_speed`, `wind_dir`, `humidity`, `precipitation_mm`.

## Common queries

```
GET /v1/sources/wmo_wwis
GET /v1/sources/wmo_wwis/bundles?country=KE&since=2026-09-01
```

## Gotchas

- City IDs are stable but not sequential — always resolve from `full_city_list.txt` rather than hardcoding.
- The English-suffix URL (`_en.json`) returns English; other languages exist. Stick to English for consistency.
- Forecasts are issued by the *national* service of each country, so quality and update cadence varies. The "max 5-day" horizon is a hard limit imposed by most NMHSs.
- The data is public but WMO requests attribution. Include "Source: WMO World Weather Information Service (worldweather.wmo.int)" in any UI that shows the data.

## Why I picked this first

- **Zero auth.** No registration, no key, no contact, no commercial agreement.
- **WMO is the canonical authority.** Same data the national services publish, just normalized.
- **Africa coverage is real.** ~150+ African cities available as IDs.
- **Stable format.** Has been at this URL since the 2000s.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[WMO WIS2 Global Broker (MQTT) — Real-Time Weather Push]] — the push-mode sibling
- [[WMO OSCAR/Surface — Station Metadata REST API]] — for cross-referencing stations


## Migrated Context (From World Bank FinancesOne (FONE).md)

---
tags: [source, economic, governance, tier-1, osint-data]
status: active
display_name: "World Bank FinancesOne (FONE)"
fetcher: ingest.fetchers.fone
source_name: financesone
---

# World Bank FinancesOne (FONE)

World Bank project finances — 547+ assets, 290k+ rows of project-level data (commitments, disbursements, repayments, status). The right primary source for tracking where World Bank money is going.

## Metadata

| Field | Value |
|---|---|
| Source system | `fone` |
| Base URL | https://financesone.worldbank.org |
| API base | https://datacatalogapi.worldbank.org/dexapps/fone |
| Schedule (cron) | `0 4 * * *` (daily at 04:00 UTC) |
| Rate limit | 60 req/min |
| Tier | 1 |
| Axis | economic, governance |
| License | CC-BY-3.0-IGO |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Asset type | Notes |
|---|---|---|
| `fone_datasets` | `dataset` | 547+ base datasets |
| `fone_views` | `view` | derived/pre-aggregated views |
| `fone_visualizations` | `visualization` | chart configs |

## Fetcher

`ingest/fetchers/fone.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='financesone'`. Per-asset rows.

## Common queries

```
GET /v1/sources/financesone
GET /v1/sources/financesone/bundles?country=KE&since=2020-01-01
GET /v1/sources/financesone/aggregates?group_by=country,sector
```

## Gotchas

- Asset_type filter is required; passing no filter returns datasets only.
- API key in the URL is not required for the public catalog but is for write/admin operations.

## Related

- [[Plan/Source Categorization]] (economic + governance axes)
- [[Ingestion/Energydata.info (CKAN)]] (same operator: WBG)
- [[Ingestion/World Bank Microdata Catalog (RTDI)]] (same operator: WBG)


## Migrated Context (From World Bank Microdata Catalog (RTDI).md)

---
tags: [source, economic, governance, tier-1, osint-data]
status: active
display_name: "World Bank Microdata Catalog (RTDI)"
fetcher: ingest.fetchers.nada
source_name: microdata_rtdi
---

# World Bank Microdata Catalog (RTDI)

World Bank microdata — Research Theme Dataset Inventory. 109 studies, mostly household surveys, labor force surveys, demographic & health surveys (DHS), living standards measurement studies (LSMS). Pairs with [[Ingestion/World Bank Microdata Catalog (FCV)]] for the fragile/conflict subset.

## Metadata

| Field | Value |
|---|---|
| Source system | `nada` |
| Base URL | https://microdata.worldbank.org |
| API base | https://microdata.worldbank.org/index.php/api |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | economic, governance |
| License | Mixed (per-study) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `rtdi` | NADA catalog with `collection_param=rtdi` | 109 studies, page_size=50 |

## Fetcher

`ingest/fetchers/nada.py` (shared with [[Ingestion/World Bank Microdata Catalog (FCV)]])

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='microdata_rtdi'`. Per-study metadata rows; no per-row data (just study URLs + citation info).

## Common queries

```
GET /v1/sources/microdata_rtdi
GET /v1/sources/microdata_rtdi/bundles?country=NG
```

## Gotchas

- NADA catalog is metadata only — actual microdata requires per-study application/approval.
- License varies per study; CC-BY-4.0 most common, but some require separate data use agreements.

## Related

- [[Plan/Source Categorization]]
- [[Ingestion/World Bank FinancesOne (FONE)]] (same operator: WBG)
- [[Ingestion/World Bank Microdata Catalog (FCV)]] (FCV subset)


## Migrated Context (From World Bank Microdata Catalog (FCV).md)

---
tags: [source, economic, governance, conflict, tier-1, osint-data]
status: active
display_name: "World Bank Microdata Catalog (FCV)"
fetcher: ingest.fetchers.nada
source_name: microdata_fcv
---

# World Bank Microdata Catalog (FCV)

World Bank microdata — Fragile & Conflict-Affected countries subset. 1,503 studies covering countries in active conflict or post-conflict reconstruction. The right primary source for survey data when ACLED/GDELT say "something is happening here" and you need ground-truth on the affected population.

## Metadata

| Field | Value |
|---|---|
| Source system | `nada` |
| Base URL | https://microdata.worldbank.org |
| API base | https://microdata.worldbank.org/index.php/api |
| Schedule (cron) | `30 5 * * *` (daily at 05:30 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | economic, governance, conflict |
| License | Mixed (per-study) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `fcv` | NADA catalog with `collection_param=fcv` | 1,503 studies, page_size=50 |

## Fetcher

`ingest/fetchers/nada.py` (shared with [[Ingestion/World Bank Microdata Catalog (RTDI)]])

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='microdata_fcv'`. Per-study metadata rows.

## Common queries

```
GET /v1/sources/microdata_fcv
GET /v1/sources/microdata_fcv/bundles?country=YE
```

## Gotchas

- Same metadata-only constraint as RTDI — actual data requires per-study approval.
- Country list shifts as countries enter/exit FCV status; the catalog itself is the source of truth.

## Related

- [[Plan/Source Categorization]] (economic + governance + conflict axes)
- [[Ingestion/World Bank Microdata Catalog (RTDI)]] (general counterpart)
- [[Ingestion/ACLED — Armed Conflict Location & Event Data Project]] (the event-level conflict data)

