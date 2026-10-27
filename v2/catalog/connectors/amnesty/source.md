# Amnesty International (amnestyusa.org, amnesty.org)

Key: `none — research/advocacy org, no public data API. Documented as non-connector.`
Endpoint: `n/a` (intentionally empty)
Auth: n/a
Format: n/a

Documentation:
- USA site: https://www.amnestyusa.org/ (Cloudflare-gated, no public API)
- Global site: https://www.amnesty.org/ (`/api` returns 500; `/en/latest/news` returns 200 as plain HTML — no RSS, no JSON)
- Decoders: https://decoders.amnesty.org/ (unreachable as of 2026-09; was a citizen-science human-rights micro-tasking platform)
- Security Lab: https://www.amnesty.org/en/tech/ (forensic methodology, not a data API)
- GitHub org `amnesty`: empty (0 repos in API; Amnesty's security work lives under `mvt-project` now)
- GitHub org `amnestywebsite`: only the `humanity-theme` WordPress theme (NOASSERTION license)

## What it is

**Amnesty International** is a human-rights research and advocacy
organisation, not a structured-data publisher. Their primary public surface
is press releases, reports, and policy documents — not bulk data feeds.

They do have two technical open-source threads worth knowing about, but
**neither is a data source we can ingest**:

1. **Amnesty Security Lab** published the forensic methodology behind
   the **Pegasus Project** (2021) — the methodology that detected NSO
   Group's Pegasus spyware on journalists' and activists' phones. The
   methodology is now productised as a tool, not a dataset.
2. **Mobile Verification Toolkit (MVT)** — the consumer-facing
   companion to that methodology. Lives at `github.com/mvt-project/mvt`
   (13k stars, NOASSERTION license, 4 public repos total: `mvt`,
   `androidqf`, `mvt-indicators` (MIT), `.github`, `license`). It is
   a forensic tool for analysing iOS/Android devices, **not** a data
   feed.

## ⚠️ Why we deliberately do NOT add this to `sources.yaml`

| Reason | Detail |
|---|---|
| **No public data API** | `amnestyusa.org` is fully Cloudflare-gated — every API path returns 403, even `/about` and `/en/who-we-are`. `amnesty.org/en/latest/news` returns HTML 200 with no RSS or JSON feed. The legacy `/api` endpoint returns 500. |
| **No bulk export** | Amnesty's content lives in long-form reports and PDF investigations. No machine-readable endpoint, no CKAN, no OData. |
| **Decoders is offline** | `decoders.amnesty.org` (their citizen-science micro-tasking platform) was unreachable on every probe (DNS / connection / TLS). The Amnesty Decoders archive on GitHub (`amnesty/decoders`) is no longer maintained. |
| **The only structured Amnesty-adjacent dataset** is the **Pegasus victim list** — a third-party repo `GranittHQ/data-pegasus-victims` (36 stars, last push 2023-11, no license). Far too sparse and stale to be a primary source. |
| **Press releases as a proxy are too noisy** | Amnesty's news flow is ~3-5 items/day, mostly reactive statements, with no lat/lon and no structured incident schema. Better covered by **External APIs** and the press-release feeds we already ingest. |

## What to use instead (free, open, machine-readable)

| Domain | Recommended connector | Notes |
|---|---|---|
| **Civic space / civil-society rating by country** | **[`civicus-monitor`](civicus-monitor.md)** (CC-BY-SA 4.0, public RSS, 198 countries × 5-tier rating) | The actual data publisher in this space. |
| **Conflict events, fatalities, actors** | **ACLED** (free academic tier via request) — covered in [`realtime-osint-roadmap`](realtime-osint-roadmap.md) | ACLED explicitly codes Amnesty-style "violence against civilians" events. |
| **Press freedom / journalist persecution** | **Civicus Monitor** (above) + **RSF Press Freedom Index** (annual PDF) | RSF data is annual, not real-time; the `explore/` page on Civicus is the better real-time proxy. |
| **Torture / detention / individual cases** | **No automated source exists.** Amnesty's case work is qualitatively reported, not coded. For individual-name searches, use **HRDAG** or **OpenSanctions** (see `realtime-osint-roadmap.md`). |
| **Spyware / surveillance-for-hire indicators** | **Citizen Lab** (https://citizenlab.ca/) — research reports + indicator feeds + the `mvt-indicators` repo (MIT, in this vault via MVT). | The IOCs from the Pegasus Project are in `mvt-project/mvt-indicators` (153 stars, MIT, regularly updated). |

## How to use Amnesty content the right way

1. **Do not** try to scrape `amnestyusa.org` (Cloudflare will block the
   IP and the `ckan.py`-style fetcher will hang on the JS challenge).
2. **Do** subscribe to their press-release email for human reading
   (https://www.amnesty.org/en/latest/news/ — opens in a browser, not
   a feed reader).
3. **Do** ingest the **Civicus Monitor** RSS feed (this vault,
   `civicus-monitor.md`) and the **ACLED** data export to cover the
   same evidentiary space with structured fields.
4. **Do** link Amnesty **report URLs** in `payloads.extras` when
   ingesting related events from another source, as provenance.
5. **Do** mention **MVT** by name in `docs/tools.md` so an analyst can
   use it to verify a device compromise claim, but do not ingest from
   it.

## See also

- [`civicus-monitor`](civicus-monitor.md) — the free, structured, human-rights data publisher in this space
- [`mvt-project/mvt-indicators`](https://github.com/mvt-project/mvt-indicators) — MIT-licensed spyware IOCs, also referenced from `docs/tools.md`
- [`realtime-osint-roadmap`](realtime-osint-roadmap.md) — for ACLED, RSF, HRDAG, OpenSanctions
- [`no-public-api`](no-public-api.md) — the master "research/advocacy orgs that have no public data API" note
