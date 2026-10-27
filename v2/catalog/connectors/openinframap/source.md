# Open Infrastructure Map — global power infrastructure from OpenStreetMap

Key: `none required (ODbL)`
Endpoint (web): `https://openinframap.org/`
Endpoint (Overpass API): `https://overpass-api.de/api/interpreter` or `https://overpass.kumi.systems/api/interpreter`
Endpoint (tile server): `https://tiles.openinframap.org/{z}/{x}/{y}.pbf` (vector tiles)
Auth: `none`
Format: **MVT (Mapbox Vector Tiles)** + **Overpass JSON** (per-tag queries) + **PNG raster fallback**

Documentation:
- Landing: https://openinframap.org/
- GitHub: https://github.com/openinframap/openinframap
- Tag catalog: https://openinframap.org/ (web UI is the source of truth for which tags are included)
- OpenStreetMap power=plant tag: https://wiki.openstreetmap.org/wiki/Tag:power%3Dplant
- Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API
- License: **ODbL 1.0** (OpenStreetMap data)
- Coverage: **global** (limited by OSM coverage; good in EU/US/UK/CA/AU, sparse in Africa/Central Asia)
- Code: MIT
- Refresh: **continuous** (OSM edits propagate within minutes via the tile server)

## What it is

**Open Infrastructure Map** is a renderer + tile server on top of
**OpenStreetMap** that focuses on **infrastructure**: power
plants, power lines (by voltage), substations, telecoms, oil/gas
pipelines, water/sewage, etc. The frontend at
`https://openinframap.org/` is the live map; the data layer is
**OSM tags** (`power=plant`, `power=line`, `power=substation`,
`power=tower`, `power=transformer`, etc.).

For our purposes, OpenInfraMap is the right **live, global, free
power infrastructure base layer**. WRI GPPD is a frozen 2022
snapshot; GEM is bi-annual but curated; **OSM is real-time and
community-maintained** (with the usual OSM quality caveats —
better in some countries than others).

## The data shape

The OSM tags that OpenInfraMap renders:

| Tag | What |
|---|---|
| `power=plant` | A power plant (one node + tags) |
| `power=plant` + `plant:source=*` | The fuel source (`wind`, `solar`, `coal`, `gas`, `hydro`, `nuclear`, `biomass`, `oil`, `waste`) |
| `power=plant` + `plant:method=*` | The technology (`combustion`, `photovoltaic`, `wind_turbine`, `run-of-the-river`, `dam`, `nuclear_fission`, etc.) |
| `power=plant` + `plant:output:electricity=*` | Installed capacity (MW) |
| `power=line` | A power line (way) |
| `power=line` + `voltage=*` | Voltage class (`11000` = 11 kV, `132000` = 132 kV, etc.) |
| `power=cable` | Underground cable |
| `power=substation` | A substation (node or polygon) |
| `power=tower` + `power=transformer` | The transmission towers + transformers |
| `power=generator` | Individual generators within a plant (e.g. one row of solar panels) |
| `power=compensator` | Reactive power devices |

The complete schema is in the OSM wiki at
`https://wiki.openstreetmap.org/wiki/Power`.

## The Overpass query (the right way to ingest)

The right way to get all power plants in a country is via the
Overpass API:

```overpass
[out:json][timeout:60];
(
  node["power"="plant"]({bbox});
  way["power"="plant"]({bbox});
  relation["power"="plant"]({bbox});
);
out body;
>;
out skel qt;
```

This returns all power plants (as nodes, ways, or relations) in
a bounding box, with their full OSM tags. For a single country,
use the country code in the Overpass `area` filter:

```overpass
[out:json][timeout:300];
area["ISO3166-1"="US"]->.searchArea;
(
  node["power"="plant"](area.searchArea);
  way["power"="plant"](area.searchArea);
  relation["power"="plant"](area.searchArea);
);
out body;
>;
out skel qt;
```

For **generation mix per country**, the query becomes:

```overpass
[out:csv("name", "plant:source"; true)];
area["ISO3166-1"="DE"]->.searchArea;
(
  node["power"="plant"]["plant:source"="coal"](area.searchArea);
  node["power"="plant"]["plant:source"="wind"](area.searchArea);
  node["power"="plant"]["plant:source"="solar"](area.searchArea);
  way["power"="plant"]["plant:source"="coal"](area.searchArea);
);
out;
```

The endpoints:

- `https://overpass-api.de/api/interpreter` (main, often overloaded)
- `https://overpass.kumi.systems/api/interpreter` (Kumi Systems mirror)
- `https://overpass.private.coffee/api/interpreter` (private.coffee mirror)
- Self-hosted via `docker run wiktorn/overpass-api` (recommended for
  production)

## How to wire it up for OpenTIR-Data

1. **First ingest**: for each of ~200 countries, run a single
   Overpass query for `power=plant` + `power=line` + `power=substation`.
   The OSM world file is ~80 GB compressed, but per-country
   queries are typically < 50 MB.
2. **Per-plant storage**: write to `osint.osm_power_plants` keyed
   by OSM ID. Per-record `country`, `name`, `plant:source`,
   `plant:method`, `plant:output:electricity`, `lat`, `lon`,
   `tags` (the full OSM tag set as JSONB).
3. **Per-line storage**: write to `osint.osm_power_lines` keyed
   by OSM way ID. Per-record `voltage`, `circuits`, `cables`,
   `from`, `to` (the substations it connects).
4. **Continuous sync**: Overpass diffs are available via
   `https://overpass-api.de/api/diff?since=...`. Run daily to
   pick up new OSM edits.
5. **Cross-reference with [[gem_global_energy_monitor]]**:
   join on `country` + plant-name fuzzy match. OSM is good
   for the spatial layer (where); GEM is good for the
   status/citation layer (what).

## Important caveats

| Caveat | Detail |
|---|---|
| **OSM quality varies by country** | Germany, Netherlands, UK, US: excellent. Sub-Saharan Africa, Central Asia: sparse. |
| **Plant capacities are missing for many plants** | `plant:output:electricity=*` is present for ~30-50% of plants. Where missing, fall back to [[gem_global_energy_monitor]] or [[wri_gppd]]. |
| **The Overpass API has rate limits** | Public instances ask for polite use. For production, self-host. |
| **Tile server has CORS restrictions** | The MVT tiles at `tiles.openinframap.org` are free for browsing but not licensed for production. Use the OSM raw tile servers or self-host. |
| **Per-country Overpass areas have different sizes** | A `timeout=300` query works for small countries (Luxembourg: 50 ms) but fails for Russia. For large countries, split the query by sub-region. |
| **Coordinate precision is OSM's** | Nominatim + Overpass give 7 decimal places of precision. Don't trust the last 2 digits for boundary work. |
| **Power line networks are not always connected** | OSM has many small islands of mapped power lines. Don't trust the graph for network connectivity analysis. |

## What we use it for

- **Power plant basemap**: every OSM-tagged power plant in the
  world, with the fuel + capacity + method tags. The right
  live data layer.
- **Transmission network**: the high-voltage transmission
  backbone (220+ kV) for any country with good OSM coverage
  (EU, US, UK, AU, CA, JP). Visualize as a graph; the
  edges are the lines, the nodes are the substations.
- **Capacity estimation**: for countries with poor official
  data, OSM is often the best (or only) source. Cross-reference
  with [[wri_gppd]] for capacity triangulation.
- **New plant detection**: daily Overpass diffs let us detect
  new solar farms, new wind farms, new industrial substations
  in near-real-time. Important for the energy-transition
  journalism beat.

## See also

- [[wri_gppd]] — the frozen 2022 baseline
- [[gem_global_energy_monitor]] — the bi-annual curated tracker
- [[wikidata_power_plants]] — the SPARQL endpoint for cross-
  reference
- [[entso_e_outages]] + [[aemo_outages]] — generation units
  in EU + Australia
- [[overpass-api]] — the OSM Overpass pattern (general, not
  power-specific)

## License of this connector note

`connectors/openinframap.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

