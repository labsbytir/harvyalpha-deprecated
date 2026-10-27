# Better Auth integration

## Current state

Harvy uses Better Auth **1.7.13** in a separate TypeScript Worker (`v2/auth/`) with D1. The Python app Worker remains the scraper/API host and forwards `/api/better-auth/*` to the auth service through `HARVY_AUTH`.

The integration is staged and **disabled by default**: `BETTER_AUTH_ENABLED` is `false`. The existing `/api/auth/*` custom login remains active while the flag is false; at cutover those routes return `410` and legacy sessions/keys are checked as a compatibility fallback. Do not enable the new route or apply migrations remotely as part of a normal deploy.

Auth source is grouped under `v2/auth/`: the Better Auth client/UI are `client.ts` and `ui.ts`, and the legacy-compatible modal controller is `public/auth-modal.js`. Vite bundles `client.ts` to `static/auth-client.js` and copies the modal controller to `static/auth-modal.js`, preserving the existing page URLs. Auth styles live in `styles/stylesheet.css`; `static/stylesheet.css` is generated. The static files are build outputs, not independent source files.

## Configured plugins

- Core: email/password with email verification/reset (enabled only when Infrastructure and email feature flags are true), Discord/GitHub/Google/Twitter OAuth (each provider appears only when its client ID and secret exist).
- Local plugins: anonymous accounts, passkeys, authenticator-app TOTP, admin, API keys (`harvy_live_` prefix), organizations, Turnstile CAPTCHA, last-login method, multi-session, and referrals.
- Better Auth Infrastructure: dashboard/audit logging, Sentinel, and transactional email require `BETTER_AUTH_API_KEY` plus `BETTER_AUTH_INFRA_ENABLED=true`; email/password additionally requires `BETTER_AUTH_EMAIL_ENABLED=true`. This is a separate service/plan and data is sent to Better Auth Infrastructure when active.
- Stripe: the plugin is conditionally loaded only when `STRIPE_ENABLED=true` and the Stripe secret/webhook are configured. It creates no subscription checkout until plans/prices are explicitly configured.

The `Harvy` Buttondown newsletter key and Buttondown subscription flow are separate from Better Auth transactional email. Never reuse the Buttondown key as `BETTER_AUTH_API_KEY`.

## Required secrets/configuration

Use Cloudflare Worker secrets (do not commit values or paste them into documentation):

```sh
npx wrangler secret put BETTER_AUTH_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put BETTER_AUTH_API_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put DISCORD_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put DISCORD_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put GITHUB_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put GITHUB_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put TWITTER_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put TWITTER_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put TURNSTILE_SECRET_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put STRIPE_SECRET_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put STRIPE_WEBHOOK_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put HARVY_ADMIN_USER_IDS --config v2/auth/wrangler.jsonc
```

`TURNSTILE_SITE_KEY` is public configuration; set it as a Worker variable after creating the Turnstile widget. Set `BETTER_AUTH_INFRA_ENABLED`, `BETTER_AUTH_EMAIL_ENABLED`, and `STRIPE_ENABLED` to `true` only when each service is ready. OAuth callback URLs use `https://harvybot.com/api/better-auth/callback/{discord|github|google|twitter}`. Set `BETTER_AUTH_ENABLED=true` on the main Worker **only after** all providers, migrations, privacy checks, and the UI have been tested.

## D1 and legacy accounts

Better Auth tables are generated in `v2/auth/auth-schema.ts`; the reviewed D1 migration is `migrations/0005_better_auth.sql`, followed by the privacy-consent audit table in `migrations/0006_auth_privacy_consents.sql`. The migrations have not been applied to production. Back up D1, review, and test locally before applying remotely.

The old `harvy_users`, `harvy_passkeys`, `harvy_sessions`, and `harvy_api_keys` tables remain intact. Existing `harvy_live_` keys are checked during the compatibility window. Legacy passkey records are not imported: users will re-enroll a Better Auth passkey rather than risk accepting incompatible credential data. Do not remove legacy tables until migration and account recovery are verified.

After changing server plugins, regenerate `v2/auth/auth-schema.ts` with the pinned Better Auth CLI version, generate and review a Drizzle SQLite migration, then place the reviewed SQL in the next root `migrations/` sequence. Use an ephemeral schema-generation secret; never put actual secrets in the schema config or migration. Test all migrations together with the local SQLite migration test before requesting a remote migration.

## Tenant/data boundary

Organizations represent customer environments, not ownership of shared ontology objects. Shared Harvy objects remain globally shared; observations, links, annotations, dashboards, and other customer-private records must be scoped to the active environment and authorized server-side. Never cache private results across environments.
