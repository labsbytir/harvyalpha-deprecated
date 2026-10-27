# Count Love (CCC predecessor, 2017-2021 archive)

Key: `none required` — public, free, no auth
Endpoint: `https://countlove.org/data/events.json`
Auth: none
Format: **JSON** (single file, 12 MB)

Documentation:
- Home: https://countlove.org/
- Data file: https://countlove.org/data/events.json
- About: https://countlove.org/about.html
- GitHub: https://github.com/CountLove/CountLove

## What it is

**Count Love** is the predecessor project to the **Harvard Crowd
Counting Consortium (CCC)**. Run as a community project from
**January 2017 to January 2021** by Benjamin Elbaugh and Nathan
Perkins (then students), the project collected data on US protest
activity and published it as a public, downloadable JSON file. The
project is now archived; the data remains available at `countlove.org`
and on GitHub.

**Coverage**: Jan 20, 2017 to Jan 31, 2021 (4 years of data covering
the Trump administration, BLM protests, COVID-era lockdowns, and the
2020 election cycle). **38,097 events**, all geocoded, all with crowd
size estimates.

**The right historical source for "what were the protests in 2017-2020
in city X?"**. Pairs with the Harvard CCC Phase 1 dataset, which
overlaps heavily in time period (CC-BY 4.0; more rigorous methodology;
more recent and ongoing).

## Data shape

```json
{
  "data": [
    {
      "id": 17447,
      "date": "2017-01-15",
      "location": "Bowie State University, Bowie, MD",
      "count": 1500,
      "lat": 39.019,
      "lon": -76.759,
      "event": "Healthcare",
      "source": "http://www.capitalgazette.com/news/ph-ac-cn-aca-rally-0116-20170115-story.html",
      "tags": [8, 23],
      "relevant": true,
      "total_articles": 1
    },
    ...
  ],
  "uniqueLocations": [...],
  "uniqueTags": [...]
}
```

**Compared to the Harvard CCC schema**, Count Love is simpler:
- `id`: integer
- `date`: YYYY-MM-DD
- `location`: free-text (city + state usually)
- `count`: integer (estimated crowd size)
- `lat` / `lon`: WGS-84
- `event`: high-level category (Healthcare, Civil Rights, Immigration, etc.)
- `source`: single URL (Harvard CCC has up to 30)
- `tags`: array of tag IDs (look up in `uniqueTags`)
- `relevant`: boolean
- `total_articles`: integer

**No per-event narrative or claims** (the Harvard CCC added this in
later phases). For OSINT, the Harvard CCC's richer schema is better
when you have it.

## Quick call — verify (no key)

```bash
# Download the JSON
curl -sL -o /tmp/cl_events.json "https://countlove.org/data/events.json" \
  -w "HTTP %{http_code}, size: %{size_download}\n"
# Expected: HTTP 200, ~12 MB

# Summarize
python3 -c "
import json
d = json.load(open('/tmp/cl_events.json'))
print(f'  events: {len(d[\"data\"])}')
print(f'  date range: {min(e[\"date\"] for e in d[\"data\"])} to {max(e[\"date\"] for e in d[\"data\"])}')
print(f'  with geocoded coords: {sum(1 for e in d[\"data\"] if e.get(\"lat\") and e.get(\"lon\"))}')
print(f'  with size estimate: {sum(1 for e in d[\"data\"] if e.get(\"count\"))}')
"
# Expected: 38,097 events, 2017-01-15 to 2021-01-31, 100% geocoded, ~60% with size
```

## Notes

- **Historical data only** — Count Love ended in January 2021. For
  current protest data, use the Harvard CCC.
- **Simple schema** — easier to ingest than the CCC's 60-column CSV,
  but less rich.
- **License**: **CC-BY 4.0** (per the Count Love GitHub LICENSE).
  Attribution: "Count Love, https://countlove.org".
- **Why both Count Love and Harvard CCC?** They overlap in time period
  (2017-2021) but have different methodology and coverage. The Harvard
  CCC is the "official" continuation and has richer data. Count Love
  is useful for cross-validation and for understanding the project's
  history.
- **Storage**: 12 MB. Trivial. Ingest once at startup, or pull weekly.
- **Credibility tier**: 2 (community project but well-cited; predecessor
  to a Harvard project).

## Comparison table

| Feature | Count Love (this) | Harvard CCC Phase 1 | Harvard CCC Phase 3 |
|---|---|---|---|
| Date range | 2017-01 to 2021-01 | 2017-01 to 2020-12 | 2025+ |
| Events | 38,097 | ~25,000 | ~58,000 (ongoing) |
| Geocoded | 100% | 100% | 100% |
| Crowd size | 60% | 100% | 100% |
| Event type | high-level (12 cats) | rich (10+ types) | rich (10+ types) |
| Claims/narrative | no | yes (Phase 2+) | yes |
| Sources per event | 1 | up to 30 | up to 30 |
| License | CC-BY 4.0 | CC-BY 4.0 | CC-BY 4.0 |
| Update cadence | archived | quarterly | weekly |
| Format | JSON (single file) | TSV (35 MB) | CSV (40 MB) |

For v1, we ingest all three to get complete 2017-present coverage.

## License: CC-BY 4.0

Count Love data is published under the **Creative Commons Attribution
4.0 International** license. Free for any use including commercial,
attribution required: "Count Love, https://countlove.org".

The source code on GitHub (`https://github.com/CountLove/CountLove`)
is **MIT-licensed**.


## Migrated Context (From Count Love US Protest Archive (2017-2021).md)

---
tags: [source, unrest, tier-2, osint-data, public-no-auth]
status: active
display_name: "Count Love US Protest Archive (2017-2021)"
fetcher: ingest.fetchers.countlove
source_name: countlove
---

# Count Love US Protest Archive (2017-2021)

Count Love. 38k US protests from 2017-01-20 to 2021-12-31, all geocoded to town level. Per-event: date, location, source, participant count estimate, related articles. Predecessor to [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]]; useful for cross-validation and pre-2017 backfill (limited).

## Metadata

| Field | Value |
|---|---|
| Source system | `countlove` |
| Base URL | https://countlove.org |
| API base | https://countlove.org |
| Schedule (cron) | `0 7 * * 1` (Mondays at 07:00 UTC) |
| Rate limit | 10 req/min |
| Tier | 2 |
| Axis | unrest |
| License | CC-BY-4.0 |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | URL | Notes |
|---|---|---|
| `events` | https://countlove.org/data/events.json | full archive JSON |

## Fetcher

`ingest/fetchers/countlove.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='countlove'`. Per-event rows.

## Common queries

```
GET /v1/sources/countlove
GET /v1/sources/countlove/bundles?state=NY&since=2020-01-01
```

## Gotchas

- The dataset is **frozen** at 2021-12-31; no new events. Use [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] for current data.
- Use as cross-validation against Harvard CCC for the 2017-2021 overlap.

## Related

- [[Plan/Source Categorization]] (unrest axis)
- [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] (current authoritative source)
- [[Ingestion/Nostr NIP-52 Calendar Events (Decentralized Protests)]] (forward-looking)
