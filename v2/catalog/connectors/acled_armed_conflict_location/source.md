---
tags: [source, conflict, unrest, security, tier-1, osint-data, mvp, requires-key]
status: active
display_name: "ACLED — Armed Conflict Location & Event Data Project"
fetcher: ingest.fetchers.acled
source_name: acled
api_key_env: ACLED_API_KEY
---

# ACLED — Armed Conflict Location & Event Data Project

ACLED — Armed Conflict Location & Event Data Project. Academic license; widely cited. Per-event: date, actors, location (lat/lon + admin1/admin2), fatalities, event_type (battles, explosions, violence against civilians, protests, riots, strategic developments). 1997-present, 1.6M+ events. Free API at `api.acleddata.com/acled/read` (registration required, free for academic/non-commercial; commercial use needs paid license). The primary structured data source for the conflict axis.

## Metadata

| Field | Value |
|---|---|
| Source system | `acled` |
| Base URL | https://acleddata.com |
| API base | https://api.acleddata.com/acled/read |
| Schedule (cron) | `0 3 * * *` (daily at 03:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | conflict, unrest, security |
| License | Academic (free for non-commercial); commercial paid license required |
| Auth | **Required**: `ACLED_API_KEY` (free academic; commercial tenants bring their own) |
| per_tenant_only | false (academic tenants can use shared; commercial tenants must bring their own key) |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `events` | https://api.acleddata.com/acled/read | GET | paginated JSON |

## Fetcher

`ingest/fetchers/acled.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='acled'`. Per-event rows: `event_id`, `event_date`, `event_type`, `actor1`, `actor2`, `country`, `admin1`, `admin2`, `location`, `latitude`, `longitude`, `fatalities`, `notes`, `source`.

## Common queries

```
GET /v1/sources/acled
GET /v1/sources/acled/bundles?country=UKR&event_type=Battles&since=2026-09-01
GET /v1/sources/acled/aggregates?group_by=country,event_type
```

## Gotchas

- **Free API key** is for academic/non-commercial use. Commercial tenants must bring their own key and use their own quota.
- 1.6M+ events; paginate aggressively.
- `email` field in API requests is required (per their terms) and is your contact.
- Event type taxonomy: `Battles`, `Explosions/Remote violence`, `Violence against civilians`, `Protests`, `Riots`, `Strategic developments`.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (conflict + unrest + security axes)
- [[Ingestion/GDELT 2.0 Global Events Database]] (broader event coverage, less structured)
- [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] (sanctioned actors)
- [[Ingestion/IOM Displacement Tracking Matrix (DTM)]] (displacement from conflict)
