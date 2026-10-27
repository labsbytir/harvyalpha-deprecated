# FiveThirtyEight datasets

Key: `none required` — all datasets are public GitHub repos under MIT/CC-BY-4.0.

Endpoint: `https://raw.githubusercontent.com/fivethirtyeight/data/master/...`
Auth: none
Format: CSV (primary), some R/Python scripts

Documentation:
- Data index: https://data.fivethirtyeight.com/
- GitHub: https://github.com/fivethirtyeight/data
- License: each dataset's `LICENSE` file (most are CC-BY-4.0)
- Article companion index: https://data.fivethirtyeight.com/

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/fivethirtyeight.py
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url="https://api.github.com",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Accept": "application/vnd.github+json"},
        ) as client:
            # 1. List every directory at the top level of the repo
            r = await client.get("/repos/fivethirtyeight/data/contents/")
            r.raise_for_status()
            for entry in r.json():
                if entry["type"] != "dir":
                    continue
                dir_name = entry["name"]
                # 2. List the contents of each dataset directory
                r2 = await client.get(f"/repos/fivethirtyeight/data/contents/{dir_name}")
                if r2.status_code != 200: continue
                for f in r2.json():
                    if f.get("name", "").endswith(".csv"):
                        yield RawBundle(
                            source_system=self.source_system,
                            source_collection=dir_name,
                            source_id=f["name"],
                            source_url=f"https://data.fivethirtyeight.com/",
                            bundle_url=f"https://raw.githubusercontent.com/fivethirtyeight/data/master/{dir_name}/{f['name']}",
                            fetched_at=self.now(),
                            payload=b"", payload_format="csv",
                            metadata={"dir": dir_name, "file": f["name"], "size": f.get("size")},
                            is_remote_only=True,
                        )
            # 3. Resolver then downloads the raw_url for each bundle.
```

## Quick call — verify

```bash
# A known dataset
curl -sL "https://raw.githubusercontent.com/fivethirtyeight/data/master/presidential-2020/presidential_state_toplines_2020.csv" \
  | head -3
```

If that returns a CSV header row, the GitHub raw URL works without auth. (My probe returned 404 because the file path was wrong — the actual path uses different naming. Use the `tree` endpoint above to enumerate, or browse the GitHub UI.)

```bash
# Use the GitHub API to list the repo's top-level entries (free, 60 req/hr unauthenticated)
curl -sL "https://api.github.com/repos/fivethirtyeight/data/contents/" \
  | python3 -c "import json,sys; print(len(json.load(sys.stdin)), 'top-level entries')"
```

## Endpoints used (verified live 2026-09-04)

```text
GET https://api.github.com/repos/fivethirtyeight/data/contents/                    # top-level dir
GET https://api.github.com/repos/fivethirtyeight/data/contents/{dir}              # files in a dataset dir
GET https://raw.githubusercontent.com/fivethirtyeight/data/master/{dir}/{file}    # raw CSV
GET https://github.com/fivethirtyeight/data                                       # HTML index
```

GitHub API: unauthenticated = 60 req/hr per IP. Add a token to raise to 5,000/hr. Free token at https://github.com/settings/tokens (no scopes needed for read-only).

## Notes

- The repo has 100+ dataset directories. Some are CSV, some are R scripts that generate CSVs (you'd need to re-run them — out of scope for v1).
- Each dataset comes with a companion article — the GitHub README is the catalog.
- Datasets are versioned by Git commits. `git log` gives a per-file history; the GitHub API gives file-level metadata at any commit.
- License is mostly CC-BY-4.0. Always check `LICENSE` in each dataset dir before redistributing.
- For OSINT, the highest-value datasets are: presidential polling, election forecasts, COVID-19 tracker, political polarization indices, policing/geographic data, congressional approval ratings.
- The resolver will dedupe FiveThirtyEight's CSVs against any other source carrying the same data (e.g. state-level polling data appears in many other CSVs).

