# NYC Benefits Screening API (City of New York / Mayor's Office for Economic Opportunity)

Key: `pending — request a personal access token via the form at https://eepurl.com/gfLTuH (free, public-domain City of NY work product, ~1-2 business day turnaround). One token per requesting organization.`
Endpoint: `https://screeningapi.cityofnewyork.us/`
Auth: `Authorization: Token <token>` header (or `?token=` query param on some endpoints; docs example uses header)
Format: **JSON** (POST a household + person list → array of eligible programs with monthly/annual benefit amounts)

Documentation:
- data.gov catalog record: https://catalog.data.gov/dataset/nyc-benefits-screening-api
- API documentation: https://screeningapidocs.cityofnewyork.us/ (with embedded Swagger UI + Markdown reference)
- Account request form: https://eepurl.com/gfLTuH
- Consumer-facing app: https://access.nyc.gov/eligibility/ (the screener a NYC resident actually uses)
- Underlying rules engine (open source): https://github.com/NYCOpportunity/benefits-screening-rules (Python, last push 2026-09-03)
- Companion rules repo (Drools): https://github.com/NYCOpportunity/ACCESS-NYC-Rules
- Live API endpoint: https://screeningapi.cityofnewyork.us/ (returns `{"detail": "Authentication credentials were not provided."}` without a token)
- Companion dataset (programs catalog, Socrata): https://data.cityofnewyork.us/Social-Services/Benefits-and-Programs-API/2j8u-wtju
- Source agency: Mayor's Office for Economic Opportunity (NYC Opportunity / NYCOpportunity)
- License: **Public domain** — City of New York work product, no copyright asserted; rules are open source in NYCOpportunity GitHub org
- First published in the federal data.gov catalog: 2019-04-19; last updated 2024-10-30; dataset identifier `qcqw-kzj6`

## What it is

The **NYC Benefits Screening API** is the machine-readable version of
the eligibility screener that powers **ACCESS NYC** — the official
City-of-New-York tool that tells a resident which Federal, State, and
Municipal benefits programs they qualify for, and what the estimated
monthly + annual dollar value is.

The screener covers **35+ benefits programs** including:

| Program | Level | Type |
|---|---|---|
| **SNAP** (Supplemental Nutrition Assistance Program) | Federal | Food |
| **Cash Assistance** (Family Assistance / Safety Net Assistance) | State | Cash |
| **WIC** (Women, Infants, and Children) | Federal | Food + nutrition |
| **HEAP** (Home Energy Assistance Program) | State | Heating/cooling |
| **Section 8 / Housing Choice Voucher** | Federal | Housing |
| **CityFHEPS** (NYC rental assistance) | Municipal | Housing |
| **SSI** (Supplemental Security Income) | Federal | Cash (disabled/aged) |
| **Medicaid** | Federal/State | Health |
| **Child Health Plus** | State | Health |
| **Essential Plan** (NY State of Health) | State | Health |
| **Child Care Voucher** | State | Childcare |
| **Pre-K / 3-K / EarlyLearnNYC** | Municipal | Childcare / education |
| **FHEPS / SOTA** | State | Housing |
| **Fair Fares NYC** (50% MetroCard discount) | Municipal | Transit |
| **IDNYC** (free municipal ID) | Municipal | Identity |
| **Lifeline** (phone/internet discount) | Federal | Telecom |
| **School Meals** (free breakfast/lunch) | Federal | Food |
| **Summer Meals** | Federal | Food |
| **Commodity Supplemental Food** | Federal | Food |
| **Senior Farmers' Market Nutrition** | Federal | Food |
| **WIC Farmers' Market Nutrition** | Federal | Food |
| **Child Tax Credit** | Federal | Tax |
| **Earned Income Tax Credit (EITC)** | Federal | Tax |
| **NYC Free Tax Prep** | Municipal | Tax |
| **Senior Citizen Rent Increase Exemption (SCRIE)** | State | Housing |
| **Disability Rent Increase Exemption (DRIE)** | State | Housing |
| **Senior Citizen Homeowners' Exemption (SCHE)** | State | Property tax |
| **Disabled Homeowners' Exemption (DHE)** | State | Property tax |
| **Veterans' Property Tax Exemption** | State | Property tax |
| **Access-A-Ride** | Municipal | Transit |
| **Reduced-Fare MetroCard** | Municipal | Transit |
| **NYC Care** (low-cost health care) | Municipal | Health |
| **HRA Home Care** | State | Health |
| **NY State of Health (Navigator help)** | State | Health |
| **HASA** (HIV/AIDS Services Administration) | State | Health + housing |

Each program has structured eligibility rules (income limits by
household size, age, disability, immigration status, ZIP, etc.) and
returns a benefit-amount formula (some are flat dollar amounts, some
are income-graduated, some are tax-credits).

## Why this is interesting to us

The screener is essentially a **rules engine for US social safety net
eligibility**. The rules themselves — income thresholds, age cutoffs,
household-size adjustments, immigration-status requirements — are
**public policy**, not proprietary data. New York has open-sourced the
rule definitions in
[`NYCOpportunity/benefits-screening-rules`](https://github.com/NYCOpportunity/benefits-screening-rules)
(Python, last commit 2026-09-03) and
[`NYCOpportunity/ACCESS-NYC-Rules`](https://github.com/NYCOpportunity/ACCESS-NYC-Rules)
(Drools rule format).

For OpenTIR-Data, the value proposition is:

1. **The rules ARE the data** — store the eligibility matrix
   (program × household-size × income limit × immigration-status
   matrix) as a structured warehouse table. This is the most useful
   public-facing artifact we can produce for journalists reporting on
   benefit cliffs, gaps, or where eligibility is at the
   state/federal/municipal seam.
2. **Per-query screening results are per-tenant, per-user** — the
   POST endpoint is for individual screening (a person with a specific
   household composition). We do not store per-person screening
   queries in the shared warehouse. A tenant that needs bulk
   screening (e.g. a newsroom testing 1,000 hypothetical households
   for a story) calls the API through their per-tenant token.
3. **Cross-reference with the companion "Benefits and Programs
   Dataset"** at `data.cityofnewyork.us/Social-Services/Benefits-and-Programs-API/2j8u-wtju`
   (Socrata) which lists every program with its own page.

## Verified probe findings (2026-09-05)

I confirmed the following directly:

| Endpoint | Result |
|---|---|
| `GET https://screeningapidocs.cityofnewyork.us/` | **200** — full Markdown reference + Swagger UI for the API |
| `GET https://screeningapi.cityofnewyork.us/` (no token) | **401** — `{"detail": "Authentication credentials were not provided."}` |
| `GET https://catalog.data.gov/dataset/nyc-benefits-screening-api` | **200** — DCAT catalog record, identifier `qcqw-kzj6`, first published 2019-04-19, last updated 2024-10-30, public access level |
| `GET https://data.cityofnewyork.us/Social-Services/Benefits-and-Programs-API/2j8u-wtju` | **200** — companion programs catalog on Socrata |
| `https://github.com/NYCOpportunity/benefits-screening-rules` | **200** — Python rules engine, last commit 2026-09-03 |
| `https://github.com/NYCOpportunity/ACCESS-NYC-Rules` | **200** — Drools rules repo (NOASSERTION license) |

The account request form (`eepurl.com/gfLTuH`) submits to a Mailchimp
form ("Service Coordination & Application Tracking" — internal City
of NY team). The documentation says requests are processed within
**1-2 business days** and the API token is sent by email. There is
no automated signup; this is intentional, because the agency wants
to track which organizations are using the API and for what.

## The request/response shape

The screen API uses a POST. The exact request schema is documented in
the Swagger UI; a simplified shape is:

```json
POST https://screeningapi.cityofnewyyouk.us/screening
Authorization: Token <your-token>
Content-Type: application/json

{
  "household": [
    {
      "relationship": "head",
      "age": 35,
      "gender": "f",
      "pregnant": false,
      "blind": false,
      "disabled": false,
      "student": false,
      "looking_for_work": true,
      "work_status": "unemployed",
      "work_hours_per_week": 0,
      "monthly_income": 0,
      "citizenship": "us_citizen",
      "residency": "nyc",
      "zipcode": "10001"
    },
    {
      "relationship": "child",
      "age": 7,
      "gender": "m",
      "citizenship": "us_citizen",
      "residency": "nyc"
    }
  ],
  "expenses": {
    "rent": 1800,
    "heat": "included",
    "child_support_paid": 0
  }
}
```

A successful response lists each program the household qualifies for,
with the **estimated monthly dollar value** and **estimated annual
dollar value**. A useful query is `?format=full` (or similar) for the
underlying rules that fired, so a tenant can write a story about
*why* a particular program was / wasn't included.

## ⚠️ The catch: per-organization token required

| Aspect | Detail |
|---|---|
| **Auth** | One personal token per requesting organization. The form is at `eepurl.com/gfLTuH`. ~1-2 business day turnaround. |
| **Quota** | No public per-token rate limit. The agency tracks usage by token. |
| **Per-tenant model** | This is the **per-tenant** model — each newsroom / non-profit / government tenant that wants to do bulk screening gets their own token. The shared warehouse only stores the **rule catalog** (one row per program, refreshed when NYCOpportunity updates the rules). |
| **License** | Public domain (City of NY work product). Rules open-sourced under MIT-style permissive terms by NYCOpportunity. |
| **Public data path** | Even without a token, the `data.cityofnewyork.us/Social-Services/Benefits-and-Programs-API/2j8u-wtju` dataset is public and lists every program. The rules (income thresholds, age cutoffs, immigration status) are public; only the per-household screening is gated by token. |

## How we wire it up

The right wiring for OpenTIR-Data:

1. **The rule catalog** (program list, income thresholds by household
   size, age cutoffs, citizenship requirements) goes into
   `osint.governance_programs` as one row per program × state of the
   rules. This is the data we **share** in the warehouse.
2. The `ingest/fetchers/nyc_benefits_screening.py` fetcher:
   - **Tier 1**: weekly refresh of the program catalog from the
     companion Socrata dataset (`2j8u-wtju`) — no token needed.
   - **Tier 2**: weekly pull of the rule definitions from
     `github.com/NYCOpportunity/benefits-screening-rules` — no token
     needed.
   - **Tier 3** (optional, per-tenant): POST representative households
     to `screeningapi.cityofnewyork.us/` with the tenant's own token
     for analysis. Each tenant's screening results are stored under
     their `org_id` RLS scope in `osint.query_history`; they are
     **not** aggregated into the shared warehouse.
3. The `sources.yaml` block keeps `enabled: false` by default and
   `requires_key: true` with `key_env: NYC_BENEFITS_SCREENING_TOKEN`.
4. Per-org env-var wiring follows the same pattern as
   [`legistar.md`](legistar.md): a per-tenant `NYC_BENEFITS_SCREENING_TOKEN`
   in `/etc/osint/<org>/secrets.env` for the newsroom / non-profit
   tenants that want bulk screening.

This makes the **rules** a shared-warehouse first-class data source
(matches the `governance` and `economic` axes) and the **per-household
screening** a per-tenant feature that flows through the same RLS
boundary as the rest of our app state.

## What we use the data for (concrete use cases)

- **Journalist**: "How many NYC households making $30k/year with 2
  kids qualify for CityFHEPS but not Section 8?" → table.
- **Non-profit benefits navigator**: bulk screen 200 client
  households, get a list of programs each qualifies for, in their
  CRM.
- **Policy researcher**: track how income thresholds change year over
  year → `osint.governance_programs` time series.
- **Developer**: build a Slack bot that lets a benefits navigator
  paste a household and get back a benefits list — the screening
  API is what powers the bot.

## See also

- [`legistar.md`](legistar.md) — same per-tenant token pattern; this
  is the closest sibling in our vault
- [`civicus-monitor.md`](civicus-monitor.md) — same agency-vs-data
  framing: a research/advocacy org that publishes structured civic
  data we can ingest directly
- [`geops.md`](geops.md) — per-tenant paid pattern (commercial use
  is a different question; NYC Benefits is free + per-tenant-token)
- [`data-gov-apis.md`](data-gov-apis.md) — the data.gov catalog
  itself, where this dataset was discovered
- [`socrata.md`](socrata.md) — the Socrata fetcher used to pull the
  companion programs catalog
- [`liveuamap.md`](liveuamap.md) — the documented non-connector
  pattern (anti-example: a paywalled source where NYC Benefits is
  the free, public-domain equivalent in its domain)

## License of this connector note

`connectors/nyc-benefits-screening.md` is dedicated to the public
domain under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From NYC Benefits Screening API (ACCESS NYC).md)

---
tags: [source, governance, economic, tier-1, osint-data, requires-key, per-tenant-only]
status: active
display_name: "NYC Benefits Screening API (ACCESS NYC)"
fetcher: ingest.fetchers.nyc_benefits_screening
source_name: nyc_benefits_screening
api_key_env: NYC_BENEFITS_SCREENING_TOKEN
---

# NYC Benefits Screening API (ACCESS NYC)

NYC Benefits Screening API. 35+ Federal/State/Municipal benefits programs (SNAP, Cash Assistance, WIC, HEAP, Section 8, CityFHEPS, Fair Fares). Public domain. Per-tenant token via https://eepurl.com/gfLTuH. Rules open-sourced at NYCOpportunity/benefits-screening-rules.

## Metadata

| Field | Value |
|---|---|
| Source system | `nyc_benefits_screening` |
| Base URL | https://screeningapidocs.cityofnewyork.us |
| API base | https://screeningapi.cityofnewyork.us |
| Schedule (cron) | `0 4 * * 0` (Sundays at 04:00 UTC) |
| Rate limit | 30 req/min |
| Tier | 1 |
| Axis | governance, economic |
| License | Public domain (US Government work product) |
| Auth | **Required**: `NYC_BENEFITS_SCREENING_TOKEN` (per-tenant) |
| per_tenant_only | **true** (screening calls are per-tenant only) |

## Collections

| Name | Endpoint | Format | Notes |
|---|---|---|---|
| `program_catalog` | https://data.cityofnewyork.us/resource/2j8u-wtju.json | Socrata JSON | public program list |
| `rules_engine` | https://raw.githubusercontent.com/NYCOpportunity/benefits-screening-rules/master/README.md | HTML scrape | open-sourced rules |
| `screening_calls` | https://screeningapi.cityofnewyork.us/screening | request/response | **per-tenant only** |

## Fetcher

`ingest/fetchers/nyc_benefits_screening.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='nyc_benefits_screening'`. Per-tenant screening results; catalog is shared.

## Common queries

```
GET /v1/sources/nyc_benefits_screening
GET /v1/sources/nyc_benefits_screening/bundles?program=SNAP
```

## Gotchas

- **The actual screening calls are per-tenant-only** — each tenant brings their own NYC token and runs screenings against their own data. The shared warehouse only stores the program catalog + rules engine.
- Companion programs catalog at data.cityofnewyork.us/Social-Services/Benefits-and-Programs-API/2j8u-wtju.
- The rules engine is open-sourced — replicate the rules in our own code for non-NYC tenants if needed.

## Related

- [[Plan/Source Categorization]] (governance + economic axes)
- [[Ingestion/Granicus Legistar Web API — NYC Council]] (companion NYC data)
- [[Ingestion/World Bank FinancesOne (FONE)]] (governance + economic at global scale)

