# NYPL Repository API (DEPRECATED — Aug 1, 2026)

Key: `none required (was: per-account token via /sign_up, but the API itself is now dead)`
Endpoint: `https://api.repo.nypl.org/api/v2/...` (was)
Auth: `Authorization: Token token="..."` header (was; no longer functional)
Format: **JSON** (default) and **XML** (append `.xml`)

Documentation:
- The API root (still serves the deprecation banner as of 2026-09-05): https://api.repo.nypl.org/
- v2 docs (still served): https://api.repo.nypl.org/ (the page itself; the linked examples are dead)
- The signup form (still serves 200, but the API endpoints return 401): https://api.repo.nypl.org/sign_up
- Deprecation contact: `repoapi@nypl.org` (NYPL)
- Bulk data alternative (the real source): https://github.com/NYPL-publicdomain/data-and-utilities
- DPLA bulk download alternative: https://pro.dp.la/developers/bulk-data
- License (was): **CC0 1.0** for bibliographic metadata; content/imagery rights per item
- API was: 10,000 requests/day per token; non-commercial use only without a separate commercial agreement

## ⚠️ This API is dead

As of 2026-09-05 — well past the announced **August 1, 2026** deprecation
date — the NYPL Repository API is **no longer serving data**. The banner
on the API root says:

> The Repo API is being deprecated and will no longer be available
> starting August 1st, 2026. No public API replacement is planned at
> this time. If you have any questions or concerns, contact us
> digitaldam@nypl.org.

I verified this directly:

| Endpoint | HTTP | Body |
|---|---|---|
| `https://api.repo.nypl.org/` (docs page) | 200 | deprecation banner + full v1/v2 endpoint listing |
| `https://api.repo.nypl.org/api/v2/items/recent?per_page=3` | 401 | `HTTP Token: Access denied.` |
| `https://api.repo.nypl.org/sign_up` | 200 | form still served, but a fresh signup no longer yields a working API token |
| `https://api.repo.nypl.org/api/v2/items/search?q=cats&publicDomainOnly=true` | 401 | same |

NYPL published the deprecation on the API root page itself, with a 1+ year
notice. **There is no public API replacement planned**. The Library's
"Digital Collections" website at `https://digitalcollections.nypl.org/`
remains the user-facing interface, but its own public-domain-collection
page explicitly redirects data-hungry users to the GitHub dump and DPLA:

> Our digitized collections are available as machine-readable data: over
> one million records for you to search, crawl and compute. Check out
> our API or download the data from GitHub.
> — `https://www.nypl.org/research/resources/public-domain-collections`

## What it was

The NYPL Repository API (a.k.a. the "Repo API" or "Digital Collections
API") was a v2 REST API over the NYPL's digital collections. It
exposed:

- **~310,000+ public-domain items** (current count, growing), out of
  **~500,000 total** items in Digital Collections
- **MODS** (Metadata Object Description Schema) bibliographic records
- **High-resolution image derivatives** (via the `imageLinks` node)
- **OCR plain text** for select collections
- **Rights statements** (per-item) — critical because only public
  domain items can be redistributed

### The data model (was)

```
Collection (e.g. "Maps of the City of New York")
  └── Container (a sub-collection or album)
        ├── Item (a logical work, e.g. a single map)
        │     ├── Capture (a scan of one face of the item, recto/verso)
        │     │     ├── imageLinks (high-res jpg derivatives)
        │     │     ├── MODS (descriptive metadata)
        │     │     ├── rights (per-item reuse statement)
        │     │     └── plainText (OCR, if available)
        │     └── Capture (verso scan, etc.)
        └── Item
```

### The endpoint surface (was)

17 v2 endpoints (now all 401):

| Endpoint | What it gave |
|---|---|
| `GET /items/total` | Total item count |
| `GET /items/featured` | Featured items |
| `GET /items/roots` | Root collections |
| `GET /collections` | All collections (top level + orphan items) |
| `GET /collections/[:uuid]` | A collection's children |
| `GET /collections/[:uuid]/subcollections` | Just the sub-containers |
| `GET /collections/[:uuid]/items` | Items in a collection |
| `GET /mods/[:uuid]` | MODS record for any UUID (capture, item, container, or collection) |
| `GET /items/mods_captures/[:uuid]` | MODS + capture info for a UUID |
| `GET /items/item_details/[:uuid]` | Capture MODS + sibling / root / immediate captures |
| `GET /items/[:type]/[:id]` | UUID lookup by local identifier (`local_bnumber`, `local_image_id`, `oclc`, `isbn`, `lccn`, etc.) |
| `GET /items/[:uuid]` | All captures for a UUID |
| `GET /items/collection/[:uuid]` | All captures (recursive) for a UUID |
| `GET /items/collection/all/[:uuid]` | All captures (full tree) for a UUID |
| `GET /items/plain_text/[:uuid]` | OCR plain text (parse the ALTO) |
| `GET /items/minified_alto/[:uuid]` | Minified ALTO XML |
| `GET /items/mets_alto/[:uuid]` | Full METS ALTO |
| `GET /items/recent` | Most recently added captures |
| `GET /items/search?q=...&field=...&ftype=...&filter[]=...` | Full-text + fielded search across MODS |
| `GET /items/rights/[:uuid]` | Rights profile for a UUID |

The killer feature was `?publicDomainOnly=true` on search, which
filtered to items cleared as public domain — a list you could
redistribute without a per-item rights check.

## What the data was good for

This was the single most useful free public-domain source for
historical research, because:

- **Maps**: NYPL's Lionel Pincus & Princess Firyal Map Division has
  the largest US collection of historical maps (~400,000 sheets, much
  digitized)
- **Photographs**: Farm Security Administration, NYC street
  photography, Civil War, Schomburg Center for Research in Black
  Culture
- **Manuscripts**: archives, broadsides, pamphlets
- **Sheet music, prints, posters**: pre-1929 = public domain
- **NYC-specific**: menus, restaurant cards, real estate
  brochures, theater programs

For OSINT specifically, the **map collection** was the killer
feature: georeferenced historical maps of New York, the US, and the
world going back to the 16th century, with full MODS metadata
(title, cartographer, publisher, date, scale, projection,
geographic subject).

## What to use instead (post-deprecation)

NYPL's own deprecation page points at two alternatives:

| Path | What it covers | License | Refresh cadence | Our connector |
|---|---|---|---|---|
| **`NYPL-publicdomain/data-and-utilities`** GitHub repo | 187K public-domain items from 2016 snapshot | CC0 | frozen snapshot (was 2016-12-30) | [[nypl-publicdomain-bulk]] |
| **DPLA bulk download** | All NYPL Digital Collections metadata (not just PD) | CC0 (NYPL contribution) | ~every 2 months (per NYPL about page) | [[dpla-bulk]] |
| NYPL Digital Collections website (manual) | Visual browsing, per-item high-res download | per-item rights | live | (browser, no API) |
| NYPL Catalog API (`platform.nypl.org`) | NYPL library catalog (books, not digital collections) | per-record | live | (not yet in vault) |

**The honest assessment**: the 2016 GitHub dump is the right primary
source for now. DPLA is the right secondary (more current, but you
have to download a 30-60 GB tarball and filter by `provider.name =
"New York Public Library"`).

For OSINT-Data v1, the right wiring is:

1. **Ingest the 2016 GitHub dump once on setup** (small enough to be
   a one-time load, ~187K records). Use it for historical baseline.
2. **Subscribe to the DPLA bulk refresh** if and when we add
   per-month updates. The DPLA tarball is large (30-60 GB) but
   well-formed.
3. **For new items** (post-2016), point tenants at
   `https://digitalcollections.nypl.org/` to download high-res images
   per item. The image derivatives are stable URL patterns:
   `https://images.nypl.org/index.php?id=<imageID>&t=w` (large),
   `&t=t` (150px), `&t=f` (140px), `&t=b` (100x100 square).

## See also

- [`nypl-publicdomain-bulk.md`](nypl-publicdomain-bulk.md) — the
  primary replacement: GitHub CC0 dump
- [`dpla-bulk.md`](dpla-bulk.md) — the secondary replacement: DPLA
  bulk tarball
- [`owid-datasets.md`](owid-datasets.md) — same CC0 bulk-dump
  pattern (OWID's `owid-datasets` repo)
- [`nasa-earthdata.md`](nasa-earthdata.md) — same "API + bulk
  archive" pattern
- [`liveuamap.md`](liveuamap.md) — same "we documented the dead API
  so future contributors don't waste time" pattern
- [`no-public-api.md`](no-public-api.md) — the
  "research/advocacy org with no public data API" family

## License of this connector note

`connectors/nypl-repo-api.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From NWS api.weather.gov + SPC Active Alerts.md)

---
tags: [source, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "NWS api.weather.gov + SPC Active Alerts"
fetcher: ingest.fetchers.nws_tornadoes
source_name: nws_tornadoes
---

# NWS api.weather.gov + SPC Active Alerts

US National Weather Service — active alerts API + Storm Prediction Center daily tornado CSVs. No key, US coverage only. Per-alert: event, severity, certainty, urgency, area (polygon), effective, expires, sender.

## Metadata

| Field | Value |
|---|---|
| Source system | `nws` |
| Base URL | https://api.weather.gov |
| API base | https://api.weather.gov |
| Schedule (cron) | `*/5* * * * *` (every 5 min) |
| Rate limit | 12 req/min |
| Tier | 1 |
| Axis | climate |
| License | Public domain (US Government work) |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `active_tornado_warnings` | event=Tornado | only active tornado warnings |

## Fetcher

`ingest/fetchers/nws_tornadoes.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='nws_tornadoes'`. Per-alert rows with full NWS CAP schema.

## Common queries

```
GET /v1/sources/nws_tornadoes
GET /v1/sources/nws_tornadoes/bundles?event=Tornado&since=2026-09-01
```

## Gotchas

- US coverage only. Outside US, use country-specific meteorological agencies.
- `User-Agent` header with contact email is required per NWS API policy.
- `effective` and `expires` are ISO-8601 with timezone.

## Related

- [[Plan/Source Categorization]] (climate axis)
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (multi-hazard global)
- [[Ingestion/USGS Earthquake Hazards Program GeoJSON Feeds]] (companion: seismic)


## Migrated Context (From NYPL Public Domain Bulk Data (2016 CC0 Release).md)

---
tags: [source, info_environment, tier-1, osint-data, public-no-auth]
status: active
display_name: "NYPL Public Domain Bulk Data (2016 CC0 Release)"
fetcher: ingest.fetchers.nypl_publicdomain_bulk
source_name: nypl_publicdomain_bulk
---

# NYPL Public Domain Bulk Data (2016 CC0 Release)

New York Public Library 2016 CC0 release. 187K items: maps, photographs, manuscripts, sheet music, prints, menus, theatrical posters, broadsides. NDJSON + CSV. CC0 1.0. Frozen 2015-12-30 snapshot. Primary replacement for the deprecated NYPL Repo API (Aug 1, 2026).

## Metadata

| Field | Value |
|---|---|
| Source system | `nypl_publicdomain_bulk` |
| Base URL | https://github.com/NYPL-publicdomain/data-and-utilities |
| API base | https://raw.githubusercontent.com/NYPL-publicdomain/data-and-utilities/master |
| Schedule (cron) | `0 0 1 1 *` (yearly, January 1) |
| Rate limit | 0 (bulk download from GitHub) |
| Tier | 1 |
| Axis | info_environment |
| License | CC0 1.0 |
| Auth | none (public) |
| per_tenant_only | false |
| format | ndjson + csv |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `items_ndjson` | https://raw.githubusercontent.com/NYPL-publicdomain/data-and-utilities/master/items/*.json | per-item metadata |
| `collections_ndjson` | https://raw.githubusercontent.com/NYPL-publicdomain/data-and-utilities/master/collections/*.json | per-collection metadata |

## Fetcher

`ingest/fetchers/nypl_publicdomain_bulk.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='nypl_publicdomain_bulk'`. Per-item rows: `uuid`, `title`, `creator`, `date`, `type`, `collection`, `rights`, `image_url`, `metadata_url`.

## Common queries

```
GET /v1/sources/nypl_publicdomain_bulk
GET /v1/sources/nypl_publicdomain_bulk/bundles?type=Photograph&since=1900
```

## Gotchas

- **Frozen at 2015-12-30.** For more current NYPL metadata, use [[Ingestion/Digital Public Library of America (DPLA) Bulk + API]] which has regular DPLA updates.
- The NYPL Repo API was deprecated Aug 1, 2026; this bulk data is the replacement.
- GitHub raw URLs — be aware of GitHub's rate limits (60 req/hr unauthenticated, 5k req/hr with token).

## Related

- [[Plan/Source Categorization]] (info_environment axis)
- [[Ingestion/Digital Public Library of America (DPLA) Bulk + API]] (current, multi-institution)
