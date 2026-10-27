# Per-utility power outage maps — bespoke scrape pattern

Key: `none` (public web pages, no API)
Endpoint: per-utility outage map page (see table below)
Auth: `none`
Format: HTML (server-rendered or SPA) with embedded JSON for the map tile data

This is a **pattern** rather than a single source. Many US
utilities publish a public outage map on their website, with
per-county / per-circuit / per-customer-meter outage counts
updated every 5-15 minutes. Most do **not** have a documented
public API. The list below is the practical set of US utilities
with public outage maps and a per-utility scrape pattern.

## The pattern

For each utility:

1. Visit the outage map URL in a browser
2. Open DevTools → Network → XHR/Fetch
3. Find the JSON endpoint the map calls (e.g.
   `https://utility.com/arcgis/rest/services/Outages/MapServer/0/query`)
4. Note the geometry field, the field aliases, and the
   refresh interval
5. Build a small fetcher that polls the JSON endpoint every
   5-15 minutes, transforms the per-utility shape to our
   `osint.power_outages_us` schema, and stores it

The fetched JSON is typically one of:
- **Esri ArcGIS REST** (`/MapServer/0/query?where=1%3D1&outFields=*&f=json`)
- **REST API with GeoJSON FeatureCollection** (less common)
- **Server-rendered HTML** with embedded JSON (the National Grid
  NY pattern)

## Major US utilities with public outage maps

| Utility | URL | Data format | States served | Refresh |
|---|---|---|---|---|
| **National Grid NY** | `https://outagemap.ny.nationalgridus.com/` | Server-rendered HTML with embedded JSON, `outagemap.ny.nationalgridus.com/reports/{report-id}` | NY (upstate) | ~5 min |
| **National Grid MA** | `https://www.nationalgridus.com/MA-Home/Outage-Central/Outage-Map` | (similar to NY) | MA | ~5 min |
| **Duke Energy** | `https://outagemap.duke-energy.com/#/home` | SPA (ArcGIS MapServer query JSON, requires JS rendering) | NC, SC, FL, IN, OH, KY | ~10-15 min |
| **ConEdison (NYC)** | `https://www.coned.com/en/outage-map` | ArcGIS REST | NYC, Westchester | ~15 min |
| **PG&E (California)** | `https://www.pge.com/outages` | Mapbox + custom JSON | CA (Northern) | ~15 min |
| **Southern California Edison** | `https://www.sce.com/outage-center` | Mapbox + custom JSON | CA (Southern) | ~15 min |
| **San Diego Gas & Electric** | `https://www.sdge.com/residential/customer-service/outage-center` | Mapbox | CA (San Diego) | ~15 min |
| **Florida Power & Light** | `https://www.fpl.com/storm-center/outage-map.html` | Esri ArcGIS | FL (most of state) | ~15 min |
| **Georgia Power** | `https://outagemap.georgiapower.com/` | Esri ArcGIS | GA (most of state) | ~15 min |
| **Oncor (Texas)** | `https://www.oncor.com/outage-map` | Mapbox | TX (most of state) | ~15 min |
| **CenterPoint Energy (Texas)** | `https://www.centerpointenergy.com/en-us/residential/services/electric-utility/outage-watch` | Esri ArcGIS | TX (Houston area) | ~15 min |
| **AEP (American Electric Power)** | `https://www.aepohio.com/outages` | (varies by state) | OH, IN, KY, WV, VA, TN, OK, AR, TX | ~15 min |
| **ComEd (Illinois)** | `https://www.comed.com/outage-map` | Esri ArcGIS | IL (Chicago area) | ~15 min |
| **DTE Energy (Michigan)** | `https://www.dteenergy.com/outage-center` | Esri ArcGIS | MI (Detroit area) | ~15 min |
| **Consumers Energy (Michigan)** | `https://www.consumersenergy.com/outage-center` | Esri ArcGIS | MI (most of state) | ~15 min |
| **Xcel Energy** | `https://www.xcelenergy.com/outage-map` | (varies by state) | MN, WI, ND, SD, CO, TX, NM | ~15 min |

## What we found for the 3 utilities the user asked about

### 1. National Grid NY

- The marketing URL the user sent (`https://www.nationalgrid.com/us/ny`)
  is a **general landing page**, not the outage map.
- The actual outage map is at `https://outagemap.ny.nationalgridus.com/`.
- Updated every 5 minutes, "Map updates every 5 minutes" footer.
- Per-county view: `outagemap.ny.nationalgridus.com/reports/06c8ed31-48c2-4104-a9a2-41f844152ae3`
- Per-state view: `outagemap.ny.nationalgridus.com/reports/30d77369-2b12-4c0d-867d-31b2e7a4f18a`
- Format: server-rendered HTML with embedded JSON. No public
  API documented.
- **National Grid is a member of ODIN** for their MA
  operations, so ODIN covers parts of their territory.

### 2. Duke Energy

- The URL the user sent (`https://outagemap.duke-energy.com/#/home`)
  is the correct map.
- Pure JavaScript SPA. The actual data comes from an Esri ArcGIS
  MapServer at `https://services.arcgis.com/.../MapServer/0/query`
  with the URL accessible only after JS bootstraps.
- Updated every 10-15 minutes.
- 6 states: NC, SC, FL, IN, OH, KY.
- **Duke is participating in ODIN** for some of their
  territories, so ODIN may cover them.

### 3. usoutage.com (already covered in [[usoutage_com]])

The WordPress scraper of PowerOutage.us. Not a source itself; the
real data flows from [[poweroutage_us]].

## How to wire it up for OpenTIR-Data

The right pattern is:

1. **For shared warehouse**: use [[odin]] (47 states) +
   [[poweroutage_us]] (per-tenant, 96% US) for the
   **majority** of US coverage.
2. **For per-tenant dashboards**: for a newsroom in California,
   subscribe to PG&E + SCE + SDG&E directly for the highest
   resolution.
3. **For ODIN + PowerOutage.us gaps** (Hawaii, Alaska, smaller
   rural coops): fall back to per-utility scraping via the
   pattern above.
4. **For the 6-8 largest utilities not in ODIN**: build a
   per-utility fetcher. Start with ConEd (NYC), Duke, PG&E,
   Florida Power & Light, Georgia Power, Oncor (Texas). These
   6 cover ~50% of US customers not already in ODIN.

## Important caveats

| Caveat | Detail |
|---|---|
| **Per-utility shapes are bespoke** | Every utility has its own JSON field names, refresh cadence, and ToS. Build a fetcher per utility. |
| **JS-rendered SPAs need a real browser** | The Duke outage map and similar SPAs need either Playwright/Puppeteer or a reverse-engineered direct XHR call. |
| **ToS is unclear for scraping** | Most utility outage maps are "view only" — there's no documented API ToS. The pragmatic defense is "we're a non-profit OSINT project" but we should check each one. |
| **No authentication, but IP rate limits** | Some utilities Cloudflare-gate their outage maps. We should not hammer them at 1 req/sec; 5-15 min cadence is the right balance. |
| **Many "outage map" sites are dead** | Some utility maps have been offline for months (e.g. some smaller Texas coops after 2021's Uri). Always verify the endpoint before wiring it up. |
| **The map data is a snapshot, not an event log** | Most utility outage maps only carry the *current* state, not the event history. For history, use OE-417, EAGLE-I, or PowerOutage.us. |

## What we use it for

- **Per-state Map view**: when ODIN coverage is insufficient
  (Hawaii, Alaska, rural coops), per-utility fills the gap.
- **Tenant-specific dashboards**: a California newsroom wants
  PG&E, SCE, and SDG&E in their dashboard; a Texas newsroom
  wants Oncor and CenterPoint.
- **Per-tenant scrapers**: tenant's "data quality" view shows
  which sources agree (ODIN + per-utility + PowerOutage.us) and
  which disagree.

## See also

- [[odin]] — the primary US shared-warehouse source
- [[poweroutage_us]] — the commercial 96% US coverage
- [[usoutage_com]] — the WordPress scraper, documented as a
  non-connector
- [[doe_oe417]] — federal major-event reports

## License of this connector note

`connectors/per_utility_outage_maps.md` is dedicated to the public
domain under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

