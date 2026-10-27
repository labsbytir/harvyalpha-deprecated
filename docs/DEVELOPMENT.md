# Harvy Development Workflow

## Repository layout

The active repository root is `/Users/pen/Documents/harvy`.

- `pages/`: HTML and TypeScript dossier renderer source
- `styles/`: canonical CSS source
- `static/`: generated Worker assets and static example data
- `v1/scrape/`: network adapters, shared Spider transport, and internal job protocol
- `v2/proxy/`: the shared `WEBSHARE_PROXY_URL` lookup/validation helper for local environment and Worker secret bindings
- `v2/scripts/`: build, documentation sync, catalog import, and manual operations tools; `src/` symlinks point to `v1/scrape/`, `v2/proxy/`, and `v2/ontology/`
- `v1/scripts/telegram_consumer.py`: the legacy queue consumer targeted by `v2/scripts/telegram-consumer@.service`
- `v2/health/`: Basin storage, schema, backfill, and operations docs
- `migrations/`: D1 migrations

## Local checks

```sh
uv sync --frozen
npm install
npm run build:templates
.venv/bin/python3 -m unittest discover -s . -p 'test_*.py'
npx wrangler deploy --dry-run
```

`npm run deploy` rebuilds templates and performs a live deployment. Review the diff and dry-run before deploying. Remote D1 migrations require a backup and explicit review.

## Conventional Commits and releases

Use `type(scope): summary`, such as `feat(query): add saved dashboards` or `fix(search): cap result count`. Husky runs Commitlint for local commits; GitHub Actions checks commit messages and pull-request titles.

This clone uses `.gitmessage` as its commit template. Before tagging `vX.Y.Z`, run `npm run changelog`, review `CHANGELOG.md`, and commit the reviewed release notes. Existing pre-adoption history is intentionally not rewritten. To make the remote check mandatory, enable the Commit message lint status check in `main` branch protection.

## Secrets and data

Use Wrangler secrets for Worker credentials. Never commit `.env`, `.dev.vars`, `consent.json`, or raw scrape data. Keep provider credentials out of browser requests and command arguments. Basin setup and ingestion details are documented in [Basin operations](../v2/health/BASIN.md).

## Obsidian guide mirror

The project notebook lives at `/Users/pen/Documents/Notes/harvy`. After editing a file in `docs/` or `v2/health/BASIN.md`, run `npm run sync:vault-guides` to refresh the copies in its `Guides/` folder. Repository files remain canonical.

Better Auth is implemented as a staged TypeScript Worker behind the Python Worker service binding. It remains disabled by default; keep legacy auth available until provider configuration, D1 migration, and end-to-end tests are complete. See [Better Auth operations](AUTH.md) and [the migration plan](PLAN.md).
