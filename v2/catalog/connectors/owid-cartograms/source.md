# OWID World Population Cartograms

Key: `none required` — ISC-licensed (BSD-equivalent) JS/Python project. Code is free to fork, modify, and self-host.

Endpoint (live demo): `https://owid.github.io/cartograms/`
Endpoint (raw data on GitHub): `https://raw.githubusercontent.com/owid/cartograms/master/data/...`
Auth: none
Format: CSV (cells), TopoJSON (base map), rendered as D3 SVG in browser

Documentation:
- Repo: https://github.com/owid/cartograms
- Live demo: https://owid.github.io/cartograms/
- Algorithm reference: Dougenik, Chrisman & Niemeyer (1985), "An Algorithm to Construct Continuous Area Cartograms"
- OWID article: https://ourworldindata.org/world-population-cartogram

## What this gives you

A **world population cartogram** — each country is drawn as a hexagonal grid where the number of cells is proportional to the country's population in a given year. The cells flow into each other with continuous borders, so the shape preserves coastline and country identity while making population differences instantly visible. India and China dwarf Europe; Africa grows dramatically in the 21st century; Russia becomes a small patch.

The whole repo is small:
- 7 JS files in `core/` totaling ~21 KB
- 1 Python script (`core/export.py`, 7.5 KB) for offline regeneration
- 1 MB UN Population Division data (`data/population/unpd.csv`)
- 41 KB of pre-computed cells (`data/output/v1/cells.csv`)
- One HTML page + 2 CSS/JS files for the UI

## Inputs

| Path | Size | What it is |
|---|---|---|
| `data/population/unpd.csv` | 1 MB | UN Population Division estimates, every country × every 5-year interval, 1950–2100 |
| `data/population/unpd-flat.csv` | 348 KB | Long format: country, year, population, area |
| `data/base/2018/v1/` and `v2/` | — | The world base map at 2018 (used as the input geometry). v2 is a higher-resolution version. |
| `data/country-code.csv` | 5.9 KB | ISO 3166-1 numeric → ISO 3166-1 alpha-3 → country name |
| `data/output/v1/cells.csv` | 41 KB | The pre-computed cartogram: `X, Y, CountryCode` (one row per hex cell) |

## Outputs (what the algorithm produces)

The `cells.csv` is a simple flat table:

```text
X, Y, CountryCode
12, 8, CHN
13, 8, CHN
14, 8, CHN
15, 8, IND
16, 8, IND
...
```

The JS frontend reads this CSV and renders each cell as a small hexagon at the (X, Y) position, colored by country. The total number of cells per country = `population / cell_value` where `cell_value` is the population per cell (1.5 million by default; user-adjustable in the UI).

## How it's used in OpenTIR-Data

### Path 1: use the pre-computed cells.csv (zero computation)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/owid_cartograms.py
import csv
import io
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. The pre-computed cells (v1)
            r = await client.get("https://raw.githubusercontent.com/owid/cartograms/master/data/output/v1/cells.csv")
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="cells",
                source_id="v1",
                source_url="https://owid.github.io/cartograms/",
                bundle_url="https://raw.githubusercontent.com/owid/cartograms/master/data/output/v1/cells.csv",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={"version": "v1", "cell_count": len(r.text.splitlines()) - 1},
            )

            # 2. The UNPD population data
            r = await client.get("https://raw.githubusercontent.com/owid/cartograms/master/data/population/unpd.csv")
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="population",
                source_id="unpd",
                source_url="https://population.un.org/wpp/",
                bundle_url="https://raw.githubusercontent.com/owid/cartograms/master/data/population/unpd.csv",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={"source": "UN Population Division"},
            )

            # 3. Country code mapping
            r = await client.get("https://raw.githubusercontent.com/owid/cartograms/master/data/country-code.csv")
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="country-codes",
                source_id="iso-mapping",
                source_url="https://github.com/owid/cartograms/blob/master/data/country-code.csv",
                bundle_url="https://raw.githubusercontent.com/owid/cartograms/master/data/country-code.csv",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={"source": "ISO 3166-1"},
            )
```

### Path 2: regenerate cartograms server-side for any year

```python
# Clone the repo and run the Python export script. The cartogram generation
# is purely Python (numpy + shapely + matplotlib), no browser needed.
#
# git clone https://github.com/owid/cartograms
# cd cartograms
# pip install -r requirements.txt
# python core/export.py --year 2050 --cell-value 2000000 --output /var/lib/clickhouse/cartograms/2050
#
# Then ingest the output CSV into ClickHouse.
```

## Quick call — verify

```bash
# Live cells CSV (v1, ~6k cells for 2018)
curl -sL "https://raw.githubusercontent.com/owid/cartograms/master/data/output/v1/cells.csv" \
  | head -5
echo ""
curl -sL "https://raw.githubusercontent.com/owid/cartograms/master/data/output/v1/cells.csv" | wc -l
echo " cells total"

# UNPD population data sample
curl -sL "https://raw.githubusercontent.com/owid/cartograms/master/data/population/unpd-flat.csv" \
  | head -3

# Country code mapping
curl -sL "https://raw.githubusercontent.com/owid/cartograms/master/data/country-code.csv" \
  | head -5

# Live demo
curl -sL -A "Mozilla/5.0" "https://owid.github.io/cartograms/" -w "demo: code=%{http_code} size=%{size_download}\n" -o /dev/null
```

Expected:
- `cells.csv` first row: `0,0,AFG` (or similar; X,Y,CountryCode)
- ~6,000 cells total
- `unpd-flat.csv` first row: header `Location,Time,PopTotal,PopDensity,PopMale,PopFemale,...`
- `country-code.csv` first row: `4,AFG,Afghanistan,Asia`
- demo: HTTP 200

## Notes

- **ISC license** is essentially MIT. You may fork, modify, and redistribute with attribution. The author is `Adesh Nalpet Adimurthy`.
- **The cartogram is the right "globe" view** for the world dashboard: instead of forcing viewers to read a Mercator projection, the country sizes ARE the data. Perfect for population, GDP, energy use, internet users, deaths from any cause.
- **Same algorithm, different variables**: the `unpd.csv` can be replaced with any country × value table (e.g. `owid/co2-data` for CO2 emissions, `owid/energy-data` for energy use) and the algorithm produces a cartogram where each country is sized by that value. The output is always `X, Y, CountryCode` plus the value.
- **For the world dashboard**: render `cells.csv` as a deck.gl `HexagonLayer` colored by your variable of choice. With a live OpenSky layer on top, you get "live flights over a population-shaped world" in one map.
- **The 2018 base map is a hardcoded snapshot.** For cartograms of 1900 or 2100, you need a base map with the historical or projected borders. The repo only has 2018; for other years, use the Natural Earth dataset or a custom simplification.
- **Performance**: the browser-side algorithm runs the cartogram generation in 5–30 seconds for 6,000 cells on a modern laptop. For real-time updates, pre-compute offline and serve the `cells.csv` as a static asset.
- **Mobile-friendly**: yes — the live demo works on phones, the SVG is responsive.
- **Citation**: if you use this in a published product, cite the OWID article and the Dougenik et al. (1985) algorithm paper. Both are noted in the repo's README.
- **Cross-source dedup**: the cells.csv is purely a derived view; the underlying population data (UNPD) is also available in [[connectors/owid-grapher]] charts and the World Bank's `SP.POP.TOTL`. The `dataset_fingerprint` resolver will treat all three as the same logical dataset.

