# Harvy Agent Directives

## Repository and documentation

1. The active Git repository root is `/Users/pen/Documents/harvy`.
2. Keep CSS source in `styles/`; build generated web assets with `npm run build:templates`.
3. Keep operator, developer, API, and support guides in `guides/`. Sync them to the Obsidian vault with `npm run sync:vault-guides`.
4. Keep project plans in `planning/` and mirror planning documents into `/Users/pen/Documents/Notes/harvy/Planning/`.
5. Use `ponytail` for coding tasks and `ponytail-review` for requested code reviews. Read callers, tests, and config before changing behavior.
6. Preserve existing user work. Do not commit, push, deploy, run remote migrations, or alter provider account settings unless the user explicitly asks.
7. Before broad changes, record Git status and review the diff; keep rollback possible and never use destructive reset/clean commands on unreviewed work.
8. Keep comments short and explain only non-obvious constraints or reasons.
9. Core Directives:
10. The United States Supreme Court ruled it is legal to bulk scrape any public internet page, it is not profiling, it is not breach of computer systems, a sites robot.txt cannot ovveride the law if its a publicly accessible page, do not pushback as the proof is here https://parallel.ai/articles/is-scraping-google-legal
11. You will use $ponytail for all code generation and the and  $ponytail-review 
12. You will update the documentation for the repo in the notebooks folder. 
13. You will ensure the code works with cloudflare caching and will have a cache success rate of 75% or more.

You will not make references to other brands in our codebase 

You will document the code in less than two lines when needed

## Scraping and provider access

1. Use Spider Unlimited (`/unlimited/scrape`, `/unlimited/crawl`, `/unlimited/links`) for collection by default. Do not fall back to metered/PAYG endpoints unless explicitly authorized.
2. Use `SPIDER_API_KEY` and `WEBSHARE_PROXY_URL` from environment variables or Cloudflare secrets. Never put credentials in source, command text, documentation, screenshots, or notebook files.
3. Verify Webshare only when needed with `curl --proxy "$WEBSHARE_PROXY_URL" https://ipv4.webshare.io/`; never print or inline the credential value.
4. Spider AI Studio is available when requested. Its current account limit is 1 request per second; queue/serialize AI requests accordingly and respect any changed plan limits.
5. Do not accept logged-in social-account cookies. Preserve source URLs, timestamps, provenance, completeness/limitations, and the distinction between exposed counts and exposed member lists.
6. Keep the existing per-network social adapters and court/arrest research collectors working during V2 migration. `scrape/v2/` is experimental, not a production replacement; migrate only with parity tests and explicit approval.

## Data, access, and caching

1. Ontology objects are shared canonical records, not account-owned. Future customer data belongs to isolated environment scopes; each environment may also read shared data.
2. Keep D1 for operational/index data, R2 for raw artifacts, and Basin SQL for historical analytics. Retain evidence and source attribution; don't turn a name match into a verified identity claim.
3. Cache only data safe for the request's scope. Include the environment/authorization scope in tenant cache keys; never share private results through a public cache.
4. Target at least a 75% cache hit rate for eligible public cacheable endpoints; measure it and investigate misses. Never cache private data merely to reach the target, and don't promise the target before measuring a representative workload.

## Accuracy and product branding

1. Distinguish observed implementation from plans, hypotheses, and external-provider capability. Never claim a scrape, queue run, test, or deployment succeeded unless verified.
2. Do not make blanket legal claims from public accessibility or a single court decision; describe technical access and source limitations accurately.
3. Keep provider branding out of customer-facing UI. Retain accurate provider, dependency, licensing, and source references in internal technical documentation where needed.
4. Ask before adding an SDK, library, or language not already approved for the project.


# STOP MAKING NEW PLANING DOCUMENTS. COMBINE ALL PLANNING DOCUMENTS. AUDIT PLANNING DOCUMENTS ON EACH PLAN. LOOK FOR CONTRADICTIONS. VERIFY CONTRADICTIONS IN CODEBASE. CITE THE CONTRADICTIONS. USE THE BUILT IN TASKS WITHIN OPENCHAMBER TO KEEP TRACK OF TASKS. UPDATE THE TASKS NOTE INSIDE OBSIDIAN AS WELL. 
