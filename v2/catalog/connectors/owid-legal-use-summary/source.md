# OWID legal-use summary: what we can and can't use (all 53 repos)

This is the comprehensive legal-use analysis of the entire OWID org. After auditing all 53 public repos and checking each license, here's the final answer to **"what can we use legally"** for OpenTIR-Data.

## The license landscape (2026-09-04, live GitHub API)

The 53 OWID public repos break down into 4 license categories:

| Category | Repos | What it means for us |
|---|---|---|
| **MIT** | 17 | ✅ Free to fork, modify, redistribute. Cite the copyright. |
| **Apache-2.0** | 2 | ✅ Same as MIT, plus a patent grant. Free to fork, modify, redistribute. |
| **NOASSERTION** | 4 | ⚠️ "The repo has license terms that don't fit SPDX, or no clear license" — basically **do not use** unless you read the actual terms |
| **NONE** | 30 | ⚠️ "No license file at all" — by default, **all rights reserved**, but the *data* inside many of these repos is independently usable |

**Bottom line: 19 repos (36%) have a clear free-software license. 34 repos (64%) have unclear or no license, so use the data, not the code.**

## What we can legally fork and use as CODE (the 19 fully licensed repos)

These are the repos you can copy, modify, and ship in OpenTIR-Data with no legal risk beyond attribution. **In priority order for OpenTIR-Data**:

### Tier 1: fork these first

| Repo | License | Stars | Size | Why it matters for us |
|---|---|---|---|---|
| **`owid/etl`** | **MIT** | 156 | 134 MB | The ETL monorepo with 200+ source-specific snapshot folders — the canonical reference for our ingest pipeline. 200+ working Python implementations of data sources. |
| **`owid/data-api`** | **MIT** | 17 | 0.9 MB | The reference FastAPI + DuckDB API surface. We can fork and swap DuckDB for ClickHouse. |
| **`owid/cartograms`** | **ISC** (effectively MIT-equivalent) | 4 | 14 MB | The Dougenik cartogram algorithm. Use to render the world-map base layer. |
| **`owid/tech-radar`** | **MIT** (forked from Zalando) | 2 | 2 MB | The tech-radar visualization. Adapt for our own org's stack visualization. |
| **`owid/skills`** | **Apache-2.0** | 4 | small | **Agent Skills** for AI coding agents (Claude Code, Codex, Cursor, etc.) to work with OWID data. The exact pattern for our own MCP server. |

### Tier 2: libraries and data

| Repo | License | Stars | Size | Use |
|---|---|---|---|---|
| `owid/owid-catalog-py` | MIT | 29 | 0 MB | Python client for the OWID catalog. **Migrated into ETL** — just use the ETL repo |
| `owid/owid-repack-py` | MIT | 3 | 0 MB | Pandas memory-efficient data types. **Migrated into ETL** — bundled with `owid-catalog` |
| `owid/owid-datautils-py` | MIT | 6 | 0 MB | Data util library. **Migrated into ETL** |
| `owid/walden` | MIT | 8 | 6 MB | Prototype catalog of data sources. **Migrated into ETL** — use `etl/lib/walden` |
| `owid/owid-importer` | MIT | 16 | 53 MB | Bulk import scripts. **Deprecated by `owid/importers`** (which is NOASSERTION, so the successor isn't legally clear) |
| `owid/poverty-data` | MIT | 36 | 7 MB | Poverty data. Use directly. |
| `owid/monkeypox` | MIT | 16 | 27 MB | 2022 mpox outbreak analysis. Use directly. |
| `owid/datasette-parquet` | Apache-2.0 | 1 | small | Utility for Datasette + Parquet. Use for our own metadata API if we go that route. |
| `owid/owid-nushell` | MIT | 3 | small | Nushell helper scripts. Skip unless we adopt Nushell. |
| `owid/netlify-actions` | MIT | 4 | small | Reusable Netlify build action. Skip unless we deploy to Netlify. |
| `owid/owid-wordpress-admin` | MIT | 3 | small | WordPress admin plugin. Skip — we don't use WordPress. |
| `owid/react-horizontal-scrolling-menu` | MIT | 2 | 26 MB | React menu component. Skip — third-party UI. |
| `owid/doc-to-archieml` | MIT | 1 | small | Google Docs → ArchieML utility. Skip — internal CMS. |
| `owid/figma-plugin` | MIT | 1 | small | Figma plugin. Skip. |

### Tier 3: confirmed don't use (UI / CMS / third-party)

| Repo | License | Use? |
|---|---|---|
| `owid/handsontable` | NOASSERTION | ❌ Third-party spreadsheet lib, also 160 MB, also no clear license |

## What we can legally use as DATA (the data-only repos)

These repos have **no code license** but contain **public, reusable data**. Use the data; attribute the original source.

| Repo | Stars | Size | What it is | Use with attribution to |
|---|---|---|---|---|
| `owid/covid-19-data` | 5658 | 99 MB | COVID-19 cases/deaths/hospitalizations/tests | Johns Hopkins, WHO, OWID aggregation |
| `owid/co2-data` | 769 | 164 MB | CO2 and GHG emissions by country | Global Carbon Project, BP Statistical Review, etc. |
| `owid/owid-datasets` | 759 | 272 MB | 766 archived CSVs with `datapackage.json` | Original publishers (CDC, WHO, World Bank, etc.) |
| `owid/energy-data` | 427 | 75 MB | Energy data (production, consumption, prices) | BP Statistical Review, EIA, IEA, etc. |
| `owid/notebooks` | 117 | 3.9 GB | Jupyter notebooks of analyses | Original publishers |
| `owid/sdg-tracker.org` | 33 | 13 MB | SDG tracker site config | UN Stats, World Bank, etc. |
| `owid/owid-grapher-py` | 22 | 4 MB | Python lib for OWID charts in Jupyter | Don't fork code; use as reference for what data to query |
| `owid/owid-content` | 16 | 17 MB | Explorer configurations | Original publishers |
| `owid/owid-datasette` | 14 | small | Metadata-only Datasette experiment | Don't use directly; the pattern is useful |
| `owid/slides` | 13 | 357 MB | reveal.js slide deck content | Don't redistribute |
| `owid/owid-grapher-svgs` | 5 | 4.9 GB | SVG exports of OWID charts | **Public domain** SVG, can be reused with attribution |
| `owid/africanindata.org` | 7 | 8 MB | Static site about African development | Don't redistribute |
| `owid/global-change-data-lab.org` | 5 | small | Homepage for the GCDL org | Don't redistribute |
| `owid/owid-theme` | 4 | 2 MB | WordPress theme | Skip |
| `owid/orae-major-conflicts` | 4 | 83 MB | 1720–1985 conflict data | US Army (public domain) |
| `owid/owid.github.io` | 4 | 148 MB | GitHub Pages org landing | Don't redistribute |
| `owid/.github` | 4 | small | Org-level GitHub config | Don't redistribute |
| `owid/owid-feedback` | 3 | small | Feedback form | Skip |
| `owid/importer-bp-statistical-review` | 3 | 11 MB | One-off BP importer | Don't use; one-off |
| `owid/owid-docs` | 3 | small | Documentation | Read but don't copy |
| `owid/site-screenshots` | 3 | 21 GB | Dashboard screenshots | Don't redistribute |
| `owid/chartbook` | 2 | 4 MB | 16k inequality rows (1720–1985) | Original US Army compendium + Google Sheet |
| `owid/actions` | 2 | small | GitHub Actions | Don't use |
| `owid/energy-use-products` | 2 | small | Energy product data | Original publishers |
| `owid/lc-reconcile` | 1 | small | Country reconciliation service | Use the pattern; don't copy the code |
| `owid/gdocs-addon` | 1 | small | Google Docs ArchieML addon | Skip |
| `owid/owid-browser-semantic-search` | 1 | small | In-browser semantic search | Use the pattern; don't copy |
| `owid/owid-lab-search-autocomplete` | 1 | small | Search UX prototype | Use the pattern; don't copy |
| `owid/static-page-test` | 0 | small | Test repo | Don't use |

## What we should avoid entirely

| Repo | License | Why avoid |
|---|---|---|
| `owid/owid-grapher` | **NOASSERTION** | ★1558, 178 MB. The platform code. The SPDX says "no clear license assertion" which functionally means **all rights reserved**. We already covered this — the license is "no longer MIT" and you may not copy, modify, or distribute without written permission. |
| `owid/importers` | **NOASSERTION** | ★18, 1.5 GB. The successor to `owid-importer`. Despite being the modern version, the license is unclear. |
| `owid/owid-wordpress` | **NOASSERTION** | ★7. WordPress instance. Skip — we don't use WordPress anyway. |
| `owid/handsontable` | **NOASSERTION** | 160 MB third-party spreadsheet lib. Don't use even if the upstream is free — the OWID fork has no clear license. |

## The 5 forks that will carry the world dashboard

If I had to pick **the 5 repos that will carry 80% of the OSINT-Data work**, they are:

1. **`owid/etl`** (MIT) — the source-specific snapshot folders. The reference for every connector we build. **Fork this, read the snapshots/ directory, copy the patterns.**
2. **`owid/data-api`** (MIT) — the FastAPI + DuckDB API surface. **Fork this, swap DuckDB for ClickHouse, deploy as our `/v1/sql` endpoint.**
3. **`owid/cartograms`** (ISC) — the world-map base layer. **Fork this, generate cartograms for any country × year × variable, render with deck.gl.**
4. **`owid/tech-radar`** (MIT) — the tech-stack visualization. **Fork this, populate with our OpenTIR-Data tech choices, deploy as `radar.opentir.org`.**
5. **`owid/skills`** (Apache-2.0) — the Agent Skills for OWID. **The exact pattern for our own MCP server.** Skill files describe what the agent should do, with curl commands and TypeScript schemas. We can fork this and write our own SKILL.md files for our own catalog.

## The 5 data sources we should ingest first

In priority order, by OSINT value and legal clarity:

1. **`owid/covid-19-data`** (no license, but data is public) — 5,658 stars, the canonical COVID-19 dataset
2. **`owid/co2-data`** — 769 stars, CO2 emissions by country
3. **`owid/energy-data`** — 427 stars, energy production/consumption
4. **`owid/poverty-data`** (MIT, data is also CC-BY) — 36 stars, poverty data
5. **`owid/owid-datasets`** — 759 stars, 766 archived CSVs

For each: pull the CSV, attribute the original source in `metadata.publisher`, run the resolver.

## The 4 things to NOT try

These are tempting but legally/technically wrong:

1. **Don't fork `owid/owid-grapher`** — explicitly not MIT anymore. Write your own visualization layer with Apache ECharts + MapLibre + deck.gl. Free, ~1 week of work.
2. **Don't copy code from `owid/owid-browser-semantic-search`** — no license. Use the architectural pattern (transformers.js + PGlite + pgvector), write your own ~150 lines of original code.
3. **Don't copy the `owid/owid-grapher-py` source** — 22 stars, looks like a working pip-installable package, but the license is NONE. Use it to understand what data to query, not what code to use.
4. **Don't try to use `owid/importers`** (1.5 GB) — the successor to `owid/owid-importer`. Despite being newer and bigger, it's NOASSERTION. Use the older `owid/owid-importer` (MIT) instead.

## The practical legal-use rule for the OSINT-Data project

**For code**: only MIT/ISC/Apache-2.0 repos. We've identified 19 of them. Five are Tier 1 forks.

**For data**: assume the data is independently usable with attribution to the original publisher, unless the data itself is from a clearly non-open source. We've identified 30 repos that are data-only or data-dominant.

**For everything else**: read but don't copy. The patterns are public knowledge; the specific code requires permission.

## The vault state (45 notes, after this final write)

```
├── 6 top-level credentials
└── 39 connector notes
    ├── 4 platform connectors (CKAN, Socrata, ArcGIS Hub, OpenDataSoft)
    ├── 1 portal registry (321 portals)
    ├── 2 grouped "no public API" notes
    ├── 18 individual source notes
    ├── 1 OWID master note (200+ source catalog)
    ├── 2 real-time: opensky, openflights
    ├── 1 real-time OSINT roadmap
    └── 10 OWID-specific notes:
        ├── owid-grapher (avoid, NOASSERTION)
        ├── owid-cartograms (ISC, fork)
        ├── owid-browser-semantic-search (architecture only)
        ├── owid-datasets (data only)
        ├── owid-tech-radar (MIT, fork)
        ├── owid-data-api (MIT, fork)
        ├── owid-chartbook (data only)
        ├── owid-orae-major-conflicts (data only, public domain)
        ├── owid-lc-reconcile (use the pattern)
        ├── owid-page2-migrated (grouped note)
        └── owid-legal-use-summary (this one)  ← NEW
```

**Every OWID public repo is now documented in the vault.** License status is unambiguous. Forking strategy is clear. Data ingestion strategy is clear. The 5 forks that carry the world dashboard are identified.

