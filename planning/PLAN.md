# Harvy Unified Master Plan & Architectural Audit

*Consolidated from all prior planning documents on 2026-10-25 per AGENTS.md directives.*

---

## Part 1: Comprehensive Planning Audit & Contradictions

This audit resolves conflicting proposals across earlier planning documents, verified against the actual codebase implementation and project constraints.

### 1. Telegram Ingestion Architecture: Dedicated Queue vs Local CLI vs Workflows
- **Contradiction:**
  - `telegram-continuous-mining.md` proposed creating a new Cloudflare Queue `harvy-telegram` with DLQ and crontab refresh.
  - `telegram-vps-wiring.md` proposed the VPS polling this queue via REST and writing directly to D1, R2, and K2.
  - BUT `harvy-workflow-orchestration.md` and Rule #497/#504 state that Cloudflare Workflows and K2 will handle orchestration, while existing `HARVY_QUEUE` remains intact.
  - AND `telegram-history-scrape.md` explicitly bounded Telegram ingestion as a local authorized Telethon CLI tool (`data/telegram/@handle/`), ruling out cloud queue/ontology/R2 pipelines to avoid Telegram account bans and ToS violations.
- **Codebase Verification:**
  - `wrangler.jsonc` has no `harvy-telegram` queue.
  - `scrape/telegram.py` exists as a local CLI. Neither Telethon nor VPS daemon scripts exist in `requirements.txt` or `pyproject.toml`.
- **Resolution:**
  - Telegram history mining remains a **local authorized CLI** (`scrape/telegram.py`) dumping to local storage (`data/telegram/`). No dedicated Cloudflare queue or unvetted remote VPS poll daemon will be created until authorized.

### 2. VPS Scraper Connectivity vs Cloudflare Security Policy
- **Contradiction:**
  - `judyrecords-continuous-mining.md` and `telegram-vps-wiring.md` proposed exposing HTTP scraper endpoints on VPS and having VPS communicate back to D1 REST and R2 S3 endpoints.
  - BUT Project Rule #507 explicitly mandates: *"Use Cloudflare service bindings for internal Worker-to-runner communication (never expose public endpoints)."*
  - AND `scripts/judyrecords_scraper_service.py` runs an unauthenticated Flask server on `0.0.0.0:8787`.
- **Codebase Verification:**
  - Exposing plain HTTP endpoints on public IPs violates Rule #507.
- **Resolution:**
  - All inter-service communication must use Cloudflare Service Bindings or Cloudflare Access/mTLS with HMAC authentication tokens. No naked HTTP ports.

### 3. Spider Unlimited vs Metered/PAYG Endpoints
- **Contradiction:**
  - `telegram-mtproto-mining.md` cited legacy scripts falling back to Spider pay-as-you-go / Google search endpoints.
  - BUT Project Rule #435 and `AGENTS.md` Directive 1 explicitly state: *"Harvy uses Spider Unlimited endpoints (/unlimited/scrape, /unlimited/crawl, /unlimited/links) by default; never fall back to metered/PAYG without explicit approval."*
- **Codebase Verification:**
  - `scrape/client.py` correctly enforces `/unlimited/*` endpoints and blocks accidental PAYG usage.
- **Resolution:**
  - All collectors (social, legal, arrest) must exclusively use Spider Unlimited and Webshare residential proxy (`WEBSHARE_PROXY_URL`).

### 4. Better Auth Migration vs Active Production Auth
- **Contradiction:**
  - `better-auth-migration.md` outlined migrating to Better Auth in `auth/`, but some tasks assumed legacy auth could be retired immediately.
  - BUT `src/worker.py` currently powers all session and passkey verification in production with `BETTER_AUTH_ENABLED = False`.
  - Migrations `0005_better_auth.sql` and `0006_auth_privacy_consents.sql` have not been executed on remote D1 (Memory #451).
- **Codebase Verification:**
  - All 135 unit tests in `tests/` pass using the legacy auth contract in `src/worker.py`. The passkey account takeover vulnerability was fixed directly in `src/worker.py`.
- **Resolution:**
  - Better Auth remains staged in `auth/` behind the `HARVY_AUTH` service binding with `BETTER_AUTH_ENABLED=false`. Full cutover will occur only after explicit user confirmation, remote D1 migration, and user passkey re-enrollment.

### 5. Scraping V2 (TypeScript Worker) vs Production Python Collectors
- **Contradiction:**
  - `scraping-v2-roadmap.md` suggested moving scrapers to a TypeScript Worker pipeline in `scrape/v2/`.
  - BUT `AGENTS.md` and Memory #480 state: *"Keep the existing per-network social adapters and court/arrest research collectors working during V2 migration. `scrape/v2/` is experimental, not a production replacement."*
- **Codebase Verification:**
  - The live, battle-tested scrapers are in `scrape/` (Python), tested via `tests/test_x_scraper.py`, `tests/test_scrape_protocol.py`, etc.
- **Resolution:**
  - `scrape/v2/` removed from repo on 2026-10-26; it was experimental and never a production replacement. Production collection continues on Python modular adapters with Spider transport.

### 6. BI Dashboard Implementation: drizzle-cube vs Custom React MUI
- **Contradiction:**
  - `harvy-shared-ontology-query-nodes.md` proposed building a custom React MUI dashboard builder.
  - BUT Memory #502 shows that `drizzle-cube 0.12.2 AnalyticsDashboard` with 29 chart types is already bundled, while `ontology/query_engine.py` compiles server-side allowlisted SQL.
- **Codebase Verification:**
  - `query/src/App.tsx` compiles to `static/query-app.js`. `src/worker.py` provides `/api/query/catalog` and `/api/query/execute`.
- **Resolution:**
  - Leverage the allowlisted 7-metric catalog in `ontology/query_engine.py` and bind it cleanly to `drizzle-cube` without adding new frontend widget bloat.

### 7. Truth Social Scraping: Legacy Untruth Script vs Harvy Pipeline
- **Contradiction:**
  - Legacy `untruth/truth_social.py` fell back to Spider metered crawl (`SPIDER_METERED_CRAWL`) on 429, violating Rule #435/#522 (Spider Unlimited only).
  - Legacy script uploaded directly to Impossible Cloud S3 (`opentir-payloads`) instead of Harvy R2 and D1 ontology (violating Rule #527).
  - `scrape/profiles.py` parsed Mastodon/Truth Social statuses, but lacked a registered adapter module.
  - `scrape/protocol.py` returned raw `truthsocial.com` instead of normalized network `truthsocial`.
- **Codebase Verification:**
  - `untruth/truth_social.py` deleted; `scrape/profiles.py` had no `adapter_for("truthsocial")`.
  - `tests/test_social_profiles.py` tests Mastodon/Truth Social node extraction, but no adapter or protocol envelope was wired.
- **Resolution:**
  - Implement modular adapter `scrape/truthsocial.py` using strict Spider Unlimited (`/unlimited/scrape`) and Webshare proxy (`WEBSHARE_PROXY_URL`).
  - Wire into `adapter_for()` in `scrape/profiles.py` and normalize in `scrape/protocol.py`. Store raw payloads in R2 and index observations in D1.

---

## Part 2: Unified Master Plan

### Module 1: Core Platform & Shared Ontology
- **Canonical Deterministic URNs**: Objects use `urn:harvy:<type>:<source>:<native_id>`. Objects are shared canonical entities, not account-owned.
- **Multi-Tenant Scoping**: `effective_dataset = shared UNION current_environment`. Private annotations, links, and dashboards are strictly partitioned by `environment_id`.
- **Storage Tiering**:
  - **D1**: Operational indexing, object registry, links (`harvy_objects`, `harvy_observations`, `harvy_links`), and saved dashboards.
  - **R2**: Authoritative immutable raw scrape payloads and exports.
  - **Basin SQL (Iceberg)**: Analytical archive, historical observations over time, heavy aggregations (>30 days).
- **Nodes & Graph Visualizer**: WebGL graph visualization (`/nodes/`) with accessibility fallback, bounded to 2 hops / 100 nodes.
- **Query BI**: Curated server-side metric queries compiled to D1 (operational) or Basin SQL (historical).

### Module 2: Data Collection & Continuous Ingestion
- **Modular Adapters**: Dedicated extractors for Facebook, Instagram, Threads, X, Truth Social, and Web Discovery.
- **Legal & Public Records**: CourtListener, Case.law, JudyRecords, Arrests.org, and Docket Alarm via `scrape/research.py`.
- **JudyRecords Workflow**: Cloudflare Workflow `harvy_schedules` triggers 14-day continuous mining, leasing jobs and streaming updates into R2 and D1.
- **Telegram History Mining**: Local authorized Telethon CLI (`scrape/telegram.py`) checkpointing into `data/telegram/`.
- **Transport Constraints**: Strict usage of Spider Unlimited (`/unlimited/*`) and Webshare residential proxy (`WEBSHARE_PROXY_URL`). Never fall back to PAYG without authorization.

### Module 3: Authentication & Multi-Tenancy (Better Auth Staged)
- **Staged TypeScript Worker**: `auth/` running Better Auth 1.7.13 with Cloudflare D1 adapter, gated by `BETTER_AUTH_ENABLED=false`.
- **Legacy Fallback**: `src/worker.py` maintains verified passkey/token auth until migration approval.
- **Data Privacy**: Granular privacy consent gate (`migrations/0006_auth_privacy_consents.sql`).
- **Cutover Readiness**: Requires remote D1 migrations 0005/0006, secret provisioning (`BETTER_AUTH_SECRET`, OAuth credentials), and user passkey re-enrollment.

### Module 4: Workflow Orchestration & Caching
- **Cloudflare Workflows**: Unified `POST /api/workflows` authenticated envelope for durable execution.
- **Queue Preservation**: Existing `HARVY_QUEUE` remains active for social profile jobs; no breaking queue changes.
- **Edge Caching Target**: 75%+ cache hit rate on eligible public endpoints (`/static/*`, `/api/search`, `/api/nodes`, `/api/query/catalog`) using Cloudflare Workers Cache API, partitioned by environment.

---

## Part 3: Operational Tasks & Milestones

- [x] Consolidate all 11 planning documents into `planning/PLAN.md`.
- [x] Audit contradictions between plans and codebase implementation.
- [x] Clean static asset redundancy and remove duplicate nested files.
- [x] Reorganize test suite into `tests/` with 100% passing tests (135/135 green).
- [ ] Implement Truth Social modular adapter in `scrape/truthsocial.py` with strict Spider Unlimited + Webshare proxy.
- [ ] Maintain cache hit rate monitoring (>75%) for public endpoints.
- [ ] Await user authorization before remote D1 migrations or live Better Auth cutover.
- [ ] Connect Telegram continuous mining only upon VPS credential provisioning.
