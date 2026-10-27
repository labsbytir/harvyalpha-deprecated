# DBpedia

Key: `none required` — all DBpedia public endpoints are free. Auth is only needed for the SPARQL Update endpoint (write).

Endpoint (SPARQL): `https://dbpedia.org/sparql`
Endpoint (Lookup): `https://lookup.dbpedia.org/api/search`
Endpoint (REST data): `https://dbpedia.org/data/{Resource}.{format}`
Endpoint (Databus): `https://databus.dbpedia.org/`
Auth: none (read); `?default-graph-uri=`, `?format=`, `?query=` (SPARQL)
Format: `JSON`, `XML`, `TTL`, `NT`, `RDF/XML`

Documentation:
- Wiki: https://wiki.dbpedia.org/
- SPARQL endpoint: https://dbpedia.org/sparql (also https://dbpedia.org/sparql?format=json)
- Lookup API: https://lookup.dbpedia.org/
- Databus (datasets): https://databus.dbpedia.org/
- REST data: https://dbpedia.org/data/Climate.json
- Query examples: https://wiki.dbpedia.org/public-queries

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/dbpedia.py
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Accept": "application/json"},
        ) as client:
            # 1. SPARQL: pull 1000 cities with their populations
            sparql = """
PREFIX dbo: <http://dbpedia.org/ontology/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?city ?name ?pop WHERE {
  ?city a dbo:City ;
        rdfs:label ?name ;
        dbo:populationTotal ?pop .
  FILTER (lang(?name) = 'en')
  FILTER (?pop > 100000)
}
ORDER BY DESC(?pop)
LIMIT 1000
"""
            r = await client.get("https://dbpedia.org/sparql",
                                 params={"query": sparql, "format": "application/json"})
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="cities",
                source_id="cities_over_100k",
                source_url="https://dbpedia.org/sparql",
                bundle_url=f"/sparql?query=...",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="json",
                metadata={"sparql_query": sparql, "endpoint": "sparql"},
            )

            # 2. Lookup: search for a term and resolve to a DBpedia resource
            r = await client.get("https://lookup.dbpedia.org/api/search",
                                 params={"query": "climate", "format": "JSON", "maxResults": 10})
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="lookup",
                source_id="lookup-climate",
                source_url="https://lookup.dbpedia.org/",
                bundle_url="/api/search?query=climate",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="json",
                metadata={"query": "climate"},
            )

            # 3. REST data: pull all facts about a resource
            r = await client.get("https://dbpedia.org/data/Climate.json")
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="resources",
                source_id="Climate",
                source_url="https://dbpedia.org/page/Climate",
                bundle_url="/data/Climate.json",
                fetched_at=self.now(),
                payload=r.content,
                payload_format="json",
                metadata={"resource": "http://dbpedia.org/resource/Climate"},
            )
```

## Quick call — verify

```bash
# SPARQL JSON
curl -sL -A "OpenTIR-Data/0.1" "https://dbpedia.org/sparql?query=$(python3 -c "import urllib.parse; print(urllib.parse.quote('SELECT ?city ?pop WHERE { ?city a <http://dbpedia.org/ontology/City> . ?city <http://dbpedia.org/ontology/populationTotal> ?pop } LIMIT 1'))")&format=application/json" \
  | head -c 400

# Lookup
curl -sL "https://lookup.dbpedia.org/api/search?query=climate&format=JSON&maxResults=2" \
  | head -c 500

# REST data
curl -sL "https://dbpedia.org/data/Climate.json" | head -c 400
```

## Endpoints used (verified live 2026-09-04)

```text
GET /sparql?query=&format=json|xml|ttl|nt|...              # SPARQL endpoint (15+ formats)
GET /api/search?query=&format=JSON&maxResults=N          # Lookup (text → resource)
GET /data/{Resource}.{json|turtle|nt|xml|rdf}            # all facts for one resource
GET /page/{Resource}                                     # HTML view
GET /resource/{Resource}                                 # alias
GET /databus/{group}/{artifact}/{version}#download       # Databus dataset download
```

SPARQL query params: `query` (URL-encoded), `format` (MIME: `application/json`, `text/turtle`, `application/rdf+xml`, `text/plain` for NT, etc.), `default-graph-uri=` (which named graph to query), `timeout=ms`.

## Notes

- DBpedia is a **structured extraction of Wikipedia**. 9.5B+ triples. Anything in Wikipedia with an infobox is here.
- The SPARQL endpoint has a 60-second timeout, max 10,000 results per query. For large pulls, paginate with `LIMIT 10000 OFFSET N`.
- **Standard prefixes:**
  - `dbo:` — DBpedia ontology (most properties, e.g. `dbo:populationTotal`, `dbo:birthDate`)
  - `dbp:` — DBpedia property (raw infobox key/value, messier but more complete)
  - `dbr:` — DBpedia resource (`dbr:Paris` = `http://dbpedia.org/resource/Paris`)
  - `rdfs:`, `rdf:`, `owl:`, `xsd:`, `foaf:`, `geo:`, `dct:`
- The **Databus** (`databus.dbpedia.org`) is the newer publish/subscribe catalog. 100k+ datasets, versioned with semver. Worth exploring for the "structured versioned data" use case.
- **Lookup** is good for entity resolution: take any text, get back the most likely DBpedia URI.
- **Cross-source dedup**: Wikipedia/DBpedia entities overlap with Wikidata, OpenCorporates, and the World Bank's country indicators. The `dataset_fingerprint` resolver will link them via the resource URI.
- **Rate limit:** anonymous SPARQL is 15 requests / second / IP, but each query can take 30+ seconds. For high-volume, contact DBpedia for a dedicated endpoint.

