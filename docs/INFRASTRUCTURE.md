# Harvy V2 Cloudflare Infrastructure Map

**Repository:** `/Users/pen/Documents/harvy`
**Created:** October 2026
**Status:** Current as of Harvy V2 implementation

---

## 🌐 Cloudflare Account Overview

**Account Name:** labsbytir
**Platform:** Cloudflare Workers, D1, R2, Basin

---

## 🏗️ Infrastructure Components

### 1. Cloudflare Workers Platform

#### Active Workers & Bindings

| Component | Location | Purpose | Binding Type | Status |
|-----------|----------|---------|--------------|--------|
| **Supervisor** | `v2/supervisor/` | Orchestrates connectors, manages runs, handles queue consumption, exposes progress API, generates release manifests | Direct binding to connectors | ✅ Active |
| **JudyRecords Connector** | `v2/catalog/connectors/judyrecords/` | Discovers and processes court records from JudyRecords API | Direct binding to Supervisor | ✅ Active |
| **TruthSocial Connector** | `v2/catalog/connectors/truthsocial/` | Discovers and processes TruthSocial posts | Direct binding to Supervisor | ✅ Active |
| **SAM.gov Connector** | `v2/catalog/connectors/sam-gov/` | Discovers and processes SAM.gov contract data | Direct binding to Supervisor | ⚠️ Code exists, not currently bound |
| **Better Auth** | `v2/auth/` | Authentication and authorization service using Better Auth | Standalone Worker | ✅ Active (local config only) |

**Key Constraint:** Direct bindings used due to Cloudflare account restrictions preventing Workers for Platforms dispatch namespaces.

---

### 2. Cloudflare D1 Databases

#### Active Instances

| Instance | Location | Purpose | Status |
|----------|----------|---------|--------|
| **V2 D1** | `v2/migrations/` | Primary operational database for V2 platform | ✅ Active |

**Schema Includes:**
- ontology_objects
- observations
- links
- dashboard_definitions
- runs
- work_items
- registrations

**Migration:** `0006_ontology_and_dashboards.sql` defines shared canonical objects


---

### 3. Cloudflare R2 Storage Buckets

#### Active Buckets (Critical!)

| Bucket | Purpose | Expiry Policy | Status | Risk Level |
|--------|---------|---------------|--------|------------|
| **harvy-raw** | Raw response artifacts (HTML, JSON) from connectors | 60-day automatic cleanup | ✅ Active | Low |
| **harvy-artifacts** | Normalized records, release manifests, page manifests, source HTML sidecars | **PERMANENT** | ✅ Active | **🔴 CRITICAL: Do NOT delete** |

**Artifact Details:**
- Source HTML stored as `.source.html` sidecars
- SHA256 checksums for data integrity
- `complete` field reflects parser coverage status

---

### 4. Cloudflare Basin

#### Active Resources

| Resource | Purpose | Status | Configuration |
|----------|---------|--------|---------------|
| **harvyql_stream** | Ingestion path for analytics data | ✅ Active | ID: `e1e54007204f43768769ee613369c85f` |
| **harvy-ql/default.graph** | Basin Catalog sink for analytics data | ✅ Active | Parquet/Zstd format |

**Data Flow:**
```
Connector → R2 artifacts → K2 events → Basin ingestion → Analytics projection
```

**Authentication:** HTTP auth disabled for unstructured JSON records (`[{"value": <JSON>}]` format)

---

## 🔗 Data Flow Architecture

### Primary Ingestion Pipeline

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            OPERATOR ACTIONS                                   │
└───────────────────────────────────────────────────────────────────────────────┘
                                │
┌───────────────────────────────▼───────────────────────────────────────────────┐
│                        V2 SUPERVISOR (v2/supervisor/)                       │
│  - Orchestrates all connectors                                              │
│  - Manages runs and work items                                              │
│  - Handles queue consumption                                                │
│  - Exposes progress API                                                     │
│  - Generates release manifests                                              │
└───────────────────────────────┬───────────────────────────────────────────────┘
                                │ (Direct Bindings)
                                ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    CONNECTORS (Direct Service Bindings)                      │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────────────┐  │
│  │ JudyRecords │    │ TruthSocial │    │ SAM.gov                        │  │
│  └──────┬──────┘    └──────┬──────┘    └─────────────────────────────────┘  │
│         │                  │                                              │
│         ▼                  ▼                                              │
│  ┌─────────────┐    ┌─────────────┐                                    │
│  │ Spider API  │    │ Spider API  │                                    │
│  │  Calls      │    │  Calls      │                                    │
│  └──────┬──────┘    └──────┬──────┘                                    │
│         │                  │                                              │
│         ▼                  ▼                                              │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Raw HTML/JSON Responses → R2 (harvy-raw)                            │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ Processing: Normalization → R2 (harvy-artifacts)                     │  │
│  │ - Source HTML sidecars (.source.html)                                │  │
│  │ - SHA256 checksums                                                   │  │
│  │ - Release manifests                                                  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │ K2 Events → Basin (harvyql_stream → harvy-ql/default.graph)         │  │
└───────────────────────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
User Request → Static UI (pages/, styles/, static/)
    ↓
Better Auth Worker (v2/auth/)
    ↓ (Validates token)
V2 D1 (ontology, user sessions)
    ↓
Supervisor / Connectors (V2_CONNECTOR_TOKEN validation)
```

---

## 🔐 Security & Authentication

### Connector Token Validation

All connectors validate `V2_CONNECTOR_TOKEN`:
- **JudyRecords & TruthSocial**: Validate Bearer token prefix
- **SAM.gov**: Validates expected Bearer-formatted header
- **All connectors**: Share the same token value

**Required Secrets:**
- `SPIDER_API_KEY` - Spider Unlimited API key
- `WEBSHARE_PROXY_URL` - Webshare proxy configuration  
- `V2_CONNECTOR_TOKEN` - Connector authentication token
- Provider-specific credentials (configured per connector)

---

## ⚠️ Critical Infrastructure Warnings

### DO NOT DELETE (🔴 Critical)
1. **harvy-artifacts R2 bucket** - Contains all normalized data
2. **V2 D1 database** - Contains all operational state and canonical objects
3. **Better Auth Worker** - Authentication service for the platform
4. **Supervisor Worker** - Orchestration service for all connectors

### Account Restrictions
- Workers for Platforms dispatch namespaces are unavailable
- Direct bindings are mandatory for connector communication
- All connectors must use identical `V2_CONNECTOR_TOKEN`

### Health & Monitoring Requirements
- Worker health probes must return valid JSON
- Connector registration requires successful health check
- Basin ingestion requires HTTP auth disabled for unstructured data
- Target cache hit rate: 75% for eligible public endpoints

---

## 📊 Storage Details

### R2 Bucket Contents

#### harvy-raw (60-day expiry)
- Raw HTML responses from connectors
- JSON API responses
- Temporary artifacts during processing
- Automatically cleaned up after 60 days
- **Purpose:** Temporary staging area for raw data

#### harvy-artifacts (PERMANENT - Critical!)
- Normalized JSON records
- Release manifests
- Page manifests
- Source HTML sidecars (`.source.html`)
- SHA256 checksums for data integrity verification
- `source_html_path` and `source_html_sha256` fields in records
- **Purpose:** Permanent storage for all processed data

### D1 Schema (Migration 0006)

**Core Tables:**
```sql
ontology_objects      - Shared canonical records
observations          - Data points and measurements
links                 - Entity relationships
dashboard_definitions - UI dashboard configurations
runs                  - Job execution records
work_items            - Individual task items
registrations         - Connector/service registrations
```

---

## 🔍 Quick Reference

### Endpoints & Locations

| Component | Access Pattern | Configuration File |
|-----------|----------------|-------------------|
| Supervisor API | `{supervisor}.workers.dev` | `v2/supervisor/wrangler.toml` |
| Better Auth | `{auth}.workers.dev` | `v2/auth/wrangler.toml` |
| JudyRecords Connector | `{judyrecords}.workers.dev` | `v2/catalog/connectors/judyrecords/wrangler.toml` |
| TruthSocial Connector | `{truthsocial}.workers.dev` | `v2/catalog/connectors/truthsocial/wrangler.toml` |

### Important Files
- **Supervisor Config**: `v2/supervisor/wrangler.toml`
- **Connector Contracts**: `v2/shared/`
- **Migrations**: `v2/migrations/`
- **Worker Source**: Each connector's directory
- **Static UI**: `pages/`, `styles/`, `static/`

### Basin Resources
- **Ingestion Path**: `harvyql_stream` (ID: `e1e54007204f43768769ee613369c85f`)
- **Catalog Sink**: `harvy-ql/default.graph`

---

## 📚 Related Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed architecture overview
- **[V2_CONNECTORS.md](docs/V2_CONNECTORS.md)** - Connector operations and bindings
- **[AUTH.md](docs/AUTH.md)** - Authentication and authorization guide
- **[HOSTING.md](docs/HOSTING.md)** - Deployment and hosting information
- **[PLAN.md](docs/PLAN.md)** - Master project plan
- **[LOGGING.md](docs/LOGGING.md)** - Logging and monitoring guide

---

## 🛠️ Maintenance Notes

### Backup Requirements
- **harvy-artifacts** must be backed up before any migration
- V2 D1 database requires regular snapshots
- Connector tokens should be rotated periodically

### Monitoring Targets
- Worker health endpoints (must return valid JSON)
- Basin ingestion success rates
- R2 bucket storage usage (harvy-artifacts is permanent)
- Cache hit rates (target: 75% for public endpoints)

### Upgrade Considerations
- All connectors must use same `V2_CONNECTOR_TOKEN`
- D1 migrations must be applied in order
- Basin ingestion paths are fixed (harvyql_stream)
- Worker names and bindings must be preserved during changes

---

## 📞 Support & Troubleshooting

### Common Issues

**Error 1010 (browser_signature_banned):**
- Cause: Default Python urllib user-agent blocked by Cloudflare
- Solution: Use descriptive client user-agent like `HarvyPlatform/2.0`

**Missing Secrets:**
- Ensure `SPIDER_API_KEY`, `WEBSHARE_PROXY_URL`, and `V2_CONNECTOR_TOKEN` are configured
- Secrets must be available to all connector Workers

**Health Check Failures:**
- Verify Worker health endpoints return valid JSON
- Check D1 database connectivity
- Confirm R2 bucket bindings are correct

### Health Endpoints
Each Worker should expose a `/health` endpoint returning JSON:
```json
{"status":"ok","timestamp":"2026-10-27T...","version":"2.0"}
```

---

**Documentation Version:** v2.0
**Next Review:** When infrastructure changes are planned
**Owner:** Harvy V2 Platform Team
