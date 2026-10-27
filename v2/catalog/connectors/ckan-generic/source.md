# CKAN (generic) connector

Key: `none required` — public CKAN API works without a key. Some government CKANs throttle anonymous requests; an `Authorization: <api_key>` header can be added per-portal.

Endpoint: `<base>/api/3/action/...`  (CKAN 2.x; the older `/api/2/` path also works on some)
Discovery: `package_search` paginates the full dataset list; `package_show` returns one package with all resources.
Storage:   a `package` has 1..N `resources`, each with a `url` to the actual file.

Documentation:
- CKAN API reference: https://docs.ckan.org/en/2.9/api/
- Action API: https://docs.ckan.org/en/2.9/api/index.html#action-api
- `package_search` schema: https://docs.ckan.org/en/2.9/api/index.html#ckan.logic.action.get.package_search

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/ckan.py
# This is the same file as ckan-energydata.md; it's already generic — you just
# change the base_url. Reuse it for any CKAN.
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            base_url=self.api_base or f"{self.base_url}/api/3/action",
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1",
                     "Authorization": self.source.get("ckan_api_key", "")},
        ) as client:
            start = 0
            rows = 100
            while True:
                r = await client.get("/package_search",
                                     params={"q": "", "rows": rows, "start": start})
                r.raise_for_status()
                result = r.json()["result"]
                for pkg in result["results"]:
                    for res in pkg.get("resources", []):
                        yield RawBundle(
                            source_system=self.source_system,
                            source_collection=self.source_collection,
                            source_id=pkg["name"],
                            source_url=f"{self.base_url}/dataset/{pkg['name']}",
                            bundle_url=res["url"],
                            fetched_at=self.now(),
                            payload=b"",
                            payload_format=(res.get("format") or "").lower(),
                            metadata={"package": {
                                "title": pkg.get("title"),
                                "notes": pkg.get("notes"),
                                "license": pkg.get("license_title"),
                                "organization": (pkg.get("organization") or {}).get("title"),
                                "country_codes": pkg.get("country_code", []),
                                "tags": [t["name"] for t in pkg.get("tags", [])],
                            }, "resource": {
                                "name": res.get("name"),
                                "size": res.get("size"),
                                "mimetype": res.get("mimetype"),
                            }},
                            is_remote_only=True,
                        )
                if start + rows >= result["count"]:
                    break
                start += rows
```

## Quick call — verify

```bash
# List 1 dataset from any CKAN
curl -sL "https://data.gov.au/api/3/action/package_search?rows=1" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); r=d['result']; print('count:',r['count']); print('first:',r['results'][0]['name'])"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /api/3/action/package_search?q=&rows=100&start=0
GET /api/3/action/package_show?id=<name>
GET /api/3/action/tag_list
GET /api/3/action/organization_list
GET /api/3/action/group_list
```

## Notes

- The user supplied a list of 130+ international portals. Most of the national/federal data portals in that list (data.gov.au, data.gov.uk, data.govt.nz, open.canada.ca, datos.gob.ar, data.gov.be, dados.gov.br, data.norge.no, data.gov.hk, data.gov.in, data.go.jp, data.go.kr, data.gov.sg, data.govt.nz, data.gov.ie, opendata.swiss, ...) are vanilla CKAN. One connector covers them all — just set `base_url` per portal in `sources.yaml`.
- `ckan-energydata.md` is the worked example with the World Bank ESMAP energydata.info portal. The fetcher code is identical.
- Some CKANs (e.g. data.gov.au) put a `ckan-api-key` per-user in the cookie; the fetcher passes it through the `Authorization` header if `ckan_api_key` is set in `sources.yaml`.
- `package_search` is paginated by `start` (offset) and `rows` (page size). Some CKANs cap `rows` at 1000; the loop handles that.

