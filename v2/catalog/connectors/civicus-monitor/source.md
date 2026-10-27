# Civicus Monitor (civic-space ratings, global)

Key: `none required` — public, free, no auth
Endpoint: `https://monitor.civicus.org/feed/` (RSS 2.0)
Auth: none
Format: **RSS 2.0** (press updates) + **HTML scrape** for the country-by-country 5-tier rating matrix

Documentation:
- Home: https://monitor.civicus.org/
- Data dashboard: https://monitor.civicus.org/data/ (timeline 2018-2024 + current)
- Ratings: https://monitor.civicus.org/about/how-it-works/ratings/
- RSS: https://monitor.civicus.org/feed/
- About: https://monitor.civicus.org/about/
- Research partner: https://monitor.civicus.org/about/research-partners/
- Methodology: https://monitor.civicus.org/about/how-it-works/methodology/
- License: **CC-BY-SA 4.0** (declared in footer of every page)

## What it is

**Civicus Monitor** tracks the state of **civic space** (freedom of
association, peaceful assembly, expression) in **198 countries**. It is
run by the **CIVICUS** civil-society alliance, with research partners
in every region. Each country gets a **0-100 score** and a **5-tier
rating**: **Open** / **Narrowed** / **Obstructed** / **Repressed** /
**Closed**. Scores are updated continuously; the full historical
timeline covers 2018-present.

This is the **real data publisher** in the human-rights space where
**Amnesty International**, **Human Rights Watch**, and the UN special
rapporteurs publish press releases but no structured data. Civicus is
the only one that gives you a comparable 0-100 score per country that
updates with press-release-grade events.

## What you can ingest

### 1. RSS feed (easiest, machine-readable)
- URL: `https://monitor.civicus.org/feed/`
- ~5-10 items/week
- Each item: title, link, pubDate, image (1080×673+), short description
- No lat/lon; country is in the title and description

### 2. Country rating matrix (HTML scrape)
- URL: `https://monitor.civicus.org/data/`
- Renders a world-map with `id="item-<ISO3>"` rows for ~198 countries
- Each row: country name, score (0-100), rating (Open/Narrowed/Obstructed/Repressed/Closed)
- Year-by-year timeline selectable via `.js-year-button` (2018-2024 + "Current data")
- License: CC-BY-SA 4.0 (per the footer link)

### 3. Country detail page (HTML, per country)
- URL: `https://monitor.civicus.org/country/<slug>/` (e.g. `/country/afghanistan/`)
- Score history, recent events, ratings by year, latest update date

## Data shape (RSS item)

```xml
<item>
  <title>Australia: Protesters continue to be targeted as courts push back on anti-protest laws and baseless charges</title>
  <link>https://monitor.civicus.org/explore/australia-protesters-continue-to-be-targeted-as-courts-push-back-on-anti-protest-laws-and-baseless-charges/</link>
  <pubDate>Thu, 03 Sep 2026 03:08:34 +0000</pubDate>
  <guid>monitor.civicus.org:explore:7439</guid>
  <media:content url="https://civicusmonitor.contentfiles.net/media/original_images/..." />
</item>
```

## Data shape (country rating row, HTML)

```html
<tr>
  <td><a href="/country/afghanistan/" class="link--country">Afghanistan</a></td>
  <td><span class="countries-list__score">8/100</span></td>
  <td class="Closed"><span>Closed</span></td>
</tr>
```

Plus a `data-iso="AFG"` attribute on the row — that's the join key.

## Free, no key, no quota

- **No auth.** No API key, no signup, no rate-limit headers seen.
- **CC-BY-SA 4.0** — share-alike is fine for our AGPL-3.0 (we are
  *more* restrictive on the project's own code; the data we ingest
  must still carry the SA clause if we redistribute, but the
  warehouse keeps attribution).
- **Real-time**: 5-10 items/week, plus rating-matrix updates as
  scores change.

## How to fetch

```bash
# 1. Pull the press-update RSS as a sanity check
curl -sSL https://monitor.civicus.org/feed/ | head -40

# 2. Pull the country-by-country rating matrix and parse the rows
curl -sSL https://monitor.civicus.org/data/ -o /tmp/civicus.html
python3 - <<'PY'
from bs4 import BeautifulSoup
import re
html = open('/tmp/civicus.html').read()
soup = BeautifulSoup(html, 'html.parser')
for row in soup.select('tr[id^="item-"]'):
    iso = row.get('data-iso')
    name = row.select_one('a.link--country').text.strip()
    score = row.select_one('.countries-list__score').text.strip()
    rating = row.select_one('td:last-child span').text.strip()
    print(f"{iso}\t{name}\t{score}\t{rating}")
PY
# AFG	Afghanistan	8/100	Closed
# ALB	Albania	68/100	Narrowed
# ...
```

## Suggested `sources.yaml` entry

```yaml
- id: civicus_monitor
  display_name: "Civicus Monitor"
  domain: monitor.civicus.org
  axis: human_rights
  tier: open
  license: CC-BY-SA-4.0
  license_url: https://creativecommons.org/licenses/by-sa/4.0/
  requires_key: false
  schedule: 0 */6 * * *   # every 6 hours
  rate_limit_rpm: 30
  attribution: "CIVICUS Monitor, https://monitor.civicus.org/, CC-BY-SA 4.0"
  endpoints:
    rss: https://monitor.civicus.org/feed/
    ratings: https://monitor.civicus.org/data/
  description: |
    Civic-space ratings (Open / Narrowed / Obstructed / Repressed / Closed)
    for 198 countries, plus press-update RSS. CC-BY-SA 4.0. Real-time.
```

## Coverage vs. alternatives

| Need | Best free source |
|---|---|
| **Country-level civic-space rating (5-tier, comparable across years)** | **Civicus Monitor** ← this connector |
| **Conflict events with fatalities and actors** | ACLED (academic tier) |
| **Press freedom index (annual)** | RSF (PDF only) — referenced from `realtime-osint-roadmap.md` |
| **Amnesty International case-by-case reports** | No automated source — see [`amnesty`](amnesty.md) |
| **Human Rights Watch reports** | No automated source — see `no-public-api.md` |

## See also

- [`amnesty`](amnesty.md) — the research/advocacy org that does *not* publish data, contrasted with Civicus
- [`realtime-osint-roadmap`](realtime-osint-roadmap.md) — ACLED, RSF, HRDAG, OpenSanctions (the broader human-rights data ecosystem)
- [`harvard-ccc`](harvard-ccc.md) — US protest events; pairs with Civicus for *what* is happening
- [`nostr-nip52`](nostr-nip52.md) — decentralised global event announcements
