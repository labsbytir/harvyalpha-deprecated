# Google Public Data Directory / Google Dataset Search

Key: `none required` — both endpoints are public. Google has no API; the data is scraped from the rendered HTML.

Status: **Deprecated, but the successor (Dataset Search) works.** The Public Data Directory at `google.com/publicdata/directory` is no longer updated and the underlying datasets have been removed. The successor is `datasetsearch.research.google.com`, which is a meta-search engine over dataset repositories worldwide.

Endpoint: `https://www.google.com/publicdata/directory` (deprecated, may 404)
Endpoint (successor): `https://datasetsearch.research.google.com/`
Auth: none
Format: HTML scrape only (no public API)

Documentation:
- Public Data Directory: https://www.google.com/publicdata/directory (legacy)
- Dataset Search: https://datasetsearch.research.google.com/
- About Dataset Search: https://datasetsearch.research.google.com/about

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/google_dataset_search.py
import httpx
from selectolax.parser import HTMLParser
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            for query in ("climate change", "open data", "economic indicators"):
                r = await client.get("https://datasetsearch.research.google.com/search",
                                     params={"query": query, "fileType": "all",
                                             "license": "all", "page": 1},
                                     headers={"Referer": "https://datasetsearch.research.google.com/"})
                r.raise_for_status()
                # HTML scrape: each result is a <div class="gs_r"> block with title, snippet, link
                tree = HTMLParser(r.text)
                results = []
                for block in tree.css("div.lc-dWzBTXc-PjbFxf"):
                    title = block.css_first("h1") or block.css_first("a")
                    link = block.css_first("a")
                    snippet = block.css_first("div.lc-dWzBTXc-bQqGNb")
                    if title and link:
                        results.append({
                            "title": title.text(strip=True),
                            "url": link.attributes.get("href"),
                            "snippet": snippet.text(strip=True) if snippet else None,
                        })
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="search",
                    source_id=query,
                    source_url=f"https://datasetsearch.research.google.com/search?query={query}",
                    bundle_url=f"https://datasetsearch.research.google.com/search?query={query}",
                    fetched_at=self.now(),
                    payload=orjson.dumps(results),
                    payload_format="json",
                    metadata={"query": query, "result_count": len(results)},
                )
```

## Quick call — verify

```bash
# Public Data Directory (legacy, may redirect)
curl -sL "https://www.google.com/publicdata/directory" -o /tmp/gpd.html -w "code=%{http_code} size=%{size_download}\n"
# Dataset Search (successor)
curl -sL "https://datasetsearch.research.google.com/search?query=climate" -o /tmp/ds.html -w "code=%{http_code} size=%{size_download}\n"
```

## Notes

- The **Public Data Directory is dead** — Google shut it down in 2019. Most of the underlying datasets were Kaggle / World Bank / US Census. Don't rely on it.
- The **Dataset Search** (successor) is essentially a Google search for datasets. It crawls figshare, DataCite, Dryad, Kaggle, GitHub, and other dataset repositories. There is no API; scrape the HTML.
- For OSINT, Dataset Search is a **discovery** tool, not a primary data source. Use it to find new datasets, then ingest them via their primary API.
- The scraper is fragile: Google's HTML structure changes regularly. Plan for monthly refactors.
- **Better alternatives** for dataset discovery (all have proper APIs):
  - **DataCite** (https://api.datacite.org/) — every DOI-registered dataset
  - **figshare** (https://api.figshare.com/v2/) — 25M+ datasets
  - **Zenodo** (https://zenodo.org/api/records) — research datasets with DOIs
  - **OpenAIRE** (https://api.openaire.eu/) — EU-funded research outputs
  - **CKAN catalog registry** (https://ckan.org/) — most national portals
- For our purposes, Google Dataset Search is best treated as a manual "find new sources" tool, not an automated ingest target.

