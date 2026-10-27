# Harvy Development Workflow

## Repository layout

The active repository root is `/Users/pen/Documents/harvy`.

- `templates/`: HTML and TypeScript dossier renderer source
- `styles/`: canonical CSS source
- `static/`: generated Worker assets and static example data
- `scrape/`: network adapters, shared Spider transport, and internal job protocol
- `proxy/`: the shared `WEBSHARE_PROXY_URL` lookup/validation helper for local environment and Worker secret bindings
- `health/`: Basin storage, schema, backfill, and operations docs
- `migrations/`: D1 migrations
- `platform-v2/`: additive supervisor and connector scaffold; separate resources, not deployed with V1

## Local checks

```sh
npm ci
python3 -m pip install -e . -r requirements.txt
npm run build:templates
python3 -m unittest discover tests
npm run typecheck:platform-v2
npm run test:platform-v2
python3 scripts/build_github_pages.py --output _site
npx wrangler deploy --dry-run
```

`npm run deploy` rebuilds templates and performs a live deployment. Review the diff and dry-run before deploying. Remote D1 migrations require a backup and explicit review.

## Conventional Commits and releases

Use `type(scope): summary`, such as `feat(query): add saved dashboards` or `fix(search): cap result count`. Husky runs Commitlint for local commits; GitHub Actions checks commit messages and pull-request titles.

This clone uses `.gitmessage` as its commit template. Before tagging `vX.Y.Z`, run `npm run changelog`, review `CHANGELOG.md`, and commit the reviewed release notes. Existing pre-adoption history is intentionally not rewritten. To make the remote check mandatory, enable the Commit message lint status check in `main` branch protection.

## Secrets and data

Use Wrangler secrets for Worker credentials. Never commit `.env`, `.dev.vars`, `consent.json`, or raw scrape data. Keep provider credentials out of browser requests and command arguments. Basin setup and ingestion details are documented in [Basin operations](../health/BASIN.md).

## Obsidian guide mirror

The project notebook lives at `/Users/pen/Documents/Notes/harvy`. After editing a file in `guides/` or `health/BASIN.md`, run `npm run sync:vault-guides` to refresh the copies in its `Guides/` folder. Repository files remain canonical.

## Documentation deployment

Documentation is authored in `guides/` and `health/BASIN.md`. Changes pushed to `main` trigger `.github/workflows/deploy-docs.yml`, which syncs documentation into [labsbytir/harvy-docs](https://github.com/labsbytir/harvy-docs). Cloudflare Pages builds the site using Quartz 5 and the Blackbird theme via native GitHub integration, deploying to `https://developers.harvybot.com`.

Better Auth is implemented as a staged TypeScript Worker behind the Python Worker service binding. It remains disabled by default; keep legacy auth available until provider configuration, D1 migration, and end-to-end tests are complete. See [Better Auth operations](AUTH.md) and the consolidated plan in `planning/PLAN.md`.
