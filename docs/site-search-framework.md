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
