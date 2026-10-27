# EAGLE-I (Environment for Analysis of Geo-Located Energy Information)

Key: `none required (CC-BY 4.0 bulk download on figshare)`
Endpoint: `https://figshare.com/articles/dataset/The_Environment_for_Analysis_of_Geoocated_Energy_Information_s_Recorded_Electricity_Outages_2014-2022/24237376`
Auth: `none`
Format: **CSV** (per-utility per-county, 2014-2022)

Documentation:
- Figshare bulk download: https://figshare.com/articles/dataset/The_Environment_for_Analysis_of_Geoocated_Energy_Information_s_Recorded_Electricity_Outages_2014-2022/24237376
- OpenEnergyHub summary: https://openenergyhub.ornl.gov/explore/dataset/eaglei_outages/
- Related DOI: https://doi.org/10.6084/m9.figshare.24237376
- License: **CC-BY 4.0** (with attribution to Oak Ridge National Laboratory)
- Maintainer: Oak Ridge National Lab
- Time range: **2014-01-01 through 2022-12-31** (8 years; superseded by ODIN going forward)
- Granularity: per-utility, per-county, per-outage event

## What it is

**EAGLE-I** was the original Oak Ridge National Lab outage data
platform, launched around 2014 after Hurricane Sandy to give
emergency-management agencies a real-time view of power outages
across the US. It ran continuously from 2014 to 2022.

In **2022, ORNL launched ODIN** (the Outage Data Initiative
Nationwide) to standardize the data interchange format
(CIM IEC 61968-3 / MultiSpeak v4.1+) and expand coverage. ODIN
is the real-time successor; EAGLE-I's bulk download is the
**historical archive** of the original platform.

The Feb 2026 ORNL deck says: *"Standardized Outage data (from
ODIN) is now ingestible into DOE's real-time situational awareness
platform, EAGLE-I."* — so EAGLE-I is now the **archive viewer** for
ODIN data, with the 2014-2022 history still downloadable as bulk
CSV.

## What the data covers

The figshare bulk download is a **single CSV** (8 GB) with the
following columns (per ORNL's data documentation):

- `utility_id` (stable ODIN/EAGLE-I ID)
- `utility_name`
- `state`, `county` (FIPS names)
- `outage_start_time` (ISO 8601)
- `outage_end_time` (ISO 8601, nullable if active at snapshot)
- `customers_out` (peak, integer)
- `customers_served` (per-county baseline)
- `cause` (free text)
- `causekind` (enum: `equipment_failure`, `severe_weather`, `public_damage`, `unknown`, ...)
- `geom` (per-county GeoJSON polygon)

The dataset contains **~2 million outage events** across 8 years
(roughly 250,000/year average), covering the major US
weather-and-grid events: Hurricane Matthew (2016), Hurricane
Harvey (2017), Hurricane Irma (2017), Hurricane Michael (2018),
the Texas winter storm Uri (Feb 2021), Hurricane Ida (2021), and
the Southwest heat dome (2021).

## How to wire it up for OpenTIR-Data

1. **First ingest**: download the 8 GB CSV from figshare once on
   setup. Store in ClickHouse as a columnar table; partition by
   `state` and `outage_start_year`.
2. **Per-utility rollup**: aggregate to
   `osint.power_outages_us_historical_utility_year` with
   `(utility_id, year, total_customers_out, mean_outage_duration)`.
3. **Major event detection**: filter on
   `customers_out > 100000 AND causekind = 'severe_weather'` to
   find the big storms; cross-reference with the NOAA Storm Events
   database (already in our `noaa_storm_events` source set).
4. **ODIN join**: this archive is the *backfill* for ODIN. The
   ODIN public endpoint carries only the current snapshot;
   EAGLE-I has 8 years of history. Join on
   `(utility_id, outage_start_time)` to reconstruct
   "this happened before" timelines.

## Important caveats

| Caveat | Detail |
|---|---|
| **8 GB bulk CSV** | The figshare download is one big CSV. Use `pandas` with chunked reading, or convert to Parquet on first ingest. |
| **Data is 2014-2022** | For 2023+ data, use ODIN (real-time) or PowerOutage.us (historical archive since 2016). |
| **Per-utility reporting quality varies** | Some smaller coops report less frequently or with less detail. The 2M events are unevenly distributed. |
| **CC-BY 4.0 (not CC0)** | Attribution to ORNL is required when redistributing. Track this in our per-org audit log. |
| **EAGLE-I is now the ODIN archive** | Going forward, ODIN's public endpoint + private subscriber feed replaces EAGLE-I. The 2014-2022 data is what EAGLE-I is good for. |
| **No real-time query** | EAGLE-I bulk is 2014-2022 only. For current data, use ODIN or PowerOutage.us. |

## What we use it for

- **Historical storm reconstruction**: "how does Hurricane Helene
  2024 compare to Hurricane Irma 2017?" — answer with per-utility
  per-county outage counts.
- **Climate trend analysis**: 8 years of per-county outage data
  lets us correlate with NOAA storm events, FEMA disaster
  declarations, and EIA generation outages to find patterns.
- **Per-utility reliability scoring**: SAIDI / SAIFI / CAIDI
  calculations (System Average Interruption Duration / Frequency /
  Customer Minutes) — the IEEE 1366 standard metrics. We can
  compute these for every US IOU and cooperative.
- **ODIN backfill**: for any tenant asking "what was the outage
  pattern in X county in 2019?" we use EAGLE-I.

## See also

- [[odin]] — the real-time successor, also ORNL
- [[doe-oe417]] — federal major-event reports (complementary
  event-level data)
- [[poweroutage_us]] — commercial 2016+ archive
- [[openenergyhub_event_correlated]] — the EAGLE-I + OE-417 +
  Census synthesized dataset (CC0)

## License of this connector note

`connectors/eagle_i.md` is dedicated to the public domain under
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

