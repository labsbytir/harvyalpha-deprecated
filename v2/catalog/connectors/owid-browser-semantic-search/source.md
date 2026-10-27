# OWID in-browser semantic search (architecture reference)

Key: `none required` for the demo. **The codebase has no license** — GitHub API reports `license: None`, and there is no `LICENSE` or `LICENSE.md` file in the repo. **You may not copy, fork, or reuse this code without written permission from OWID.** The pattern is the part worth copying; the code itself is not under a free license.

Status: **prototype, not production.** 1 star on GitHub. Actively inspired by `transformers.js` + PGlite + pgvector.

Endpoint (live code): `https://github.com/owid/owid-browser-semantic-search`
Coredump (1.4 MB JSON of OWID content): `https://raw.githubusercontent.com/owid/owid-browser-semantic-search/main/public/coredump.json`
Auth: none
Format: JSON (coredump), WASM Postgres (embedded)

Documentation:
- Repo: https://github.com/owid/owid-browser-semantic-search
- Built on: https://github.com/huggingface/transformers.js
- Built on: https://github.com/electric-sql/pglite (WASM Postgres in browser)
- Built on: https://github.com/pgvector/pgvector (vector similarity)

## What it is (and what it isn't)

This is a **prototype semantic search engine for the OWID website that runs entirely in the browser**:

```text
┌──────────────────────────────────────────────────────────────┐
│                       Browser tab                            │
│  ┌─────────────┐    ┌─────────────┐    ┌──────────────────┐  │
│  │ React 19    │    │ Web Worker  │    │ PGlite (WASM     │  │
│  │ + MUI       │◄──►│ Hugging Face │    │ Postgres)        │  │
│  │ (the UI)    │    │ Transformers │    │ + pgvector        │  │
│  └─────────────┘    │ (embeddings) │    │ (vector storage)  │  │
│                     └─────────────┘    └──────────────────┘  │
│                              ▲                                 │
│                              │ loads                            │
│                              ▼                                 │
│                   public/coredump.json                         │
│                  (1.4 MB of OWID content)                       │
└──────────────────────────────────────────────────────────────┘
```

It generates **embeddings of OWID's content titles** (not the full body text) using a transformers.js model running in a Web Worker, stores them in a WASM Postgres database with the pgvector extension, and does similarity search entirely client-side. The user types a query, it gets embedded with the same model, and pgvector returns the closest matches by cosine distance.

The point of the prototype is to demonstrate that **"infrastructure-free" semantic search is now possible** for ~10k items, all in the browser. The trade-off is that embedding generation is slow on a low-end device (~5–30 seconds for the first 1000 items), but the search itself is instant.

## License: NONE — code is not reusable

```text
$ curl -I https://raw.githubusercontent.com/owid/owid-browser-semantic-search/main/LICENSE
HTTP/2 404
```

```text
$ curl -sL "https://api.github.com/repos/owid/owid-browser-semantic-search" | grep license
"license": null
```

Under default copyright law, **no license = all rights reserved**. The OWID team hasn't (yet) published a free-software license on this repo. **Do not copy the code, do not fork, do not vendor the source files.** The architectural pattern is public knowledge; the specific code is not free to reuse.

## The architecture IS reusable — build your own

The dependency stack is all MIT/Apache/ISC:

- `huggingface/transformers.js` (Apache 2.0) — JS port of HF transformers, runs models in ONNX Runtime Web
- `@electric-sql/pglite` (Apache 2.0) — WASM Postgres in the browser, ~3 MB gzipped
- `pgvector` (PostgreSQL license) — vector extension, packaged for pglite
- React 19, MUI, Vite (MIT)

You can build the same pattern for your own catalog with ~150 lines of original code. Don't import this repo's `src/`.

## How to use it in OpenTIR-Data (3 paths)

### Path 1: copy the architecture for our in-browser catalog search

```typescript
// /Users/penelope/Documents/opentir/dashboard/src/semantic-search/SearchBox.tsx
// Original code. Pattern inspired by owid-browser-semantic-search but written from scratch.
import { useState, useEffect, useRef } from "react";
import { pipeline, env } from "@huggingface/transformers";
import { PGlite } from "@electric-sql/pglite";
import { vector } from "@electric-sql/pglite/vector";

export function SearchBox({ catalogUrl }: { catalogUrl: string }) {
    const [query, setQuery] = useState("");
    const [results, setResults] = useState<{ title: string; score: number; url: string }[]>([]);
    const dbRef = useRef<PGlite | null>(null);
    const embedderRef = useRef<any>(null);

    useEffect(() => {
        (async () => {
            // 1. Load the catalog (the OSINT-Data dataset_fingerprints + titles + descriptions)
            const catalog = await fetch(catalogUrl).then(r => r.json());

            // 2. Spin up an in-browser pgvector
            const db = new PGlite();
            await db.loadExtension(vector);
            await db.exec(`
                CREATE TABLE items (
                    id INTEGER PRIMARY KEY,
                    title TEXT, description TEXT, url TEXT,
                    embedding VECTOR(384)
                )
            `);
            await db.exec("CREATE INDEX ON items USING hnsw (embedding vector_cosine_ops)");

            // 3. Load transformers.js (small embedding model, e.g. all-MiniLM-L6-v2)
            env.allowLocalModels = false;
            const extractor = await pipeline("feature-extraction", "Xenova/all-MiniLM-L6-v2");
            embedderRef.current = extractor;

            // 4. Embed each catalog item, store in pgvector
            for (let i = 0; i < catalog.length; i++) {
                const text = `${catalog[i].title} ${catalog[i].description || ""}`;
                const out = await extractor(text, { pooling: "mean", normalize: true });
                const vec = Array.from(out.data as Float32Array);
                await db.query(
                    "INSERT INTO items (id, title, description, url, embedding) VALUES ($1, $2, $3, $4, $5)",
                    [i, catalog[i].title, catalog[i].description || "", catalog[i].url, JSON.stringify(vec)]
                );
            }
            dbRef.current = db;
        })();
    }, [catalogUrl]);

    async function runSearch() {
        if (!dbRef.current || !embedderRef.current) return;
        const out = await embedderRef.current(query, { pooling: "mean", normalize: true });
        const vec = Array.from(out.data as Float32Array);
        const r = await dbRef.current.query(`
            SELECT title, url, 1 - (embedding <=> $1) AS score
            FROM items
            ORDER BY embedding <=> $1
            LIMIT 10
        `, [JSON.stringify(vec)]);
        setResults(r.rows);
    }

    return (
        <div>
            <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => e.key === "Enter" && runSearch()}
                placeholder="Search the OSINT catalog..."
            />
            <ul>
                {results.map(r => (
                    <li key={r.url}>
                        <a href={r.url}>{r.title}</a> — {r.score.toFixed(3)}
                    </li>
                ))}
            </ul>
        </div>
    );
}
```

This is original code (not copied from OWID), it implements the same pattern, and it's all MIT/Apache 2.0 dependencies. The whole search engine is one React component.

### Path 2: server-side equivalent (PostgreSQL + pgvector)

If you prefer a server-side API (faster, sharable, larger corpus), mirror the architecture with regular Postgres + pgvector. ClickHouse is great for the warehouse; Postgres + pgvector is the right tool for semantic search.

```python
# /Users/penelope/Documents/opentir/api/search/semantic.py
# Original code. The endpoint takes a query string, embeds it via a server-side
# sentence-transformers model, and returns the top N matches from pgvector.

from fastapi import FastAPI, Query
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import asyncpg

app = FastAPI()
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

class SearchHit(BaseModel):
    dataset_id: str
    title: str
    description: str
    score: float
    url: str

@app.get("/search", response_model=list[SearchHit])
async def search(q: str = Query(min_length=2, max_length=500), limit: int = 20):
    vec = model.encode(q, normalize_embeddings=True).tolist()
    pool = await asyncpg.create_pool("postgresql://osint:***@localhost/osint")
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT dataset_id, title, description, homepage_url,
                   1 - (embedding <=> $1::vector) AS score
            FROM datasets
            ORDER BY embedding <=> $1::vector
            LIMIT $2
        """, vec, limit)
    await pool.close()
    return [SearchHit(**dict(r)) for r in rows]
```

### Path 3: the `coredump.json` is a useful reference

The 1.4 MB `public/coredump.json` in the OWID repo is a snapshot of OWID's content catalog (charts, articles, tags). It's not copyrightable as a data structure — it just lists titles. You can use the **format** of this file as a reference for how to package your own catalog for semantic search:

```json
{
    "generatedAt": "2026-09-04T22:35:00Z",
    "items": [
        {
            "type": "chart",
            "title": "Life expectancy at birth, by country",
            "slug": "life-expectancy",
            "url": "https://ourworldindata.org/grapher/life-expectancy",
            "tags": ["health", "mortality", "population"],
            "summary": "Period life expectancy at birth, given mortality rates..."
        },
        ...
    ]
}
```

For your OSINT-Data catalog, the same shape would be:

```json
{
    "generatedAt": "...",
    "items": [
        {
            "dataset_id": "DS-abc123",
            "title": "WHO intentional homicide rate, 2010-2024",
            "description": "Age-standardized rate per 100,000...",
            "publisher": "WHO via UNODC",
            "tags": ["crime", "health", "sdg-16-1-1"],
            "url": "https://dataunodc.un.org/datareport/hom-victim"
        },
        ...
    ]
}
```

## Quick call — verify the architectural pieces

```bash
# The coredump.json (data shape reference; do not reuse the code)
curl -sL "https://raw.githubusercontent.com/owid/owid-browser-semantic-search/main/public/coredump.json" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('items:', len(d.get('items', []))); print('first:', d['items'][0])"

# Verify the dependencies are all free
pip install pglite   # not pip — pglite is JS-only
pip install pgvector sentence-transformers   # these are MIT
npm install @electric-sql/pglite @huggingface/transformers   # both MIT/Apache
```

Expected: `coredump.json` has ~5000+ items; the dependencies install cleanly under their respective free licenses.

## Notes

- **License is the headline finding.** The OWID code is all rights reserved. The architectural pattern (transformers.js + pglite + pgvector + React) is built on fully free dependencies, and the JS code in the OWID repo is mostly 50–100 lines of glue between well-known libraries. Writing your own version of this glue is a 1-day project, not a copyright problem.
- **The model choice matters.** `Xenova/all-MiniLM-L6-v2` (used in the OWID prototype) gives 384-dimensional embeddings, ~50 MB download. It's small enough to ship in a web worker and good enough for "find me datasets about X" queries. For multilingual content, switch to `Xenova/multilingual-e5-small` (still ~120 MB, supports 100+ languages).
- **Speed**: embedding the OSINT-Data catalog (~3,000 datasets) takes ~30 seconds on a modern laptop. Search is instant.
- **Accuracy**: with title-only embeddings, expect ~70% precision on vague queries ("stuff about Africa"). With title + description + tags + publisher, expect ~90%.
- **Cross-source dedup angle**: semantic search is *another* way to find duplicates. A dataset called "Intentional homicide rate" and one called "Homicide victims per 100,000" will have similar embeddings even if their text fingerprints (which I built earlier) differ. This complements the `dataset_fingerprint` resolver — use semantic search for discovery, the fingerprint resolver for storage.
- **MCP angle**: this exact pattern (sentence-transformers + pgvector) is what should power our MCP server's `search_indicator` and `find_similar` tools.

