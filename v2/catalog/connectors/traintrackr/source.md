# Traintrackr (traintrackr.io) — REFERENCE, not a connector

Key: `n/a — commercial product company, no public data API. Do not ingest.`
Endpoint: `n/a`
Auth: n/a
Format: n/a

Documentation:
- Home: https://www.traintrackr.io/
- Data Sources page: https://www.traintrackr.io/data
- Setup: https://www.traintrackr.io/setup
- About: https://www.traintrackr.io/ (about section)
- GitHub: none (no public engineering org)

## What it is

**TrainTrackr** is a small Somerville MA / London UK product company
(2-person team, founded ~2018) that sells **physical LED maps** for
real-time transit visualization. They ship for MBTA Boston, MTA NYC
Subway, London Underground, and a few other networks. The hardware is
an ESP8266/ESP32-driven LED matrix that pulls live transit data and
lights up moving train markers. They sell direct to consumers
(typically $300-$700 per board) and also offer custom orders.

This is **not a data source** — they consume the same free / public
transit APIs we already have in our vault to drive their hardware. Their
/data page is a marketing page: "Use our data" (requires buying a
board), "Send us your data" (Coming Soon), or "Connect directly" (DIY
reprogramming of the ESP board).

## ⚠️ Why we deliberately do NOT add it to `sources.yaml`

| Reason | Detail |
|---|---|
| **Not a data publisher** | They don't publish a feed. They consume. |
| **No public API** | Their "data" is only accessible to board owners via their (private, un-documented) cloud service. The "Send us your data" link says "Coming Soon". |
| **Single-vendor commercial product** | ~2-person team, no GitHub org, no engineering blog about their data pipeline. Even if the API existed, depending on a startup for our warehouse would be a vendor risk. |
| **No reuse rights on the LED art** | Even if we wanted to copy their visual style, we'd be reverse-engineering their product. |

## What they're actually using (the data sources under the LED)

The Traintrackr product consumes the same free / public transit APIs
that we already have in our vault. Per their data page and the MBTA /
MTA / TfL official documentation, the public sources they tap into are:

| Board | Underlying free data source | Already in our vault? |
|---|---|---|
| Boston MBTA | `https://api.mbta.com/` (v3, free with key) | not yet, but covered by `geOps` (geOps aggregates MBTA) |
| NYC Subway MTA | `https://api.mta.info/` (GTFS-RT, free) | not yet; **`opensky`** is unrelated. **geOps** aggregates MTA. |
| London Underground | TfL Unified API (`https://api.tfl.gov.uk/`, free with key) | not yet; would be a future connector |
| Other networks | Various GTFS-RT feeds | mostly covered by **`geOps`** (425 feeds) |

So if we wanted the *same data Traintrackr shows on its LED boards*
inside our dashboard, we have two paths:

1. **Subscribe to geOps** (`connectors/geops.md`) — paid per-tenant
   key, but a turnkey unified API covering all the networks Traintrackr
   ships boards for.
2. **Wire up the agency APIs directly** (MBTA v3, MTA, TfL) — free,
   but ~6-10 small fetchers per region. Worth doing for a few major
   networks (MBTA, MTA, TfL, BART, SBB, SNCF) and using the geOps
   Stops API as a unified stop-lookup service.

## What we should actually do

For a v1 dashboard focused on the **12 axes** in our schema
(`unrest / climate / conflict / economic / info_environment / security /
health / energy / migration / sanctions / cyber / governance`),
transit data is **not on the critical path**. When a tenant asks for
"real-time vehicles on a map":

1. Point them at **`connectors/geops.md`** if they want a single
   turnkey paid key.
2. Else wire **`ingest/fetchers/mbta.py`** + **`mta.py`** + **`tfl.py`**
   as three separate small fetchers, each ~50 lines, free, with
   per-tenant keys via env var.
3. Use **`overpass-api`** + **`openrailwaymap`** for the *track
   geometry* layer underneath the vehicles.

The Traintrackr LED-board product is, conceptually, the same pipeline
we'd build, but frozen in hardware and locked to ~5 networks. Useful
as a *reference* for what a polished consumer product looks like
in this space, not as a data source.

## How this note was sourced

| Step | Result |
|---|---|
| Probe `https://www.traintrackr.io/` | 200, marketing landing page |
| Probe `https://www.traintrackr.io/data` | 200, three options: use their data (product-gated), send your data (coming soon), or connect directly (DIY) |
| Probe `https://www.traintrackr.io/api` | Not a documented endpoint |
| GitHub search for "traintrackr" | No public engineering org |

## See also

- [`geops`](geops.md) — the closest free/paid turnkey alternative for the same data
- [`openrailwaymap`](openrailwaymap.md) — the free OSM-based rail geometry layer to put *underneath* a real-time vehicle map
- [`overpass-api`](overpass-api.md) — the data source for OSM rail tagging
- [`transitland`](https://www.transit.land/) — GTFS feed registry (1,200+ feeds)
- `traintrackr` is documented here in the "Reference implementations (pattern only, not a data source)" section of `Welcome.md` if you want to cite it as a *design pattern* for the live-transit dashboard view.
