# Transitland (Interline) — GTFS / GTFS-RT / GBFS / MDS aggregator

Key: `none required (anonymous tier) — optional `TRANSITLAND_API_KEY` for higher rate limits`
Endpoint: `https://transit.land/api/v2/...` (GraphQL at `https://transit.land/graphql`) + `https://www.transit.land/feeds.csv` for bulk
Auth: HTTP `?api_key=...` query param OR `Authorization: Bearer <token>` header (free tier supported)
Format: **GraphQL** (primary) + **REST** + **CSV bulk export**

Documentation:
- Landing: https://www.transit.land
- Feeds table: https://www.transit.land/feeds
- GraphiQL playground: https://transit.land/playground
- REST API: https://www.transit.land/api/v2
- Bulk feeds export: https://www.transit.land/feeds.csv
- Onestop ID system: https://www.transit.land/ids (every entity — feed, operator, stop, route — has a stable Onestop ID)
- Datastore tools: https://github.com/interline-io (Interline's GitHub org)
- License (data): per-feed (mostly ODbL, CC-BY, or agency-specific ToS)
- License (code): mostly MIT and BSD, see https://github.com/interline-io
- Maintained by: **Interline** (a Mapbox-affiliated company that stewards the project)
- Coverage: thousands of GTFS / GTFS-RT / GBFS / MDS feeds globally

## What it is

**Transitland** is a community-editable aggregator of public transit
feeds, originally created by the **Center for Urban Transportation
Research (CUTR)** at the University of South Florida and now
maintained by **Interline**. It sits alongside the Mobility
Database as one of the two canonical transit data registries, but
with a different emphasis:

| Aspect | Mobility Database | Transitland |
|---|---|---|
| **Focus** | Schema validation + freshness per feed | Per-entity federation (operators, stops, routes) with stable IDs across feeds |
| **ID system** | `mdb-NNNN` slugs per feed | **Onestop IDs** (`f-9q9-caltrain` for feeds, `o-9q9-mtanyctbusbrooklyn` for operators, `s-9q9-5h3y` for stops) — stable across feed versions |
| **Validation** | Canonical GTFS Schedule Validator + Seal of Reliability | Per-feed `import_status` (success / failure + `fetch_error` if applicable) |
| **Federation** | Single catalog | Cross-feed entity resolution (the same physical stop may appear in multiple GTFS feeds; Transitland gives it a single Onestop ID) |
| **License** | CC0 catalog metadata | Per-feed (no global license wrapper) |
| **API style** | OAuth2 REST | GraphQL + REST + CSV bulk |

For our use case, the right pattern is:

- **Mobility Database** as the **registry of feed sources** (the
  "where to fetch" question)
- **Transitland** as the **registry of canonical entities** (the
  "is this the same stop in two feeds" question)

Both are first-class, both are free, both expose public APIs.

## The Onestop ID system

Transitland's killer feature is the **Onestop ID** — a stable,
hierarchical identifier scheme for transit entities:

| Onestop ID | Entity | Example |
|---|---|---|
| `f-9q9-caltrain` | feed | `f-<geohash>-<slug>` |
| `o-9q9-mtanyctbusbrooklyn` | operator | `o-<geohash>-<slug>` |
| `s-9q9-5h3y` | stop | `s-<geohash>-<base36-checksum>` |
| `r-9q9-caltrain~bullet~bullet` | route | `r-<geohash>-<operator>~<route>` |

The geohash prefix (`9q9` in the examples) gives a spatial
hierarchy: stops in the same neighborhood share the same prefix.
This is the same pattern that the **Tile38** in-memory geospatial
database uses, and it makes spatial queries cheap.

The IDs are **stable across feed versions** — if a transit agency
ships GTFS v2025-08-15 and then v2025-09-12, the same physical stop
keeps the same Onestop ID, even if the internal `stop_id` in the
GTFS file changes. This is **the** feature that makes cross-feed
and cross-version analysis possible.

## The data shape (GraphQL)

A typical query:

```graphql
query {
  feeds(where: { country: "US", import_status: SUCCESS }) {
    onestop_id
    name
    urls { static_current }
    state {
      fetched_at
      import_status
      feed_version {
        sha1
        earliest_calendar_date
        latest_calendar_date
      }
    }
    operator {
      onestop_id
      name
      country
      state
      metro
    }
  }
}
```

Returns:

```json
{
  "data": {
    "feeds": [
      {
        "onestop_id": "f-9q9-caltrain",
        "name": "Caltrain",
        "urls": {
          "static_current": "https://www.caltrain.com/.../google_transit.zip"
        },
        "state": {
          "fetched_at": "2026-09-04T10:31:17Z",
          "import_status": "SUCCESS",
          "feed_version": {
            "sha1": "5ec05bcc8f7668ad8ef23608171fc6609853ac9a",
            "earliest_calendar_date": "2026-09-04",
            "latest_calendar_date": "2026-12-13"
          }
        },
        "operator": {
          "onestop_id": "o-9q9-caltrain",
          "name": "Caltrain",
          "country": "US",
          "state": "CA"
        }
      }
    ]
  }
}
```

This is **live, validated, and stable** — the per-feed `state` is
updated daily, and the Onestop ID lets you join across feeds and
versions.

## The bulk export

For one-time snapshot loads, the CSV at `https://www.transit.land/feeds.csv`
gives every feed with its Onestop ID, country, subdivision,
producer URL, and license. ~10,000 rows.

For a richer dump, the GraphQL endpoint supports cursor-based
pagination over `feeds` and `feed_versions`, with filters for
`country`, `subdivision`, `import_status`, `spec` (GTFS / GTFS-RT /
GBFS), and tags.

## How to wire it up for OpenTIR-Data

1. **First ingest**: download `feeds.csv` once. Each row → one
   `osint.datasets` record with `source='transitland_bulk'`.
2. **GraphQL API for incremental updates**: subscribe to the
   `feeds(where: { last_imported_at: { _gt: "<last-sync>" } })` filter.
   Update our `osint.datasets.last_seen_at` and the per-feed
   `fetch_status` for each changed feed.
3. **Operator / route / stop federation**: when we ingest a GTFS
   feed via the generic fetcher, **also call Transitland's GraphQL
   to resolve the Onestop ID** for each stop, route, and operator
   in the feed. Store the Onestop IDs as `payloads.extras.onestop_*`
   in our warehouse. This gives us cross-feed entity resolution
   "for free".
4. **Per-tenant token**: the anonymous tier is fine for bulk loads
   and incremental updates. The paid tier (Transitland Premium)
   exists but is not required.

## Important caveats

| Caveat | Detail |
|---|---|
| **Transitland web UI is Cloudflare-gated** | `https://www.transit.land/feeds` returns a Cloudflare challenge page for non-browser clients. The API at `https://transit.land/api/v2` and the GraphQL at `https://transit.land/graphql` are not gated. |
| **Transitland is a different organization than MobilityData** | Both cover the same feeds but maintain separate catalogs. Cross-reconciliation between them is a non-trivial exercise; the Onestop ID + the `mdb-NNNN` slug aren't directly related. |
| **Onestop ID stability is community-edited** | If Transitland's editors make a mistake, an Onestop ID can be re-pointed. We should keep a per-tenant audit log of "Onestop ID → which feed versions we resolved" so we can re-resolve if a correction happens. |
| **The free tier's rate limit is undisclosed** | Use the anonymous tier for bulk loads; assume ~10 req/min. Paid tier for production workloads. |
| **License is per-feed** | Transitland doesn't impose a global license on its federation. Each feed retains its own license. |
| **MDS (Mobility Data Specification)** | Transitland also indexes MDS feeds (micromobility / shared bikes / scooters). Our `osint.datasets` model can hold these, but our current axes don't include micromobility — flag for a future axis. |

## What we use it for

- **Cross-feed entity resolution**: "is this stop in BART the
  same as the one in Caltrain's GTFS?" — yes, via Onestop IDs.
- **Federated operator search**: "show me every operator in the
  US Northeast with the Seal of Reliability" — combine
  Transitland's operator index with Mobility Database's feed
  metadata.
- **Per-tenant transit map**: the Map view's "transit overlay"
  layer renders stops + routes from feeds the tenant has enabled,
  with cross-feed merges via Onestop ID.
- **Data lineage**: per-tenant audit logs can show "your query
  matched stops s-9q9-5h3y, s-9q9-5h3z, ... from feeds f-9q9-mta,
  f-9q9-bart, ... — all resolved to the same physical locations".

## See also

- [[mobility-database]] — the primary transit registry (catalog +
  validation)
- [[transitwiki]] — the stale 2022 reference; **do not use for new
  work**
- [[gtfs-de]] — already in our vault; one specific national feed
- [[geops]] — geOps Realtime, an aggregator over many of these
  same GTFS feeds
- [[legistar]] — same "stable entity IDs across versions" pattern
  (NYC Council bodies, matters, votes)

## License of this connector note

`connectors/transitland.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From Transitland (Interline) GTFS Aggregator.md)

---
tags: [source, transit, info_environment, tier-1, osint-data, public-no-auth]
status: active
display_name: "Transitland (Interline) GTFS Aggregator"
fetcher: ingest.fetchers.transitland
source_name: transitland
---

# Transitland (Interline) GTFS Aggregator

Transitland (Interline). Thousands of GTFS/GTFS-RT/GBFS/MDS feeds. GraphQL + REST + CSV bulk. Onestop ID system for cross-feed entity resolution (`f-9q9-caltrain` for feeds, `o-9q9-mtanyct` for operators, `s-9q9-5h3y` for stops). Per-feed `import_status` (different signal than [[Ingestion/Mobility Database (MobilityData) GTFS Catalog]]'s validator). Pairs with [[Ingestion/Mobility Database (MobilityData) GTFS Catalog]] for full transit coverage.

## Metadata

| Field | Value |
|---|---|
| Source system | `transitland` |
| Base URL | https://www.transit.land |
| API base | https://transit.land/api/v2 |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | transit, info_environment |
| License | Transitland terms (free, attribution required) |
| Auth | none (public) |
| per_tenant_only | false |
| format | csv + graphql |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `feeds_csv` | https://www.transit.land/feeds.csv | GET | CSV |
| `feeds_graphql` | https://transit.land/graphql | POST | GraphQL |

## Fetcher

`ingest/fetchers/transitland.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='transitland'`. Per-feed metadata rows with Onestop IDs.

## Common queries

```
GET /v1/sources/transitland
GET /v1/sources/transitland/bundles?country=US&import_status=success
```

## Gotchas

- Onestop ID format is the key to cross-source joins. `f-` for feed, `o-` for operator, `s-` for stop, `r-` for route.
- `import_status` distinguishes between "fetched" and "successfully parsed" — better signal than Mobility Database's `status` field for data quality.
- GraphQL endpoint is the right choice for filtered queries; CSV is for bulk.

## Related

- [[Plan/Source Categorization]] (transit + info_environment axes)
- [[Ingestion/Mobility Database (MobilityData) GTFS Catalog]] (companion aggregator)
- [[Ingestion/gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS)]] (single feed)
- [[Ingestion/gtfs.de Nahverkehr (German Local/Urban Transit GTFS)]] (single feed)
- [[Ingestion/gtfs.de GTFS-Realtime (27 German Transit Agencies)]] (single feed)

