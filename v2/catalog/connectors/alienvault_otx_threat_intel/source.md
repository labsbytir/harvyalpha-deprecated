---
tags: [source, cyber, security, sanctions, tier-2, osint-data, requires-key]
status: active
display_name: "AlienVault OTX Threat-Intel Pulses"
fetcher: ingest.fetchers.otx
source_name: otx_alienvault
api_key_env: OTX_API_KEY
---

# AlienVault OTX Threat-Intel Pulses

AT&T AlienVault Open Threat Exchange (OTX). Threat-intel pulses — IOCs (indicators of compromise), threat actors, campaigns, malware families, attack patterns. Free API, free key.

## Metadata

| Field | Value |
|---|---|
| Source system | `otx` |
| Base URL | https://otx.alienvault.com |
| API base | https://api.otx.alienvault.com/api/v1 |
| Schedule (cron) | `0 9 * * *` (daily at 09:00 UTC) |
| Rate limit | 60 req/min |
| Tier | 2 |
| Axis | cyber, security, sanctions |
| License | OTX terms (free for any use, attribution to AlienVault required) |
| Auth | **Required**: `OTX_API_KEY` |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `pulses_subscribed` | `modified_since_days=7` | pulses from subscribed authors, last 7 d |

## Fetcher

`ingest/fetchers/otx.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='otx_alienvault'`. Per-pulse rows: `id`, `name`, `description`, `tags`, `indicators[]`, `adversary`, `attack_ids`, `malware_families`, `created`, `modified`.

## Common queries

```
GET /v1/sources/otx_alienvault
GET /v1/sources/otx_alienvault/bundles?tag=ransomware&since=2026-09-01
GET /v1/sources/otx_alienvault/aggregates?group_by=adversary
```

## Gotchas

- Subscribe to relevant authors in OTX UI first; the API only returns pulses from authors you follow.
- Some IOCs overlap with [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] (sanctioned actors with linked infrastructure).

## Related

- [[Plan/Source Categorization]] (cyber + security + sanctions axes)
- [[Ingestion/VirusTotal File/URL/IP Reputation]] (IOC enrichment)
- [[Ingestion/Shodan IoT/Host Search]] (infrastructure lookup)
- [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] (sanctions cross-ref)
