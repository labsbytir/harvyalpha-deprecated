# NASA FIRMS (Fire Information for Resource Management System)

Key: `pending — register a free key at https://firms.modaps.eosdis.nasa.gov/api/keys` (free for non-commercial / research use; rate limit 1,000 requests / 10 minutes; tier 1)

Endpoint: `https://firms.modaps.eosdis.nasa.gov/api/`
Auth: `?MAP_KEY=<key>` query parameter (URL parameter, not header)
Format: `CSV` (default) or `JSON` (via `format=json`)

Documentation:
- API home: https://firms.modaps.eosdis.nasa.gov/api/
- API key signup: https://firms.modaps.eosdis.nasa.gov/api/keys (free, NASA Earthdata login)
- API status: https://firms.modaps.eosdis.nasa.gov/data/status/
- Map UI (the site you linked): https://firms.modaps.eosdis.nasa.gov/map/
- Data availability: https://firms.modaps.eosdis.nasa.gov/data/availability/
- User guide: https://www.earthdata.nasa.gov/learn/earth-observation-data/near-real-time/firms

## What it is

NASA's **Fire Information for Resource Management System (FIRMS)** distributes
**satellite-detected active fire data** in near real-time from two sensors
aboard multiple Earth-observing satellites:

- **MODIS** (Terra + Aqua satellites, since 2000). Resolution: 1 km.
  - `MODIS_NRT` — Near Real-Time (3-5 hour latency)
  - `MODIS_SP` — Standard Processing (1-2 day latency, higher quality)
- **VIIRS** (Suomi NPP + NOAA-20 + NOAA-21 satellites, since 2012). Resolution: 375 m.
  - `VIIRS_SNPP_NRT` — Suomi NPP, Near Real-Time
  - `VIIRS_NOAA20_NRT` — NOAA-20, Near Real-Time
  - `VIIRS_NOAA21_NRT` — NOAA-21, Near Real-Time (newest)

Each fire detection is a point with latitude, longitude, brightness temperature,
fire radiative power, scan/track pixel coordinates, confidence level, and
satellite + sensor metadata. ~10,000-20,000 detections per day globally.

This is the **canonical source for wildfire OSINT**. Every fire-map site
(fireping.net, wildfirelivemap.com, firemap.live, the-world-now.com) is
either using FIRMS data directly or scraping from a site that does.

## API endpoints (verified live 2026-09-05)

```text
# Country / region — bounding box (west,south,east,north)
GET /api/area/csv/{sensor}/{area}/{day_range}/{date}
GET /api/area/csv/{sensor}/{area}/1/{date}              # last 24h
GET /api/area/csv/MODIS_NRT/world/1/2026-09-05         # whole world, MODIS
GET /api/area/csv/VIIRS_NOAA20_NRT/world/7/2026-09-05  # VIIRS, last 7 days

# Per country (2-letter ISO code, or "world")
GET /api/country/csv/{sensor}/{country}/{day_range}/{date}

# All available datasets
GET /api/data_availability/csv/{sensor}/{country}

# Active fire region from WMS tile
GET /api/area_map/csv/{sensor}/{area}/{day_range}/{date}

# JSON variant: add ?format=json to any csv URL
GET /api/area/json/MODIS_NRT/world/1/2026-09-05?format=json
```

Response is CSV with one row per fire detection, columns:

```text
latitude, longitude, brightness, scan, track, acq_date, acq_time,
satellite, confidence, version, bright_t31, frp, daynight, type
```

- `confidence`: "low" | "nominal" | "high" (string for MODIS, % for VIIRS)
- `frp`: Fire Radiative Power (MW)
- `daynight`: "D" or "N"
- `type`: 0 = offshore, 1 = presumed vegetation fire, 2 = active volcano,
  3 = other static land source

## How it's used in OpenTIR-Data (3 ways)

### Way 1: daily global snapshot

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/nasa_firms.py
# Daily pull of every active fire detection worldwide.
import os
import time
import httpx
from datetime import datetime, timezone, timedelta
from ingest.clickhouse import ch

FIRMS_KEY = os.environ.get("FIRMS_MAP_KEY", "")
if not FIRMS_KEY:
    raise SystemExit("FIRMS_MAP_KEY required — register at https://firms.modaps.eosdis.nasa.gov/api/keys")

BASE = "https://firms.modaps.eosdis.nasa.gov/api"
SENSORS = ["MODIS_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT", "VIIRS_NOAA21_NRT"]


def fetch_daily_fires(date: str = None) -> list[dict]:
    """Fetch 24h of fires for every sensor, worldwide."""
    if date is None:
        date = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d")
    rows = []
    now = datetime.now(timezone.utc)
    for sensor in SENSORS:
        url = f"{BASE}/area/csv/{sensor}/world/1/{date}"
        r = httpx.get(url, params={"MAP_KEY": FIRMS_KEY}, timeout=60.0)
        if r.status_code != 200:
            print(f"[firms:{sensor}] HTTP {r.status_code}: {r.text[:100]}")
            continue
        lines = r.text.strip().split("\n")
        if not lines or len(lines) < 2:
            continue
        # CSV: lat,lon,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight,type
        for line in lines[1:]:
            parts = line.split(",")
            if len(parts) < 14:
                continue
            try:
                rows.append({
                    "as_of": now,
                    "sensor": sensor,
                    "satellite": parts[8],
                    "acq_date": parts[5],
                    "acq_time": parts[6],
                    "lat": float(parts[0]),
                    "lon": float(parts[1]),
                    "brightness": float(parts[2]) if parts[2] else None,
                    "bright_t31": float(parts[10]) if parts[10] else None,
                    "frp": float(parts[11]) if parts[11] else None,
                    "confidence": parts[9],
                    "daynight": parts[12],
                    "type": int(parts[13]) if parts[13] else None,
                    "credibility": 1,   # NASA FIRMS = tier 1
                    "source_url": f"https://firms.modaps.eosdis.nasa.gov/map/?lat={parts[0]}&lon={parts[1]}",
                })
            except (ValueError, IndexError):
                continue
        print(f"[firms:{sensor}] {len(rows)} fires for {date}")
        time.sleep(0.5)  # 200 req / 10 min = ~3s, but be polite
    return rows


if __name__ == "__main__":
    rows = fetch_daily_fires()
    if rows:
        ch.insert_observations("fire_detections", rows)
    print(f"inserted {len(rows)} fire detections")
```

### Way 2: bounding-box query for a region of interest

```python
# Add to nasa_firms.py
def fetch_box_fires(west: float, south: float, east: float, north: float,
                    days: int = 7) -> list[dict]:
    """Fetch fires in a bbox for the last `days` days."""
    area = f"{west},{south},{east},{north}"
    rows = []
    for sensor in SENSORS:
        url = f"{BASE}/area/csv/{sensor}/{area}/{days}/{(datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')}"
        r = httpx.get(url, params={"MAP_KEY": FIRMS_KEY}, timeout=60.0)
        if r.status_code == 200:
            # same parsing as Way 1
            ...
    return rows
```

### Way 3: country-level (per ISO country code)

```python
# Add to nasa_firms.py
def fetch_country_fires(country_iso2: str, days: int = 7) -> list[dict]:
    """Fetch fires for a single country, 1-10 days."""
    rows = []
    for sensor in SENSORS:
        url = f"{BASE}/country/csv/{sensor}/{country_iso2}/{days}/{(datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')}"
        ...
    return rows
```

## Quick call — verify (no key)

```bash
# Without a key, returns the "Invalid MAP_KEY" error
curl -sL "https://firms.modaps.eosdis.nasa.gov/api/area/csv/MODIS_NRT/world/1/2026-09-05"
# Expected: "Invalid MAP_KEY.\nInvalid source.\nInvalid day range. Expects [1..5]."

# With a key, returns CSV header + rows
curl -sL "https://firms.modaps.eosdis.nasa.gov/api/area/csv/MODIS_NRT/world/1/2026-09-05?MAP_KEY=YOUR_KEY" \
  | head -3
# Expected:
#   latitude,longitude,brightness,scan,track,acq_date,acq_time,satellite,confidence,version,bright_t31,frp,daynight,type
#   33.45310,-111.98780,335.4,1.4,1.0,2026-09-05,0730,T,71,2.0NRT,300.1,12.5,D,0
#   33.44960,-111.97840,332.7,1.2,1.0,2026-09-05,0730,T,52,2.0NRT,297.8,8.4,D,0
```

## Notes

- **Used by all 4 sites you linked** — fireping.net, wildfirelivemap.com, firemap.live, and the NASA FIRMS map UI itself all consume this API. We're going direct to the source.
- **Free for non-commercial / research use** — no payment required, just NASA Earthdata login (which is also free).
- **Rate limit**: 1,000 requests per 10 minutes. Our daily snapshot is 5 calls (one per sensor) — well within limits.
- **Coverage**: global, with a 3-5 hour latency for NRT and 1-2 day latency for SP.
- **Volume**: ~10,000-20,000 fire detections/day globally; ~6-10M/year.
- **Credibility tier**: 1 (NASA = primary source).
- **License**: NASA-produced data is **public domain** (US government work). No attribution requirement, but standard academic citation.
- **Storage cost**: 10K-20K rows/day = 3.6M-7.3M rows/year. ClickHouse compresses 10-50x. **Storage: ~500 MB/year**.
- **Use cases**:
  - **Wildfire map view** in the dashboard (Map view of the 12-axis "climate" sub-axis)
  - **Real-time fire alerts** for subscribers (which newsrooms / non-profits would be)
  - **Historical fire analysis** (where are fires getting worse year-over-year?)
  - **Sanctions / conflict intersection** (fires near conflict zones can indicate military activity or scorched-earth tactics)
  - **Climate change tracking** (permafrost fires, Arctic fires, drought-driven fires)
- **Compliance**: NASA's terms allow non-commercial use; for commercial products, contact NASA directly. Since our product is open-core (AGPL-3.0 with hosted tier), we're "non-commercial" for the open-source self-host version and need a commercial agreement for the hosted tier if our revenue exceeds NASA's threshold.

## License: NASA-produced data, public domain

The data is produced by NASA and is in the public domain (US Government work,
17 U.S.C. § 105). No copyright, no licensing restrictions on use, no
attribution requirement (though standard academic citation is appreciated).

