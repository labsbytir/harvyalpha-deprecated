# Harvy product introduction

This notebook is the reader-friendly companion to `docs/INTRO_GUIDE.md` and `docs/MESSAGING_GUIDE.md`.

Harvy is a public-source reconnaissance and evidence system. It runs bounded connector jobs, preserves source captures, creates normalized artifacts, and records provenance and limitations. The live site’s voice is terminal-like, concise, evidence-focused, and energetic; product claims must still match the implemented V2 code.

## Current connector status

- **JudyRecords:** deployed and exercised with a bounded direct-record sample; normalized JSON and original HTML sidecar were produced. Search discovery and broad pagination remain unverified.
- **Truth Social:** deployed and exercised with a bounded profile sample that wrote an artifact. Full historical coverage is not proven.
- **SAM.gov:** connector code exists, but it is not bound to the supervisor and has no verified live run.
- **Catalog candidates:** source definitions are not live connectors. They remain disabled until implementation, binding, capability verification, and a bounded artifact are proven.

## Messaging rule

Say what source was observed, what was stored, when it was captured, and what remains unknown. Never turn a name match into a verified identity, a captured page into a complete archive, or a queued run into a completed result.

See the two canonical guides in `docs/` for the complete feature and messaging explanation.
