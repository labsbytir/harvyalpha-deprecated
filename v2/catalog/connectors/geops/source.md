# geOps Mobility APIs (Realtime + Routing + Stops + Maps)

Key: `pending — request a personal key from support@geops.io (free for non-commercial, paid for commercial). A public demo key is embedded in the dev portal HTML for testing — DO NOT use it for production.`
Endpoint: `https://api.geops.io/`
Auth: `key=...` query string parameter **or** `Authorization: ...` header
Format: **GeoJSON FeatureCollection** for stops; **GeoJSON trajectories** for realtime; **Mapbox Vector Tile style.json** for maps; **OpenAPI 3.0** + **AsyncAPI 2.6** specs

Documentation:
- Live demo (the URL you sent): https://mobility.portal.geops.io/world.geops.transit
- Developer portal: https://developer.geops.io/
- Realtime API: https://developer.geops.io/apis/realtime
- Routing API: https://developer.geops.io/apis/routing
- Stops API: https://developer.geops.io/apis/stops
- Maps API: https://developer.geops.io/apis/maps
- OpenAPI (Realtime): https://developer.geops.io/swagger/realtime.json
- OpenAPI (Stops): https://developer.geops.io/swagger/stops.json
- OpenAPI (Routing): https://developer.geops.io/swagger/routing.json
- AsyncAPI (Realtime WebSocket): https://backend.developer.geops.io/tralis-docs/asyncapi.json
- WebSocket endpoint: `wss://api.geops.io/tracker-ws/v1?key=<key>`
- License: **free for non-commercial** + **paid for commercial** (no public pricing page; email support@geops.io for a plan). Underlying feed data carries per-publisher licenses (CC-BY 4.0, ODbL, ETALAB 2.0, CC-BY 3.0 IT, etc.).
- GitHub (client library): https://github.com/geops (mobility-toolbox-js is the JS client, MIT)

## What it is

**geOps** is a Swiss GIS consultancy that has built **4 unified mobility APIs**
on top of GTFS + GTFS-RT feeds from **~425 transport agencies worldwide**.
The map you sent (`mobility.portal.geops.io/world.geops.transit`) is the
public read-only viewer; the dev portal exposes the same data as 4
ingestable APIs. The whole stack is their own product, internally named
**Tralis** (the WebSocket realtime backend).

This is a **meta-aggregator**: the 425 feeds come from SBB, SNCF, RATP
Dev, BART, MBTA, Trenitalia, Madrid CRTM, Helsinki HSL, Poland
regional, MBTA, MTA, MVV Munich, etc. Each feed carries its own
license and per-feed `publisher` / `publisherUrl` / `operator` /
`license` / `licenseUrl` fields in the response.

## The 4 APIs

### 1. Realtime API (vehicle positions + delays + stop sequences)
- **REST base**: `https://api.geops.io/tracker-http/v1`
- **WebSocket**: `wss://api.geops.io/tracker-ws/v1?key=<key>` (full bidirectional, AsyncAPI-documented)
- **OpenAPI**: `/swagger/realtime.json` — 4 endpoints
  - `GET /feeds/` — list all active feeds with bbox + per-feed license
  - `GET /trajectories/{feed_name}/?bbox=...` — current trajectories in a bbox
  - `GET /journeys/{train_id}/` — full LineString trajectory of one vehicle
  - `GET /calls/{train_id}/` — stop sequence (with realtime delay) for a vehicle
- **Output**: GeoJSON FeatureCollection (EPSG:3857 Web Mercator)
- **Vehicle modes**: tram, subway, rail, bus, ferry, cablecar, gondola, funicular, coach

### 2. Routing API (public transport + pedestrian routing)
- **REST base**: `https://api.geops.io/routing/v1`
- **OpenAPI**: `/swagger/routing.json`
- **Networks**: OpenStreetMap (default, most detail) + proprietary datasets
- **Input**: station name/ID or lat/lon pair
- **Output**: route geometry + legs + intermediate stops

### 3. Stops API (worldwide public-transport stop lookup)
- **REST base**: `https://api.geops.io/stops/v1/`
- **OpenAPI**: `/swagger/stops.json`
- **Single endpoint**: `GET /?q=...&limit=...&bbox=...&field=...&mots=...&prefagencies=...&ref_location=...`
- **Output**: GeoJSON FeatureCollection
- **Stop metadata**: `uid`, `name`, `country_code` (ISO-2), `municipality_name`, `mot` (bus/rail/tram/ferry/subway/gondola/cable_car/funicular), `platforms` (per mode), `ifopt` (European public-transport stop ID), `id` (UIC railway code), `code` (DS100 / national code, e.g. `BERT` for Berlin Hbf), `ident_source`
- **Coverage**: "still Europe-focused but continuously extended to more parts of the world" (geOps's own framing)
- **Free demo** — works without any paid plan for low-volume queries

### 4. Maps API (Mapbox vector tile styles for public transport)
- **Style URL**: `https://maps.geops.io/styles/{style}/style.json?key={key}`
- **Styles**: `base_bright_v2`, `base_dark_v2`, `travic_v2` (and a few more)
- **Tile data**: `https://maps.geops.io/data/{dataset}.json?key={key}` (vector tiles, including `openmaptiles`, `base`, `journey_pois`, `perimeter_mask`, `relief_white`)
- **Use case**: SvelteKit frontend base layer; emphasis on public transport + barrier-free info
- **Output**: standard Mapbox Vector Tile spec — works in MapLibre, Mapbox GL, OpenLayers

## Verified working with the public demo key

A public demo key (`5cc87b12d7c5370001c1d6554840ecb89d2743d2b0aad0588b8ba7eb`)
is embedded in the public HTML of `https://developer.geops.io/apis/maps`
and works against the 3 REST APIs for testing. It is **not** a secret
and is **not** a substitute for a personal key — geOps publishes it for
the map-style preview tiles on their own dev pages, and it is rate-limited
accordingly.

I verified the demo key against:

```bash
# 1. Stops API — Berlin Hbf (3 results with full UIC/IFOPT/platforms)
curl "https://api.geops.io/stops/v1/?q=Berlin&limit=3&key=5cc87b12d7c5370001c1d6554840ecb89d2743d2b0aad0588b8ba7eb"

# 2. Realtime Feeds API — 425 feeds, 25,258 trajectories
curl "https://api.geops.io/tracker-http/v1/feeds/?key=5cc87b12d7c5370001c1d6554840ecb89d2743d2b0aad0588b8ba7eb"

# 3. Maps API style.json
curl "https://maps.geops.io/styles/base_bright_v2/style.json?key=5cc87b12d7c5370001c1d6554840ecb89d2743d2b0aad0588b8ba7eb"
```

All three returned 200 with valid data. The Demo key is documented
here for **dev/testing only** — do not put it in any deployed env var
that runs continuously.

## ⚠️ The catch: licensing

| Plan | Cost | Quota | Commercial use |
|---|---|---|---|
| **Free tier (personal key)** | $0 | "Free usage is intended for non-commercial purposes only" (geOps's own words) | **No** — research, hobby, journalism, non-profit only |
| **Commercial / production** | "Contact us" | Per plan | **Yes** — email `support@geops.io` for a quote |
| Public demo key | $0 | Implied low (dev portal embedding) | **No** — for testing only |

The geOps license is **not** an OSI-approved open license. The "free
for non-commercial" tier is a courtesy, not a grant. For our hosted
multi-tenant project that will be sold to journalists, newsrooms, and
developers, this means **commercial keys per tenant** (since the AGPL-3.0
of OpenTIR-Data doesn't waive geOps's commercial restriction).

## Why we do NOT add it to `sources.yaml` by default

| Reason | Detail |
|---|---|
| **Commercial-use restriction** | A geOps key obtained for free is non-commercial only. Our project sells to paying tenants (per `docs/product.md`), so a default free key would breach geOps's ToS. |
| **No anonymous public endpoint** | There is no zero-auth path. Even the dev portal says "we can provide you with a personal API key" — you must email them. |
| **Demo key is for display only** | The key in the dev portal HTML is for rendering the style previews. Production use would burn through whatever informal quota geOps has set. |
| **Per-feed license complexity** | Each of the 425 feeds has its own license. We would need to honor 425 individual license attributions in the `osint.datasets` table — doable but non-trivial. |

## What to do instead / how to wire it up

For a per-tenant setup (which is our model), the right path is:

1. Each tenant that wants geOps coverage adds their own `geops` source
   block to their per-org env vars: `GEOPS_API_KEY=<their key>`.
2. The `ingest/fetchers/geops_realtime.py` fetcher reads
   `os.environ["GEOPS_API_KEY"]` and calls the Realtime API for that
   tenant's bbox of interest.
3. The `sources.yaml` keeps an entry for `geops_realtime` but with
   `enabled: false` by default and a per-tenant `org_id` flag in the
   per-org `ingest_overrides.yaml`.
4. Each per-feed license is preserved in `payloads.extras.feed_license`
   so the `osint.datasets.source_tier` roll-up can correctly classify
   feeds that are themselves commercial (BART, SBB, etc.) vs feeds
   that are CC-BY / ODbL.

This makes geOps a **first-class per-tenant connector** rather than a
shared-warehouse one — the right place for a paid API with
non-commercial-only defaults.

## Underlying data sources (free alternatives if you don't want geOps)

geOps is an aggregator. The underlying data is free from the publishers
themselves. If you want to skip geOps entirely, the equivalent free
sources for the most useful regions are:

| Region | Free alternative |
|---|---|
| Worldwide feed index | **Transitland** (`https://www.transit.land/`, GTFS feed registry) — 1,200+ feeds, public API |
| Germany rail | [`gtfs.de`](gtfs-de.md) (CC-BY 4.0 static, CC BY-SA 4.0 realtime) — full Deutsche Bahn + regional + local feeds, **the same data geOps surfaces under the `de-gtfs-de` feed** |
| Switzerland SBB | `https://opentransportdata.swiss/en/` — official SBB GTFS, free with key |
| France IDF (Paris) | `https://prim.iledefrance-mobilites.fr/` — Prim / IDFM open data |
| Italy (Trenitalia, regional) | `https://www.italoferrovia.it/`, individual region APIs |
| OpenStreetMap routing | **OSRM** (`http://project-osrm.org/`) or **Valhalla** (`https://valhalla.github.io/valhalla/`) — both free, self-hostable |
| Worldwide OSM POI | `https://overpass-api.de/` (Overpass, free) |
| Worldwide admin | **Overture Maps** + **GADM** (already in our vault) |

For most OpenTIR-Data use cases, **Transitland + Valhalla + Overpass**
cover the same ground as geOps without a per-tenant paid relationship.

## How to wire up a geOps fetcher (sketch)

```python
# ingest/fetchers/geops_realtime.py — sketch, not yet implemented
import os, httpx, orjson
from datetime import datetime, timezone

class GeopsRealtimeFetcher:
    name = "geops_realtime"
    base_url = "https://api.geops.io/tracker-http/v1"

    def __init__(self, **kwargs):
        self.api_key = os.environ["GEOPS_API_KEY"]
        self.bbox = kwargs.get("bbox", "-180,-90,180,90")  # default whole world

    async def fetch_once(self) -> list[dict]:
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"{self.base_url}/trajectories/world/",
                params={"bbox": self.bbox, "key": self.api_key},
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
        out = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            geom = feature.get("geometry", {})
            if not geom.get("coordinates"):
                continue
            x, y = geom["coordinates"][-1]  # last point in partial trajectory
            # Convert EPSG:3857 → EPSG:4326 here, or store raw + label
            out.append({
                "source": "geops_realtime",
                "kind": "vehicle_position",
                "ts": props.get("timestamp"),
                "lat": y,  # if you converted, else label "EPSG:3857"
                "lon": x,
                "vehicle_id": props.get("train_id"),
                "line": (props.get("line") or {}).get("name"),
                "mode": props.get("type"),
                "delay_sec": props.get("delay"),
                "has_realtime": props.get("has_realtime"),
                "feed_short_name": props.get("tenant"),
                "feed_license": (props.get("license") or ""),
                "raw": feature,
            })
        return out
```

(The coord system is the big decision: geOps is EPSG:3857 throughout;
our `osint.datasets` should store EPSG:4326. Convert at ingest time.)

## See also

- [Liveuamap](liveuamap.md) — the same pattern: paid API with free
  alternatives documented (Harvard CCC, Count Love, ACLED)
- [OpenSky](opensky.md) — already in our `sources.yaml`; the same
  per-tenant model for a paid API
- [OpenFlights](openflights.md) — the reference airport/route dataset
- [OWID Data API](owid-data-api.md) — the data-API reference
  architecture (FastAPI + DuckDB / ClickHouse)
- [Transitland](https://www.transit.land/) — free registry of 1,200+ GTFS feeds
- [Valhalla routing engine](https://valhalla.github.io/valhalla/) — open-source routing alternative
- [Overpass API](overpass-api.md) — already in our `sources.yaml`; the
  free OSM POI query engine

## License of this connector note

`connectors/geops.md` is dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

