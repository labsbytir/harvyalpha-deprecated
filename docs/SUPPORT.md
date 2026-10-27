# Harvy Support and Troubleshooting

## Search has no results

Universal search currently queries `harvy_search_documents` in D1. Empty results can mean the data has not been indexed; it does not mean the source has no records. Search is a bounded title/snippet/body substring lookup, not arbitrary SQL.

## A job cannot be opened

Job status, artifact, and download endpoints require the `X-Job-Token` returned by `POST /api/jobs`. It is different from an account session. If the token is lost, the current API does not provide token recovery.

## A job type returns 501

Username and research jobs are not implemented in the Cloudflare Worker yet. The local Python service has separate job paths; do not assume they are available on `harvybot.com`.

## UI changes do not appear

CSS sources are in `styles/` and templates are in `pages/`. Run `npm run build:templates`; then hard-refresh the browser if an older asset is cached.

## Basin data is missing

The local Flask app has Basin upload helpers. The Cloudflare Worker profile path currently writes raw responses to R2 and search projections to D1; it does not yet ingest normalized object records into Basin. See [Basin operations](../v2/health/BASIN.md).

## Support contact

No public support portal or SLA is configured in the application documentation. For an internal issue, capture the route, status code, request/job ID, and sanitized logs. Never include API keys, proxy credentials, session cookies, or private raw records.
