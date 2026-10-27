# V2 Authentication

## Current state

Better Auth 1.7.13 source lives in `v2/auth/`. Its Worker uses the shared V2 D1 database (`harvy-platform-v2`, a Cloudflare resource name) and has a locally configured route at `https://harvybot.com/api/better-auth/*`. The auth Worker and route were not deployed as part of this refactor.

The V2 migrations are `v2/migrations/0004_better_auth.sql` and `v2/migrations/0005_auth_privacy_consents.sql`. They have not been applied remotely. The old local account Worker and compatibility routes were removed. Existing accounts in the separate legacy database have not been imported; do not promise login continuity until a reviewed migration/re-enrollment path exists.

The browser client and UI are `v2/auth/client.ts` and `v2/auth/ui.ts`. The modal controller is `v2/auth/public/auth-modal.js`; Vite copies generated assets into `static/`. The UI must use the Better Auth client only—do not add fallback calls to removed legacy auth or newsletter routes.

## Plugins and gates

The configured plugins include anonymous accounts, passkeys, authenticator-app TOTP, API keys, organizations, Turnstile, multi-session, referrals, and optional admin/audit/Stripe features. Email/password and external services remain feature-gated. Enable a feature only after its secret, callback, privacy, and end-to-end flow are configured and tested.

## Required secrets

Use Wrangler prompts or the approved secrets store; never include values in source or documentation. Examples of secret names are `BETTER_AUTH_SECRET`, OAuth client IDs/secrets, `TURNSTILE_SECRET_KEY`, and optional `BETTER_AUTH_API_KEY` or Stripe secrets. Public `TURNSTILE_SITE_KEY` is a Worker variable, not a secret. See the V2 auth Wrangler config for the exact bindings.

## Safe cutover

Before any live migration or auth deployment:

1. Back up the target V2 D1 database and review the two auth migrations.
2. Test migration and rollback/recovery locally.
3. Decide how existing users and passkeys will be re-enrolled or imported; no compatibility path is present in the V2-only codebase.
4. Verify the custom-domain route does not conflict with the existing public route.
5. Obtain explicit approval before applying remote migrations or deploying.

Organizations represent customer environments, not ownership of shared ontology objects. Private observations, links, dashboards, and other customer data must be authorized and scoped server-side; never expose them through a public cache.
