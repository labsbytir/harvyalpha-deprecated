# Overpass API (live OpenStreetMap POI query)

Key: `none required` — public, free. Polite rate limit: 1 request/sec per IP.
For high-volume use, self-host with the public Overpass instance
or run your own.
Endpoint: `https://overpass-api.de/api/interpreter` (main public instance)
Auth: none
Format: **JSON**, **XML**, **CSV** — same OSM data model

Documentation:
- API home: https://wiki.openstreetmap.org/wiki/Overpass_API
- Query language: https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL
- Public instance: https://overpass-api.de/
- Mirror: https://overpass.kumi.systems/api/interpreter
- Try it: https://overpass-turbo.eu/

## What it is

**Overpass API** is the live read-only query interface for
OpenStreetMap. It's like "SQL for the OSM planet file" — you can ask
"give me every hospital in this bbox" or "give me every building
taller than 50m tagged as a hospital in Chicago" and get a JSON
response in seconds.

Overpass is the **right tool for live POI queries** when Overture Maps
is too heavy. For a v1 dashboard, you can run Overpass queries on
demand without downloading a 270 GB dataset.

## Quick call — verify (no key)

```bash
# Every hospital in central Paris
curl -sL -X POST "https://overpass-api.de/api/interpreter" \
  -d 'data=[out:json][timeout:5];(node["amenity"="hospital"](48.85,2.30,48.87,2.37);way["amenity"="hospital"](48.85,2.30,48.87,2.37););out body;>' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for el in d['elements'][:5]:
    name = el.get('tags', {}).get('name', 'unnamed')
    print(f\"{el['type']} {el['id']}: {name}\")
"
# Expected: 5+ hospitals in central Paris

# Every embassy in Washington, DC
curl -sL -X POST "https://overpass-api.de/api/interpreter" \
  -d 'data=[out:json][timeout:10];node["office"="diplomatic"](38.85,-77.10,38.95,-77.00);out;' \
  | python3 -c "import json, sys; print(len(json.load(sys.stdin)['elements']), 'embassies')"
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/overpass.py
# Geocode an event's lat/lon to a POI name.
import httpx
from typing import Optional


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def reverse_geocode_poi(lat: float, lon: float, radius_m: int = 50) -> Optional[dict]:
    """Find the nearest named POI to (lat, lon). Returns the first hit."""
    radius_deg = radius_m / 111000.0  # ~111 km per degree
    bbox = f"{lat - radius_deg},{lon - radius_deg},{lat + radius_deg},{lon + radius_deg}"
    query = f"""
    [out:json][timeout:5];
    (
      node["name"]({bbox});
      way["name"]({bbox});
      relation["name"]({bbox});
    );
    out body;
    """
    r = httpx.post(OVERPASS_URL, data={"data": query}, timeout=30.0)
    r.raise_for_status()
    elements = r.json().get("elements", [])
    if not elements:
        return None
    # Return the first named element
    return {
        "osm_id": elements[0]["id"],
        "osm_type": elements[0]["type"],
        "name": elements[0].get("tags", {}).get("name", ""),
        "category": elements[0].get("tags", {}).get("amenity", "") or
                    elements[0].get("tags", {}).get("shop", "") or
                    elements[0].get("tags", {}).get("office", "") or
                    elements[0].get("tags", {}).get("tourism", ""),
        "tags": elements[0].get("tags", {}),
    }


def list_hospitals_in_bbox(west: float, south: float, east: float, north: float) -> list[dict]:
    """List all hospitals in a bbox."""
    query = f"""
    [out:json][timeout:30];
    (
      node["amenity"="hospital"]({south},{west},{north},{east});
      way["amenity"="hospital"]({south},{west},{north},{east});
    );
    out body;
    """
    r = httpx.post(OVERPASS_URL, data={"data": query}, timeout=60.0)
    r.raise_for_status()
    return [
        {
            "osm_id": el["id"],
            "name": el.get("tags", {}).get("name", ""),
            "lat": el.get("lat") or el.get("center", {}).get("lat"),
            "lon": el.get("lon") or el.get("center", {}).get("lon"),
            "tags": el.get("tags", {}),
        }
        for el in r.json().get("elements", [])
    ]
```

## Notes

- **Polite rate limit**: 1 request/sec per IP from the public instance.
  For high-volume use, self-host. The Docker image is at
  `wiktorn/overpass-api`.
- **Tile server URLs**: 5+ public Overpass instances including the
  main German one and several mirrors. The query syntax is identical.
- **Returns OSM data** (nodes, ways, relations) with tags. The
  full OSM tag schema is documented at
  https://wiki.openstreetmap.org/wiki/Tags — there are thousands of
  possible tags. The most common categories: `amenity`, `shop`,
  `office`, `tourism`, `highway`, `building`, `natural`.
- **For the dashboard's "down to the address" requirement**: Overpass
  can reverse-geocode a lat/lon to the nearest named POI, building, or
  road. For full street address, combine with Nominatim.
- **OSM data license**: ODbL 1.0. The same caveats as Nominatim
  apply (share-alike if we redistribute OSM data).
- **For our use case**: don't use the public instance for
  high-volume queries. Either self-host Overpass (Docker image is
  easy) or use the Overture Maps data files.

## License: ODbL 1.0 (data) + GPL-2.0 (server code)

The OpenStreetMap **data** returned by Overpass is ODbL 1.0. The
**Overpass server code** is GPL-2.0. For our use case (querying
public data, displaying in our dashboard), ODbL share-alike is the
relevant constraint — same as for Overture Maps.

