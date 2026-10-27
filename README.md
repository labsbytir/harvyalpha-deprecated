# Harvy

<p align="center">
  <img src="static/harvy-github-banner.png" alt="Harvy" width="800">
</p>

<p align="center"><strong>Public-source collection, evidence, and research workflows.</strong></p>

<p align="center">
  <a href="https://github.com/labsbytir/harvy/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/labsbytir/harvy/ci.yml?branch=main&style=for-the-badge&label=CI"></a>
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.8%2B-3178C6?style=for-the-badge&logo=typescript&logoColor=white">
  <img alt="Cloudflare Workers" src="https://img.shields.io/badge/Cloudflare-Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white">
</p>

<p align="center"><a href="https://labsbytir.github.io/harvy/">Visit the project site ↗</a></p>

Harvy preserves source URLs, timestamps, provenance, and collection limitations so findings can be reviewed in context rather than treated as verified identity claims.

## What it does

- Runs bounded, explicitly registered source connectors.
- Stores raw captures in R2 and normalized artifacts separately.
- Uses D1 for operational state and Basin for historical analytics.
- Provides static research and dossier interfaces; their V2 API routes must be verified before use.

The supported implementation is V2 under `v2/`. Connector Workers, supervisor, portal shell, shared contracts, migrations, and Wrangler configurations are maintained there. `pages/` and `styles/` are source for generated static assets in `static/`.

## Build and test

```sh
npm ci
npm run build:templates
python3 -m unittest discover tests
npm run typecheck:v2
npm run test:v2
npm run test:auth-consent
```

## Deploy

Each Worker has its own Wrangler configuration and explicit deployment script: `deploy:auth`, `deploy:judyrecords`, `deploy:truthsocial`, `deploy:sam-gov`, and `deploy:supervisor`. These commands make live Cloudflare changes; review the target config and get deployment approval before running them. Remote D1 migrations are separate and require a backup and explicit approval.

See [V2 connectors](docs/V2_CONNECTORS.md), [authentication](docs/AUTH.md), [hosting](docs/HOSTING.md), [support](docs/SUPPORT.md), [privacy](docs/PRIVACY.md), [terms](docs/TERMS.md), and [Basin operations](v2/health/BASIN.md). The single project plan is [docs/PLAN.md](docs/PLAN.md).

Repository docs live in `docs/` and operational notebooks in `notebooks/`. The repositories are canonical; sync them with `npm run sync:vault-guides` and `npm run sync:harvy-docs` respectively.

The bundled username-check dataset includes attribution and license terms in `v2/data/whatsmyname-LICENSE.md`. No project-wide license is declared.
