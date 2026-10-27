---
tags: [source, sanctions, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "OFAC Specially Designated Nationals (SDN) List"
fetcher: ingest.fetchers.ofac_sdn
source_name: ofac_sdn
---

# OFAC Specially Designated Nationals (SDN) List

OFAC Specially Designated Nationals (SDN) List — US Treasury sanctions designations. Public domain (US Government work). Updated daily. Free downloads at treasury.gov/ofac/downloads (sdn.xml, sdn_advanced.xml, sdn_comments.xml, consolidated sanctions list). The primary US sanctions dataset, pairs with [[Ingestion/EU Consolidated Financial Sanctions List]] for the EU side. ~13K entries, ~85 MB compressed XML.

## Metadata

| Field | Value |
|---|---|
| Source system | `ofac_sdn` |
| Base URL | https://sanctionssearch.ofac.treas.gov |
| API base | https://www.treasury.gov/ofac/downloads |
| Schedule (cron) | `0 4 * * *` (daily at 04:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | sanctions |
| License | Public domain (US Government work) |
| Auth | none (public) |
| per_tenant_only | false |
| format | xml |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `sdn_xml` | https://www.treasury.gov/ofac/downloads/sdn.xml | GET | XML |
| `sdn_advanced` | https://www.treasury.gov/ofac/downloads/sdn_advanced.xml | GET | XML |
| `consolidated` | https://www.treasury.gov/ofac/downloads/consolidated/consolidated.xml | GET | XML |

## Fetcher

`ingest/fetchers/ofac_sdn.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='ofac_sdn'`. Per-entry rows: `uid`, `firstName`, `lastName`, `sdnType` (Individual/Entity/Vessel/Aircraft), `programs[]`, `aka[]`, `addresses[]`, `nationality`, `citizenship`, `birthDates[]`, `remarks`.

## Common queries

```
GET /v1/sources/ofac_sdn
GET /v1/sources/ofac_sdn/bundles?program=SDGT
GET /v1/sources/ofac_sdn/aggregates?group_by=program,sdn_type
```

## Gotchas

- **Three XML files:** `sdn.xml` (the main list), `sdn_advanced.xml` (with more fields), `consolidated.xml` (all OFAC lists combined). Use the consolidated for the canonical picture.
- 85 MB compressed; the daily fetch is the largest non-bulk download in the pipeline.
- `programs[]` is a list per entry (e.g., `SDGT`, `CYBER2`, `RUSSIA-EO14024`).
- Also has an [OFAC Sanctions Search web UI](https://sanctionssearch.ofac.treas.gov/) (the `/sanctionssearch` part); the bulk downloads are the API.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (sanctions axis)
- [[Ingestion/EU Consolidated Financial Sanctions List]] (EU counterpart)
- [[Ingestion/AlienVault OTX Threat-Intel Pulses]] (cross-ref threat actors with sanctions)
