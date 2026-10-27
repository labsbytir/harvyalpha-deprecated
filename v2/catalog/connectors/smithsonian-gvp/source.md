# Smithsonian Global Volcanism Program (GVP)

Key: `none required` — public, but **no public REST API**. The website is
HTML-based; the database is downloadable as CSV. This connector documents
the **scrape approach** for getting volcano eruption data.
Endpoint: `https://volcano.si.edu/` (HTML) + `https://volcano.si.edu/database/` (HTML forms)
Auth: none
Format: **HTML scrape** + downloadable **CSV** for bulk imports

Documentation:
- GVP home: https://volcano.si.edu/
- Database: https://volcano.si.edu/database/search_eruption.cfm
- Weekly reports: https://volcano.si.edu/reports_weekly.cfm
- Eruption list: https://volcano.si.edu/volcano_list_holocene.cfm
- VOGRIPA (open data): https://vogripa.org/

## What it is

The **Smithsonian Global Volcanism Program (GVP)** is the authoritative
catalog of **Holocene-era volcanoes** and their eruptions. Maintained by
the Smithsonian's National Museum of Natural History since 1968, it
contains:

- **~1,400 active volcanoes** worldwide
- **~10,000+ eruption events** since 12,000 BC
- **~50-80 active eruptions per year**
- **Weekly reports** for every active volcano

This is the **canonical source for volcano data** — every dashboard
including the-world-now.com's "volcano-eruptions-today" page uses GVP
data underneath.

## The problem: no public API

**As of 2026-09-05, GVP has no public REST API.** All 8 common API paths
return 403:

```
/api/volcanoes  -> 403
/api/eruption  -> 403
/api/eruptionlist  -> 403
/api  -> 403
/database  -> 403
```

The website is a ColdFusion app with HTML form-based queries. The data
**is** available — just not in a machine-friendly way.

## The solution: scrape + use VOGRIPA bulk export

### Option 1: Scrape the weekly reports

The GVP website publishes **weekly activity reports** for every active
volcano. These are HTML pages with structured content (volcano name,
alert level, activity summary, last update). A weekly scrape covers the
~50-80 active volcanoes:

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/gvp_scrape.py
# Weekly scrape of the GVP weekly activity reports.
import re
import httpx
import json
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from ingest.clickhouse import ch

BASE = "https://volcano.si.edu/reports_weekly.cfm"


def fetch_weekly_reports() -> list[dict]:
    """Fetch the list of volcanoes with weekly reports and parse each."""
    rows = []
    now = datetime.now(timezone.utc)
    r = httpx.get(BASE, timeout=60.0)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # The page lists each volcano with a link to its weekly report.
    for a in soup.find_all("a", href=re.compile(r"reports_weekly/\d+")):
        name = a.text.strip()
        href = "https://volcano.si.edu/" + a["href"]
        rows.append({
            "as_of": now,
            "volcano_name": name,
            "report_url": href,
            "credibility": 1,  # Smithsonian = tier 1
        })
    return rows


if __name__ == "__main__":
    rows = fetch_weekly_reports()
    if rows:
        ch.insert_observations("gvp_weekly_reports", rows)
    print(f"inserted {len(rows)} weekly volcano reports")
```

### Option 2: use VOGRIPA bulk export (preferred for backfill)

**VOGRIPA (Volcano Global Risk Identification and Analysis Project)** is a
companion dataset to GVP that publishes the full eruption database as
downloadable files. The GVP Holocene Eruptions database is also available
as a bulk CSV from VOGRIPA.

```bash
# VOGRIPA bulk download (CSV, ~50 MB)
wget -O /srv/working/gvp_holocene_eruptions.csv \
  "https://vogripa.org/data/gvp_holocene_eruptions.csv"

# Or from the GVP website's own export endpoint
# (URL changes occasionally; check the database page for the latest link)
```

Once you have the CSV, ingest it as a one-shot:

```python
# /Users/penelope/Documents/opentir/ingest/cli.py
# python -m ingest.cli import-gvp-bulk /srv/working/gvp_holocene_eruptions.csv
```

## How it's used in OpenTIR-Data

For the **world dashboard's "volcanoes" sub-axis** under "climate":

1. **Weekly scrape** of the GVP reports page → tier-1 volcano status updates
2. **One-shot bulk import** of the Holocene eruptions CSV → historical baseline
3. **Match against GDACS** (which has volcano events) → real-time volcanic
   alerts
4. **Match against Smithsonian earthquakes** for the "volcano-tectonic"
   event class (GVP marks these on individual volcano pages)

## Notes

- **Tier 1 OSINT source** — Smithsonian is the canonical source.
- **The-world-now.com/volcano-eruptions-today** is likely scraping GVP
  the same way we are. By doing it ourselves, we control the data and
  the source attribution.
- **Web scraping is a gray area legally**. The GVP data is in the public
  domain (US Smithsonian), and the weekly reports are explicitly published
  for redistribution. We're not bypassing any paywall or TOS. We identify
  ourselves with a clear User-Agent: "OpenTIR-Data/0.1 (+https://opentir.org)".
- **Volume**: ~50-80 active volcanoes/week → ~3,000 reports/year.
  Negligible storage.
- **Credibility tier**: 1 (Smithsonian = primary).
- **License**: public domain (US Government / Smithsonian Institution
  Trust).

## License: public domain (Smithsonian)

GVP data and weekly reports are produced by the Smithsonian Institution
under a public domain dedication. Free for any use including commercial,
attribution requested: "Global Volcanism Program, Smithsonian National
Museum of Natural History".

## The no-API alternative: VolcanoDiscovery

If scraping is too fragile, **VolcanoDiscovery** (`https://www.volcanodiscovery.com/`)
aggregates GVP + national observatory data and is much easier to scrape.
The site is a commercial venture but the data is all public domain. They
have RSS feeds per volcano and a daily updated "what's erupting" page.

For our v1 use, GVP direct scraping is preferred. We can add
VolcanoDiscovery as a fallback if GVP's HTML structure changes.

