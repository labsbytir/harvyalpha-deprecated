---
tags: [source, migration, conflict, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "IOM Displacement Tracking Matrix (DTM)"
fetcher: ingest.fetchers.iom_dtm
source_name: iom_dtm
---

# IOM Displacement Tracking Matrix (DTM)

IOM Displacement Tracking Matrix (DTM) — the global standard for internal-displacement tracking. CC-BY 3.0 IGO. Country-level event tracking, baseline area assessments, flow monitoring, and surveys. 90+ countries covered. Primary source for the migration axis, paired with [[Ingestion/UNHCR Refugee Population Statistics]] for cross-border flows. Free API at `/api/open/v1`.

## Metadata

| Field | Value |
|---|---|
| Source system | `iom_dtm` |
| Base URL | https://dtm.iom.int |
| API base | https://dtm.iom.int/api |
| Schedule (cron) | `0 6 * * *` (daily at 06:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | migration, conflict |
| License | CC-BY 3.0 IGO |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `country_events` | https://dtm.iom.int/api/open/v1/event/country | GET | paginated JSON |

## Fetcher

`ingest/fetchers/iom_dtm.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='iom_dtm'`. Per-country, per-event rows.

## Common queries

```
GET /v1/sources/iom_dtm
GET /v1/sources/iom_dtm/bundles?country=SD&since=2026-09-01
GET /v1/sources/iom_dtm/aggregates?group_by=country,event_type
```

## Gotchas

- The DTM API is at `/api/open/v1`; older documentation may show different paths.
- Event types: `Event Tracking`, `Baseline Assessment`, `Flow Monitoring`, `Survey`.
- 90+ countries; coverage is best in active conflict/disaster zones.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (migration + conflict axes)
- [[Ingestion/UNHCR Refugee Population Statistics]] (cross-border counterpart)
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (driver of displacement)
