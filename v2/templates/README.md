# Platform v2 connector templates

Copy one template per new connector. Do not modify or deploy the existing v1 `harvy` Worker while building v2. The supervisor has one shared v2 work queue and one dispatch namespace; connectors need neither a queue nor supervisor service binding.

```
cp -r platform-v2/templates/api-connector platform-v2/<connector-id>
```

## Which template

| Template | Use when | Modeled on |
|---|---|---|
| `api-connector` | Source has a public paginated JSON API (key in query/header) | `platform-v2/sam-gov` |
| `web-scraper` | Source needs browser-rendered HTML via Spider Unlimited + proxy | `platform-v2/truthsocial` |
| `legal-research` | Court/arrest record pages via Spider Unlimited + proxy | `platform-v2/judyrecords` |

## Per-template setup

1. Copy the directory to `platform-v2/<id>`; name its script `harvy-<id>` and replace the template ID in `/health`, discovery items, and `/v2/process` with `<id>`.
2. Fix `$schema` to `../../node_modules/wrangler/config-schema.json`, replace the R2 bucket and Secrets Store ID placeholders, and attach only approved provider secrets. Bind the shared `V2_CONNECTOR_TOKEN` separately. Keep `workers_dev: false`.
3. Fill the `TODO(connector)` sections: bounded input validation, source URL allowlist, extraction, normalization, artifact paths, and provenance. Do not deploy with example URLs or parser logic.
4. `platform-v2/tsconfig.json` includes every top-level connector `src/` automatically. Verify typecheck and tests, then deploy into the **v2 dispatch namespace** and register it disabled. Enable only after source access, credential scope, and behavior are verified.

The supervisor does not need a code/config change per connector. See [the v2 dispatch and secrets guide](../../guides/PLATFORM_V2_CONNECTORS.md) for the complete deployment and registration procedure.

## Invariants every template keeps

- `GET /health` returns `{ status: "ok", connector }`; `POST /v2/discover` requires `Authorization: Bearer <V2_CONNECTOR_TOKEN>` (timing-safe compare) and `no-store` JSON.
- `POST /v2/process` validates the work item and returns `{ artifact_path, record_count? }`; the supervisor's shared queue handler owns the D1 claim, retry/failure state, DLQ configuration and K2 completion events.
- Raw payloads go to R2 under `harvy-ql/raw/<family>/<connector>/<run_id>/`; normalized records are JSON with `schema_version`, `record_id`, `source_url`, `collected_at`, `provenance`, `limitations`.
- Secrets stay in env bindings; proxy/API keys never appear in URLs stored in D1/R2 (redact before persist).
