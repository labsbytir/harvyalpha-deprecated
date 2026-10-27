# Harvy Unified Master Plan & Architectural Audit

*Consolidated from all prior planning documents on 2026-10-25 per AGENTS.md directives.*

---

## Part 1: Comprehensive Planning Audit & Contradictions

This audit was consolidated on 2026-10-25. The codebase has changed since that snapshot; the dated corrections below supersede earlier claims when they conflict. Implementation, deployment, and capability verification remain separate statuses.

### Current status refresh — 2026-10-26

- **V1 remains production:** `src/worker.py`, root `wrangler.jsonc`, `scrape/`, `templates/`, and `static/` are the current app/runtime paths.
- **Platform v2 is additive and not deployed:** `platform-v2/` contains the supervisor, JudyRecords/Truth Social/SAM.gov connector code, projector, source catalog, queue/workflow contracts, and release manifests. Its remote resource IDs remain placeholders.
- **Dispatch design correction (2026-10-26, local only):** older v2 notes described one service binding and one Queue per connector; `platform-v2/supervisor/wrangler.jsonc` now declares one `V2_CONNECTORS` dispatch namespace and one `harvy-v2-work` Queue with DLQ. The supervisor's D1 registry (`platform-v2/migrations/0003_v2_connectors.sql`) gates new runs. This resolves the earlier `guides/ARCHITECTURE.md` claim that Workers for Platforms was deferred for customer code: operator-owned connectors also need runtime dispatch. Entitlement, dispatch-namespace Secrets Store bindings, migrations and delivery remain unverified, so this is implementation design, not deployed capability. See `guides/PLATFORM_V2_CONNECTORS.md`.
- **Connector status:** SAM.gov is implemented but disabled pending `SAM_GOV_API_KEY` and a verified sample query. Truth Social remains capability-gated. Imported directory, CMS, portal, social, bulk, and stream entries are catalog-only, not active feeds.
- **Validation:** GitHub CI passed 147 Python tests and TypeScript checks at commit `242b658`; no live v2 collection run, remote migration, or v2 deployment was performed.
- **Pages:** the public GitHub Pages site is live at `https://labsbytir.github.io/harvy/` and shows a roadmap plus recent commit history.

### 1. Telegram Ingestion Architecture: Dedicated Queue vs Local CLI vs Workflows
- **Contradiction:**
  - `telegram-continuous-mining.md` proposed creating a new Cloudflare Queue `harvy-telegram` with DLQ and crontab refresh.
  - `telegram-vps-wiring.md` proposed the VPS polling this queue via REST and writing directly to D1, R2, and K2.
  - BUT `harvy-workflow-orchestration.md` and Rule #497/#504 state that Cloudflare Workflows and K2 will handle orchestration, while existing `HARVY_QUEUE` remains intact.
  - AND `telegram-history-scrape.md` explicitly bounded Telegram ingestion as a local authorized Telethon CLI tool (`data/telegram/@handle/`), ruling out cloud queue/ontology/R2 pipelines to avoid Telegram account bans and ToS violations.
- **Historical verification (2026-10-25):** the earlier audit saw only the local Telethon CLI and no dedicated queue.
- **Current codebase verification (2026-10-26):** `requirements.txt:3` includes Telethon; `wrangler.jsonc:62-71` declares the `harvy-telegram` producer queue; `scripts/telegram_refresh.py:55-95` can enqueue; and `scripts/telegram_consumer.py:34-42,211-244` pulls from the Queue REST API and writes R2/D1 data. The systemd unit `scripts/telegram-consumer@.service:11` targets missing `scripts/telegram_consumer_loop.py`, and Wrangler has no `harvy-telegram` consumer binding.
- **Current resolution:** both local CLI and queue/VPS code paths exist, but end-to-end/continuous operation is not verified. Do not call it local-only or deployed; keep activation blocked until the service entrypoint, queue contract, credentials, and storage/ack path are reconciled and authorized.

### 2. VPS Scraper Connectivity vs Cloudflare Security Policy
- **Contradiction:** earlier proposals described a VPS HTTP bridge and treated the checked-in Flask bridge as unauthenticated.
- **Current codebase verification:** `scripts/judyrecords_scraper_service.py:20-23` compares `Authorization: Bearer …` against `JUDY_SCRAPER_TOKEN` with `hmac.compare_digest`. The checked-in module does not specify a listener host/port, so the prior claim that it binds `0.0.0.0:8787` is not verified from this file.
- **Resolution:** retain the token check and use service bindings for Worker-to-Worker calls. Verify the actual VPS listener/firewall configuration before claiming the bridge is publicly exposed or safely isolated.

### 3. Spider Unlimited vs Metered/PAYG Endpoints
- **Contradiction:**
  - `telegram-mtproto-mining.md` cited legacy scripts falling back to Spider pay-as-you-go / Google search endpoints.
  - BUT Project Rule #435 and `AGENTS.md` Directive 1 explicitly state: *"Harvy uses Spider Unlimited endpoints (/unlimited/scrape, /unlimited/crawl, /unlimited/links) by default; never fall back to metered/PAYG without explicit approval."*
- **Codebase Verification:**
  - `v1/scrape/client.py` correctly enforces `/unlimited/*` endpoints and blocks accidental PAYG usage.
- **Resolution:**
  - Use Spider Unlimited and `WEBSHARE_PROXY_URL` by default for web-page collection. Documented first-party APIs such as SAM.gov may be called directly with their own scoped credential and pagination limits. Never fall back to Spider PAYG without explicit authorization.

### 4. Better Auth Migration vs Active Production Auth
- **Contradiction:**
  - `better-auth-migration.md` outlined migrating to Better Auth in `v2/auth/`, but some tasks assumed legacy auth could be retired immediately.
  - BUT `src/worker.py` currently powers all session and passkey verification in production with `BETTER_AUTH_ENABLED = False`.
  - Migrations `0005_better_auth.sql` and `0006_auth_privacy_consents.sql` have not been executed on remote D1 (Memory #451).
- **Codebase Verification:**
  - The legacy auth contract remains in `src/worker.py`; Better Auth remains disabled. The latest GitHub CI run passed 147 Python tests plus TypeScript/auth checks at commit `242b658`; remote migration/cutover status still requires separate verification.
- **Resolution:**
  - Better Auth remains staged in `v2/auth/` behind the `HARVY_AUTH` service binding with `BETTER_AUTH_ENABLED=false`. Full cutover will occur only after explicit user confirmation, remote D1 migration, and user passkey re-enrollment.

### 5. `scrape/v2/` Experiment vs Platform v2
- **Contradiction:**
  - `scraping-v2-roadmap.md` suggested moving scrapers to a TypeScript Worker pipeline in `v1/scrape/v2/`.
  - BUT `AGENTS.md` and Memory #480 state: *"Keep the existing per-network social adapters and court/arrest research collectors working during V2 migration. `v1/scrape/v2/` is experimental, not a production replacement."*
- **Codebase Verification:**
  - The live, battle-tested scrapers are in `v1/scrape/` (Python), tested via `tests/test_x_scraper.py`, `tests/test_scrape_protocol.py`, etc.
- **Resolution:**
  - `scrape/v2/` was removed; it is not the same project as the separate `platform-v2/` supervisor/connector scaffold. Production collection remains on the Python adapters. Platform v2 source exists but is not deployed.

### 6. BI Dashboard Implementation: drizzle-cube vs Custom React MUI
- **Contradiction:**
  - `harvy-shared-ontology-query-nodes.md` proposed building a custom React MUI dashboard builder.
  - BUT Memory #502 shows that `drizzle-cube 0.12.2 AnalyticsDashboard` with 29 chart types is already bundled, while `ontology/query_engine.py` compiles server-side allowlisted SQL.
- **Codebase Verification:**
  - `v2/graph/src/App.tsx` compiles to `static/query-app.js`. `src/worker.py` provides `/api/query/catalog` and `/api/query/execute`.
- **Resolution:**
  - Leverage the allowlisted 7-metric catalog in `ontology/query_engine.py` and bind it cleanly to `drizzle-cube` without adding new frontend widget bloat.

### 7. Truth Social Scraping: Legacy Untruth Script vs Harvy Pipeline
- **Contradiction:**
  - Legacy `untruth/truth_social.py` fell back to Spider metered crawl (`SPIDER_METERED_CRAWL`) on 429, violating Rule #435/#522 (Spider Unlimited only).
  - Legacy script uploaded directly to Impossible Cloud S3 (`opentir-payloads`) instead of Harvy R2 and D1 ontology (violating Rule #527).
  - `v1/scrape/profiles.py` parsed Mastodon/Truth Social statuses, but lacked a registered adapter module.
  - `v1/scrape/protocol.py` returned raw `truthsocial.com` instead of normalized network `truthsocial`.
- **Codebase Verification:**
  - V1 `scrape/truthsocial.py` is registered by `scrape/profiles.py:333-348` and has local parser/protocol tests.
  - A separate TypeScript connector exists in `platform-v2/truthsocial/`; its supervisor registry keeps it disabled until Spider Unlimited social-domain capability is verified.
- **Resolution:**
  - Mark the V1 adapter implementation complete; do not equate code presence with live capability. Keep the v2 connector disabled until capability, source access, and privacy checks pass. Preserve source attribution and public-only limitations.

### 8. Storage Tiering: Single Overloaded Bucket vs Separated R2 & Basin Lakehouse
- **Contradiction:**
  - Early v2 scaffold and `health/BASIN.md:11` allowed pointing Basin Catalog at an arbitrary bucket or sharing a single bucket (`harvy-platform-v2`) for raw crawl dumps, parsed records, release manifests, and the Basin Iceberg sink.
  - BUT Apache Iceberg catalogs require strict snapshot and file-level integrity. Applying S3 lifecycle expiration (TTL) to purge raw scrape dumps in a shared bucket corrupts Iceberg table metadata by deleting underlying Parquet files.
- **Codebase Verification:**
  - `platform-v2/projector/src/index.ts:82,97` forwards events to `V2_BASIN_STREAM` while connectors write raw JSON to `V2_BUCKET`. In the root `wrangler.jsonc:48-60`, separate buckets (`harvy`, `harvy-map-data`, `harvy-logs`) already exist for v1.
- **Resolution:**
  - Enforce the 3-tier storage architecture: `harvy-raw` (ephemeral scrape payloads, TTL 60–90d), `harvy-artifacts` (normalized records, release manifests, permanent), and `harvy-warehouse` (managed exclusively by Basin Pipelines & Catalog; queried via Basin SQL; no direct Worker R2 writes, no manual S3 TTL).

---

## Part 2: Unified Master Plan

### Module 1: Core Platform & Shared Ontology
- **Canonical Deterministic URNs**: Objects use `urn:harvy:<type>:<source>:<native_id>`. Objects are shared canonical entities, not account-owned.
- **Multi-Tenant Scoping**: `effective_dataset = shared UNION current_environment`. Private annotations, links, and dashboards are strictly partitioned by `environment_id`.
- **Storage Tiering (3-Tier Standard)**:
  - **D1**: Operational indexing, object registry, links (`harvy_objects`, `harvy_observations`, `harvy_links`), connector registration, and saved dashboards.
  - **R2 Raw Lake (`harvy-raw` / `harvy-v2-raw`)**: Ephemeral raw crawl captures, spider bodies, API JSON dumps. Direct key-value `put`/`get`. Safe for S3 lifecycle expiration (TTL 60–90 days).
  - **R2 Artifact Store (`harvy-artifacts` / `harvy-v2-artifacts`)**: Immutable normalized entities, dossiers, and release manifests (`manifest.json`). Long-term retention, served to user downloads.
  - **Basin Warehouse (`harvy-warehouse` / `harvy-v2-warehouse`)**: Managed exclusively by Basin Pipelines and Basin Catalog. Stores Apache Iceberg metadata snapshots and columnar Parquet tables. Ingested via streaming `send()`, queried via distributed Basin SQL. Never apply S3 TTL.
- **Nodes & Graph Visualizer**: WebGL graph visualization (`/nodes/`) with accessibility fallback, bounded to 2 hops / 100 nodes.
- **Query BI**: Curated server-side metric queries compiled to D1 (operational) or Basin SQL (historical).

### Module 2: Data Collection & Continuous Ingestion
- **Modular Adapters**: Dedicated extractors for Facebook, Instagram, Threads, X, Truth Social, and Web Discovery.
- **Legal & Public Records**: CourtListener, Case.law, JudyRecords, Arrests.org, and Docket Alarm via `scrape/research.py`.
- **JudyRecords Workflow**: V1 `src/worker.py` routes authenticated `/api/workflows` calls through the `HARVY_WORKFLOWS` service binding. The bound workflow source is not in this repository; verify its remote schedule/run status before treating continuous mining as active.
- **Telegram History Mining**: the authorized Telethon CLI and a separate v1 Queue/VPS path both exist. The Queue consumer systemd unit points to a missing module, so continuous operation is unverified and remains blocked pending reconciliation.
- **Transport Constraints**: Strict usage of Spider Unlimited (`/unlimited/*`) and Webshare residential proxy (`WEBSHARE_PROXY_URL`). Never fall back to PAYG without authorization.

### Module 3: Authentication & Multi-Tenancy (Better Auth Staged)
- **Staged TypeScript Worker**: `v2/auth/` running Better Auth 1.7.13 with Cloudflare D1 adapter, gated by `BETTER_AUTH_ENABLED=false`.
- **Legacy Fallback**: `src/worker.py` maintains verified passkey/token auth until migration approval.
- **Data Privacy**: Granular privacy consent gate (`migrations/0006_auth_privacy_consents.sql`).
- **Cutover Readiness**: Requires remote D1 migrations 0005/0006, secret provisioning (`BETTER_AUTH_SECRET`, OAuth credentials), and user passkey re-enrollment.

### Module 4: Workflow Orchestration & Caching
- **Cloudflare Workflows**: V1 `POST /api/workflows` routes through the configured service binding; the executor implementation is outside this repository.
- **Queue Preservation**: root `wrangler.jsonc` declares the `HARVY_QUEUE` binding and the worker sends jobs to it; remote queue/consumer health must be verified before claiming active operation.
- **Edge Caching Target**: 75%+ cache hit rate on eligible public endpoints (`/static/*`, `/api/search`, `/api/nodes`, `/api/query/catalog`) using Cloudflare Workers Cache API, partitioned by environment.

### Module 5: Central Connector Secrets (Cloudflare Secrets Store MVP)
- **Central storage**: Store provider credentials once in the account-level Cloudflare Secrets Store, not as duplicated per-Worker secrets or source-code values.
- **Worker access**: Each connector gets a minimal `secrets_store_secrets` binding in its Wrangler configuration and reads the value with `await env.<binding>.get()`. The binding is configuration, not a copy of the credential.
- **Scope**: Attach secret bindings only to approved Workers (`workers` scope alone is not per-Worker access control); keep credentials in the connector that makes the external request. Do not proxy provider credentials through the supervisor.
- **MVP**: Start with `SPIDER_API_KEY` and `WEBSHARE_PROXY_URL` for the v2 JudyRecords connector. Add other provider secrets only when a connector is approved.
- **Rotation**: Rotate the account-level secret in Secrets Store; redeploy only if Cloudflare requires binding metadata refresh. Never place secret values in Git, Wrangler vars, notebooks, logs, or plans.
- **Boundary**: Cloudflare One Access, Tunnel, and mTLS secure access to applications and networks; they do not automatically inject API credentials into Workers and are not required for this secrets MVP.

### Module 6: Documentation Site Deployment (Quartz 5 + Cloudflare Pages)
- **Docs Builder**: Quartz 5 with Blackbird dark theme (`@quartz-themes/core`), hosted at [labsbytir/harvy-docs](https://github.com/labsbytir/harvy-docs).
- **Deployment**: Native Cloudflare Pages Git connection (`harvy-docs`), serving custom domain `developers.harvybot.com`.
- **Sync Workflow**: `.github/workflows/deploy-docs.yml` triggers on documentation changes in `guides/` and `health/BASIN.md`, synchronizing content into `harvy-docs`.
- **Interactive Features**: Giscus discussion-backed comments on documentation pages, dynamic GitHub repository statistics, commit history tracker, and Harvy overview embed.

---

## Part 3: Operational Tasks & Milestones

- [x] Consolidate all 11 planning documents into `docs/PLAN.md`.
- [x] Audit contradictions between plans and codebase implementation.
- [x] Clean static asset redundancy and remove duplicate nested files.
- [x] Reorganize test suite into `tests/`; the latest CI run passed 147 Python tests (commit `242b658`).
- [x] Implement and register the V1 Truth Social adapter in `scrape/truthsocial.py`; keep v2 activation gated on provider capability verification.
- [x] Add the Platform v2 connector catalog and SAM.gov API connector scaffold; SAM.gov remains disabled pending a secret and bounded sample verification.
- [x] Publish the GitHub Pages project pitch, roadmap, and recent-commit changelog.
- [x] Deploy Quartz 5 docs site with Blackbird theme and Giscus to Cloudflare Pages at developers.harvybot.com connected to labsbytir/harvy-docs; add documentation sync GitHub Action.
- [ ] Maintain cache hit rate monitoring (>75%) for public endpoints.
- [ ] Await user authorization before remote D1 migrations or live Better Auth cutover.
- [ ] Reconcile the Telegram Queue consumer and systemd entrypoint; verify a safe end-to-end run before enabling continuous processing.
- [x] Add the JudyRecords v2 Secrets Store bindings and secret lookup; account provisioning, store ID replacement, and deployment remain pending.
- [ ] Create account-level Secrets Store entries and bind them only to approved v2 connectors; verify secret scope and rotation before deployment.

---

## Part 4: Documentation Mirror and Cloudflare Deployment Plan (2026-10-26)

**Documentation rule (Harvy-docs):** repository documentation lives in `notebooks/` and is mirrored into the `harvy-docs` repository with `npm run sync:harvy-docs` (`scripts/sync_docs_repo.py`, shared with `.github/workflows/deploy-docs.yml`; target `HARVY_DOCS_REPO` or `--dest`, default `/Users/pen/Documents/harvy-docs`). Repository files are canonical and the mirror is regenerated, never edited in place.

### Deployment plan (execute once the code is pushed)

1. **Pre-push gate** on the deploy commit: `npm run build:templates`, `python3 -m unittest discover tests`, `npm run typecheck:platform-v2`, `npm run test:platform-v2`. The last recorded CI pass (147 tests) is at `242b658`, which predates the pending work — re-verify on the new commit.
2. **Commit and push** the pending tree (29 files: storage-tier standardization, dispatch-based v2 supervisor, JudyRecords bulk runner). Push and deploy require explicit user authorization.
3. **Docs publish themselves on push:** pushing `harvy` main with `guides/**`, `health/BASIN.md` or `notebooks/**` changes runs `.github/workflows/deploy-docs.yml`, which syncs `content/` into `labsbytir/harvy-docs` and pushes it; that push is configured to trigger the Cloudflare Pages build of the Quartz docs site (the Pages project for `developers.harvybot.com` is recorded complete in the task log but is not verified here). Locally, `npm run sync:harvy-docs` (same `scripts/sync_docs_repo.py`) refreshes the mirror without pushing.
4. **Secrets** on the production Worker must already exist and stay out of source, logs, and screenshots: `SPIDER_API_KEY`, `WEBSHARE_PROXY_URL`, `HARVY_ACCESS_TOKEN`, plus the optional research/newsletter keys listed in `guides/HOSTING.md`.
5. **Dry-run both bundles** (`guides/HOSTING.md`), then `npm run deploy`: it builds templates, deploys the staged auth Worker (`BETTER_AUTH_ENABLED` stays `false`), and deploys the Python Worker `src/worker.py` on the `harvybot.com/*` routes.
6. **Post-deploy verification:** `GET /health`, smoke `/`, `/platform/`, `/research/`, `/static/*`; measure the cache hit rate on eligible public endpoints and hold the >=75% target (Module 4) without caching private data; scan Worker logs for secret leakage.
7. **Platform v2 is out of scope** for this deployment: its Wrangler configs still carry placeholder resource IDs and unverified entitlements (`guides/PLATFORM_V2_CONNECTORS.md`, `notebooks/platform-v2-first-five.md`). Provisioning, migrations 0001-0003, Secrets Store bindings, and the first bounded run remain on the task list.

### Contradiction audit for this plan (verified in the codebase 2026-10-26)

- `README.md:22` and `README.md:24` duplicated the project-site link; the duplicate is removed with this change.
- Two docs-sync scripts existed: `scripts/sync_docs_repo.py` (wired into `deploy-docs.yml`, copies `guides/` + `health/BASIN.md` into the Quartz `content/` tree) and `scripts/sync_harvy_docs.py` (notebooks mirror into top-level `notebooks/`). They are reconciled into `scripts/sync_docs_repo.py`, which now also copies `notebooks/` to `content/notebooks/`; the redundant script is removed.
- `deploy-docs.yml` did not trigger on `notebooks/**`, so notebook edits never reached the docs site; the paths filter now includes it. Quartz renders `content/` only, so a top-level `notebooks/` mirror would never have been published.
- `guides/HOSTING.md:1-3,43-47` describes a Flask/gunicorn service deployment while `README.md:35` and `wrangler.jsonc:5` (`main: src/worker.py`, routes at `wrangler.jsonc:11-18`) make the Cloudflare Worker the hosted app. Both paths exist (`web_app.py` and `src/worker.py`); this plan deploys the Worker path only.
- Part 1 section 8 and Module 1 set the 3-tier bucket names `harvy-raw` / `harvy-artifacts` / `harvy-warehouse`, but root `wrangler.jsonc:48-60` still binds `harvy`, `harvy-map-data`, `harvy-logs`. The standardization work changed guidance, not deployed bucket names; this plan does not rename buckets — data migration is a separate, reviewed step.
- The status refresh above cites CI at `242b658`; that is stale for the pending tree, so treat validation as unverified until step 1 passes; the local suite at this reconciliation reports 160 tests passing.
- `wrangler.jsonc:62-71` declares the `harvy-telegram` producer queue with no consumer binding, matching the unresolved status in Part 1 section 1; continuous Telegram ingestion stays disabled.
