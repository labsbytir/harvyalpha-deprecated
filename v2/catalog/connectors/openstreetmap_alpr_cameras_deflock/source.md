---
tags: [source, cyber, security, tier-1, osint-data, public-no-auth]
status: active
display_name: "OpenStreetMap ALPR Cameras (DeFlock-equivalent)"
fetcher: ingest.fetchers.osm_alpr
source_name: osm_alpr
---

# OpenStreetMap ALPR Cameras (DeFlock-equivalent)

OSM-tagged ALPR (Automatic License Plate Reader) cameras — Flock Safety + other vendors. ~1,440 in NYC metro alone. Civil-liberties / surveillance infrastructure. The right primary source for "where are the ALPR cameras in city X."

## Metadata

| Field | Value |
|---|---|
| Source system | `osm_alpr` |
| Base URL | https://www.openstreetmap.org |
| API base | https://overpass-api.de/api/interpreter |
| Schedule (cron) | `0 5 * * 1` (Mondays at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | cyber, security |
| License | ODbL 1.0 (OpenStreetMap data) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `us` | iso2=US, timeout=600 | US ALPRs |
| `gb` | iso2=GB, timeout=300 | UK ALPRs |
| `ca` | iso2=CA, timeout=300 | Canadian ALPRs |
| `de` | iso2=DE, timeout=300 | German ALPRs |
| `fr` | iso2=FR, timeout=300 | French ALPRs |
| `au` | iso2=AU, timeout=300 | Australian ALPRs |

## Fetcher

`ingest/fetchers/osm_alpr.py` (Overpass API queries)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='osm_alpr'`. Per-camera rows: `osm_id`, `lat`, `lon`, `tags.manufacturer`, `tags.model`, `tags.direction`, `tags.ref`, `city`, `country`, `operator`.

## Common queries

```
GET /v1/sources/osm_alpr
GET /v1/sources/osm_alpr/bundles?country=US&bbox=-74.05,40.55,-73.75,40.95
```

## Gotchas

- Overpass API is rate-limited and time-budgeted (default 25 s server-side; we set 600 s for the US query). Be patient.
- ALPR coverage in OSM is **crowdsourced** — quality varies wildly. DeFlock-equivalent efforts focus on US/UK/CA/DE/FR/AU.
- Mirror servers: `overpass.kumi.systems`, `overpass.private.coffee` (rotate if main is overloaded).

## Related

- [[Plan/Source Categorization]] (cyber + security axes)
- [[Ingestion/Open Infrastructure Map (OSM Power Infrastructure)]] (companion: OSM-derived infrastructure)
- [[Ingestion/Nostr NIP-52 Calendar Events (Decentralized Protests)]] (privacy/protest context)
