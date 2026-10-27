# V2 Hosting and Deployment

All Worker configurations are explicit files under `v2/`; there is no root Worker configuration or one-shot deployment. Do not run `wrangler deploy` without `--config`.

## Local verification

```sh
npm ci
npm run build:templates
npm run typecheck:v2
npm run test:v2
python3 -m unittest discover tests
npx wrangler deploy --dry-run --config v2/supervisor/wrangler.jsonc
npx wrangler deploy --dry-run --config v2/catalog/connectors/judyrecords/wrangler.jsonc
npx wrangler deploy --dry-run --config v2/catalog/connectors/truthsocial/wrangler.jsonc
npx wrangler deploy --dry-run --config v2/catalog/connectors/sam-gov/wrangler.jsonc
npx wrangler deploy --dry-run --config v2/auth/wrangler.jsonc
```

## Deployment

Deploy connector Workers before the supervisor so direct service bindings resolve. Use the corresponding explicit npm script (`deploy:judyrecords`, `deploy:truthsocial`, `deploy:sam-gov`, `deploy:supervisor`, or `deploy:auth`) only after config review and explicit deployment approval. This code refactor did not deploy Workers, run remote migrations, or alter account settings.

Required values are supplied through the existing Cloudflare Secrets Store or Worker secrets. Names include `SPIDER_API_KEY`, `WEBSHARE_PROXY_URL`, `V2_CONNECTOR_TOKEN`, `V2_SUPERVISOR_TOKEN`, and source-specific keys. Never copy secret values into vars, docs, notebooks, logs, screenshots, or command arguments. See [V2 connector operations](V2_CONNECTORS.md) and [authentication operations](AUTH.md).

## Public site and routes

The retired root Worker implementation is removed from the repository. The V2 supervisor is an API Worker and does not serve the static site. `pages/`, `styles/`, and `v2/portal/` build assets into `static/`, but a V2 site Worker and query API routes are not implemented yet. Do not switch the public catch-all route or claim the public site is on V2 until that replacement is built and verified.

The V2 auth config defines the `/api/better-auth/*` custom-domain route and targets the V2 D1 database. Its migration has not been applied remotely; existing account data was not migrated. Review route precedence, schema, backup, and account recovery before any auth deployment or migration.

## Storage and caching

Keep raw captures in `harvy-raw`, normalized records and manifests in `harvy-artifacts`, and historical analytics in Basin. Do not combine the R2 buckets or apply raw-object lifecycle rules to Basin-managed data. Cache only scope-safe public responses; measure the 75% target on representative eligible traffic before reporting it.
