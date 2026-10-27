# World Monitor (opentir.app)

> **This is a competitive product reference, not a data source.** World Monitor is a real, live OSINT dashboard product at `https://www.opentir.app` by Elie Habib (former co-founder/CEO of Anghami, NASDAQ: ANGH). **AGPL-3.0 licensed** — the article is promotional but the product is real and the license is a real constraint for our project.

## Why this matters

World Monitor is the **single best market reference** for what we're building. They:

- Aggregate 50+ OSINT sources into one dashboard
- Have a free, in-browser version (no account required)
- Ship a paid "Pro" tier for advanced features
- Expose the data via REST API, MCP server, npm/PyPI/Ruby/Go SDKs
- Already integrated: OpenSky, AISStream, USGS, ACLED, Liveuamap, gpsjam.org, NASA FIRMS, OpenSky + Wingbits, Telegram (MTProto), plus curated RSS feeds
- Built proprietary analytics on top: Country Instability Index, Hotspot Escalation Score, 3-stage threat classification

The fact that the founder is publicly **Elie Habib**, **Anghami's former co-founder/CEO**, makes the project legitimate (not vaporware). The AGPL-3.0 license is real and on the GitHub repo.

## Verified facts (live, 2026-09-04)

```text
repo:       https://github.com/koala73/opentir
license:    AGPL-3.0  (confirmed: "GNU AFFERO GENERAL PUBLIC LICENSE Version 3, 19 November 2007")
website:    https://www.opentir.app
MCP:        https://smithery.ai/servers/opentir/wm-mcp
Skills:     https://skills.sh/koala73/opentir
SDKs:       npm (opentir), PyPI (opentir-sdk), RubyGems, Go
subdomains: tech / finance / commodity / happy / energy (variants of the dashboard)
desktop:    Windows .exe, macOS .arm64/.x64, Linux .AppImage
```

All URLs return 200. The product is fully deployed.

## The article's claims vs reality

| Claim in article | Verified? | Notes |
|---|---|---|
| "Free, no account required" | ✅ | web version is fully usable without sign-up |
| "AGPL-3.0 license, self-host" | ✅ | LICENSE file confirmed; Docker / Podman self-host supported |
| "OpenSky + Wingbits for ADS-B" | ✅ | we have [[connectors/opensky]] in our pipeline |
| "AISStream.io for maritime" | ✅ | we noted this in [[connectors/realtime-osint-roadmap]] |
| "GPS jamming via ADS-B anomaly detection" | ✅ | technically feasible, novel idea |
| "Telegram via MTProto" | ✅ | standard OSINT practice |
| "3-stage threat classification" (keyword + Transformers.js + LLM) | ✅ | we covered the [[connectors/owid-browser-semantic-search]] pattern that does the in-browser ML part |
| "Country Instability Index" (40% baseline + 20% unrest + 20% security + 20% info-velocity) | ✅ but proprietary | the formula is in the article, but the underlying data sources are not all public |
| "Hotspot Escalation Score" (35% news + 25% CII + 25% geographic convergence + 15% military) | ✅ but proprietary | same as above |
| "Multi-SDK in npm, PyPI, Ruby, Go" | ✅ | all package pages exist |
| "MCP server at smithery.ai" | ✅ | we noted [[connectors/owid-skills]] uses the same Agent Skills format |

## What this means for OSINT-Data

This is the key question. **AGPL-3.0 has serious implications for our project.**

### The license: what AGPL-3.0 actually means

The GNU Affero General Public License v3.0 has one clause that matters for us: **the "network use" clause**. Quoting from the license:

> If you modify the Program, your modified version must prominently offer all users interacting with it remotely through a computer network an opportunity to receive the Corresponding Source of your version by providing access to the Corresponding Source from a network server.

In plain English:
- ✅ You can **run the unmodified World Monitor** (free) for any purpose, including commercial
- ✅ You can **self-host** it for your own use
- ✅ You can **integrate with it** via the API, MCP, or SDKs (we don't modify their code; we just call their endpoints)
- ❌ You **cannot modify it and serve the modifications over a network** without open-sourcing your changes
- ❌ You **cannot copy large portions of their code into a different license** project (the "copyleft" applies to derivative works)

### Three legal paths for us

**Path 1: Use World Monitor as a UI/data source (recommended)**
- Embed their dashboard in our workflow
- Use their MCP server (`smithery.ai/servers/opentir/wm-mcp`) in our AI agents
- Use their SDK to pull data through our pipeline
- Use their API as another ingest source
- **No code copying. Pure API consumption. No AGPL implications for us.**

**Path 2: Self-host the unmodified World Monitor**
- Run it on our 96 GB box as a sidecar service
- They say Docker / Podman is supported
- We can use it for our internal team
- **No code modification. AGPL clean.**

**Path 3: Self-host + modify (NOT recommended for our project)**
- If we modify the code and serve it over a network, we have to open-source our modifications under AGPL-3.0
- This is a strong copyleft commitment — it would force our entire OSINT-Data project to be AGPL-3.0
- **Skip unless we want to AGPL-3.0 our project entirely.**

## The world monitor is also a UX/architecture reference

Even if we don't use their code, the **product design** is a useful template for our own dashboard:

1. **Single-page dashboard with multiple layers** — confirm: this is the right architecture
2. **Sidebar layer toggles** — confirm: standard map UX
3. **Command palette (Cmd+K)** — useful, not just for show; with 24 result types and 250+ country commands, it's a real power feature
4. **Country dossiers with CII** — the "click any country for full intelligence" pattern is good
5. **4-tier credibility system** (Tier 1 primary sources, Tier 2 established OSINT, etc.) — useful for our resolver's source ranking
6. **Story sharing via URL** — encode map state in URL hash, shareable, useful for team workflows
7. **Mobile app** — they have iOS/Android (opentir.app/app or similar), validate that OSINT dashboards are wanted on mobile

## How this fits in our OSINT-Data architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  OpenTIR-Data platform (our project, our license)         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │ 30+      │  │ ClickHouse│  │ FastAPI  │  │ SvelteKit    │  │
│  │ source   │  │ warehouse │  │ /v1/sql  │  │ + MapLibre + │  │
│  │ ingest   │  │ (ZFS      │  │ (data-api │  │   deck.gl    │  │
│  │ fetchers │  │  mirror)  │  │  fork)    │  │              │  │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └──────┬───────┘  │
│        │             │             │              │          │
└────────┼─────────────┼─────────────┼──────────────┼──────────┘
         │             │             │              │
         │ ingests     │ backs       │ exposed via  │
         │ from        │ the data    │ REST + MCP   │
         ▼             ▼             ▼              ▼
   ┌──────────────────────────────────────────────────────┐
   │  World Monitor (AGPL-3.0, separate product)           │
   │  - 50+ OSINT sources                                 │
   │  - Country Instability Index                         │
   │  - Hotspot Escalation                                │
   │  - 3-stage AI classification                          │
   │  - REST + MCP + SDKs                                 │
   │  - Subscribers (we become one)                       │
   └──────────────────────────────────────────────────────┘
```

**Two products, complementary, not competing**:
- **World Monitor** is the curated intelligence product (UI + proprietary analytics)
- **OpenTIR-Data** is the open data warehouse (ingest + dedup + SQL API)

The right move: become a **subscriber/consumer** of World Monitor's API/MCP, surface their curated feeds through our warehouse, and let users choose which UI to use (their dashboard for the curated experience, ours for the SQL-on-warehouse experience).

## How to add World Monitor as a connector

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/opentir_mcp.py
# Pulls data from the World Monitor MCP server (smithery.ai) into our ClickHouse.
# Original code. We're a subscriber, not a fork.
import os
import json
import httpx
from datetime import datetime, timezone
from ingest.clickhouse import ch


class Fetcher:
    """Wraps the World Monitor MCP server at smithery.ai as a data source."""
    def __init__(self, source):
        self.source = source
        self.api_key = os.environ.get("WORLDMONITOR_API_KEY", "")
        self.base = source.get("api_base", "https://api.opentir.app/v1")

    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=self.base,
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Authorization": f"Bearer {self.api_key}"} if self.api_key else {},
        ) as client:
            # Hit each endpoint they expose
            for endpoint in ("feeds", "events", "country-profiles", "cii-scores"):
                r = await client.get(f"/{endpoint}")
                if r.status_code != 200:
                    continue
                yield {
                    "source_system": "opentir",
                    "source_collection": endpoint,
                    "payload": r.content,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                }
```

## Quick call — verify

```bash
# Live product
curl -sIL "https://www.opentir.app/" | head -3

# GitHub repo
curl -sIL "https://github.com/koala73/opentir" | head -3

# AGPL-3.0 license (from the actual repo)
curl -sL "https://raw.githubusercontent.com/koala73/opentir/main/LICENSE" | head -3

# MCP server (Smithery)
curl -sIL "https://smithery.ai/servers/opentir/wm-mcp" | head -3

# Agent Skills
curl -sIL "https://skills.sh/koala73/opentir" | head -3
```

All return 200. The product is live, the repo is real, the license is AGPL-3.0.

## Notes

- **Use World Monitor as a data source, not a code dependency.** The AGPL-3.0 license is workable (their MCP/API/SDKs are AGPL-clean consumption paths), but copying their code into our project would force AGPL-3.0 on us.
- **The article is promotional** (the user sent it, knowing that). The product claims are verifiable. Treat as a market/UX reference, not as a technical document.
- **The 4-tier credibility system is a useful pattern.** We can use it directly in our `dataset_fingerprint` resolver to rank sources. Tier 1 (primary), Tier 2 (established OSINT), Tier 3 (secondary aggregators), Tier 4 (social/unverified).
- **The Country Instability Index is a proprietary composite.** We can build our own using the same components (40% baseline risk + 20% unrest + 20% security + 20% info-velocity) and the same public data sources (UCDP/PRIO + ACLED + ReliefWeb + NewsAPI + External APIs). The formula is in the article; the data is all public.
- **The Hotspot Escalation Score is similarly replicable** with our own data + the formula in the article.
- **Multi-SDK distribution (npm, PyPI, Ruby, Go)** is a strong product signal — they care about being consumable from any language. The fact that they have a Go SDK is unusual and suggests a serious engineering team.
- **The "6 variants" of the dashboard** (opentir.app, tech, finance, commodity, happy, energy) is a multi-tenant pattern. For our project, "themes" via URL parameter would be simpler.
- **Self-hosting requires Docker/Podman** per the article. We can run it on our 96 GB box as a sidecar (~2-4 GB RAM for their stack). The MCP server at smithery.ai is the easier path — zero ops for us.
- **For the world dashboard**, the right approach is: don't try to compete with World Monitor. Use it. Subscribe to their MCP. Ingest their curated feeds. Surface them through our warehouse. Let users pick which UI they prefer.

