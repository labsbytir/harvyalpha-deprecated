# Harvy Introduction: Features and Connectors

## What Harvy is

Harvy is a public-source collection and research system. It accepts a bounded investigation request, asks a source-specific connector to discover work, processes that work in the background, stores the resulting evidence, and reports what happened.

The product has two layers. The public-facing experience uses concise reconnaissance language and research views. The V2 platform underneath provides the run coordinator, connector Workers, queues, storage, authentication configuration, event projection, and shared data contracts.

The most important beginner rule is to separate four states: documented, implemented, tested, and verified live. A source can appear in the catalog without having a working connector, and a successful sample does not prove complete historical coverage.

## How a collection run works

1. An operator submits a run with a connector ID, environment, bounded input, and idempotency key.
2. The supervisor checks that the connector is registered, enabled, and capability-verified.
3. The Workflow asks the connector to discover bounded items.
4. The supervisor validates the discovered URLs and stores work-item state in D1.
5. The shared Queue delivers work to a background consumer.
6. The supervisor claims each item and calls the private connector’s `/v2/process` endpoint.
7. The connector fetches the public source and writes an artifact to R2.
8. The supervisor records completion and emits a K2 event.
9. The projector sends selected events to analytics, progress, or Basin historical storage.

## Features currently represented in V2

### Bounded collection runs

Runs have explicit inputs, environments, statuses, and idempotency keys. Resending the same logical request can return the existing run rather than creating another one. A queued or accepted run is not yet a completed collection.

### Connector registration and capability gates

A connector is not enabled simply because its code exists. It must have the expected health response, service binding, registration, and capability verification. This prevents an unfinished connector from receiving production work.

### Background processing

Queues move discovered work out of the request path. Retries handle transient failures, while permanent source or input errors are recorded as failures. The dead-letter queue handles delivery or handler failures; it is not a substitute for application-level failure records.

### Evidence storage

`harvy-raw` is intended for original source captures. `harvy-artifacts` is intended for normalized records and release manifests. A normalized record should retain its source URL, collection time, parser version, completeness state, and limitations.

### Provenance and limitations

Harvy’s records are designed to answer “where did this come from?” and “what did the collector not establish?” This is especially important for public-source research: a matching name is not automatically a verified identity, and a captured page is not automatically a complete archive.

### Ontology and relationship data

The V2 schema defines canonical object types, objects, observations, link types, links, and dashboard definitions. Observations can point to stored evidence. Links can carry confidence, properties, and an evidence observation.

### Event projection and analytics

K2 carries structured events about connector and run activity. The projector sends events to Basin for historical analytics, Analytics Engine for metrics, and D1 for public progress. These analytics paths do not replace the original artifacts.

### Authentication configuration

Better Auth code and migrations exist under `v2/auth/` and target the shared V2 D1 database. The repository documentation says the auth route and migrations were not deployed as part of the refactor, so this should be described as implemented locally/configured—not as a verified live account system.

### Query and dashboard interface

The graph UI contains typed client code for catalog, query, and dashboard operations. The architecture documentation states that the V2-owned query routes are not implemented yet. The interface should therefore be described as a current UI foundation, not a fully verified analytics product.

## Connector guide

### JudyRecords

**What it collects:** Public court-record pages supplied as direct record URLs or discovered through bounded source requests.

**What the code produces:** A normalized record with title, case number, court, filing date, case type, status, parties, raw extracted text, source URL, collection time, parser version, completeness, and limitations. The connector also preserves the original HTML as a sidecar for the verified direct-record flow.

**Why it matters:** Court records can provide primary-source evidence for legal research and entity investigation. The original HTML and normalized fields make results easier to inspect and compare. The connector does not establish guilt, identity, or legal conclusions.

**Current status:** Deployed and exercised with a bounded direct-record sample. Search-result discovery and broad pagination remain unverified. The 75,000-record goal is not evidence that the connector currently has that coverage.

### Truth Social

**What it collects:** Public profile responses and public posts associated with a requested handle, subject to the connector’s bounded input and parser behavior.

**What the code produces:** Account and post fields extracted from public responses, including identifiers, content-related fields, account information, links, timestamps, and provenance. It uses scoped secret bindings and writes artifacts to R2.

**Why it matters:** Public posts can contribute time-stamped evidence to a research timeline. The source URL and collection metadata help an analyst distinguish an observed public post from a claim about a person’s complete activity.

**Current status:** Deployed and exercised with a bounded one-profile sample that wrote an artifact. This does not prove historical pagination, full-post coverage, or archive completeness.

### SAM.gov

**What it collects:** Public government opportunity data through the source API, including notice identifiers, titles, solicitation numbers, posted dates, response deadlines, types, place-of-performance information, and resource links.

**What the code produces:** Normalized opportunity records with source URL, collection timestamp, parser version, completeness status, a limitation noting that the API returns the latest version, and redacted API-key handling. Raw page material is retained through the configured artifact path.

**Why it matters:** Procurement notices can reveal public contracting activity, agencies, deadlines, locations, and relationships between organizations and government opportunities. They are useful for research and monitoring, but a notice alone does not prove an award, performance, or relationship.

**Current status:** Connector code and a private Worker configuration exist, but the repository says SAM.gov is not bound to the supervisor and has no verified live run. It must remain disabled until capability and output are checked.

## Catalog-only connector candidates

The source catalog contains many proposed stream definitions, including weather, government, civic, social, and other public-source families. Catalog disposition is not deployment approval. Entries may have a specification and source URL while having no source-specific implementation, tests, binding, or live-verified pull.

For a beginner, the correct question is not “Is this source in the catalog?” It is “Does this source have an implementation, a private Worker, a supervisor binding, an enabled D1 registration, a capability check, and a verified bounded artifact?”

New connectors should be added under `v2/catalog/connectors/<id>/`, implement the health/discover/process contract, use source-specific validation, preserve provenance, make R2 writes safe to repeat, add tests, and remain disabled until a bounded sample succeeds.

## What the data means

- **Raw capture:** The original response or source file saved for inspection and replay.
- **Normalized record:** A predictable structured representation extracted from the raw source.
- **Artifact:** A stored output file that can be referenced by later processing or research.
- **Observation:** A source-backed statement about an object at a particular time.
- **Link:** A relationship between canonical objects, ideally supported by an observation.
- **Completeness:** Whether the expected structured fields were extracted—not whether the entire source was archived.
- **Limitation:** A known boundary, such as missing history, unsupported pagination, or an API returning only the latest version.
- **Environment:** The scope in which data may be accessed; private results must not leak into shared public outputs.

## First-time user path

1. Choose one implemented connector.
2. Use one public target and a small date or item limit.
3. Submit a bounded run with a fresh idempotency key.
4. Wait for the final run status instead of stopping at `queued` or `202 Accepted`.
5. Inspect the D1 work state, Queue/DLQ status, R2 artifact path, source URL, timestamp, completeness, and limitations.
6. Treat the result as evidence to review, not an automatic identity or legal conclusion.

## Current boundaries

Harvy does not currently have verified V2 implementations for every platform named in the marketing site. SAM.gov is not connected to the supervisor. The query API routes and live auth cutover require separate verification. Full historical archives, universal cross-platform identity resolution, and complete coverage should not be promised without measured evidence.

## Source basis

Product tone was reviewed from `https://harvybot.com`. Implementation status and architecture were checked against `docs/V2_CONNECTORS.md`, `docs/ARCHITECTURE.md`, `v2/shared/contracts.ts`, `v2/supervisor/src/index.ts`, and the connector implementations under `v2/catalog/connectors/`.
