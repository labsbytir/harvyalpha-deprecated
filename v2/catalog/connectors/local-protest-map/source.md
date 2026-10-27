# Data Culture Group — local-protest-map (REFERENCE, not a connector)

Key: `n/a — reference implementation, not a data source. Do not ingest.`
Endpoint: `n/a`
Auth: n/a
Format: n/a

Documentation:
- Article: https://medium.com/data-culture-group/try-this-tool-to-map-protests-for-local-news-storybench-7f4eaa0ab006 (originally on Storybench, 2025-05-08)
- Live demo: https://dataculture.northeastern.edu/local-protest-map/
- Source code: https://github.com/dataculturegroup/local-protest-map
- License: **NOASSERTION** (no LICENSE file in the repo) — pattern only, do not fork

## What it is

A small static Leaflet + Svelte tool built by **Rahul Bhargava** at
Northeastern's **Data Culture Group** (College of Arts, Media and
Design). The tool is a **DataWrapper-style embeddable map** of recent
local US protests, designed to be dropped into a local-news story via
`<iframe>`. It is a **presentation tool**, not a data source.

## Why we do NOT add it to `sources.yaml`

| Reason | Detail |
|---|---|
| **Not a data source** | The tool reads from JSON files that the author manually re-exports from ACLED and Harvard CCC each week. It does not publish a feed. |
| **License is NOASSERTION** | The repo has no LICENSE file. We can't legally redistribute the code under our own name. We can **read it for inspiration** but not fork or vendor it. |
| **Single author, 0 stars, 0 forks** | Worth reading once, not a maintained project to depend on. |

## What it IS useful for (3 things)

### 1. A Svelte + Leaflet reference for our own Map view
- The repo is small (~26 KB), Svelte 5, Leaflet 1.x, Stadia Maps base
  layer, no backend — exactly the "static asset + minimal Svelte"
  pattern we want for the 6 dashboard views in `docs/dashboard-design.md`.
- Worth reading for: how they apply a small random "bump" to
  coincident lat/lons (so overlapping events stay visible) and how
  they wire a static CSV/JSON dataset into a Leaflet `L.geoJSON` call.
- **Do not** copy the bump function into our code without documenting
  it (or it could look like we are faking data provenance).

### 2. The 95% Media Cloud ↔ ACLED empirical finding
Rahul Bhargava sampled stories from the **Media Cloud** press corpus,
looked up each story's referenced protest, and checked whether that
protest had a matching row in **ACLED**:

> "I reviewed every story in the Media Cloud corpus to identify which
> ACLED event it was about (linking it by the unique `event_id_cnty`
> provided from ACLED). Just two protests were in the Media Cloud
> dataset that did not have a related ACLED entry, both small events
> reported by university student-run news sites. 95% of the sample I
> pulled from the basic Media Cloud query were already in ACLED,
> leading me to believe it was a trustworthy source for a list of
> protests."
>
> — [Source: storybench.org / Medium, 2025-05-08][article]

The evaluation sheet is on Google Sheets:
https://docs.google.com/spreadsheets/d/1KWI7kUK0ZLZJs2SJl5FulZX_sKJRzhqO0CJPJvbzPL4/

**This is the most useful single finding in the article.** It tells us:

- **ACLED is ~95% recall against press coverage of US protest events.**
  This validates our use of ACLED as the **primary** US-unrest source
  in `sources.yaml` (tier 1, axis `unrest`).
- **Media Cloud press coverage tracks ACLED**, not the other way
  around. The 5% gap is mostly small university-student events, not
  ACLED blind spots. So we can use Media Cloud as a *cross-source
  check* on ACLED completeness, not a substitute for it.
- **A `event_id_cnty` join key** is what makes the cross-source match
  possible. We should preserve ACLED's `event_id_cnty` in our
  `osint.datasets.dataset_fingerprint` resolver output so Media Cloud
  (and any other press-source fetcher we add later) can join back to
  ACLED.

**Action**: when the ACLED fetcher lands in `ingest/fetchers/acled.py`,
it should preserve `event_id_cnty` as a `payloads.extras.event_id_cnty`
field, not collapse it into a hash. See `ingest/resolver.py` for the
fingerprint rules.

### 3. Stadia Maps as a tile-provider alternative
- The tool uses **Stadia Maps** (https://stadiamaps.com/products/maps/map-styles/)
  as its base layer: **200,000 free tile hits / month** across all uses,
  then paid. Bhargava notes he could swap providers with one line via
  Leaflet.
- For our dashboard, the candidates are:
  - **MapLibre + free OSM tiles** (zero cost, no rate limit if you run
    your own tile server, but quality varies by region)
  - **Mapbox** (free tier: 50k loads/mo, then $5/1k)
  - **Stadia Maps** (200k free/mo, then paid — sweet spot for
    low-traffic newsroom use)
  - **Carto basemaps** (free for non-commercial)
- Recommendation for v1: **MapLibre + a self-hosted OSM tile mirror**
  for the prod path, **Stadia Maps** as the fallback if the mirror is
  down. Track in `docs/dashboard-design.md` §5 when we get to the
  Map view.

## Source identification

| Field | Value |
|---|---|
| Source title | "Try this tool to map protests for local news" |
| Author | Rahul Bhargava, Northeastern University Data Culture Group |
| Published | 2025-05-08 (Storybench), 2025-05-09 (Medium republication) |
| URL | https://www.storybench.org/try-this-tool-to-map-protests-for-local-news/ |
| Canonical | https://medium.com/data-culture-group/try-this-tool-to-map-protests-for-local-news-storybench-7f4eaa0ab006 |
| Code | https://github.com/dataculturegroup/local-protest-map |
| Tools | Svelte, Leaflet, Stadia Maps, DataWrapper-style iframe embed |
| License (code) | NOASSERTION (no LICENSE file) |
| License (article) | ALL_RIGHTS_RESERVED (Medium default) |

## See also

- [`harvard-ccc`](harvard-ccc.md) — the Harvard CCC dataset the tool reads (also in `sources.yaml`)
- [`mediacloud`](../mediacloud.md) — Media Cloud, the press-coverage source the tool cross-references (also referenced in `sources.yaml` and the vault)
- [`realtime-osint-roadmap`](realtime-osint-roadmap.md) — ACLED's place in the broader real-time OSINT feed
- [`owid-browser-semantic-search`](owid-browser-semantic-search.md) — the other "pattern only, no license" reference in this vault
- `docs/dashboard-design.md` §5 — where the Svelte+Leaflet map view + Stadia Maps trade-off will land
- `ingest/credibility.py` — the 4-tier classifier (ACLED is statically tier 1; the 95% finding is a *cross-source* validation, not a source-tier change)
