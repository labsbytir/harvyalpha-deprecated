# OpenFlights (airports, airlines, routes reference data)

Key: `none required` — ODbL-licensed (Open Database License) reference data, hosted on GitHub.

Endpoint: `https://raw.githubusercontent.com/jpatokal/openflights/master/data/{name}.dat`
Auth: none
Format: CSV (no headers, no quotes — see column maps below)

Documentation:
- Main: https://openflights.org/
- Data: https://openflights.org/data.php
- Source: https://github.com/jpatokal/openflights
- License: ODbL (https://opendatacommons.org/licenses/odbl/)

## Reference datasets

| File | Size | Rows | Purpose |
|---|---|---|---|
| `airports.dat` | 1.1 MB | ~10,000 | Worldwide airports with IATA/ICAO codes, lat/lon, altitude, timezone, DST, type |
| `airlines.dat` | 397 KB | ~6,000 | Worldwide airlines with IATA/ICAO codes, callsign, country, active status |
| `routes.dat` | 2.4 MB | ~67,000 | All known commercial airline routes: airline, source airport, dest airport, codeshare, stops, equipment |
| `countries.dat` | 6 KB | ~250 | ISO 3166-1 country codes → name, continent, currency, languages |
| `planes.dat` | 8 KB | ~200 | Aircraft models: IATA code, name, capacity |

## How it's used in OpenTIR-Data (static reference data)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/openflights.py
import csv
import io
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

BASE = "https://raw.githubusercontent.com/jpatokal/openflights/master/data"


# OpenFlights CSV has no header. Column maps per file:
AIRPORTS_COLS = ["airport_id","name","city","country","iata","icao",
                 "lat","lon","alt","tz_offset_hr","dst","tz","type","source"]
AIRLINES_COLS = ["airline_id","name","alias","iata","icao","callsign",
                 "country","active"]
ROUTES_COLS = ["airline","airline_id","src_iata","src_airport_id",
               "dst_iata","dst_airport_id","codeshare","stops","equipment"]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            for filename, cols in [
                ("airports.dat", AIRPORTS_COLS),
                ("airlines.dat", AIRLINES_COLS),
                ("routes.dat",   ROUTES_COLS),
                ("countries.dat", None),
                ("planes.dat",    None),
            ]:
                r = await client.get(f"{BASE}/{filename}")
                r.raise_for_status()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection=filename.replace(".dat", ""),
                    source_id=filename,
                    source_url="https://openflights.org/data.php",
                    bundle_url=f"{BASE}/{filename}",
                    fetched_at=self.now(),
                    payload=r.content,
                    payload_format="csv",
                    metadata={"filename": filename, "columns": cols, "size": len(r.content)},
                )
```

## Quick call — verify

```bash
# Airports
curl -sL "https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat" \
  | head -2

# Routes (67k rows)
curl -sL "https://raw.githubusercontent.com/jpatokal/openflights/master/data/routes.dat" \
  | wc -l
```

Expected:
- `airports.dat` first row: `1,"Goroka","Goroka","Papua New Guinea","GKA","AYGA",-6.081689,145.391881,5282,10,"U","Pacific/Port_Moresby","airport","OurAirports"`
- `routes.dat` row count: ~67,000

## Column maps

### airports.dat (14 cols)
```text
airport_id, name, city, country, iata, icao, lat, lon, alt, tz_offset_hr, dst, tz, type, source
```
- `iata` may be `\N` (null) for some smaller airports
- `dst` is a one-char code: E=Europe, A=US/Canada, S=South America, O=Australia, Z=New Zealand, N=None, U=Unknown
- `type` is one of: `airport`, `station`, `port`, `unknown`

### airlines.dat (8 cols)
```text
airline_id, name, alias, iata, icao, callsign, country, active
```
- `active` is `Y` or `N`
- `iata` may be `\N` for cargo-only / private

### routes.dat (9 cols)
```text
airline, airline_id, src_iata, src_airport_id, dst_iata, dst_airport_id, codeshare, stops, equipment
```
- `codeshare` is `Y` or blank
- `stops` is an integer (0 for direct)
- `equipment` is space-separated IATA aircraft type codes (e.g. `738 73G` for 737-800 / 737-700)

## Notes

- **Static reference data.** Re-pull monthly; OpenFlights updates when the community reports changes.
- **Join with OpenSky** for the world dashboard: take the `icao24` from a live OpenSky state, look up the `airline` and `src_iata`/`dst_iata` in OpenFlights, render the flight on a map.
- **Coverage** is biased toward scheduled commercial flights. Charter, private, and military flights are spotty. For military, see [[connectors/opensky]] notes — and consider ADS-B Exchange as a complement.
- **Quality**: ~95% accurate. Some defunct airlines stay in the database, some newer routes are missing. For high-stakes work, cross-check with `cirium.com` or `flightaware.com`.
- **License**: ODbL. Free to use, requires attribution ("OpenFlights"), and any derived database must also be ODbL.
- **For OSINT**: this is the reference layer for "where is flight X going?" Without OpenFlights, you see anonymous state vectors. With it, you see "KLM604 from AMS to LHR" — a real, named operation.

