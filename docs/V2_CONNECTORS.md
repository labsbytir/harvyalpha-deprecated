# V2: direct service-bound connectors and account secrets

This guide describes the V2 connector deployment. The supervisor and JudyRecords/Truth Social Workers are ordinary private Workers. Their implementations live in `v2/catalog/connectors/{judyrecords,truthsocial,sam-gov}/`; SAM.gov has code but is not bound to the supervisor. Dispatch namespaces are unavailable in this account, so the supervisor uses direct service bindings. V2 source and configuration are maintained under `v2/`.

## Why a connector requires a supervisor binding

Ordinary Worker service bindings are enumerated in the *calling* Worker's Wrangler config. The supervisor maps supported connector IDs to private services in `connectorService`; adding a connector requires updating the supervisor binding, mapping, tests, and deployment. JudyRecords and Truth Social share one `harvy-v2-work` Queue and one Workflow. Bind only private V2 connector services.

```text
authenticated POST /v2/runs
  → validate explicit environment + bounded input
  → check registered, enabled, capability-verified connector in v2 D1
  → Workflow calls the connector's /v2/discover through its service binding
  → validate item IDs, URLs and scope → persist v2 D1 items → shared Queue
  → supervisor queue consumer: claim D1 lease → service binding POST /v2/process
  → connector writes its R2 artifact and returns its path; JudyRecords stores normalized JSON plus original HTML
  → supervisor emits v2 K2 event, finalizes D1 item/run and acknowledges Queue message
```

The connector is not automatically approved just because its code exists or was deployed. Discovery and work require an explicit D1 registration and activation. ArtifactFS/Artifacts may later trigger builds from versioned source, but neither Artifacts nor Worker initialization creates bindings or approves a connector. No Artifacts integration is configured here.

## Contract and trust boundaries

Each v2 connector implements `GET /health` (JSON `connector` must match its ID), authenticated `POST /v2/discover` (returns bounded `items` with `connector`, `run_id`, `environment_id`, HTTPS `url` and `source_url`, `kind`), and authenticated `POST /v2/process` (takes the claimed item and returns `{ "artifact_path": "...", "record_count": 0 }`; count is optional). `/v2/process` replies 422 for permanent source/item errors and 503 for transient errors. The shared consumer retries transient failures with the existing D1 lease and at-most-eight-attempt logic. After the last attempt or a permanent error, it marks the item failed in D1 and acknowledges the message; the configured Queue DLQ catches delivery/handler failures, **not** these application-level failures. Invalid or permanent items cannot be silently routed to a different connector. R2 writes should be safe to repeat because Queue delivery and K2 publish may retry.

`v2/shared/contracts.ts` validates all run IDs and explicit environment IDs; existing JudyRecords, Truth Social and SAM.gov run inputs keep their source-specific validators. A new connector's generic JSON input is capped at 16 KiB at the supervisor, **not** considered a source-specific security validator: implement bounded inputs and an HTTPS origin/path allowlist in its own discovery and process handlers. The supervisor caps discovery at 1,000 items; the connector may need to break larger runs into smaller batches. Connector code must reject cross-source URLs, embedded credentials, unauthorized scopes, and malformed inputs. Do not treat a person's name in a source record as verified identity. Public progress is aggregated from shared-scope events only; private artifacts must not be placed in a public cache.

The shared supervisor token authorizes the registration and run API. A separate `V2_CONNECTOR_TOKEN` secures connector calls from the supervisor. Keep connector Workers off `workers.dev` (`workers_dev: false`) and do not expose `/v2/process` on a public route. Set the same connector token on the supervisor and approved connectors without checking it into source or logging it. The supervisor **does not** pass provider credentials; each connector receives only its approved resource/secret bindings. D1 controls registration and leases, KV holds non-secret optional flags, R2 stores artifacts, K2 carries telemetry. A disabled connector blocks *new runs*; already queued work for a registered connector can still drain, so use Queue pause/recovery procedures to stop processing.

## Secrets Store is central storage, not automatic authorization

Create provider credentials once in account-level Secrets Store. A binding explicitly attaches a named secret to a Worker at deploy time. `await env.SPIDER_API_KEY.get()` retrieves its value; `workers` scope means the Workers *service* may consume it, **not** that only a particular Worker can. The binding list is the per-connector allowlist. JudyRecords and Truth Social request Spider/Proxy only; SAM.gov requests its API key only. The supervisor must never hold the provider keys or a binding to the entire store.

Use the account's Secrets Store ID (`a47356e8f71f432e8fc18ee717af2d64`) in the connector config's `secrets_store_secrets` entries. Each provider secret needs `workers` scope; the CI/deployment credential attaching it needs **Account Secrets Store Edit**, not merely Read. Separate secret administration from deployment when possible, and do not let an unreviewed connector manifest choose arbitrary secret names. The single-store/open-beta limits (currently 100 production secrets) should be checked against your account before scaling onboarding. Rotating a shared secret changes it for **all** bound connectors. Audit logs cover access and create/update/delete actions, but do not substitute for per-Worker binding review. Local Secrets Store entries are different from remote values and may be unencrypted on disk: use dummy local credentials and keep `.wrangler/state` out of Git.

The dispatch namespace is unavailable in this account; direct service bindings are the active design. The deployed JudyRecords and Truth Social Workers successfully read their bound Spider/Webshare Secrets Store values during bounded samples. Do not move provider credentials into the supervisor as a workaround.

## Current deployment and rollout

1. V2 D1 migrations and the shared Queue, DLQ, Workflow, K2 stream, KV namespace, and R2 buckets are configured. Verify the live D1 migration state before applying anything; never rerun applied migrations.
2. Active connector configs are `v2/catalog/connectors/judyrecords/wrangler.jsonc`, `v2/catalog/connectors/truthsocial/wrangler.jsonc`, and `v2/catalog/connectors/sam-gov/wrangler.jsonc`. Preserve their Worker names so the supervisor service bindings continue to resolve.
3. Spider/Webshare Secrets Store bindings are configured on JudyRecords and Truth Social; SAM.gov's API key binding is configured on its Worker. The same `V2_CONNECTOR_TOKEN` must be set on the supervisor and each bound connector. `V2_SUPERVISOR_TOKEN` separately protects the operator API.
4. JudyRecords and Truth Social were deployed and registered. A bounded Truth Social profile sample wrote an artifact, but this does not prove historical completeness. A direct JudyRecords record URL was scraped and stored; the `search=Adam` crawl returned no record URLs, so term-based discovery remains unverified. SAM.gov is not connected to the supervisor.
5. For a new connector, place it under `v2/catalog/connectors/<id>/`, add its private service binding and `connectorService` mapping, test and deploy it, register it disabled, then enable only after a bounded sample verifies source access and artifact persistence.
6. Inspect `GET /v2/runs/<id>`, D1 work-item state, Queue/DLQ, R2 artifact paths and K2 progress. A health response or local test alone does not establish collection success. Cache only scope-safe public data.

For another connector, copy `v2/templates/<kind>` to `v2/catalog/connectors/<id>/`, use a lowercase ID matching `^[a-z][a-z0-9-]{0,62}$`, and set its Worker name to `harvy-<id>`. Fix the template `$schema` path after copying; attach only approved provider secrets and the shared internal token. Implement the TODOs, add source-specific tests, and update the supervisor service binding and `connectorService` mapping. Deploy it as a private Worker, then register and enable it as above.

## Recovery and known limits

- Failed registration `/health` means the service is absent, has the wrong ID, or is unhealthy. Check its service binding, Worker name and logs before enabling; never silently fall back to a public URL.
- A 409 on run creation means disabled/unverified registration or a KV flag explicitly disabling it. Input validation errors return 400; old idempotency keys with different input return 409. Secret binding authorization failures require checking both the deployer's Secrets Store Edit permission and the secret's `workers` scope.
- To pause **new** runs, PUT registration with `enabled: false`. To stop existing work, pause/drain the v2 Queue separately, inspect failed D1 items, leases and DLQ, then resume or replay with the same idempotency behavior. Do not delete artifacts or reset D1 to roll back a Worker. Preserve old connector versions until queued items can drain.
- The shared Queue starts with batch size two and a 15-minute D1 item lease; unlike separate per-connector queues, a noisy or rate-limited connector can delay others. Monitor per-connector lag, failures, source limits and DLQ; split queues or add a rate-limited routing tier only when observed load justifies it. Long-running items need a measured timeout/lease strategy before live use. Worker/Workflow retries can repeat provider requests or R2 writes, so choose deterministic artifact paths and idempotent output handling.
- The bounded Truth Social sample exercised Queue delivery, Secrets Store access, and R2 artifact writing. A full backfill, historical pagination, and JudyRecords discovery from a search-results page remain unverified. Registration is an authenticated operator API, not an initialization side effect.

Sources: [Workers service bindings](https://developers.cloudflare.com/workers/runtime-apis/bindings/service-bindings/), [Secrets Store Workers binding](https://developers.cloudflare.com/secrets-store/integrations/workers/), [access control](https://developers.cloudflare.com/secrets-store/access-control/), [audit logs](https://developers.cloudflare.com/secrets-store/audit-logs/).
