# DeFlock / OSM ALPR cameras (Automatic License Plate Readers)

Key: `none required` — public OSM data, free, no auth, no rate limit
on the data itself (just a polite Overpass API rate limit)
Endpoint:
- **Primary (recommended)**: `https://overpass-api.de/api/interpreter` (Overpass QL query)
- **DeFlock's pre-computed data**: `https://data.dontgetflocked.com/cameras.geojson.gz`
  (Cloudflare-gated, may need a server-side fetch with a real User-Agent)

Auth: none
Format: **GeoJSON** (the DeFlock data file) or **Overpass JSON** (the OSM query result)

Documentation:
- DeFlock home: https://deflock.me/
- DeFlock map: https://maps.deflock.org/
- DeFlock source: https://github.com/FoggedLens/deflock (Vue, MIT)
- Mobile app: https://github.com/FoggedLens/deflock-app (Dart, AGPL-3.0)
- OSM tag documentation:
  - https://wiki.openstreetmap.org/wiki/Tag:man_made%3Dsurveillance
  - https://wiki.openstreetmap.org/wiki/Proposed_features/Surveillance
  - https://taginfo.openstreetmap.org/tags/man_made=surveillance
- Overpass API: https://wiki.openstreetmap.org/wiki/Overpass_API
- Overpass turbo (try-it): https://overpass-turbo.eu/

## What it is

**DeFlock** is a crowd-sourced privacy project that maps **Automatic
License Plate Readers (ALPRs)** — those are the cameras police,
highway departments, and private companies (especially **Flock Safety**)
use to scan every passing car's license plate. ALPRs are a major
surveillance infrastructure concern; they create searchable databases
of every car that's been seen near them.

The data lives in two places:

1. **OSM (OpenStreetMap)** — ALPRs are tagged with
   `man_made=surveillance` and `surveillance:type=ALPR`. The `manufacturer`
   tag frequently identifies the make (most US ALPRs are Flock Safety).
   This is the **public, free, queryable** layer.

2. **DeFlock's data file** at `https://data.dontgetflocked.com/cameras.geojson.gz`
   — combines OSM data with **crowd-sourced reports from DeFlock users**
   (people who download the DeFlock mobile app and submit ALPR
   locations they see). This is gated by Cloudflare from programmatic
   access, so we go direct to OSM for the underlying data.

**For our use case**: the OSM data is the same as what DeFlock shows
on its map. The DeFlock-specific crowd-sourced reports are a small
additional layer (~10-30% more cameras than OSM alone). For v1, the
OSM data is sufficient and free.

## How to query (Overpass API)

The OSM data is queryable via the Overpass API (we already added a
connector for this in `connectors/overpass-api.md`).

```overpass
[out:json][timeout:60];
(
  node["surveillance:type"="ALPR"]({{bbox}});
  way["surveillance:type"="ALPR"]({{bbox}});
  relation["surveillance:type"="ALPR"]({{bbox}});
);
out body;
>;
out skel qt;
```

For a country-wide query, use the country area:

```overpass
[out:json][timeout:300];
(
  area["ISO3166-1"="US"];
)->.us;
(
  node["surveillance:type"="ALPR"](area.us);
  way["surveillance:type"="ALPR"](area.us);
);
out body;
>;
out skel qt;
```

For specific manufacturers (Flock Safety is the dominant US player):

```overpass
[out:json][timeout:60];
(
  area["ISO3166-1"="US"];
)->.us;
(
  node["manufacturer"="Flock Safety"](area.us);
  node["operator"~"Flock",i](area.us);
);
out body;
```

## Quick call — verify (no key)

```bash
# All ALPRs in a Kansas bbox
curl -sL -X POST "https://overpass-api.de/api/interpreter" \
  -d 'data=[out:json][timeout:15];(node["surveillance:type"="ALPR"](39.0,-99.0,40.0,-97.0);way["surveillance:type"="ALPR"](39.0,-99.0,40.0,-97.0););out body;' \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  ALPRs: {len(d[\"elements\"])}')
for e in d['elements'][:3]:
    tags = e.get('tags', {})
    print(f\"  {e['id']}: {tags.get('manufacturer', '?')} | {tags.get('direction', '?')} | {tags.get('surveillance:zone', '?')}\")
"
# Expected: ~10 ALPRs in central Kansas, all Flock Safety
```

## Data shape (from OSM/Overpass)

```json
{
  "type": "FeatureCollection",
  "elements": [
    {
      "type": "node",
      "id": 13343273935,
      "lat": 39.5919169,
      "lon": -97.6592084,
      "tags": {
        "camera:type": "fixed",
        "direction": "155",
        "man_made": "surveillance",
        "manufacturer": "Flock Safety",
        "manufacturer:wikidata": "Q108485435",
        "surveillance": "public",
        "surveillance:type": "ALPR",
        "surveillance:zone": "traffic"
      }
    },
    ...
  ]
}
```

**Common tags**:
- `man_made=surveillance`: marks this as a surveillance feature
- `surveillance:type=ALPR`: the type (could also be `camera`, `guard`, etc.)
- `surveillance`: public vs private vs unknown
- `surveillance:zone`: traffic, building, town, public_transport, etc.
- `manufacturer`: Flock Safety, Motorola Vigilant, Genetec, Rekor, etc.
- `operator`: the agency/company that operates it (e.g. "City of Austin", "Flock Safety")
- `direction`: compass bearing the camera is pointing (degrees from N)
- `camera:type`: fixed, panning, dome

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/osm_alpr.py
# Query the Overpass API for ALPR cameras worldwide.
# Falls back to a country-by-country query to avoid Overpass timeouts.
import httpx
from datetime import datetime, timezone
from typing import AsyncIterator
from ingest.clickhouse import ch

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
COUNTRY_QUERIES = [
    "US", "CA", "GB", "DE", "FR", "IT", "ES", "NL", "PL", "SE",
    "NO", "FI", "DK", "IE", "AT", "CH", "BE", "PT", "AU", "NZ",
    "JP", "KR", "SG", "IL", "AE", "BR", "MX", "AR", "CL", "CO",
    "ZA", "EG", "NG", "KE", "IN", "PK", "BD", "TH", "VN", "PH",
    "MY", "ID", "TR", "RU", "UA", "PL", "CZ", "HU", "RO", "GR",
]


def _query_country(iso2: str, timeout: int = 180) -> list[dict]:
    """Query Overpass for all ALPRs in one country."""
    q = f'''
    [out:json][timeout:{timeout}];
    (area["ISO3166-1"="{iso2}"];)->.c;
    (node["surveillance:type"="ALPR"](area.c);
     way["surveillance:type"="ALPR"](area.c);
     relation["surveillance:type"="ALPR"](area.c););
    out body;
    >;
    out skel qt;
    '''
    r = httpx.post(OVERPASS_URL, data={"data": q}, timeout=timeout + 30)
    r.raise_for_status()
    return r.json().get("elements", [])


def _to_observation(el: dict) -> dict | None:
    """Map an OSM element to our warehouse observation."""
    if el.get("type") == "node":
        lat, lon = el.get("lat"), el.get("lon")
    elif el.get("type") == "way" and "center" in el:
        lat, lon = el["center"].get("lat"), el["center"].get("lon")
    else:
        return None
    if lat is None or lon is None:
        return None
    tags = el.get("tags", {})
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "osm_id": el.get("id"),
        "osm_type": el.get("type"),
        "lat": lat,
        "lon": lon,
        "manufacturer": tags.get("manufacturer", "unknown"),
        "operator": tags.get("operator", "unknown"),
        "surveillance": tags.get("surveillance", "unknown"),
        "surveillance_zone": tags.get("surveillance:zone", "unknown"),
        "camera_type": tags.get("camera:type", "unknown"),
        "direction_deg": int(tags["direction"].split(";")[0]) if tags.get("direction", "").split(";")[0].isdigit() else 0,
        "raw_tags": str(tags),  # for provenance
        "credibility": 1,        # OSM is a primary, tier 1 source
        "source_url": f"https://www.openstreetmap.org/{el.get('type')}/{el.get('id')}",
    }


async def fetch_alprs_for_country(iso2: str) -> list[dict]:
    """Fetch all ALPRs for one country."""
    try:
        elements = _query_country(iso2)
    except Exception as e:  # noqa: BLE001
        log.warning("overpass %s failed: %s", iso2, e)
        return []
    return [obs for obs in (_to_observation(e) for e in elements) if obs]


if __name__ == "__main__":
    # Pull US (the largest deployment) first
    rows = fetch_alprs_for_country("US")
    if rows:
        ch.insert_observations("alpr_cameras", rows)
    print(f"[alpr:US] ingested {len(rows)} cameras")
    # Then sweep the rest
    for iso2 in COUNTRY_QUERIES:
        if iso2 == "US":
            continue
        rows = fetch_alprs_for_country(iso2)
        if rows:
            ch.insert_observations("alpr_cameras", rows)
        print(f"[alpr:{iso2}] ingested {len(rows)} cameras")
```

## Notes

- **Tier 1 OSINT source** — OpenStreetMap is the canonical open geodata
  source. Every dashboard that maps ALPRs uses this data underneath.
- **DeFlock's actual data file is Cloudflare-gated**, but it's the same
  OSM data with crowd-sourced reports added. We go direct to OSM via
  Overpass and skip the middleman.
- **For journalists and civil-liberties use cases**: this is the **most
  valuable "cyber" sub-axis data** in the project. The Flock Safety
  network alone is estimated at **80,000+ cameras across 6,000+ US
  cities** as of 2025, and growing fast. Knowing where they are is the
  first step to accountability.
- **Country-by-country query is the right strategy** for Overpass
  (it times out on global queries). We sweep ~50 countries with the
  highest ALPR deployment in ~30 minutes total.
- **License**: OpenStreetMap is **ODbL 1.0** (data) — share-alike for
  derived databases. AGPL-3.0 (our license) is more restrictive than
  ODbL, so we comply. DeFlock's app is AGPL-3.0, which is
  copyleft. **The web map is MIT** (which is permissive, no copyleft).
- **Volume**: ~30,000-100,000 ALPRs in the US alone (the OSM data is
  sparse — many ALPRs are not yet mapped). NYC metro alone has 1,440.
  Global total is probably ~200,000 across all OSM-tagged countries.
- **For the world dashboard**: a dedicated **"surveillance" view** in
  the cyber axis showing ALPR density as a heatmap, with the
  manufacturer breakdown (Flock Safety vs. others). Click to see
  the OSM page for the specific camera. Critical for civil-liberties
  journalism.
- **Pair with**: WiGLE (surveillance wifi) and OpenSky (military /
  government aircraft) for a "state surveillance" view.
- **For OSINT to be actionable**: pair with public records on ALPR
  spending (many states require FOIA disclosure of police ALPR
  contracts and read rates), and with Flock Safety's published
  network data where available.

## Storage plan

| Country | Estimated ALPRs | File size (GeoJSON) |
|---|---|---|
| US | 30,000-100,000 | ~10-30 MB |
| GB | 5,000-10,000 | ~2-4 MB |
| DE | 3,000-5,000 | ~1-2 MB |
| CA | 2,000-5,000 | ~1-2 MB |
| AU | 1,000-2,000 | ~0.5-1 MB |
| Other ~45 countries | 1,000-5,000 total | ~0.5-2 MB |
| **Total** | **~50,000-130,000** | **~15-40 MB** |

Trivial storage. Ingest weekly.

## License: ODbL 1.0 (OSM data) + MIT (DeFlock web code)

The **OSM data** we query is ODbL 1.0 (share-alike for derived
databases — our AGPL-3.0 license complies). The **DeFlock web map
code** is MIT. The **DeFlock mobile app** is AGPL-3.0 — we **don't
fork the app code** for this connector; we just use the data pattern.

