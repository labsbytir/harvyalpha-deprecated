# GADM (Database of Global Administrative Areas)

Key: `none required` — public, free for non-commercial use. Commercial use
requires a license (https://gadm.org/license.html)
Endpoint: `https://gadm.org/download_world.html` (data download) +
`https://geodata-eu-flask-1.apps.allizom.org/gadm/v4.0/` (GADM v4.0 API, when
available)
Auth: none
Format: **Shapefile** (`.shp`), **GeoPackage** (`.gpkg`), **R** (`.rds`)

Documentation:
- Home: https://gadm.org/
- Data download: https://gadm.org/download_world.html
- License: https://gadm.org/license.html
- Version 4.0: https://gadm.org/data.html
- Format docs: https://gadm.org/formats.html

## What it is

**GADM** is the **canonical database of global administrative areas**.
Maintained by a team at UC Davis, it provides hierarchical boundary
polygons for:

- **Level 0**: Countries (~250)
- **Level 1**: States / provinces / regions (~5,000)
- **Level 2**: Counties / districts (~50,000)
- **Level 3**: Municipalities / cities (~500,000)
- **Level 4**: Sub-municipalities / wards (select countries)
- **Level 5**: Cities / towns (select countries)

Each polygon has a stable **GID** (GADM ID), a **name** in multiple
languages, and a **parent reference** for the hierarchy. You can resolve
"Paris, France" to (Country: FRA, L1: Île-de-France, L2: Paris, L3: Paris, L5: Paris).

**This is the right database for "down to the town/city level" for
choropleth maps, geofencing, and "data for region X" queries.** Pairs
naturally with the warehouse's `country_codes[]` and `primary_country_code`
columns.

## How to use it

### Option 1: download the GeoPackage

```bash
# Full world, 4 levels, ~1 GB
wget -O /srv/working/gadm_410-levels.gpkg.zip \
  "https://geodata-eu-flask-1.apps.allizom.org/gadm/v4.0/gadm_410-levels.zip"

# Or per-country
wget -O /srv/working/gadm_410-USA.gpkg.zip \
  "https://geodata-eu-flask-1.apps.allizom.org/gadm/v4.0/gadm_410-USA.zip"
```

### Option 2: load into DuckDB and query

```python
import duckdb
con = duckdb.connect()
# After downloading gadm_410-levels.gpkg
con.execute("""
    INSTALL spatial;
    LOAD spatial;
""")
# gadm_410 has 5 layers: level 0..4
con.execute("""
    CREATE TABLE gadm_level1 AS
    SELECT GID_1, GID_0, NAME_1, geometry
    FROM ST_Read('/srv/working/gadm_410-levels.gpkg', layer='level_1')
""")
# Now query
print(con.execute("""
    SELECT GID_1, NAME_1
    FROM gadm_level1
    WHERE GID_0 = 'USA'
    ORDER BY NAME_1
""").fetchall())
```

### Option 3: per-region subset

For a v1 deployment, we don't need the full world. We can subset to the
regions our users care about (e.g., a tile per country we have customers
in). Each country file is 1-50 MB.

## Notes

- **The right database for "down to the town/city level"** for the
  warehouse's `country_codes[]` and `primary_country_code` columns. When
  we want to display "all events in Paris", we use GADM's Paris polygon
  + ClickHouse's `pointInPolygon()` to filter.
- **Use case in our project**: every row in `osint.datasets` has
  `country_codes[]` and `primary_country_code`. To go from "all events
  for country = RUS" to "all events in Moscow Oblast" we need GADM
  polygons.
- **Storage cost**: full world GADM 4.0 is ~1 GB. Per-country files
  1-50 MB each. Trivial.
- **License**: **free for non-commercial use** (academic, research,
  personal). **Commercial use requires a paid license** (~$150-$500/year
  per user, with bulk discounts). Since our product is open-core with
  a hosted tier, the **self-host open-source version is fine for
  non-commercial users**, and the **commercial use of the hosted
  tier** may require us to negotiate a GADM license.
- **Alternative**: **Natural Earth** (https://www.naturalearthdata.com/)
  is public domain and free for any use, but only has country + state
  level (no counties/municipalities). Use Natural Earth for the
  background layers; use GADM for the deep hierarchy.
- **Update cadence**: ~yearly. New versions are infrequent.
- **Format**: GeoPackage is the recommended format (modern, single-file,
  OGC standard). Shapefile has column-name length limits that
  cause issues with some GADM fields.

## License: free for non-commercial, paid for commercial

Per https://gadm.org/license.html:

> The GADM data are freely available for academic and other
> non-commercial use. For commercial use, a license is required.

The GADM team is reasonable about commercial licensing. For our v1
project (AGPL-3.0 + hosted):

- **Open-source self-host users**: free, ODbL-style usage OK
- **Hosted tier (paid)**: we may need to negotiate a commercial GADM
  license if our hosted product incorporates GADM data

For v1, the safe path: use GADM in the open-source product (free) and
**negotiate commercial licensing before launch** of the hosted tier.
Budget: $500-$2000/year for a small commercial user base.

**Alternative for commercial use**: **Natural Earth** (public domain)
covers country + state level for free. For deeper hierarchy in
commercial contexts, consider **OpenAddresses** (public domain) or
**GADM commercial** (paid).
