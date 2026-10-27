# Nostr NIP-52 (calendar events) — the data protocol behind protest.net / Flockstr

Key: `none required` — public, free, decentralized. No auth, no rate limit, no API key.
Endpoint: `wss://<relay>` (Nostr relay WebSocket)
Auth: none (Nostr uses public-key cryptography; no central auth)
Format: **Nostr events** (JSON over WebSocket, NIP-01 protocol)

Documentation:
- Nostr protocol: https://github.com/nostr-protocol/nips
- NIP-52 (calendar event): https://github.com/nostr-protocol/nips/blob/master/52.md
- Relay list: https://nostr.watch (live relay directory)
- Flockstr (protest.net's app): https://calendar.protest.net/
- Nostr clients: https://github.com/aljazceru/awesome-nostr

## What it is

**Nostr** ("Notes and Other Stuff Transmitted by Relays") is a
decentralized protocol for social networking. **NIP-52** is the
"Calendar Event" specification — defines how to publish and query
date-based events on the Nostr network.

`protest.net` is a **demo of Flockstr** (`calendar.protest.net`), a
Next.js app that lets users browse NIP-52 calendar events. The
underlying data is **on public Nostr relays** — we can query it
directly without going through the app.

**For our use case**: NIP-52 is the right protocol for **decentralized,
free, no-auth, public event data** — the same shape as Harvard CCC's
protest data but without the centralized curator. Anyone can publish
an event (e.g. "March for X in Y on Z"); the events propagate through
relays; we can subscribe and ingest them.

**Note on protest density**: in my probe of 4 public relays with
`#t: ["protest", "march", "rally", "demonstration", "activism", "action", "blm", "climate", "palestine"]`,
I found only 1 explicitly tagged "protest" event. Most events on
Nostr relays are general community events. **The right ingest
strategy is to filter for the political-action tags we care about, not
to ingest everything.**

## NIP-52 event format

```json
{
  "id": "884f23cc053c6638...",       // SHA-256 of the serialized event
  "pubkey": "b997407dbf9ba1e1...",   // Nostr public key of the organizer
  "created_at": 1788548648,         // Unix timestamp
  "kind": 31923,                    // 31922 = date-based, 31923 = time-based
  "tags": [
    ["d", "89aae3d667e91c70"],      // d-tag: replaceable event identifier
    ["title", "Sactown Social - Turkovich Family Wines"],
    ["summary", "Have a glass of wine and support a merchant accepting btc!"],
    ["image", "https://..."],
    ["start", "2026-09-12T19:00:00Z"],
    ["end", "2026-09-12T22:00:00Z"],
    ["start_tzid", "America/Los_Angeles"],
    ["location", "30471 Buckeye Road · Winters, CA"],
    ["g", "9qceh7wxyz..."],         // geohash (NIP-52)
    ["t", "social"],                 // free-form hashtag
    ["t", "wine"],
    ["organizer", "b997407d...", "Jane Doe"]  // [pubkey, optional name]
  ],
  "content": "Long-form description here",
  "sig": "..."                       // Schnorr signature
}
```

**Key fields**:
- `kind=31922`: date-based (whole-day event)
- `kind=31923`: time-based (event with start/end times)
- `g` tag: geohash (precision ~1 km, perfect for city-level rendering)
- `location` tag: free-text human address
- `start` / `end` tags: ISO-8601 timestamps
- `t` tag: free-form hashtag (searchable)
- `d` tag: replaceable identifier (so updates to the same event don't create duplicates)

## Public relays (the right ones to query)

| Relay | Notes |
|---|---|
| `wss://relay.damus.io` | Damus (iOS), large, well-staffed |
| `wss://relay.nostr.band` | Indexer, good for fast queries |
| `wss://nos.lol` | Community-run, reliable |
| `wss://relayable.org` | Aggregator (multiple relays behind it) |
| `wss://nostr.wine` | Paid relay, good uptime |
| `wss://nostr.mom` | Community-run |
| `wss://purplepag.es` | Profile-only (not for events) |
| `wss://eden.nostr.land` | Community-run |
| `wss://relay.primal.net` | Primal client relay |

Full live list: https://nostr.watch

## Quick call — verify (no key)

```bash
# Install websockets
pip install websockets

# Query for NIP-52 events tagged with "protest"
python3 << 'EOF'
import asyncio, json, ssl, websockets

RELAYS = ["wss://relay.damus.io", "wss://nos.lol", "wss://nostr.wine", "wss://nostr.mom"]

async def query(url, filters):
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    try:
        async with websockets.connect(url, open_timeout=15, ssl=ssl_ctx) as ws:
            await ws.send(json.dumps(["REQ", "probe", filters]))
            events = []
            try:
                while len(events) < 20:
                    msg = await asyncio.wait_for(ws.recv(), timeout=10)
                    data = json.loads(msg)
                    if data[0] == "EVENT":
                        events.append(data[2])
                    elif data[0] in ("EOSE", "CLOSED"):
                        break
            except asyncio.TimeoutError:
                pass
            return events
    except Exception as e:
        return []

async def main():
    filters = {"kinds": [31922, 31923], "#t": ["protest", "march", "rally"], "limit": 20}
    results = await asyncio.gather(*[query(r, filters) for r in RELAYS])
    all_events = {e['id']: e for r in results for e in (r if isinstance(r, list) else [])}
    print(f'  unique events: {len(all_events)}')
    for e in list(all_events.values())[:5]:
        tags = {t[0]: t[1] for t in e.get('tags', []) if isinstance(t, list) and len(t) >= 2}
        print(f"    {e.get('created_at')}  {tags.get('title', ['?'])[0][:60]}")
        print(f"      loc: {tags.get('location', ['?'])[0][:60]}")
        print(f"      geohash: {tags.get('g', [''])[0]}")

asyncio.run(main())
EOF
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/nostr_nip52.py
# Subscribe to NIP-52 calendar events on the public Nostr relay network.
import asyncio
import json
import logging
import ssl
from datetime import datetime, timezone

import websockets

from .base import BaseFetcher, RawBundle

log = logging.getLogger(__name__)

RELAYS = [
    "wss://relay.damus.io",
    "wss://nos.lol",
    "wss://nostr.wine",
    "wss://nostr.mom",
    "wss://relay.nostr.band",
]

# Tags that match our "unrest" axis
PROTEST_TAGS = [
    "protest", "march", "rally", "demonstration",
    "activism", "action", "blm", "climate", "palestine",
    "5050",  # the 50501 movement
    "antifa", "resist",
]


def _ssl_context() -> ssl.SSLContext:
    """SSL context that doesn't verify (Nostr relay certs can be self-signed)."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _query_relay(url: str, filters: dict, timeout: float = 15.0,
                       limit: int = 50) -> list[dict]:
    try:
        async with websockets.connect(
            url, open_timeout=timeout, close_timeout=timeout, ssl=_ssl_context(),
        ) as ws:
            await ws.send(json.dumps(["REQ", "opendosint", filters]))
            events = []
            try:
                while len(events) < limit:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                    data = json.loads(msg)
                    if data[0] == "EVENT":
                        events.append(data[2])
                    elif data[0] in ("EOSE", "CLOSED"):
                        break
            except asyncio.TimeoutError:
                pass
            return events
    except Exception as e:  # noqa: BLE001
        log.warning("[nostr:%s] query failed: %s", url, e)
        return []


def _to_bundle(event: dict) -> RawBundle | None:
    """Map a NIP-52 event to a RawBundle."""
    tags = event.get("tags", [])
    tag_dict = {t[0]: t[1] for t in tags if isinstance(t, list) and len(t) >= 2}
    # NIP-52: title and summary are required for both kinds
    title = (tag_dict.get("title") or ["?"])[0]
    location = (tag_dict.get("location") or [""])[0]
    geohash = (tag_dict.get("g") or [""])[0]
    if not title or title == "?":
        return None
    # Parse start time
    start_str = (tag_dict.get("start") or [""])[0]
    try:
        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
    except ValueError:
        start_dt = datetime.fromtimestamp(event.get("created_at", 0), tz=timezone.utc)
    # All `t` tags become tags
    t_tags = [t[1] for t in tags if isinstance(t, list) and len(t) >= 2 and t[0] == "t"]
    # Geohash → rough lat/lon (decode later in the resolver or dashboard)
    return RawBundle(
        source_system="nostr_nip52",
        source_collection="protests",
        source_id=event.get("id", "?"),
        source_url=f"https://njump.me/{event.get('pubkey', '?')}",
        bundle_url="nostr://" + event.get("id", ""),
        fetched_at=datetime.now(timezone.utc),
        payload=b"",
        payload_format="json",
        byte_size=0,
        is_remote_only=True,
        metadata={
            "title": title,
            "summary": (tag_dict.get("summary") or [""])[0],
            "content": event.get("content", ""),
            "location": location,
            "geohash": geohash,
            "start": start_str,
            "end": (tag_dict.get("end") or [""])[0],
            "organizer_pubkey": event.get("pubkey", ""),
            "tags": t_tags,
            "kind": event.get("kind"),
            "created_at": event.get("created_at"),
        },
    )


class Fetcher(BaseFetcher):
    """Fetches NIP-52 calendar events from public Nostr relays."""

    source_system = "nostr_nip52"
    source_tier = 2  # community-published, mixed quality

    async def fetch(self) -> "AsyncIterator[RawBundle]":  # type: ignore
        filters = {
            "kinds": [31922, 31923],
            "#t": PROTEST_TAGS,
            "limit": 100,
        }
        # Sweep all relays in parallel
        all_events = []
        for relay in RELAYS:
            events = await _query_relay(relay, filters)
            log.info("[nostr:%s] %d events", relay, len(events))
            all_events.extend(events)
        # Dedupe by id
        seen = set()
        unique = []
        for e in all_events:
            eid = e.get("id", "")
            if eid and eid not in seen:
                seen.add(eid)
                unique.append(e)
        log.info("[nostr] %d unique events across %d relays", len(unique), len(RELAYS))
        for e in unique:
            bundle = _to_bundle(e)
            if bundle is not None:
                yield bundle
```

## Notes

- **Tier 2 (community-published)** — the data quality is mixed. Anyone
  can publish a NIP-52 event; some are spam. We can use the
  `organizer` field (Nostr pubkey) to filter for known good
  publishers.
- **License**: **public domain** in spirit — Nostr is a public,
  permissionless protocol. The data is published by individuals
  and is theirs to publish. We can re-publish.
- **For the "unrest" axis** of the 12-axis model: NIP-52 events are a
  **decentralized complement** to the Harvard CCC. The CCC is the
  authoritative curated US protest dataset; NIP-52 is the
  unfiltered long tail (anywhere, anyone, any topic).
- **Update cadence**: real-time. New events appear on relays within
  seconds of being published. We poll daily (or hourly) and ingest.
- **Geocoding**: NIP-52 includes `g` (geohash) and `location`
  (free-text). The geohash is precise enough for city-level
  rendering; the free-text location is for display only. We can
  geocode the free-text with Nominatim if we need a precise address.
- **For v1 of the dashboard**: pull NIP-52 events filtered by
  `["protest", "march", "rally", "demonstration", "blm", "climate",
  "palestine", "5050"]` etc. Show alongside the Harvard CCC data,
  with a "decentralized" badge to distinguish. Useful for users who
  want broader, less-curated coverage.
- **Pair with**: Harvard CCC (authoritative curated US protests) and
  Count Love (2017-2021 historical) for complete global + US protest
  coverage.
- **Real-time alert potential**: subscribe to a relay with a
  websocket, filter for protest tags, push to NATS for the dashboard's
  real-time layer. The data is published in seconds.

## License: public domain (decentralized)

Nostr is a public protocol. Events are published by individuals using
their own public keys. There is no central license; the convention is
that the public domain applies. We can re-publish and re-use freely.

For attribution: include the event's pubkey + npub in the dashboard's
event detail page. Convert pubkey to npub at `https://nostrcheck.com/public/npub.php`.


## Migrated Context (From Nostr NIP-52 Calendar Events (Decentralized Protests).md)

---
tags: [source, unrest, tier-2, osint-data, public-no-auth]
status: active
display_name: "Nostr NIP-52 Calendar Events (Decentralized Protests)"
fetcher: ingest.fetchers.nostr_nip52
source_name: nostr_nip52
---

# Nostr NIP-52 Calendar Events (Decentralized Protests)

NIP-52 calendar events from public Nostr relays. Tagged `protest`, `march`, `rally`, `blm`, `climate`, `palestine`, `5050`, `antifa`, `resist`, `demonstration`, `activism`, `action`. The decentralized data behind protest.net / Flockstr.

## Metadata

| Field | Value |
|---|---|
| Source system | `nostr_nip52` |
| Base URL | wss://relay.damus.io |
| API base | wss://relay.damus.io |
| Schedule (cron) | `0 */6 * * *` (every 6 hours) |
| Rate limit | 30 req/min |
| Tier | 2 |
| Axis | unrest |
| License | NIP-52 (CC0-ish; relay-determined) |
| Auth | none (public relays) |
| per_tenant_only | false |

## Collections

| Name | Tags | Relays | Kinds | Limit |
|---|---|---|---|---|
| `protest_tags` | protest, march, rally, demonstration, activism, action, blm, climate, palestine, 5050, antifa, resist | relay.damus.io, nos.lol, nostr.wine, nostr.mom, relay.nostr.band | 31922, 31923 | 200 |

## Fetcher

`ingest/fetchers/nostr_nip52.py` (WebSocket subscription)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='nostr_nip52'`. Per-event rows: `id`, `pubkey`, `kind`, `content`, `tags[]`, `created_at`, `relay`.

## Common queries

```
GET /v1/sources/nostr_nip52
GET /v1/sources/nostr_nip52/bundles?tag=blm&since=2026-09-01
```

## Gotchas

- **Forward-looking** — NIP-52 events are usually created before the event happens, not after. This is the prediction layer, not the history layer.
- Nostr is pseudonymous; pubkey ≠ real identity. Cross-reference with [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] for confirmation.
- Relays come and go. The relay list is the first thing to update when a relay goes down.

## Related

- [[Plan/Source Categorization]] (unrest axis)
- [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] (historical, structured)
- [[Ingestion/Count Love US Protest Archive (2017-2021)]] (historical cross-validation)


## Migrated Context (From AbuseIPDB IP Abuse Reports.md)

---
tags: [source, cyber, security, tier-2, osint-data, requires-key]
status: active
display_name: "AbuseIPDB IP Abuse Reports"
fetcher: ingest.fetchers.abuseipdb
source_name: abuseipdb
api_key_env: ABUSEIPDB_API_KEY
---

# AbuseIPDB IP Abuse Reports

IP-address abuse reports aggregated from 100k+ contributing networks. 100k IPs/day on the free tier. Per-IP: `abuseConfidenceScore` (0-100), `totalReports`, `lastReportedAt`, `countryCode`, `usageType`, `isp`.

## Metadata

| Field | Value |
|---|---|
| Source system | `abuseipdb` |
| Base URL | https://www.abuseipdb.com |
| API base | https://api.abuseipdb.com/api/v2 |
| Schedule (cron) | `0 8 * * *` (daily at 08:00 UTC) |
| Rate limit | 60 req/min |
| Tier | 2 |
| Axis | cyber, security |
| License | AbuseIPDB terms (free for lookup, paid for bulk) |
| Auth | **Required**: `ABUSEIPDB_API_KEY` |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `blacklist` | `confidence_minimum=90` | the high-confidence abuse list |

## Fetcher

`ingest/fetchers/abuseipdb.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='abuseipdb'`. Per-IP rows.

## Common queries

```
GET /v1/sources/abuseipdb
GET /v1/sources/abuseipdb/bundles?confidence_min=90
```

## Gotchas

- Free tier = 1,000 lookups/day. Don't burn it on per-packet firewall logs.
- `confidence_minimum=90` keeps the signal/noise ratio sane; below 90 is mostly false positives.
- API key in `Authorization: Bearer <key>` header, not URL.

## Related

- [[Plan/Source Categorization]] (cyber + security axes)
- [[Ingestion/crt.sh Certificate Transparency Logs]] (companion: subdomains)
- [[Ingestion/VirusTotal File/URL/IP Reputation]] (companion: file/URL hash)
- [[Ingestion/Shodan IoT/Host Search]] (companion: open ports)

