# Overture Maps (Meta's open place database, 4B+ places)

Key: `none required` — public, free, open. No API key, no rate limits
on the data itself (downloaded as files from S3).
Endpoint: `s3://overturemaps-tiles-us-west-2-beta/`
Auth: AWS public read (anonymous)
Format: **GeoParquet** files, partitioned by theme and geographic tile

Documentation:
- Official docs: https://docs.overturemaps.org/
- Schema reference: https://docs.overturemaps.org/schema/
- GitHub: https://github.com/OvertureMaps/
- Python library: https://github.com/OvertureMaps/overturemaps-py
- Release notes: https://github.com/OvertureMaps/data/releases
- Visual explorer: https://explore.overturemaps.org/

## What it is

**Overture Maps** is a free, open, global map dataset maintained by the
**Overture Maps Foundation** (founded by Meta, Microsoft, Amazon, TomTom,
and Bosch). It combines data from OpenStreetMap, US Census Bureau, US
Geological Survey, and other open sources into a unified, structured
format. The dataset has **4+ billion places** including:

- **~4B places** (POIs, addresses, businesses)
- **~200M buildings** with footprints
- **~60M km of roads** with names, speed limits, lane counts
- **~1M admin boundaries** (countries, states, counties, cities, neighborhoods)

Released as **GeoParquet** files partitioned by theme (`places`,
`addresses`, `buildings`, `roads`, `admins`) and by geographic tile.
You download what you need.

**The primary free geo database for "down to the town/address level"**
that the user asked for.

## Themes

| Theme | What's in it | File size | Use case |
|---|---|---|---|
| `places` | POIs, businesses, named places | ~50 GB | "Find all hospitals in Chicago" |
| `addresses` | Street addresses worldwide | ~30 GB | Reverse geocoding at building level |
| `buildings` | Building footprints + heights | ~80 GB | "Show me every building in this bbox" |
| `roads` | Road network with names + types | ~100 GB | Routing, isochrones |
| `admins` | Country/state/county/city boundaries | ~5 GB | Choropleth maps, geofencing |
| `base` | Land/water/coastline (low res) | ~3 GB | Map backgrounds |

## How to use it (Python example)

```python
# Requires: pip install overturemaps-py duckdb
from overturemaps import core
import duckdb

# Get a bbox for a city: (west, south, east, north)
paris = (2.224, 48.852, 2.420, 48.902)
chicago = (-87.940, 41.644, -87.524, 41.940)

# Download places for Paris
places_path = core.overture_type(
    type="place",
    bbox=paris,
    output_format="geojson",
    output_path="/srv/working/paris_places.geojson"
)
# Now query it
df = duckdb.query(f"SELECT id, name, category, geometry FROM '{places_path}' LIMIT 100").df()
print(df.head())
```

## Notes

- **The right answer for "down to the town/address level"** for our v1.
  Combine Overture Maps (places) with Nominatim (forward geocoder) and
  GADM (admin boundaries) for the full stack.
- **License**: Overture data is published under **ODbL 1.0** (the same as
  OpenStreetMap) for OSM-derived data, and **public domain** for US
  Census and US Geological Survey data. The Overture Schema itself is
  **Apache-2.0**.
- **Storage cost**: full Overture data is ~270 GB. We can subset to
  per-region tiles (e.g., one tile per country we operate in).
- **Format**: GeoParquet (Apache Arrow / Parquet with geometry extension).
  Use DuckDB or GeoPandas to read; both are in our `requirements.txt`
  style already.
- **Update cadence**: Overture releases monthly. Subscribe to the
  GitHub releases page for new versions.
- **For the dashboard's "down to the town of where things are happening"**
  requirement: Overture `places` + `addresses` give us sub-meter accuracy
  for most urban areas. Combined with the country reconciler for ISO
  codes, every cell in the warehouse can be mapped to a specific
  street address.
- **Combined with our existing tools**:
  - **Nominatim** (already in `docs/tools.md`) for forward geocoding
    (address → lat/lon)
  - **Overture Maps** (this) for the database (places, buildings, addresses)
  - **GADM** (next connector) for admin boundaries (country → state → city)
  - **OpenAddresses** (next connector) for the global address database
  - **Overpass API** (next connector) for live OSM POI queries
  - **MaxMind GeoLite2** (next connector) for IP-based user geolocation

## Storage plan for our project

| Tile | Size | Use |
|---|---|---|
| North America | ~30 GB | Primary |
| Europe | ~25 GB | Primary |
| Asia | ~30 GB | Primary |
| Africa | ~15 GB | Secondary |
| South America | ~10 GB | Secondary |
| Oceania | ~5 GB | Secondary |
| Antarctica | <1 GB | Trivial |
| **Total** | **~115 GB** | Fits in 2 TB cold tier |

Or, the **streaming approach**: don't download Overture. Use it on-demand
via DuckDB's HTTP range reads. We only fetch the tiles we need for a
given query, never the full dataset. **This is the recommended v1
approach** — no upfront storage cost, but slower per query.

## License: ODbL 1.0 + Apache-2.0 (mixed)

- The Overture **data** is ODbL 1.0 (OSM-derived) and public domain (US
  government-derived). Free for any use including commercial, with the
  ODbL share-alike terms (which means **a derived database must also be
  ODbL or ODbL-compatible**).
- The Overture **schema** and code libraries are Apache-2.0.
- **Important**: if we redistribute Overture data through our product
  (e.g., as a "geocode this address" feature), the share-alike clause
  may require our product to be ODbL-compatible. We are already
  AGPL-3.0, which is more restrictive than ODbL, so this is fine for
  us. For a permissive-licensed product, this would be a concern.
