# V2 API Reference

## Supervisor API

Use the deployed supervisor URL from `V2_SUPERVISOR_URL`. Operator routes require `Authorization: Bearer <V2_SUPERVISOR_TOKEN>`; never place the token in browser code or source files. Responses are JSON. See [V2 connector operations](V2_CONNECTORS.md) for rollout and recovery details.

| Method | Route | Authorization | Purpose |
|---|---|---|---|
| `GET` | `/health` | None | Readiness response; does not verify collection coverage. |
| `GET` | `/v2/connectors` | Supervisor bearer | Current D1 connector registrations and safe settings. |
| `PUT` | `/v2/connectors/{id}` | Supervisor bearer | Register or update an existing connector; deployment is separate. |
| `GET` | `/v2/source-catalog` | Supervisor bearer | Candidate source inventory, not an enabled-connector list. |
| `POST` | `/v2/runs` | Supervisor bearer | Start an idempotent, bounded run for a registered, enabled connector. |
| `GET` | `/v2/runs/{id}` | Supervisor bearer | Read run state, timestamps, and errors. |
| `POST` | `/v2/releases` | Supervisor bearer | Validate and store a dataset release manifest. |
| `GET` | `/api/public/progress?days=1\|7\|30` | None | Shared-scope aggregate; public cached response. |
| `GET` | `/api/public/datasets/{dataset}/{release}/manifest` | None | Public shared release manifest; public cached response. |

Run creation requires a lowercase connector ID, explicit environment scope, idempotency key, and source-specific bounded input. Registration must be enabled and capability-verified first. A connector's presence in code or the source catalog is not approval to collect.

## Private connector service API

These routes are only for supervisor-to-connector service bindings. They are not public endpoints and use `V2_CONNECTOR_TOKEN` bearer authentication.

| Method | Route | Purpose |
|---|---|---|
| `GET` | `/health` | Confirm Worker identity. |
| `POST` | `/v2/discover` | Return bounded, validated work items. |
| `POST` | `/v2/process` | Process a claimed item and return its R2 artifact path. |

## Authentication

The Better Auth Worker in `v2/auth/` exposes `GET /api/better-auth/config` and the Better Auth API under `/api/better-auth/*`. The custom-domain route and V2 D1 migration are configured locally but were not deployed or applied in this refactor. See [authentication operations](AUTH.md).

## Not implemented

- The static query interface still needs V2 query and dashboard endpoints.
- Facebook profile/group collection and CourtListener search/bulk import need V2 implementations.
- No run endpoint promises full source history or completeness. The JudyRecords 75,000-record target and full Truth Social history remain unverified goals.

Do not cache private or environment-scoped responses publicly. The 75% cache-hit target applies only to eligible public endpoints and requires measurement.
