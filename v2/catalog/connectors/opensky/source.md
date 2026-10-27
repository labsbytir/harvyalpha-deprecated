# OpenSky Network (live ADS-B flight tracking)

Key: `none required` for `/api/states/all` (anonymous, rate-limited to 100 req/day, 10s data cache, ~10,000 flights per response). For higher limits and access to historical data (`/api/flights/all`, `/api/flights/aircraft`), create a free account at https://opensky-network.org/profile and use the OAuth2 client credentials flow.

Endpoint: `https://opensky-network.org/api/`
Auth: none (anonymous read); `Authorization: Bearer <token>` for authenticated
Format: `JSON`

Documentation:
- API home: https://opensky-network.org/apidoc/
- Swagger: https://opensky-network.org/apidoc/rest.swagger.json
- Forum / docs: https://opensky-network.org/forum/
- Datasets (historical bulk): https://opensky-network.org/datasets/
- Auth tutorial: https://opensky-network.org/forum/t/authentication/577

## How it's used in OpenTIR-Data (real-time fetchers)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/opensky_realtime.py
# This is a special fetcher: it PUSHES live data into ClickHouse rather than crawling.
import os
import json
import time
import asyncio
import httpx
import orjson
from datetime import datetime, timezone
from ingest.clickhouse import ch


OPENSKY_TOKEN = os.environ.get("OPENSKY_TOKEN", "")
BASE = "https://opensky-network.org/api"
POLL_INTERVAL_SECS = 10     # data is cached for 10s; don't poll faster


def make_token():
    """OAuth2 client_credentials flow for OpenSky."""
    if OPENSKY_TOKEN:
        return OPENSKY_TOKEN
    r = httpx.post(f"{BASE}/auth/realms/opensky/protocol/openid-connect/token", data={
        "grant_type": "client_credentials",
        "client_id": os.environ["OPENSKY_CLIENT_ID"],
        "client_secret": os.environ["OPENSKY_CLIENT_SECRET"],
    })
    r.raise_for_status()
    return r.json()["access_token"]


async def main():
    async with httpx.AsyncClient(
        base_url=BASE,
        timeout=30.0,
        headers={"User-Agent": "OpenTIR-Data/0.1",
                 "Authorization": f"Bearer {make_token()}" if OPENSKY_TOKEN else ""},
    ) as client:
        seen_icaos: set[str] = set()
        while True:
            r = await client.get("/states/all")
            r.raise_for_status()
            body = r.json()
            states = body.get("states", [])
            now = datetime.now(timezone.utc)
            rows = []
            for s in states:
                # OpenSky state vector: [icao24, callsign, origin_country, time_position,
                # last_contact, longitude, latitude, baro_altitude, on_ground, velocity,
                # true_track, vertical_rate, sensors, geo_altitude, squawk, spi, position_source]
                icao = s[0]
                if icao in seen_icaos:
                    continue
                if s[5] is None or s[6] is None:  # no lat/lon
                    continue
                seen_icaos.add(icao)
                rows.append({
                    "icao24": icao,
                    "callsign": (s[1] or "").strip(),
                    "country": s[2],
                    "lon": s[5], "lat": s[6],
                    "baro_alt_m": s[7] or 0.0,
                    "on_ground": 1 if s[8] else 0,
                    "velocity_mps": s[9] or 0.0,
                    "heading_deg": s[10] or 0.0,
                    "vertical_rate_mps": s[11] or 0.0,
                    "geo_alt_m": s[13] or 0.0,
                    "squawk": s[14] or "",
                    "source_ts": body.get("time", 0),
                    "ingested_at": now,
                })
            if rows:
                ch.insert_live("opensky_states", rows)
                print(f"[{now.isoformat()}] inserted {len(rows)} new flight states (total in air: {len(states)})")
            # Reset tracker every 5 minutes so we see updates
            if now.minute % 5 == 0:
                seen_icaos.clear()
            await asyncio.sleep(POLL_INTERVAL_SECS)


if __name__ == "__main__":
    asyncio.run(main())
```

## Quick call — verify

```bash
# Live state vector: ~10k flights currently in the air
curl -sL "https://opensky-network.org/api/states/all" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
print('time:', d.get('time'))
print('flights:', len(d.get('states', [])))
print('first 3:')
for s in d['states'][:3]:
    print(' ', s[0], s[1], s[2], s[5], s[6], 'alt', s[7])
"
```

Expected: `time: 1788xxx`, `flights: 8000-12000`, with each state showing `icao24`, `callsign`, `origin_country`, `lon/lat`, `baro_altitude`.

## Endpoints used (verified live 2026-09-04)

```text
GET /api/states/all                                          # all in-air flights
GET /api/states/all?icao24=abc123                            # one aircraft
GET /api/states/all?lamin=46&lomin=6&lamax=48&lomax=8       # bbox
GET /api/states/all?time=1700000000                          # historical snapshot (anon, 1h ago)
GET /api/flights/all?begin=1700000000&end=1700086400         # flights in time range (auth)
GET /api/flights/aircraft?icao24=abc123&begin=...&end=...     # per-aircraft history (auth)
GET /api/flights/icao24/{icao}/{begin}/{end}                 # one aircraft (auth)
GET /api/metadata/flight/aircraft/list                       # full aircraft list (auth)
GET /api/metadata/flight/countries                           # supported countries (auth)
GET /api/metadata/flight/operators                           # operators (auth)
GET /api/metadata/flight/ownStates                           # own-sensor states (auth)
GET /api/auth/realms/opensky/protocol/openid-connect/token   # OAuth2 token
```

State vector fields (22 fields, 0-indexed):
```
0  icao24              hex string, unique aircraft ID
1  callsign            trimmed
2  origin_country      ISO 3166-1 alpha-2
3  time_position       Unix timestamp of last position update
4  last_contact        Unix timestamp of last ADS-B message
5  longitude           WGS-84
6  latitude            WGS-84
7  baro_altitude       meters
8  on_ground           bool
9  velocity            m/s
10 true_track          degrees (0=N, clockwise)
11 vertical_rate       m/s
12 sensors             array of sensor IDs
13 geo_altitude        meters (GNSS)
14 squawk              transponder code (4 octal digits)
15 spi                 special purpose indicator
16 position_source     0=ADS-B, 1=ASTERIX, 2=MLAT
```

## Notes

- **Free tier**: anonymous `/api/states/all` returns the current snapshot, cached for 10 seconds. 100 requests/day for anonymous; 4,000 requests/day for authenticated users; 8,000+ for the higher tiers.
- **Historical data**: `/api/flights/all` and per-aircraft endpoints need auth, and the date range is capped (1 hour for free, 30 days for premium).
- **Bulk historical**: the OpenSky dataset is published as daily Parquet files at `https://opensky-network.org/datasets/raw/`. The Impala shell at `https://opensky-network.org/data/impala/` is a public SQL interface over the same data — useful for queries like "every flight that landed at LHR between 2019-01 and 2020-12".
- **OpenSky vs ADS-B Exchange**: OpenSky is the academic/research-grade network (free, 30+ universities contribute receivers). ADS-B Exchange is the enthusiast-grade network (faster updates, more receivers, paid tier for commercial). The "real-time OSINT" use case usually wants both.
- **Volume signal**: at any given moment there are ~10,000–18,000 aircraft in the air worldwide. The state vector response is ~1 MB. Polling every 10s = ~8.6 GB/day of raw state data, ~2 GB/day after dedup. Compresses ~10x with columnar storage.
- **For the world dashboard**: this is THE single highest-value real-time feed. Combined with OpenFlights airport/route data, you can render live flight tracks, identify unusual patterns (e.g. military aircraft over a conflict zone, diverted flights), and watch the entire world's air traffic live.
- **Latency**: ~1 second from ADS-B reception to API availability. Faster than Twitter, faster than most news feeds.


## Migrated Context (From OpenSky Network Live ADS-B State Vectors.md)

---
tags: [source, security, info_environment, tier-2, osint-data, live-push]
status: active
display_name: "OpenSky Network Live ADS-B State Vectors"
fetcher: ingest.fetchers.opensky
source_name: opensky_live
---

# OpenSky Network Live ADS-B State Vectors

OpenSky Network — crowdsourced ADS-B receiver network. Live state vectors for ~10k aircraft in the air at any moment. Per-aircraft: icao24, callsign, origin_country, time_position, last_contact, lon, lat, baro_altitude, on_ground, velocity, true_track, vertical_rate, sensors.

## Metadata

| Field | Value |
|---|---|
| Source system | `opensky` |
| Base URL | https://opensky-network.org |
| API base | https://opensky-network.org/api |
| Schedule (cron) | `@reboot` (continuous, long-running) |
| Rate limit | 6 req/min (anonymous); 100 req/min with OAuth |
| Tier | 2 |
| Axis | security, info_environment |
| License | Free for non-commercial; data is public |
| Auth | none (public, anonymous); optional OAuth for higher rate |
| per_tenant_only | false |
| live_push | true |

## Collections

| Name | Notes |
|---|---|
| `live_states` | full live state vector stream |

## Fetcher

`ingest/fetchers/opensky.py` (long-running WebSocket/streaming consumer)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='opensky_live'`. Per-aircraft state snapshots every 10 s.

## Common queries

```
GET /v1/sources/opensky_live
GET /v1/sources/opensky_live/bundles?icao24=a4b1c2&since=2026-09-05
```

## Gotchas

- Anonymous rate limit (6 req/min) is not enough for live streaming. Either OAuth up or sample at 10 s intervals.
- icao24 is the 24-bit Mode S transponder address in HEX; join on this for aircraft tracking.
- 10k flights × 6 snapshots/min = 60k rows/min. Compress in ClickHouse.

## Related

- [[Plan/Source Categorization]] (security + info_environment axes)
- [[Ingestion/Cloudflare Radar Internet Trends]] (companion: cyber layer)

