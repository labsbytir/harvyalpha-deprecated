# Host Harvy Social

The website is served by Python/Flask. All scraping runs through Spider Unlimited
and the server's optional Webshare proxy. No local browser is installed or used.

## Required server environment

- `SPIDER_API_KEY`: your Spider key.
- `WEBSHARE_PROXY_URL`: your Webshare endpoint (`http://user:password@host:port`).
  Optional; blank uses Spider's proxy network. URL-encode special characters in credentials.
- `HARVY_ACCESS_TOKEN`: a random workspace secret of at least 24 characters.
  Generate one with `python3 -c 'import secrets; print(secrets.token_urlsafe(32))'`.
- `HARVY_DATA_DIR`: writable, persistent output directory. Defaults to
  `data/web-jobs` beside the source; use `/app/data/web-jobs` in Docker.
- `HARVY_JOB_TIMEOUT`: local worker deadline in seconds; default 3600.
- `BUTTONDOWN_API_KEY`: optional server-side Buttondown token for user-initiated newsletter signups. Store it as a Worker secret, never in source or browser code. After rotating the exposed key, configure it with `npx wrangler secret put BUTTONDOWN_API_KEY`.
- `BASIN_INGEST_URL` / optional `BASIN_INGEST_TOKEN`: stream job JSON artifacts into Basin. See `../v2/health/BASIN.md`.
- Optional API credentials for the Legal & Mapping research page: `COURTLISTENER_API_TOKEN`, `CASELAW_API_TOKEN`, `DOCKETALARM_USERNAME`, `DOCKETALARM_PASSWORD`, `JUDYRECORDS_API_KEY`, and `MAPILLARY_ACCESS_TOKEN`. See `RESEARCH.md`.

Use the host's secret/environment settings. Provider keys never go in the HTML,
browser code, command arguments, or committed files. `.env.example` has no real
credentials. Python does not automatically load `.env` files.

The newsletter D1 consent audit table and account privacy timestamp require migration `0003_newsletter_privacy.sql`; review and back up the existing database before applying it.
The `Harvy` Buttondown segment is a saved filter over the `harvy` tag and should be created in the Buttondown account before promotion.

## Run locally

After setting the environment variables:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --no-input -r requirements.txt
.venv/bin/python web_app.py
```

Open `http://127.0.0.1:8903` yourself and enter the workspace access token.
The application does not open a browser automatically. No scraping request is
sent until a user submits a profile and checks the public-research acknowledgement.

## Production

Use a persistent Python web service or container host, not a short-lived serverless
function. For a Python service, use this start command behind the host's HTTPS proxy:

```bash
gunicorn --workers 1 --threads 4 --bind 0.0.0.0:$PORT 'web_app:create_app()'
```

For a container:

```bash
docker build -t harvy-social .
docker run --env-file .env -p 8000:8000 -v harvy-data:/app/data harvy-social
```

## Cloudflare Workers Deployment (harvybot.com)

The main app remains a Python Worker with edge static assets. Better Auth is a separate TypeScript Worker behind the `HARVY_AUTH` service binding.

1. Configure secrets on Cloudflare:
   ```bash
   npx wrangler secret put SPIDER_API_KEY
   npx wrangler secret put WEBSHARE_PROXY_URL
   npx wrangler secret put HARVY_ACCESS_TOKEN
   ```

2. Test deployment bundle:
   ```bash
   npx wrangler deploy --dry-run
   npx wrangler deploy --dry-run --config v2/auth/wrangler.jsonc
   ```

3. Deploy both Workers to production on `harvybot.com` (Better Auth stays disabled until `BETTER_AUTH_ENABLED` is deliberately turned on):
   ```bash
   npm run deploy
   ```

Route topology:
- `/` serves the public reconnaissance landing page.
- `/platform/` serves the interactive reconnaissance platform.
- `/research/` serves legal-source and geospatial searches.
- `/api/better-auth/*` is the staged auth route; it returns disabled until `BETTER_AUTH_ENABLED=true` and the auth secret is configured.
- `/static/*` served at edge speed via Workers Static Assets.

### Staged Better Auth service

Better Auth runs in a separate TypeScript Worker (`v2/auth/wrangler.jsonc`) using the existing D1 database. It remains disabled by default; `BETTER_AUTH_ENABLED` in the main `wrangler.jsonc` must stay `false` until provider configuration, D1 migration, privacy checks, and end-to-end tests are complete. `npm run deploy` builds assets, deploys `harvy-auth`, then deploys the main Worker.

Configure Better Auth secrets on `harvy-auth` using `--config v2/auth/wrangler.jsonc`; see [Better Auth operations](AUTH.md) for provider names and callback URLs. `TURNSTILE_SITE_KEY` is public configuration; `TURNSTILE_SECRET_KEY` is a secret. Better Auth Infrastructure (`BETTER_AUTH_API_KEY`) is separate from Buttondown and enables external email, dashboard, audit, and Sentinel services only when configured. Stripe remains a plugin-only integration until products/prices and webhook settings are supplied.

Provision the required secrets interactively (enter values at the Wrangler prompt; never place them in command arguments):

```sh
npx wrangler secret put BETTER_AUTH_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put BETTER_AUTH_API_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put GITHUB_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put GITHUB_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put GOOGLE_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put DISCORD_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put DISCORD_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put TWITTER_CLIENT_ID --config v2/auth/wrangler.jsonc
npx wrangler secret put TWITTER_CLIENT_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put TURNSTILE_SECRET_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put STRIPE_SECRET_KEY --config v2/auth/wrangler.jsonc
npx wrangler secret put STRIPE_WEBHOOK_SECRET --config v2/auth/wrangler.jsonc
npx wrangler secret put HARVY_ADMIN_USER_IDS --config v2/auth/wrangler.jsonc
```

Set public `TURNSTILE_SITE_KEY` under the auth Worker's variables. Keep `BETTER_AUTH_INFRA_ENABLED`, `BETTER_AUTH_EMAIL_ENABLED`, and `STRIPE_ENABLED` false until their accounts and flows are verified; keep `BETTER_AUTH_ENABLED` false on the main Worker until the complete cutover is tested. Never paste secret values in chat or commit them.

The Docker image listens on port 8000. Set the host's container port accordingly,
attach persistent storage to `/app/data`, and terminate HTTPS at the host/proxy.
`GET /health` is the health check. Do not expose the Flask development server publicly.

## Privacy, limits and deployment boundaries

- API access requires the workspace token. Each job also receives its own random
  token, required to view progress, cancel or download its files.
- No provider credentials or job tokens are stored in browser local/session storage.
  Keep the tab open until downloading; refreshing loses that tab's job token.
- Only one local scrape runs at a time, limiting upstream concurrency and account
  abuse. A second submission receives a busy response rather than joining a queue.
- **Use exactly one Gunicorn worker and one application instance.** Job metadata
  and authorization tokens are in memory. This is a small shared workspace, not
  a multi-instance job platform.
- Results remain on persistent disk, but a server restart loses live job metadata
  and client download access. Stop active jobs before deployments. The operator
  can recover files from `HARVY_DATA_DIR`; there is no automatic resume.
- The Stop button ends the local worker, not API requests Spider already received.
- Downloads include JSON only, not image/video binaries. Archives over 100 MB must
  be downloaded as individual files. The operator is responsible for retention
  and deleting old output when no longer needed.
- Job results are partial public snapshots. Read `manifest.json` for missing
  sections, pagination and scrolling limitations. Debra's full timeline remains unresolved.

Run checks with `python3 -m unittest discover -v`. No real API requests are made by tests.
