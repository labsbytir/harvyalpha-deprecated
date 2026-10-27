# NOAA Storm Prediction Center + NWS API (tornadoes + severe weather)

Key: `none required` for NOAA SPC and api.weather.gov. The Iowa Mesonet
backup uses a contact-required service.
Endpoint: `https://api.weather.gov/` (primary) + `https://www.spc.noaa.gov/` (secondary)
Auth: none (User-Agent required for api.weather.gov per their TOS)
Format: `JSON`, `Cap-XML` (Common Alerting Protocol), `ATOM` (RSS)

Documentation:
- NWS API home: https://www.weather.gov/documentation/services-web-api
- NWS API base: https://api.weather.gov/
- SPC home: https://www.spc.noaa.gov/
- SPC outlooks: https://www.spc.noaa.gov/products/outlook/
- SPC storm reports (today): https://www.spc.noaa.gov/climo/torn/
- Iowa Mesonet (backup): https://mesonet.agron.iastate.edu/

## What it is

For US tornado + severe weather data, the canonical source is the
**NOAA Storm Prediction Center (SPC)**. For global severe weather alerts
(including tornadoes), the canonical source is the **NWS api.weather.gov**.

The combination of these two gives us:

- **Real-time tornado warnings** (SPC issues tornado watches; local NWS
  offices issue tornado warnings; api.weather.gov surfaces both)
- **Storm reports** (confirmed tornado touchdowns, hail, wind damage)
- **Daily / weekly / monthly tornado statistics** (from SPC)
- **Severe weather outlooks** (categorical, probabilistic)

For non-US tornadoes, **the situation is harder** — there's no global
tornado equivalent of NASA FIRMS or USGS Earthquakes. The best free
sources are:
- **European Severe Storms Laboratory (ESSL)**: European tornado + severe
  weather database at `https://www.essl.org/`
- **International Best Track Archive for Climate Stewardship (IBTrACS)**:
  tropical cyclones globally (not tornadoes, but related)
- **Tornadoes in Australia / NZ / Japan / Argentina** are reported by
  national weather services, mostly via news media.

## api.weather.gov endpoints (verified live 2026-09-05)

```text
# Active alerts (all severities, all types)
GET /alerts/active
GET /alerts/active?area=US
GET /alerts/active?severity=Extreme
GET /alerts/active?event=Tornado

# Single alert
GET /alerts/{id}

# Filter by state / zone
GET /alerts/active?area=OK
GET /alerts/active?zone=OKZ025

# Cap-XML format (the canonical emergency alert format)
GET /alerts/active.cap
```

Each alert has:
- `event`: "Tornado Warning" | "Tornado Watch" | "Severe Thunderstorm Warning" | ...
- `severity`: "Extreme" | "Severe" | "Moderate" | "Minor" | "Unknown"
- `certainty`: "Observed" | "Likely" | "Possible" | "Unlikely" | "Unknown"
- `urgency`: "Immediate" | "Expected" | "Future" | "Past" | "Unknown"
- `headline`: short description
- `description`: full text
- `area`: list of affected regions
- `effective`, `expires`, `sent`: timestamps
- `geometry`: GeoJSON polygon for the affected area

## SPC endpoints (verified live 2026-09-05)

```text
# Today's tornado reports (CSV, updated every 5 min during severe weather)
GET /climo/torn/YYMMDD-torn.csv  (e.g. 260905-torn.csv for Sept 5 2026)
GET /climo/torn/

# SPC outlook archive
GET /products/outlook/archive/YYYY/MMDD/ (HTML)
```

The tornado CSV format: state, tornado number, time (UTC), f-scale, lat, lon, count.

## Quick call — verify (no key)

```bash
# All active tornado warnings
curl -sL -H "User-Agent: OpenTIR-Data/0.1 (+https://opentir.org)" \
  "https://api.weather.gov/alerts/active?event=Tornado" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
features = d.get('features', [])
print('Active tornado warnings:', len(features))
for f in features[:3]:
    p = f['properties']
    print(f'  {p[\"event\"]} | {p[\"headline\"]}')
"

# All active severe alerts
curl -sL -H "User-Agent: OpenTIR-Data/0.1 (+https://opentir.org)" \
  "https://api.weather.gov/alerts/active?severity=Extreme,Severe" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('Active Extreme/Severe alerts:', len(d.get('features', [])))
"

# SPC tornado reports for today
curl -sL "https://www.spc.noaa.gov/climo/torn/260905-torn.csv" | head -5
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/nws_tornadoes.py
# Real-time US tornado + severe weather alerts.
import httpx
from datetime import datetime, timezone
from ingest.clickhouse import ch

NWS_BASE = "https://api.weather.gov"
HEADERS = {"User-Agent": "OpenTIR-Data/0.1 (+https://opentir.org)",
           "Accept": "application/geo+json"}


def fetch_active_tornado_alerts() -> list[dict]:
    """Fetch all active tornado warnings + watches in the US."""
    r = httpx.get(f"{NWS_BASE}/alerts/active",
                  params={"event": "Tornado"},
                  headers=HEADERS, timeout=30.0)
    r.raise_for_status()
    d = r.json()
    rows = []
    now = datetime.now(timezone.utc)
    for f in d.get("features", []):
        p = f["properties"]
        rows.append({
            "as_of": now,
            "alert_id": f["id"],
            "event": p.get("event", ""),
            "severity": p.get("severity", ""),
            "certainty": p.get("certainty", ""),
            "urgency": p.get("urgency", ""),
            "headline": p.get("headline", ""),
            "description": p.get("description", ""),
            "area": ", ".join(p.get("area", [])),
            "effective": p.get("effective", ""),
            "expires": p.get("expires", ""),
            "sender": p.get("senderName", ""),
            "credibility": 1,  # NWS = tier 1
            "source_url": p.get("uri", ""),
        })
    return rows


if __name__ == "__main__":
    rows = fetch_active_tornado_alerts()
    if rows:
        ch.insert_observations("nws_alerts", rows)
    print(f"inserted {len(rows)} active tornado alerts")
```

## Notes

- **api.weather.gov requires a User-Agent** that identifies you. We set
  `"OpenTIR-Data/0.1 (+https://opentir.org)"` per the NWS TOS.
- **Rate limit**: 1 request per second for api.weather.gov (officially
  recommended, not enforced).
- **Coverage**: US only for api.weather.gov; global for some SPC products.
- **SPC tornado CSVs** are per-day (YYYY-MM-DD format). Polling today's
  file every 5 minutes gives near-real-time updates during severe weather.
- **For the "natural disaster" axis** in our world dashboard: pair with
  NASA FIRMS (fires), USGS Earthquakes (earthquakes), GDACS (multi-hazard),
  and Smithsonian GVP (volcanoes). US tornadoes via api.weather.gov.
- **For non-US tornadoes**: scrape the ESSL database or use national
  weather services. We don't have a clean global tornado API.
- **Credibility tier**: 1 (NOAA = primary source).
- **Volume**: ~1,000 tornado warnings/year in the US. Negligible storage.

## License: NOAA public domain

NOAA data and NWS API responses are in the public domain (US Government
work, 17 U.S.C. § 105). Free for any use, attribution to "NOAA / National
Weather Service" is appreciated.

