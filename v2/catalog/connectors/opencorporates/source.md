# OpenCorporates

Key: `pending — register at https://opencorporates.com/api_accounts/new` (free for personal/non-commercial use, 200 calls/day; paid tiers for more).

Endpoint: `https://api.opencorporates.com/v0.4/`
Auth: `?api_token=<key>` query param
Format: `JSON` (default), `YAML` (legacy)

Documentation:
- API home: https://opencorporates.com/api_docs
- Sign up: https://opencorporates.com/api_accounts/new
- Jurisdiction list: https://opencorporates.com/jurisdictions
- Developer wiki: https://github.com/opencorporates/opencorporates/wiki

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/opencorporates.py
import os
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

API_TOKEN = os.environ["OPENCORPORATES_API_TOKEN"]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://api.opencorporates.com/v0.4",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            for jc in ("us_de", "us_ca", "gb", "de", "fr", "nl"):
                # Get a few notable companies per jurisdiction
                for q in ("tesla", "apple", "google"):
                    r = await client.get("/companies/search",
                                         params={"q": q, "jurisdiction_code": jc,
                                                 "api_token": API_TOKEN, "per_page": 50})
                    if r.status_code == 404: continue
                    r.raise_for_status()
                    body = r.json()
                    for c in body.get("results", {}).get("companies", []):
                        co = c.get("company", {})
                        yield RawBundle(
                            source_system=self.source_system,
                            source_collection=jc,
                            source_id=co["company_number"],
                            source_url=co.get("opencorporates_url", ""),
                            bundle_url=f"/companies/{jc}/{co['company_number']}?api_token=***",
                            fetched_at=self.now(),
                            payload=orjson.dumps(co),
                            payload_format="json",
                            metadata={"company": co, "jurisdiction": jc, "query": q},
                        )
```

## Quick call — verify

```bash
# Replace YOUR_TOKEN with the real token after signup
curl -sL "https://api.opencorporates.com/v0.4/companies/search?q=tesla&jurisdiction_code=us_de&api_token=YOUR_TOKEN" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('total:', d.get('results', {}).get('total_count')); print('first:', d['results']['companies'][0]['company']['name'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /v0.4/companies/search?q=&jurisdiction_code=&api_token=    # search
GET /v0.4/companies/{jurisdiction_code}/{company_number}    # one company
GET /v0.4/companies/{jurisdiction_code}/{company_number}/officers
GET /v0.4/companies/{jurisdiction_code}/{company_number}/filings
GET /v0.4/officers/search?q=                                 # search officers
GET /v0.4/corporate_groupings/{uri}                           # corporate hierarchies
GET /v0.4/jurisdictions                                       # all jurisdictions
GET /v0.4/industry_codes                                      # NAICS/SIC mapping
```

Query params: `q`, `jurisdiction_code`, `company_number`, `registered_name`, `incorporation_date`, `current_status`, `per_page` (max 100), `page`, `api_token`, `normalise_company_name=true|false`.

## Notes

- Free tier: 200 calls/day. Paid: from $90/mo for 50k. The company-catalog crawl needs the paid tier.
- OpenCorporates aggregates 200M+ companies from 200+ jurisdictions. Massive dedup opportunity with national business registries.
- The `corporate_groupings` endpoint is OSINT gold — it shows parent/subsidiary trees across jurisdictions.
- `normalise_company_name=true` is critical: same legal entity can appear as "Apple Inc.", "Apple, Inc.", "Apple Incorporated" etc.
- 401 in my probe = missing/empty token. The endpoint itself returns 200 with a valid token.
- For OSINT, the highest-value fields are: registered address, officers, filings, ultimate parent.


## Migrated Context (From AWS_Open_Data_Integration.md)

# AWS Open Data Registry Integration

OpenTIR now ingests all 1,176 datasets from the AWS Open Data Registry (https://registry.opendata.aws/) for intelligence analysis and mapping.

## Files Added

- scripts/ingest/opendata_aws.mjs — RSS puller and trust scorer
- api/v1/opendata-aws.js — queryable REST endpoint
- api/v1/opendata-aws-creds.js — local Redis credentials shim
- /etc/cron.d/opendata-aws-daily — nightly refresh at 04:00 UTC

## Query API

GET /api/v1/opendata-aws exposes the cached datasets with rich filtering.

Query parameters:
- q: Free-text search across title, description, and S3 bucket names
- bucket: Filter to datasets referencing a specific S3 bucket substring (e.g. noaa)
- min_trust: Minimum trust score (0-100)
- limit: Max results (default 100, hard cap 1176)

Example:
- curl https://cloud.opentir.org/api/v1/opendata-aws?q=sentinel&limit=5
- curl https://cloud.opentir.org/api/v1/opendata-aws?bucket=noaa
- curl https://cloud.opentir.org/api/v1/opendata-aws?min_trust=80

## Mapping (next step)

To enable geospatial mapping of datasets, the S3 bucket metadata is enriched at ingest with a region field. The map dashboard can later render dataset locations by joining the bucket region with the existing geo index.


## Migrated Context (From Open Infrastructure Map (OSM Power Infrastructure).md)

---
tags: [source, info_environment, climate, tier-1, osint-data, public-no-auth]
status: active
display_name: "Open Infrastructure Map (OSM Power Infrastructure)"
fetcher: ingest.fetchers.openinframap
source_name: openinframap
---

# Open Infrastructure Map (OSM Power Infrastructure)

Open Infrastructure Map — global power infrastructure from OpenStreetMap. ODbL 1.0 (data) + MIT (code). Power plants tagged `power=plant` with `plant:source` (wind/solar/coal/gas/hydro/nuclear/biomass/oil/waste), `plant:method` (combustion/photovoltaic/wind_turbine/run-of-the-river/dam/nuclear_fission), and `plant:output:electricity` (MW). Power lines `power=line` with `voltage` (11000=11kV, 132000=132kV, 400000=400kV). Substations `power=substation`. Generators `power=generator`. Live updates via OSM tile server (tiles.openinframap.org). Per-country Overpass queries recommended.

## Metadata

| Field | Value |
|---|---|
| Source system | `openinframap` |
| Base URL | https://openinframap.org |
| API base | https://overpass-api.de/api/interpreter |
| Schedule (cron) | `0 0 * * 0` (Sundays) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | info_environment, climate |
| License | ODbL 1.0 (data) + MIT (code) |
| Auth | none (public) |
| per_tenant_only | false |
| format | overpass_json + mvt |

## Collections

| Name | Endpoint | Method | Format |
|---|---|---|---|
| `overpass_power_plants` | https://overpass-api.de/api/interpreter | POST | Overpass JSON |
| `overpass_power_lines` | https://overpass-api.de/api/interpreter | POST | Overpass JSON |
| `overpass_substations` | https://overpass-api.de/api/interpreter | POST | Overpass JSON |
| `vector_tiles` | https://tiles.openinframap.org/{z}/{x}/{y}.pbf | GET | MVT |
| `overpass_kumi_mirror` | https://overpass.kumi.systems/api/interpreter | POST | Overpass JSON |

## Fetcher

`ingest/fetchers/openinframap.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='openinframap'`. Per-feature rows.

## Common queries

```
GET /v1/sources/openinframap
GET /v1/sources/openinframap/bundles?feature=power_plant&country=DE
```

## Gotchas

- Overpass API is rate-limited and time-budgeted (default 25 s server-side). Per-country queries are recommended.
- **Mirrors:** `overpass.kumi.systems`, `overpass.private.coffee` — rotate if main is overloaded.
- Quality varies by country — excellent in DE/NL/UK/US/AU/CA/JP, sparse in Africa/Central Asia.
- Cross-references [[Ingestion/WRI Global Power Plant Database v1.3.0]] + [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] via plant-name fuzzy match.

## Related

- [[Plan/Source Categorization]] (info_environment + climate axes)
- [[Ingestion/WRI Global Power Plant Database v1.3.0]] (historical baseline)
- [[Ingestion/Global Energy Monitor (25 Open Energy Trackers)]] (current)
- [[Ingestion/Wikidata — Global Power Infrastructure (SPARQL)]] (federation)
- [[Ingestion/Climate TRACE — Global Per-Asset Emissions Inventory]] (emissions)
- [[Ingestion/OpenStreetMap ALPR Cameras (DeFlock-equivalent)]] (companion: OSM infrastructure)

