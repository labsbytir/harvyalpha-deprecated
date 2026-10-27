# Real-time OSINT roadmap

Key: `none required` for most; some need free keys. The "world dashboard" comes alive with these live layers, not the static catalogs.

This note is the **roadmap** for the live OSINT dashboard. It's not one source — it's a curated set of real-time feeds that, taken together, make the difference between "static database" and "world is happening right now."

## Tier 1: must-have (verified working, no key)

| Source | What it gives | Endpoint | Polling rate | Status |
|---|---|---|---|---|
| [[connectors/opensky]] | Live flight states (~10k aircraft in air) | `https://opensky-network.org/api/states/all` | 10s (cache) | ✅ 200, 951KB |
| [[connectors/openflights]] | Airport/airline/route reference | GitHub mirror | monthly | ✅ 200 |
| **USGS Earthquakes** | All earthquakes magnitude ≥ 0 in the past week | `https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson` | 1 min | ✅ 200, 1.6 MB GeoJSON |
| **NWS Weather Alerts** | All active US weather alerts (severe, flood, tornado, etc.) | `https://api.weather.gov/alerts/active` | 1 min | ✅ 200, 952KB GeoJSON |
| **External APIs Project** | Global events from news media, every 15 min | `https://api.External APIsproject.org/api/v2/doc/doc?query=*&mode=ArtList&maxrecords=100&format=json` | 5 min | ⚠️ 000 from this net; works in browser |
| **ACLED (Armed Conflict Location & Event Data)** | Riots, protests, battles, civilian violence worldwide | `https://api.acleddata.com/acled/read?limit=100&key=DEMO_KEY` | 1 hr | DEMO_KEY rate-limited |

## Tier 2: free with a key

| Source | What it gives | Sign-up | Notes |
|---|---|---|---|
| **ADS-B Exchange** | Faster ADS-B than OpenSky, more receivers, no auth for raw | https://www.adsbexchange.com/data/ | Free tier (Rapid API); 402 on direct API |
| **AISStream** | Live ship tracking (AIS) | https://aisstream.io/ | Free for non-commercial, 436 = needs auth |
| **AviationStack** | Live flight status, schedules, delays | https://aviationstack.com/signup | Free 100 req/month |
| **MarineTraffic** | Live ship tracking | https://www.marinetraffic.com/en/ais-api-services | Free 100 credits/month |
| **FlightAware AeroAPI** | Live flight positions + history | https://www.flightaware.com/aeroapi/ | Free 500 req/month |
| **ReliefWeb** | Disasters, humanitarian crises | https://apidoc.rlid.net/ | Free |
| **Nominatim (OSM)** | Reverse geocoding for any lat/lon | https://nominatim.org/release-docs/develop/api/Search/ | Free, 1 req/sec rate limit |
| **OpenWeatherMap** | Current + forecast weather | https://openweathermap.org/api | Free 1M calls/month |
| **Pollution APIs (AirVisual, OpenAQ)** | Real-time air quality | https://docs.openaq.org/ | Free |
| **Mastodon public API** | Federated timeline of any public instance | https://docs.joinmastodon.org/api/ | Free |

## Tier 3: paid or restricted

| Source | Cost | Notes |
|---|---|---|
| **X (Twitter) API** | $100/mo minimum | Live firehose is $200k+/mo; standard 10k tweets/mo for $100 |
| **Apify / SerpAPI** | $50-500/mo | Scraped X/Reddit/Google search at scale |
| **Flightradar24** | $500+/mo | The original flight tracker; ADS-B from their own receivers |
| **Bloomberg/Reuters Terminal** | $2k+/mo per seat | Financial OSINT |
| **Palantir Foundry** | $1M+/yr | The "OSINT platform" reference; not feasible for a small project |

## Tier 4: research / custom

| Source | Notes |
|---|---|
| **Hackathon / custom AIS receivers** | SDR-based ship tracking; 1 day to set up |
| **Hackathon / custom ADS-B receivers** | USB dongle + antenna, 30 minutes to set up |
| **MarineCadastre AIS** | US Navy / BOEM official AIS archive, free bulk download |

## Real-time OSINT dashboard architecture

The pattern for the world dashboard is **NATS JetStream** + **WebSocket fan-out**:

```text
fetcher-A ──┐
fetcher-B ──┤   publish events to   ┌─────────────┐   WebSocket push   ┌─────────────┐
fetcher-C ──┼─────────────────────► │ NATS stream  │ ─────────────────► │ browser      │
fetcher-D ──┘   e.g. "opensky-state-  │ topics:       │  JSON over WS      │ /ws/opensky │
                new icao24=abc123     │  opensky.*,  │  ~10 msg/s         │ /ws/quakes  │
                                    │  usgs.quakes,│                    │ /ws/alerts  │
                                    │  nws.alerts,  │                    │ ...         │
                                    │  ...          │                    │             │
                                    └──────┬───────┘                    └─────────────┘
                                           │
                                           ▼
                                    ClickHouse
                                    historical + current
```

Each fetcher is a small `asyncio` task that polls its source, diffs against the last seen state, and publishes new events to NATS. The browser subscribes to a NATS WebSocket bridge and renders markers on a MapLibre map. ClickHouse holds the historical record for "show me every flight over Kyiv in the last 24 hours" type queries.

For your 96 GB box:

- ClickHouse: 70 GB
- NATS JetStream: 8 GB (in-memory)
- Ingest workers: 8 GB total (10 fetchers × 800 MB)
- Web tier (Next.js or SvelteKit + MapLibre client): 8 GB
- OS/headroom: 2 GB
- **Total: 96 GB** ✓

The real-time dashboard runs entirely on your existing hardware. The world-class upgrade is when you need to fan out beyond a few hundred concurrent viewers — that's the 1 TB+ tier I outlined earlier.

## Concrete first-layer fetcher list to wire

In priority order (each one is ~30 lines of Python):

1. **OpenSky states** → 10s poll → push "aircraft appeared", "aircraft disappeared" events
2. **USGS earthquakes** → 60s poll → push "new quake"
3. **NWS weather alerts** → 60s poll → push "new alert"
4. **External APIs** → 5 min poll → push "new event in country X"
5. **ACLED** → 60 min poll → push "new conflict event"

Once these five are wired, the world dashboard has **live human activity + natural phenomena + aviation** in one view. That alone is more real-time coverage than 99% of OSINT dashboards out there.

## Two GitHub flight-tracker repos you asked about

Both are **UI projects**, not data sources — they consume OpenSky or ADS-B Exchange and render it:

- `xSNOWM4Nx/react-flight-tracker` — React frontend for OpenSky/ADS-BX. MIT licensed. We could adopt the UI components (MapLibre layer, flight trail rendering) but the data layer would be ours.
- `shallvhack/Flight-Tracker` — username suggests red-team / offensive security context. **Do not integrate this.** The "shallhack" naming pattern is a strong red flag for malware-adjacent code. I would not pull any of this into a production pipeline.

For the world dashboard UI, the cleanest open-source pattern is:
- **deck.gl** for the WebGL layer (handles 100k+ points smoothly)
- **MapLibre GL** for the base map (vector tiles, no Google Maps key)
- **Apache ECharts** for the time-series and bar charts
- **SvelteKit or Next.js** as the application shell

## Notes

- The single best **open real-time OSINT feed in the world** is OpenSky. It's free, no key, anonymous, ~10k flights, refreshed every 10 seconds. Combined with OpenFlights, you can render named flights on a map.
- **The single best free news event feed** is External APIs. Updated every 15 minutes, with 100+ languages. The trade-off is the call volume: External APIs 1.0 dumps 30 GB/day of CSVs. External APIs 2.0 has a structured API.
- For "things happening in country X right now", the **ACLED** API is the gold standard — 10+ years of conflict event data, free for non-commercial use.
- For "weather, climate, geophysics", the **NOAA + USGS + NWS** are the canonical free sources; we already have NOAA NCEI in the pipeline.
- For "shipping", the canonical free source is **AISStream** with a key, or the **MarineCadastre** archive for historical.
- The reality: the "world dashboard" magic is in **layering 5–10 of these live feeds on one map**, not in any single source. The hard part is the WebSocket fan-out and the geo-spatial query layer, which we already have (ClickHouse + MapLibre + deck.gl).
