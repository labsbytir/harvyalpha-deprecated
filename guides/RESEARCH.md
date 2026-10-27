# Legal and geospatial research sources

Open `http://127.0.0.1:8903/research/` (or `/research/` on the hosted app) for the research panel. After a job finishes, FlexSearch 0.8.212 builds a browser-memory index of that job's saved JSON artifacts, protected by the workspace and per-job tokens. It does not download or index every historical file at once; use Basin SQL for archive-wide search. FlexSearch is Apache-2.0; its license is in `static/FLEXSEARCH-LICENSE.txt`.

Requests are authorized with the Harvy workspace token; source credentials are read only from server environment variables.

## Configure server-side credentials

| Variable | Used for |
| --- | --- |
| `SPIDER_API_KEY` | Spider public-page collection |
| `WEBSHARE_PROXY_URL` | Proxy for Spider target requests and direct API calls |
| `JUDYRECORDS_API_KEY` | JudyRecords official API |
| `COURTLISTENER_API_TOKEN` | Optional CourtListener REST API token; the API also permits limited unauthenticated searches |
| `CASELAW_API_TOKEN` | Optional Case.law API token |
| `DOCKETALARM_USERNAME`, `DOCKETALARM_PASSWORD` | Docket Alarm API login |
| `MAPILLARY_ACCESS_TOKEN` | Mapillary Graph API |
| `BASIN_INGEST_URL`, `BASIN_INGEST_TOKEN` | Optional Basin archive; see [BASIN.md](../health/BASIN.md) |

Do not put API keys in templates, job arguments, or browser requests. Restart the server after changing its environment.

## Source behavior

- **CourtListener:** REST API search, capped at one page of ten results per job. It is rate-limited; configure a token for ongoing use.
- **Case.law:** attempts the documented REST endpoint. The endpoint returned HTML rather than JSON during implementation checks, so the report marks this source unavailable unless it returns JSON.
- **JudyRecords:** uses its documented `/search` API via Spider, with the API key sent in a server-side request header. The site's terms state its API is the permitted programmatic access path.
- **Docket Alarm:** API search only when credentials exist. The connector uses indexed search; it does not fetch live PACER data or download documents.
- **Arrests.org:** public search page via Spider + the configured Webshare proxy, using the supplied state and first/last name. It saves the raw response; any result must be independently checked against the court source.
- **CourtRecord.net:** link-out only. Its posted terms restrict copying and commercial reuse of its materials.
- **Google Scholar:** link-out only; no official public search API was verified.
- **Mapillary:** image-radius API query (50 m, up to 10 results). Creator identifiers are not requested.
- **Google Maps:** `python -m v1.scrape.google_maps <https://www.google.com/maps/place/...> --out <folder>` uses Spider's `/unlimited/scrape` endpoint and the shared proxy secret helper. It preserves the raw response and normalizes only exposed JSON-LD business/review data. It does not call Spider's metered `/fetch` Maps extractor; review coverage remains partial and explicitly marked incomplete.
- **Zoom Earth and OpenSfM:** links only. Zoom Earth has no public API documented; OpenSfM is a local photogrammetry toolkit, not a hosted API.

Search names can match different people; an arrest record is not proof of guilt. Court and legal data can be incomplete or stale. Restrict access to downloaded archives and Basin tables, and set appropriate retention before enabling persistent storage.
