# Granicus Legistar Web API (NYC Council + ~3,000 US municipalities)

Key: `pending — request a free API token from the municipality's Legistar site (NYC: fill form at https://council.nyc.gov/legislation/api/)`
Endpoint: `https://webapi.legistar.com/v1/{Client}/{endpoint}`
Auth: `?token=verylongbase64token` URL parameter
Format: **JSON** (OData v3 URL conventions, 1000-row pagination limit)

Documentation:
- NYC Council marketing page: https://council.nyc.gov/legislation/api/ (the one you sent)
- Granicus API examples: https://webapi.legistar.com/Home/Examples
- Granicus API help: https://webapi.legistar.com/Help
- OData v3 URL conventions: https://www.odata.org/documentation/odata-version-3-0/url-conventions/
- Granicus Legistar product: https://www.granicus.com/solutions/legislative-management/
- SaaS vendor: **Granicus** (acquired Legistar ~2019; the SaaS powers ~3,000 US municipalities)
- License: **Public domain** (US government work product, 17 U.S.C. § 105)
- Granicus API version: 26.4.2.0 (as of 2026-09-05)

## What it is

**Legistar** is Granicus's legislative-management SaaS. It is the same
backend that powers legislative websites for **~3,000 US municipalities
and counties** — NYC Council, Chicago City Council, Boston, LA County,
Seattle, San Francisco, etc. Each customer is a `Client` name in the
URL path (`/v1/nyc/`, `/v1/chicago/`, `/v1/kingcounty/`, etc.).

For NYC: `Client = nyc`, base URL `https://webapi.legistar.com/v1/nyc/`.

The API was released publicly on **November 16, 2017** as part of the
Council's "Council 2.0" transparency initiative. It exposes the same
data you see on `https://legistar.council.nyc.gov/Legislation.aspx`,
just machine-readable: council members, committees, bills, hearings,
events, votes, attachments.

## The full endpoint surface (~20 endpoints)

From the Granicus Help page at `https://webapi.legistar.com/Help`. All
under `https://webapi.legistar.com/v1/nyc/...`:

| Endpoint | What it gives |
|---|---|
| `Bodies` | Committees and chambers (e.g. "Committee on Health", "Committee on Housing", "City Council", "Committee on Public Safety") |
| `BodyTypes` | Body classifications |
| `CodeSections` | NYC Administrative Code sections (e.g. "Title 17, Section 100") |
| **Events** | Meetings (Stated, Committee, Hearings) with date/time/location/body |
| `EventItems` | Items on an event's agenda (each one is a bill being discussed) |
| `EventItems/{EventItemId}/RollCalls` | The actual roll call vote for that event item |
| `EventItems/{EventItemId}/Votes` | Per-person vote records (yea/nay/abstain) |
| `Indexes` | Subject index terms (e.g. "Housing", "Transportation") |
| `MatterIndexes` | Bill ↔ index term links |
| **Matters** | Bills, resolutions, motions, local laws — the core "legislation" objects |
| `MatterAttachments` | PDFs and supporting documents attached to a bill |
| `MatterCodeSections` | Which Admin Code sections a bill modifies |
| `MatterHistories` | Action history: introduced → committee → voted → enacted |
| `MatterRelations` | Bill-to-bill links (e.g. a resolution related to a bill) |
| `MatterSponsors` | Council members who sponsored a bill |
| `MatterStatuses` | "Introduced", "In Committee", "Passed", "Enacted", etc. |
| `MatterTexts` | The actual text of a bill (multiple versions per bill) |
| `MatterTypes` | "Bill", "Resolution", "Local Law", "Motion", "Communication" |
| `MatterRequesters` | Who requested the matter |
| `OfficeRecords` | Council member terms in office |
| **Persons** | All people in the system (council members + staff) |
| `Persons/{PersonId}/OfficeRecords` | A person's tenure history |
| `Persons/{PersonId}/RollCalls` | All votes this person has cast |
| `RollCalls` (deprecated alias) | → `EventItems/{EventItemId}/RollCalls` |
| `Votes` | → `EventItems/{EventItemId}/Votes` |
| `VoteTypes` | Classification of votes (yea / nay / abstain / recusal) |
| `Actions` | Internal workflow actions |

For our **governance axis** in the dashboard, the most useful endpoints
to start with are:

- `Bodies` — committee structure (~25 committees + the full Council)
- `Matters` — all bills, with status, type, sponsors, code-sections
- `Events` — meeting calendar
- `Persons` + `OfficeRecords` — who's currently in office
- `EventItems/{EventItemId}/Votes` — how they actually voted
- `MatterHistories` — the audit trail

## How to call (NYC example)

```bash
# 1. Get a free API token by filling the form at:
#    https://council.nyc.gov/legislation/api/
#    (You'll get an email with a long base64 token within 1-2 business days.)

# 2. Try it
TOKEN="<your-token>"
curl "https://webapi.legistar.com/v1/nyc/Persons?token=$TOKEN" | head -100
curl "https://webapi.legistar.com/v1/nyc/Matters?\$top=10&\$skip=0&token=$TOKEN"
curl "https://webapi.legistar.com/v1/nyc/Events?\$filter=EventDate+ge+datetime'2026-09-01'&token=$TOKEN"

# 3. Paging (OData v3)
curl "https://webapi.legistar.com/v1/nyc/Matters?\$top=100&\$skip=0&token=$TOKEN" > page1.json
curl "https://webapi.legistar.com/v1/nyc/Matters?\$top=100&\$skip=100&token=$TOKEN" > page2.json
# ... up to 1000 rows per request, then continue with skip=1000, 2000, etc.
```

⚠️ The `$` in OData query params **must be URL-escaped as `\$` in bash**
or single-quoted, or the shell will try to expand them as variables.

## Why a token is required for NYC (and how to get one)

The Granicus API help page says:

> "Some clients require use of API tokens for access. If the read-only
> operations above give an unauthorized response, please refer to that
> client for their token policy."

NYC is one of the token-required clients. The marketing page at
`https://council.nyc.gov/legislation/api/` has a form: name + email.
You'll get a long base64 token by email within 1-2 business days. The
form is a normal read-access request; there's no charge and no
approval gate beyond identity confirmation.

For other municipalities, the token policy varies — some are public
no-auth (worth checking before applying). The Granicus examples at
`https://webapi.legistar.com/Home/Examples` mention this is client-
specific.

## Suggested `sources.yaml` entry

```yaml
- name: legistar_nyc
  display_name: "Granicus Legistar — NYC Council (legislation, votes, members)"
  domain: legistar.council.nyc.gov
  api_base: https://webapi.legistar.com/v1/nyc
  client: nyc
  axis: governance
  tier: 1
  license: Public domain (17 U.S.C. § 105)
  requires_key: true
  key_env: LEGISTAR_NYC_TOKEN
  schedule: "0 */6 * * *"          # 4x daily; the council updates throughout the day
  rate_limit_per_minute: 30
  fetcher_module: ingest.fetchers.legistar
  public_no_auth: false
  cred_blurb: "NYC Council legislation via Granicus Legistar Web API. Bills, resolutions, motions, votes, council members, committees, meetings. Public domain. Free API token via form at https://council.nyc.gov/legislation/api/."
  description: |
    Granicus Legistar SaaS (same backend as ~3,000 US municipalities).
    OData v3 query language, 1000-row pagination, $top/$skip/$filter.
  collections:
    - name: bodies
      endpoint: /Bodies
    - name: persons
      endpoint: /Persons
    - name: matters
      endpoint: /Matters
    - name: events
      endpoint: /Events
      # filter: $filter=EventDate+ge+datetime'2026-09-01'
    - name: matters_recent
      endpoint: /Matters
      # filter: $filter=PassageDate+ge+datetime'2026-01-01'
      # top=200, sort by last-modified
```

The same fetcher would work for any other Legistar-powered
municipality — just swap `{Client}` and `LEGISTAR_{CITY}_TOKEN`:

| City | Client name | Legistar URL |
|---|---|---|
| NYC | `nyc` | `webapi.legistar.com/v1/nyc/` |
| Chicago | `chicago` | `webapi.legistar.com/v1/chicago/` |
| Boston | `boston` | `webapi.legistar.com/v1/boston/` |
| King County (WA) | `kingcounty` | `webapi.legistar.com/v1/kingcounty/` |
| LA County | `lacounty` | `webapi.legistar.com/v1/lacounty/` |
| San Francisco | `sfgov` | `webapi.legistar.com/v1/sfgov/` |
| Seattle | `seattle` | `webapi.legistar.com/v1/seattle/` |
| Denver | `denver` | `webapi.legistar.com/v1/denver/` |

The full client list is dynamic; you can probe `https://webapi.legistar.com/v1/` (which is itself token-gated for most clients, so this is a chicken-and-egg) or look up each municipality's council website for their Legistar URL.

## Connection to the broader OSINT stack

- **Civic-space rating by country** → [`civicus-monitor`](civicus-monitor.md) (5-tier governance, 198 countries, CC-BY-SA 4.0)
- **Press releases** → External APIs + per-org RSS (already in `sources.yaml`)
- **Public statements** → Federal Register + White House + agency RSS
- **Bill text / laws passed** → Legistar (this) + state-level equivalents
- **Member voting records** → Legistar (this) + GovTrack (federal) + OpenStates (state)
- **Lobbying / influence** → Senate LDA + OpenSecrets
- **Civic engagement** → Harvard CCC + Civicus Monitor (unrest overlap)

For a US-specific governance dashboard, the most useful set is
**Legistar (municipal) + OpenStates (state) + GovTrack (federal) +
LDA/OpenSecrets (influence)**. Legistar is the right place for
city-council granularity.

## See also

- [Civicus Monitor](civicus-monitor.md) — civic-space ratings by country (different axis: civic vs legislative)
- [OpenStates](https://openstates.org/) — state legislature data (US, free, public-domain) — note: not in our vault yet
- [GovTrack](https://www.govtrack.us/) — federal legislative data
- [Federal Register](https://www.federalregister.gov/) — federal executive rules
- `geops.md` — the commercial equivalent for *transit* data; same "us-gov data behind a SaaS API" pattern
- `ingest/fetchers/` — the OData paging pattern is the closest to what `ckan.py` does (also OData)
- This is the **first concrete coverage we have of the `governance` axis** in our 12-axis schema — worth wiring up the moment a NYC-area tenant signs up


## Migrated Context (From Granicus Legistar Web API — NYC Council.md)

---
tags: [source, governance, tier-1, osint-data, requires-key]
status: active
display_name: "Granicus Legistar Web API — NYC Council"
fetcher: ingest.fetchers.legistar
source_name: legistar_nyc
api_key_env: LEGISTAR_NYC_TOKEN
---

# Granicus Legistar Web API — NYC Council

Granicus Legistar Web API for the NYC Council. Bills, resolutions, motions, votes, council members, committees, meetings, bill histories. Public domain (US gov work product). Free API token via https://council.nyc.gov/legislation/api/ form. OData v3 query. The same SaaS backs ~3,000 US municipalities.

## Metadata

| Field | Value |
|---|---|
| Source system | `legistar` |
| Base URL | https://legistar.council.nyc.gov |
| API base | https://webapi.legistar.com/v1/nyc |
| Client | `nyc` |
| Schedule (cron) | `0 */6 * * *` (every 6 hours) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | governance |
| License | Public domain (US Government work product) |
| Auth | **Required**: `LEGISTAR_NYC_TOKEN` (free) |
| per_tenant_only | false |

## Collections

| Name | Endpoint | Description |
|---|---|---|
| `bodies` | `/Bodies` | Committees + chambers (~25 committees + full City Council) |
| `persons` | `/Persons` | Council members + staff |
| `matters` | `/Matters` | Bills, resolutions, motions, local laws (filter by PassageDate / status / type) |
| `events` | `/Events` | Meetings (Stated, Committee, Hearings) — filter by date range |
| `matter_histories` | `/Matters/{MatterId}/Histories` | Audit trail of each bill |
| `roll_calls` | `/EventItems/{EventItemId}/RollCalls` | Roll-call votes; join with /Votes for per-member yea/nay/abstain |

## Fetcher

`ingest/fetchers/legistar.py` (OData v3 client)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='legistar_nyc'`. Per-matter, per-event, per-roll-call rows.

## Common queries

```
GET /v1/sources/legistar_nyc
GET /v1/sources/legistar_nyc/bundles?matter_type=Resolution&since=2026-09-01
GET /v1/sources/legistar_nyc/aggregates?group_by=sponsor,status
```

## Gotchas

- API token is **free** but requires manual form submission at https://council.nyc.gov/legislation/api/. No instant signup.
- OData v3 means `$filter`, `$select`, `$orderby`, `$top`, `$skip` query params (not v4).
- The same SaaS serves ~3,000 US municipalities — if we want to expand, the URL pattern is `webapi.legistar.com/v1/<client>`.

## Related

- [[Plan/Source Categorization]] (governance axis)
- [[Ingestion/NYC Benefits Screening API (ACCESS NYC)]] (companion NYC data)
- [[Ingestion/Granicus Legistar Web API — Other Municipalities]] (planned Phase 2)
