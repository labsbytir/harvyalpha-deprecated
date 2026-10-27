# GDACS (Global Disaster Alert and Coordination System)

Key: `none required` — public, no auth, no key. Run by the European Commission
Joint Research Centre (JRC) in cooperation with UN OCHA.
Endpoint: `https://www.gdacs.org/gdacsapi/api/`
Auth: none
Format: `GeoJSON` (default), `JSON`, `RSS`, `KML`

Documentation:
- API home: https://www.gdacs.org/gdacsapi/
- API docs: https://www.gdacs.org/gdacsapi/
- Coverage: https://www.gdacs.org/About/Coverage.aspx
- Real-time map: https://www.gdacs.org/
- Wikipedia: https://en.wikipedia.org/wiki/Global_Disaster_Alert_and_Coordination_System

## What it is

GDACS is a **real-time multi-hazard alert system** run by the **European
Commission's Joint Research Centre (JRC)** in partnership with **UN OCHA
(UN Office for the Coordination of Humanitarian Affairs)**. It provides
near-real-time alerts for:

- **Earthquakes** (M5.0+ globally; merged from USGS + EMSC)
- **Tropical cyclones** (worldwide, from NOAA NHC + JMA + IMD)
- **Floods** (from GloFAS + national agencies)
- **Volcanoes** (from Smithsonian GVP + national observatories)
- **Wildfires** (from NASA FIRMS + EFFIS, for high-impact events)
- **Droughts** (less frequent)

Each event has a **color-coded alert level** (Green = low impact, Orange =
moderate, Red = high) and includes population exposure estimates, affected
country/region, and source attribution.

**This is the best single source for "geopolitical risk"** because it
covers the natural-disaster events that drive humanitarian crises, which
in turn drive conflict, displacement, and economic disruption.

## API endpoints (verified live 2026-09-05)

```text
# GeoJSON event list
GET /gdacsapi/api/events/geteventlist/SEARCH?fromDate=2026-09-01&toDate=2026-09-04
GET /gdacsapi/api/events/geteventlist/SEARCH?fromDate=2026-09-01&toDate=2026-09-04&alertlevel=Green;Orange;Red
GET /gdacsapi/api/events/geteventlist/SEARCH?eventtype=EQ&fromDate=2026-08-01&toDate=2026-09-05

# Single event detail
GET /gdacsapi/api/events/geteventdetail/1001314

# Per type (EQ, TC, FL, VO, WF, DR)
GET /gdacsapi/api/events/geteventlist/EQ?fromDate=2026-08-01&toDate=2026-09-05
GET /gdacsapi/api/events/geteventlist/TC?fromDate=2026-08-01&toDate=2026-09-05

# Geographic search
GET /gdacsapi/api/events/geteventlist/SEARCH?bbox=-10,30,40,72&fromDate=2026-08-01&toDate=2026-09-05
```

**Parameters**:
- `fromDate`, `toDate` (YYYY-MM-DD; max ~12 months range per call)
- `alertlevel` (semicolon-separated: `Green`, `Orange`, `Red`)
- `eventtype` (EQ | TC | FL | VO | WF | DR)
- `country` (ISO 3166-1 alpha-3)
- `bbox` (west,south,east,north)
- `format` (json | geojson | rss | kml)

## Quick call — verify (no key)

```bash
# Last week's events, GeoJSON
curl -sL "https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?fromDate=2026-08-29&toDate=2026-09-05&alertlevel=Green;Orange;Red" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('count:', len(d.get('features', [])))
print('first 3:')
for f in d['features'][:3]:
    p = f['properties']
    print(f'  {p[\"eventtype\"]} | {p[\"name\"]} | alert={p[\"alertlevel\"]} | {p.get(\"country\", \"\")}')
"

# Earthquakes only
curl -sL "https://www.gdacs.org/gdacsapi/api/events/geteventlist/EQ?fromDate=2026-09-01&toDate=2026-09-05" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('EQs in last 5 days:', len(d.get('features', [])))
"
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/gdacs.py
# Daily pull of high-impact global events.
import httpx
from datetime import datetime, timezone, timedelta
from ingest.clickhouse import ch

BASE = "https://www.gdacs.org/gdacsapi/api"

EVENT_TYPE_NAMES = {
    "EQ": "earthquake", "TC": "tropical_cyclone", "FL": "flood",
    "VO": "volcano", "WF": "wildfire", "DR": "drought",
}


def fetch_recent_events(days: int = 7,
                        min_alert: str = "Green") -> list[dict]:
    """Fetch all events from the last `days` at or above `min_alert`."""
    levels = {"Green": 1, "Orange": 2, "Red": 3}
    wanted = [k for k, v in levels.items() if v >= levels[min_alert]]
    today = datetime.now(timezone.utc)
    start = (today - timedelta(days=days)).strftime("%Y-%m-%d")
    end = today.strftime("%Y-%m-%d")
    url = f"{BASE}/events/geteventlist/SEARCH"
    r = httpx.get(url, params={
        "fromDate": start, "toDate": end,
        "alertlevel": ";".join(wanted),
    }, timeout=60.0)
    r.raise_for_status()
    d = r.json()
    rows = []
    for f in d.get("features", []):
        p = f["properties"]
        geom = f["geometry"]["coordinates"] if f.get("geometry") else [None, None]
        rows.append({
            "as_of": today,
            "gdacs_id": p.get("eventid"),
            "episode_id": p.get("episodeid"),
            "name": p.get("name", ""),
            "event_type": EVENT_TYPE_NAMES.get(p.get("eventtype", ""), p.get("eventtype", "")),
            "alert_level": p.get("alertlevel", ""),
            "country": p.get("country", ""),
            "iso3": p.get("iso3", ""),
            "from_date": p.get("fromdate", ""),
            "to_date": p.get("todate", ""),
            "lon": geom[0] if len(geom) > 0 else None,
            "lat": geom[1] if len(geom) > 1 else None,
            "severity": p.get("severity", ""),
            "population": p.get("population", ""),
            "vulnerability": p.get("vulnerability", ""),
            "description": p.get("description", ""),
            "htmldescription": p.get("htmldescription", ""),
            "credibility": 1,  # JRC + UN OCHA = tier 1
            "source_url": p.get("url", ""),
        })
    return rows


if __name__ == "__main__":
    rows = fetch_recent_events(days=7, min_alert="Orange")
    if rows:
        ch.insert_observations("gdacs_events", rows)
    print(f"inserted {len(rows)} high-impact events (last 7 days, Orange+)")
```

## Notes

- **Tier 1 OSINT source** — run by the European Commission's JRC and UN
  OCHA. The most authoritative multi-hazard alert system in the world.
- **Used by every UN agency, every EU emergency service, every major
  disaster-response NGO** (Red Cross, MSF, OCHA, etc.) and every major
  newsroom. The-world-now.com's "geopolitical-risk" page is largely GDACS
  data repackaged.
- **Coverage**: global. 12-month rolling window for queries; older data
  is in the static database.
- **Volume**: ~100-200 events per week; ~5,000-10,000 per year. Negligible
  storage.
- **Rate limit**: not published, but use at < 1 req/sec.
- **Credibility tier**: 1 (EC + UN = primary source).
- **License**: GDACS is a public service. Terms at https://www.gdacs.org/About/Terms.aspx
  allow free use with attribution. Suitable for any use including commercial.
- **For the world dashboard**: this is the **"disaster" axis** in the
  12-axis model. Pair with:
  - **USGS Earthquakes** for more granular EQ data
  - **NASA FIRMS** for more granular wildfire data
  - **Smithsonian GVP** for more granular volcano data
  - **NOAA NHC** for tropical cyclone tracks
- **Comparison to other sources**:
  - **ReliefWeb**: humanitarian reports (slower, more detailed, but not
    real-time alerts)
  - **OCHA FTS**: financial tracking (different data, not a substitute)
  - **ACLED**: conflict events (different category — political violence,
    not natural disasters)
- **For the "geopolitical-risk" view of the dashboard**: pair GDACS with
  ACLED, UCDP, and External APIs for a complete "what's happening in the world"
  picture. GDACS = natural disasters driving displacement, ACLED = political
  violence, UCDP = organized conflict, External APIs = news/event mentions.

## License: EC + UN OCHA public service

GDACS is a public service provided by the European Commission (JRC) and
UN OCHA. Free for any use including commercial. Attribution to "GDACS /
EC JRC / UN OCHA" is required and should appear in any published work.

