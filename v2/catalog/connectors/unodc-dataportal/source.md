# UNODC Data Portal (dataunodc.un.org)

Key: `none required` — public, no auth. No API key exists for the new portal.

Status: **HTML scrape required.** The new portal is a brand-new Drupal 11 SPA (rolled out 2025) that does **not** expose a public JSON/REST API. The actual data is server-rendered HTML inside the `/datareport/*` pages. Confirmed by inspecting the network panel in a real browser: 91 requests on the page, all static assets (JS, CSS, images, fonts) plus Google Analytics; **zero** XHR/fetch calls for data.

Endpoint: `https://dataunodc.un.org/datareport/{slug}` (HTML page; no JSON)
Auth: none
Format: HTML (data is inside a `<table>`)

Documentation:
- Portal: https://dataunodc.un.org
- Mirror: https://data.unodc.org
- Underlying unodc.org: https://www.unodc.org/unodc/en/data-and-analysis/
- Drug monitoring platform: https://dmp.unodc.org/

## How it's used in OpenTIR-Data (HTML scrape approach)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/unodc.py
import asyncio
import httpx
from selectolax.parser import HTMLParser
from ingest.fetchers.base import BaseFetcher, RawBundle

REPORTS = [
    "hom-victim",           # intentional homicide
    "violent-offences",     # violent & sexual crime
    "cjs-arrested",         # access & functioning of justice
    "prison-held",          # prisons & prisoners
    "druguse",              # drug use & treatment
    "druguse-general",      # drug use (general)
    "drug-seizure",         # drug trafficking
    "econ-corruption",      # corruption & other crime
    "firearm-seizures",     # firearms trafficking
    "tip-victims",          # trafficking in persons
    "wildlife-seizures",    # wildlife trafficking
    "sdg-3-5-1",            # SDG 3.5.1 indicator
    "covid-homicide",       # COVID-19 & homicide
]


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://dataunodc.un.org",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
            follow_redirects=True,
        ) as client:
            for slug in REPORTS:
                r = await client.get(f"/datareport/{slug}")
                r.raise_for_status()
                html = r.text
                # parse the main data table
                tree = HTMLParser(html)
                table = tree.css_first("table.data-table") or tree.css_first("table")
                rows = []
                if table:
                    for tr in table.css("tr"):
                        cells = [td.text(strip=True) for td in tr.css("td,th")]
                        if cells:
                            rows.append(cells)
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="reports",
                    source_id=slug,
                    source_url=f"https://dataunodc.un.org/datareport/{slug}",
                    bundle_url=f"/datareport/{slug}",
                    fetched_at=self.now(),
                    payload=orjson.dumps(rows),
                    payload_format="json",
                    metadata={"slug": slug, "row_count": len(rows), "html_bytes": len(html)},
                )
                # also save the raw HTML for archival
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="reports_html",
                    source_id=slug,
                    source_url=f"https://dataunodc.un.org/datareport/{slug}",
                    bundle_url=f"/datareport/{slug}",
                    fetched_at=self.now(),
                    payload=html.encode("utf-8"),
                    payload_format="html",
                    metadata={"slug": slug},
                )
```

## Quick call — verify

```bash
curl -sL "https://dataunodc.un.org/datareport/hom-victim" \
  | python3 -c "
import sys
from selectolax.parser import HTMLParser
html = sys.stdin.read()
tree = HTMLParser(html)
table = tree.css_first('table')
if table:
    rows = [[c.text(strip=True) for c in tr.css('td,th')] for tr in table.css('tr')]
    print(f'rows: {len(rows)}')
    print('header:', rows[0])
    print('row 5:', rows[5])
"
```

## Reports (verified live 2026-09-04)

```text
/datareport/hom-victim            intentional homicide
/datareport/violent-offences      violent & sexual crime
/datareport/cjs-arrested          access & functioning of justice
/datareport/prison-held           prisons & prisoners
/datareport/druguse               drug use & treatment
/datareport/druguse-general       drug use (general)
/datareport/drug-seizure          drug trafficking & cultivation
/datareport/econ-corruption       corruption, environmental, & other crime
/datareport/firearm-seizures      firearms trafficking
/datareport/tip-victims           trafficking in persons
/datareport/wildlife-seizures     wildlife trafficking
/datareport/sdg-3-5-1             SDG 3.5.1 indicator
/datareport/covid-homicide        COVID-19 & homicide
```

Also available:
- `/countryprofile/<ISO3>` — country profile pages
- `/microdata` — microdata catalog
- `/datasearch` — full indicator search

## Notes

- **No public API.** The Drupal 11 SPA loads data into the HTML server-side; no XHR/fetch calls are made. Confirmed by inspecting the network panel in Brave.
- The legacy UNODC site at `https://www.unodc.org/unodc/en/data-and-analysis/` has bulk Excel/CSV downloads that are still public.
- The `dmp.unodc.org` site is a separate Drupal 11 instance for drug monitoring — same approach applies.
- The HTML is messy (deeply nested tables, many class names) — `selectolax` is the right parser; `BeautifulSoup` is too slow and `lxml` is fine too.
- The "Download data" button on each `/datareport/*` page links to a static Excel file; you can also pull those directly with `httpx.get(...)`.
- Cross-source dedup: homicide data overlaps with World Bank `VC.IHR.PSRC.P5` and FBI CDE indicators. The `dataset_fingerprint` resolver will merge.

