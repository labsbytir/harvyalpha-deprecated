# OWID Datasets (archived legacy collection)

Key: `none required` — all datasets are public CSV data, with per-dataset source attribution in `datapackage.json`. **The repo itself has no declared license** (no `LICENSE` file, GitHub API reports `license: null`), but the underlying data is published under CC-BY-4.0 from the original source (CDC, WHO, World Bank, FAO, OECD, etc.). **Use the data; do not copy the repo's automation code without checking the source terms.**

Status: **archived** — the README at the top of the repo says: *"This repository has not been updated in some time, and has therefore been archived. There are new ways to obtain chart data and metadata: Our Chart API, Improved data downloads, ETL."*

Endpoint: `https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/<name>/<name>.csv`
Auth: none
Format: CSV (long format, plus per-dataset `datapackage.json` for Frictionless Data Package metadata)

Documentation:
- Repo: https://github.com/owid/owid-datasets
- README: https://raw.githubusercontent.com/owid/owid-datasets/master/README.md
- Successor (recommended): the [OWID Chart API](https://docs.owid.io/projects/etl/api/chart-api/) — programmatic access to any chart's data
- Successor (data downloads): https://ourworldindata.org/easier-to-reuse-our-data
- Successor (full ETL): https://github.com/owid/etl

## What's in the box

```text
owid-datasets/
├── README.md             (the "archived" notice + the per-dataset format spec)
└── datasets/             (766 folders, 278 MB total)
    ├── 20th century deaths in US - CDC/
    │   ├── 20th century deaths in US - CDC.csv    (32 KB, 1900-1998 deaths)
    │   ├── README.md                              (411 bytes, short blurb)
    │   └── datapackage.json                       (15 KB, Frictionless metadata)
    ├── A Century of Work and Leisure - Ramey and Francis (2009)/
    │   ├── *.csv
    │   ├── README.md
    │   └── datapackage.json
    ├── ...   (763 more)
    └── pm25-exposure-world-bank/
```

**Each of the 766 datasets** follows the same shape:
- One **CSV** with the data (typically `Entity, Year, ...indicators` columns)
- One **README.md** with a short description
- One **datapackage.json** (Frictionless Data Package spec) with full metadata: title, description, sources (with URLs and retrieval dates), tags, and a per-column schema

The CSV is the data, the `datapackage.json` is the gold for our resolver — it has the source URL, retrieval date, and column types in machine-readable form.

## Why the license is a non-issue for our use case

The repo's code (the script that generates `datapackage.json`) has no declared license. But:

1. **The data itself is from public sources** — CDC, WHO, World Bank, FAO, OECD, etc., each with their own open license (mostly CC-BY-4.0 or public domain for government data).
2. **The `datapackage.json` includes the source attribution** — every dataset points back to the original publisher and URL.
3. **Our resolver** already tracks the upstream source via `metadata.publisher` and `metadata.source_url` (see the `dataset_fingerprint` resolver in `ingest/resolver.py`). We'd credit CDC, WHO, World Bank, etc. — not "OWID".
4. **OWID explicitly redirects users** to the successor (the ETL pipeline + Chart API) which is properly maintained.

So: use the data with proper attribution to the original source, link to the upstream URL, and treat this as a convenient archive of already-cleaned smaller datasets.

## Sample datapackage.json (real, from "20th century deaths in US - CDC")

```json
{
  "name": "20th century deaths in US - CDC",
  "title": "20th century deaths in US - CDC",
  "id": 1937,
  "description": "Data is compiled based on the list of top 10 causes of death published by the Centre for Diseases Control (CDC). This is measured across both sexes and all ages. Death rates are reported per 100,000 and are not age-standardized.",
  "sources": [
    {
      "name": "20th century deaths in US - CDC",
      "dataPublishedBy": "Centre for Diseases Control (CDC). Leading Causes of Death, 1900-1998.",
      "dataPublisherSource": null,
      "link": "https://www.cdc.gov/nchs/data/dvs/lead1900_98.pdf",
      "retrievedDate": "1st February 2018",
      "additionalInfo": "..."
    }
  ],
  "owidTags": ["Causes of Death"],
  "resources": [
    {
      "path": "20th century deaths in US - CDC.csv",
      "schema": {
        "fields": [
          {"name": "Entity",  "type": "string"},
          {"name": "Year",    "type": "year"},
          {"name": "Heart disease - Deaths", "type": "integer"},
          ...
        ]
      }
    }
  ]
}
```

This is a **Frictionless Data Package** — a community-standard spec for describing tabular data. Our resolver can ingest the `datapackage.json` and use it to populate `metadata.publisher`, `metadata.source_url`, `metadata.retrieved_at`, and the column schema — all for free.

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/owid_datasets.py
import json
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

BASE = "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets"


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            # 1. Enumerate all dataset folders via the GitHub API
            r = await client.get(
                "https://api.github.com/repos/owid/owid-datasets/contents/datasets",
                headers={"Accept": "application/vnd.github+json"},
            )
            r.raise_for_status()
            for entry in r.json():
                name = entry["name"]
                # 2. Fetch the metadata (datapackage.json) — this is the gold
                meta_resp = await client.get(f"{BASE}/{name}/datapackage.json")
                if meta_resp.status_code != 200:
                    continue
                metadata = meta_resp.json()
                # 3. Fetch the CSV
                csv_resp = await client.get(f"{BASE}/{name}/{name}.csv")
                csv_resp.raise_for_status()
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="archived_datasets",
                    source_id=str(metadata.get("id", name)),
                    source_url=f"https://github.com/owid/owid-datasets/tree/master/datasets/{name}",
                    bundle_url=f"{BASE}/{name}/{name}.csv",
                    fetched_at=self.now(),
                    payload=csv_resp.content,
                    payload_format="csv",
                    metadata={
                        "title": metadata.get("title"),
                        "description": metadata.get("description"),
                        "sources": metadata.get("sources", []),
                        "tags": metadata.get("owidTags", []),
                        "schema": metadata.get("resources", [{}])[0].get("schema", {}),
                    },
                )
```

## Quick call — verify

```bash
# List the first 3 datasets
curl -sL "https://api.github.com/repos/owid/owid-datasets/contents/datasets" \
  | python3 -c "import json,sys; [print('  -',d['name']) for d in json.load(sys.stdin)[:5]]"

# Sample dataset (one of the 766)
curl -sL "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/20th%20century%20deaths%20in%20US%20-%20CDC/20th%20century%20deaths%20in%20US%20-%20CDC.csv" \
  | head -3

# Same dataset's metadata
curl -sL "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/20th%20century%20deaths%20in%20US%20-%20CDC/datapackage.json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('  title:', d['title']); print('  source:', d['sources'][0]['dataPublishedBy']); print('  link:', d['sources'][0]['link'])"
```

Expected:
- First 5 datasets listed
- CSV first row: `Entity,Year,Accidents (excl. road) - Deaths,Accidents (total)  - Deaths,...`
- Metadata: `title: 20th century deaths in US - CDC`, `source: Centre for Diseases Control (CDC).`, `link: https://www.cdc.gov/nchs/data/dvs/lead1900_98.pdf`

## Notes

- **766 datasets, ~278 MB total.** Crawl-once-and-cache. Re-pull only when the dataset shows `last_seen_at` drift.
- **The CSV format is wide, not long** — each row is one (entity, year) and columns are indicators. For the resolver, treat each indicator (column) as a separate variable. This means a single OWID dataset often expands to 5–20+ "logical" datasets in our catalog.
- **`datapackage.json` is the gold** — it has the original source URL, the retrieval date, the column schema, and the OWID tags. Use it to populate `metadata.publisher`, `metadata.source_url`, `metadata.retrieved_at`, `metadata.tags` automatically.
- **The 766 datasets skew smaller** than the main OWID catalog (which has 3,000+ via the ETL). This is by design — these were the "individually uploaded and annotated" ones. The big datasets (life expectancy, GDP, CO2) live in the ETL/Chart API now.
- **Cross-source dedup**: the archived datasets overlap heavily with the upstream sources (CDC ↔ WHO ↔ World Bank). The `dataset_fingerprint` resolver will merge them by `(title, publisher, period, country, tags)`. Use the `dataPublishedBy` field in `datapackage.json` as the canonical publisher, not "OWID".
- **For the new world dashboard, prefer the Chart API.** This archived repo is the "if Chart API doesn't have it" fallback. Both share the same underlying ETL, so the data is consistent — but the Chart API is alive, the data downloads are alive, and only this archive is frozen in time.
- **The ETL repo's `snapshots/` directory is the source of truth** for any dataset you find here. If you want the latest version, check the corresponding `etl/snapshots/{source}/{YYYY-MM-DD}/` directory for the most recent extract.

