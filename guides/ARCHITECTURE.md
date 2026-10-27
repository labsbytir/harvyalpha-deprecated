# Harvy Architecture

## Codebase and runtime

- Repository: `/Users/pen/Documents/harvy` — [GitHub](https://github.com/labsbytir/harvy)
- **Standard Worker** (Python): `src/worker.py` — API routes, auth, jobs, ontology/query/nodes, ops/log ingest, workflows proxy. Queue consumer runs the profile collector inline.
- **Auth Worker** (TypeScript): `auth/` — staged Better Auth service behind the `HARVY_AUTH` binding (`/api/better-auth/*`).
- **Platform v2 Workers** (TypeScript): `platform-v2/` — supervisor with a v2 dispatch namespace and one shared work queue, plus isolated connector Workers (`sam-gov`, `truthsocial`, `judyrecords`). Templates: `platform-v2/templates/`.
- Local/hosted Python service: `web_app.py` (Flask)
- Page source: `templates/`; CSS source: `styles/`; generated Worker assets: `static/`
- Network collectors and shared scrape protocol: `scrape/`
- Basin storage/schema/docs: `health/`

## Current data flow (standard Worker)

```text
Browser → Standard Worker (src/worker.py) → HARVY_QUEUE → profile collector (same Worker)
                                                       ├─ raw response → R2 (jobs/{id}/raw/profile.json)
                                                       ├─ profile/post search documents → D1 (harvy_search_documents)
                                                       └─ objects / observations / authored-links → D1 (shared scope)
```

D1 holds job state, denormalized search documents, ontology tables, and account/passkey tables. Raw profile responses are stored in R2. The Worker profile path does not yet send normalized ontology records to Basin; the local Flask service has Basin upload helpers. See [Basin operations](../health/BASIN.md).

Caching: dynamic API defaults to `no-store`; `/api/artifacts/{id}` is Worker-cached for 5 minutes; `/api/status` is edge-cached for 5 seconds. Only public, unscoped payloads are cached.

## Platform v2 status

`platform-v2/` is an additive TypeScript scaffold with a separate supervisor, dispatch namespace, shared queue/workflow, connector Workers, and Basin/Analytics Engine projector. Its resource IDs are placeholders and the v2 Workers have not been deployed; SAM.gov and Truth Social remain gated, and imported source-catalog entries are disabled. See the [v2 dispatch guide](PLATFORM_V2_CONNECTORS.md), [master plan](../planning/PLAN.md), and [connector scope catalog](../platform-v2/catalog/connector-scopes.json).

```text
Supervisor → dispatch namespace → Connector discovery
           → shared v2 work queue → Supervisor consumer → dispatch namespace → Connector processing → R2 raw artifacts
                                    └→ K2 events → Basin pipeline → Analytics Engine projector
```

Connector contracts, queue-claim logic, K2 event publishing, and release manifests live in `platform-v2/shared/` (`contracts.ts`, `queue.ts`, `events.ts`, `release-manifest.ts`). New connectors start from `platform-v2/templates/` (api-connector, web-scraper, legal-research), are registered disabled in v2 D1, and must not reuse v1 bindings, tables, queues, or workflows.

## Planned data model

Use shared canonical objects, append-only observations, and evidence-backed links. Objects are not owned by user accounts. Future customer environments may add private observations/links that reference shared objects; a customer's accessible dataset is `shared + its environment`. Keep raw payloads in R2, operational lookups in D1, and historical analytics in Basin SQL/Iceberg.

## Standardized Storage Architecture (R2 vs. Basin)

Harvy separates blob object storage from analytical lakehouse storage across three standardized tiers to prevent catalog corruption and enforce least-privilege:

1. **Raw Scrape Lake (`harvy-raw` / `harvy-v2-raw`)**:
   - Binding: `V2_RAW_BUCKET` (or v1 `RAW_BUCKET`).
   - Stores raw HTTP response dumps, spider payloads, and HTML. Key-value access via `put`/`get`.
   - Ephemeral: safe for S3 lifecycle expiration (TTL 60–90 days).
2. **Artifact & Release Store (`harvy-artifacts` / `harvy-v2-artifacts`)**:
   - Binding: `V2_ARTIFACTS_BUCKET`.
   - Stores normalized JSON entities, dossier snapshots, and immutable release manifests (`manifest.json`).
   - Long-term retention; served via API downloads and dossier view.
3. **Analytical Lakehouse (`harvy-warehouse` / `harvy-v2-warehouse`)**:
   - Managed exclusively by **Basin Pipelines & Basin Catalog**.
   - Contains Apache Iceberg metadata snapshots and columnar Parquet data.
   - Workers do not write directly to this bucket via R2 bindings; Workers stream events via `env.V2_BASIN_STREAM.send()`.
   - Queried via distributed **Basin SQL** for BI dashboards, aggregations, and historical audit queries.
   - Never apply S3 object TTL rules to this bucket; Iceberg manages snapshot retention and compaction internally.

## User features

- **Query** (current): React/MUI saved-dashboards builder at `/query/` using a server-side allowlisted query catalog; D1 for current operational metrics and Basin SQL for historical aggregates (Basin routing planned).
- **Nodes** (planned): Reagraph network visualization of persisted objects/links with provenance and a non-WebGL list fallback.
- Workers for Platforms dynamic dispatch is the proposed v2 routing mechanism for **operator-owned** connectors; it is not a customer-code execution feature. Its account entitlement and dispatch-namespace Secrets Store binding compatibility must be checked before deployment.

The implementation plan is in [planning/PLAN.md](../planning/PLAN.md).
