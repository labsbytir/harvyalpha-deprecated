# OWID Page-2 repos: migrated, experimental, and frontend (mostly not for us)

This note groups the remaining 22 OWID repos from page 2 of the org listing. The single useful one — `owid/lc-reconcile` — has its own connector note. **The other 22 are mostly migrated to the ETL monorepo, frontend/CMS work, or third-party forks. They are not data sources for OSINT-Data.**

## The "migrated to ETL" group

These four repos have READMEs that literally say "use the ETL repo instead." The actual code/data is in `owid/etl`.

| Repo | Last push | Size | Status | What it's been replaced by |
|---|---|---|---|---|
| `owid/walden` | 2023-06-13 | 6 MB | "Migrated to etl/lib/walden" | `https://github.com/owid/etl/tree/master/lib/walden` — the data catalog |
| `owid/owid-repack-py` | 2023-11-01 | 0 MB | "Folded into ETL" | `https://github.com/owid/etl/tree/master/lib/repack` — Pandas memory types |
| `owid/owid-content` | 2025-04-08 | 17 MB | "No longer actively maintained" | Explorer config now in ETL database |
| `owid/owid-datasette` | 2024-07-09 | 0 MB | "Test to see if a read-only SQLite+Datasette instance is useful" | The actual Datasette instance is private; the SQLite DB is generated in another (private) repo |

**Verdict**: don't pull from these. For walden's catalog data, use `owid/etl` directly (the catalog is now a set of YAML files in `etl/lib/walden/`). For repack, just `pip install owid-catalog` which bundles it.

## The "frontend / CMS" group

Not data sources; not interesting for our pipeline.

| Repo | Last push | What it is | Useful? |
|---|---|---|---|
| `owid/slides` | 2024-11-26 | reveal.js template (357 MB of slide content) | No — presentation tool |
| `owid/owid-lab-search-autocomplete` | 2025-03-07 | Figma prototype for search UX (TypeScript) | No — design prototype |
| `owid/netlify-actions` | 2021-12-10 | Reusable Netlify build action (MIT) | No — CI action |
| `owid/owid-theme` | 2019-01-15 | WordPress theme | No |
| `owid/owid-wordpress` | 2020-09-22 | Headless WordPress instance (1 MB) | No — WordPress |
| `owid/owid-wordpress-admin` | 2019-09-17 | WordPress admin plugin (MIT) | No — WordPress |
| `owid/owid-feedback` | 2023-10-24 | Feedback form, Netlify Functions + Mailgun | No |
| `owid/owid-jupyter-demo` | 2021-07-09 | Jupyter demo | No — demo |
| `owid/owid.github.io` | 2022-01-27 | GitHub Pages org landing | No — landing page |
| `owid/africanindata.org` | 2018-07-20 | Static site about African dev (8 MB) | No — presentation |

## The "third-party fork" group

Things OWID forked from upstream and maintains with small customizations.

| Repo | Last push | What it is | Useful? |
|---|---|---|---|
| `owid/handsontable` | 2022-08-31 | HandsOnTable spreadsheet component (NOASSERTION, 160 MB) | No — third-party UI |
| `owid/react-horizontal-scrolling-menu` | 2022-09-01 | React horizontal menu (MIT) | No — third-party UI |
| `owid/doc-to-archieml` | 2022-09-28 | Google Docs → ArchieML (MIT) | No — internal CMS tool |

## The "internal tools" group

| Repo | Last push | What it is | Useful? |
|---|---|---|---|
| `owid/gdocs-addon` | 2024-08-26 | Google Docs Apps Script for ArchieML | No — internal CMS |
| `owid/importer-bp-statistical-review` | 2022-06-22 | One-off importer script for BP Statistical Review | No — one-off |

## The actual data-side note for page 2

The data from `owid/owid-content` (17 MB) and `owid/owid-datasette` (the SQLite DB) **are accessible** if you want them — `owid/owid-content` has the Explorer configurations in TSV form, and `owid/owid-datasette` has a `update.sh` script that fetches the latest SQLite DB from S3. But:

- The Explorer configs are now live in the ETL database (per their own README)
- The Datasette SQLite is "metadata only" (no actual data rows, per their own README) — useful for "find all pages that mention X" but not for the warehouse

**For our use case, the right path is to ingest directly from `owid/etl`** (the canonical source now) rather than these read-only archive repos.

## What's actually useful from page 2

**Just one repo**: [[connectors/owid-lc-reconcile]] — the country reconciliation service. Worth a real fetcher for our resolver. The rest of page 2 is "thanks for the historical record, OWID, but the work is now in `owid/etl`."

## The full OWID license story, complete (8 OWID-specific notes in the vault)

| Repo | License | Status | Use? |
|---|---|---|---|
| **`owid/data-api`** | **MIT** | ✅ fork | Backend API surface (FastAPI + DuckDB → swap to ClickHouse) |
| **`owid/tech-radar`** | **MIT** | ✅ fork | Tech-radar visualization for our own org |
| **`owid/cartograms`** | **ISC** | ✅ fork | Population cartograms |
| `owid/co2-data`, `owid/energy-data`, `owid/covid-19-data`, `owid/poverty-data` | CC-BY-4.0 (data only) | ✅ use | Direct CSV data with attribution |
| `owid/owid-datasets` | No license on code; data is CC-BY-4.0 | ⚠️ data only | 766 archived CSVs |
| `owid/chartbook` | No license on code; data is public | ⚠️ data only | 16k inequality rows |
| `owid/orae-major-conflicts` | No license on code; data is public domain (US Gov) | ⚠️ data only | 1720–1985 conflict history |
| **`owid/lc-reconcile`** (this page) | No license; small code | ✅ use the pattern | Country reconciliation service |
| `owid/walden`, `owid/owid-repack-py`, `owid/owid-content`, `owid/owid-datasette` | n/a | Migrated to ETL | ❌ use the ETL monorepo instead |
| `owid/owid-grapher` | No free license | ❌ avoid | |
| `owid/owid-browser-semantic-search` | No license | ❌ avoid | |
| `owid/etl` | Open to read | ⚠️ read | Read for understanding, write your own version |

**Two of the "migrated" repos (walden, owid-content) and one of the "migrated" repos (owid-datasette) are not data sources** — they're just archives of the historical state of the ETL. The migration story tells us OWID has consolidated everything into `etl/`, which is the right pattern to mimic.
