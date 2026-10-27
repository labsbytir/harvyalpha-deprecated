# Harvy Worker API Reference

Base URL: `https://harvybot.com`. Implementation: `src/worker.py` (Python Workers). JSON responses use `application/json`. All dynamic API responses default to `Cache-Control: no-store` except where noted.

## Health and public status

| Method | Route | Notes |
|---|---|---|
| `GET` | `/health` | Runtime and secret-presence indicators only; secret values are never returned. |
| `GET` | `/api/status` | Public counts (objects, observations, telegram progress) plus component states. Edge-cached `public, max-age=5`. No hostnames, errors, or bridge internals. |

## Search and dossier data

| Method | Route | Request | Notes |
|---|---|---|---|
| `GET` | `/api/universal-search?q=...&type=...` | Query parameters | FTS over title/snippet/body in D1, LIKE fallback; max 50 results. `type` accepts supported source categories. Emails masked. |
| `POST` | `/api/universal-search` | `{ "query": "...", "type": "all" }` | Same search as GET. |
| `GET` | `/api/artifacts/{uuid}` | — | Selected document plus profile record and sibling posts for the dossier renderer. Emails masked. Worker-cached, `public, max-age=300`. |
| `POST` | `/api/records/{id}/reveal` | `{ "turnstileToken": "…" }` for anonymous | Returns stored email for a record. Authed: 50/day (100 admin) via D1 quota. Anonymous: 3/hour by IP, Turnstile required when configured. |

## Profile jobs

| Method | Route | Request / authorization | Notes |
|---|---|---|---|
| `POST` | `/api/jobs` | `{ "url": "https://…", "consent": true }` | Queues a supported HTTPS public profile (`ALLOWED_PROFILE_HOSTS` in `src/worker.py`). Returns `202`, `id`, and `job_token`. Job envelope via `scrape/protocol.py`; dispatched on `HARVY_QUEUE`. |
| `GET` | `/api/jobs/{id}` | `X-Job-Token: <job_token>` | Job status, logs, saved-file list, post count, elapsed. |
| `GET` | `/api/jobs/{id}/search-documents` | `X-Job-Token` | Up to 100 search documents for the job, emails masked. |
| `GET` | `/api/jobs/{id}/files/{path}` | `X-Job-Token` | Retrieve a job-scoped JSON artifact from R2. |
| `GET` | `/api/jobs/{id}/download` | `X-Job-Token` | Download the job's first saved JSON as attachment. |
| `POST` | `/api/jobs/{id}/stop` | `X-Job-Token` | Cancels work only while it remains queued. |

Queue consumer (`Default.queue`) validates the envelope, runs Spider Unlimited scrape with proxy, extracts profile/posts (`extract_profile_details`), replays Threads GraphQL for up to 25 posts, stores raw JSON in R2 (`jobs/{id}/raw/profile.json`), indexes `social` + `posts` rows in D1, and ingests shared ontology objects/observations/authored-links (environment `shared`).

## Account and email signup

| Method | Route | Request | Notes |
|---|---|---|---|
| `GET` | `/api/auth/config` | — | Feature flags only (`newsletter_enabled`). |
| `GET` | `/api/auth/session` | session/API key | Current user or `null`. |
| `POST` | `/api/auth/register-anonymous` | `{ "privacyAccepted": true, "turnstileToken"? }` | Required privacy acknowledgment; caches a 10-min KV registration challenge. |
| `POST` | `/api/auth/passkey/register-verify` | `{ "userId", "credentialId", "publicKey"?, "name"? }` | Creates user + passkey in D1, issues 30-day `harvy_session` cookie. |
| `POST` | `/api/auth/passkey/login-challenge` | — | Issues 5-min KV login challenge. |
| `POST` | `/api/auth/passkey/login-verify` | `{ "credentialId", "challengeId", "clientDataJSON", "authenticatorData", "signature" }` | Verifies WebAuthn assertion (type, challenge, UP flag), issues session cookie. |
| `POST` | `/api/auth/2fa/generate` | auth required | Returns TOTP secret, `qrUri`, and 10 backup codes; 10-min KV pending state. |
| `POST` | `/api/auth/2fa/verify` | `{ "code": "123456" }` | Enables 2FA in D1 on valid code. |
| `GET` | `/api/auth/api-keys` | auth required | Lists key metadata (never raw values). |
| `POST` | `/api/auth/api-keys` | `{ "name"?: "…" }` | Returns `harvy_live_…` once; only hash/prefix stored. |
| `DELETE` | `/api/auth/api-keys/{id}` | auth required | Revokes key. |
| `POST` | `/api/auth/sign-out` | session cookie | Deletes session, clears cookie. |
| `POST` | `/api/newsletter/subscribe` | `{ "email": "…", "privacyAccepted": true, "newsletterOptIn": true }` | Explicit opt-in only. Adds the `harvy` tag in Buttondown, double opt-in; stores subscriber ID + consent in D1, not the email. 6/hour per IP. Requires `BUTTONDOWN_API_KEY`. |

## Staged Better Auth service

Better Auth runs behind the `HARVY_AUTH` service binding. Its API is exposed at `/api/better-auth/*` only after `BETTER_AUTH_ENABLED=true`; default is disabled. `GET /api/better-auth/config` returns enabled feature flags only. Legacy `/api/auth/*` routes remain active while the flag is false and return `410` after cutover; existing legacy API keys/sessions are still checked during the migration window.

Better Auth endpoints cover the configured email/OAuth, anonymous/passkey, 2FA, admin, API key, organization, CAPTCHA, session, referral, audit, Sentinel, and gated Stripe plugins. The D1 schema is in `migrations/0005_better_auth.sql`; signup-policy acknowledgments are audited by `migrations/0006_auth_privacy_consents.sql`. Neither migration has been applied remotely.

## Ontology, query, dashboards, nodes

| Method | Route | Notes |
|---|---|---|
| `GET` | `/api/query/catalog` | Allowlisted metric catalog; browser never supplies raw SQL. |
| `POST` | `/api/query/execute` | `{ "metric": "…", "filters"?: {…} }`. Scoped to caller's `environment_id` (default `shared`). |
| `GET/POST` | `/cubejs-api/v1/load`, `/api/cube/load` | Cube-compatible load; maps measures/dimensions/timeDimensions to one allowlisted metric. |
| `POST` | `/cubejs-api/v1/batch`, `/api/cube/batch` | Batch variant of load. |
| `GET` | `/cubejs-api/v1/meta`, `/api/cube/meta` | Static cube metadata. |
| `GET` | `/cubejs-api/v1/sql`, `/api/cube/sql` | Static example SQL stub, not executed. |
| `GET` | `/cubejs-api/v1/dry-run`, `/api/cube/dry-run` | Returns `ok`. |
| `GET/POST` | `/api/dashboards` | Auth required. Scoped to owner's environment. POST creates `{title, description, layout, queries}`. |
| `PUT/DELETE` | `/api/dashboards/{id}` | Owner + environment scoped update/delete. |
| `GET` | `/api/nodes/graph?center=…&limit=…` | Links + member objects, scoped `shared + environment`, max 200. |
| `GET` | `/api/ontology/objects/{urn}` | Object row plus up to 50 scoped observations. |

## Workflows proxy

`GET/POST/PUT/PATCH /api/workflows/*` requires authentication. Forwards to the `HARVY_WORKFLOWS` service with `X-Harvy-Environment` and `X-Harvy-Actor` headers. Returns `503` when the binding is unavailable.

## Ops and log ingest

| Method | Route | Auth | Notes |
|---|---|---|---|
| `POST` | `/api/logs/ingest` | `HARVY_LOGS_INGEST_KEY` or user session | Accepts JSON/NDJSON log events, groups by service, writes to `HARVY_LOGS` R2 under `external/{service}/YYYY/MM/DD/HH/`. |
| `GET` | `/api/ops/health` | ops token or user | Worker/D1/R2/bridge/workflow checks. |
| `GET` | `/api/ops/summary` | ops token or user | 24h metrics, flow counts, recent runs/events, telegram objects, schedule row, health. |
| `POST` | `/api/ops/ingest` | ops token or user | Host metrics + up to 25 events into D1; prunes metrics >7d, events >3d. |
| `POST` | `/api/ops/force` | ops token or user | Enqueues a `judyrecords.refresh` workflow run (shared scope). |

Ops auth is `HARVY_OPS_TOKEN` via `x-api-key`/`Authorization: Bearer`, falling back to the current user.

## Separate Platform v2 supervisor (not deployed)

These paths belong to `platform-v2/supervisor/src/index.ts`, **not** to the production `harvybot.com` Python Worker. They require separate v2 D1, Workflow, dispatch namespace, shared Queue, K2, R2 and KV bindings. For the security and rollout procedure, see [v2 connector operations](PLATFORM_V2_CONNECTORS.md).

| Method | Route | Authorization | Meaning |
|---|---|---|---|
| `GET` | `/health` | None | D1 readiness only; no credentials exposed. |
| `GET` | `/v2/connectors` | `V2_SUPERVISOR_TOKEN` bearer | D1 registrations and non-secret KV settings; not a list of all deployed scripts. |
| `PUT` | `/v2/connectors/{id}` | Supervisor bearer | Body `{ "enabled": false, "capability_verified": false }`; ID is lowercase slug. To enable, both must be `true` and `/health` must confirm script identity. Does **not** create or deploy the script. |
| `POST` | `/v2/runs` | Supervisor bearer | `{ "connector": "judyrecords", "environment_id": "shared", "idempotency_key": "...", "input": { ... } }`; refuses disabled/unverified registration, returns `202` with `run_id` and Workflow ID. Source-specific validation is retained for the first three connectors; new connector input is size-bounded and must be validated by that connector. |
| `GET` | `/v2/runs/{id}` | Supervisor bearer | D1 run state, error and timestamps. |
| `GET` | `/v2/source-catalog` | Supervisor bearer | Disabled candidate-source catalog; not an enabled-connector inventory. |
| `POST` | `/v2/releases` | Supervisor bearer | Immutable bulk dataset release manifest after R2 metadata checks. |
| `GET` | `/api/public/progress?days=1\|7\|30` | None | Shared-scope aggregate only; `public, max-age=300` caching. |
| `GET` | `/api/public/datasets/{dataset}/{release}/manifest` | None | Public shared release manifest only; `public, max-age=300`. |

Internal dispatched connectors implement `GET /health`, `POST /v2/discover` and `POST /v2/process`. The POSTs require `V2_CONNECTOR_TOKEN` bearer, are not public API routes and return `no-store`. The supervisor's shared Queue consumer owns work claims/retries, not the connector. No provider secret value is supplied over these calls.

## Not implemented in the Worker

`POST /api/username-jobs` and `POST /api/research-jobs` return `501`. Do not present these as live Worker capabilities until their queue consumers are implemented.

## Security and limitations

- The job token is a per-job capability, not a user authorization system.
- Search/profile reads are public; ontology, query, dashboards, and nodes apply `shared + environment` scope (see `ontology/contracts.py:build_scope_filter`).
- Legacy passkey credentials are not imported into Better Auth; users re-enroll at cutover.
- BI requests must use approved metric/filter definitions, never raw browser-supplied SQL.
