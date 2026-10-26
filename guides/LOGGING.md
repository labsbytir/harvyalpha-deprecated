# Harvy Logging Architecture: Cloudflare Logs & R2 `harvy-logs`

Unified logging system for Harvy, covering both the Cloudflare edge ecosystem and external servers, scrapers, and background daemons, backed by Cloudflare R2 bucket `harvy-logs`.

Reference: [Cloudflare Logs Documentation](https://developers.cloudflare.com/logs/)

---

## 1. Architecture Overview

```
                                      ┌─────────────────────────────────────────┐
┌───────────────────────────────┐     │                                         │
│ Cloudflare Edge / Workers     │────▶│ Cloudflare Logpush Job                  │───┐
│ (HTTP Requests, Trace Events) │     │ (Account & Zone Level)                  │   │
└───────────────────────────────┘     └─────────────────────────────────────────┘   │
                                                                                    │
┌───────────────────────────────┐     ┌─────────────────────────────────────────┐   ▼
│ External Servers & Tools      │────▶│ Harvy Worker API: POST /api/logs/ingest │──▶ R2: harvy-logs
│ (Python Scrapers, VPS, Daemons│     │ (Validates key, batches, partitions)    │   ▲
└───────────────────────────────┘     └─────────────────────────────────────────┘   │
                                                                                    │
┌───────────────────────────────┐                                                   │
│ Direct S3 / Vector / Fluent   │───────────────────────────────────────────────────┘
│ (Optional high-throughput)    │
└───────────────────────────────┘
```

### Storage Hierarchy (`harvy-logs`)

```
harvy-logs/
├── cloudflare/
│   ├── workers/{DATE}/               # Cloudflare Logpush: Workers trace events & tail logs
│   │   └── <job_id>_<timestamp>_<hash>.log.gz
│   └── http/{DATE}/                  # Cloudflare Logpush: HTTP request logs
│       └── <job_id>_<timestamp>_<hash>.log.gz
└── external/
    └── {service}/{YYYY}/{MM}/{DD}/{HH}/
        ├── {timestamp}_{uuid}.json          # Single log event
        └── {timestamp}_batch_{uuid}.ndjson  # Batch log events
```

---

## 2. Cloudflare Ecosystem Setup (Logpush)

Cloudflare Logpush automatically pushes structured logs from the edge to R2 without consuming Worker CPU.

### Step 1: Create the R2 Bucket

```bash
npx wrangler r2 bucket create harvy-logs
```

Ensure the bucket binding is declared in `wrangler.jsonc`:

```jsonc
"r2_buckets": [
  {
    "binding": "HARVY_LOGS",
    "bucket_name": "harvy-logs"
  }
]
```

### Step 2: Configure Logpush Jobs

Use the automated script:

```bash
export CLOUDFLARE_API_TOKEN="<api-token-with-logs-edit-permissions>"
export CLOUDFLARE_ACCOUNT_ID="<account-id>"
export CLOUDFLARE_ZONE_ID="<zone-id>"
export R2_ACCESS_KEY_ID="<r2-access-key>"
export R2_SECRET_ACCESS_KEY="<r2-secret-key>"

python3 scripts/setup_cloudflare_logs.py
```

Or configure manually via `curl`:

#### Workers Trace Events (Account Level)
Captures all Worker invocations, tail events, errors, subrequests, wall time, and uncaught exceptions across all Harvy Workers (`harvy`, `harvy-auth`, `harvy-workflows`):

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/accounts/$CLOUDFLARE_ACCOUNT_ID/logpush/jobs" \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "harvy-workers-trace-logs",
       "dataset": "workers_trace_events",
       "destination_conf": "r2://harvy-logs/cloudflare/workers/{DATE}?account-id='$CLOUDFLARE_ACCOUNT_ID'&access-key-id='$R2_ACCESS_KEY_ID'&secret-access-key='$R2_SECRET_ACCESS_KEY'",
       "enabled": true
     }'
```

#### HTTP Requests (Zone Level)
Captures edge HTTP traffic to `harvybot.com`:

```bash
curl -s -X POST "https://api.cloudflare.com/client/v4/zones/$CLOUDFLARE_ZONE_ID/logpush/jobs" \
     -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "name": "harvy-zone-http-logs",
       "dataset": "http_requests",
       "destination_conf": "r2://harvy-logs/cloudflare/http/{DATE}?account-id='$CLOUDFLARE_ACCOUNT_ID'&access-key-id='$R2_ACCESS_KEY_ID'&secret-access-key='$R2_SECRET_ACCESS_KEY'",
       "enabled": true
     }'
```

---

## 3. External Servers and Tools Logging

External tools (e.g. Telethon scrapers, VPS daemons, background graph jobs) push logs using either the Worker HTTP ingestion API or the Python logging client.

### Ingest Endpoint: `POST /api/logs/ingest`

- **URL**: `https://harvybot.com/api/logs/ingest`
- **Method**: `POST`
- **Auth**: Header `x-api-key: <HARVY_LOGS_INGEST_KEY>` or `Authorization: Bearer <API_KEY>`

#### Single Record Payload
```json
{
  "service": "telegram_scraper",
  "level": "INFO",
  "message": "Fetched 250 messages from channel",
  "timestamp": "2026-10-25T14:30:00Z",
  "environment": "production",
  "metadata": {
    "channel_id": 1234567,
    "batch_size": 250
  }
}
```

#### Batch Payload
```json
{
  "events": [
    {
      "service": "social_crawler",
      "level": "INFO",
      "message": "Scraped profile target_1",
      "metadata": { "platform": "x" }
    },
    {
      "service": "social_crawler",
      "level": "WARN",
      "message": "Rate limit encounter on proxy",
      "metadata": { "proxy": "9.249.21.58" }
    }
  ]
}
```

#### Response
```json
{
  "status": "ok",
  "ingested": 2,
  "keys": [
    "external/social_crawler/2026/10/25/14/1729866600000_batch_a1b2c3d4.ndjson"
  ]
}
```

---

## 4. Python Client Integration

The repository includes a production-ready client and standard `logging.Handler` in `health/harvy_logger.py`.

### Standard Python Logging Handler

```python
import logging
from health.harvy_logger import HarvyLogHandler

logger = logging.getLogger("harvy_scraper")
logger.setLevel(logging.INFO)

# Attach Harvy log handler
handler = HarvyLogHandler(
    service="telegram_scraper",
    ingest_url="https://harvybot.com/api/logs/ingest",
    api_key="<HARVY_LOGS_INGEST_KEY>",
    buffer_size=20,  # Flush after 20 logs or 5 seconds
)
logger.addHandler(handler)

logger.info("Scrape job started", extra={"metadata": {"target": "@sample"}})
```

### Standalone Logger

```python
from health.harvy_logger import HarvyLogger

logger = HarvyLogger(
    service="vps_monitor",
    ingest_url="https://harvybot.com/api/logs/ingest",
    api_key="<HARVY_LOGS_INGEST_KEY>",
)

logger.info("Service started successfully", metadata={"host": "vps-01"})
logger.error("Database connection timeout", metadata={"retry": 3})
```

---

## 5. Querying Logs in R2

### Via Wrangler CLI
```bash
# List log objects
npx wrangler r2 object list harvy-logs --prefix cloudflare/workers/
npx wrangler r2 object list harvy-logs --prefix external/

# Download and inspect
npx wrangler r2 object get harvy-logs/external/telegram_scraper/2026/10/25/14/sample.json --file -
```

### Via DuckDB (Local SQL over R2)
```sql
INSTALL httpfs;
LOAD httpfs;
SET s3_endpoint = '<account-id>.r2.cloudflarestorage.com';
SET s3_access_key_id = '<r2-access-key>';
SET s3_secret_access_key = '<r2-secret-key>';

SELECT service, level, message, timestamp
FROM read_ndjson_auto('s3://harvy-logs/external/*/*/*/*/*/*.ndjson')
WHERE level = 'ERROR'
ORDER BY timestamp DESC
LIMIT 50;
```
