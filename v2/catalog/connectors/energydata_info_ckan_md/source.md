---
tags: [source, energy, climate, tier-1, osint-data]
status: active
display_name: "Energydata.info (CKAN)"
fetcher: ingest.fetchers.ckan
source_name: energydata_info
---

# Energydata.info (CKAN)

Open energy data via a CKAN 2.9 instance hosted by the World Bank. 1,191 packages covering global energy datasets — production, consumption, access, prices, efficiency, renewables, electricity.

## Metadata

| Field | Value |
|---|---|
| Source system | `ckan` |
| Base URL | https://energydata.info |
| API base | https://energydata.info |
| Catalog endpoint | `/api/3/action/package_search` |
| Schedule (cron) | `0 3 * * *` (daily at 03:00 UTC) |
| Rate limit | 120 req/min |
| Tier | 1 |
| Axis | energy, climate |
| License | Mixed (per-dataset, mostly open) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Format | Notes |
|---|---|---|---|
| `ckan_root` | (full catalog search) | JSON | paginated, 100/page |

## Fetcher

`ingest/fetchers/ckan.py` (shared with all CKAN instances)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='energydata_info'`. Each CKAN package becomes one row with metadata + resource list.

## Common queries

```
GET /v1/sources/energydata_info
GET /v1/sources/energydata_info/bundles?since=2026-09-01
GET /v1/sources/energydata_info/aggregates?group_by=organization
```

## Gotchas

- License varies per dataset; check `license_id` field before downstream redistribution.
- 1,191 packages × ~3 resources each = ~3,500 resource endpoints. Paginate aggressively.

## Related

- [[Plan/Source Categorization]] (energy + climate axes)
- [[Ingestion/World Bank FinancesOne (FONE)]] (also WBG)
- [[Ingestion/World Bank Microdata Catalog (RTDI)]] (also WBG)
