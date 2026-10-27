---
tags: [source, migration, conflict, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "UNHCR Refugee Population Statistics"
fetcher: ingest.fetchers.unhcr_refugees
source_name: unhcr_refugees
---

# UNHCR Refugee Population Statistics

UNHCR Refugee Statistics (Refugee Data Finder + RSQ API) — persons of concern (refugees, asylum-seekers, IDPs, stateless). CC-BY 4.0. Annual + mid-year updates since 1951. Free API at `api.unhcr.org/rsq/v1` (no key required). The right primary source for the cross-border half of the migration axis. Pairs with [[Ingestion/IOM Displacement Tracking Matrix (DTM)]] (which covers internal displacement).

## Metadata

| Field | Value |
|---|---|
| Source system | `unhcr_refugees` |
| Base URL | https://www.unhcr.org |
| API base | https://api.unhcr.org/rsq/v1 |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | migration, conflict |
| License | CC-BY 4.0 |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `persons_of_concern` | https://api.unhcr.org/rsq/v1/population | GET | paginated JSON |

## Fetcher

`ingest/fetchers/unhcr_refugees.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='unhcr_refugees'`. Per-country, per-year rows.

## Common queries

```
GET /v1/sources/unhcr_refugees
GET /v1/sources/unhcr_refugees/bundles?country_of_origin=SYR
GET /v1/sources/unhcr_refugees/aggregates?group_by=country,year
```

## Gotchas

- Population categories: `Refugees`, `Asylum-seekers`, `Internally displaced persons (IDPs)`, `Stateless persons`, `Others of concern`, `Returned refugees`, `Returned IDPs`.
- Country codes are ISO 3166-1 alpha-3; UNHCR also uses its own 3-letter codes (sometimes).
- Annual + mid-year updates; expect the dataset to lag 3-6 months behind real time.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (migration + conflict axes)
- [[Ingestion/IOM Displacement Tracking Matrix (DTM)]] (internal counterpart)
- [[Ingestion/ACLED — Armed Conflict Location & Event Data Project]] (conflict driver)
