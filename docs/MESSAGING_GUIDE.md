# Harvy Messaging Guide

## Positioning

Harvy is a public-source reconnaissance platform that follows an entity’s public trail, preserves the evidence it finds, and shows how separate public references connect.

**Short description:** Follow the public trail. Preserve the evidence. Understand the connections.

**Long description:** Harvy runs bounded public-source collection jobs, stores original captures beside normalized records, retains provenance and limitations, and turns completed work into research-ready artifacts and relationship evidence.

## The voice

The live HarvyBot site uses a terminal-inspired, high-signal voice: short labels, status lines, strong verbs, and concrete artifacts. It presents Harvy as a relentless investigator who cross-examines redirects, pagination, timestamps, and links instead of accepting a surface answer.

Keep the energy, but make the claims more precise. The best Harvy copy sounds confident because it names the evidence: source URL, capture time, record count, artifact path, coverage boundary, or explicit limitation.

Harvy can be quirky in personality and disciplined in product language. The character may be analytical, persistent, and playful; the product must remain careful about identity, completeness, legal status, and what was actually verified.

## Message pillars

### 1. Public trail, not private access

Harvy works with public-source material and does not require access to private or authenticated account areas. Say “public profile,” “public post,” “public record,” or “public API response.” Do not imply access to private messages, private groups, or hidden account data.

### 2. Evidence before inference

Harvy preserves source URLs, timestamps, original captures, parser versions, and limitations. A relationship in a graph should be described as an observed source-backed link—not proof of identity, intent, ownership, or coordination.

### 3. Bounded reconnaissance

A collection job has explicit inputs and limits. Say what was requested, what was collected, and what remains unknown. Avoid “complete archive,” “all posts,” “100% accurate,” or “full history” unless a measured run proves that exact claim.

### 4. Traceable results

The product is more than a search result. It produces records that can be inspected, replayed, compared, and connected back to their source evidence.

### 5. Clean operational control

Harvy’s strongest technical story is controlled collection: registered connectors, explicit scope, queued work, retries, environment isolation, raw files, normalized artifacts, and event telemetry.

## Preferred vocabulary

| Prefer | Avoid |
|---|---|
| public-source reconnaissance | surveillance |
| source-backed edge | inferred relationship |
| observed public record | verified identity |
| bounded collection | unlimited coverage |
| original capture | scraped truth |
| normalized artifact | cleaned-up fact |
| coverage limitation | hidden gap |
| collection run | magic search |
| evidence trail | certainty engine |
| source connector | bot |

## Product claims

### Safe claims now

- Harvy can run explicitly registered V2 connector jobs.
- The supervisor coordinates discovery, queued processing, retries, and run status.
- Raw and normalized artifacts are stored separately in the V2 design.
- Connector events can feed analytics and progress projections.
- A bounded Truth Social profile sample produced an artifact.
- A bounded JudyRecords direct-record sample produced normalized JSON and an original HTML sidecar.

### Claims requiring qualification

- **“20+ platforms”** is a website positioning claim, not proof that 20+ V2 connectors are implemented and live.
- **“Cross-platform mapping”** should be described as available where an implemented connector exposes explicit source-backed links.
- **“Historical archive”** must specify the source, date window, pagination coverage, and completeness result.
- **“Verified”** should refer to a source or collection status, not automatically to a person or organization’s identity.
- **“Real-time”** should be reserved for a connector with a measured push or polling interval.

## Copy patterns

### Homepage headline

**Follow the public trail.**

### Homepage subhead

Run bounded public-source investigations, preserve the original evidence, and see how explicit links connect records across the open web.

### Run status

`RUN // TRUTHSOCIAL // PROFILE SAMPLE`

`[QUEUED] Request accepted with bounded scope.`

`[FETCHED] Public profile response captured.`

`[STORED] Normalized artifact written with source URL and capture time.`

`[LIMIT] Result does not establish historical completeness.`

### Connector card

**JudyRecords**  
Public court-record capture with normalized case fields, parties, dates, and preserved source HTML. Direct-record collection is verified; broad search discovery remains limited.

### Limitation language

> This result reflects the requested public source and collection window. It is not a claim of complete historical coverage or verified identity.

## Do and do not

- Do lead with the investigation outcome and evidence trail.
- Do show the source, time, scope, and limitation near the result.
- Do use terminal/status styling for operational feedback.
- Do use personality in headings and onboarding, not in evidence fields.
- Do not promise coverage that the connector has not measured.
- Do not turn a name match into an identity claim.
- Do not expose secrets, proxy details, private account data, or internal tokens.
- Do not describe catalog entries as working connectors.
- Do not call a queued run complete.

## Audience-specific messages

### Beginner researcher

“Start with one public target. Harvy records what it found, where it came from, and what the collection did not cover.”

### Analyst

“Use bounded runs and inspect the artifact trail: source URL, capture time, parser version, completeness, and limitations.”

### Operator

“Enable connectors only after capability verification. Monitor queue lag, retries, dead-letter items, artifact paths, and event projections.”

### Developer

“Implement the connector contract, validate source-specific inputs, make writes idempotent, preserve provenance, and prove the flow with a bounded fixture and live sample.”

## One-sentence test

If a sentence sounds impressive but does not tell the reader what source was observed, what was stored, or what remains uncertain, rewrite it.

## Source basis

The tone and visible product language were reviewed from the live HarvyBot homepage at `https://harvybot.com`. Capability status was checked against `docs/V2_CONNECTORS.md`, `docs/ARCHITECTURE.md`, and the implementations under `v2/catalog/connectors/`.
