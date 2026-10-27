# AEMO NEMWeb — Australian Energy Market Operator

Key: `none required for NEMWeb bulk download (anonymous); per-tenant for the NEM Data Dashboard JSON API`
Endpoint (bulk): `http://nemweb.com.au/Reports/CURRENT/` (live) + `http://nemweb.com.au/Reports/Archive/` (historical)
Endpoint (API): `https://aemo.com.au/aemo/data/...` (dashboard backend)
Auth: `none` for bulk; API requires AEMO portal account
Format: **CSV** (per IS_0XX / DISPATCH_0XX naming) for bulk; **JSON** for the dashboard API

Documentation:
- NEMWeb main page: http://nemweb.com.au
- Current reports (live): http://nemweb.com.au/Reports/CURRENT/
- Archive reports (historical): http://nemweb.com.au/Reports/Archive/
- Data Model (MMSDM): https://www.aemo.com.au/energy-systems/electricity/national-electricity-market-nem/data-nem/market-management-system-data-model
- Developer API: https://dev.aemo.com.au/api-docs
- Open Electricity Platform (3rd-party): https://platform.openelectricity.org.au/
- apis.io: https://apis.io/providers/aemo/
- License: **free public use** for the bulk NEMWeb data
- Coverage: **National Electricity Market (NEM)** — Queensland,
  New South Wales, Victoria, South Australia, Tasmania. The
  Wholesale Electricity Market (WEM, Western Australia) is
  separate, also by AEMO.
- Refresh: **5-minute dispatch intervals** for live data; daily
  for settlements

## What it is

**AEMO** (Australian Energy Market Operator) operates the
National Electricity Market (NEM), one of the world's longest
interconnected power systems (stretching from Queensland to
Tasmania). Their **NEMWeb** service publishes a continuous stream
of CSVs to a public file server, with no auth, no rate limit, and
no fees.

For OSINT-Data v1, the key table is **`NETWORK_OUTAGEDETAIL`** —
the same name as the ENTSO-E outage table, but for Australia.
Every planned and forced outage on NEM transmission and
distribution network elements is published here.

## Critical distinction: this is transmission, not customer-level

Like ENTSO-E, NEMWeb's outage data is **transmission and
generation level** — a coal unit tripping, a 500 kV line being
taken out for maintenance, a wind farm curtailment event. It is
**not** "X customers are without power" — that's not aggregated
at the NEM level. For customer-level Australian outage data,
there is no public equivalent of ODIN or PowerOutage.us. The
state-level distribution businesses (Endeavour Energy, AusNet,
Essential Energy, etc.) publish their own outage maps, but
without a public API.

So AEMO is the **right source for understanding the operational
state of the Australian grid**, but not for counting affected
households.

## The NEMWeb file structure

NEMWeb publishes hundreds of CSV files continuously. The most
useful for outage analysis:

| File pattern | Content | Update |
|---|---|---|
| `DISPATCHIS_*.csv` | Dispatch interval summary (5-min) | every 5 min |
| `DISPATCH_UNIT_SCADA_*.csv` | Per-unit generation output | every 5 min |
| `DISPATCHREGIONSUM_*.csv` | Regional demand summary | every 5 min |
| `NETWORK_OUTAGEDETAIL_*.csv` | Network outage detail | per event |
| `MARKET_NOTICEBOARD_*.csv` | Market notices (curtailment, reserve, etc.) | per event |
| `TRADINGIS_*.csv` | Trading interval summary (30-min) | every 30 min |

The file naming convention is consistent:

```
{PREFIX}_{YYYYMMDDHHMMSS}_{SEQUENCE}.csv
```

## The R client (`aemo` package)

The `aemo` CRAN package gives tidy R access to the bulk data:

```r
# Install
install.packages("aemo")

# Outages in a date window
aemo::aemo_outages(
  start = "2026-09-01",
  end = "2026-09-05",
  outage_type = "FORCED"  # or "PLANNED" or NULL
)
# Columns: outageid, starttime, endtime, substationid,
#          equipmenttype, equipmentid, outagetype, regionid,
#          restarttimeunknown
```

This is a great pattern to mirror in Python (with pandas / polars)
for OSINT-Data.

## The 3rd-party Open Electricity Platform

A third party (Open Electricity) operates a paid API at
`https://platform.openelectricity.org.au/` that wraps NEMWeb with
a friendlier JSON interface, sub-100ms p95, 99.98% SLA, 5-min
refresh. The free tier is anonymous. This is the **path of least
resistance** for a tenant that wants Australian data without
parsing NEMWeb's quirky CSVs.

## How to wire it up for OpenTIR-Data

1. **First ingest**: pick the most useful files
   (`NETWORK_OUTAGEDETAIL_*.csv`, `DISPATCHREGIONSUM_*.csv`) and
   download via `curl` or `wget` from `http://nemweb.com.au/Reports/CURRENT/`.
   Refresh every 5 minutes.
2. **CSV parse**: the NEMWeb CSVs have a custom 2-line header
   (filename + field definitions). Use a parser that strips the
   header before loading as a real CSV.
3. **Per-region rollup**: store to `osint.aemo_outages` keyed
   by `(regionid, starttime)`.
4. **Geo-enrichment**: NEM regions are 5 fixed zones (QLD, NSW,
   VIC, SA, TAS). Cross-ref with GADM.
5. **Cross-source correlation**: join with ENTSO-E (EU outages)
   on `timestamp` for global grid stress analysis.

## Important caveats

| Caveat | Detail |
|---|---|
| **NEMWeb CSVs have custom headers** | The first 2 rows of each CSV are a filename + field list. Strip before parsing. |
| **This is transmission, not customer-level** | See the critical distinction above. NEMWeb outages are not "X customers are out." |
| **No public API for state-level customer outages** | Ausgrid, Endeavour, Essential, AusNet, etc. publish outage maps with no public API. |
| **WEM (Western Australia) is separate** | Different data format, different file structure. The `aemo` R package focuses on NEM; WEM needs separate handling. |
| **Free public use, but no SLA** | The file server is best-effort. Implement your own retry + backfill logic. |
| **Real-time ticker is busy** | At market open and close, hundreds of files appear per minute. A 5-min poll is fine; a 1-min poll may miss things during heavy updates. |

## What we use it for

- **AU Map view**: 5 NEM region polygons (QLD, NSW, VIC, SA,
  TAS) with regional demand and outage choropleths.
- **Time series**: per-region generation mix, demand, and
  outage MW over time.
- **Network view**: bidding zones as nodes, interconnectors
  (NSW-QLD, VIC-SA, etc.) as edges, with outage events as
  edge-decorations.
- **Story view**: during a heatwave in SE Australia, NEMWeb
  tells us which generators are off-line, which interconnectors
  are constrained, and which loads are being shed.

## See also

- [[odin]] — the US federal standard
- [[entso_e_outages]] — the European equivalent
- [[national_grid_uk_connected_data]] — UK distribution-level
- [[poweroutage_us]] — commercial customer-level aggregator

## License of this connector note

`connectors/aemo_outages.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From AEMO NEMWeb (Australian Energy Market Operator).md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth, refactored]
status: active
display_name: "AEMO NEMWeb (Australian Energy Market Operator)"
fetcher: ingest.fetchers.aemo
source_name: aemo_outages
---

# AEMO NEMWeb (Australian Energy Market Operator)

AEMO NEMWeb JSON API (REFACTORED 2026-09-05 from rolling-bulk CSV to JSON API). Australian Energy Market Operator. `visualisations.aemo.com.au/aemo/apps/api/report/5min/{NEMNETWORK_OUTAGEDETAIL|NEMDISPATCHREGIONSUM|NEMMARKET_NOTICEBOARD}`. No auth, no rate limit, free. 5-min dispatch intervals. Covers NEM (Queensland, NSW, Victoria, South Australia, Tasmania). Transmission-level, not customer-level.

## Metadata

| Field | Value |
|---|---|
| Source system | `aemo_nemweb` |
| Base URL | https://visualisations.aemo.com.au |
| API base | https://visualisations.aemo.com.au/aemo/apps/api/report/5min |
| Schedule (cron) | `*/5 * * * *` (every 5 min) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | AEMO terms (free, attribution required) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Format | Notes |
|---|---|---|---|
| `network_outage_detail` | http://nemweb.com.au/Reports/CURRENT/NETWORK_OUTAGEDETAIL_*.csv | CSV | legacy |
| `dispatch_regionsum` | http://nemweb.com.au/Reports/CURRENT/DISPATCHREGIONSUM_*.csv | CSV | legacy |
| `market_noticeboard` | http://nemweb.com.au/Reports/CURRENT/MARKET_NOTICEBOARD_*.csv | CSV | legacy |
| (NEW, JSON) | visualisations.aemo.com.au/aemo/apps/api/report/5min/{NEMNETWORK_OUTAGEDETAIL\|NEMDISPATCHREGIONSUM\|NEMMARKET_NOTICEBOARD} | JSON | **refactored endpoint** |

## Fetcher

`ingest/fetchers/aemo.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='aemo_outages'`. Per-5-min dispatch rows.

## Common queries

```
GET /v1/sources/aemo_outages
GET /v1/sources/aemo_outages/bundles?region=NSW1&since=2026-09-01
```

## Gotchas

- **Refactored 2026-09-05** from rolling-bulk CSV (5-min window of files appearing in `/Reports/CURRENT/`) to the JSON visualisations API. The CSV endpoints still exist but we now use the JSON one.
- Transmission-level only. For customer-level, Australia does not have a free public source.
- NEM = National Electricity Market = QLD, NSW, VIC, SA, TAS. Not WA (which is the WEM — separate market).

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/ENTSO-E Transparency Platform (European Grid)]] (EU counterpart)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (US customer-level)
- [[Ingestion/U.S. EIA Open Data (Energy Information Administration)]] (US energy context)

