# Hydro-Québec — Pannes en cours (Quebec Power Outages)

Key: `none required (public REST API + KMZ polygons)`
Endpoint: `https://pannes.hydroquebec.com/pannes/donnees/v3_0/bisversion.json`
Auth: `none`
Format: **JSON** (per-panne markers) + **KMZ** (per-panne polygon geometry)

Documentation:
- Dataset: https://donnees.hydroquebec.com/explore/dataset/pannes-interruptions/
- API documentation (French): https://donnees.hydroquebec.com/explore/dataset/pannes-interruptions/api/
- License: **Open Government Licence — Quebec** (similar to OGL 3.0, derivative use OK with attribution)
- Coverage: **Hydro-Québec service territory** (most of Quebec + parts of Ontario)
- Refresh: **continuous** (the `bisversion.json` is the BIS file version timestamp; the data itself updates per panne)

## What it is

**Hydro-Québec's** real-time power outage API, published through
the Données Ouvertes (Open Data) platform. The API is a
**3-step REST pattern** that returns a JSON list of active
outages plus a KMZ file with the geographic polygons of each
affected zone.

Hydro-Québec is the **provincial Crown corporation** that
generates, transmits, and distributes ~99% of Quebec's
electricity. Their outage data is the **right place for
Quebec** (and the right starting point for any Canadian
province-specific work).

## The 3-step API pattern

### Step 1: Get the current BIS version

```bash
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/bisversion.json'
# Returns: "20180418084019" (or similar timestamp)
```

The BIS (Bilan des Interruptions de Service) is the current
outage-balance snapshot. The version is a timestamp.

### Step 2: Get the per-panne JSON

```bash
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/bismarkers{BIS_VERSION}.json'
# e.g. https://pannes.hydroquebec.com/pannes/donnees/v3_0/bismarkers20180418084019.json
```

Returns a JSON array of currently active outages, each with:

- `id` (unique)
- `dateHeureDebut` (ISO 8601)
- `heurePrevueRétablissement` (ISO 8601, nullable)
- `nombreClientsAffectes` (integer)
- `cause` (French: `bris d'équipement`, `cause naturelle`, ...)
- `coordonnees` ([lon, lat])
- `zone` (polygon reference, see step 3)
- `mrc` (regional county municipality)
- `regionAdministrative` (administrative region)

### Step 3: Get the KMZ polygon overlay

```bash
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/bispoly{BIS_VERSION}.kmz'
# e.g. https://pannes.hydroquebec.com/pannes/donnees/v3_0/bispoly20180418084019.kmz
```

Returns a KMZ (zipped KML) of polygon overlays for each panne
zone. The `id` of each panne in step 2 matches a `<Placemark>` in
the KMZ.

## The planned-interruptions variant

The same pattern has a parallel "AIP" (Avis d'Interruptions
Planifiées) for **planned** outages:

```bash
# Step 1: get the AIP version
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipversion.json'
# Step 2: get the per-interruption JSON
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/aipmarkers{AIP_VERSION}.json'
# Step 3: get the KMZ polygon overlay
curl 'https://pannes.hydroquebec.com/pannes/donnees/v3_0/aippoly{AIP_VERSION}.kmz'
```

This is gold for the "scheduled maintenance" view.

## Per-location query (third-party documented)

A third-party GitHub project (`github.com/b13bs/Hydro-Quebec-power-outages`)
documents the **mobile-app API** that the Hydro-Québec iOS app
uses, with per-coordinates queries:

```bash
# By latitude
python hydro.py lat:45.5054
# By longitude
python hydro.py long:-73.615
```

This is undocumented and unofficial but the data shape is the
same as the open data API.

## How to wire it up for OpenTIR-Data

1. **First ingest**: poll step 1 (BIS version) every 5 minutes.
   When the version changes, fetch step 2 (markers JSON).
2. **Per-panne storage**: write to `osint.power_outages_ca` keyed
   by `id` (or `dateHeureDebut + coordonnees` for dedup).
3. **KMZ overlay**: store the polygon geometries in our
   `osint.outage_zones_ca` table for the Map view. Use a KML
   parser (e.g. Python's `fastkml`) to extract polygons.
4. **Geo-enrichment**: each panne's `coordonnees` + `mrc` + `region`
   give us lat/lon + Quebec administrative regions. Cross-ref
   with the GADM admin boundary layer.
5. **Planned interruptions**: parallel cron for the AIP endpoint
   gives us the "scheduled maintenance" view.
6. **Cross-check with PowerOutage.us**: for Quebec outages
   present in both, flag disagreements.

## Important caveats

| Caveat | Detail |
|---|---|
| **Hydro-Québec only** | Doesn't cover other Canadian provinces. For Ontario, IESO; for BC, BC Hydro; for the Maritimes, the per-province utilities. |
| **French-first metadata** | Cause names, region names, and most error messages are in French. Plan for `fr-CA` localization. |
| **No public historical archive** | The BIS / AIP endpoints are current-state only. For historical Hydro-Québec data, you need to poll and store every snapshot yourself. |
| **The 3-step pattern is manual** | You need to parse the version, substitute it, then fetch. There is no direct "give me all pannes" endpoint. |
| **OGL-Quebec (not CC0)** | Attribution required. Track in per-org audit logs. |
| **KMZ parsing is fragile** | KML/KMZ is XML in a zip; structure varies between providers. Use `fastkml` and write a per-feature sanity check. |

## What we use it for

- **Canada Map view**: per-panne polygon overlays on the Quebec
  map.
- **Real-time alerting**: 5-min cron → alert when
  `nombreClientsAffectes > 1000` for a single panne.
- **Planned maintenance calendar**: the AIP endpoint lets us show
  upcoming scheduled outages to tenants ahead of time.
- **Cold-weather resilience**: Hydro-Québec is famous for
  ice-storm resilience (1998 ice storm). The 3-step API lets us
  build historical comparison.

## See also

- [[odin]] — the US federal standard, same pattern
- [[national_grid_uk_connected_data]] — the UK, same CKAN pattern
- [[entso_e_outages]] — Europe transmission-level
- [[poweroutage_us]] — commercial 95% Canada coverage (US-focused,
  includes Quebec)

## License of this connector note

`connectors/hydro_quebec_pannes.md` is dedicated to the public
domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

