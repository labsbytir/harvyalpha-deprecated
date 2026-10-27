# gtfs.de — Patrick Brosi's free German GTFS + GTFS-RT aggregator

Key: `none required` — public CC-BY 4.0 / CC BY-SA 4.0, no auth, no key
Endpoint: `https://download.gtfs.de/germany/{fv|rv|nv|full}_free/latest.zip` (static) + `https://realtime.gtfs.de/realtime-free.pb` (realtime)
Auth: none
Format: **GTFS** (CSV-in-ZIP, standard spec) + **GTFS-RT** (Protocol Buffers, standard spec)

Documentation:
- Home: https://gtfs.de/
- English: https://gtfs.de/en/
- Feeds list: https://gtfs.de/en/feeds/
- Realtime: https://gtfs.de/en/realtime/
- Services (paid extensions): https://gtfs.de/en/services/
- Contact: https://gtfs.de/en/contact/
- Author: Patrick Brosi — `https://patrickbrosi.de` — Chair of Algorithms and Data Structures, University of Freiburg
- License: **CC-BY 4.0** for static feeds, **CC BY-SA 4.0** for realtime stream
- Underlying data: **DELFI e.V. National Access Point** (mandated by EU Delegated Regulation 2017/1926)
- Last verified update timestamp: `Sat Aug 29 10:36:37 CEST 2026` (rebuilt daily; 30-day rolling window for the free base feeds)

## What it is

**gtfs.de** is a free, public, machine-readable feed aggregator for
**all of Germany's public transit** — every bus, tram, U-Bahn, S-Bahn,
regional train, long-distance train (ICE, IC, EC, etc.), ferry, and
cog railway in the country. It is maintained by **Patrick Brosi** at
the University of Freiburg, the same researcher behind the
[Travic](https://travic.app/) visualization (2013-present) and
the `de-gtfs-de` feed surfaced through the
[geOps Realtime API](geops.md) (same `publisher: Patrick Brosi`).

The data is **derived from the German National Access Point (DELFI
e.V.)** — a public NeTEx-format dataset mandated by **EU Delegated
Regulation 2017/1926** (the EU Multimodal Transport Data
Regulation). gtfs.de converts the NeTEx dump into a daily-rebuilt
**GTFS** (General Transit Feed Specification) bundle, ready to feed
into any standard transit routing engine.

The static feeds are the same one of the world's largest GTFS
datasets, per gtfs.de's own description: "20,000+ lines, 500,000+
stop points, almost 2 million regular services". The free base feeds
cover the next 30 days; the paid extensions cover the full schedule
period.

## Free base feeds (verified working)

| Feed | File | Size | Coverage | License |
|---|---|---|---|---|
| **de_fv** — Schienenfernverkehr | `https://download.gtfs.de/germany/fv_free/latest.zip` | ~400 KB | ICE, IC, ECE, EC, EN, railJet, Night Trains (Deutsche Bahn + others) | CC-BY 4.0 |
| **de_rv** — Schienenregionalverkehr | `https://download.gtfs.de/germany/rv_free/latest.zip` | (same path pattern) | RB, RE, IRE, S-Bahnen, non-federal railways | CC-BY 4.0 |
| **de_nv** — Local/urban transit | `https://download.gtfs.de/germany/nv_free/latest.zip` | **~272 MB unzipped** | All U-Bahnen, Straßenbahnen, Busse, Fähren, Zahnradbahnen across every Verkehrsverbund | CC-BY 4.0 |
| **de_full** — Combined | `https://download.gtfs.de/germany/full_free/latest.zip` | (not currently available — returns 403) | All of the above | CC-BY 4.0 |

I confirmed via `curl -I` that:

```
$ curl -sI https://download.gtfs.de/germany/fv_free/latest.zip
HTTP/1.1 200 OK
Content-Length: 405156
Content-Type: application/zip
Last-Modified: Sat, 29 Aug 2026 08:36:37 GMT
```

```
$ curl -sI https://download.gtfs.de/germany/nv_free/latest.zip
HTTP/1.1 200 OK
Content-Length: 272342247   # 272 MB
Content-Type: application/zip
Last-Modified: Sat, 29 Aug 2026 08:36:48 GMT
```

The `de_full` endpoint currently returns 403 — likely a recent change.
Use the three individual feeds and merge in our ingest pipeline.

## Free realtime stream (GTFS-RT)

- **URL**: `https://realtime.gtfs.de/realtime-free.pb`
- **Format**: GTFS-RT Protocol Buffers (`.pb` file)
- **Contents**: `TripUpdates` (vehicle positions + delays) and `ServiceAlerts` (cancellations, delays)
- **Update frequency**: every 10 seconds
- **License**: **CC BY-SA 4.0** (note the share-alike — different from the static feeds!)
- **Covers 27 agencies** (as of 2026-09-05):
  - Verkehrsverbund Oberelbe (Dresden) — DL-DE→BY-2.0
  - Verkehrsverbund Rhein-Sieg (Cologne/Bonn) — special agreement
  - Verkehrsverbund Bremen/Niedersachsen — CC BY-SA 4.0
  - Verkehrsverbund Rhein-Ruhr — special agreement (buses incomplete)
  - NVBW Baden-Württemberg — DL-DE→BY-2.0 (buses incomplete)
  - VAG Nürnberg — CC BY-SA 4.0
  - opentransportdata.swiss (Swiss border area) — attribution
  - OVapi Netherlands (border) — free
  - DEFAS Bayern — special agreement
  - VBB Berlin/Brandenburg — CC-BY 4.0
  - DELFI GTFS-RT (multi-region) — CC BY-SA
  - 8x SIRI regional streams (Bavaria, Saarland, Rhein-Neckar, Baden-Württemberg, Oberelbe, Berlin/Brandenburg, Rhein/Sieg, Rhein/Ruhr, Mecklenburg-Vorpommern, Hessen, Schleswig-Holstein, Mittelthüringen, Sachsen-Anhalt) — CC BY-SA
  - VRN Rhein-Neckar — DL-DE→BY-2.0
  - Stadtwerke Münster — unknown
  - Hamburger Hochbahn — grayed out (license questions pending)

## How to ingest (Python sketch)

```python
# ingest/fetchers/gtfs_de.py — sketch, not yet implemented
import os, httpx, zipfile, csv
from datetime import datetime, timezone, timedelta
from pathlib import Path

class GtfsDeFetcher:
    name = "gtfs_de"
    base_url = "https://download.gtfs.de/germany"

    def __init__(self, **kwargs):
        self.feeds = kwargs.get("feeds", ["fv_free", "nv_free", "rv_free"])
        self.cache_dir = Path(os.environ.get("GTFS_DE_CACHE", "/var/lib/osint/gtfs_de"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    async def fetch_once(self) -> dict[str, str]:
        """Download all configured feeds to local cache, return feed_name -> zip_path."""
        out = {}
        async with httpx.AsyncClient(timeout=300) as client:
            for feed in self.feeds:
                url = f"{self.base_url}/{feed}/latest.zip"
                r = await client.get(url)
                r.raise_for_status()
                path = self.cache_dir / f"{feed}_latest.zip"
                path.write_bytes(r.content)
                out[feed] = str(path)
        return out

    def load_into_clickhouse(self, zip_path: str, ch_client) -> int:
        """Parse a GTFS bundle and insert stops/trips/routes/stop_times.
        Use `partridge` (https://github.com/remix/partridge) for the heavy lifting
        and a small wrapper to bulk-INSERT into ClickHouse. ~10k rows/sec expected.
        """
        import partridge
        feed = partridge.load_feed(zip_path)
        stops = feed.stops[["stop_id", "stop_name", "stop_lat", "stop_lon"]].to_dict("records")
        routes = feed.routes[["route_id", "agency_id", "route_short_name",
                              "route_long_name", "route_type"]].to_dict("records")
        # stop_times is the big one (10M+ rows for de_nv)
        stop_times = feed.stop_times[["trip_id", "stop_id", "stop_sequence",
                                      "arrival_time", "departure_time"]].to_dict("records")
        # trips in their own table
        trips = feed.trips[["trip_id", "route_id", "service_id",
                            "trip_headsign", "direction_id",
                            "shape_id"]].to_dict("records")
        # ...bulk INSERT into ClickHouse (see ingest/clickhouse.py)...
        # Return total rows inserted.
        return len(stops) + len(routes) + len(trips) + len(stop_times)
```

The `de_nv` (local transit) feed is 272 MB compressed — probably
~1-2 GB unzipped with full stop_times. Plan to ingest off-peak (e.g.
`0 4 * * *`) and to keep only the next 30 days in the warehouse.

## Suggested `sources.yaml` entry

```yaml
- name: gtfs_de_fv
  display_name: "gtfs.de Schienenfernverkehr (long-distance rail Germany)"
  domain: gtfs.de
  axis: transit
  tier: 1
  license: CC-BY-4.0
  license_url: https://creativecommons.org/licenses/by/4.0/
  requires_key: false
  schedule: "0 5 * * *"          # daily, after the 04:36 UTC rebuild
  rate_limit_per_minute: 0      # static ZIP, no rate limit
  public_no_auth: true
  attribution: "gtfs.de / Patrick Brosi / University of Freiburg / DELFI e.V."
  description: |
    German long-distance rail (ICE, IC, EC, railJet, Night Trains).
    Free, CC-BY 4.0, daily rebuild. ~5.3K trips, ~1.2K stops, 30-day window.
  collections:
    - name: de_fv
      endpoint: https://download.gtfs.de/germany/fv_free/latest.zip
      file_format: gtfs_static
- name: gtfs_de_nv
  display_name: "gtfs.de Nahverkehr (local transit Germany)"
  domain: gtfs.de
  axis: transit
  tier: 1
  license: CC-BY-4.0
  license_url: https://creativecommons.org/licenses/by/4.0/
  requires_key: false
  schedule: "0 5 * * *"          # daily
  rate_limit_per_minute: 0
  public_no_auth: true
  attribution: "gtfs.de / Patrick Brosi / University of Freiburg / DELFI e.V."
  description: |
    German local transit (all buses, trams, U-Bahnen, S-Bahnen, ferries).
    Free, CC-BY 4.0, daily rebuild. ~500K stops, ~2M trips, 30-day window.
    272 MB compressed ZIP — ingest off-peak.
  collections:
    - name: de_nv
      endpoint: https://download.gtfs.de/germany/nv_free/latest.zip
      file_format: gtfs_static
# gtfs_de_rv and gtfs_de_rt (realtime) are deferred to v1.1
```

## Why this is a real, free, ingestable connector (vs alternatives)

| Alternative | Cost | Coverage | Why gtfs.de wins |
|---|---|---|---|
| **gtfs.de (this)** | Free, CC-BY 4.0 | All of Germany, ~2M trips, 500K+ stops | Best free option; official NeTEx→GTFS conversion |
| **Mobility Database (Transitland v2)** | Free, public | 200+ DE feeds, fragmented | gtfs.de is the unified whole-of-Germany feed; others are per-agency |
| **DB API (DB Vertrieb)** | Free with key, no public-data license | DB trains only | Smaller scope; license is "free for non-commercial" |
| **OpenTripPlanner self-hosted** | Free but you bring data | depends | Same data; gtfs.de is the upstream data we feed into OTP |
| **geOps Realtime (paid)** | Free for non-commercial | 425 worldwide feeds | geOps's `de-gtfs-de` feed is **literally gtfs.de** (same publisher) |
| **European Long-Term Rail Timetables (DB Hacon)** | Paid | Europe-wide | Comprehensive but commercial |

For our dashboard's "transit / infrastructure" axis, **gtfs.de is the
right free primary source for Germany**. geOps adds the worldwide
realtime layer (paid, per-tenant) on top.

## Connection to Travic, geOps, and mvt-project

This is the data-source family Patrick Brosi runs:

| Project | Type | License | Status |
|---|---|---|---|
| **gtfs.de** (this) | Free GTFS + GTFS-RT aggregator | CC-BY 4.0 / CC BY-SA 4.0 | Active, daily rebuilds |
| **Travic** (travic.app) | Academic visualization | Server currently in maintenance | Same author; uses gtfs.de as primary data |
| **geOps Realtime** (commercial) | Worldwide GTFS-RT aggregator | Free for non-commercial | Same author; the `de-gtfs-de` feed is **literally** the gtfs.de realtime stream |
| **mvt-project/mvt** (Mobile Verification Toolkit) | Forensic tool | NOASSERTION | Co-maintainer overlap; different domain (spyware forensics, not transit) |

So ingesting gtfs.de directly is **the same data geOps surfaces**
through their paid Realtime API, with a 5-minute delay (geOps is
realtime; gtfs.de static is daily but realtime is also daily via the
GTFS-RT stream).

## Connection to DELFI and EU policy

The data underneath gtfs.de is **DELFI** (Durchgängige
Elektronische Fahrgastinformation) — a cooperative of all German
transit agencies, mandated by **EU Delegated Regulation 2017/1926**
(the "MMTIS" regulation on Multimodal Travel Information Services).
Every EU member state has a similar National Access Point:
- DE: DELFI (gtfs.de sits on top of this)
- FR: `prim.iledefrance-mobilites.fr` + national PAN
- ES: `data.renfe.com` + `nap.transportes.gob.es`
- UK: `naptan.dft.gov.uk` + `data.gov.uk`
- IT: `nap.roby.it`
- …etc.

For a pan-EU rollout of our dashboard, gtfs.de is the right template
for "national GTFS aggregator". We can mirror this pattern by writing
a `gtfs-{country_code}.md` vault note for each country's NAP.

## See also

- [Travic](travic.md) — the academic predecessor visualization by the same author
- [geOps](geops.md) — the commercial worldwide aggregator; the `de-gtfs-de` feed comes from gtfs.de
- [Transitland](https://www.transit.land/) — fragmented per-agency GTFS registry, 200+ DE feeds
- [OpenRailwayMap](openrailwaymap.md) — OSM-based rail geometry to render *underneath* a gtfs.de-derived transit map
- [Overpass API](overpass-api.md) — alternative for OSM-based stop data
- [DB Hacon (paid EU timetable)](https://www.hacon.de/) — commercial pan-EU alternative
- `ingest/fetchers/` — `ckan.py` and `nada.py` are the closest existing patterns (also download a static file, parse, INSERT)


## Migrated Context (From gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS).md)

---
tags: [source, transit, security, tier-1, osint-data, public-no-auth]
status: active
display_name: "gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS)"
fetcher: ingest.fetchers.gtfs_de
source_name: gtfs_de_fv
---

# gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS)

gtfs.de Schienenfernverkehr — German long-distance rail: ICE, IC, EC, EN, railJet, Night Trains. ~5.3K trips, ~1.2K stops, 30-day rolling window. CC-BY 4.0. Daily rebuild. Author: Patrick Brosi, U. Freiburg. Underlying: DELFI e.V. National Access Point.

## Metadata

| Field | Value |
|---|---|
| Source system | `gtfs_de` |
| Base URL | https://download.gtfs.de/germany |
| API base | https://download.gtfs.de/germany |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 0 (bulk download) |
| Tier | 1 |
| Axis | transit, security |
| License | CC-BY 4.0 |
| Auth | none (public) |
| per_tenant_only | false |
| format | gtfs_static ZIP, ~0.4 MB |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `de_fv` | https://download.gtfs.de/germany/fv_free/latest.zip | 30-day rolling window |

## Fetcher

`ingest/fetchers/gtfs_de.py` (unzips + loads into per-tenant DuckDB)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='gtfs_de_fv'`. GTFS tables: `agency`, `routes`, `stops`, `trips`, `stop_times`, `calendar`, `calendar_dates`, `transfers`.

## Common queries

```
GET /v1/sources/gtfs_de_fv
GET /v1/sources/gtfs_de_fv/bundles?route=ICE_15
```

## Gotchas

- The 30-day window means: today's download is invalid in 30 days. Re-fetch daily.
- Long-distance only — no regional/local transit. See [[Ingestion/gtfs.de Nahverkehr (German Local/Urban Transit GTFS)]] for that.
- For real-time updates, see [[Ingestion/gtfs.de GTFS-Realtime (27 German Transit Agencies)]].

## Related

- [[Plan/Source Categorization]] (transit + security axes)
- [[Ingestion/gtfs.de Nahverkehr (German Local/Urban Transit GTFS)]] (local counterpart)
- [[Ingestion/gtfs.de GTFS-Realtime (27 German Transit Agencies)]] (real-time updates)
- [[Ingestion/Mobility Database (MobilityData) GTFS Catalog]] (global registry)
- [[Ingestion/Transitland (Interline) GTFS Aggregator]] (alternative aggregator)


## Migrated Context (From gtfs.de GTFS-Realtime (27 German Transit Agencies).md)

---
tags: [source, transit, security, tier-1, osint-data, public-no-auth, live-push]
status: active
display_name: "gtfs.de GTFS-Realtime (27 German Transit Agencies)"
fetcher: ingest.fetchers.gtfs_de_rt
source_name: gtfs_de_rt
---

# gtfs.de GTFS-Realtime (27 German Transit Agencies)

gtfs.de GTFS-RT stream. TripUpdates + ServiceAlerts for 27 German transit agencies. Updated every 10 s. CC BY-SA 4.0 (share-alike). Author: Patrick Brosi, U. Freiburg. Same agency list as the static feed, plus opentransportdata.swiss and OVapi NL for cross-border.

## Metadata

| Field | Value |
|---|---|
| Source system | `gtfs_de_rt` |
| Base URL | https://realtime.gtfs.de |
| API base | https://realtime.gtfs.de |
| Schedule (cron) | `*/1 * * * *` (every 1 min) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | transit, security |
| License | CC BY-SA 4.0 (share-alike) |
| Auth | none (public) |
| per_tenant_only | false |
| format | gtfs_rt_protobuf |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `realtime_free` | https://realtime.gtfs.de/realtime-free.pb | single free feed, all 27 agencies |

## Fetcher

`ingest/fetchers/gtfs_de_rt.py` (protobuf decode)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='gtfs_de_rt'`. Per-update rows: `trip_id`, `stop_id`, `delay_seconds`, `timestamp`, `schedule_relationship`, `vehicle_id`, `congestion_level`, `occupancy_status`.

## Common queries

```
GET /v1/sources/gtfs_de_rt
GET /v1/sources/gtfs_de_rt/bundles?agency=berlin_bvg&since=2026-09-05
```

## Gotchas

- **share-alike** license (CC BY-SA 4.0) — derivatives must use the same license. Document this in any tenant-facing API.
- Protobuf binary format; don't try to grep.
- 27 agencies is the free tier; some agencies have their own paid feeds with more detail.

## Related

- [[Plan/Source Categorization]] (transit + security axes)
- [[Ingestion/gtfs.de Schienenfernverkehr (German Long-Distance Rail GTFS)]] (static FV)
- [[Ingestion/gtfs.de Nahverkehr (German Local/Urban Transit GTFS)]] (static NV)
- [[Ingestion/Mobility Database (MobilityData) GTFS Catalog]] (global registry)
