# V2 Development Workflow

## Repository layout

- `v2/`: supervisor, connectors, portal shell, shared contracts, authentication, migrations, and operational scripts.
- `tests/`: Python tests for V2 tooling and shared logic; `v2/tests/`: Worker contract tests.
- `pages/`, `styles/`, `static/`: static source, canonical CSS, and generated assets.
- `docs/`: operator, developer, API, support, and planning documentation.
- `notebooks/`: operational notes mirrored to the documentation repository.

Do not add a root legacy Worker, compatibility symlink, or alternate V2 directory.

## Local checks

```sh
npm ci
npm run build:templates
python3 -m unittest discover tests
npm run typecheck:v2
npm run test:v2
npm run test:auth-consent
```

`npm run build:templates` typechecks and builds the V2 auth client, graph bundle, and static pages. Python tests use the standard library; `requirements.txt` contains the optional NudeNet prescan dependency for local media-safety workflows.

For a local D1 migration test, use `--local` and the V2 Wrangler config. Never use `--remote` without an explicit backup and approval.

## Deployment boundaries

Each Worker has an explicit Wrangler config under `v2/`. The `deploy:*` npm scripts make live Cloudflare changes; dry-run the specific config and obtain approval before running them. Remote database migrations are separate from Worker deployment. Do not claim a source collection or full coverage from a dry run, typecheck, health response, or single-record sample.

## Documentation mirrors

Repository files are canonical. Run `npm run sync:vault-guides` to refresh the Obsidian guide mirror and `npm run sync:harvy-docs` to refresh the `notebooks/` mirror. Do not edit the generated mirrors directly.
