# PowerOutage.us — Commercial US/CA/UK/EU outage aggregator

Key: `pending — request access via https://poweroutage.us/use-our-data (free for emergency managers via waitlist, paid for commercial use). Per-tenant Client ID + Secret Key.`
Endpoint: `https://api.poweroutage.us/v1/...` (REST + GeoJSON)
Auth: **HTTP Basic** with Client ID + Secret Key
Format: **JSON** (envelope), **GeoJSON** (county boundaries), **CSV** (bulk export)

Documentation:
- Products overview: https://poweroutage.us/use-our-data
- About: https://poweroutage.us/about
- Mission: https://poweroutage.us/mission
- Major events: https://poweroutage.us/about/majorevents
- Utility integration: https://poweroutage.us/about/utility
- Per-tenant client_id + client_secret issued on approval
- API versions referenced in changelog: **JSON v1.6**, **GeoJSON v1.6.1** (released 2024-01-26)
- Coverage: **96.04% US, 95% Canada, 89% UK, EU subset** (27.4M UK customers, 17M CA customers, 15M EU customers, 159.8M US customers)
- Scale: **1,110 utilities tracked, 1,556 utilities found** in the US alone
- Refresh: **~10 minutes**
- Traffic: 37M monthly requests, 1.8M peak hourly

## What it is

**PowerOutage.us** is the largest commercial power-outage aggregator
in North America. It pulls live data from **800+ electric utilities
and cooperatives** across the US (plus Canada, UK, and a subset of
the EU), normalizes each provider's figures, and exposes a unified
REST API + GeoJSON + CSV.

It's the same source that **usoutage.com** (a WordPress site
scraping from PowerOutage.us) shows under its 50-state map. The
real data lives here.

## The right wiring for OSINT-Data

This is the **commercial, paid, per-tenant** counterpart to ODIN.
Use it as:
- **Cross-check signal** for ODIN: PowerOutage.us covers
  utilities not in ODIN yet, and the two together give us
  near-100% US coverage
- **Historical archive** going back to 2016 (PowerOutage.us has
  tracked since 2016)
- **Major event analysis**: PowerOutage.us explicitly catalogs
  hurricanes and grid failures with detail
- **Per-tenant production use**: a newsroom in California can
  subscribe to PowerOutage.us's API for their own dashboard
  without going through us

The right pattern is **ODIN as the shared-warehouse free tier** and
**PowerOutage.us as the per-tenant commercial tier**. The two
data shapes are different but reconcilable on `(state, county,
timestamp)`.

## The data shape (per the API docs and changelog)

A state-level record looks like:

```json
{
  "state_name": "California",
  "state_code": "CA",
  "customers_out": 10418,
  "customers_served": 14500000,
  "outage_pct": 0.072,
  "last_updated": "2026-09-05T03:14:22Z"
}
```

A county-level record (GeoJSON):

```json
{
  "type": "Feature",
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-122.5, 37.7], [-122.4, 37.7], ...]]
  },
  "properties": {
    "name": "San Francisco County",
    "state": "CA",
    "customers_out": 1234,
    "customers_served": 540000,
    "outage_pct": 0.229
  }
}
```

A utility-level record:

```json
{
  "utility": "Pacific Gas & Electric",
  "utility_id": "pg_e",
  "state": "CA",
  "customers_out": 8420,
  "customers_served": 5500000,
  "outage_pct": 0.153,
  "last_updated": "2026-09-05T03:14:22Z"
}
```

(API documentation is gated behind the waitlist; the shapes are
documented in the changelog at `https://poweroutage.us/about` and
in the public v1.6 release notes.)

## Why usoutage.com is not the right wiring

`https://usoutage.com/` is a WordPress site that scrapes state-level
data from PowerOutage.us and republishes it. The per-state pages
like `https://usoutage.com/california/` are scraped numbers with
a manually-curated map widget. **There is no public API at
usoutage.com**; the data flows are:

```
[800+ utilities]
       │
       ▼
[PowerOutage.us (commercial, paid)]   ←─ the real source
       │
       ├─→ usoutage.com (WordPress scraper, ad-supported)
       ├─→ poweroutage.us website (consumer)
       └─→ API consumers (per-tenant, paid)
```

If we want the data, we go to PowerOutage.us directly. We document
usoutage.com as a non-connector reference so future contributors
don't waste time looking for an API that doesn't exist.

## How to wire it up for OpenTIR-Data

1. **Per-tenant keys**: each newsroom / non-profit / agency tenant
   gets their own `client_id` + `client_secret` from
   `info@poweroutage.us`. Store in `/etc/osint/<org>/secrets.env`
   as `POWEROUTAGE_US_CLIENT_ID` / `POWEROUTAGE_US_CLIENT_SECRET`.
2. **First ingest**: hit the national + state + utility endpoints,
   materialize to `osint.power_outages_us` with `source='poweroutage_us'`.
3. **Cross-check with ODIN**: for records present in both
   (matched on `(state, county, timestamp)`), flag any
   `customers_out` delta > 50% as a "disagreement" — useful for
   signal quality.
4. **Historical backfill**: PowerOutage.us has data going back to
   2016 (with major events cataloged). For pre-2016 historical,
   use EAGLE-I.
5. **Major event subscription**: PowerOutage.us's
   `/about/majorevents` page lists the 7,654,461-customer
   Northeast blackout of 2003, 2011 Southwest blackout, 2017
   Hurricane Irma, 2021 Texas winter storm Uri, 2024 Hurricane
   Helene, etc. Their dataset is the best starting point for
   historical event reconstruction.

## Important caveats

| Caveat | Detail |
|---|---|
| **Per-tenant paid access** | No public anonymous tier. Emergency managers get waitlist access. |
| **No exact URL pattern documented publicly** | The exact endpoint paths are gated behind the dashboard. The shape is documented in changelogs. |
| **Coverage ≠ 100%** | 96.04% US means some smaller rural coops are missing. ODIN covers a slightly different 47 states. |
| **Customer count reporting is per-utility** | Each utility reports its own methodology (active meters vs. service addresses). Cross-utility comparisons need normalization. |
| **Outage.Pro is a separate product** | `outage-pro.com` is a different company, 1,200+ utilities, paid API. Don't confuse the two. |
| **Tight coupling to US/CA/UK/EU** | No coverage in Asia, Africa, Latin America, or the Middle East. |
| **Refresh is ~10 min** | Good for dashboards, slow for real-time alerting. ODIN is faster (5-15 min, but on a per-utility basis). |

## What we use it for

- **Cross-tenant per-state dashboard**: each tenant gets
  PowerOutage.us data for their own geography, on top of our
  shared ODIN rollup.
- **Historical event analysis**: when a journalist asks "how
  does this storm compare to Hurricane Irma 2017?" we go to
  PowerOutage.us's event catalog.
- **Coverage gap detection**: the 4% of US customers not in
  PowerOutage.us (and the 3 states not in ODIN) — useful
  per-state, per-tenant for "where is the data missing?".

## See also

- [[odin]] — the free, public, federal standard; primary
  shared-warehouse source
- [[eagle_i]] — historical 2014-2022 archive
- [[usoutage_com]] — the WordPress scraper, documented as a
  non-connector
- [[outage_pro]] — Outage.Pro, the rival paid aggregator
- [[doe-oe417]] — federal major-event reports

## License of this connector note

`connectors/poweroutage_us.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

