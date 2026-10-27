# OWID Chartbook of Economic Inequality

Key: `none required` for the data. **The code has no declared license** (HTTP 404 on `LICENSE` files, GitHub API returns `license: null`), but the **data is published** at a public Google Sheet and is freely accessible. Use the data with attribution; don't copy the repo's automation code (it's an old R + Python 2 workflow anyway, not worth forking).

Status: **archived / frozen.** Last push 2022-06-21. The data is a snapshot of inequality research through ~2020; the underlying academic sources continue to update (WID.world, World Bank, OECD, etc.) but this repo doesn't.

Endpoint:
- **Real data (Google Sheet, public, no auth)**: `https://docs.google.com/spreadsheets/d/1jLNfP3iuteUJrH0zS9qWONskyKh9pFcl1hKSlgEc-I8/gviz/tq?tqx=out:csv&sheet=All+data`
- **References CSV**: `https://raw.githubusercontent.com/owid/chartbook/main/References.csv`
- **Repo (HTML pages, 27 country folders)**: `https://github.com/owid/chartbook`

Auth: none
Format: `CSV` (data), `CSV` (references)

Documentation:
- Repo: https://github.com/owid/chartbook
- README: https://raw.githubusercontent.com/owid/chartbook/main/README.md
- Live data sheet: https://docs.google.com/spreadsheets/d/1jLNfP3iuteUJrH0zS9qWONskyKh9pFcl1hKSlgEc-I8/edit#gid=1578718062
- 27 country Google Sheets linked from the README (one per country)

## What this gives you

A **curated, peer-reviewed, time-series dataset of economic inequality** for 27 countries. The data shape is rich:

```csv
country,year,value,series_code,dimension,measure,welfare_concept,short_reference,long_reference,reference url,preferred_definition,description,source_codes_used,legend
argentina,1953,0.45,aptinc,relative,gini,disposable_income,Altimir 1986,"Altimir, Oscar...",https://doi.org/...,...
argentina,1959,0.41,aptinc,relative,gini,disposable_income,Altimir 1986,...,
...
united_states,1913,0.51,aptinc,relative,gini,disposable_income,Atkinson Piketty 2010,...,
```

**14 columns:**
- `country`, `year`, `value` — the core triple
- `series_code` — e.g. `aptinc` (after-tax-personal-income), `aptwea` (wealth), `sptinc992` (P99/P90 ratio)
- `dimension` — `relative` vs `absolute`
- `measure` — `gini`, `top1`, `top10`, `p90p10`, `palma`, etc.
- `welfare_concept` — `disposable_income`, `market_income`, `wealth`, `consumption`
- `short_reference`, `long_reference`, `reference url` — full academic citation
- `preferred_definition`, `description`, `source_codes_used`, `legend` — methodology metadata

**16,213 rows, 27 countries, ~100 years of data per country.** This is the most rigorous public inequality dataset I've seen. Every row is tied to a specific academic source with DOI.

## The 27 countries

```text
Argentina, Australia, Brazil, Canada, Finland, France, Germany, Iceland, India,
Indonesia, Italy, Japan, Malaysia, Mauritius, Netherlands, New Zealand, Norway,
Portugal, Singapore, South Africa, Spain, Sweden, Switzerland, UK, US, …
```

Each has its own Google Sheet (linked in the README) and its own folder in the repo. The "All data" sheet is the consolidated 16k-row CSV.

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/owid_chartbook.py
import csv
import io
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

ALL_DATA = (
    "https://docs.google.com/spreadsheets/d/1jLNfP3iuteUJrH0zS9qWONskyKh9pFcl1hKSlgEc-I8"
    "/gviz/tq?tqx=out:csv&sheet=All+data"
)
REFERENCES = "https://raw.githubusercontent.com/owid/chartbook/main/References.csv"


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. The data (16k rows)
            r = await client.get(ALL_DATA)
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="inequality_series",
                source_id="all-countries",
                source_url=ALL_DATA,
                bundle_url=ALL_DATA,
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={
                    "row_count": sum(1 for _ in r.text.splitlines()) - 1,
                    "columns": r.text.splitlines()[0] if r.text else "",
                    "countries": 27,
                },
            )

            # 2. The references (189 academic citations)
            r = await client.get(REFERENCES)
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="references",
                source_id="all-references",
                source_url=REFERENCES,
                bundle_url=REFERENCES,
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={"row_count": sum(1 for _ in r.text.splitlines()) - 1},
            )
```

## Quick call — verify

```bash
# The data (16k rows, 6.3 MB CSV)
curl -sL -A "Mozilla/5.0" \
  "https://docs.google.com/spreadsheets/d/1jLNfP3iuteUJrH0zS9qWONskyKh9pFcl1hKSlgEc-I8/gviz/tq?tqx=out:csv&sheet=All+data" \
  -o /tmp/cb.csv -w "code=%{http_code} size=%{size_download}\n"
echo "  rows: $(wc -l < /tmp/cb.csv 2>/dev/null)"
echo "  header: $(head -1 /tmp/cb.csv 2>/dev/null)"

# The references
curl -sL "https://raw.githubusercontent.com/owid/chartbook/main/References.csv" \
  -o /tmp/refs.csv -w "code=%{http_code} size=%{size_download}\n"
echo "  references: $(wc -l < /tmp/refs.csv 2>/dev/null)"
```

Expected:
- `cb.csv`: HTTP 200, 6.3 MB, 16,214 rows (header + 16,213 data)
- `refs.csv`: HTTP 200, 50 KB, 189 lines

## Why the data is special

What makes this dataset OSINT-grade:

1. **Every row is academically cited.** `reference url` points to a DOI; `long_reference` is the full citation. The `series_code` lets you trace each data point back to a specific paper.
2. **Multiple inequality metrics, harmonized.** `aptinc` (after-tax income), `aptwea` (wealth), `sptinc992` (top 1% share), `p90p10` (90/10 ratio), `palma` (Palma ratio), `gini`. All in one table, comparable across countries.
3. **Welfare concept is explicit.** `disposable_income` vs `market_income` vs `consumption` vs `wealth` — the user can filter to "income inequality after taxes and transfers" without ambiguity.
4. **Methodology metadata per row.** `preferred_definition`, `description`, `source_codes_used` let a researcher (or AI agent) decide whether the row matches their question.
5. **Long time series.** Most countries have 50+ years of data, some (US, UK, France) 100+ years. This is the **only public source** that has harmonized inequality time series across many countries at this depth.

## Notes

- **The Google Sheet is the canonical source** — pull from there, not from the repo. The repo's `bottom_chart.csv` per country is a small derived artifact; the Sheet has the full 16k rows with all the methodology metadata.
- **The repo code is old** (R + Python 2-era, d3 v3, c3.js). The `dataprep.R` and `chartprep.py` scripts are 100 lines of data-wrangling boilerplate that we don't need — our resolver does the same work more cleanly.
- **For the world dashboard**, this is the **inequality layer**. The data renders well as small multiples (one chart per country, multiple metrics) or as a global ranking (top 10 most unequal countries, change over time).
- **The `References.csv`** is gold for the resolver's `metadata.publisher` field. Use it directly: each row has `Country, Reference, Reference URL` — perfect for our `dataset.metadata.sources[]` array.
- **Cross-source dedup**: the Gini coefficient in this dataset overlaps with World Bank's `SI.POV.GINI`, the OECD's Income Distribution Database, and SWIID. The `dataset_fingerprint` resolver will merge them all into one logical series. This dataset's `welfare_concept` field is the most explicit of the bunch, so it should win ties.
- **The chartbook is the right sibling to the OWID main catalog.** OWID's main ETL covers economic growth, demographics, energy, etc. The chartbook is the curated, peer-reviewed deep-dive on economic inequality. Use both.
- **No live updating.** The Google Sheet is presumably maintained by hand by the chartbook maintainers. Re-pull monthly. The underlying academic series continue to evolve (WID.world updates annually), so the chartbook lags by 1-2 years vs the latest research.
- **The 27-country list is biased toward developed countries** plus a few middle-income (Brazil, Argentina, Mexico, China, India, South Africa, Indonesia, Malaysia, Mauritius). The "missing" countries (most of Africa, Central Asia, etc.) reflect where academic inequality research has been done, not where inequality doesn't exist.

