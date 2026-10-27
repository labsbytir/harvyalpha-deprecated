# Human Rights Watch (hrw.org)

Key: `none — research/advocacy org, no public data API. Documented as non-connector.`
Endpoint: `n/a` (intentionally empty)
Auth: n/a
Format: n/a

Documentation:
- Home: https://www.hrw.org/
- API root probed: `https://api.hrw.org/` (network error on probe; not a documented endpoint)
- RSS probed: `https://www.hrw.org/sites/default/files/rss-feed/news.rss` (404)
- About HRW data: https://www.hrw.org/about/our-data (no machine-readable bulk export; the page describes the survey methodology only)
- GitHub: HRW does **not** have a public engineering or data GitHub org

## What it is

**Human Rights Watch** is the second-largest international human-rights
research and advocacy organisation (after Amnesty). Their primary
output is **long-form investigative reports** and **press releases**,
not data.

## ⚠️ Why we deliberately do NOT add this to `sources.yaml`

| Reason | Detail |
|---|---|
| **No public data API** | `api.hrw.org` does not resolve to a documented endpoint. There is no `v1/` or `/api/` route. |
| **No working RSS** | `hrw.org/sites/default/files/rss-feed/news.rss` returns 404 (the legacy RSS path is gone). HRW has not published a replacement feed URL as of 2026-09. |
| **No bulk export** | All content lives in HTML pages and PDFs (`https://www.hrw.org/news/`). No machine-readable schema, no CKAN, no OData. |
| **Press releases as a proxy are too noisy** | HRW publishes ~5-10 items/day, mostly long-form. Like Amnesty, no lat/lon, no structured event schema, no actor coding. Already covered (better) by **External APIs**, **Civicus Monitor**, and **ACLED**. |

## What to use instead (free, open, machine-readable)

For everything HRW covers, prefer:

- **Civic-space ratings by country** → [`civicus-monitor`](civicus-monitor.md) (CC-BY-SA 4.0, RSS + HTML)
- **Conflict / civilian-violence events** → **ACLED** (academic tier; see `realtime-osint-roadmap.md`)
- **Press / civil-liberties press releases** → **External APIs DOC 2.0** (already in `sources.yaml`)
- **Sanctions / designated persons** → **OpenSanctions** + OFAC SDN (see `realtime-osint-roadmap.md`)

## How to use HRW content the right way

1. **Do not** try to scrape `hrw.org/news/` (their site is JS-heavy and has aggressive anti-bot).
2. **Do** subscribe to the **HRW email newsletter** for human reading.
3. **Do** ingest **Civicus Monitor** (this vault, `civicus-monitor.md`) and **ACLED** to cover the same evidentiary space with structured fields.
4. **Do** link HRW **report URLs** in `payloads.extras` when ingesting related events from another source, as provenance.

## See also

- [`amnesty`](amnesty.md) — same pattern (research/advocacy org, no data API) with the same workaround
- [`civicus-monitor`](civicus-monitor.md) — the actual free data publisher for this space
- [`realtime-osint-roadmap`](realtime-osint-roadmap.md) — ACLED, RSF, HRDAG, OpenSanctions
- [`no-public-api`](no-public-api.md) — the master "research/advocacy orgs that have no public data API" note
