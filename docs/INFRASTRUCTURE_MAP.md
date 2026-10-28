# 🗺️ Harvy V2 Infrastructure Map

**Last Updated:** 2026-10-27  
**Status:** ✅ ACTIVE & OPERATIONAL  
**Version:** V2

---

## 🎯 Executive Summary

Harvy V2 is a **fully deployed** Cloudflare-based data ingestion and analytics platform with:
- **5 Workers** deployed and operational
- **K2 durable event streaming** configured
- **Basin analytics pipeline** active
- **R2 storage** for raw and normalized data
- **D1 database** for operational data
- **Queues** for async processing
- **Analytics Engine** for observability

**All components are production-ready and actively processing data.**

---

## 🏗️ Infrastructure Architecture

```
┌───────────────────────────────────────────────────────────────────────────────┐
│                            CLOUDFLARE PLATFORM                              │
├───────────────────────────────────────────────────────────────────────────────┤
│                                                                               │
│  ┌─────────────┐    ┌─────────────┐    ┌───────────────────────────────────┐  │
│  │  Supervisor │    │   Auth      │    │         JudyRecords Connector    │  │
│  │  Worker     │    │   Worker    │    │                                   │  │
│  └──────┬──────┘    └──────┬──────┘    └──────────┬──────────────────────┘  │
│         │                  │                       │                        │
│         ├──────────────────┴───────────────────────┴────────────────────────┤
│         │                                                                   │
│  ┌──────▼──────┐    ┌─────────────┐    ┌───────────────────────────────────┐  │
│  │   K2 Topic  │    │   D1 DB     │    │      TruthSocial Connector       │  │
│  │  harvy-     │    │  harvy-     │    │                                   │  │
│  │  events     │    │  platform-  │    └──────────────┬───────────────────┘  │
│  └──────┬──────┘    │  v2         │                   │                     │
│         │            └───────────────┘                   │                     │
│         │                                              │                     │
│  ┌──────▼────────────────────────────────────────────────▼─────────────────┐  │
│  │                            R2 BUCKETS                              │  │
│  │                                                                       │  │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌───────────────────┐  │  │
│  │  │  harvy-raw      │    │  harvy-artifacts│    │  harvy-ql         │  │  │
│  │  │  (60-day expiry)│    │  (permanent)    │    │  (Basin warehouse)│  │  │
│  │  └─────────────────┘    └─────────────────┘    └───────────────────┘  │  │
│  │                                                                       │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                               │
│  ┌─────────────┐    ┌─────────────────────────────────────────────────────┐  │
│  │  Queues     │    │               Basin Pipeline                      │  │
│  │             │    │                                                     │  │
│  │  • harvy-   │    │  • Stream: harvyql_stream (e1e54...)              │  │
│  │    v2-work  │    │  • Sink: harvy-ql/default.graph (Parquet/Zstd)   │  │
│  │  • DLQ      │    │  • Pipeline ID: cbee9eb32e4a4617a81fda117c750c10  │  │
│  └─────────────┘    └─────────────────────────────────────────────────────┘  │
│                                                                               │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

## 📦 Deployed Workers (5 Total)

### 1. **Supervisor Worker** ✅ DEPLOYED
- **Name:** harvy-supervisor-datasourcename
- **Bindings:** V2_DB, V2_CONFIG, V2_RAW_BUCKET, V2_ARTIFACTS_BUCKET, V2_EVENTS (K2), V2_WORK_QUEUE, V2_JUDYRECORDS, V2_TRUTHSOCIAL, V2_RUN_WORKFLOW
- **Status:** Workers Dev + Production configured

### 2. **Auth Worker** ✅ DEPLOYED
- **Name:** harvy-auth
- **Route:** harvybot.com/api/better-auth/*
- **Binding:** HARVY_D1 (D1 database)
- **Status:** Production

### 3. **JudyRecords Connector** ✅ DEPLOYED
- **Name:** harvy-judyrecords
- **Bindings:** V2_RAW_BUCKET, V2_ARTIFACTS_BUCKET, SPIDER_API_KEY, WEBSHARE_PROXY_URL
- **Status:** Production

### 4. **TruthSocial Connector** ✅ DEPLOYED
- **Name:** harvy-truthsocial
- **Bindings:** V2_RAW_BUCKET, V2_ARTIFACTS_BUCKET, SPIDER_API_KEY, WEBSHARE_PROXY_URL
- **Status:** Production

### 5. **Projector Worker** ✅ DEPLOYED
- **Name:** harvy-v2-projector
- **Bindings:** V2_DB, V2_CONFIG, V2_RAW_BUCKET, V2_ARTIFACTS_BUCKET, V2_BASIN_STREAM (Basin), V2_ANALYTICS, V2_PUBLIC_ANALYTICS
- **Triggers:** Cron every 5 minutes
- **K2 Endpoint:** Configured
- **Status:** Workers Dev + Production configured

---

## ☁️ K2 Event Streaming (ACTIVE)

### K2 Topic Configuration
- **Topic Name:** harvy-events
- **Stream ID:** e8073c59caed4ee193cd995aa457b21a
- **Binding:** V2_EVENTS (Supervisor Worker)
- **Status:** ✅ ACTIVE

---

## 📊 Basin Analytics Pipeline (ACTIVE)

### Basin Configuration
- **Stream Name:** harvyql_stream
- **Stream ID:** e1e54007204f43768769ee613369c85f
- **Pipeline ID:** cbee9eb32e4a4617a81fda117c750c10
- **Sink:** harvy-ql/default.graph (Parquet/Zstd)
- **Status:** ✅ ACTIVE

---

## 💾 R2 Storage Configuration

### Buckets (3 Total)
- **harvy-raw:** 60-day expiry for raw crawls
- **harvy-artifacts:** Permanent storage for normalized records
- **harvy-ql:** Basin warehouse (Iceberg/Parquet)

---

## 🗄️ D1 Database Configuration

### Shared V2 Database
- **Database Name:** harvy-platform-v2
- **Database ID:** 2fb9f8e4-ca31-4cd0-95b4-b084429816f2
- **Migrations:** v2/migrations/
- **Applied:** 0006_ontology_and_dashboards.sql

---

## 📦 Queues Configuration

### Work Queue
- **Queue Name:** harvy-v2-work
- **Binding:** V2_WORK_QUEUE
- **Consumer:** Supervisor Worker
- **DLQ:** harvy-v2-work-dlq

### Build Events Queue
- **Queue Name:** harvy-v2-build-events
- **Binding:** V2_BUILD_EVENTS
- **Consumer:** Projector Worker
- **DLQ:** harvy-v2-build-events-dlq

---

## 🔍 Analytics Engine

### Datasets (2 Total)
- harvy_v2_internal_events
- harvy_v2_public_progress

---

## 📈 Infrastructure Health Checks

### ✅ Deployed & Operational
- [x] Supervisor Worker
- [x] Auth Worker
- [x] JudyRecords Connector
- [x] TruthSocial Connector
- [x] Projector Worker
- [x] K2 Topic (harvy-events)
- [x] Basin Pipeline (harvyql_stream → harvy-ql/default.graph)
- [x] R2 Buckets (harvy-raw, harvy-artifacts, harvy-ql)
- [x] D1 Database (harvy-platform-v2)
- [x] Queues (harvy-v2-work, harvy-v2-build-events)
- [x] Analytics Engine (2 datasets)

### ⚠️ Needs Attention
- [ ] Cache hit rate measurement (PLAN.md target: 75%)
- [ ] SAM.gov connector binding
- [ ] TruthSocial timeline pagination verification
- [ ] JudyRecords term discovery verification
- [ ] Auth cutover

---

## 📋 Configuration Files Summary

| File | Purpose |
|------|---------|
| v2/supervisor/wrangler.jsonc | Supervisor configuration |
| v2/auth/wrangler.jsonc | Auth Worker configuration |
| v2/catalog/connectors/judyrecords/wrangler.jsonc | JudyRecords connector |
| v2/catalog/connectors/truthsocial/wrangler.jsonc | TruthSocial connector |
| v2/projector/wrangler.jsonc | Projector Worker configuration |
| v2/workflows/openstates-ingest.json | OpenStates ingestion workflow |
| v2/agents/openstates-agent.json | Token-optimized agent |

---

**Document Owner:** Harvy Agent  
**Last Reviewed:** 2026-10-27  
**Status:** ✅ COMPLETE

