# Upload Worker Template

A public-facing Worker that accepts file uploads, streams them to R2, processes them into standardized JSON artifacts, and uploads to Basin for analytics.

## Features

- ✅ **Drag-and-drop interface** - Simple web UI for file uploads
- ✅ **Streaming uploads** - Files streamed directly to R2 without loading into Worker memory
- ✅ **Real-time processing** - Files processed into standardized JSON format immediately
- ✅ **Basin integration** - Artifacts automatically uploaded to Basin catalog
- ✅ **Public endpoint** - Can be exposed via custom domain
- ✅ **Progress tracking** - Real-time upload status for each file
- ✅ **Error handling** - Failed uploads reported with details

## Architecture

```
User Browser → Upload Worker (public endpoint)
       ↓
   R2 Bucket (harvy-upload) - Raw file storage
       ↓
   R2 Bucket (harvy-artifacts) - Processed JSON artifacts
       ↓
   Basin Catalog (harvy-ql) - Analytics storage
```

## Deployment

### 1. Create R2 Buckets

```bash
# Create buckets (if they don't exist)
wrangler r2 bucket create harvy-upload
wrangler r2 bucket create harvy-artifacts
```

### 2. Configure Environment Variables

```bash
# Basin integration (optional)
export BASIN_INGEST_URL="https://your-stream.ingest.cloudflare.com"
export BASIN_INGEST_TOKEN="your-token-if-auth-enabled"
```

### 3. Deploy Worker

```bash
# Deploy to Workers Dev (for testing)
wrangler deploy --env production

# Or deploy to custom domain
wrangler deploy --name harvy-upload-worker --env production
```

### 4. Configure Route

Add a route in your DNS:
```
upload.yourdomain.com → harvy-upload-worker.workers.dev
```

## Usage

### Web Interface

Visit the Worker URL to access the drag-and-drop upload page:
```
https://upload.yourdomain.com/
```

### API Endpoint

```bash
# Upload a file via curl
curl -X POST -F "file=@example.html" https://upload.yourdomain.com/api/upload

# Response
{
  "success": true,
  "fileId": "uuid",
  "fileName": "example.html",
  "fileSize": 12345,
  "artifactPath": "processed/example.html.json",
  "artifactId": "sha256:..."
}
```

### Health Check

```bash
curl https://upload.yourdomain.com/health

# Response
{
  "status": "ok",
  "worker": "harvy-upload-worker",
  "features": ["file-upload", "r2-storage", "basin-integration"]
}
```

## File Processing

### Input Files
- HTML files → `raw_response` artifacts
- JSON files → `normalized_entity` artifacts  
- Text files → `raw_response` artifacts
- Any format → Preserved in `content` field

### Output Artifact Structure

```json
{
  "artifact_id": "sha256:...",
  "artifact_type": "raw_response" | "normalized_entity",
  "content_type": "text/html",
  "content": "<file content>",
  "encoding": "utf-8",
  "metadata": {
    "file_size": 12345,
    "modified_at": "2024-01-01T00:00:00+00:00",
    "source_path": "harvy-upload/example.html",
    "processing_timestamp": "2024-01-01T00:00:00+00:00",
    "upload_timestamp": "2024-01-01T00:00:00+00:00"
  },
  "provenance": {
    "source_bucket": "harvy-upload",
    "collection_method": "web_upload"
  }
}
```

## Storage

### R2 Buckets

| Bucket | Purpose | Lifecycle |
|--------|---------|-----------|
| `harvy-upload` | Raw uploaded files | Configure retention as needed |
| `harvy-artifacts` | Processed JSON artifacts | Permanent storage |

### Basin Catalog

Processed artifacts are uploaded to Basin with:
- **Table**: `default.harvy_scraped_data`
- **Schema**: `v2/health/schema.json`
- **Query**: Use Basin SQL to analyze uploaded files

## Security

### Public Access
- Worker is publicly accessible (unless behind Cloudflare Access)
- Files are streamed directly to R2
- No file content loaded into Worker memory (streaming)

### Authentication (Optional)
Add authentication by:
1. Using Cloudflare Access
2. Requiring `Authorization: Bearer <token>` header
3. Checking `V2_CONNECTOR_TOKEN` binding

## Monitoring

### Worker Metrics
- Upload count
- Processing time
- Error rates
- File sizes

### Basin Queries
```sql
-- Count uploaded artifacts
SELECT source, kind, COUNT(*)
FROM default.harvy_scraped_data
WHERE source = 'harvy-upload'
GROUP BY source, kind;

-- Get recent uploads
SELECT artifact_path, collected_at, file_sha256
FROM default.harvy_scraped_data
WHERE source = 'harvy-upload'
ORDER BY collected_at DESC
LIMIT 100;
```

## Customization

### Modify Processing Logic
Edit `src/index.ts` to:
- Change artifact format
- Add validation
- Extract structured data from files
- Add metadata enrichment

### Add File Type Support
Extend the `createArtifact` function to handle:
- PDFs (extract text with OCR)
- Images (extract metadata)
- Archives (unpack and process)
- Videos (extract thumbnails)

### UI Customization
Edit the HTML/CSS in the Worker to:
- Change colors and branding
- Add file type restrictions
- Include custom instructions
- Add analytics tracking

## Performance

### Memory Usage
- Files streamed directly to R2 (no memory load)
- Processing happens in Worker memory after upload
- Large files (>100MB) may need container-based processing

### Upload Limits
- Default: Cloudflare Workers body size limit (100MB for Workers, 1GB for Enterprise)
- For larger files: Use multipart uploads or container-based processor

## Troubleshooting

### Issue: Uploads failing
**Check:**
- R2 bucket bindings in wrangler.jsonc
- Worker has write permissions to buckets
- File size within limits

**Solution:**
```bash
wrangler tail --format json
```

### Issue: Basin upload not working
**Check:**
- `BASIN_INGEST_URL` environment variable
- `BASIN_INGEST_TOKEN` if authentication required
- Basin stream is active

**Solution:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{}' $BASIN_INGEST_URL
```

### Issue: Worker memory limits
**Check:**
- File size being uploaded
- Processing complexity

**Solution:**
- Use smaller files
- Offload processing to container
- Stream directly to R2 without processing in Worker

## References

- [Cloudflare Workers](https://developers.cloudflare.com/workers/)
- [R2 Storage](https://developers.cloudflare.com/r2/)
- [Basin Pipelines](https://developers.cloudflare.com/basin-pipelines/)
- [Workers Documentation](https://developers.cloudflare.com/workers/platform/storage-options/)

## License

This template is provided as-is for Harvy V2 platform use.

---

**Template Version:** 1.0  
**Last Updated:** October 27, 2024  
**Author:** Harvy V2 Team
