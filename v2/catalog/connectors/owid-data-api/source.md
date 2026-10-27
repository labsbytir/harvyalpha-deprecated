# OWID Data API (MIT-licensed, reference implementation)

Key: `none required` — **MIT-licensed** (Copyright Our World in Data). Fork-friendly, modify-friendly. **The data is the same OWID catalog** we already cover in [[connectors/ourworldindata]]; this repo is the **API server that fronts that data with DuckDB + FastAPI**.

Status: **experimental, archived 2022.** Last commit was 2022-08-30. Not publicly deployed. The README says "experimental" multiple times. **Use this as a reference architecture, not a production service.**

Endpoint: **no public deployment exists.** Run it yourself: `git clone https://github.com/owid/data-api && make run`. README has the full instructions.
Auth: none
Format: `JSON`, `CSV`, `Parquet` (the `crawler` uses DuckDB which can write/read all three)

Documentation:
- Repo: https://github.com/owid/data-api
- Local docs: `http://127.0.0.1:8000/v1/docs` after `make run` (FastAPI auto-generated OpenAPI)
- Source: https://raw.githubusercontent.com/owid/data-api/main/README.md
- License: **MIT** (confirmed via `LICENSE` file in repo)

## What this is

The data-api is a **thin REST + SQL layer** over OWID's data catalog. Two components:

```text
┌──────────────┐    crawls every      ┌──────────────┐    REST + SQL    ┌──────────────┐
│ ETL catalog  │ ──────────────────►  │ DuckDB cache │ ────────────────► │ any client   │
│ (parquet on  │                     │ (duck.db)    │   /v1/dataset/   │              │
│  S3 / local) │                     │              │   /v1/sql etc.   │              │
└──────────────┘                     └──────────────┘                   └──────────────┘
```

The **crawler** is a Python script that walks the ETL's published catalog (parquet files in S3) and builds a single DuckDB file. The **API** is a FastAPI service that exposes that DuckDB over REST, including a `POST /v1/sql` endpoint that lets clients run arbitrary SQL.

## Why this matters for OpenTIR-Data

This is the **exact architecture we should build for our own catalog**. We have:

- A 96 GB box with ClickHouse (the warehouse)
- ~30 source connectors feeding data into ClickHouse
- A `dataset_fingerprint` resolver that dedupes across sources

The data-api gives us the **server-side API surface** to expose that to:

1. **AI agents** (the MCP server we discussed in [[connectors/owid-browser-semantic-search]])
2. **Third-party developers** who want programmatic access without running the Python pipeline
3. **Dashboards** that want fast SQL queries (faster than going through Next.js → ClickHouse direct)
4. **External data scientists** who want to query our warehouse with familiar SQL

The MIT license means we can **fork this repo and adapt it for ClickHouse** — replacing DuckDB with ClickHouse, swapping the crawler for our existing ingest pipeline, keeping the FastAPI structure.

## Sample endpoints (from the README)

| Method | Path | What it does |
|---|---|---|
| `GET` | `/health` | health check |
| `GET` | `/v1/variableById/data/{id}` | one variable's time series (JSON) |
| `GET` | `/v1/variableById/metadata/{id}` | one variable's metadata (JSON) |
| `GET` | `/v1/dataset/data/{channel}/{namespace}/{version}/{dataset}/{table}.csv` | full dataset as CSV |
| `GET` | `/v1/dataset/data/{channel}/{namespace}/{version}/{dataset}/{table}.feather` | full dataset as Feather (binary) |
| `GET` | `/v1/dataset/metadata/{...}` | dataset metadata |
| `POST` | `/v1/sql` | arbitrary SQL against the catalog |
| `GET` | `/v1/sql?sql=...&type=csv` | GET variant of /v1/sql |

The `POST /v1/sql` is the killer feature:

```bash
# List every table in the catalog
http POST http://127.0.0.1:8000/v1/sql \
  sql="PRAGMA show_tables;" type=csv

# Read 10 rows from a dataset
http POST http://127.0.0.1:8000/v1/sql \
  sql="select * from garden__ggdc__2020_10_01__ggdc_maddison__maddison_gdp limit 10;" type=csv
```

That's the **killer pattern** for an OSINT data warehouse. Users (and AI agents) can issue arbitrary SQL against your catalog and get CSV/JSON back. No special SDK, no per-endpoint API learning curve.

## How it's used in OpenTIR-Data (3 ways)

### Way 1: fork the repo, swap DuckDB for ClickHouse

The MIT license + Python + FastAPI stack makes this a 1-day job. The crawler's job is "build a local mirror of the catalog" — for us, that's just "configure a ClickHouse connection string." Keep everything else: the FastAPI skeleton, the OpenAPI docs, the `/v1/sql` endpoint, the type=csv/json/feather response formats.

Sketch of the swap:

```python
# /Users/penelope/Documents/opentir/api/data_api/main.py
# Original code. Forked structure from owid/data-api; backed by ClickHouse.
import os
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from clickhouse_driver import Client

CH = Client(
    host=os.environ.get("OSINT_CH_HOST", "127.0.0.1"),
    port=int(os.environ.get("OSINT_CH_PORT", "9000")),
    user=os.environ.get("OSINT_CH_USER", "default"),
    password=os.environ.get("OSINT_CH_PASSWORD", ""),
    database=os.environ.get("OSINT_CH_DB", "osint"),
)

app = FastAPI(title="OpenTIR-Data API", version="0.1.0")

class SQLQuery(BaseModel):
    sql: str
    type: str = "json"   # "json" | "csv" | "tsv"

@app.get("/health")
def health():
    return {"status": "ok", "clickhouse": CH.execute("SELECT version()")[0][0]}

@app.get("/v1/dataset/data/{dataset_id}.csv")
def dataset_csv(dataset_id: str):
    sql = f"SELECT * FROM osint.datasets WHERE dataset_id = %(d)s ORDER BY first_seen_at"
    rows = CH.execute(sql, {"d": dataset_id})
    if not rows:
        raise HTTPException(404, "dataset not found")
    cols = [d[0] for d in CH.execute("SELECT name FROM system.columns WHERE table = 'datasets'")]
    csv = ",".join(cols) + "\n"
    csv += "\n".join(",".join(str(v) for v in r) for r in rows)
    return PlainTextResponse(csv, media_type="text/csv")

@app.post("/v1/sql")
def sql_query(q: SQLQuery):
    # Read-only enforcement: only allow SELECT, SHOW, DESCRIBE, EXPLAIN
    if not q.sql.strip().lower().startswith(("select", "show", "describe", "explain", "with")):
        raise HTTPException(400, "only read-only queries allowed")
    try:
        rows = CH.execute(q.sql)
    except Exception as e:
        raise HTTPException(400, f"query failed: {e}")
    if not rows:
        return {"rows": [], "columns": []}
    cols = [d[0] for d in CH.execute("SELECT 1")]
    if q.type == "csv":
        out = ",".join(map(str, cols)) + "\n"
        out += "\n".join(",".join(str(v) for v in r) for r in rows)
        return PlainTextResponse(out, media_type="text/csv")
    return {"columns": cols, "rows": [list(r) for r in rows]}
```

The full `/v1/docs` OpenAPI UI is auto-generated by FastAPI. ~80 lines of original code, 1-day build.

### Way 2: query the OWID data-api directly for reference data

If the user wants to use OWID's own instance of the data-api (which doesn't exist publicly yet) — for now, fall back to the CSV download path we covered in [[connectors/ourworldindata]]. The data-api repo is reference-only at this point.

### Way 3: port the `/v1/sql` endpoint to your own OpenTIR-Data MCP server

This is the missing piece. The MCP server we sketched in [[connectors/owid-browser-semantic-search]] needs a `run_sql` tool — and the OWID data-api gives us the **exact same endpoint signature** we should use. Copy `POST /v1/sql` from this repo into our MCP server, point it at ClickHouse, expose to AI agents.

## Quick call — verify (no public deployment, so we verify the repo)

```bash
# License (MIT)
curl -sL "https://raw.githubusercontent.com/owid/data-api/main/LICENSE" | head -3

# README
curl -sL "https://raw.githubusercontent.com/owid/data-api/main/README.md" | head -10

# Run locally (requires poetry + Python 3.10)
git clone https://github.com/owid/data-api
cd data-api
cp .env.example .env
make testdb
make run
# Now open http://127.0.0.1:8000/v1/docs
```

Expected: MIT license header, README mentions FastAPI + DuckDB + Hypercorn, `make run` starts a local server on port 8000 with the OpenAPI UI.

## Notes

- **The data-api is the single most useful OWID repo to fork** for our use case, because it's the only one that has the actual API surface we want to build. The license is MIT, the code is small (~860 KB), the patterns are sound (FastAPI + DuckDB + crawler).
- **DuckDB is a great choice for the prototype** but doesn't scale beyond ~100 GB of data per file. For us, ClickHouse is the right answer — 4 TB+ on the data, hundreds of millions of rows, concurrent reads.
- **The `/v1/sql` endpoint is the killer feature.** With read-only enforcement (only `SELECT`, `SHOW`, `DESCRIBE`, `EXPLAIN`, `WITH`), it's safe to expose publicly. This is the same pattern as `pgx`/`postgrest` for Postgres, but for a data warehouse.
- **The crawler is replaceable.** In the OWID data-api, the crawler builds a DuckDB from S3 parquet. For us, the "crawler" is our existing `ingest/` pipeline that writes to ClickHouse. Same end result; no extra component.
- **The 3-year staleness is a signal, not a blocker.** The repo is the reference implementation. The patterns (FastAPI, DuckDB, /v1/sql, crawl-then-serve) are timeless. For our 2026 build, we use modern equivalents: ClickHouse instead of DuckDB, Pydantic v2, FastAPI 0.110+.
- **For the world dashboard, this is a backend service.** The Next.js/SvelteKit frontend calls our `/v1/sql` endpoint, not ClickHouse directly. This is the right separation: dashboard = stateless presentation; data-api = stateless query service; ClickHouse = stateful warehouse.
- **The `data_api/` directory** (per the repo layout) is where the FastAPI routers live. `crawler/` is the S3→DuckDB loader. `tests/` has a `test_v1.py` that doubles as a working OpenAPI example. `demo/` has a `notebook.ipynb` that shows end-to-end usage.
- **This is the missing piece for our MCP server.** The MCP server we discussed needs a `run_sql` tool that points at our ClickHouse. The OWID data-api gives us the exact endpoint signature. Same name (`/v1/sql`), same response shape (`{columns, rows}` or CSV), same read-only enforcement. **Build the MCP server, then put a `/v1/sql` endpoint behind it, and the AI agent pattern is complete.**

## License: MIT (confirmed)

```text
MIT License

Copyright (c) 2021-2022 Our World in Data

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, ...
```

This is the second MIT-licensed OWID repo we've found (along with `owid/tech-radar`). It is the **single best fork target** for our world dashboard backend.

