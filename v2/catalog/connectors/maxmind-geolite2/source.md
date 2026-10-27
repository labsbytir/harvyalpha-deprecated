# MaxMind GeoLite2 (free IP geolocation)

Key: `pending — register free at https://www.maxmind.com/en/geolite2/signup` (free for non-commercial; commercial use requires paid GeoIP2)
Endpoint: `https://www.maxmind.com/en/geoip-lite-databases` (download) + `https://www.maxmind.com/en/geoip2-precision-demo-service` (web service)
Auth: MaxMind account (free) for downloads; license key for web service
Format: **CSV** (downloads), **JSON** (web service)

Documentation:
- Home: https://www.maxmind.com/en/geolite2
- Signup: https://www.maxmind.com/en/geolite2/signup
- Country accuracy: ~99.5% (CC-by-country), city accuracy ~75-85% in US/EU
- Download formats: https://www.maxmind.com/en/geoip-lite-databases
- Web service docs: https://dev.maxmind.com/geoip/geoip2/web-services/

## What it is

**MaxMind GeoLite2** is the world's most-cited **IP-to-location** database.
Given any IP address, it returns the country, region, city, lat/lon, and
ISP/network. Used by every major ad-tech, fraud-detection, and analytics
company.

- **Free** for non-commercial use
- **Paid** for commercial use (GeoIP2 — $30-$600/month depending on volume)
- Updated monthly
- Available as CSV download (build your own lookup) or as a web service

**Not for street-address geocoding** (use Nominatim / Overture Maps for
that). This is for **"where is the user connecting from"** — useful for
our dashboard's "your region" feature, fraud detection, and
analytics.

## Quick call — verify (after signup)

```bash
# After registering, download the GeoLite2-City.mmdb file
# Then query with any MaxMind client
python3 -c "
import geoip2.database
reader = geoip2.database.Reader('/srv/working/GeoLite2-City.mmdb')
response = reader.city('8.8.8.8')
print(f'IP: 8.8.8.8')
print(f'  country: {response.country.name} ({response.country.iso_code})')
print(f'  city: {response.city.name}')
print(f'  location: ({response.location.latitude}, {response.location.longitude})')
print(f'  timezone: {response.location.time_zone}')
"
# Expected: country=US, city=Mountain View, lat=37.4, lon=-122.0

# Or use the web service
curl -sL "https://geoip.maxmind.com/geoip/v2.1/city/8.8.8.8?demo=1" | python3 -m json.tool
# Expected: full JSON response with country, city, lat, lon
```

## Notes

- **License**: free for non-commercial use. **Commercial use requires
  GeoIP2** (paid). Read https://www.maxmind.com/en/geolite2-licensing
  for the exact terms.
- **Accuracy**: ~99.5% country, ~85% city (in US/EU), ~70% in
  Asia/Africa. For our use case (showing the user which region they're
  in), country accuracy is fine.
- **For the dashboard's "your region" feature**: useful for showing the
  user which region's content is most relevant to them. Also useful
  for fraud detection (sign-in from a new country, impossible travel).
- **Self-host vs web service**: the CSV download + your own lookup
  (`geoip2.database.Reader`) is the **fastest, free, and self-hostable**
  path. The web service is paid for high-volume.
- **Update cadence**: monthly. Subscribe to the changelog.
- **File size**: GeoLite2-City.mmdb is ~70 MB. GeoLite2-Country.mmdb
  is ~5 MB. GeoLite2-ASN.mmdb is ~10 MB. All trivial to host.

## License: free for non-commercial, paid for commercial

Per https://www.maxmind.com/en/geolite2-licensing:

> GeoLite2 databases are free for any use, but require attribution
> when used in a commercial product.

For our product:
- **Open-source self-host users**: free, attribution required ("This
  product includes GeoLite2 data created by MaxMind, available from
  https://www.maxmind.com/")
- **Hosted tier (paid)**: we need to either attribute or upgrade to
  GeoIP2. The attribution requirement is reasonable to comply with.

The attribution text must be in the product's "About" page or similar
location. Recommended placement: in the footer of every page, or in
the dashboard's "About" modal.

## Implementation in our project

For v1, we use GeoLite2 to:
1. Set the default org location (e.g., "This org is in New York, US")
2. Default the dashboard's region filter to the user's country
3. Flag unusual sign-ins for the audit team

Self-host the .mmdb file in `/var/lib/maxmind/`, updated monthly via cron.
Use the `geoip2` Python library for lookups. Cache results in ClickHouse
for 24 hours to avoid hammering the lookup on every request.


## Migrated Context (From GDELT 2.0 Global Events Database.md)

---
tags: [source, conflict, info_environment, governance, tier-2, osint-data, mvp]
status: active
display_name: "GDELT 2.0 Global Events Database"
fetcher: ingest.fetchers.gdelt
source_name: gdelt
---

# GDELT 2.0 Global Events Database

Global Database of Events, Language, and Tone — monitors broadcast, print, and web news in 100+ languages, extracts events using the CAMEO event taxonomy, codes tone. Updated every 15 min. ~3 TB+ historical, 250+ categories of events.

## Metadata

| Field | Value |
|---|---|
| Source system | `gdelt` |
| Base URL | https://www.gdeltproject.org |
| API base | https://api.gdeltproject.org/api/v2 |
| Schedule (cron) | `0 14 * * *` (daily at 14:00 UTC) |
| Rate limit | 12 req/min |
| Tier | 2 |
| Axis | conflict, info_environment, governance |
| License | CC-BY (data); research-use only |
| Auth | none (public) |
| per_tenant_only | false |

## Collections

| Name | Query | Notes |
|---|---|---|
| `top_articles_en` | `sourcelang:english`, `timespan=1day`, `max_articles=250` | top 250 English articles/day |

## Fetcher

`ingest/fetchers/gdelt.py` (uses Doc 2.0 + TV API + GKG)

## Storage

Lands in ClickHouse `osint.bundles` with `source_name='gdelt'`. Per-event rows: `GlobalEventID`, `Day`, `Actor1Code`, `Actor2Code`, `EventCode`, `QuadClass`, `GoldsteinScale`, `AvgTone`, `ActionGeo_Lat`, `ActionGeo_Long`, `SOURCEURL`.

## Common queries

```
GET /v1/sources/gdelt
GET /v1/sources/gdelt/bundles?eventcode=14&since=2026-09-01
GET /v1/sources/gdelt/aggregates?group_by=eventcode,country
```

## Gotchas

- GDELT's "event" granularity is per-article, not per-incident. Multiple articles about the same event = multiple rows.
- `AvgTone` is normalized to roughly -100 to +100; negative = negative tone.
- The full GDELT 2.0 raw tables are on BigQuery (free public dataset) for historical analysis.

## Related

- [[Plan/MVP Sources]] (one of the 12)
- [[Plan/Source Categorization]] (conflict + info_environment + governance axes)
- [[Ingestion/ACLED — Armed Conflict Location & Event Data Project]] (structured conflict data)
- [[Ingestion/Harvard Crowd Counting Consortium (US Protests)]] (unrest data)
