# Mobility Database (MobilityData) — GTFS / GTFS-RT / GBFS catalog

Key: `pending — request a free OAuth2 refresh token via the API signup (https://mobilitydatabase.org). The bulk GitHub catalog is public; the API requires auth.`
Endpoint: `https://api.mobilitydatabase.org/v1` (REST) + `https://mobilitydatabase.org/feedstoclone` etc.
Auth: **OAuth2 bearer token** in `Authorization: Bearer <access_token>` header (access tokens expire after 1 hour; refresh tokens are long-lived)
Format: **JSON** (REST) + **NDJSON / CSV** for bulk (GitHub)

Documentation:
- Landing: https://mobilitydatabase.org
- OpenAPI: https://mobilitydatabase.org/api-docs (interactive, browser-rendered)
- About: https://mobilitydatabase.org/about
- Seal of Reliability: https://mobilitydatabase.org/seal-of-reliability
- GitHub catalog repo: https://github.com/MobilityData/mobility-database-catalogs
- Python client: `pip install mobility-database-catalogs` (from the catalog repo)
- License (catalog metadata): **CC0 1.0**
- License (code in catalog repo): **Apache 2.0**
- License (data itself, per feed): per-feed (mostly ODbL, CC-BY, or agency-specific ToS)
- Maintained by: **MobilityData** (the non-profit behind GTFS itself)
- Coverage: **6000+ feeds, 99+ countries** as of 2026-09

## What it is

The **Mobility Database** is the canonical community-maintained
registry of public transit data feeds, maintained by **MobilityData**
— the same non-profit organization that maintains the **GTFS
specification** itself, the **Canonical GTFS Schedule Validator**,
and the **GBFS specification**. If a feed exists in the GTFS
ecosystem, it's in here.

It serves three products:

1. **Bulk catalog (GitHub)** — `MobilityData/mobility-database-catalogs`
   is the canonical source of truth. A Git repo of **JSON files
   per feed** (one per source), with a **CC0 1.0** license on the
   catalog metadata. Code under **Apache 2.0**. A Python library
   (`mobility-database-catalogs` on PyPI) wraps the JSON files with
   query helpers (`get_sources()`, `get_sources_by_country_code()`,
   `get_sources_by_subdivision_name()`, `get_sources_by_bounding_box()`,
   `get_sources_by_feature()`, `get_sources_by_status()`).
2. **REST API** — `https://api.mobilitydatabase.org/v1` — live
   query interface. Filter by country / subdivision / bounding box
   / feature / status. Free OAuth2 (refresh-token based) with no
   rate limit announced. Returns the same per-feed records.
3. **Web UI** — https://mobilitydatabase.org — search and browse
   6000+ feeds. Includes validation status, bounding box, license,
   producer URL, last-fetched timestamp, "Seal of Reliability"
   badge, etc.

This is the **right place** to start if you need to add GTFS
coverage for a region. Not Transitland, not TransitWiki, not the
gtfs.org pointer page — this.

## The Seal of Reliability

A unique feature: MobilityData runs the **Canonical GTFS Schedule
Validator** on every feed daily and awards a "Seal of Reliability"
to feeds that meet 5 criteria:

- **Official** — authorized by the transit agency
- **Stable** — same producer URL for 6+ uninterrupted months
- **Available** — can be downloaded from the URL each day (with a
  14-day grace period if it goes down)
- **Compliant** — 0 errors in the GTFS Schedule Validator (with a
  30-day grace period for new errors)
- **Fresh** — at least 7 days of rolling service coverage
  (calendar.txt + calendar_dates.txt) plus continuous coverage
  (no gaps between feed versions, ≤ 2-year service window)

The Seal is the **trust signal** for downstream consumers. If we
need to know which feeds are production-safe, the Seal badge is
the answer. The API exposes this as a per-feed boolean + a
`reasons` array explaining the failure modes for non-Sealed feeds.

## The catalog data shape

Each feed in the catalog is a JSON record with this shape:

```json
{
  "id": "mdb-1234",
  "type": "gtfs",
  "status": "active",
  "provider": "New York City Transit Authority",
  "name": "MTA New York City Transit Subway",
  "country_code": "US",
  "subdivision_name": "New York",
  "municipality": "New York",
  "bounding_box": {
    "minimum_latitude": 40.55,
    "maximum_latitude": 40.92,
    "minimum_longitude": -74.05,
    "maximum_longitude": -73.74
  },
  "feed_contact_email": "gtfs@nyct.com",
  "producer_url": "https://api.mta.info/gtfs/nyct/subway.zip",
  "urls": {
    "direct_download": "https://api.mta.info/gtfs/nyct/subway.zip",
    "latest": "https://api.mta.info/gtfs/nyct/subway.zip",
    "license": "https://www.mta.info/terms-of-use"
  },
  "license": {
    "spdx_identifier": "CC0-1.0",
    "url": "https://creativecommons.org/publicdomain/zero/1.0/"
  },
  "features": ["fares-v1", "pathways"],
  "last_fetched_at": "2026-09-04T10:30:00Z",
  "last_imported_at": "2026-09-04T10:45:00Z",
  "latest_dataset": {
    "id": "mdbds-5678",
    "hash": "323052edec49c3a4b3da812298c5848af5486a19",
    "downloaded_at": "2026-09-04T10:30:00Z",
    "validation_report": {
      "passed": true,
      "error_count": 0,
      "warning_count": 2,
      "notice_count": 14,
      "url": "https://storage.googleapis.com/mobilitydata-gtfs-analytics-prod/..."
    }
  },
  "tags": ["fares-v1", "pathways", "wheelchair-accessible"],
  "notes": "Updated monthly by MTA."
}
```

This is **richer** than the raw GTFS feed because it includes the
bounding box (essential for the Map view's filter), the license
declaration (essential for our per-org compliance logging), the
Seal-of-Reliability validation result, and the producer URL
(essential for actually fetching the feed).

## How to wire it up for OpenTIR-Data

This is the right source to back our **`gtfs_registry`** table in
the warehouse. The wiring:

1. **First ingest**: `git clone --depth 1
   https://github.com/MobilityData/mobility-database-catalogs`
   into the ingest worker's local disk. The repo is ~30 MB. The
   JSON files are organized by country code (`catalogs/<cc>/<id>.json`).
2. **Per-file parse**: each JSON file is one feed. Resolve
   `id` (the `mdb-NNNN` slug) to our `dataset_fingerprint` and
   write to `osint.datasets` with `source='mobility_database_catalog'`.
   Keep the per-feed bounding box, license, and validation
   metadata as `payloads.extras.*`.
3. **Daily refresh**: pull the GitHub repo (or the REST API) and
   diff against the local snapshot. For each changed feed, update
   the `last_fetched_at`, `latest_dataset.hash`, and
   `validation_report` fields.
4. **Per-feed fetch**: once the registry is loaded, the
   `ingest/fetchers/gtfs_generic.py` fetcher can take any
   `producer_url` from the registry and ingest the feed into
   `osint.gtfs_stops`, `osint.gtfs_routes`, `osint.gtfs_trips`,
   etc. The registry tells us **where to fetch**; the generic
   fetcher does the **how**.

This gives us a single, federated source for global GTFS coverage
without writing 10,000 one-off feed configurations.

## Important caveats

| Caveat | Detail |
|---|---|
| **The bulk repo is on GitHub** | We could clone it or fetch it via the raw API. Cloning is faster; the raw API is more "live". For v1, clone once + daily `git pull` is fine. |
| **OAuth2 is per-developer, not per-feed** | The free API tier is per-account. The 1-hour access tokens are short-lived but the refresh token is long-lived. For production, each tenant has their own developer account. |
| **The REST API is the canonical way to do incremental updates** | Don't `git diff` the GitHub repo (large tree, many PR merges). Use the REST API's `?updated_since=<timestamp>` filter. |
| **Validation reports live in a public GCS bucket** | `https://storage.googleapis.com/mobilitydata-gtfs-analytics-prod/...` — the JSON Schema and CSV reports per feed are public. |
| **GTFS-RT and GBFS feeds are in the same catalog** | The `type` field discriminates (`gtfs` vs `gtfs-rt` vs `gbfs`). Our fetcher routes based on type. |
| **The Seal of Reliability is updated daily** | If a feed loses its Seal, the `latest_dataset.validation_report.passed` flips to false. We should drop the feed from "production-safe" queries on this signal. |
| **Some feeds are stale (status: `inactive` or `deprecated`)** | Filter `status='active'` on the registry query. |
| **License metadata is per-feed** | Don't assume CC0; the catalog metadata is CC0, but each individual feed has its own license. The `license.spdx_identifier` field tells you which. |
| **Provider attribution** | For CC-BY feeds, preserve the `feed_contact_email` and `producer_url` in the dataset metadata so we can comply with attribution requirements. |

## What we use it for

- **Coverage baseline**: one table with every known GTFS feed in
  the world. Filter by country, bounding box, license, Seal status.
- **Per-tenant fetch targets**: a tenant in São Paulo can ask for
  "every active GTFS feed in Brazil with the Seal of Reliability",
  and the registry answers.
- **Cross-validation**: the `validation_report.error_count > 0`
  feeds are the ones to flag in the dashboard's "data quality" view.
- **Discovery UI**: the dashboard's "Sources" tab uses this
  registry as the index, instead of our hand-curated `sources.yaml`.
- **License compliance**: every feed we ingest has a clear
  license declaration from the registry, so per-org audit logs
  can prove compliance.

## See also

- [[transitland]] — the secondary transit registry, with per-feed
  import state (different signal than Mobility Database's validator)
- [[transitwiki]] — the stale 2022 reference; **do not use for new
  work**
- [[gtfs-de]] — already in our vault; one specific national feed
- [[geops]] — geOps Realtime, an aggregator over many of these
  same GTFS feeds
- [[legistar]] — same "public domain, per-record license, bulk
  download" pattern

## License of this connector note

`connectors/mobility-database.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From Mobility Database (MobilityData) GTFS Catalog.md)

---
tags: [source, transit, info_environment, tier-1, osint-data, public-no-auth]
status: active
display_name: "Mobility Database (MobilityData) GTFS Catalog"
fetcher: ingest.fetchers.mobility_database
source_name: mobility_database
---

# Mobility Database (MobilityData) GTFS Catalog

Mobility Database (MobilityData). 6000+ GTFS/GTFS-RT/GBFS feeds, 99+ countries. CC0 metadata (per the GitHub catalog repo) + Apache 2.0 code. OAuth2 for the live REST API (free, per-developer). The primary registry for global GTFS coverage; supersedes TransitWiki + OpenMobilityData.

## Metadata

| Field | Value |
|---|---|
| Source system | `mobility_database` |
| Base URL | https://mobilitydatabase.org |
| API base | https://api.mobilitydatabase.org/v1 |
| Schedule (cron) | `0 4 * * *` (daily at 04:00 UTC) |
| Rate limit | 60 req/min |
| Tier | 1 |
| Axis | transit, info_environment |
| License | CC0 (catalog metadata) + Apache 2.0 (code) |
| Auth | none (catalog) / OAuth2 (API, free) |
| per_tenant_only | false |
| format | ndjson + json_paginated |

## Collections

| Name | Endpoint | Format | Notes |
|---|---|---|---|
| `catalog_github` | https://raw.githubusercontent.com/MobilityData/mobility-database-catalogs/main/catalogs/*.json | NDJSON | full catalog |
| `catalog_api` | https://api.mobilitydatabase.org/v1/feeds | paginated JSON | live API |

## Fetcher

`ingest/fetchers/mobility_database.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='mobility_database'`. Per-feed metadata rows: `feed_id`, `provider`, `country`, `data_type`, `status`, `urls`.

## Common queries

```
GET /v1/sources/mobility_database
GET /v1/sources/mobility_database/bundles?country=US&data_type=gtfs
GET /v1/sources/mobility_database/aggregates?group_by=country,data_type
```

## Gotchas

- OAuth2 is per-developer, not per-app. The free tier is generous.
- Pairs with [[Ingestion/Transitland (Interline) GTFS Aggregator]] for full transit coverage.
- The catalog has a `status` field (`active`/`deprecated`/`inactive`) — filter on `active` for ingest.

## Related

- [[Plan/Source Categorization]] (transit + info_environment axes)
- [[Ingestion/Transitland (Interline) GTFS Aggregator]] (alternative aggregator)
- [[Ingestion/gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS)]] (single feed example)
- [[Ingestion/gtfs.de Nahverkehr (German Local/Urban Transit GTFS)]] (single feed example)
- [[Ingestion/gtfs.de GTFS-Realtime (27 German Transit Agencies)]] (single feed example)

