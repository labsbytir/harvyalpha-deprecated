# ENTSO-E Transparency Platform — European Outages

Key: `pending — request a security token at https://transparency.entsoe.eu by emailing transparency@entsoe.eu with subject "Restful API access" (free, ~1-2 business day)`
Endpoint: `https://web-api.tp.entsoe.eu/api`
Auth: **security token** in `?securityToken=<token>` query parameter
Format: **XML** (IEC 62325 format)

Documentation:
- Landing: https://transparency.entsoe.eu/
- Outage domain: https://transparency.entsoe.eu/outage-domain/r2/unavailabilityInTransmissionGrid/show
- API documentation: https://documenter.getpostman.com/view/14764470/Uyr5nL3q
- apis.io entry: https://apis.io/apis/entso-e/entso-e-market-data-query-api/
- License: **free for non-commercial use** (commercial requires a separate agreement)
- Coverage: **all 61 EU bidding zones** + neighboring countries (Norway, Switzerland, UK pre-Brexit, etc.)
- Refresh: **daily** for many datasets; some (like generation outages) update within hours

## What it is

**ENTSO-E** (European Network of Transmission System Operators
for Electricity) is the umbrella organization for European
electricity TSOs. Their **Transparency Platform** publishes a
single REST API endpoint that returns any of 60+ datasets via
the IEC 62325 standard, including:

- **Generation outages** (`get_generation_outages`) — planned and
  forced outages of generation units, per bidding zone
- **Transmission outages** (`get_transmission_outages`) —
  planned and forced outages of transmission assets (lines,
  transformers) between bidding zones
- **Load** (`get_actual_total_load`, `get_load_forecast`)
- **Day-ahead prices** (`get_day_ahead_prices`)
- **Cross-border flows** (`get_cross_border_flow`)

For OSINT-Data v1, the **outage endpoints** are the most useful:
they tell us *why* the European grid is constrained right now.

## Critical distinction: this is transmission, not customer-level

ENTSO-E outages are **transmission-level** — a generation unit
tripping, a major interconnector being taken out for maintenance.
They are **not** "X customers are without power" — that's
typically the responsibility of **distribution-level** operators
(DNOs in the UK, distribution system operators in other EU
countries), and the data lives in **per-utility** outage maps
that are not aggregated at the EU level.

So ENTSO-E is the **right source for understanding why a country
or bidding zone is experiencing grid stress**, but not for
counting how many homes are out.

## The data shape (per IEC 62325)

A generation outage record:

```xml
<Publication_MarketDocument xmlns="urn:iec62325.351:tc57wg16:451-6:generationlifecycle:3:2">
  <mRID>...</mRID>
  <revisionNumber>1</revisionNumber>
  <type>A72</type>  <!-- A72 = unavailability -->
  <sender_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</sender_MarketParticipant.mRID>
  <sender_MarketParticipant.marketRole.type>A32</sender_MarketParticipant.marketRole.type>
  <receiver_MarketParticipant.mRID codingScheme="A01">10X1001A1001A450</receiver_MarketParticipant.mRID>
  <receiver_MarketParticipant.marketRole.type>A33</receiver_MarketParticipant.marketRole.type>
  <createdDateTime>2026-09-05T00:00:00Z</createdDateTime>
  <period.timeInterval>
    <start>2026-09-05T00:00Z</start>
    <end>2026-09-12T00:00Z</end>
  </period.timeInterval>
  <TimeSeries>
    <mRID>1</mRID>
    <businessType>A37</businessType>  <!-- A37 = unavailability -->
    <BiddingZone_Domain.mRID codingScheme="A01">10Y1001A1001A39H</BiddingZone_Domain.mRID>
    <quantity_Measure_Unit.name>MAW</quantity_Measure_Unit.name>  <!-- MW -->
    <curveType>A01</curveType>
    <Period>
      <timeInterval>
        <start>2026-09-05T00:00Z</start>
        <end>2026-09-12T00:00Z</end>
      </timeInterval>
      <resolution>PT60M</resolution>
      <Point>
        <position>1</position>
        <quantity>500</quantity>  <!-- 500 MW unavailable -->
      </Point>
    </Period>
  </TimeSeries>
</Publication_MarketDocument>
```

The query pattern is:

```bash
curl 'https://web-api.tp.entsoe.eu/api?securityToken=YOUR_TOKEN&documentType=A72&biddingZone_Domain.mRID=10Y1001A1001A39H&periodStart=202609050000&periodEnd=202609120000'
```

## How to wire it up for OpenTIR-Data

1. **First ingest**: get a security token, then call
   `get_generation_outages` and `get_transmission_outages` for
   the 10-20 most-active EU bidding zones (DE, FR, ES, IT, PL,
   NL, BE, SE, NO, etc.). Cache responses for 1 hour.
2. **XML parse**: use Python's `lxml` or the `entsoe-py` client
   library (https://github.com/EnergieID/entsoe-py) to parse the
   IEC 62325 XML.
3. **Per-bidding-zone rollup**: store to
   `osint.entsoe_outages` keyed by `(bidding_zone, mRID, period_start)`.
4. **Geo-enrichment**: each `BiddingZone_Domain.mRID` maps to a
   known European country / region. Add ISO 3166 + NUTS codes.
5. **Cross-source correlation**: join with ODIN (US outages) and
   PowerOutage.us (US/CA/UK outages) on `timestamp` for global
   grid stress analysis.

## Important caveats

| Caveat | Detail |
|---|---|
| **Free for non-commercial only** | Commercial use needs a separate ENTSO-E agreement. Our hosted / multi-tenant product is commercial. |
| **Per-tenant token recommended** | For our project, each EU-region tenant should have their own security token, not a shared one. |
| **XML is verbose** | IEC 62325 is a verbose standard. Use `entsoe-py` or a thin wrapper. |
| **This is transmission, not customer-level** | See the critical distinction above. ENTSO-E outages are not "X customers are out." |
| **Refresh is per-endpoint** | Generation outages: per event (continuous). Transmission outages: per event. Day-ahead prices: daily. Check the docs per endpoint. |
| **Per-zone quota** | The free tier has a request limit. Use the `entsoe-py` client with proper rate-limiting. |
| **No outage maps / no GeoJSON** | All responses are XML. The `entsoe-py` client converts to pandas DataFrames. |

## What we use it for

- **EU Map view**: per-bidding-zone outage summary as a choropleth
  layer (the 61 EU zones as polygons).
- **Time series**: per-zone generation outage MW over time, for
  understanding "why is the French grid short this winter?"
- **Network view**: bidding-zone interconnection outages as graph
  edges, with the bidding zones as nodes.
- **Story view**: when a country like France experiences a
  cold-snap-driven grid stress event, ENTSO-E outages tell us
  *why* (e.g. 4 nuclear plants offline for maintenance, 6 GW of
  unplanned outages).

## See also

- [[odin]] — the US federal standard
- [[aemo_outages]] — the Australian equivalent (NEMWeb)
- [[national_grid_uk_connected_data]] — UK distribution-level
  outages
- [[poweroutage_us]] — commercial customer-level aggregator

## License of this connector note

`connectors/entso_e_outages.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

