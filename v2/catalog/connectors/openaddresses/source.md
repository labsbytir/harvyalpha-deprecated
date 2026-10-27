# OpenAddresses (global open address database)

Key: `none required` — public, free, no rate limit
Endpoint: `https://batch.openaddresses.io/` (data) + `https://results.openaddresses.io/` (search)
Auth: none
Format: **CSV** (one row per address: `LON,LAT,NUMBER,STREET,UNIT,CITY,DISTRICT,REGION,POSTCODE,ID,HASH`)

Documentation:
- Home: https://openaddresses.io/
- Data download: https://results.openaddresses.io/
- Bulk download API: https://batch.openaddresses.io/
- Source: https://github.com/openaddresses/openaddresses
- License: https://github.com/openaddresses/openaddresses/blob/master/LICENSE.md (MIT for the code, data is per-source)

## What it is

**OpenAddresses** is a free, open, global database of street addresses.
Unlike Overture Maps (which has places, buildings, addresses combined)
or GADM (which has admin boundaries but no addresses), **OpenAddresses
focuses on addresses only** and is the largest open address database in
the world.

- **~680 million address records** worldwide
- **~100 countries** covered
- Updated by **community contributions** and **imports** from open
  government data (US Census, Canadian government, UK Ordnance Survey
  open data, etc.)
- License per source: most are **public domain** or **ODbL**, with a
  few CC-BY-4.0 exceptions noted in the per-source README.

**This is the right database for "find the address of this event"** —
e.g., reverse-geocoding a lat/lon to "123 Main St, Springfield IL, USA"
with no API rate limit and no API key.

## Quick call — verify (no key)

```bash
# Search for a specific address
curl -sL "https://results.openaddresses.io/?search=1600+Pennsylvania+Ave&country=us" | head -c 500
# Expected: list of matching addresses as JSON

# Bulk download a country
curl -sL -O "https://batch.openaddresses.io/data/country/us.zip"
unzip us.zip
head -3 us.csv
# Expected: LON,LAT,NUMBER,STREET,UNIT,CITY,DISTRICT,REGION,POSTCODE,ID,HASH
```

## Notes

- **Coverage**: best in the US, Canada, UK, Australia, New Zealand,
  Western Europe. Spottier in Africa, Asia, South America. Use
  Overture Maps or Nominatim as a fallback.
- **Bulk download**: per-country CSV/zip files. The US file is
  ~10 GB, the world is ~50 GB compressed. Reasonable to download
  per-region as needed.
- **License**: most sources are public domain or ODbL. A few CC-BY-4.0
  sources require attribution. The per-source license is in the data
  README. For our use case (looking up addresses, not redistributing
  the full database), the licenses are fine.
- **No API key, no rate limit**: bulk downloads are public. Search
  via `results.openaddresses.io` is rate-limited per IP but
  adequate for low-volume lookups. For high-volume, self-host
  OpenAddresses.
- **For the dashboard's "down to the address level" requirement**:
  OpenAddresses is the **right tool for reverse geocoding** (lat/lon
  → street address). For **forward geocoding** (street address →
  lat/lon), use Nominatim. For **place-level search** (POIs, businesses,
  landmarks), use Overture Maps.
- **Powers Mapbox's geocoder**: Mapbox's commercial geocoder is built
  on top of OpenAddresses + OSM. If Mapbox can use it, we can too.
- **Format**: CSV is the universal format. Easy to import into
  ClickHouse, Postgres, or DuckDB.

## Storage plan

| Region | Size (uncompressed) | Use |
|---|---|---|
| US | 10 GB | Primary |
| Canada | 500 MB | Primary |
| UK | 800 MB | Primary |
| Europe (other) | 2 GB | Primary |
| Australia + NZ | 600 MB | Primary |
| Asia | 3 GB | Secondary |
| Africa + South America | 1.5 GB | Secondary |
| **Total** | **~20 GB** | Fits in 2 TB cold tier |

Or, **use Overture Maps `addresses` theme as a single-source replacement**
(it includes OpenAddresses + Overture's own address data). Recommended
for v1.

## License: per-source (mostly public domain + ODbL)

Per the OpenAddresses FAQ:

> OpenAddresses data is provided by many sources, each with their own
> license. Most are public domain or ODbL. A few are CC-BY. We
> redistribute under the most-permissive license of the source.

For our use case (looking up addresses, not redistributing the full
database), the licenses are fine. If we want to ship the addresses
inside our product, we need to track per-source attribution. Easier
to use Overture Maps addresses (single license, ODbL) instead.

## License: MIT for the code, per-source for the data

The OpenAddresses **code** is MIT-licensed. The **data** is per-source
(mostly public domain and ODbL, with a few CC-BY exceptions). For our
use case, MIT code + permissive data = fine.
