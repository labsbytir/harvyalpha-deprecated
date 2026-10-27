---
tags: [source, climate, tier-1, osint-data, public-no-auth, wmo, mqtt, realtime]
status: proposed
display_name: "WMO WIS2 Global Broker (MQTT) — Real-Time Weather Push"
source_name: wmo_wis2
---

# WMO WIS2 Global Broker (MQTT) — Real-Time Weather Push

WMO Information System 2.0 (WIS2) is the next-generation global weather data exchange. The Global Broker is an MQTT broker that re-publishes weather notifications from all WIS2 member nodes worldwide. **Public read-only access**, with hard-coded `everyone/everyone` credentials. Real-time push, not polling.

## Metadata

| Field | Value |
|---|---|
| Source system | `wmo_wis2` |
| Broker | `mqtts://globalbroker.meteo.fr:8883` |
| Username | `everyone` (public) |
| Password | `everyone` (public) |
| Auth | **Public read-only** (anyone can subscribe) |
| Tier | 1 |
| Axis | climate |
| License | Per publisher (each WMO member sets its own data license) |
| per_tenant_only | false |
| Coverage type | global |
| Operational model | **Long-running subscriber, not a request/response fetcher** |

## Topic hierarchy

WIS2 uses a hierarchical topic structure, e.g.:

```
origin/a/wis2/<centre-id>/data/<dataset>/<subdataset>/<year>/<month>/<day>/...
```

Each notification is a small JSON message pointing to the actual data file (often a BUFR, GRIB, or NetCDF blob stored at a URL). Subscribers pick the topics they care about.

## What you'll see in the messages

- Surface observations (SYNOP) from national networks
- Upper-air soundings
- Forecast bulletins
- Severe weather warnings
- Climate data products
- Marine data
- Aviation METAR / TAF

**Per message:** the data is referenced by URL, not embedded. So you need:
1. A long-running subscriber that listens on the broker
2. A fetcher that pulls the actual file from the URL
3. A parser for BUFR / GRIB / NetCDF (use `ecmwf/cfgrib`, `pybufrkit`, or `xarray`)

## Fetcher

Not yet implemented. Pattern:

1. **Subscriber worker** (long-running) connects to `globalbroker.meteo.fr:8883` with `everyone/everyone`, subscribes to topic pattern like `origin/+/+/data/surface-weather-observations/synop/#`, receives notifications.
2. **HTTP fetcher** (per-message) downloads the referenced file (often a GRIB2 or BUFR).
3. **Parser** converts GRIB2 → structured rows using `cfgrib` (or `eccodes` for more control).
4. **Sink** writes to ClickHouse `osint.bundles` with `source_name='wmo_wis2'`.

This is more infrastructure than a single fetcher function. Phase 1.5+ work.

## Storage

ClickHouse `osint.bundles` with `source_name='wmo_wis2'`. Per-observation rows. Fields depend on parser config — minimum: `station_id`, `time`, `lat`, `lon`, `temp`, `dewpoint`, `pressure`, `wind_speed`, `wind_dir`, `raw_payload_url` (for replay).

## Why I picked this

- **Real-time push.** No polling, no schedule. The moment a station reports, you get it.
- **Truly global.** Every WMO member publishing under WIS2 ends up here.
- **Free, public, no auth beyond the public creds.** The same `everyone` user works for everyone.
- **The future.** WIS2 is the planned successor to GTS; investing now means being on the right side of the transition.

## Gotchas

- **MQTT infrastructure.** Need a long-running subscriber, not a request/response fetcher. Existing fetcher pattern in `ingest/fetchers/` is HTTP-pull; this is a new pattern.
- **GRIB2 / BUFR parsing is non-trivial.** Each dataset has its own schema. Plan for 1-2 weeks of work per parser.
- **Broker is in France.** Latency for non-European subscribers is real but tolerable for OSINT.
- **The `everyone` user is read-only.** Cannot publish. Cannot see private topics. Sufficient for our use.
- **Volume can spike** during severe weather. Plan for backpressure.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[WMO World Weather Information Service (WWIS) JSON API]] — the pull-mode sibling
- [[WMO OSCAR/Surface — Station Metadata REST API]] — for cross-referencing which stations are publishing
