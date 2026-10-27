# Harvard Crowd Counting Consortium (CCC) — US protest events

Key: `none required` — public, free, no auth. Hosted on Harvard Dataverse.
Endpoint: `https://dataverse.harvard.edu/dataverse/crowdcountingconsortium`
Auth: none
Format: **CSV** (Phase 3), **TSV** (Phases 1 + 2), **JSON** (countlove.org archive)

Documentation:
- CCC home: https://ash.harvard.edu/programs/crowd-counting-consortium/
- Harvard Dataverse: https://dataverse.harvard.edu/dataverse/crowdcountingconsortium
- Count Love (predecessor project, 2017-2021 archive): https://countlove.org/
- countlove.org data: https://countlove.org/data/events.json (12 MB JSON, 38k events)
- Ash Center (parent org): https://ash.harvard.edu/
- Research lab: Nonviolent Action Lab at Harvard Kennedy School

## What it is

The **Crowd Counting Consortium (CCC)** is a research project at Harvard
Kennedy School's Ash Center for Democratic Governance and Innovation.
Started in 2017 by Dr. Erica Chenoweth (political scientist, known for
her work on nonviolent resistance), the CCC uses **computer vision +
human coding** to estimate crowd sizes at political protests in the
United States. The result is the most-cited open dataset on US protest
activity.

**The data is already geocoded.** Every event has:
- `lat` / `lon` (WGS-84)
- `resolved_locality` (city/town)
- `resolved_state` (2-letter code)
- `resolved_county` (county name)
- `fips_code` (5-digit FIPS code for the county)
- `date` (M/D/YYYY)
- `event_type` (protest, march, rally, demonstration, etc.)
- `size_low` / `size_high` / `size_mean` (estimated crowd size)
- `organizations` (sponsoring orgs)
- `claims_summary` / `issues` (protest demands and topics)
- `source1` through `source30` (up to 30 source URLs as provenance)
- `arrests_any` / `participant_casualties_any` / `police_casualties_any` /
  `property_damage_any` (numeric facts)
- `valence` (-1 / 0 / 1, conservative-leaning / neutral / progressive)
- `online` (1 if virtual event, 0 if in-person)

**This is the right source for the "unrest" sub-axis of the 12-axis
model.** Pairs with ACLED (international) to give global coverage of
political crowd events.

## Datasets (3 phases)

| Phase | DOI | File | Size | Rows | Coverage |
|---|---|---|---|---|---|
| 1 (2017-2020) | `10.7910/DVN/6OPP7H` | `ccc_compiled_20172020.tab` | 36 MB | ~25k | Jan 2017 - Dec 2020 |
| 2 (2021-2024) | `10.7910/DVN/9MMYDI` | `ccc_compiled_20212024.tab` | 128 MB | ~80k | Jan 2021 - Dec 2024 |
| 3 (2025-) | `10.7910/DVN/RI9JFU` | `ccc-phase3-public.csv` | 40 MB | ~58k | 2025+ |
| countlove.org archive | (separate) | `data/events.json` | 12 MB | 38k | Jan 2017 - Jan 2021 |

**Total: ~200k events** with full geocoding, crowd-size estimates,
provenance, and topic tags.

## API endpoints (Harvard Dataverse Native API)

```text
# List datasets in the CCC dataverse
GET /api/dataverses/crowdcountingconsortium/contents

# Get a single dataset's metadata
GET /api/datasets/:persistentId/?persistentId=doi:10.7910/DVN/RI9JFU

# Download a file
GET /api/access/datafile/{file_id}
# e.g., https://dataverse.harvard.edu/api/access/datafile/14059539

# Download latest version of a dataset
# (only works for some configs; otherwise list files first and pull by id)
```

The file IDs from my probe:
- Phase 1 data: `10808404` (ccc_compiled_20172020.tab)
- Phase 2 data: `10822959` (ccc_compiled_20212024.tab)
- Phase 3 data: `14059539` (ccc-phase3-public.csv)
- Data dictionaries for each phase: `10808405`, `10808409`, `14059540`

## Quick call — verify (no key)

```bash
# List the CCC dataverse
curl -sL "https://dataverse.harvard.edu/api/dataverses/crowdcountingconsortium/contents" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
for it in d['data']:
    if it['type'] == 'dataset':
        print(f\"  {it['persistentUrl']}\")
"
# Expected: 3 dataset URLs (one per phase)

# Download Phase 3 (40 MB, 2025+)
curl -sL -o /tmp/ccc_phase3.csv \
  "https://dataverse.harvard.edu/api/access/datafile/14059539"
# Verify the columns
head -1 /tmp/ccc_phase3.csv | tr ',' '\n' | head -20
# Expected: date,locality,state,resolved_locality,resolved_state,resolved_county,fips_code,lat,lon,location,title,...

# countlove.org archive (12 MB JSON)
curl -sL "https://countlove.org/data/events.json" \
  | python3 -c "
import json, sys
d = json.load(sys.stdin)
print('  events:', len(d['data']))
print('  first event:')
for k, v in list(d['data'][0].items())[:10]:
    print(f'    {k}: {v}')
"
# Expected: 38,097 events with date, location, count, lat, lon, event, source, tags
```

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/harvard_ccc.py
# Pull the Harvard CCC's latest data and ingest into our warehouse.
import httpx
import csv
import io
from datetime import datetime, timezone
from ingest.clickhouse import ch

CCC_BASE = "https://dataverse.harvard.edu"
PHASE_FILE_IDS = {
    "phase1": 10808404,    # 2017-2020, ~25k events
    "phase2": 10822959,    # 2021-2024, ~80k events
    "phase3": 14059539,    # 2025+, ~58k events (updated regularly)
}


def fetch_ccc_phase(file_id: int) -> list[dict]:
    """Download one phase of the CCC data and yield dicts."""
    url = f"{CCC_BASE}/api/access/datafile/{file_id}"
    r = httpx.get(url, timeout=120.0)
    r.raise_for_status()
    text = r.text
    # The file is CSV (Phase 3) or TSV (Phases 1+2). Detect the delimiter.
    delimiter = "\t" if "\t" in text.splitlines()[0] else ","
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    for row in reader:
        yield row


def to_observation(row: dict) -> dict | None:
    """Map a CCC row to our warehouse's `protest_events` observation."""
    try:
        lat = float(row.get("lat") or 0)
        lon = float(row.get("lon") or 0)
    except (TypeError, ValueError):
        return None
    if not lat or not lon:
        return None

    # Date is M/D/YYYY
    date_str = row.get("date", "")
    if not date_str:
        return None
    try:
        month, day, year = date_str.split("/")
        event_date = datetime(int(year), int(month), int(day), tzinfo=timezone.utc)
    except (ValueError, AttributeError):
        return None

    # Crowd size: prefer the mean; fall back to mid-point of low/high
    size_mean = row.get("size_mean") or row.get("size_text") or ""
    try:
        size = float(size_mean)
    except (TypeError, ValueError):
        try:
            size = (float(row.get("size_low", 0) or 0) + float(row.get("size_high", 0) or 0)) / 2
        except (TypeError, ValueError):
            size = 0

    return {
        "as_of": datetime.now(timezone.utc),
        "event_date": event_date,
        "title": row.get("title", "") or row.get("event_type", ""),
        "lat": lat,
        "lon": lon,
        "resolved_locality": row.get("resolved_locality", ""),
        "resolved_state": row.get("resolved_state", ""),
        "resolved_county": row.get("resolved_county", ""),
        "fips_code": row.get("fips_code", ""),
        "size": size,
        "event_type": row.get("event_type", ""),
        "organizations": row.get("organizations", "").split("; ") if row.get("organizations") else [],
        "issues": row.get("issues", "").split(";") if row.get("issues") else [],
        "claims_summary": row.get("claims_summary", ""),
        "valence": int(row.get("valence", 0) or 0),
        "online": int(row.get("online", 0) or 0),
        "arrests_any": int(row.get("arrests_any", 0) or 0),
        "casualties_any": int(row.get("participant_casualties_any", 0) or 0),
        "source1": row.get("source1", ""),
        "source2": row.get("source2", ""),
        "source3": row.get("source3", ""),
        "credibility": 1,   # Harvard Kennedy School = tier 1
    }


if __name__ == "__main__":
    for phase, file_id in PHASE_FILE_IDS.items():
        rows = list(fetch_ccc_phase(file_id))
        observations = [to_observation(r) for r in rows]
        observations = [o for o in observations if o is not None]
        if observations:
            ch.insert_observations("protest_events", observations)
        print(f"[{phase}] ingested {len(observations)} events")
```

## Notes

- **The right source for the "unrest" sub-axis** of the 12-axis model.
  Pairs with ACLED (international) for global coverage.
- **Already geocoded to town level** — no need to call Nominatim for
  every event. The CCC's research team has done that work.
- **Crowd-size estimates are a number, not a single source** — they
  compute low/high/mean estimates from a "low" source (official
  statements) and a "high" source (independent media). For the
  dashboard, plot the `size_mean` as the marker size, or use `size_low`
  and `size_high` for a range bar.
- **Valence** is the political tilt: -1 (conservative), 0 (neutral),
  +1 (progressive). Useful for filtering or coloring.
- **`repeater = 1`** means it's a recurring event (e.g. "every Wednesday
  pro-Palestine protest at Albany Medical Center"). Useful for the
  "ongoing activity" layer of the dashboard.
- **`online = 1`** marks virtual events. Relevant for post-2020
  pandemic-era protest patterns.
- **Sources** are URLs to news coverage. Up to 30 per event. The first
  source is typically the most authoritative.
- **Update cadence**: Phase 3 is updated as new events are coded.
  Re-pull weekly to stay current.
- **License**: per Harvard Dataverse conventions, CCC data is
  **CC-BY 4.0** (attribution to the Crowd Counting Consortium).
  Verify on the dataset page before redistribution.
- **Volume**: ~200k events total. Stored in ClickHouse, this is
  ~50 MB compressed. Trivial.
- **Credibility tier**: 1 (Harvard Kennedy School = primary
  academic source).
- **For the dashboard**: a dedicated "protests" view (or a layer in
  the existing "unrest" axis) showing CCC events as colored dots on
  the map, sized by crowd, colored by valence. The town-level geocoding
  is the key feature.

## License: CC-BY 4.0 (verify on dataset page)

Per Harvard Dataverse conventions, the CCC data is published under a
**Creative Commons Attribution 4.0** license. This means we can use
the data in any product (commercial or non-commercial) as long as we
attributed to the Crowd Counting Consortium and the original authors
(Chenoweth et al.). Recommended citation:

> Chenoweth, Erica; Pressman, Jeremy; et al. (2024). Crowd Counting
> Consortium [dataset]. Harvard Dataverse.
> https://doi.org/10.7910/DVN/H8W2F2

**Before redistribution, verify the exact license on the dataset page**.
License terms can be updated between phases; the metadata on the
dataset page is authoritative.


## Migrated Context (From Harvard Crowd Counting Consortium (US Protests).md)

---
tags: [source, unrest, governance, tier-1, osint-data, mvp, public-no-auth]
status: active
display_name: "Harvard Crowd Counting Consortium (US Protests)"
fetcher: ingest.fetchers.harvard_ccc
source_name: harvard_ccc
---

# Harvard Crowd Counting Consortium (US Protests)

Harvard University Crowd Counting Consortium. ~200k US protest events, all geocoded to town/county level. 3 phases of data: 2017-2020, 2021-2024, 2025+. Per-event: date, city, state, organization, claims (Black Lives Matter, climate, pro-life, etc.), participant count estimate, source URLs.

## Metadata

| Field | Value |
|---|---|
| Source system | `harvard_ccc` |
| Base URL | https://dataverse.harvard.edu |
| API base | https://dataverse.harvard.edu/api |
| Schedule (cron) | `0 6 * * 1` (Mondays at 06:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | unrest, governance |
| License | CC-BY-4.0 |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | File ID | Notes |
|---|---|---|
| `phase1_2017_2020` | `10808404` | Harvard Dataverse file |
| `phase2_2021_2024` | `10822959` | Harvard Dataverse file |
| `phase3_2025_plus` | `14059539` | Harvard Dataverse file |

## Fetcher

`ingest/fetchers/harvard_ccc.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='harvard_ccc'`. Per-event rows: `date`, `city`, `state`, `lat`, `lon`, `organization`, `claims[]`, `participants`, `source_urls[]`.

## Common queries

```
GET /v1/sources/harvard_ccc
GET /v1/sources/harvard_ccc/bundles?state=CA&since=2026-06-01
GET /v1/sources/harvard_ccc/aggregates?group_by=state,claim
```

## Gotchas

- **Primary academic source** for the unrest axis. Most-cited US protest dataset.
- `claims` is a list per event; aggregation needs `unnest(claims)` first.
- Coverage is comprehensive for large/mid-size events; small (<25 participants) events are undercounted.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (unrest + governance axes)
- [[Ingestion/Count Love US Protest Archive (2017-2021)]] (predecessor, cross-validation)
- [[Ingestion/Nostr NIP-52 Calendar Events (Decentralized Protests)]] (forward-looking)
- [[Ingestion/ACLED — Armed Conflict Location & Event Data Project]] (violent unrest)

