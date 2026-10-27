# DOE OE-417 — Electric Emergency Incident and Disturbance Report

Key: `none required (US federal public domain)`
Endpoint: `https://www.oe.netl.doe.gov/oe417_annual_summary.aspx`
Auth: `none`
Format: **Excel** (annual summary workbooks, 2000-present) + **PDF** (per-event narrative reports)

Documentation:
- Annual summary data tables: https://www.oe.netl.doe.gov/oe417_annual_summary.aspx
- Form submission portal: https://doe417.pnnl.gov/
- OpenEnergyHub mirror: https://openenergyhub.ornl.gov/explore/dataset/oe-417-annual-summaries/
- EIA archive: https://www.eia.gov/electricity/data/disturbance/
- License: **Public domain** (17 U.S.C. § 105, US Government work)
- Maintainer: DOE Office of Cybersecurity, Energy Security, and
  Emergency Response (CESER), via NETL/PNNL
- Time range: **2000 through present** (per-event, with annual
  summaries)

## What it is

**Form OE-417** (Electric Emergency Incident and Disturbance
Report) is the federal reporting form that US electric utilities,
regional reliability organizations, and balancing authorities
**must submit to the Department of Energy** within specific
timeframes when they experience:

- Loss of firm load ≥ 300 MW for ≥ 1 hour
- Load shedding of ≥ 100 MW
- Voltage reductions of ≥ 5%
- Public appeals to reduce demand
- Physical attacks / vandalism / cyber attacks on grid
  infrastructure
- Loss of monitoring or control capability (SCADA / EMS failures)
- Fuel supply emergencies (natural gas, coal, uranium)
- Loss of equipment or generation ≥ 2,000 MW

The form captures **event-level** data: what happened, where,
when, who was affected, and the cause. This is the federal record
of major grid events.

The form data is published in two forms:
- **Annual summary** (Excel / PDF) — a year-by-year table of all
  reported events with cause, region, demand loss, customers
  affected, and category. Public domain.
- **Per-event PDF narrative** — the actual OE-417 form submissions
  with full operational details. Often FOIA-required, sometimes
  proactively published.

## What it covers that other sources don't

| Aspect | ODIN | EAGLE-I | PowerOutage.us | **OE-417** |
|---|---|---|---|---|
| Real-time | Yes | No (historical) | Yes | No (event-based) |
| Customer-level counts | Yes | Yes | Yes | Yes (per-event aggregate) |
| Cause detail | Brief | Brief | Brief | **Detailed narrative** |
| Cyber attack | No | No | No | **Yes** |
| Physical attack | No | No | No | **Yes** |
| Fuel supply emergency | No | No | No | **Yes** |
| Voltage reduction | No | No | No | **Yes** |
| Load shedding | No | No | No | **Yes** |
| Equipment failure | Yes | Yes | Yes | Yes (with full detail) |
| Generation outage | No | No | No | **Yes** (≥2,000 MW) |

**OE-417 is the right source for understanding the operational
context of a major event** — not just the "X customers were out
for Y hours" but the "we lost 3,000 MW of generation because of
a cold snap in Texas" or "ransomware attack on a control center
caused 4-hour load shedding across two states."

## How to wire it up for OpenTIR-Data

1. **First ingest**: download each annual summary Excel from
   `https://www.oe.netl.doe.gov/oe417_annual_summary.aspx`. One
   file per year, 2000-present.
2. **Per-event schema**: each row is one event with
   `(date_event_began, time_event_began, date_of_restoration,
   time_of_restoration, area_affected, nerc_region, alert_criteria,
   event_type, demand_loss_mw, customers_affected, category)`.
3. **Correlation with ODIN + EAGLE-I**: join on
   `(date_event_began, area_affected, nerc_region)` to enrich
   the outage timeline with the cause narrative.
4. **Cross-reference with EIA**: the EIA publishes per-event
   summaries in the Electric Power Monthly, "Major Electric
   Disturbances and Unusual Occurrences" Appendix B1/B2.
5. **Per-tenant alert triggers**: subscribe to the DOE CESER
   email list (https://doe417.pnnl.gov) for new event submissions;
   ingest to `osint.oe417_events` for the journalist-dashboard
   "major events" view.

## The third-party mirror: securethegrid.com

A security researcher maintains an analysis of all OE-417 data from
2010 to present at `https://securethegrid.com/oe-417-database/`,
with a CSV download. This is useful as a cross-check on the
official summaries and as a more queryable index. **Not** a primary
source — go to the DOE/NETL annual summaries first.

## The OpenEnergyHub synthesis

OpenEnergyHub has a synthesized dataset at
`https://data.openei.org/files/6458/Outage_Dataset_R1.zip` that
merges:

- **EAGLE-I** (2014-2022 per-county outages, ~2M events)
- **OE-417** (per-event major disturbance reports)
- **US Census CO-EST2024-POP** (county population estimates)

into a single event-correlated dataset under **CC0** (no
attribution required). This is the right starting point if you
want one downloadable file with everything.

## Important caveats

| Caveat | Detail |
|---|---|
| **Public domain but Excel format** | The annual summaries are XLSX. Convert to CSV or Parquet on first ingest. |
| **2000+ events, not millions** | OE-417 is major events only, not every customer outage. Use ODIN for high-volume real-time. |
| **Submission lag** | Utilities have 1 hour, 6 hours, or 24 hours to submit depending on severity. Events appear in the summaries weeks-to-months after. |
| **Per-event PDFs are FOIA-only by default** | The detailed OE-417 forms are not all publicly downloadable. Many require FOIA requests to DOE. |
| **Categories overlap** | A single event may have multiple alert_criteria values. Dedup is required. |
| **NERC also tracks similar data** | The North American Electric Reliability Corporation tracks the same events at a regional level, often with more operational detail. Public at `https://www.nerc.com/pa/rrm/ea/Pages/Lessons-Learned.aspx`. |

## What we use it for

- **Major event timeline**: any time we need to answer "what
  happened in [state] in [year] that caused major outages?" OE-417
  is the canonical source.
- **Cause attribution**: when a journalist asks "was that
  outage caused by a cyber attack, a storm, or a grid failure?"
  OE-417 has the cause field.
- **Cross-source correlation**: per-event joining with ODIN
  (real-time customer counts) and EAGLE-I (per-county historical)
  gives the complete picture.
- **Network / event timelines**: the OE-417 PDF narratives
  (when FOIA'd) include operator statements, which are great
  for the Story view's "what actually happened" panel.

## See also

- [[odin]] — the real-time customer-level data
- [[eagle_i]] — the historical customer-level archive
- [[openenergyhub_event_correlated]] — the EAGLE-I + OE-417 +
  Census synthesized dataset (CC0)
- [[nerc]] — the regional reliability coordinator complement
- [[poweroutage_us]] — the commercial aggregator's event catalog

## License of this connector note

`connectors/doe_oe417.md` is dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.


## Migrated Context (From DOE OE-417 Electric Emergency Incident Reports.md)

---
tags: [source, info_environment, security, cyber, tier-1, osint-data, public-no-auth]
status: active
display_name: "DOE OE-417 Electric Emergency Incident Reports"
fetcher: ingest.fetchers.doe_oe417
source_name: doe_oe417
---

# DOE OE-417 Electric Emergency Incident Reports

DOE OE-417 — Electric Emergency Incident and Disturbance Report. Public domain (US Government work). Annual Excel summaries 2000-present. Per-event reports for major disturbances ≥ 300 MW load loss, including weather, equipment failure, physical attacks, cyber attacks, fuel emergencies. The right source for the operational context of a major event.

## Metadata

| Field | Value |
|---|---|
| Source system | `doe_oe417` |
| Base URL | https://www.oe.netl.doe.gov/oe417_annual_summary.aspx |
| API base | https://doe417.pnnl.gov |
| Schedule (cron) | `0 0 1 * *` (monthly) |
| Rate limit | 12 req/min |
| Tier | 1 |
| Axis | info_environment, security, cyber |
| License | Public domain (US Government work) |
| Auth | none (public) |
| per_tenant_only | false |
| format | xlsx + csv |

## Collections

| Name | Endpoint | Notes |
|---|---|---|
| `annual_summary_excel` | https://www.oe.netl.doe.gov/oe417_annual_summary.aspx | annual Excel |
| `openenergyhub_mirror` | https://openenergyhub.ornl.gov/explore/dataset/oe-417-annual-summaries/ | CSV mirror on OpenEnergyHub |

## Fetcher

`ingest/fetchers/doe_oe417.py`

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='doe_oe417'`. Per-event rows: `event_date`, `event_type`, `area_affected`, `demand_loss_mw`, `customers_affected`, `cause`, `restoration_date`, `narrative`.

## Common queries

```
GET /v1/sources/doe_oe417
GET /v1/sources/doe_oe417/bundles?event_type=Cyber%20Attack&since=2015-01-01
GET /v1/sources/doe_oe417/aggregates?group_by=cause,year
```

## Gotchas

- 300 MW threshold is approximate; some smaller events are also reported.
- `event_type` taxonomy: `Weather`, `Equipment Failure`, `Physical Attack`, `Cyber Attack`, `Fuel Emergency`, `Operator Action`, `Vandalism`, `Other`.
- Mirror at PNNL (Pacific Northwest National Lab) is more reliable than the .netl.doe.gov page.

## Related

- [[Plan/Source Categorization]] (info_environment + security + cyber axes)
- [[Ingestion/ODIN — Outage Data Initiative Nationwide (ORNL/DOE)]] (real-time)
- [[Ingestion/EAGLE-I Historical US Outage Archive (ORNL 2014-2022)]] (per-county history)
- [[Ingestion/AlienVault OTX Threat-Intel Pulses]] (cyber context)

