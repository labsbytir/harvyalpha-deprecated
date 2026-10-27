# EFFIS (European Forest Fire Information System)

Key: `pending — register at https://effis.jrc.ec.europa.eu/effis/api/` (free, EU JRC; used by firemap.live for European fires)
Endpoint: `https://ies-research.jrc.ec.europa.eu/firms/api/`
Auth: API key in `?key=<MAP_KEY>` (similar to NASA FIRMS)
Format: `CSV`, `JSON`, `Shapefile`

Documentation:
- EFFIS home: https://effis.jrc.ec.europa.eu/
- API documentation: https://effis.jrc.ec.europa.eu/effis/api/
- API key request: https://effis.jrc.ec.europa.eu/effis/api/key-request
- Fire News: https://effis.jrc.ec.europa.eu/active-fires/
- Dataset catalog: https://effis.jrc.ec.europa.eu/datasets/

## What it is

EFFIS is the **European Forest Fire Information System**, run by the
**European Commission's Joint Research Centre (JRC)**. It monitors forest
fires and wildland fires across Europe, North Africa, the Middle East,
and parts of Asia. It complements NASA FIRMS by:

- **Higher resolution** in Europe (250m vs 375m for VIIRS, 1km for MODIS)
- **European-specific datasets** like burnt area, damage assessment, and
  pre-fire risk indices
- **Direct integration with EU emergency services** (EFFIS is the data
  backbone for the EU Civil Protection Mechanism)
- **Sensor fusion** combining MODIS + VIIRS + Sentinel-2 + national sources
  for the most complete European fire picture

For our use case, EFFIS is **NASA FIRMS but better for Europe**. We use
both: NASA FIRMS for global coverage, EFFIS for higher-quality European
data.

## API endpoints (similar shape to NASA FIRMS)

```text
# Active fire detections (MODIS + VIIRS)
GET /firms/api/active_fire/csv/{sensor}/{area}/{day_range}/{date}
GET /firms/api/active_fire/json/{sensor}/{area}/{day_range}/{date}

# Burnt area (per country, per year)
GET /firms/api/burntarea/csv/{country}/{year}

# Fire danger forecast (Fire Weather Index)
GET /firms/api/fwi/{country}/{date}

# Land cover / fuel map
GET /firms/api/lc/{bbox}/{date}
```

The exact API path may be `https://ies-research.jrc.ec.europa.eu/firms/api/`
or `https://effis.jrc.ec.europa.eu/firms/api/` — both are part of the JRC
infrastructure. Use the key to authenticate either way.

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/effis.py
# Daily pull of European active fires (better resolution than NASA FIRMS in EU).
import os
import httpx
from datetime import datetime, timezone, timedelta
from ingest.clickhouse import ch

EFFIS_KEY = os.environ.get("EFFIS_KEY", "")
if not EFFIS_KEY:
    raise SystemExit("EFFIS_KEY required — register at https://effis.jrc.ec.europa.eu/effis/api/")

BASE = "https://ies-research.jrc.ec.europa.eu/firms/api"
SENSORS = ["MODIS", "VIIRS_SNPP", "VIIRS_NOAA20"]


def fetch_european_fires(days: int = 1) -> list[dict]:
    """Fetch all European fires for the last `days` days."""
    rows = []
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    for sensor in SENSORS:
        url = f"{BASE}/active_fire/csv/{sensor}/EUROPE/{days}/{start}"
        r = httpx.get(url, params={"key": EFFIS_KEY}, timeout=60.0)
        if r.status_code != 200:
            print(f"[effis:{sensor}] HTTP {r.status_code}")
            continue
        lines = r.text.strip().split("\n")
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) < 14:
                continue
            try:
                rows.append({
                    "as_of": today,
                    "sensor": sensor,
                    "satellite": parts[8],
                    "acq_date": parts[5],
                    "acq_time": parts[6],
                    "lat": float(parts[0]),
                    "lon": float(parts[1]),
                    "brightness": float(parts[2]) if parts[2] else None,
                    "frp": float(parts[11]) if parts[11] else None,
                    "confidence": parts[9],
                    "credibility": 1,  # EU JRC = tier 1
                    "source_url": "https://effis.jrc.ec.europa.eu/",
                })
            except (ValueError, IndexError):
                continue
    return rows


if __name__ == "__main__":
    rows = fetch_european_fires(days=1)
    if rows:
        ch.insert_observations("effis_fires", rows)
    print(f"inserted {len(rows)} European fire detections")
```

## Notes

- **Used by firemap.live** (alongside NASA FIRMS) for their European layer.
- **Complements NASA FIRMS** — EFFIS has better European coverage, NASA
  FIRMS has better global coverage. We use both.
- **Free for non-commercial / research use**; commercial use requires a
  separate agreement with the JRC.
- **Rate limit**: not published, but be polite (~1 req/sec).
- **Volume**: ~1,000-3,000 European fires per day during fire season (summer).
- **Credibility tier**: 1 (EC JRC = primary source).
- **License**: EFFIS data is **public domain** (EC-JRC-produced). Free for
  any use, attribution requested.
- **For the world dashboard**: this is the **European slice** of the fire
  layer. NASA FIRMS handles the rest of the world.

## License: EC JRC public domain

EFFIS data is produced by the European Commission's Joint Research Centre
and is in the public domain. Free for any use including commercial,
attribution requested: "EFFIS / European Commission Joint Research Centre".


## Migrated Context (From EFFIS European Forest Fire Information System.md)

---
tags: [source, climate, tier-1, osint-data, requires-key]
status: active
display_name: "EFFIS European Forest Fire Information System"
fetcher: ingest.fetchers.effis
source_name: effis
api_key_env: EFFIS_KEY
---

# EFFIS European Forest Fire Information System

European Forest Fire Information System (EC JRC). Higher-resolution fire detection for Europe than NASA FIRMS. MODIS + VIIRS S-NPP + VIIRS NOAA-20 sensors. Free with EFFIS key.

## Metadata

| Field | Value |
|---|---|
| Source system | `effis` |
| Base URL | https://effis.jrc.ec.europa.eu |
| API base | https://ies-research.jrc.ec.europa.eu/firms/api |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | climate |
| License | CC-BY (EC JRC) |
| Auth | **Required**: `EFFIS_KEY` |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `europe_daily` | area=EUROPE, MODIS + 2 VIIRS, day_range=1 | European fires daily |

## Fetcher

`ingest/fetchers/effis.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='effis'`. Per-detection rows in same shape as NASA FIRMS.

## Common queries

```
GET /v1/sources/effis
GET /v1/sources/effis/bundles?country=PT&since=2026-09-01
```

## Gotchas

- EFFIS key is free; sign up at https://effis.jrc.ec.europa.eu/about/.
- The Europe-only filter is hardcoded in the API; outside Europe, use NASA FIRMS.
- Detection schema is similar to FIRMS but not identical; normalize on ingest.

## Related

- [[Plan/Source Categorization]] (climate axis)
- [[Ingestion/NASA FIRMS Active Fire Detection]] (global counterpart)
- [[Ingestion/GDACS Multi-Hazard Alerts (EC JRC / UN OCHA)]] (multi-hazard context)

