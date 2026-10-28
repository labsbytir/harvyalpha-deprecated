# OpenStates JSON Ingest Workflow

## Overview
This workflow ingests OpenStates JSON data files from the OpenStates.org bulk data repository and stores them in:
- **harvy-artifacts** R2 bucket (permanent storage)
- **harvyql_stream** Basin ingestion path (analytics)

## Input
- Array of URLs pointing to OpenStates JSON files (e.g., from Link Gopher)
- Example: `https://data.openstates.org/json/latest/AK_30_json_4yJM4COoSGZD18ITqW4lsG.zip`

## Failure Handling Features

### 1. **HTTP Status Code Validation**
- Checks if HTTP status is 200 OK
- Routes failed downloads to error handler
- Identifies: 404, 500, 429 (rate limited), etc.

### 2. **Content-Type Validation**
- Verifies response is JSON (`application/json`)
- Catches corrupted or wrong-format responses

### 3. **Retry Mechanism**
- **3 attempts** per file (configurable)
- Tracks attempt count in metadata
- Manual retry queue for failed downloads
- Retryable flag for external orchestration

### 4. **Error Classification**
- **download_failed**: HTTP errors, timeouts, network issues
- **r2_upload_failed**: R2 bucket permission issues, quota exceeded
- **basin_ingest_failed**: Basin API errors, authentication failures

### 5. **Error Aggregation**
- Collects all failures in final node
- Groups by error type for analysis
- Provides summary statistics

### 6. **Continue on Fail**
- All storage operations set `continueOnFail: true`
- One failure doesn't stop entire workflow
- Parallel processing continues for other files

### 7. **Debug Logging**
- Console logging for all operations
- Error details captured in output
- Status tracking for each file

### 8. **External Error Workflow**
- Configured to trigger external error handler
- Can integrate with notification systems

## Processing Flow

```
Prepare URLs → Download JSON → Check HTTP Status
    ↓ (200 OK)                    ↓ (Failed)
Check JSON Content → Extract Metadata → Route to Storage
    ↓                              ↓
[Success Path]            [Error Path]
    ↓                              ↓
Upload to R2 ←→ Success Tracking → Debug Logging
Send to Basin ←→ Handle Failures → Aggregate Failures
    ↓                              ↓
[Continue]               [Retry Queue]
```

## Error Output Structure

Each failure includes:
```json
{
  "status": "download_failed",
  "error": "Error message from HTTP client",
  "error_type": "download",
  "url": "original_url",
  "attempt": 1,
  "retryable": true,
  "timestamp": "ISO timestamp"
}
```

## Failure Aggregation Output

Final output includes:
- Total failures count
- Failures grouped by error type
- Original error details for each failure
- Total processed count

## Usage

### Basic Execution
1. Import the workflow into n8n
2. Configure credentials:
   - R2 API credentials for `harvy-artifacts` bucket
   - Basin HTTP authentication for `harvyql_stream`
3. Provide input with array of URLs
4. Execute workflow

### Monitoring Failures
- Check the "Aggregate Failures" node output
- Review console logs for detailed error messages
- Use error count to identify systemic issues

### Retry Failed Items
1. Export failed items from error aggregation
2. Update attempt count
3. Re-import into workflow or use manual retry queue

## Configuration Options

### Retry Settings
- **Max attempts**: 3 (hardcoded in workflow)
- **Retry delay**: Manual (external orchestration recommended)
- **Retry queue**: Available via "Manual Retry Queue" node

### Timeout Settings
- **Download timeout**: 30 seconds
- **Basin timeout**: 30 seconds
- **Retry interval**: Not automated (external scheduling)

## Best Practices

1. **Monitor error rates**: Track failures over time
2. **Set up alerts**: Use error aggregation output for notifications
3. **Rate limiting**: Implement delays between batches if hitting 429 errors
4. **Credential rotation**: Update credentials before they expire
5. **Storage quotas**: Monitor R2 bucket usage

## Example Error Scenarios

### Scenario 1: 404 Not Found
```
Status: download_failed
Error: "404 Not Found"
Error type: download
Retryable: false (file doesn't exist)
```

### Scenario 2: R2 Quota Exceeded
```
Status: r2_upload_failed
Error: "Quota exceeded"
Error type: r2_upload
Retryable: false (requires quota increase)
```

### Scenario 3: Temporary Network Issue
```
Status: download_failed
Error: "ETIMEDOUT"
Error type: download
Retryable: true (network issue)
```

## Notes
- Uses `HarvyPlatform/2.0` user-agent to avoid Cloudflare 1010 errors
- All operations are idempotent (safe to retry)
- Success tracking provides audit trail
- Debug logging helps with troubleshooting
