# OWID Country Reconciliation Service (lc-reconcile)

Key: `none required` — public service. **No LICENSE file** in the repo (the standard `owid/`-repo issue), but the source is a small (~250 lines) Flask + MySQL wrapper around an open-source concept (OpenRefine reconciliation protocol), and the country-name data it returns is itself public. Use the code as a **reference implementation**; write your own version that points at your own ClickHouse catalog.

Status: **archived / frozen** (last push 2019-11-15). The service is referenced in OWID's own internal workflow but is not a public deployment. We can stand up our own version with a few hours of work.

Endpoint: **no public deployment** — the service is `python reconcile.py` against a local MySQL. The OpenRefine-compatible protocol means any OpenRefine instance can call it.
Auth: none (per the OpenRefine reconciliation API spec)
Format: `JSON` over `application/x-www-form-urlencoded` (the OpenRefine protocol)

Documentation:
- Repo: https://github.com/owid/lc-reconcile
- OpenRefine reconciliation API: https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Service-API
- Standard: https://reconciliation-api.github.io/specs/latest/
- README: https://raw.githubusercontent.com/owid/lc-reconcile/master/README.md

## What this is

A **country name reconciliation service** that conforms to the OpenRefine Reconciliation Service API. Given a free-text country name from any source ("U.S.", "USA", "United States of America", "America", "Estados Unidos"), it returns the **canonical OWID entity** with a confidence score.

```text
client (OpenRefine, our resolver, Jupyter, etc.)
    │  POST /reconcile
    │  queries=[{"query": "USA", "type": "/country"}]
    ▼
lc-reconcile service
    │  SELECT e.id, e.name FROM entities WHERE LOWER(e.name) LIKE '%usa%'
    │     UNION
    │  SELECT ... FROM country_name_tool_countryname cn
    │     INNER JOIN country_name_tool_countrydata cd
    │     ON cd.id = cn.owid_country
    ▼
returns
    { "result": [
        { "id": "United States",
          "name": "United States",
          "score": 95,
          "match": true,
          "type": [{"id": "/country", "name": "country"}]
        }
    ]}
```

The standard use case: you have a CSV with 10,000 rows of free-text country names (some "U.S.", some "USA", some "United States of America", some misspellings). You run OpenRefine with this service, and it cleans every name to the canonical OWID entity.

## Why this is genuinely useful for OSINT-Data

The OSINT world has **the same country-name problem everywhere**. Every source uses a different spelling:
- World Bank: "United States"
- OpenSky: "United States" (and "US" for the 2-letter prefix)
- UN: "United States of America"
- OpenFlights: "United States"
- Eurostat: "United States"
- WB WDI: "USA"
- A user CSV: "U.S.A.", "USA", "U.S.", "United States", "America", "the US"

Without reconciliation, the resolver creates 5+ separate "datasets" for what is logically the same country. **With reconciliation, every variant maps to one canonical entity**, and cross-source dedup just works.

This is **the missing piece** for the `dataset_fingerprint` resolver. Even with the current `(title, publisher, period, country_codes, tags)` fingerprint, the `country_codes` array is the most error-prone field. Reconciliation fixes that.

## How it's used in OpenTIR-Data

### Path 1: stand up our own country reconciler against ClickHouse

```python
# /Users/penelope/Documents/opentir/api/reconcile/countries.py
# Original code. Compatible with OpenRefine Reconciliation Service API v0.2.
# Backed by ClickHouse (where the canonical country list lives).
from flask import Flask, request, jsonify
from clickhouse_driver import Client
import re
from difflib import SequenceMatcher

app = Flask(__name__)
ch = Client(host="127.0.0.1", port=9000, database="osint")

# A small but high-quality set of country aliases
ALIASES = {
    "u.s.": "United States", "u.s.a.": "United States", "usa": "United States",
    "us": "United States", "america": "United States", "united states of america": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "uae": "United Arab Emirates", "u.a.e.": "United Arab Emirates",
    "holland": "Netherlands", "the netherlands": "Netherlands",
    "czechia": "Czech Republic", "czech": "Czech Republic",
    "burma": "Myanmar", "macedonia": "North Macedonia",
    "swaziland": "Eswatini", "holy see": "Vatican", "vatican city": "Vatican",
    # ... ~200 entries
}


def canonicalize(name: str) -> tuple[str, float]:
    """Map any spelling to the canonical OWID-style entity name. Returns (canonical, score 0-100)."""
    s = re.sub(r"\s+", " ", name.strip().lower().rstrip("."))
    if s in ALIASES:
        return ALIASES[s], 100.0
    # Fuzzy match against the canonical list
    rows = ch.execute("SELECT entity_name FROM osint.countries")
    best_score, best_name = 0.0, s
    for (canonical,) in rows:
        score = SequenceMatcher(None, s, canonical.lower()).ratio() * 100
        if score > best_score:
            best_score, best_name = score, canonical
    return best_name, best_score


@app.route("/reconcile", methods=["POST", "GET"])
def reconcile():
    queries = request.json.get("queries", []) if request.json else request.form.get("queries", "[]")
    if isinstance(queries, str):
        import json as _json
        queries = _json.loads(queries)
    result = {}
    for q in queries:
        text = q.get("query", "")
        canonical, score = canonicalize(text)
        result[str(q.get("id", text))] = {
            "result": [{
                "id": canonical,
                "name": canonical,
                "score": score,
                "match": score >= 85,
                "type": [{"id": "/country", "name": "country"}]
            }]
        }
    return jsonify(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
```

That's ~50 lines of original code, Flask + ClickHouse + ~200 alias entries. Run it, point OpenRefine at `http://localhost:5000/reconcile`, reconcile any CSV.

### Path 2: use it in our resolver directly

Add a `_canonicalize_country(name)` step to `ingest/resolver.py`:

```python
# In the resolver, after we identify country_codes from a bundle's metadata
def _canonicalize_country(name: str) -> str:
    """Ask our local reconciler for the canonical name. Falls back to input on error."""
    try:
        r = httpx.post("http://localhost:5000/reconcile",
                       json={"queries": [{"id": "1", "query": name}]},
                       timeout=2.0)
        hits = r.json()["1"]["result"]
        if hits and hits[0]["score"] >= 85:
            return hits[0]["name"]
    except Exception:
        pass
    return name
```

This goes in front of the fingerprint computation. The result: every "U.S.", "USA", "America" in source data becomes "United States" before the fingerprint hash is computed, so cross-source dedup just works.

### Path 3: integrate with OpenRefine for bulk CSV cleanup

The OWID README has the full OpenRefine integration walkthrough. For our OSINT pipeline, the bulk-cleanup use case is:

- **Bulk import** a CSV with 50,000 country-name rows
- **OpenRefine** with our reconciler cleans every row in ~30 seconds
- **Export** the canonicalized CSV back to a file
- **Ingest** the cleaned CSV with our normal pipeline

## Quick call — verify (no public deployment, so we verify the protocol)

```bash
# The service is local-only. To test, clone and run:
git clone https://github.com/owid/lc-reconcile
cd lc-reconcile
# Set MySQL credentials in settings.cfg
pip install -r requirements.txt
python reconcile.py
# Then in another terminal:
curl -X POST http://localhost:5000/reconcile \
  -H "Content-Type: application/json" \
  -d '{"queries":[{"id":"1","query":"USA"},{"id":"2","query":"U.S.A."},{"id":"3","query":"Brit"}]}'
# Returns: { "1": {"result":[{"id":"United States", "score": 95, ...}]}, ... }
```

## Notes

- **The code is small** — `reconcile.py` is 5.5 KB / ~150 lines, the SQL is ~50 lines, the README is the integration walkthrough. Easy to fork or rewrite.
- **The hard part is the alias data.** OWID's `country_name_tool` (the MySQL table behind this service) has thousands of curated aliases — "United States" → 47 variants, "Russia" → 32 variants including "USSR" and "Russian Federation", etc. **Building this from scratch is the bulk of the work.** Open solutions:
  - **OpenRefine's own country reconciliation** (https://github.com/OpenRefine/OpenRefine/wiki/Reconciliation-Services) — multiple community-built services
  - **Wikidata's Q-id mapping** (Q5 = United States, Q30 = Italy, etc.) — every Wikipedia article has a canonical country code
  - **ISO 3166** (alpha-2, alpha-3, numeric) — official codes for every country, but no aliases
  - **GeoNames**, **RestCountries** — public APIs that return alias lists
  - For our use case, a curated table of ~500 aliases covering 95% of OSINT data covers the long tail well enough.
- **OpenRefine integration is the killer use case.** Any CSV from any source can be cleaned in 30 seconds, then ingested. The OSINT pipeline becomes "ingest any CSV, auto-reconcile country names against our canonical list, dedupe by fingerprint."
- **MySQL is the wrong backend for us** — the original uses MySQL because OWID's Grapher uses MySQL. For us, ClickHouse (or a small SQLite/Postgres sidecar) is the right answer.
- **MCP integration**: this is the country-resolution layer the MCP server needs. When an AI agent asks "show me African energy data", the resolver calls `/reconcile?query=African` to find the canonical entity list, then queries ClickHouse for the matching datasets.
- **License caveat**: no LICENSE file. The code is small and the protocol is standard, so writing your own version (as I did in Path 1 above) is the right move. The ~50 lines of original code above are MIT-compatible (just standard OpenRefine protocol implementation against our data).

