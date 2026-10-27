# Site-search framework

`search/` is the shared HTTP layer for submitting a website's conventional HTML
search bar. `SearchClient.search(page_url, query)` discovers a GET or POST form,
keeps hidden fields, submits without logged-in cookies, and returns response
metadata plus normalized links.

The first form with a likely query input is intentionally the only default
policy. JavaScript-only search bars need a site-specific adapter that can
produce the same `SearchResponse`; browser automation and authenticated
sessions are not part of this base layer.

JudyRecords uses a site-specific session adapter because its search submits an
asynchronous job and requires polling before record URLs are available. Once a
record URL is discovered, the record fetch may use Spider Unlimited with the
configured Webshare proxy; parsing remains separate from discovery.

## Bounded JudyRecords bulk runner

`scripts/judyrecords_bulk_runner.py` implements the local bulk loop: serialized Spider AI search (`/ai/browser`, max 1 request/second) -> Unlimited `/unlimited/links` or `/unlimited/crawl` indexing -> SQLite batched queue -> up to three concurrent `/unlimited/scrape` workers using the Webshare proxy -> page validation -> local raw/record storage -> run summary. It does not deploy or enable remote resources; credentials come from `SPIDER_API_KEY`, `WEBSHARE_PROXY_URL`, and optional `SPIDER_WEBHOOK_TOKEN`. Use `--target 75000 --concurrency 3 --rounds 2` only after a small verified run.
