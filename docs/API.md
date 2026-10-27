# Harvy Worker API Reference

Base URL: `https://harvybot.com`. Implementation: `src/worker.py`. JSON responses use `application/json`.

## Search and dossier data

| Method | Route | Request | Notes |
|---|---|---|---|
| `GET` | `/api/universal-search?q=...&type=...` | Query parameters | Searches title, snippet, and body in D1; max 50 results. `type` accepts supported source categories. |
| `POST` | `/api/universal-search` | `{ "query": "...", "type": "all" }` | Same search as GET. |
| `GET` | `/api/artifacts/{uuid}` | — | Returns the selected document, profile record, and sibling posts for the dossier renderer. Public response; currently cached for five minutes. |
| `GET` | `/health` | — | Runtime and secret-presence indicators only; secret values are never returned. |

## Profile jobs

| Method | Route | Request / authorization | Notes |
|---|---|---|---|
| `POST` | `/api/jobs` | `{ "url": "https://…", "consent": true }` | Queues a supported HTTPS public profile. Returns `202`, `id`, and `job_token`. |
| `GET` | `/api/jobs/{id}` | `X-Job-Token: <job_token>` | Job status, logs, and saved-file list. |
| `GET` | `/api/jobs/{id}/search-documents` | `X-Job-Token` | Search documents associated with the job. |
| `GET` | `/api/jobs/{id}/files/{path}` | `X-Job-Token` | Retrieve a job-scoped JSON artifact. |
| `GET` | `/api/jobs/{id}/download` | `X-Job-Token` | Download the job's saved JSON. |
| `POST` | `/api/jobs/{id}/stop` | `X-Job-Token` | Cancels work only while it remains queued. |

## Account and email signup

| Method | Route | Request | Notes |
|---|---|---|---|
| `POST` | `/api/auth/register-anonymous` | `{ "privacyAccepted": true }` | Required privacy-policy acknowledgment before starting passkey registration. |
| `POST` | `/api/newsletter/subscribe` | `{ "email": "…", "privacyAccepted": true, "newsletterOptIn": true }` | Explicit opt-in only. Adds the `harvy` tag in Buttondown and requests double opt-in; account creation never subscribes users automatically. Stores Buttondown subscriber ID and consent timestamp in D1, not the email address. Requires the `BUTTONDOWN_API_KEY` Worker secret. |

The newsletter route rate-limits by source IP. It does not import existing accounts or accept bulk subscriber uploads.
The Buttondown `Harvy` segment should be configured as a saved filter over the `harvy` tag; only confirmed opt-ins enter the active audience.

## Staged Better Auth service

Better Auth currently runs behind the `HARVY_AUTH` service binding. Its API is exposed at `/api/better-auth/*` only after the main Worker variable `BETTER_AUTH_ENABLED` is explicitly set to `true`; default is disabled. `GET /api/better-auth/config` returns enabled feature flags only, never secret values. Legacy `/api/auth/*` routes remain active while the flag is false and return `410` after cutover; existing legacy API keys/sessions are still checked by the main Worker during the migration window.

Better Auth endpoints cover the configured email/OAuth, anonymous/passkey, 2FA, admin, API key, organization, CAPTCHA, session, referral, audit, Sentinel, and gated Stripe plugins. Provider-specific methods are unavailable until their credentials are configured. The Better Auth D1 schema is in `migrations/0005_better_auth.sql`; signup-policy acknowledgments are audited by `migrations/0006_auth_privacy_consents.sql`. Neither migration has been applied remotely.

## Not implemented in the Worker

`POST /api/username-jobs` and `POST /api/research-jobs` currently return `501`. Do not present these as live Worker capabilities until their queue consumers are implemented.

## Security and limitations

- The job token is a per-job capability, not a user/account authorization system.
- The current search and profile records do not yet have environment/tenant scope.
- The legacy custom passkey/account routes remain for compatibility; their stored credentials are not imported into Better Auth. Users re-enroll passkeys during cutover.
- Future BI requests must use approved metric/filter definitions, never raw browser-supplied SQL.
