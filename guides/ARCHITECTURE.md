# Harvy Architecture

## Codebase and runtime

- Repository: `/Users/pen/Documents/harvy` — [GitHub](https://github.com/labsbytir/harvy)
- Cloudflare entry point: `src/worker.py` (Python Workers)
- Local/hosted Python service: `web_app.py` (Flask)
- Page source: `templates/`; CSS source: `styles/`; generated Worker assets: `static/`
- Network collectors and shared scrape protocol: `scrape/`
- Basin storage/schema/docs: `health/`

## Current data flow

```text
Browser → Cloudflare Worker → Queue → profile collector
                                  ├─ raw response → R2
                                  └─ profile/post search documents → D1
```

D1 currently contains job state and denormalized search documents, plus account/passkey tables. Raw profile responses are stored in R2. The current Cloudflare Worker profile path does not yet send normalized ontology records to Basin; the local Flask service has Basin upload helpers. See [Basin operations](../health/BASIN.md).

## Planned data model

Use shared canonical objects, append-only observations, and evidence-backed links. Objects are not owned by user accounts. Future customer environments may add private observations/links that reference shared objects; a customer's accessible dataset is `shared + its environment`. Keep raw payloads in R2, operational lookups in D1, and historical analytics in Basin SQL/Iceberg.

## User features

- **Query** (current): React/MUI saved-dashboards builder at `/query/` using a server-side allowlisted query catalog; D1 for current operational metrics and Basin SQL for historical aggregates (Basin routing planned).
- **Nodes** (planned): Reagraph network visualization of persisted objects/links with provenance and a non-WebGL list fallback.
- Workers for Platforms is deferred unless customers need to upload and execute their own Worker code.

The implementation plan is in [planning/PLAN.md](../planning/PLAN.md).
