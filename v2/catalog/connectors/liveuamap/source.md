# Liveuamap (usprotests.liveuamap.com, ukraine.liveuamap.com, etc.)

Key: `pending — paid API. Pro $150/month, Enterprise $1000+/month. Get key at https://me.liveuamap.com/devapi`
Endpoint: `https://usprotests.liveuamap.com/api` (and 14+ other regional maps)
Auth: API key required (paid subscription)
Format: **GeoJSON**

Documentation:
- US Protests: https://usprotests.liveuamap.com/
- API home: https://usprotests.liveuamap.com/api
- API pricing: $150/mo Pro, $1000+/mo Enterprise
- All regional maps: https://{ukraine,syria,venezuela,iraq,iran,sudan,kashmir,asia,libya,california,latam,usa,koreas,usprotests}.liveuamap.com
- Source: https://github.com/liveuamap/liveuamap (PHP, Apache-2.0)
- About: https://liveuamap.com/about

## What it is

**Liveuamap** is a nonprofit, volunteer-run project of civic journalism
that maps real-time global events. Started in 2014 to track the
Ukraine-Russia conflict, it has expanded to **15+ regional maps**:
Ukraine, Syria, Venezuela, Iraq, Iran, Sudan, Kashmir, Asia, Libya,
California, Latin America, USA, Korea, and **US Protests**.

The data is **hand-curated by volunteers** from open sources (news, social
media, government reports) and plotted on interactive maps with
**26 event categories** (Bus, Artillery, Airplane, Helicopter, Camp,
Capture, Dead, Fights, Fires, Injures, Molotovs, Police, Gun, Speech,
Stop, Tanks, Thugs, Nuke, Warship, Gas, Drone, **Rally**, Hostage, etc.).

**The `usprotests.liveuamap.com` map** is the US-specific variant —
focused on US protest activity. It reuses the war-tracking schema,
so the data is a mix of protest events AND adjacent incidents (police
activity, infrastructure events) that the volunteers tag as relevant.

## ⚠️ The catch: it's paid

The data is **not freely exported**. To get programmatic access:

| Tier | Cost | Quota | Coverage |
|---|---|---|---|
| Pro | **$150/month** | 200 req/day, GeoJSON | All regions |
| Enterprise | **$1000+/month** | 1500 req/day | All regions, areas of interest, local languages, priority support |

The `/rss` and `/atom.xml` URLs **return the API pricing page** (HTML), not real feeds. The free view of the website is human-only; the data is the product.

**This makes Liveuamap one of the few paid connectors in our vault.**
For our product, the recommendation is:
- **v1**: do NOT use Liveuamap. The free alternatives (Harvard CCC + Count Love + Nostr NIP-52 + ACLED) cover the same use case better and at $0/month.
- **v2**: consider Liveuamap's **$150/month Pro tier** as a paid "real-time conflict" layer for the active war zones (Ukraine, Sudan, Myanmar), where their volunteer speed is genuinely valuable.

## Quick call — verify

```bash
# Without an API key, the endpoint returns an error
curl -sL "https://usprotests.liveuamap.com/api" 
# Expected: {"success":false,"error_code":98,"message":"Error! Bad api name!"}
# (You need a specific apiName= parameter + API key)

# The free /rss URL is not a real feed
curl -sL "https://usprotests.liveuamap.com/rss" | head -5
# Expected: HTML "Liveuamap API - Discovery Explorer" (the pricing page)

# The site is the source of truth (human-readable only)
curl -sL "https://usprotests.liveuamap.com/" | grep -oE 'src="[^"]*\.js' | head -3
# The map data is loaded client-side from a private API
```

## How it would be used (if/when we pay for the API)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/liveuamap.py
# Optional connector: requires paid API key.
# Skip for v1 — the free alternatives are better.
import os
import httpx
from datetime import datetime, timezone, timedelta
from ingest.clickhouse import ch

LIVEUAMAP_API_KEY = os.environ.get("LIVEUAMAP_API_KEY", "")
LIVEUAMAP_API_NAME = os.environ.get("LIVEUAMAP_API_NAME", "protests")
# Map of regional map → API endpoint
REGIONS = {
    "usprotests": "https://usprotests.liveuamap.com/api",
    "ukraine": "https://ukraine.liveuamap.com/api",
    "syria": "https://syria.liveuamap.com/api",
    "sudan": "https://sudan.liveuamap.com/api",
}


async def fetch_liveuamap_events(region: str, since_iso: str = None) -> list[dict]:
    """Fetch events from one regional Liveuamap map."""
    if not LIVEUAMAP_API_KEY:
        return []
    base = REGIONS[region]
    params = {
        "apiName": LIVEUAMAP_API_NAME,
        "apiKey": LIVEUAMAP_API_KEY,
        "act": "getMarkers",
        "from": since_iso or (datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),
    }
    r = httpx.get(base, params=params, timeout=60.0)
    r.raise_for_status()
    data = r.json()
    return data.get("markers", [])


def to_observation(marker: dict, region: str) -> dict:
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "region": region,
        "title": marker.get("name", ""),
        "lat": marker.get("lat", 0),
        "lon": marker.get("lng", 0),
        "category_id": marker.get("type_id", 0),
        "category_name": marker.get("type_name", ""),
        "timestamp": marker.get("timestamp", 0),
        "source": marker.get("source_text", ""),
        "source_url": marker.get("source_link", ""),
        "credibility": 2,  # Liveuamap = volunteer-curated, tier 2
    }
```

## Notes

- **The data quality is real** — Liveuamap is volunteer-run but the
  data is hand-curated and updated in real-time. For active war
  zones, it's the fastest non-paywalled source.
- **The categories are war-tracking** — Bus, Artillery, Tank, etc.
  are useful for Ukraine/Syria/Sudan but mostly noise for US
  Protests. The relevant US Protests category is `Rally` (id 22).
- **The "usprotests" sub-project is small** — most Liveuamap effort
  goes to Ukraine/Sudan/Syria. The US Protests site is a secondary
  effort.
- **Source code is Apache-2.0**, so we COULD self-host. But the
  data sources (volunteer-aggregated) are not bundled, and the
  default admin password is admin/admin (a known UAMAP weakness,
  mentioned in the README). Not recommended for production.
- **Better free alternatives** for our use case:
  - **Harvard CCC** (https://dataverse.harvard.edu/dataverse/crowdcountingconsortium) — 200k US protest events, CC-BY 4.0, fully geocoded
  - **Count Love** (https://countlove.org/data/events.json) — 38k US events 2017-2021, CC-BY 4.0
  - **Nostr NIP-52** (`wss://relay.damus.io`, etc.) — decentralized global events, free, real-time
  - **ACLED** (https://acleddata.com) — international, including protests, paid for commercial
  - **External APIs** (https://www.External APIsproject.org) — news mentions of protests, free, mass-scale
  - **Overpass API** + `surveillance:type=ALPR` (in OSM) — wait, that's for ALPRs, not protests. Sorry, wrong bullet.

The free alternatives are **better for our product**:
- More events (Harvard CCC has 200k vs UAMAP's ~few thousand)
- More reliable (academic curation vs volunteer speed)
- No rate limit (Harvard CCC: one bulk download, vs UAMAP's 200 req/day cap)
- No cost

The one place where Liveuamap wins is **real-time speed in active
war zones** (Ukraine, Sudan, Myanmar). If a customer wants that
specifically, the $150/month Pro tier is fair.

## License: Apache-2.0 (code), but data is paid

- **Liveuamap source code**: Apache-2.0 (https://github.com/liveuamap/liveuamap/blob/master/LICENSE)
- **Liveuamap data**: requires paid API key. Not redistributable without a license.
- **Self-hosting**: technically possible (Apache-2.0) but the volunteer-aggregated data is not bundled; you'd have to re-implement the source collectors. Not recommended.

## Recommendation for OpenTIR-Data

**Do not add Liveuamap to the default `sources.yaml`.** The free
alternatives (Harvard CCC + Count Love + Nostr NIP-52) are better
for our use case:

| Use case | Best free source | Why |
|---|---|---|
| US protest history (2017+) | Harvard CCC | 200k events, CC-BY, fully geocoded, academic |
| US protest history (2017-2021) | Count Love | 38k events, CC-BY, cross-validation |
| Global real-time protests | Nostr NIP-52 | Decentralized, no rate limit, real-time |
| International political violence | ACLED | 2M+ events, academic rigor, free for non-commercial |
| News mentions of protests | External APIs | Billions of events, free, real-time |
| **Real-time war-zone events** | **Liveuamap** (paid) | **The only option for sub-minute latency in active conflicts** |

If the product grows and a customer specifically wants the Liveuamap
real-time war layer, add it as a paid, opt-in connector. Document the
cost and the alternative clearly so customers understand what they're
paying for.


## Migrated Context (From EU Consolidated Financial Sanctions List.md)

---
tags: [source, sanctions, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "EU Consolidated Financial Sanctions List"
fetcher: ingest.fetchers.eu_sanctions
source_name: eu_sanctions
---

# EU Consolidated Financial Sanctions List

EU Consolidated Financial Sanctions List — Council of the European Union. CC-BY 4.0. Updated daily. Free XML download at `webgate.ec.europa.eu/fsd/fsf/public/files` (full sanctions list, persons, entities). Pairs with [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] for the US side. ~50K entries. Also has a geospatial view at sanctionsmap.eu (no API; HTML scrape for the map polygons).

## Metadata

| Field | Value |
|---|---|
| Source system | `eu_sanctions` |
| Base URL | https://www.sanctionsmap.eu |
| API base | https://webgate.ec.europa.eu/fsd/fsf/public/files |
| Schedule (cron) | `0 5 * * *` (daily at 05:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | sanctions |
| License | CC-BY 4.0 |
| Auth | none (public) |
| per_tenant_only | false |
| format | xml |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `fsdl_full` | https://webgate.ec.europa.eu/fsd/fsf/public/files/cspfullsanlist_1_1.xml | GET | XML |
| `fsdl_persons` | https://webgate.ec.europa.eu/fsd/fsf/public/files/csppersons_1_1.xml | GET | XML |
| `fsdl_entities` | https://webgate.ec.europa.eu/fsd/fsf/public/files/cspentities_1_1.xml | GET | XML |

## Fetcher

`ingest/fetchers/eu_sanctions.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='eu_sanctions'`. Per-entry rows.

## Common queries

```
GET /v1/sources/eu_sanctions
GET /v1/sources/eu_sanctions/bundles?program=UKR
GET /v1/sources/eu_sanctions/aggregates?group_by=program,type
```

## Gotchas

- Three files: `cspfullsanlist_1_1.xml` (full), `csppersons_1_1.xml` (persons only), `cspentities_1_1.xml` (entities only). Use `full` for the canonical picture.
- ~50K entries; larger than OFAC SDN (~13K).
- Geospatial view at [sanctionsmap.eu](https://www.sanctionsmap.eu) — no API, requires HTML scraping (not in scope here).
- CC-BY 4.0 attribution required: "European Union, 2024, https://sanctionsmap.eu".

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (sanctions axis)
- [[Ingestion/OFAC Specially Designated Nationals (SDN) List]] (US counterpart)
- [[Ingestion/CIVICUS Monitor Civic-Space Ratings]] (sanctioned states context)


## Migrated Context (From YouTube Live TV Channels (International News).md)

---
tags: [source, info_environment, conflict, tier-2, osint-data, public-no-auth, live-push]
status: active
display_name: "YouTube Live TV Channels (International News)"
fetcher: ingest.fetchers.live_tv_hub
source_name: live_tv_channels
---

# YouTube Live TV Channels (International News)

29 international news channels via YouTube live embeds. Geocoded to broadcast HQ. The "Live TV Hub" dashboard widget — embedded YouTube live streams of major international news channels, suitable for the [[Architecture/Edge Stack|world dashboard]].

## Metadata

| Field | Value |
|---|---|
| Source system | `youtube_live` |
| Base URL | https://www.youtube.com |
| API base | https://www.youtube.com/embed/live_stream |
| Schedule (cron) | `live` (always running) |
| Rate limit | 60 req/min |
| Tier | 2 |
| Axis | info_environment, conflict |
| License | per-channel YouTube terms (free for embedding) |
| Auth | none (public) |
| per_tenant_only | false |
| live_push | true |

## Collections

| Name | Notes |
|---|---|
| `channels` | 29 channels, list at `/data/live_tv_channels.json` |

## Fetcher

`ingest/fetchers/live_tv_hub.py` (list-management; no real-time API calls)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='live_tv_channels'`. One row per channel with `channel_id`, `name`, `country`, `language`, `hq_lat`, `hq_lon`, `youtube_embed_url`.

## Common queries

```
GET /v1/sources/live_tv_channels
GET /v1/sources/live_tv_channels/bundles?language=ar
```

## Gotchas

- The 29 channels come from a curated JSON file (`/data/live_tv_channels.json`), not from the YouTube API. Channels can go offline without notice.
- Adopted from the mathdroid/karnak (situation.watch) pattern.
- The embed URL pattern is `https://www.youtube.com/embed/live_stream?channel=<channel_id>`.

## Related

- [[Plan/Source Categorization]] (info_environment + conflict axes)
- [[Ingestion/GDELT 2.0 Global Events Database]] (companion: what those channels are reporting)
- [[Architecture/Edge Stack]] (this is a dashboard widget, not raw data)

