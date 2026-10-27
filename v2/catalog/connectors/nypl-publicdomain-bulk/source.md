# NYPL Public Domain Bulk Data (GitHub CC0 dump, 2016 snapshot)

Key: `none required — all data is public on GitHub under CC0 1.0`
Endpoint: `https://github.com/NYPL-publicdomain/data-and-utilities`
Auth: `none`
Format: **JSON (one record per line, NDJSON)** for items + collections; **CSV** (with pipe-delimited arrays) for spreadsheet users

Documentation:
- Repository: https://github.com/NYPL-publicdomain/data-and-utilities
- README: https://github.com/NYPL-publicdomain/data-and-utilities/blob/master/README.md
- License file (CC0): https://github.com/NYPL-publicdomain/data-and-utilities/blob/master/LICENSE
- Code examples: https://github.com/NYPL-publicdomain/data-and-utilities/tree/master/code_examples
- NYPL Labs remix site: http://publicdomain.nypl.org/
- NYPL Digital Collections website (live, post-2016 items): https://digitalcollections.nypl.org/
- License: **CC0 1.0 Universal** (public domain dedication, no attribution required)
- Snapshot date: **2015-12-30** (released 2016-01-06 as the "NYPL January 2016 Public Domain Release")
- Scale: **187,000+ items** (initial release); the README explicitly says this is a one-time release, not a regularly-refreshed dataset

## What it is

The **NYPL Public Domain Bulk Data** is a one-time CC0 release of
metadata (and high-resolution image links) for every public-domain
item in NYPL's Digital Collections as of 2015-12-30. The release
was published on January 6, 2016, alongside the launch of
high-resolution image downloads on the Digital Collections website.

This is the **primary replacement for the deprecated NYPL Repo
API** ([`nypl-repo-api.md`](nypl-repo-api.md)). It's the only
free, machine-readable, license-clean source for NYPL's
public-domain digital collections.

The dataset is organized as two parallel collections of files:

| Path | Format | Description |
|---|---|---|
| `items/*.json` | NDJSON (one item per line) | One file per collection. Each line is one item with all its captures, image links, contributors, dates, etc. |
| `items/*.csv` | CSV with pipe-delimited arrays | Same items, flattened to a single table for spreadsheet workflows |
| `collections/*.json` | NDJSON (one collection per line) | The parent collections that group items |
| `collections/*.csv` | CSV | Same collections, flattened |

There are also per-collection subfolders and a `captures/` directory
in some releases.

## The data fields (from the README)

The CSV and JSON files have these fields (CSV column → JSON key):

- `UUID` → `uuid` — the unique identifier (same scheme as the Repo API)
- `Database ID` → `databaseID` — internal NYPL ID
- `Title` → `title`
- `Alternative Title` → `alternativeTitle` (array)
- `Contributor` → `contributor` (array of strings in CSV, array of objects in JSON)
- `Contributor name` → `contributor.contributorName` (JSON only)
- `Creator` → `creator` (array)
- `Date Created` → `dateCreated` (structured: original, period, year, century, era)
- `Date Of Work` → `dateOfWork`
- `Description` → `description`
- `Subject (Name)` / `Subject (Topic)` / `Subject (Geographic)` / `Subject (Temporal)` → split subject fields with LCSH + URI links
- `Genre` → `genre`
- `Physical Description` → `physicalDescription`
- `Language` → `language`
- `Publisher` → `publisher`
- `Place Of Publication` → `placeOfPublication`
- `Place Of Origin` → `placeOfOrigin`
- `Rights` → `rights` (the rights statement; for PD items, this is "Public Domain" or similar)
- `Rights URI` → `rightsURI` (e.g. `http://rightsstatements.org/vocab/NoC-US/1.0/`)
- `Type Of Resource` → `typeOfResource` (still image, text, cartographic, notated music, moving image, etc.)
- `Item URL` → `itemURL`
- `Digital Collections URL` → `digtalCollectionsURL` (typo in source)
- `Image ID` → `imageID` (the canonical image identifier)
- **Captures** → `captures` (JSON only: array of high-res JPG URLs)
- **Ocr Text** → `ocrText` (when available)
- **Number Of Captures** → `numCaptures`
- **Repository** → `repository` ("Research Libraries" or "Schomburg Center" or "Science, Industry and Business Library")
- **Division** → `division` (Wallach Division of Art, Prints and Photographs, etc.)
- **Collection ID** → `collectionID`
- **Collection Name** → `collectionName`
- **Sub-Collection** → `subCollectionName`

This is a much richer structure than the Repo API's `MODS` output,
because the release was flattened specifically to be friendly to
non-librarians (CSV-friendly). You lose the strict MODS XML
hierarchy, but you gain easy SQL ingestion.

## How to wire it up for OpenTIR-Data

This is a **one-time bulk load**, not a continuous source. The
right pattern is:

1. **Add a source block** `nypl_publicdomain_bulk` in `sources.yaml`
   with `schedule: "0 0 1 1 *"` (annually, on January 1) just to
   detect if NYPL ever publishes a refresh.
2. **First ingest** is a full download of the GitHub repo at
   `git clone https://github.com/NYPL-publicdomain/data-and-utilities`
   (or a sparse fetch of just `items/*.json` + `collections/*.json`).
3. **Per-file parse**: stream each NDJSON file line-by-line, resolve
   per-record `uuid` to a dataset_fingerprint, write to the
   `osint.datasets` table with `source='nypl_publicdomain_bulk'`.
4. **For image derivatives**: store the `captures[]` URLs as the
   `raw_payload.image_url` field. We don't download the high-res
   JPGs by default (187K × ~2 MB = 374 GB of image data) but a
   tenant with a "show me the actual image" use case can pull
   individual JPGs on demand via the per-item `imageID` URL pattern.
5. **For OCR**: `ocrText` (when present) is plain text from
   Internet Archive's OCR; store as `payloads.extras.ocr_text` and
   index in the full-text search index.

For OSINT-Data specifically, the high-value subsets are:

| Subset | Scale | What it gives |
|---|---|---|
| **Maps** (cartographic `typeOfResource`) | ~50,000+ maps | Historical georeferenced maps of NYC + US + world, with publisher, scale, projection. Cross-reference with the David Rumsey Map Collection (already partially in our vault) for full coverage. |
| **Photographs** (still image, 20th c.) | ~50,000+ photographs | Pre-1929 = PD. The FSA collection alone is ~16,000 photographs; WPA + NYC street photography; Schomburg's Black history photographs. |
| **Menus** (Restaurant Trade Cards collection) | ~10,000+ | Historical NYC restaurant menus, 1850s-1920s. Great for food / migration / immigration history journalism. |
| **Sheet music** (notated music) | ~10,000+ | Pre-1929 sheet music covers. Strong immigration / racial caricature content — important for journalism on historical propaganda imagery. |
| **Prints** (still image, 17th-19th c.) | ~20,000+ | Political cartoons, satirical prints, broadsides. |
| **Theatrical posters** | ~5,000+ | Pre-1929 theater posters. |

## Important caveats

| Caveat | Detail |
|---|---|
| **It's a 2016 snapshot** | The data is from 2015-12-30. NYPL has added ~200,000 more PD items since then via the Digital Collections website. The README explicitly says "at this time the data is a snapshot" — they were considering regular updates but never published one. |
| **Items missing from the snapshot** | If you need post-2016 NYPL PD items, use [[dpla-bulk]] (refreshed ~every 2 months) or scrape per-item from `digitalcollections.nypl.org`. |
| **The license is CC0 for the metadata** | Image content is also released as PD by NYPL's clearance work, but you should re-check the `rightsURI` field per item if you're redistributing. |
| **Some fields are noisy** | The CSV flattening loses some structure; dates are partial; subjects sometimes have a free-text + a URI. Expect ~5-10% dirty records. |
| **Big download** | The full JSON dump is ~2-3 GB. NDJSON is line-by-line streamable. |
| **GitHub repo is "public archive" mode** | I should check this — if NYPL has marked the repo read-only, that's another signal that no refresh is coming. (The repo's last commit was 2017, suggesting it's been frozen for years.) |

## What we use the data for

- **Map view**: historical New York / US / world maps as a base
  layer toggle (toggle "show 1850s maps" → see how the NYC shoreline
  changed)
- **Story view**: chronological exploration of a single topic
  (e.g. "NYC restaurant menus 1850-1925") with item-level deep links
  to the high-res image
- **Time series**: `dateCreated.year` × count of items × subject →
  show how NYPL's collection reflects historical attention
  (immigration, industrialization, etc.)
- **Network**: shared `contributor` × item → author network
- **Compare**: NYPL's "subject=immigration" set vs Library of
  Congress's, vs Internet Archive's

## See also

- [`nypl-repo-api.md`](nypl-repo-api.md) — the deprecated API this
  dump replaces
- [`dpla-bulk.md`](dpla-bulk.md) — the more-current alternative
  channel (covers all NYPL metadata, not just PD)
- [`owid-datasets.md`](owid-datasets.md) — same CC0 bulk-dump
  pattern (OWID's `owid-datasets` repo)
- [`nasa-earthdata.md`](nasa-earthdata.md) — same "API + bulk
  archive" pattern (NASA's CMR + Earthdata Cloud)
- [`civicus-monitor.md`](civicus-monitor.md) — same
  "structured-data release under a public license" pattern

## License of this connector note

`connectors/nypl-publicdomain-bulk.md` is dedicated to the public
domain under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

