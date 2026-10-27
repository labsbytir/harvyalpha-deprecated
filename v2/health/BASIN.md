# Harvy data archive: Basin

Harvy can stream every local JSON artifact from a scrape job into Basin Pipelines, with a Basin Catalog Iceberg sink so the records can be queried using Basin SQL. Original job files remain in `data/`; Basin is an additional archive/analytics copy.

## 1. Create the Basin table

Requires a Cloudflare account with Workers Paid and R2 enabled. From this project, run `npx wrangler basin pipelines setup --name harvy_scraped_data` and select:

1. HTTP endpoint enabled; require authentication if you will expose the stream URL outside the server.
2. Load `health/schema.json` as the structured stream schema.
3. Basin Catalog / Iceberg sink: active warehouse bucket `harvy-ql`, namespace `default`, table `graph`.
4. Live pipeline: `cbee9eb32e4a4617a81fda117c750c10` (`harvyql_pipeline`), executing: `INSERT INTO harvyql_sink SELECT * FROM harvyql_stream;`.
5. Active stream endpoint: `https://e1e54007204f43768769ee613369c85f.ingest.cloudflare.com` (`harvyql_stream`).

## Storage Separation: R2 Direct vs. Basin Catalog

R2 and Basin serve distinct storage layers and use separate buckets:

- **Raw Scrapes (`harvy-raw`)**: Ephemeral object storage for crawler payloads, raw HTTP responses, and HTML. Lifecycle rule `expire-raw-crawls-60d` automatically expires objects after 60 days.
- **Artifacts & Releases (`harvy-artifacts`)**: Permanent object storage for normalized JSON entities, dossier snapshots, and release manifests. Key-value access (`get`/`put`). No expiration.
- **Basin Warehouse (`harvy-ql`)**: Managed exclusively by Basin Pipelines and Basin Catalog (`9061d93166998cf39e011a52b369b812_harvy-ql`). Stores Apache Iceberg metadata snapshots and columnar Parquet files queryable via Basin SQL.
- **Rule**: Never apply arbitrary S3 lifecycle/TTL rules to the Basin warehouse bucket (`harvy-ql`). Iceberg tables manage their own snapshot compaction (1h interval, 128MB compaction enabled); manual object deletion corrupts the Iceberg table metadata.

The R2 Account API token is entered only into the Basin setup flow; do not put it in `wrangler.jsonc` or the browser. Basin Pipelines has a 5 MB maximum ingestion request. `v2/health/basin_storage.py` batches below 5 MB and splits oversized JSON artifacts into ordered text chunks. Cloudflare documents 50 GB/month of included SQL transforms and Iceberg sink delivery on Workers Paid; R2 storage/catalog charges also apply. Initial records may take 3–7 minutes to become queryable.

## 2. Configure Harvy

Set these server-side for Gunicorn (never in frontend JavaScript):

```sh
BASIN_INGEST_URL="https://e1e54007204f43768769ee613369c85f.ingest.cloudflare.com"
BASIN_INGEST_TOKEN="<stream-token-if-authentication-is-enabled>"
WEBSHARE_PROXY_URL="<existing Webshare proxy URL>"
```

`BASIN_INGEST_TOKEN` may be omitted only when the stream endpoint is intentionally unauthenticated. Harvy writes each completed or partial job's JSON artifacts; if Basin is not configured or a write fails, the local job files are retained and the job status reports the archive state.

## 3. Backfill and query

After configuring the stream, backfill existing JSON artifacts once:

```sh
.venv/bin/python -m health.basin_backfill --root data
```

The backfill excludes the bundled WhatsMyName reference dataset. Event IDs are deterministic per file and chunk; if a backfill is repeated, deduplicate by `event_id` in queries. For very large files, concatenate `payload.raw_json_chunk` ordered by `chunk_index` to reconstruct the source JSON text.

Enable the catalog and set `WRANGLER_BASIN_SQL_AUTH_TOKEN` to the R2 account token in the shell that runs Wrangler, then query:

```sh
npx wrangler basin catalog get <bucket-name>
npx wrangler basin sql query "<warehouse-name>" \
  "SELECT source, kind, COUNT(*) AS artifacts FROM default.harvy_scraped_data GROUP BY source, kind ORDER BY artifacts DESC"
npx wrangler basin sql query "<warehouse-name>" \
  "SELECT artifact_path, collected_at, payload FROM default.harvy_scraped_data WHERE source = 'www.facebook.com' LIMIT 10"
```

`source`, `kind`, `artifact_path`, timestamps, chunk information, and payloads are stored in the table. Treat the warehouse as sensitive: scraped artifacts can contain personal information. Restrict Cloudflare/R2 access and apply the retention/deletion rules required for your use case.
