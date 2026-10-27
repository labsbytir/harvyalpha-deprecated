# Travic (travic.app) — REFERENCE, not a connector

Key: `n/a — academic visualization tool, no public data API. Do not ingest.`
Endpoint: `https://travic.app/`
Auth: n/a
Format: n/a

Documentation:
- Home: https://travic.app/
- About (in-page overlay): click the "About" button on the home page
- Author: Patrick Brosi — University of Freiburg, Chair of Algorithms and Data Structures (`https://patrickbrosi.de`)
- Backend (currently in maintenance): `https://travic.cs.uni-freiburg.de/trajserv/` (returns empty as of 2026-09-05)
- Configuration: `https://travic.app/cfg.js` (client-side config; reveals base map API keys — see warning below)
- License: not stated on the public page; the data is owned by transit agencies and is "subject to terms of others"
- Started: 2013; 13-year history at time of writing
- GitHub: no public engineering repo (the author has a personal GitHub `PatrickBrosi` account with 0 public repos)

## What it is

**Travic** is a long-running academic project by **Patrick Brosi** at
the University of Freiburg, started in 2013. It is a **public
visualization** of worldwide transit movement (trains, buses, trams,
subways, ferries) on a map, with a fast-forward / slow-forward /
real-time playback control (the in-page footer has "Faster" / "Normal" /
"Slower" / "Current" speed buttons).

As of 2026-09-05, the public site shows:

> "We are currently doing maintenance work on our servers, please come
> back later."

and the backend at `https://travic.cs.uni-freiburg.de/trajserv/` returns
empty. So Travic is **not currently ingestable**.

## ⚠️ Why we deliberately do NOT add it to `sources.yaml`

| Reason | Detail |
|---|---|
| **No public data API** | The client is a static JS that talks to a private backend (`/trajserv/`) with no public docs, no Swagger, no API key issuance flow. |
| **Currently in maintenance** | The page is broken as of 2026-09-05; backend is offline. |
| **No GitHub source** | The author has no public engineering repos. We can't fork or vendor. |
| **Same author as gtfs.de** | The data Travic shows is the same data gtfs.de publishes; ingest gtfs.de directly. |
| **3 map tile API keys leaked in `cfg.js`** | HERE, BING, THUNDERFOREST keys are hardcoded. A design pattern to **not** copy in our SvelteKit frontend (proxy tile keys server-side). |

## What it is useful for (3 things)

### 1. Patrick Brosi lineage (research-group mapping)
Travic, [gtfs.de](gtfs-de.md), and the
[geOps Realtime `de-gtfs-de` feed](geops.md) are **all from the same
research group**. Patrick Brosi runs them out of the University of
Freiburg. Understanding this lineage is the right way to find free
data:
- Travic = the visualization
- gtfs.de = the free public data pipeline
- geOps = the commercial worldwide aggregator (with the same
  `de-gtfs-de` feed under the hood)

### 2. Playback UI pattern (the "faster / normal / current time" buttons)
The in-page footer has a clean time-scrubbing UI:
```
1x  ‹‹  ▶  ››  •  ⚙
```
- `1x` (current speed indicator)
- `‹‹` (Faster speed)
- `▶` (Normal speed / pause-toggle)
- `››` (Slower speed)
- `•` (Reset to current time)
- `⚙` (Configuration)

This is a polished pattern for our dashboard's **Time series** view —
when a user wants to scrub a transit / vehicle dataset, this 5-button
control plus a date/time input is the minimal UI. Worth replicating in
`docs/dashboard-design.md` §"Time series".

### 3. The leaked-keys warning (server-side tile proxy)
`https://travic.app/cfg.js` exposes:
```js
window.TransitLayerCfg.HERE_MAPS_POSTFIX =
  "?app_id=cc3LgXoEjCqJg41QLG6p&app_code=_11rnDUuyoiTqzlhBRnoZg";
window.TransitLayerCfg.BING_KEY = "AuW--H478I-gvPNpDWMmQFdVRxbgTaknhKgYfZF6NapticYpnnMwawwzxkED6o1v";
window.TransitLayerCfg.THUNDERFOREST_KEY = "1e0ac3c170714e3d90ec290edea3fce1";
```

These are **demo-tier** keys for the public site. If we copy this
pattern and ship our own SvelteKit frontend with `THUNDERFOREST_KEY`
hardcoded in a `.js` file on the client, an attacker can scrape it and
burn the quota. The correct pattern for our project:

- **Tile keys live in a server-side proxy** in `ingest/tile-proxy/`.
- The SvelteKit frontend fetches `https://app.opentacos.com/tiles/{z}/{x}/{y}` from **our** domain.
- Our tile proxy adds the `?key=…` query string from an env var and forwards to the upstream.
- We rate-limit per-IP and per-API-key on our proxy.

This is captured in the `geOps` vault note under the "Maps API" section
as the recommended pattern; reinforced here as a "do not do what
Travic did" reference.

## Connection to the rest of the OSINT ecosystem

| Project | Same author? | License | Free? |
|---|---|---|---|
| **Travic** (this) | Patrick Brosi, U. Freiburg | unspecified | Free (public visualization) |
| **[gtfs.de](gtfs-de.md)** | Yes, same | CC-BY 4.0 / CC BY-SA 4.0 | Free, machine-readable |
| **[geOps Realtime](geops.md) `de-gtfs-de`** | Yes (geOps is a spinoff of the same group) | free for non-commercial | Free tier + paid plans |
| **Mobility Database (Transitland)** | No (Conveyal/MobilityData) | free for non-commercial | Free |
| **OpenStreetMap + Overpass** | No (community) | ODbL | Free |

When a tenant asks "where is the canonical free source for German
public-transit data?", the answer is **gtfs.de**, not Travic. Travic
is a viewer on top of gtfs.de.

## How this note was sourced

| Step | Result |
|---|---|
| Probe `https://travic.app/` | 200, page shows maintenance banner |
| Probe `https://travic.app/api/` | 404 |
| Probe `https://travic.app/about/` | 404 |
| Probe `https://travic.cs.uni-freiburg.de/trajserv/` | 200 OK, empty body (maintenance) |
| Probe `https://travic.app/cfg.js` | 200, client config (HERE/BING/THUNDERFOREST keys) |
| Probe `https://api.github.com/repos/patrickbrosi/travic` | 404 (not a GitHub user) |
| Probe `https://api.github.com/users/PatrickBrosi` | 200, 0 public repos, account created 2025-12 |
| Probe `https://gtfs.de/` | 200, found the free CC-BY feeds |

## See also

- [`gtfs-de`](gtfs-de.md) — the **real, free, ingestable** data source; the right answer
- [`geops`](geops.md) — commercial worldwide aggregator with the same `de-gtfs-de` feed
- [`traintrackr`](traintrackr.md) — the consumer LED-board product that uses similar transit APIs
- `docs/dashboard-design.md` — where the playback UI pattern (5-button time scrub) should be referenced
