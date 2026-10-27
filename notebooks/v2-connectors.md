# V2 connector operations note

This notebook records verified connector status; the single work plan is in `docs/PLAN.md`. The supported source tree is root `v2/`, with active connector implementations under `v2/catalog/connectors/`.

## Verified deployment and sample status

- The supervisor and JudyRecords/Truth Social Workers were deployed as private Workers using direct service bindings because dispatch namespaces are unavailable for this account.
- A bounded Truth Social profile run completed one item and wrote one artifact. It does not prove timeline pagination or historical completeness.
- A JudyRecords direct-record URL was scraped and stored with full extracted text and original HTML sidecar. The generic search seed and `search=Adam` crawl yielded no record URLs; search-result discovery, pagination, and the 75,000-record target remain unverified.
- SAM.gov connector code is present but is not bound to the supervisor and has no verified live run.
- No Facebook profile/group connector or CourtListener V2 connector is currently implemented.

## Orchestration and secrets

The supervisor owns run registration, Queue claims/retries, K2 events, and run finalization. Connectors expose private `/health`, `/v2/discover`, and `/v2/process` handlers. The supervisor calls them through direct service bindings. Registration is explicit; code presence or deployment does not enable a connector.

JudyRecords and Truth Social receive `SPIDER_API_KEY` and `WEBSHARE_PROXY_URL` through account Secrets Store bindings. Internal calls use `V2_CONNECTOR_TOKEN`; the operator API uses `V2_SUPERVISOR_TOKEN`. Never write secret values into this notebook.

## Storage and analytics

- `harvy-raw`: raw source captures.
- `harvy-artifacts`: normalized records and release manifests.
- Basin: historical analytics, separate from the R2 buckets.

Do not combine raw/normalized object storage with Basin-managed data. Keep source URLs, timestamps, provenance, completeness, and access limitations with each artifact. A name match is not a verified identity.

## Catalog reconciliation

The checked-in source catalog currently contains 99 stream entries and 11 reference entries. The upstream crosswalk claims 106 imported definitions; its disposition headings sum to 117 (20 + 22 + 64 + 11), while the Stream Index lists 95 proposed implementations and no working streams. These counts conflict and must be reconciled before the catalog is treated as complete. Catalog entries are candidates, not live connectors.

SAM.gov connector bounds are a one-year posted-date interval, at most 100 API records per page, and 25 pages per run. Its API key is attached only to outbound requests and removed from captured responses. A bounded capability check is required before enabling it.
