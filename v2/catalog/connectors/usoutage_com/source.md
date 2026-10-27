# usoutage.com — WordPress scraper of PowerOutage.us (NON-CONNECTOR)

Key: `none`
Endpoint: `https://usoutage.com/` (no public API; WordPress scraping only)
Auth: `none`
Format: HTML (WordPress), with state-by-state pages `https://usoutage.com/{state-slug}/`

Documentation:
- Landing: https://usoutage.com/
- State pages: `https://usoutage.com/california/`, `https://usoutage.com/new-york/`, etc. (50 states + DC)
- Privacy policy: https://usoutage.com/privacy-policy/
- Powered by: WordPress + "Interactive Geo Maps" plugin
- Maintained by: "Powerus" (publisher name on the page) — ad-supported blog
- **No public data API exists.** The per-state tables are
  HTML-embedded data pulled from PowerOutage.us.

## ⚠️ This is a WordPress scraper, not a data source

`usoutage.com` is a WordPress site (built on the "Root" theme
with the "Interactive Geo Maps" plugin) that **scrapes state-level
outage data from PowerOutage.us** and republishes it on
50+ per-state pages with a US map widget on the front page. The
per-state pages have a consistent format:

- State name (e.g. "California")
- Customers Tracked (e.g. `15,385,174` for CA, `8,721,196` for NY)
- Customers Out (e.g. `734` for CA, `1,212` for NY)
- "Last Updated" timestamp
- "View All" link to PowerOutage.us

The map widget on the front page (`map_13450`) is a JS overlay
that color-codes each state by its `Customers Out` count, with
a tooltip showing the per-state breakdown. The state polygons
come from `cdn.amcharts.com/lib/4/geodata/usaAlbersHigh.js` (the
AmCharts US Albers projection), and the per-state data is
embedded as a JS array of objects:

```js
{"name":"California","id":"US-CA","tooltipContent":"State name: <b>California</b><br>Customers Tracked: <b>15,385,174</b><br>Customers Out: <b>734</b>","content":"https://usoutage.com/california/","useDefaults":"0","source":"manual_entry","action":"open_url","fill":"#1976D2","hover":"#64B5F6"}
```

The `tooltipContent` is the real-time per-state data, refreshed
periodically. The "source": "manual_entry" field is misleading —
the data is from PowerOutage.us, not entered by hand.

## Why we don't ingest this

| Reason | Detail |
|---|---|
| **No public API** | The whole site is HTML scraping. The map widget's data is embedded in a JS object, not exposed as a JSON endpoint. |
| **Ad-supported, not a real publisher** | The site is a content / ad play, not a utility data source. They monetize traffic, not data. |
| **PowerOutage.us is the underlying source** | Going direct to [[poweroutage_us]] is faster, more accurate, more granular (county + utility + state), and gives you API access. |
| **ToS is unclear** | There's no documented permission to scrape usoutage.com. PowerOutage.us's ToS governs their data; usoutage.com's ToS is not visible. |
| **State polygons are third-party** | The map uses AmCharts geodata, not the usoutage.com's data. |

## The "Powerus" publisher and the "Interactive Geo Maps" plugin

The site is published by "Powerus" (visible in the schema.org
metadata as `"@type":["Person","Organization"],"name":"Powerus"`)
and uses the "Interactive Geo Maps" WordPress plugin
(`https://usoutage.com/wp-content/plugins/interactive-geo-maps/`).
The plugin's map data is a JSON object embedded in the page's
HTML, with each state as one entry.

This is the same pattern many ad-supported "aggregator" sites use
to capture SEO traffic from "power outage" search queries while
not actually being a utility.

## When this site is useful (legitimately)

- **Discovery**: if a journalist is searching for a state-specific
  outage story, a Google search for "California power outage"
  might surface usoutage.com before PowerOutage.us itself. The
  per-state page is a useful landing page.
- **Verification**: the per-state numbers should roughly match
  PowerOutage.us. If they don't, that's a signal of either lag
  in the WordPress site or data quality issues in the scraping.
- **Historical**: usoutage.com has been live since at least 2024
  (the schema.org "datePublished" dates suggest 2024+ content).
  Internet Archive may have snapshots.

## What to use instead (the right path)

For OpenTIR-Data v1:

| Need | Right source |
|---|---|
| US shared-warehouse (free) | [[odin]] — ORNL+DOE, public OpenEnergyHub |
| US per-tenant (paid) | [[poweroutage_us]] — 96% US coverage, per-tenant API |
| US historical | [[eagle_i]] — 2014-2022 bulk CSV |
| US major events | [[doe_oe417]] — federal event reports |
| Canada (Quebec) | [[hydro_quebec_pannes]] — public REST API |
| Canada (other) | PowerOutage.us aggregator (95% Canada) + per-province utilities |
| UK | [[national_grid_uk_connected_data]] — public CKAN API |
| EU | [[entso_e_outages]] — transmission-level |
| Australia | [[aemo_outages]] — NEMWeb bulk |
| Japan | No public equivalent; [[od]] unofficial scraper (see connector note) |

## License of this connector note

`connectors/usoutage_com.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

