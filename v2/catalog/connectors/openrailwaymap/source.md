# OpenRailwayMap (OpenStreetMap-based worldwide railway map)

Key: `none required` — public tile server + Overpass-compatible schema, no auth, no rate limit
Endpoint: `https://tiles.openrailwaymap.org/`
Auth: none
Format: **Mapbox Vector Tiles** for the new vector style + **PNG raster tiles** (legacy) for the four base map styles; data is **OpenStreetMap** (`railway=*` tagging)

Documentation:
- Live map: https://www.openrailwaymap.org/
- Tile URL pattern: `https://{a,b,c}.tiles.openrailwaymap.org/{style}/{z}/{x}/{y}.png`
  - `style` = `standard`, `signals`, `maxspeed`, `electrification`, `gauge`
  - Subdomain rotation `a/b/c` for parallel tile loading
- GitHub: https://github.com/OpenRailwayMap/OpenRailwayMap (GPL-3.0, 513 stars, 103 forks, last commit 2026-04-20)
- Tile JSON: `https://tiles.openrailwaymap.org/{style}/0/0/0.json` (verify on a fresh style)
- Underlying data: **OpenStreetMap** `railway=*` tags, queried via the project's own PostGIS-backed tile server (osm2pgsql + MapCSS rendering rules)
- License: data is **ODbL** (OpenStreetMap contributor terms); the project code is **GPL-3.0**
- Source code: https://github.com/OpenRailwayMap/OpenRailwayMap (CSS/MapCSS) + https://github.com/OpenRailwayMap/orm (tile server)

## What it is

**OpenRailwayMap** is a free, public, OSM-based map of the world's
railway infrastructure. It's a rendering layer on top of OpenStreetMap
data, specialized for rail features (tracks, signals, gauges,
electrification, max speeds, stations, yards, crossings, depots). The
project is run by a small volunteer team and has been continuously
maintained since 2011.

There is no public ingestable API per se — the tile server is the
"API". To get the underlying OSM railway data structured, you query
**Overpass API** (already in our vault) for `railway=*` in your bbox of
interest. OpenRailwayMap's tile server is a *renderer*, not a *data
source*; the data source is OSM.

## Tile URL patterns (verified)

I confirmed that `https://tiles.openrailwaymap.org/standard/11/1023/682.png`
returns a 200 with PNG content (London, zoom 11). The five styles
each render a different aspect of railway infrastructure:

| Style | URL suffix | What it shows |
|---|---|---|
| `standard` | `/standard/{z}/{x}/{y}.png` | Track gauge (standard / narrow / broad), track count, electrification, usage, all on a transparent overlay over OSM base |
| `signals` | `/signals/{z}/{x}/{y}.png` | Signal types (block, distant, shunt, stop), interlocking, crossing types |
| `maxspeed` | `/maxspeed/{z}/{x}/{y}.png` | Speed limits per track, color-coded |
| `electrification` | `/electrification/{z}/{x}/{y}.png` | Contact line voltage (25 kV AC, 15 kV AC, 1.5 kV DC, 3 kV DC, etc.), overhead vs third rail |
| `gauge` | `/gauge/{z}/{x}/{y}.png` | Track gauge in mm (1435 standard, 1668 Iberian, 1520 Russian, 1067 Cape, 1000 metre, etc.) |

All styles are **transparent PNGs** — you overlay them on top of an
OSM base map (or any base map). The vector-tile JSON style at
`/styles/{style}.json` (when available) is Mapbox/MapLibre compatible.

## How to query the data (Overpass, not OpenRailwayMap)

```bash
# All railway tracks in a bbox (London):
curl -X POST https://overpass-api.de/api/interpreter \
  --data 'data=[out:json][timeout:60];
    (
      way["railway"="rail"](51.3,-0.3,51.7,0.1);
      way["railway"="light_rail"](51.3,-0.3,51.7,0.1);
      way["railway"="subway"](51.3,-0.3,51.7,0.1);
      way["railway"="tram"](51.3,-0.3,51.7,0.1);
    );
    out body;>;out skel qt;'

# All railway signals in a bbox:
curl -X POST https://overpass-api.de/api/interpreter \
  --data 'data=[out:json][timeout:60];
    node["railway"="signal"](51.3,-0.3,51.7,0.1);
    out body;'

# All electrified tracks with their voltage:
curl -X POST https://overpass-api.de/api/interpreter \
  --data 'data=[out:json][timeout:60];
    way["electrified"="contact_line"](51.3,-0.3,51.7,0.1);
    out body;'
```

OSM railway tags you'll get (the ones OpenRailwayMap renders):
- `railway=rail` / `light_rail` / `subway` / `tram` / `narrow_gauge` / `funicular` / `monorail` / `disused` / `abandoned` / `razed` / `proposed` / `construction`
- `usage=main` / `branch` / `industrial` / `military` / `tourism` / `scientific` / `test`
- `gauge=1435` / `1668` / `1520` / `1524` / `1600` / `1067` / `1000` / `1004` / etc. (mm)
- `electrified=contact_line` / `rail` / `4th_rail` / `no`
- `voltage=25000` / `15000` / `3000` / `1500` / `750` (volts)
- `frequency=50` / `16.7` / `0` (Hz; 0 = DC)
- `maxspeed=120` / `sign` / etc. (km/h or mph)
- `tracks=1` / `2` / `3` / `4` (track count)
- `passenger_lines=2` / etc.
- `signal=*-block` / `distant` / `shunting` / `stop` / etc. (signals)
- `railway:signal=*-indicator` etc.

## Suggested `sources.yaml` entry

```yaml
- id: openrailwaymap
  display_name: "OpenRailwayMap (OSM-based railway infrastructure)"
  domain: openrailwaymap.org
  axis: infrastructure
  tier: 1
  license: ODbL-1.0
  license_url: https://opendatacommons.org/licenses/odbl/1-0/
  requires_key: false
  schedule: "monthly"   # OSM is updated continuously; a monthly full-export diff is enough
  rate_limit_per_minute: 0   # no rate limit on tile server, but please follow their tile usage policy
  attribution: "Map data © OpenStreetMap contributors, CC-BY-SA; rendered by OpenRailwayMap, GPL-3.0"
  description: |
    Worldwide railway infrastructure rendered from OpenStreetMap railway tags.
    Five specialized styles (standard, signals, maxspeed, electrification, gauge).
    Data ingestion: query Overpass API for railway=* in a bbox; tile rendering: use the
    public tile server in MapLibre/Leaflet.
  endpoints:
    tile_standard: https://{a,b,c}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png
    tile_signals: https://{a,b,c}.tiles.openrailwaymap.org/signals/{z}/{x}/{y}.png
    tile_maxspeed: https://{a,b,c}.tiles.openrailwaymap.org/maxspeed/{z}/{x}/{y}.png
    tile_electrification: https://{a,b,c}.tiles.openrailwaymap.org/electrification/{z}/{x}/{y}.png
    tile_gauge: https://{a,b,c}.tiles.openrailwaymap.org/gauge/{z}/{x}/{y}.png
    overpass_data: https://overpass-api.de/api/interpreter
  usage_policy: |
    Tile usage policy: https://www.openrailwaymap.org/about (typically "reasonable for
    OSM, please host your own tile server for production"). For OpenTIR-Data's
    internal dashboard use this is fine; for a public-facing map, self-host the
    tiles via the OpenRailwayMap tile server project.
```

## Why this is a real free connector (vs. the alternatives)

| Alternative | Cost | Coverage | Notes |
|---|---|---|---|
| **OpenRailwayMap (this)** | Free, ODbL data, GPL-3.0 code | Worldwide, OSM-where-mapped | Best for *visualization* of the OSM railway data; the data is OSM. |
| **Overpass API alone** | Free, ODbL | Worldwide | Same data, but you have to render it yourself |
| **geOps Stops + Realtime** | Free for non-commercial | 425 transport agencies | Live vehicle positions + stop metadata, but no track geometry |
| **Transitland** | Free, public registry | 1,200+ GTFS feeds | Timetables + stops, no track geometry |
| **OurOSM `owid/etl`** (MIT) | Free | Curated 200+ sources | References, not a tile service |
| **HERE / Mapbox rail** | Paid | Commercial | Not free, not in our budget |

For a worldwide rail map view, **OpenRailwayMap + Overpass** is the
free answer. For live vehicle positions, geOps. For timetables, Transitland.
The three together cover the railway-domain axes (infrastructure,
operations, schedule).

## How to render in a SvelteKit page (sketch)

```svelte
<!-- /map in Svelte 5 + MapLibre -->
<script lang="ts">
  import maplibregl from 'maplibre-gl';
  import { onMount } from 'svelte';

  let mapEl: HTMLDivElement;
  onMount(() => {
    const map = new maplibregl.Map({
      container: mapEl,
      style: {
        version: 8,
        sources: {
          'osm': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '© OpenStreetMap contributors',
          },
          'openrailwaymap': {
            type: 'raster',
            tiles: [
              'https://a.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
              'https://b.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
              'https://c.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
            ],
            tileSize: 256,
          },
        },
        layers: [
          { id: 'osm', type: 'raster', source: 'osm' },
          { id: 'rail', type: 'raster', source: 'openrailwaymap' },
        ],
        center: [-0.1278, 51.5074],
        zoom: 11,
      },
    });
  });
</script>
<div bind:this={mapEl} style="width:100%; height:100%"></div>
```

The `signals` / `maxspeed` / `electrification` / `gauge` styles are
particularly useful for the **Compare** and **Network** dashboard views:
they let a user see, at a glance, "where is 25 kV AC electrification
in continental Europe?" or "where are the Cape-gauge (1,067 mm)
networks in Japan / Australia / South Africa?".

## See also

- [`overpass-api`](overpass-api.md) — the data source underneath OpenRailwayMap; query `railway=*` in any bbox
- [`geops`](geops.md) — live vehicle positions + stops, complementary to the OSM rail geometry
- [`transitland`](https://www.transit.land/) — GTFS timetable registry, 1,200+ feeds
- [`owid-cartograms`](owid-cartograms.md) — reference tile server architecture (the same `tiles.{s}.` pattern)
- [`socrata`](socrata.md) — for US rail data via data.transportation.gov and data.bts.gov (the FRA's machine-readable rail data lives there)
- [`traintrackr`](traintrackr.md) — the commercial product that uses similar transit APIs to drive LED hardware

