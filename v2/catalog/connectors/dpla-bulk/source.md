# DPLA Bulk Download (Digital Public Library of America)

Key: `none required — bulk data is free; DPLA API requires a key for higher rate limits (the public anonymous quota is 1 req / 5 sec, ~17K/day)`
Endpoint: `https://pro.dp.la/developers/bulk-data`
Auth: `none for bulk; DPLA API key for `/api/v3/*` endpoints`
Format: **JSON Lines** (one record per line, NDJSON); **JSON** for the API

Documentation:
- Bulk data developer hub: https://pro.dp.la/developers/bulk-data
- DPLA API v3 docs: https://pro.dp.la/developers/pipes
- DPLA codex (search UI): https://dp.la/
- Bulk data on AWS S3 (also accessible): `s3://dpla-provider-export/` (managed by DPLA / LYRASIS)
- DPLA MAP v3 (Mapping Application): https://pro.dp.la/developers/pipes
- Bulk download script: `https://github.com/dpla/platform/blob/master/scripts/bulk_download.sh` (community-maintained)
- License (NYPL contribution): **CC0 1.0** (per NYPL's contribution to DPLA; other providers have their own terms)
- License (DPLA aggregation): the metadata aggregation itself is dedicated to **CC0 1.0** for the parts contributed by CC0-licensed providers; non-CC0 providers contribute under their own terms
- Refresh cadence: **~every other month** per NYPL's Digital Collections about page

## What it is

The **Digital Public Library of America** (DPLA) is a non-profit
aggregation layer that pulls metadata from ~40+ large US cultural
heritage institutions — NYPL, Library of Congress, Smithsonian,
Harvard, Internet Archive, HathiTrust, California Digital Library,
and many state/regional digital libraries — into a single
searchable index.

DPLA exposes the same metadata in two ways:

1. **API** (`https://api.dp.la/v3/items`): keyword + faceted search
   over all aggregated items. Pagination via `page` + `page_size`.
2. **Bulk download**: a full export of every record as NDJSON
   (gzipped per-provider tarballs), refreshed ~every other month.
   Each tarball is one contributing institution's full metadata
   export.

For our use case, the bulk download is the right path because:

- The full NYPL Digital Collections metadata is there (~500K
  items, not just the 187K PD subset from the 2016 GitHub dump)
- It's more current (refreshed ~every 2 months, vs the frozen
  2016 GitHub dump)
- It's free, no API key required
- The format is clean NDJSON
- The rights metadata is preserved per-record

## The bulk download URL pattern

```
https://pro.dp.la/developers/bulk-data
```

The actual download URLs are **per-institution** and **time-stamped**.
The current pattern (as of 2026) is:

```
https://dpla-provider-export-prod.s3.amazonaws.com/.../nyp.jsonl.gz
```

or

```
https://bulk.dp.la/.../nyp.jsonl.gz
```

(I need to verify the exact URL on the DPLA bulk-data developer page
before wiring up a fetcher. The URL pattern changes occasionally as
DPLA migrates infrastructure; check the official page before
relying on it.)

## The DPLA API (for incremental updates + per-record lookups)

For the daily / weekly incremental case (when we don't want to
redownload a 30-60 GB tarball just to pick up new items), the
`/api/v3/items` endpoint is the right tool:

```
GET https://api.dp.la/v3/items
  ?sourceResource.subject.name=immigration
  &provider.name=New+York+Public+Library
  &page_size=100
  &page=1
  &api_key=<your-key>
```

The DPLA API has:

- **Full-text search** across all contributing institutions
- **Faceted filtering** by `provider.name`, `sourceResource.type`,
  `sourceResource.subject.name`, `sourceResource.spatial.name`,
  `sourceResource.date.begin` / `end` (year ranges), `rights`
- **Per-record deep links** to the contributing institution's
  original page
- **IIIF manifest** support (so a viewer can render thumbnails
  directly)
- **GeoJSON-encoded coordinates** in `sourceResource.spatial` (for
  map view)
- **Rights statements** per record (CC0, CC-BY, NoC-US, InC, etc.)

A free API key raises the rate limit to **2,000 requests/hour per
key** (vs the anonymous tier's ~17K/day but slower). Keys are
issued at https://pro.dp.la/developers/pipes after a quick signup.

## The data shape (per record)

A DPLA item record looks like:

```json
{
  "id": "nypl--7a04f0e0c0f4b4f5e0c0f4b4f5e0c0f4",
  "provider": {
    "name": "New York Public Library",
    "@id": "http://dp.la/api/contributor/nypl"
  },
  "dataProvider": "NYPL Research Libraries",
  "isPartOf": { "name": "Maps of New York City" },
  "@type": "ore:Aggregation",
  "sourceResource": {
    "title": ["Map of the city of New York, 1851"],
    "description": ["Hand-colored lithograph..."],
    "subject": [
      { "name": "New York (N.Y.) -- Maps" },
      { "name": "Manhattan (New York, N.Y.)" }
    ],
    "creator": ["W. J. Stone"],
    "type": ["image", "cartographic"],
    "date": [
      { "begin": "1851", "end": "1851" }
    ],
    "spatial": [
      {
        "name": "New York, NY",
        "coordinates": "40.7128, -74.0060"
      }
    ],
    "language": [{"name": "English"}],
    "rights": [
      "Public Domain"
    ],
    "rightsURI": [
      "http://rightsstatements.org/vocab/NoC-US/1.0/"
    ],
    "format": "image/jpeg",
    "identifier": ["nypl:UUID-12345-67890"],
    "isPartOf": { "name": "Maps of New York City" }
  },
  "ingestType": "item",
  "ingestDate": "2024-11-15T00:00:00Z",
  "object": "https://images.nypl.org/...jpg",
  "IIIFManifest": "https://iiif.io/api/presentation/2.1/example/manifest.json",
  "thumbnail": "https://iiif.io/api/image/.../full/200,/0/default.jpg"
}
```

This is **richer** than the NYPL Repo API's MODS output for our
purposes, because:

- **Coordinates** are pre-extracted from the subject headings (great
  for the Map view)
- **IIIF manifest URL** is pre-computed (great for the viewer)
- **`@type: ore:Aggregation`** is a DPLA-specific wrapper that
  gives us both the metadata and the digital object URL in one record
- **`provider` / `dataProvider`** separate the aggregator (DPLA)
  from the source institution (NYPL)
- **`rights` is a per-record array** with both text and URI

## How to wire it up for OpenTIR-Data

Two complementary sources:

1. **`dpla_bulk`**: a one-time (or quarterly) bulk load of the
   DPLA `nyp.jsonl.gz` (NYPL) tarball. ~500K records per
   institution per refresh.
2. **`dpla_api_nypl`**: an incremental API fetcher that hits
   `/api/v3/items?provider.name=New+York+Public+Library&page_size=500`
   with a `sort_by=ingestDate` order, daily. Catches new items
   between bulk refreshes.

The right pattern:

- **First ingest** is the bulk tarball, in full
- **Daily increment** is the API, sorted by `ingestDate desc`,
  paginating until you hit a record you've already stored
- **Quarterly re-bulk** to catch any records the API missed (e.g.
  DPLA's reconciliation work)

For the DPLA API fetcher, an API key is the right path because
the public anonymous rate limit (~17K/day) is fine for one
institution's incremental updates but uncomfortable for catch-up
scans. Per-tenant keys live in `/etc/osint/<org>/secrets.env` as
`DPLA_API_KEY`.

## Important caveats

| Caveat | Detail |
|---|---|
| **The bulk tarball is large** | ~30-60 GB for the full DPLA export (all institutions). The NYPL-only slice is ~5-10 GB. |
| **Bulk URL pattern changes** | DPLA migrated off their old bulk-data hosting multiple times. Verify the URL on the current docs page before wiring it up. |
| **NYPL contribution is CC0** | The DPLA aggregation itself is CC0 for CC0-licensed contributions; other providers' contributions are under their own terms. Filter on `rights` / `rightsURI` to be safe. |
| **The API key has a 2000 req/hr cap** | That's still 480K records/day, more than enough for incremental. |
| **DPLA Pipeline shutdown** | DPLA's old Pipes/MAP API v2 was deprecated in 2022. The v3 API at `https://api.dp.la/v3/items` is current. |
| **IIIF manifest URLs may not be stable** | DPLA's IIIF endpoints have moved several times. Treat them as best-effort, not canonical. |

## What we use the data for

- **Map view**: pre-geocoded coordinates for ~5M+ items, with
  a `provider.name` filter to scope to NYPL / LoC / Smithsonian
- **Time series**: `sourceResource.date.begin` × count of items ×
  subject → publication trends
- **Story view**: per-item IIIF deep links for the viewer
- **Network**: `creator` × item → artist / author network
- **Compare**: NYPL coverage vs Library of Congress vs Smithsonian
  for a given subject

## See also

- [`nypl-publicdomain-bulk.md`](nypl-publicdomain-bulk.md) —
  the NYPL-specific CC0 dump (smaller, PD-only, frozen 2016)
- [`nypl-repo-api.md`](nypl-repo-api.md) — the deprecated API
  this and `nypl-publicdomain-bulk` together replace
- [`owid-datasets.md`](owid-datasets.md) — same CC0 bulk-dump
  pattern
- [`nasa-earthdata.md`](nasa-earthdata.md) — same "API + bulk
  archive" pattern
- [`civicus-monitor.md`](civicus-monitor.md) — same
  structured-data under public license pattern

## License of this connector note

`connectors/dpla-bulk.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

