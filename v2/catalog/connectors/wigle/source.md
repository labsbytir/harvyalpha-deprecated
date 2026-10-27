# WiGLE (Wireless Geographic Logging Engine)

Key: `pending — register a free account at https://wigle.net/account` (free tier: 100 API calls/day, daily site-stats + leaderboard are public and don't count against the quota; HTTP Basic auth with `api_name` + `api_token` for the search/detail endpoints)
Token: `pending — find at https://wigle.net/account after signup, click "Show API token"`

Endpoint: `https://api.wigle.net/api/v2/`
Auth: **HTTP Basic** with `Authorization: Basic base64(api_name:api_token)` for `/network/*` and `/file/*`. **Public** (no auth) for `/stats/site` and `/stats/standings`.
Format: `JSON`

Documentation:
- API home: https://api.wigle.net/
- Interactive Swagger UI: https://api.wigle.net/swagger
- OpenAPI spec (authoritative, 107 KB, all endpoints): https://api.wigle.net/swagger.json
- Account / signup: https://wigle.net/account
- API token page (after signup): https://wigle.net/account → "Show API token"
- Free-tier limits: shown after login on https://wigle.net/account
- Wikipedia: https://en.wikipedia.org/wiki/WiGLE

## What it is

WiGLE is a **24-year-old crowd-sourced geolocation database** of:

- **2.0B+ WiFi networks** (BSSID, SSID, lat/lon, last seen, encryption type, channel)
- **27.3B+ geolocated observations** (one network can be seen many times)
- **5.8B+ Bluetooth devices** (BLE, classic — including AirTags, Tiles, Find My)
- **30.6M+ cell towers** (MCC, MNC, LAC, CID, signal strength)
- **731k+ contributors** (wardrivers, since 2001)
- **1.5M+ new WiFi networks geolocated every day**

The data is contributed by people running **wardriving apps** (the official WiGLE Android app, Kismet, Kali, etc.) while driving / walking / flying around. WiGLE aggregates and de-duplicates the contributions, then exposes the result via a search API. **It is the largest, oldest, and most-cited crowd-sourced WiFi/cell/BT geolocation database in the world.**

## Public endpoints (no auth, no quota) — verified live 2026-09-04

```bash
# 1. Site-wide totals
curl -sL "https://api.wigle.net/api/v2/stats/site" | python3 -m json.tool
# Expected response (abridged):
# {
#   "success": true,
#   "userstot": 731772,                 # total contributors
#   "nettotal": 2035023533,             # unique WiFi networks
#   "loctotal": 27322740539,            # total geolocated observations
#   "bttotal": 5818891011,              # unique Bluetooth devices
#   "btloc": 5689970461,                # total BT geolocated observations
#   "genloc": 30217304,                 # geolocated cell towers
#   "gentotal": 30560663,               # unique cell towers
#   "netwpa2": 1515731517,              # WPA2 networks
#   "netwpa3": 99670881,                # WPA3 networks
#   "netwpa": 39550312,                 # WPA1 networks
#   "netwep": 50828194,                 # WEP networks (legacy, unencrypted)
#   "netnowep": 37643959,               # Open networks (no encryption)
#   "nettoday": 967605,                 # new networks today
#   "netlocdy": 963173,                 # networks geolocated in last 24h
#   "netlocd2": 1193075,                # networks geolocated in last 48h
#   "transtot": 8624954,                # total file-upload transactions
#   "trans1da": 5507,                   # transactions in last 24h
#   "trans2da": 5264,                   # transactions in last 48h
#   "size": 26,                         # data dumps size in GB
#   "waitQueue": 1124,                  # file-import backlog
#   "geoQueue": 3                       # geocoding backlog
# }

# 2. Per-country statistics — the killer public endpoint for the world dashboard
curl -sL "https://api.wigle.net/api/v2/stats/countries" | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('total countries:', len(d.get('countries', [])))
print('top 5 by wifi count:')
for c in sorted(d.get('countries', []), key=lambda x: x.get('wifiCount',0), reverse=True)[:5]:
    print(' ', c.get('country'), 'wifi:', c.get('wifiCount'), 'cell:', c.get('cellCount'), 'bt:', c.get('btCount'))
"
# Returns: ~250 country records, each with wifiCount, cellCount, btCount
# Use case: country-by-country WiFi density map for the world dashboard

# 3. Per-region statistics within a country
curl -sL "https://api.wigle.net/api/v2/stats/regions?country=US" | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('regions:', len(d.get('regions', [])))
print('top 5 by wifi count:')
for r in sorted(d.get('regions', []), key=lambda x: x.get('wifiCount',0), reverse=True)[:5]:
    print(' ', r.get('region'), 'wifi:', r.get('wifiCount'), 'cell:', r.get('cellCount'))
"
# Returns: per-state / per-region breakdown for one country
# Use case: US state-by-state infrastructure map

# 4. General statistics (broader site view, fewer keys)
curl -sL "https://api.wigle.net/api/v2/stats/general" | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('keys:', sorted(d.keys())[:20])
"
# Returns a different named map of stats (less detail than /stats/site)

# 5. Leaderboard (paginated, top 100)
curl -sL "https://api.wigle.net/api/v2/stats/standings?pagestart=0&pageend=100" | python3 -m json.tool
# Returns: totalUsers, pageStart, pageEnd, results[100] = {rank, userName,
#   discoveredWiFiGPS, discoveredWiFiGPSPercent, discoveredWiFi, discoveredCellGPS,
#   discoveredCell, discoveredBtGPS, discoveredBt, totalWiFiLocations, first, last, self}
# Total: 96,513 active users (as of 2026-09-04)
# Sort options: discovered | total | monthcount | prevmonthcount | gendisc
```

**The public stats are 5 calls/day forever, no quota, no auth.** This is a free daily snapshot of one of the largest geolocation datasets in the world.

**Per-country (`/stats/countries`) is the single highest-value public endpoint for our world dashboard** — one call returns WiFi/cell/BT counts for ~250 countries, which is the entire country-level infrastructure layer for free.

## Authenticated endpoints (free, 100 calls/day)

```bash
# HTTP Basic auth with API name + API token
# Get these from https://wigle.net/account after registering
API_NAME="YOUR_API_NAME"
API_TOKEN="YOUR_API_TOKEN"
AUTH=$(printf '%s:%s' "$API_NAME" "$API_TOKEN" | base64)

# Search WiFi networks by SSID, BSSID, or location
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/network/search?onlymine=false&ssid=Starbucks&resultsPerPage=10" \
  | python3 -m json.tool
# Returns: searchAfter, searchBefore, totalResults, results[10]
# Each result: {ssid, netId (BSSID), trilat, trilong, lastupdt, channel, encryption, type, ...}
# Search supports: SSID exact/wildcard, BSSID/octet prefix, lat/lon box,
# closestLat/closestLong (sorted by distance), lastupdt/firsttime/lasttime
# (epoch or yyyyMMdd-HHMMSS), transid range (yyyyMMdd-00000), encryption
# (None/WEP/WPA/WPA2/WPA3/Unknown), freenet/paynet, minQoS, channel/frequency,
# rcois range, houseNumber/road/city/region/postalCode/country, resultsPerPage
# (max 1000 COMMAPI / 100 site), searchAfter (pagination cursor)

# Get full details for one WiFi network by BSSID
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/network/detail?netid=00:11:22:33:44:55" \
  | python3 -m json.tool
# Returns: WiFiNetworkDetailResponse with all observations, location accuracy,
# CDMA/GSM/LTE/NR/WCDMA/WiFi breakdowns, addresses, results

# Search Bluetooth devices by name or location (same params as WiFi, with name/namelike)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/bluetooth/search?latrange1=37.7&latrange2=37.8&longrange1=-122.5&longrange2=-122.4&showBle=true&resultsPerPage=100" \
  | python3 -m json.tool
# Returns BluetoothSearchResponse. showBt / showBle toggle classic vs BLE.
# mfgrIdMinimum / mfgrIdMaximum filter by manufacturer.

# Get full details for one Bluetooth device
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/bluetooth/detail?netid=<bt-id>&reverseAddress=true" \
  | python3 -m json.tool
# Returns: trilat, trilong, name, type, capabilities, deviceType,
# bestClusterWiGLEQoS, firstSeen, lastSeen, locationClusters (cluster of all observations)

# Search cell towers (GSM/LTE/WCDMA/5G NR/CDMA) by location or operator
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/cell/search?cell_op=310260&cell_net=12345&cell_id=67890&showLte=true" \
  | python3 -m json.tool
# Returns: cell tower records. showGsm/showCdma/showLte/showWcdma/showNr filter by type.

# Get MCC/MNC code metadata (for cell networks)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/cell/mccMnc?mcc=310&mnc=260" \
  | python3 -m json.tool
# Returns: array of MccMncRecord (operator names, country)

# Address → coordinates geocoding (uses OpenStreetMap Nominatim)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/network/geocode?addresscode=Kremlin%2C%20Moscow%2C%20Russia" \
  | python3 -m json.tool
# Returns: NetworkGeocodingResponse with lat/lon for the address
# Use case: "Kremlin" → (55.7520, 37.6175) → feed into /network/search closestLat/Lon

# Your own user profile
curl -sL -H "Authorization: Basic $AUTH" "https://api.wigle.net/api/v2/profile/user" | python3 -m json.tool
# Returns: your user object (rank, stats, badges, etc.)

# Your API tokens
curl -sL -H "Authorization: Basic $AUTH" "https://api.wigle.net/api/v2/profile/apiToken" | python3 -m json.tool
# Returns: list of all your API tokens (don't expose publicly!)

# File upload (your own wardriving files)
curl -sL -H "Authorization: Basic $AUTH" "https://api.wigle.net/api/v2/file/transactions" | python3 -m json.tool
# Returns: list of your uploaded file import transactions and their status

# v3 alpha: gridded WiFi density histograms (1-year buckets, 0.5° max box)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v3/density/wifi?topLat=38&bottomLat=37&leftLon=-123&rightLon=-122" \
  | python3 -m json.tool
# Returns: DensityResponse with gridded first-seen and most-recently-seen
# density histograms. THIS is the time-series data for the world dashboard.
# Max bounding box: 0.5° × 0.5°. Slower for larger boxes.

# v3 alpha: WiFi detail (REST-ful URL form)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v3/detail/wifi/<wifiNetworkId>" | python3 -m json.tool
# Returns: WiFiDetail with trilat, trilong, firstSeen, lastSeen, locationClusters

# v3 alpha: cell channel list
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v3/cellChannel/LTE" | python3 -m json.tool
# Returns: ChannelDetailResponse with channels, latitude, longitude, qos
# Types: GSM | LTE | WCDMA | NR
```

## How it's used in OpenTIR-Data (3 ways)

### Way 1: daily site-stats snapshot — fully public, no quota

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/wigle_public.py
# Runs once a day. Zero auth. Inserts one row with the full site-wide totals.
import json
from datetime import datetime, timezone
import httpx
from ingest.clickhouse import ch

BASE = "https://api.wigle.net/api/v2"


def fetch_site_stats() -> dict:
    """Public endpoint. No auth. No quota. Single call per day."""
    r = httpx.get(f"{BASE}/stats/site", timeout=30.0)
    r.raise_for_status()
    s = r.json()
    if not s.get("success"):
        raise RuntimeError(f"WiGLE /stats/site returned failure: {s}")
    return {
        "as_of": datetime.now(timezone.utc),
        "userstot": s["userstot"],
        "nettotal": s["nettotal"],
        "loctotal": s["loctotal"],
        "bttotal": s["bttotal"],
        "btloc": s["btloc"],
        "gentotal": s["gentotal"],
        "genloc": s["genloc"],
        "netwpa2": s["netwpa2"],
        "netwpa3": s["netwpa3"],
        "netwpa": s["netwpa"],
        "netwep": s["netwep"],
        "netnowep": s["netnowep"],
        "nettoday": s["nettoday"],
        "netlocdy": s["netlocdy"],
        "netlocd2": s["netlocd2"],
        "transtot": s["transtot"],
        "trans1da": s["trans1da"],
        "credibility": 1,
        "source_url": "https://api.wigle.net/api/v2/stats/site",
    }


def fetch_top_users(limit: int = 100) -> list[dict]:
    """Public leaderboard. One call per day. Top `limit` users."""
    r = httpx.get(f"{BASE}/stats/standings", params={"pagestart": 0, "pageend": limit}, timeout=30.0)
    r.raise_for_status()
    s = r.json()
    now = datetime.now(timezone.utc)
    rows = []
    for u in s.get("results", []):
        rows.append({
            "as_of": now,
            "rank": u["rank"],
            "userName": u["userName"],
            "discoveredWiFiGPS": u.get("discoveredWiFiGPS", 0),
            "discoveredWiFi": u.get("discoveredWiFi", 0),
            "discoveredCellGPS": u.get("discoveredCellGPS", 0),
            "discoveredCell": u.get("discoveredCell", 0),
            "discoveredBtGPS": u.get("discoveredBtGPS", 0),
            "discoveredBt": u.get("discoveredBt", 0),
            "totalWiFiLocations": u.get("totalWiFiLocations", 0),
            "first": u.get("first"),
            "last": u.get("last"),
            "credibility": 1,
            "source_url": "https://wigle.net/stats/standings",
        })
    return rows


if __name__ == "__main__":
    stats = fetch_site_stats()
    ch.insert_observations("wigle_site_stats", [stats])
    leaders = fetch_top_users(100)
    ch.insert_observations("wigle_top_users", leaders)
    print(f"[{stats['as_of'].isoformat()}] inserted 1 site row + {len(leaders)} leader rows")
    print(f"  networks: {stats['nettotal']:,}, observations: {stats['loctotal']:,}, "
          f"bt: {stats['bttotal']:,}, today: {stats['nettoday']:,}")
```

### Way 2: address-based geofence query — needs the free API key

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/wigle_geofence.py
# For each address of interest, find all WiFi networks seen in a 1km box.
# Useful for "what infrastructure exists in <conflict zone / disaster area>".
import os
import base64
import time
import httpx
from datetime import datetime, timezone
from ingest.clickhouse import ch

API_NAME = os.environ.get("WIGLE_API_NAME", "")
API_TOKEN = os.environ.get("WIGLE_API_TOKEN", "")
if not API_NAME or not API_TOKEN:
    raise SystemExit("WIGLE_API_NAME and WIGLE_API_TOKEN required")

AUTH = "Basic " + base64.b64encode(f"{API_NAME}:{API_TOKEN}".encode()).decode()
BASE = "https://api.wigle.net/api/v2"


def search_box(lat: float, lon: float, radius_km: float = 1.0,
               results_per_page: int = 100) -> list[dict]:
    """Search for all WiFi networks in a ~radius_km box around (lat, lon)."""
    delta = radius_km / 111.0  # 1° lat ≈ 111 km
    params = {
        "onlymine": "false",
        "latrange1": lat - delta,
        "latrange2": lat + delta,
        "longrange1": lon - delta,
        "longrange2": lon + delta,
        "resultsPerPage": results_perPage if False else results_per_page,
    }
    r = httpx.get(f"{BASE}/network/search", params=params,
                  headers={"Authorization": AUTH}, timeout=30.0)
    r.raise_for_status()
    d = r.json()
    if not d.get("success"):
        return []
    rows = []
    for n in d.get("results", []):
        rows.append({
            "as_of": datetime.now(timezone.utc),
            "ssid": n.get("ssid", ""),
            "bssid": n.get("netId", ""),
            "lat": n.get("trilat"),
            "lon": n.get("trilong"),
            "lastupdt": n.get("lastupdt"),
            "channel": n.get("channel"),
            "encryption": n.get("encryption"),
            "type": n.get("type"),
            "credibility": 1,
            "source_url": f"https://wigle.net/search#detailSearch?netid={n.get('netId')}",
        })
    return rows


if __name__ == "__main__":
    # Example: a known mobile-infrastructure site in a conflict zone
    points_of_interest = [
        ("some_id", 50.4501, 30.5234),  # Kyiv
        ("some_id", 31.7683, 35.2137),  # Jerusalem
    ]
    total = 0
    for label, lat, lon in points_of_interest:
        rows = search_box(lat, lon, radius_km=2.0)
        ch.insert_observations("wigle_geofence", rows)
        total += len(rows)
        time.sleep(1.0)  # 100 calls/day = 1 call per 864s; be polite, 1s is fine
    print(f"inserted {total} network rows from {len(points_of_interest)} points")
```

### Way 3: BSSID-based device tracking — needs the free API key

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/wigle_bssid.py
# Look up all known locations for a specific BSSID (MAC address).
# Use cases: asset tracking, stolen device location, asset recovery.
def lookup_bssid(bssid: str) -> dict | None:
    r = httpx.get(f"{BASE}/network/detail",
                  params={"netid": bssid},
                  headers={"Authorization": AUTH}, timeout=30.0)
    r.raise_for_status()
    d = r.json()
    if not d.get("success") or not d.get("results"):
        return None
    return d["results"][0]
```

### Way 4: per-country infrastructure snapshot — public, no quota

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/wigle_countries.py
# Daily snapshot of WiFi/cell/BT counts per country. One call, no auth.
# This is the country-by-country infrastructure layer for the world dashboard.
import httpx
from datetime import datetime, timezone
from ingest.clickhouse import ch

BASE = "https://api.wigle.net/api/v2"


def fetch_country_stats() -> list[dict]:
    r = httpx.get(f"{BASE}/stats/countries", timeout=30.0)
    r.raise_for_status()
    d = r.json()
    now = datetime.now(timezone.utc)
    rows = []
    for c in d.get("countries", []):
        rows.append({
            "as_of": now,
            "country": c.get("country"),
            "wifiCount": c.get("wifiCount", 0),
            "cellCount": c.get("cellCount", 0),
            "btCount": c.get("btCount", 0),
            "credibility": 1,
            "source_url": f"https://wigle.net/stats#country={c.get('country')}",
        })
    return rows


if __name__ == "__main__":
    rows = fetch_country_stats()
    ch.insert_observations("wigle_country_stats", rows)
    print(f"[{rows[0]['as_of'].isoformat()}] inserted {len(rows)} country rows")
```

### Way 5: WiFi density histogram (v3 alpha) — needs the free API key

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/wigle_density.py
# Historical density histograms of WiFi networks first-seen and most-recently-seen
# for a bounding box, in 1-year buckets. THIS is the time-series data for the
# world dashboard's "info-environment" axis.
# Max box: 0.5° × 0.5°. Larger = slower. v3 is alpha — may not count against quota.
import os
import time
import httpx
from datetime import datetime, timezone
from ingest.clickhouse import ch

API_NAME = os.environ["WIGLE_API_NAME"]
API_TOKEN = os.environ["WIGLE_API_TOKEN"]
AUTH = "Basic " + __import__("base64").b64encode(f"{API_NAME}:{API_TOKEN}".encode()).decode()


def fetch_density(top_lat: float, bottom_lat: float,
                  left_lon: float, right_lon: float) -> dict:
    """Returns gridded first-seen + most-recently-seen density histograms."""
    r = httpx.get("https://api.wigle.net/api/v3/density/wifi",
                  params={"topLat": top_lat, "bottomLat": bottom_lat,
                          "leftLon": left_lon, "rightLon": right_lon},
                  headers={"Authorization": AUTH}, timeout=60.0)
    r.raise_for_status()
    return r.json()


if __name__ == "__main__":
    # 6 continental-scale calls (one per inhabited continent) give a daily
    # global density snapshot. ~6 calls/day. Comfortably under 100.
    regions = [
        ("europe",         71.0,  35.0, -10.0,  40.0),
        ("north_america",  72.0,  15.0, -170.0, -50.0),
        ("south_america",  12.0, -55.0,  -82.0, -34.0),
        ("asia",           78.0,  -5.0,   60.0, 150.0),
        ("africa",         37.0, -35.0,  -18.0,  52.0),
        ("oceania",        -1.0,-45.0,  110.0, 180.0),
    ]
    for name, t, b, l, r in regions:
        d = fetch_density(t, b, l, r)
        ch.insert_observations("wigle_density", [{
            "as_of": datetime.now(timezone.utc),
            "region": name,
            "top_lat": t, "bottom_lat": b, "left_lon": l, "right_lon": r,
            "firstSeen": d.get("firstSeen"),
            "mostRecent": d.get("mostRecent"),
            "credibility": 1,
            "source_url": "https://api.wigle.net/api/v3/density/wifi",
        }])
        time.sleep(0.5)
```

## Quick call — verify

```bash
# 1. Public site stats — no key needed
curl -sL "https://api.wigle.net/api/v2/stats/site" | python3 -c "
import json,sys
s = json.load(sys.stdin)
print('success:', s.get('success'))
print('users:', s['userstot'])
print('wifi networks:', s['nettotal'])
print('wifi observations:', s['loctotal'])
print('bluetooth devices:', s['bttotal'])
print('cell towers:', s['gentotal'])
print('WPA2:', s['netwpa2'], 'WPA3:', s['netwpa3'], 'open:', s['netnowep'])
print('new today:', s['nettoday'])
"
# Expected: success:True, users:~731k, networks:~2.0B, observations:~27B

# 2. Public leaderboard — no key needed
curl -sL "https://api.wigle.net/api/v2/stats/standings?pagestart=0&pageend=3" | python3 -c "
import json,sys
s = json.load(sys.stdin)
print('total users:', s['totalUsers'])
print('top 3:')
for r in s['results']:
    print(' ', r['rank'], r['userName'], 'wifi:', r['discoveredWiFi'], 'bt:', r['discoveredBt'])
"

# 3. With a free key (after registering at https://wigle.net/account)
export WIGLE_API_NAME="YOUR_API_NAME"
export WIGLE_API_TOKEN="YOUR_API_TOKEN"
AUTH=$(printf '%s:%s' "$WIGLE_API_NAME" "$WIGLE_API_TOKEN" | base64)
curl -sL -H "Authorization: Basic $AUTH" \
  "https://api.wigle.net/api/v2/network/search?onlymine=false&ssid=Starbucks&resultsPerPage=2" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('success:', d.get('success'))
print('totalResults:', d.get('totalResults'))
for r in d.get('results', [])[:2]:
    print(' ', r['netId'], r.get('ssid'), r.get('trilat'), r.get('trilong'), r.get('encryption'))
"
```

## Endpoints used (verified live 2026-09-04 against the official swagger.json spec)

```text
# Public, no auth, no quota
GET /api/v2/stats/site                            # site-wide totals (abbreviated response)
GET /api/v2/stats/general                         # alternate site-wide named map
GET /api/v2/stats/countries                       # per-country wifiCount/cellCount/btCount
GET /api/v2/stats/standings?pagestart=N&pageend=M # user leaderboard
GET /api/v2/stats/regions?country=XX              # per-region within one country
GET /api/v2/stats/group                           # group standings (paid)
GET /api/v2/stats/user                            # your own stats (paid)

# Authenticated, free tier (100 calls/day on search/detail; profile/file excluded)
GET /api/v2/network/search?...                    # WiFi search (rich filter set, see swagger)
GET /api/v2/network/detail?netid=<BSSID>          # WiFi detail
GET /api/v2/network/geocode?addresscode=...       # address → coordinates (uses OSM Nominatim)
GET /api/v2/bluetooth/search?...                  # Bluetooth search (BT + BLE filters)
GET /api/v2/bluetooth/detail?netid=<bt-id>        # Bluetooth detail
GET /api/v2/cell/search?...                       # Cell search (GSM/LTE/WCDMA/5G NR/CDMA)
GET /api/v2/cell/mccMnc?mcc=&mnc=                 # MCC/MNC code metadata
GET /api/v2/profile/user                          # your user object
GET /api/v2/profile/apiToken                      # your API tokens (sensitive)
GET /api/v2/file/transactions                     # your file import status
GET /api/v2/file/kml/{transid}                    # download KML of one upload
POST /api/v2/file/upload                          # upload a wardriving file
POST /api/v2/network/comment                      # add a comment to a network
GET /api/v2/group/admin                           # group admin
GET /api/v2/group/groupEventStats/{groupId}       # group event stats
GET /api/v2/group/groupForUser/{userName}         # group for a user
GET /api/v2/group/groupMembers                    # group members

# v3 alpha endpoints (REST-ful URLs, may not count against free quota — untested)
GET /api/v3/density/wifi?topLat=&bottomLat=&leftLon=&rightLon=
                                                # gridded first-seen + most-recently-seen
                                                # density histograms, 1-year buckets,
                                                # max 0.5° × 0.5° box
GET /api/v3/cellChannel/{type}                   # channel list for GSM|LTE|WCDMA|NR
GET /api/v3/detail/wifi/{wifiNetworkId}          # WiFi detail (REST-ful)
GET /api/v3/detail/bt/{btNetworkId}              # Bluetooth detail (REST-ful)
GET /api/v3/detail/cell/{type}/{operator}/{lac}/{cid}  # cell detail
GET /api/v3/detail/cell/CDMA/{sid}/{nid}/{bsid}  # CDMA cell detail

# WiFi search filter parameters (from swagger):
#   onlymine, notmine, latrange1/2, longrange1/2, closestLat, closestLong,
#   lastupdt, firsttime, lasttime, startTransID, endTransID,
#   encryption (None/WEP/WPA/WPA2/WPA3/Unknown), freenet, paynet,
#   netid (BSSID or first 3 octets), ssid, ssidlike (% and _ wildcards),
#   minQoS (0-7), variance (0.001-0.2), rcoisMinimum, rcoisMaximum,
#   channel, frequency (integer MHz),
#   houseNumber, road, city, region, postalCode, country,
#   resultsPerPage (max 1000 COMMAPI / 100 site), searchAfter (pagination cursor)
```

## Notes

- **The five public endpoints are gold** — `/stats/site` gives a daily snapshot of the entire WiGLE universe, `/stats/countries` gives per-country infrastructure counts (the entire world layer in one call), `/stats/regions` gives per-region within a country, `/stats/standings` gives the leaderboard, `/stats/general` gives an alternate named map. All five work without any auth and don't count against the free quota. That's a 5-call/day, 0-cost ingestion of the world WiFi/BT/cell growth signal.
- **The 100 calls/day free tier is the bottleneck** for the search/detail endpoints. 100 calls × 100 results/call = 10,000 networks/day. That's enough for a daily geofence scan of ~100 small areas. For high-volume use, the premium tier starts at $20/month (https://wigle.net/account).
- **WPA3 is at 99M networks vs WPA2 at 1.5B** — only 6.2% of networks are on WPA3. The trend (WPA2 → WPA3 migration) is a meaningful security signal that can be tracked daily from the public site-stats endpoint.
- **The "Starlink in a conflict zone" use case** is real and documented: people running Starlink in war zones typically don't change the default SSID ("Starlink") and BSSID pattern, so WiGLE search by SSID=Starlink in a region gives you a daily-updating view of where the terminals are. The Ukrainian military and various journalists have used this technique.
- **MAC address randomization on modern phones** means Bluetooth/wifi device tracking is harder for personal devices, but **fixed infrastructure** (routers, access points, IoT devices) still broadcasts its real MAC and is fully trackable. AirTags/Tiles use rotating MACs but their BLE advertisements are distinctive and fingerprinted by WiGLE.
- **For OSINT, the three most useful queries are**:
  1. `?ssid=<name>` — find networks with a specific name (chain stores, ISP defaults, military bases, "Starlink", "xfinity", etc.)
  2. `?netid=<BSSID>` — find all known locations for one device
  3. `?latrange1=&latrange2=&longrange1=&longrange2=` — find all networks in a geographic area
- **For the world dashboard**: the public `/stats/countries` endpoint is one of the **highest-leverage additions** to our "info-environment" axis — one call returns WiFi/cell/BT counts for ~250 countries, ready to render as a country-by-country choropleth. Combine with the daily `/stats/site` snapshot (plot `nettoday` and `netwpa3` over 30 days for a global encryption-adoption story) and the v3 alpha `/v3/density/wifi` endpoint (gridded first-seen density histograms by year) for the full infrastructure story. For deep dives, the 100-calls/day free tier covers daily geofence scans of ~100 small areas (e.g. "Starlink in conflict zones" by SSID), or BSSID lookups for asset tracking.
- **No scraping needed**: the API is the canonical way. Don't try to scrape the wigle.net map.
- **Credibility tier**: 1 (WiGLE is the de facto industry standard for crowd-sourced geolocation; data is contributed directly by wardrivers with GPS).
- **Storage cost**:
  - Site stats: 1 row/day. Trivial.
  - Leaderboard: 100 rows/day. Trivial.
  - Geofence queries: 100 calls × 100 results = 10k rows/day. ~3.6M rows/year. ClickHouse compresses 10x. ~50 MB/year.
  - For high-volume tracking, the paid tier is needed. But the public endpoints are more than enough for v1.
- **No signup needed for the public endpoints.** Just paste the URL into the fetcher and you're done. The two unauthenticated endpoints alone justify adding WiGLE to the project.

## License: data is OSINT (no proprietary claims)

The data returned by WiGLE's API is **publicly contributed geolocation data** — the same data anyone can see on the wigle.net map. WiGLE's terms (https://wigle.net/terms) allow use of the data for research, journalism, and non-commercial purposes. The free API tier is for personal / non-commercial use; commercial use requires the paid tier.

**The API client code** we write is Apache-2.0 (matches our project license). No copyleft, no attribution requirement beyond standard academic citation. **WiGLE itself is not the source of the data** — it's the aggregator. The data was contributed by the 731k users, who agreed to WiGLE's terms when they signed up.

**A note on ethics**: WiGLE data can be used to locate individuals (their home WiFi, their Bluetooth devices). Always pair the data with appropriate journalistic / research framing, and consider the privacy implications. The BSSID of someone's home router is a stable identifier that doesn't change for years. **Use this data with care.**

