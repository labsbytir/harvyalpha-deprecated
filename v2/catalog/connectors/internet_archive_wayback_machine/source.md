---
tags: [source, info_environment, tier-2, osint-data]
status: active
display_name: "Internet Archive Wayback Machine CDX"
fetcher: ingest.fetchers.wayback_cdx
source_name: wayback_cdx
---

# Internet Archive Wayback Machine CDX

Internet Archive's CDX index of web snapshots. We use it to track changes to a watchlist of URLs (government sites, news outlets, extremist forums, etc.). Per-URL, per-snapshot.

## Metadata

| Field | Value |
|---|---|
| Source system | `wayback` |
| Base URL | https://web.archive.org |
| API base | https://web.archive.org |
| Schedule (cron) | `0 6 * * *` (daily at 06:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 2 |
| Axis | info_environment |
| License | Internet Archive's terms (free for non-commercial, attribution required) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Notes |
|---|---|
| `watchlist` | URL list configured in `collections[].urls` (admin-managed) |

## Fetcher

`ingest/fetchers/wayback_cdx.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='wayback_cdx'`. Per-snapshot rows: `urlkey`, `timestamp`, `original`, `mimetype`, `statuscode`, `digest`, `length`.

## Common queries

```
GET /v1/sources/wayback_cdx
GET /v1/sources/wayback_cdx/bundles?url=example.com&since=2026-01-01
```

## Gotchas

- Be respectful: the CDX API is free but rate-limited; don't dump the whole index.
- Watchlist management is admin-only — update via `sources.yaml` or a future admin UI.
- IA's terms prohibit commercial bulk download of content; we store metadata + hashes, not full HTML.

## Related

- [[Plan/Source Categorization]] (info_environment axis)
- [[Ingestion/crt.sh Certificate Transparency Logs]] (companion: "what changed on a domain")
