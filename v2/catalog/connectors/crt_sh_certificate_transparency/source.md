---
tags: [source, cyber, security, tier-2, osint-data]
status: active
display_name: "crt.sh Certificate Transparency Logs"
fetcher: ingest.fetchers.crt_sh
source_name: crt_sh
---

# crt.sh Certificate Transparency Logs

Certificate Transparency (CT) log query engine. Tracks every SSL/TLS certificate ever issued for a domain — including subdomains the org didn't know they had. The right primary source for "what new subdomains appeared on example.com this week."

## Metadata

| Field | Value |
|---|---|
| Source system | `crt_sh` |
| Base URL | https://crt.sh |
| API base | https://crt.sh |
| Schedule (cron) | `0 7 * * *` (daily at 07:00 UTC) |
| Rate limit | 20 req/min |
| Tier | 2 |
| Axis | cyber, security |
| License | Public CT data (no copyright, but crt.sh has its own terms) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Query | Notes |
|---|---|---|
| `identity` | `identity=%` (all identities) | per-tenant identity list goes here |

## Fetcher

`ingest/fetchers/crt_sh.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='crt_sh'`. Per-certificate rows: `id`, `logged_at`, `not_before`, `not_after`, `common_name`, `dns_names`, `issuer_name`.

## Common queries

```
GET /v1/sources/crt_sh
GET /v1/sources/crt_sh/bundles?identity=%.example.com
```

## Gotchas

- crt.sh is a single-server hobby project. Be polite: max 20 req/min.
- Identity `%.example.com` returns every subdomain of example.com — large result sets, paginate.
- The CT log itself is the data; crt.sh is just a search engine over the log.

## Related

- [[Plan/Source Categorization]] (cyber + security axes)
- [[Ingestion/Internet Archive Wayback Machine CDX]] (companion: "what changed on a URL")
- [[Ingestion/AbuseIPDB IP Abuse Reports]] (companion: "is this IP hostile")
