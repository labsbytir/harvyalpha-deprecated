# OWID Tech Radar (MIT-licensed, forked from Zalando)

Key: `none required` — **MIT-licensed** (Copyright 2017-2022 Zalando SE). This is one of the few OWID repos you can fork, modify, and self-host without restriction.

Endpoint (live demo): `https://owid.github.io/tech-radar/`
Endpoint (raw index.html with the data inline): `https://raw.githubusercontent.com/owid/tech-radar/master/docs/index.html`
Auth: none
Format: HTML (the radar data is embedded as a JS object literal in `index.html`)

Documentation:
- Repo: https://github.com/owid/tech-radar
- Live: https://owid.github.io/tech-radar/
- Upstream: https://github.com/zalando/tech-radar
- The radar.js library: https://github.com/owid/tech-radar/blob/master/docs/radar.js
- License: MIT (Copyright 2017-2022 Zalando SE; OWID fork is also MIT)

## What this is (and what it isn't)

This is **not a data source** for our OSINT pipeline. It's a small static page that visualizes what tech OWID uses:

```text
                    ADOPT          TRIAL         ASSESS          HOLD
                  (use widely)  (in production) (eval)         (avoid)
Languages         TypeScript,                                        Stata,
                  Python                                            R
Infrastructure    Buildkite,                                         Multi-purpose
                  GH Actions,                                        servers
                  LXC containers
Publication                                                       Walden
Data Management    ETL, Fast track,                                Walks-through
                   Snapshots
```

A tech radar is a one-page visualization of an organization's technology choices, plotted on a **4×4 grid**:
- **Quadrants** (axes) = categories (Languages, Infrastructure, Publication, Data Management)
- **Rings** (concentric) = adoption status (Adopt, Trial, Assess, Hold)
- **Entries** = individual technologies, positioned by category + adoption status
- **Movement** (up/down triangle) = whether a tech moved between rings since the last review

It's a fantastic tool for **decision transparency** in any tech org. Zalando invented it; OWID forked it with their own data; it's MIT so anyone can use it.

## The data (extracted from the live HTML)

The radar data is **inline in `docs/index.html`** as a JavaScript object literal. There is no separate JSON or CSV file. To ingest it you parse the HTML and extract the `entries:` array.

Current OWID entries (last updated 2023.01, the file may not have changed since):

| Quadrant | Ring | Label | Note |
|---|---|---|---|
| Languages | ADOPT | TypeScript | OWID's main frontend language |
| Languages | ADOPT | Python | ETL, data, ML |
| Languages | ASSESS | R | research/stats, not production |
| Languages | HOLD | Stata | legacy, moving away |
| Infrastructure | ADOPT | LXC containers | virtualization |
| Infrastructure | ADOPT | Buildkite | CI/CD (see [[connectors/ourworldindata]] for the buildkite badges) |
| Infrastructure | ADOPT | Github Actions | secondary CI |
| Infrastructure | ADOPT | Dedicated hardware | physical servers for ClickHouse-class workloads |
| Infrastructure | ADOPT | DigitalOcean Spaces | S3-compatible object storage |
| Infrastructure | ADOPT | Infrastructure as code | Terraform/Ansible |
| Infrastructure | TRIAL | DigitalOcean Droplets | VMs |
| Infrastructure | HOLD | Multi-purpose servers | anti-pattern: don't share |
| Data Management | ADOPT | ETL | the `owid/etl` monorepo |
| Data Management | ADOPT | Fast track | the `etl/owl_steps/` for rapid iteration |
| Data Management | ADOPT | Snapshots | the `etl/snapshots/` we already use |
| Data Management | TRIAL | Grapher admin | the chart editor |
| Data Management | ASSESS | Walks-through | the "new user onboarding" flow |
| Data Management | HOLD | Walden | the "prototype catalog" — now superseded |

## How it's used in OpenTIR-Data (3 ways)

### Way 1: read it as intel about OWID's stack

Before you commit to a tech choice, check what OWID uses. If they adopted it, the bus factor is non-trivial (multiple engineers, real production load, public documentation). If they hold it, they've actively rejected it.

For our pipeline, the relevant signals:
- **ClickHouse-class workloads → dedicated hardware** (matches our architecture choice in [[docs/architecture]] )
- **Buildkite + GitHub Actions** for CI (we can use either or both)
- **DigitalOcean Spaces** (S3-compatible) for blob storage — our `/srv/working` and `/srv/backups` design can use this if we move to cloud
- **Walden is HOLD** — confirming our earlier note that `owid/walden` is superseded

### Way 2: extract the data programmatically

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/owid_tech_radar.py
import json
import re
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            r = await client.get("https://raw.githubusercontent.com/owid/tech-radar/master/docs/index.html")
            r.raise_for_status()
            html = r.text

            # Extract the radar_visualization({...}) call argument
            m = re.search(r"radar_visualization\(\s*(\{.*?\})\s*\);", html, re.DOTALL)
            if not m:
                return
            config_text = m.group(1)

            # Pull out the quadrants, rings, entries
            def grab_array(key):
                mm = re.search(rf'{key}\s*:\s*\[(.*?)\]', config_text, re.DOTALL)
                if not mm: return []
                # Naive but good enough for this tiny payload
                return [s.strip().strip('"').strip("'") for s in re.findall(r'"([^"]+)"', mm.group(1))]

            quadrants = grab_array("quadrants")
            rings = grab_array("rings")
            entries_match = re.search(r'entries\s*:\s*\[(.*?)\]\s*//ENTRIES', config_text, re.DOTALL)
            entries = json.loads(f"[{entries_match.group(1)}]") if entries_match else []

            yield RawBundle(
                source_system=self.source_system,
                source_collection="tech_choices",
                source_id="owid-2023.01",
                source_url="https://owid.github.io/tech-radar/",
                bundle_url="https://raw.githubusercontent.com/owid/tech-radar/master/docs/index.html",
                fetched_at=self.now(),
                payload=html.encode("utf-8"),
                payload_format="html",
                metadata={
                    "quadrants": quadrants,
                    "rings": rings,
                    "entries": entries,
                    "title": "Our World In Data Tech Radar",
                    "date": "2023.01",
                },
            )
```

### Way 3: fork it for your own org's tech radar

This is the real value of MIT-licensed code. Want an OpenTIR-Data tech radar? Same radar.js, same HTML shape, just replace the `entries:` array with our own:

```html
<script>
radar_visualization({
  svg_id: "radar",
  title: "OpenTIR-Data Tech Radar",
  date: "2026.09",
  quadrants: [
    { name: "Ingest" },
    { name: "Storage" },
    { name: "Query" },
    { name: "Presentation" },
  ],
  rings: [
    { name: "ADOPT",   color: "#5ba300" },
    { name: "TRIAL",   color: "#009eb0" },
    { name: "ASSESS",  color: "#c7ba00" },
    { name: "HOLD",    color: "#e09b96" }
  ],
  entries: [
    { "quadrant": 0, "ring": 0, "label": "ClickHouse",   "active": true, "moved": 0 },
    { "quadrant": 0, "ring": 0, "label": "httpx",        "active": true, "moved": 0 },
    { "quadrant": 1, "ring": 0, "label": "ZFS mirror",   "active": true, "moved": 1 },
    { "quadrant": 1, "ring": 1, "label": "MinIO (S3)",   "active": true, "moved": 0 },
    { "quadrant": 2, "ring": 0, "label": "SQL",          "active": true, "moved": 0 },
    { "quadrant": 2, "ring": 1, "label": "MCP servers",  "active": true, "moved": 1 },
    { "quadrant": 3, "ring": 0, "label": "Apache ECharts","active": true,"moved": 0 },
    { "quadrant": 3, "ring": 0, "label": "MapLibre GL",  "active": true, "moved": 0 },
    { "quadrant": 3, "ring": 1, "label": "deck.gl",      "active": true, "moved": 0 },
    { "quadrant": 0, "ring": 3, "label": "BeautifulSoup","active": true, "moved": 0 },
    { "quadrant": 1, "ring": 3, "label": "HDD primary",  "active": true, "moved": 0 }
  ]
});
</script>
```

That gives us a public `radar.opentir.org` (or wherever) showing our own architecture choices, for free, in 200 lines of HTML+JS.

## Quick call — verify

```bash
# Live demo
curl -sI "https://owid.github.io/tech-radar/" -w "demo: code=%{http_code} size=%{size_download}\n" -o /dev/null

# License (MIT)
curl -sL "https://raw.githubusercontent.com/owid/tech-radar/master/LICENSE.txt" | head -3

# Entry count
curl -sL "https://raw.githubusercontent.com/owid/tech-radar/master/docs/index.html" \
  | grep -oE '"label":\s*"[^"]+"' | wc -l
```

Expected: demo returns 200, license is "The MIT License (MIT)", and `grep -c '"label":'` returns ~20 entries.

## Notes

- **The radar data is dated 2023.01.** The repo hasn't been updated in 2+ years. The "OWID in 2026" tech stack probably has more entries and different ring assignments, but the public radar is frozen. Treat it as a snapshot.
- **The radar.js library is **d3 v4** based, from 2017.** Modern alternatives: d3 v7, or use a fully-typed React+SVG implementation. For a quick win, use the existing radar.js; for a "real" tech radar in 2026, write it fresh in Svelte or React.
- **This is the only OWID repo in the vault that's MIT-licensed and fully forkable**, alongside `owid/cartograms` (ISC) and the four data-only repos (`co2-data`, `energy-data`, `covid-19-data`, `poverty-data`). Treat it as the canonical example of an OWID project that you can stand on the shoulders of.
- **Tech-radar is a culture artifact as much as a tool.** Publishing one is a public commitment: "this is what we use, this is what we're moving away from, this is what we're evaluating." For a small project like OpenTIR-Data, that's a 1-hour Git commit and a 1-day conversation. Worth doing.
- **For the world dashboard**, the radar visualization is a separate page (`/radar` or `/tech`), not a layer in the map. It's a "who we are and how we work" page, not a "what's happening in the world" page.


## Migrated Context (From Cloudflare Radar Internet Trends.md)

---
tags: [source, info_environment, cyber, tier-2, osint-data, requires-key]
status: active
display_name: "Cloudflare Radar Internet Trends"
fetcher: ingest.fetchers.cloudflare_radar
source_name: cloudflare_radar
api_key_env: CLOUDFLARE_API_TOKEN
---

# Cloudflare Radar Internet Trends

Cloudflare's free Radar API — country-level internet traffic, attack, and adoption trends. ~20% of all web traffic flows through CF, so the signal-to-noise is excellent.

## Metadata

| Field | Value |
|---|---|
| Source system | `cloudflare_radar` |
| Base URL | https://radar.cloudflare.com |
| API base | https://api.cloudflare.com/client/v4/radar |
| Schedule (cron) | `0 12 * * *` (daily at 12:00 UTC) |
| Rate limit | 60 req/min |
| Tier | 2 |
| Axis | info_environment, cyber |
| License | Cloudflare terms (free) |
| Auth | **Required**: `CLOUDFLARE_API_TOKEN` |
| per_tenant_only | false |

## Collections

| Name | Filter | Notes |
|---|---|---|
| `attacks_layer3` | `location=*` (all countries) | L3 DDoS attack summary per country |

## Fetcher

`ingest/fetchers/cloudflare_radar.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='cloudflare_radar'`. Per-country, per-day rows.

## Common queries

```
GET /v1/sources/cloudflare_radar
GET /v1/sources/cloudflare_radar/bundles?country=UA&since=2026-09-01
GET /v1/sources/cloudflare_radar/aggregates?group_by=country,attack_vector
```

## Gotchas

- The token must have `Account > Account Analytics > Read` permission, not just zone-scoped.
- Country codes are ISO 3166-1 alpha-2 (`UA`, not `UKR`).
- Radar is updated daily; sub-day resolution requires the GraphQL API (paid).

## Related

- [[Plan/Source Categorization]] (info_environment + cyber axes)
- [[Ingestion/Shodan IoT/Host Search]] (companion: internet host search)
- [[Ingestion/AbuseIPDB IP Abuse Reports]] (companion: per-IP reputation)

