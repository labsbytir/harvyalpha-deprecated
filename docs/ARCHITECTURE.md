# Harvy V2 Architecture

## Canonical source layout

- `v2/supervisor/`: run orchestration, connector registration, Queue consumption, public progress, and release manifests.
- `v2/catalog/connectors/`: source Workers and catalog-only candidates.
- `v2/shared/`: connector contracts, queue logic, events, and release-manifest helpers.
- `v2/migrations/`: the V2 D1 schema, including Better Auth tables.
- `v2/auth/`: the Better Auth Worker and client/UI.
- `v2/graph/`: static query interface source; its old API host was removed and V2 query routes are not implemented yet.
- `v2/portal/`: shared V2 browser shell source.
- `pages/` and `styles/`: static page and CSS source; `static/` contains generated outputs.

V2 platform source and deployment configuration live under root `v2/`. No root compatibility directory is part of the supported layout.

## Ingestion flow

```text
Operator → V2 supervisor → private connector /discover
                         → D1 registration + run/item state
                         → shared Queue → supervisor claim/retry
                         → private connector /process → R2 artifact
                         → K2 event → Basin/Analytics projection
```

The supervisor uses direct service bindings for JudyRecords and Truth Social because dispatch namespaces are unavailable in this account. Each connector retrieves data with its own scoped secret bindings; provider credentials are never forwarded through the supervisor. SAM.gov has connector code but is not currently bound to the supervisor.

## Storage and scope

- **D1:** operational state, registrations, runs, work items, canonical ontology objects/observations/links, and dashboard definitions.
- **R2 `harvy-raw`:** source response artifacts.
- **R2 `harvy-artifacts`:** normalized records and release manifests.
- **Basin:** historical analytics, separate from the R2 buckets.

Ontology objects are shared canonical records. Private/customer data must be isolated by environment and authorization scope. Never expose private results via a public cache. The 75% cache-hit goal applies only to eligible public endpoints and has not been measured on a representative workload.

## Authentication and public UI

Better Auth is implemented in `v2/auth/` and configured to use the V2 D1 database. Its custom-domain route and migrations are local configuration only; this refactor did not deploy them or apply remote migrations. Legacy account migration/re-enrollment needs an explicit, reviewed plan.

The static query UI still needs V2-owned query API routes before it can be treated as functional. A health response or successful connector sample does not verify unrelated UI or historical data coverage.

See [V2 connector operations](V2_CONNECTORS.md), [authentication](AUTH.md), [Basin operations](../v2/health/BASIN.md), and the [master plan](PLAN.md).
