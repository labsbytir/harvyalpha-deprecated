# Sources with no public API (manual scrape / bulk download)

These sources either have no programmatic API or require paid access. They can be ingested with HTML scraping, bulk file download, or paid-API credentials.

| Source | URL | Status | Ingestion strategy |
|---|---|---|---|
| UNICEF Data | https://data.unicef.org/resources/resource-type/datasets/ | CKAN exists at `/api/3/action/` but Cloudflare blocks our probes; data is public. | `ckan-generic` fetcher with `data.unicef.org` as base URL. CF may rate-limit; retry with browser-like UA. |
| Open Science Data Cloud | https://www.opensciencedatacloud.org/ | Site was unreachable from this network (000). | Try `https://api.opensciencedatacloud.org/` from server. If alive, use Globus-based API. |
| Google Scholar | https://scholar.google.com/ | **No official API.** Google deprecated Scholar's API; scraping is against ToS. | Use a paid proxy: [SerpAPI](https://serpapi.com/google-scholar-api), [Scaleserp](https://scaleserp.com/), or [Elsevier](https://dev.elsevier.com/). Each costs ~$50/mo+ for meaningful throughput. |
| Pew Research datasets | https://www.pewresearch.org/download-datasets/ | No API; bulk CSV/SPSS downloads linked from each article. | `scrape-downloads` fetcher: list every "Download Dataset" link on `pewresearch.org`, pull the .csv/.sav file. |
| NCES | https://nces.ed.gov/ | Some datasets via `api.data.gov/ed/`. CCD/EDFacts bulk CSVs at `nces.ed.gov/ccd/data/zip/`. | `data_gov` fetcher for College Scorecard; `bulk-ccd` fetcher for CCD/EDFacts. |
| CDC NCEH | https://www.cdc.gov/nceh/data.htm | No dedicated API; the underlying data is on `data.cdc.gov` (Socrata). | Use the existing `socrata` fetcher with `data.cdc.gov` as base. Browse `https://data.cdc.gov/browse?category=Environmental+Health` for the dataset catalog. |
| IEA Energy Atlas | https://www.iea.org/data-and-statistics | Cloudflare blocks the public site; the real API at `https://api.iea.org/...` is **paid** (subscription required for `Monthly Oil Statistics` MES, `Monthly Gas Statistics` MGS, etc.). | Either: (1) pay for IEA API access, or (2) use the `data-un` mirrors of IEA data (e.g. UNdata has IEA-sourced series). |
| Glassdoor Research | https://www.glassdoor.com/research/ | **No API.** Scraping blocked by ToS. | No clean solution. Some of their published reports (e.g. "Worklife Balance", "Best Places to Work") are on `https://www.glassdoor.com/research/data/` as one-off PDF/XLSX; `manual-glassdoor` fetcher downloads those. |
| UNICEF Data | https://data.unicef.org/ | Cloudflare blocks the public API. | Use the `ckan-generic` fetcher with a proper browser-like UA header. If still blocked, scrape the HTML list at `/resources/resource-type/datasets/`. |

## Notes for the user

- "No public API" doesn't mean "no data" — usually there's a bulk download or a non-REST endpoint. The `manual-` and `bulk-` fetchers in OpenTIR-Data handle the awkward cases.
- For the data portal OSINT use case, the highest-value paid sources are: **OpenCorporates** ($90/mo for 50k calls) and **Google Scholar via SerpAPI** ($50/mo+). Everything else is free.
- The CDC NCEH case is interesting: there's no NCEH-specific API, but the data lives on the parent `data.cdc.gov` (Socrata) catalog, which the existing `socrata` connector already covers. The only "manual" step is finding the right Socrata dataset id.
- The 403s from `cdc.gov` and `nces.ed.gov` in my probe are Cloudflare blocking my IP, not real auth issues. Real browsers get through.


## Migrated Context (From WiGLE Public Site Statistics.md)

---
tags: [source, info_environment, security, tier-2, osint-data, public-no-auth]
status: active
display_name: "WiGLE Public Site Statistics"
fetcher: ingest.fetchers.wigle_public
source_name: wigle_public_stats
---

# WiGLE Public Site Statistics

WiGLE (Wireless Geographic Logging Engine) — public, no-auth stats from wigle.net. Total networks observed, per-country, per-US-state breakdowns. 5 API calls/day on the public-no-auth tier; full API requires a free account.

## Metadata

| Field | Value |
|---|---|
| Source system | `wigle` |
| Base URL | https://wigle.net |
| API base | https://api.wigle.net/api/v2 |
| Schedule (cron) | `0 16 * * *` (daily at 16:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 2 |
| Axis | info_environment, security |
| License | WiGLE terms (stats public, full data per free account) |
| Auth | none (public-no-auth for stats) |
| per_tenant_only | false |

## Collections

| Name | Notes |
|---|---|
| `site_stats` | site-wide totals |
| `per_country` | per-country counts |
| `per_region` | per-US-state (country=US) counts |

## Fetcher

`ingest/fetchers/wigle_public.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='wigle_public_stats'`. Per-day stat snapshots.

## Common queries

```
GET /v1/sources/wigle_public_stats
GET /v1/sources/wigle_public_stats/bundles?country=DE
```

## Gotchas

- 5 calls/day is hard. Use the public stats endpoints sparingly; switch to the free-account API for >5/d.
- WiGLE is a community project; coverage is best in US/DE/NL/UK/JP, sparse in Africa/Central Asia.

## Related

- [[Plan/Source Categorization]] (info_environment + security axes)
- [[Ingestion/OpenSky Network Live ADS-B State Vectors]] (companion: RF/aviation tracking)


## Migrated Context (From Digital Public Library of America (DPLA) Bulk + API.md)

---
tags: [source, info_environment, tier-1, osint-data, public-no-auth]
status: active
display_name: "Digital Public Library of America (DPLA) Bulk + API"
fetcher: ingest.fetchers.dpla_bulk
source_name: dpla_bulk
---

# Digital Public Library of America (DPLA) Bulk + API

DPLA. ~5M+ records from NYPL + Library of Congress + Smithsonian + Harvard + 40+ other US cultural heritage institutions. NDJSON bulk tarballs refreshed ~every 2 months; /api/v3/items for incremental updates. CC0 for CC0-licensed contributions. Aggregator layer, not a single-institution dump.

## Metadata

| Field | Value |
|---|---|
| Source system | `dpla_bulk` |
| Base URL | https://pro.dp.la |
| API base | https://api.dp.la/v3 |
| Schedule (cron) | `0 0 1 */3 *` (quarterly) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment |
| License | CC0 (for CC0-licensed contributions); per-institution otherwise |
| Auth | none (public) |
| per_tenant_only | false |
| format | ndjson_gz (bulk, ~5 GB) + json_paginated (API) |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `nyp_ndjson` | https://bulk.dp.la/nyp.jsonl.gz | bulk tarball, ~5 GB |
| `dpla_api_nypl` | https://api.dp.la/v3/items | paginated API, NYPL filter |

## Fetcher

`ingest/fetchers/dpla_bulk.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='dpla_bulk'`. Per-item rows.

## Common queries

```
GET /v1/sources/dpla_bulk
GET /v1/sources/dpla_bulk/bundles?provider=NYPL&since=2020-01-01
```

## Gotchas

- 5 GB bulk tarball is non-trivial. Use the API for incremental updates; bulk only for full re-loads.
- DPLA's rights metadata is heterogeneous — check `rights` field before downstream redistribution.
- For NYPL-only frozen historical data, use [[Ingestion/NYPL Public Domain Bulk Data (2016 CC0 Release)]] which is smaller.

## Related

- [[Plan/Source Categorization]] (info_environment axis)
- [[Ingestion/NYPL Public Domain Bulk Data (2016 CC0 Release)]] (NYPL-only frozen)

