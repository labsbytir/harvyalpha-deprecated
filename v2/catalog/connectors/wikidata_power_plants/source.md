# Wikidata — global power infrastructure via SPARQL

Key: `none required (CC0)`
Endpoint (SPARQL): `https://query.wikidata.org/sparql`
Endpoint (REST): `https://www.wikidata.org/w/api.php`
Auth: `none` for low-volume; user-agent + contact-email header recommended
Format: **SPARQL JSON** + **JSON** (REST API) + **RDF/XML** (linked data)

Documentation:
- Wikidata: https://www.wikidata.org
- Query service: https://query.wikidata.org/
- SPARQL endpoint: https://query.wikidata.org/sparql
- Wikidata Query Service tutorial: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service
- Power plant QID: https://www.wikidata.org/wiki/Q159719
- Nuclear power plant QID: https://www.wikidata.org/wiki/Q134447
- Hydroelectric power station QID: https://www.wikidata.org/wiki/Q15911738
- License: **CC0 1.0** (Wikidata data) + **CC-BY-SA 4.0** (item labels and descriptions)
- Coverage: **global** (community-curated; quality varies by
  country)
- Refresh: **continuous** (SPARQL queries are real-time; bulk
  dumps updated weekly)

## What it is

**Wikidata** is the structured-data companion to Wikipedia —
a CC0-licensed knowledge base of **~110 million items**, each
with a stable QID (e.g. `Q159719` = "power plant",
`Q134447` = "nuclear power plant") and a set of typed
properties (e.g. `P17` = country, `P210` = installed capacity,
`P625` = coordinate location).

For power infrastructure, Wikidata is the right **cross-reference
and federation layer**. Every notable power plant in the world
has a Wikidata item, linked to:

- The country (`P17` → ISO 3166-1 country)
- The operator (`P176` → operator organization)
- The parent company (`P749` → parent organization)
- The installed capacity (`P210` → in MW)
- The fuel source (`P1056` → product or material produced or
  service provided, sometimes via `P101` "field of this occupation")
- The commission date (`P619` → commissioning date)
- The coordinates (`P625` → coordinate location)
- The image (`P18` → image, often a satellite or aerial photo
  from Wikimedia Commons)
- The Wikipedia article (`P910` → topic's main Wikimedia portal)
- The Wikidata QID of equivalent items in other databases (e.g.
  `P8947` = "Global Power Plant Database ID", the
  `gppd_idnr` from [[wri_gppd]])

This is the right source for **federated identifiers** and for
**cross-referencing** between [[wri_gppd]], [[gem_global_energy_monitor]],
and [[openinframap]]. Wikidata is the global "join key" of OSINT.

## The query pattern (SPARQL)

A query for all nuclear power plants with installed capacity:

```sparql
SELECT ?plant ?plantLabel ?country ?countryLabel ?capacity ?coord WHERE {
  ?plant wdt:P31 wd:Q134447 .                    # instance of nuclear power plant
  ?plant wdt:P17 ?country .                       # country
  ?plant wdt:P210 ?capacity .                     # installed capacity (MW)
  ?plant wdt:P625 ?coord .                        # coordinate
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY DESC(?capacity)
LIMIT 100
```

Try it at https://query.wikidata.org/ (the live SPARQL editor).

A more complex query for the top 50 wind farms by capacity:

```sparql
SELECT ?plant ?plantLabel ?countryLabel ?capacity WHERE {
  ?plant wdt:P31/wdt:P279* wd:Q15911738 .          # instance of or subclass of hydro
  # replace with: wd:Q194356 (wind farm)
  ?plant wdt:P17 ?country .
  ?plant wdt:P210 ?capacity .
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
ORDER BY DESC(?capacity)
LIMIT 50
```

A query that returns the per-country count of power plants by
fuel type:

```sparql
SELECT ?countryLabel (COUNT(?plant) AS ?count) WHERE {
  VALUES ?fuel {
    wd:Q9 wd:Q12714 wd:Q11650585 wd:Q805012 wd:Q846556 wd:Q2996119
  }
  ?plant wdt:P31/wdt:P279* wd:Q159719 .            # instance of power plant
  ?plant wdt:P17 ?country .
  ?plant wdt:P1056 ?fuel .                         # fuel source
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en" }
}
GROUP BY ?countryLabel
ORDER BY DESC(?count)
LIMIT 50
```

(Where `Q9` = thermal, `Q12714` = fossil fuel, `Q11650585` =
nuclear, `Q805012` = petroleum, `Q846556` = coal, `Q2996119` =
renewable.)

## The key Wikidata IDs to know

| QID | Entity |
|---|---|
| `Q159719` | power plant |
| `Q134447` | nuclear power plant |
| `Q194356` | wind farm |
| `Q13293210` | solar farm |
| `Q15911738` | hydroelectric power station |
| `Q2996119` | renewable energy source |
| `Q846556` | coal |
| `Q4240` | natural gas |
| `Q805012` | petroleum |
| `Q11650585` | nuclear power |
| `Q9` | thermal energy |
| `Q12714` | fossil fuel |
| `P17` | country (ISO 3166-1) |
| `P176` | manufacturer / operator |
| `P210` | installed capacity (MW) |
| `P625` | coordinate location |
| `P619` | commissioning date |
| `P1056` | product or material produced / service provided |
| `P749` | parent organization |
| `P18` | image (Wikimedia Commons) |
| `P910` | topic's main Wikimedia portal (Wikipedia article)
| `P8947` | Global Power Plant Database ID (links to [[wri_gppd]]) |

## How to wire it up for OpenTIR-Data

1. **First ingest**: pull a Wikidata JSON dump (~100 GB
   uncompressed) or query per-country. For our use case, per-
   country SPARQL queries are sufficient — Wikidata's query
   service is fast enough.
2. **Per-plant storage**: write to `osint.wikidata_power_plants`
   keyed by QID. Per-record `country`, `operator`, `parent`,
   `capacity_mw`, `coord`, `commissioning_date`, `gppd_idnr`.
3. **Cross-reference**: for each power plant in [[wri_gppd]],
   query Wikidata for the same plant and store the QID. For
   each plant in [[gem_global_energy_monitor]] and
   [[openinframap]], same.
4. **Reverse direction**: for each QID in our warehouse, query
   Wikidata for all linked items — operator, parent, regulatory
   body, etc. — and store the federation graph.

## Important caveats

| Caveat | Detail |
|---|---|
| **Wikidata is community-curated** | Quality varies by country. Germany, UK, US: excellent. Africa, Central Asia: sparse. |
| **Some properties are sparse** | `P210` (capacity) is present for ~30-40% of plants. For the rest, fall back to [[wri_gppd]] or [[gem_global_energy_monitor]]. |
| **SPeEdBricKer-er queries can time out** | Don't do `SELECT * WHERE { ?item wdt:P31 wd:Q159719 }` — it'll exceed the 30-second SPARQL timeout. Use filters. |
| **Item labels require a SERVICE clause** | Plain SPARQL returns QIDs. To get human-readable labels, add the `SERVICE wikibase:label` clause. |
| **Properties change over time** | Wikidata QIDs are stable; property IDs (`P31`, `P210`, ...) are stable. The *meaning* of a property can drift slightly. |
| **CC-BY-SA on labels** | The QID + facts are CC0. The labels and descriptions are CC-BY-SA (because they're derived from Wikipedia). We can re-publish the QIDs and facts under CC0; we should re-publish labels with attribution. |
| **Bulk dumps are huge** | The full Wikidata JSON is ~100 GB. Use per-query or per-country SPARQL for our use cases. |

## What we use it for

- **Federated identifiers**: every power plant in our warehouse
  has a stable Wikidata QID, linked to Wikipedia articles, GEM
  trackers, OSM relations, and (via `P8947`) the WRI GPPD
  `gppd_idnr`. The right "join key" between [[wri_gppd]] +
  [[gem_global_energy_monitor]] + [[openinframap]] + Wikipedia.
- **Ownership chains**: every operating company is a Wikidata
  item with `P749` (parent org). Build the corporate ownership
  graph for the entire global power industry.
- **Wikipedia linkage**: every power plant in our warehouse
  has a Wikipedia article via `P910`. Link from the dashboard
  to the human-readable background.
- **Cross-language coverage**: Wikidata is available in 300+
  languages. A German energy journalist gets a German label;
  a Japanese one gets a Japanese one.
- **Type-ahead search**: "is there a power plant called X?"
  → check Wikidata. The disambiguation is built-in.

## See also

- [[wri_gppd]] — the frozen 2022 baseline
- [[gem_global_energy_monitor]] — the bi-annual curated tracker
- [[openinframap]] — the live OSM-based power infrastructure
- [[entso_e_outages]] + [[aemo_outages]] — generation units
  in EU + Australia
- [[socrata]] — the Socrata/CKAN pattern, also CC0 (US
  state / city / county open data portals)

## License of this connector note

`connectors/wikidata_power_plants.md` is dedicated to the public
domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

