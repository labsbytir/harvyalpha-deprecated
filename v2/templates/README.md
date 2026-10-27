# V2 connector templates

Copy one template per new connector. Keep connector implementation and configuration under `v2/`. The supervisor uses a shared work queue and direct service bindings to private connector Workers; adding a connector requires its supervisor binding and service mapping.

```
cp -r v2/templates/api-connector v2/catalog/connectors/<connector-id>
```

## Which template

| Template | Use when | Modeled on |
|---|---|---|
| `api-connector` | Source has a public paginated JSON API (key in query/header) | `v2/catalog/connectors/sam-gov` |
| `web-scraper` | Source needs browser-rendered HTML via Spider Unlimited + proxy | `v2/catalog/connectors/truthsocial` |
| `legal-research` | Source needs public legal records via Spider Unlimited + proxy | `v2/catalog/connectors/judyrecords` |

## Per-template setup

1. Copy the directory to `v2/catalog/connectors/<id>`; name its script `harvy-<id>` and replace the template ID in `/health`, discovery items, and `/v2/process` with `<id>`.
2. Fix `$schema` to `../../../../node_modules/wrangler/config-schema.json`, replace the R2 bucket and Secrets Store ID placeholders, and attach only approved provider secrets. Bind the shared `V2_CONNECTOR_TOKEN` separately. Keep `workers_dev: false`.
3. Fill the `TODO(connector)` sections: bounded input validation, source URL allowlist, extraction, normalization, artifact paths, and provenance. Do not deploy with example URLs or parser logic.
4. `v2/tsconfig.json` includes nested connector `src/` files. Verify typecheck and tests, deploy the private Worker, add its service binding to `v2/supervisor/wrangler.jsonc` and mapping to `connectorService`, then register it disabled. Enable only after source access, credential scope, and behavior are verified.

See [the V2 connector operations guide](../../docs/V2_CONNECTORS.md) for deployment and registration details.

## Invariants every template keeps

- `GET /health` returns `{ status: "ok", connector }`; `POST /v2/discover` requires `Authorization: Bearer <V2_CONNECTOR_TOKEN>` (timing-safe compare) and `no-store` JSON.
- `POST /v2/process` validates the work item and returns `{ artifact_path, record_count? }`; the supervisor's shared queue handler owns the D1 claim, retry/failure state, DLQ configuration and K2 completion events.
- Raw payloads go to R2 under `harvy-ql/raw/<family>/<connector>/<run_id>/`; normalized records are JSON with `schema_version`, `record_id`, `source_url`, `collected_at`, `provenance`, `limitations`.
- Secrets stay in env bindings; proxy/API keys never appear in URLs stored in D1/R2 (redact before persist).
