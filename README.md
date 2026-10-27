# Harvy

<p align="center">
  <img src="static/harvy-github-banner.png" alt="Harvy" width="800">
</p>

<p align="center"><strong>Public-source research, evidence collection, and searchable case intelligence.</strong></p>

<p align="center">
  <a href="https://github.com/labsbytir/harvy/actions/workflows/ci.yml"><img alt="CI status" src="https://img.shields.io/github/actions/workflow/status/labsbytir/harvy/ci.yml?branch=main&style=for-the-badge&label=CI"></a>
  <img alt="Python 3.12+" src="https://img.shields.io/badge/Python-3.12%2B-3776AB?style=for-the-badge&logo=python&logoColor=white">
  <img alt="Cloudflare Workers" src="https://img.shields.io/badge/Cloudflare-Workers-F38020?style=for-the-badge&logo=cloudflare&logoColor=white">
  <img alt="TypeScript" src="https://img.shields.io/badge/TypeScript-5.8%2B-3178C6?style=for-the-badge&logo=typescript&logoColor=white">
  <img alt="React" src="https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black">
</p>

<p align="center">
  <a href="https://discord.gg/zcSM5Qy3tm"><img alt="Discord: Join Community" height="40" src="https://img.shields.io/badge/Discord-Join%20Community-5865F2?style=for-the-badge&logo=discord&logoColor=white"></a>
  <a href="https://buymeacoffee.com/tirlabs"><img alt="Buy Me a Coffee" height="40" src="https://img.shields.io/badge/Buy%20Me%20a%20Coffee-Support-FFDD00?style=for-the-badge&logo=buymeacoffee&logoColor=black"></a>
</p>

<p align="center"><a href="https://labsbytir.github.io/harvy/">Visit the project site ↗</a></p>

Harvy brings public-source collection, source evidence, and research workflows into one workspace. It preserves provenance and collection limits so observations can be reviewed in context rather than treated as verified identity claims.

## What it does

- Collects supported public profile, court, and research pages.
- Retains source artifacts in R2 and indexes operational records in D1.
- Provides research, query, and dossier interfaces over collected data.
- Includes Basin ingestion and historical analytics tooling.

The current production Worker is Python at `src/worker.py`; its profile path stores raw captures in R2 and search documents in D1. **Platform v2 is in development** under `platform-v2/`; its isolated connectors, Basin projectors, and supervisor are not yet deployed.

## Technology

**Current application:** Cloudflare Workers, D1, R2, Python, React, TypeScript, and Vite.

**Platform v2, in development:** Cloudflare Queues, Workflows, K2, Basin Pipelines, Workers Analytics Engine, and Workers Cache. These bindings/resources must be provisioned and verified before deployment.

## Build and test

```sh
npm ci
python3 -m pip install -e . -r requirements.txt
npm run build:templates
python3 -m unittest discover tests
npm run typecheck:platform-v2
npm run test:platform-v2
```

Template source lives in `templates/`, CSS source in `styles/`, scraper adapters in `scrape/`, and generated Worker assets in `static/`. Repository documentation lives in `notebooks/` and mirrors into the [harvy-docs](https://github.com/labsbytir/harvy-docs) repository with `npm run sync:harvy-docs`.

## Deployment

The production Worker is configured by `wrangler.jsonc`. Build generated assets with `npm run build:templates` before deploying. Provider credentials belong in Worker secrets, never in source or queue messages. See [Hosting](guides/HOSTING.md), [Scraping](guides/SCRAPING.md), [Research](guides/RESEARCH.md), and [Basin operations](health/BASIN.md).

Platform v2 has separate Wrangler configurations and resource placeholders. Do not deploy those configs until the v2 D1/KV/R2/Queue resources, K2 subscriptions, and secrets have been provisioned and reviewed.

## Privacy and provenance

Collectors preserve source URLs, timestamps, provenance, and known limitations. Harvy does not accept logged-in social-account cookies. Local scrape data and consent state are excluded from Git. See [Privacy](guides/PRIVACY.md) and [Acceptable Use](guides/ACCEPTABLE_USE.md).

The bundled username-check dataset includes its own attribution and license terms in `data/whatsmyname-LICENSE.md`. No project-wide license is declared yet.

## Community and support

Join the [Discord community](https://discord.gg/zcSM5Qy3tm), support development through [Buy Me a Coffee](https://buymeacoffee.com/tirlabs), or open an issue on [GitHub](https://github.com/labsbytir/harvy/issues). For safe troubleshooting details, see [Support](guides/SUPPORT.md).
