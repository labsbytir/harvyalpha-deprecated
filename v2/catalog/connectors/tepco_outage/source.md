# TEPCO (Tokyo Electric Power) — outage data (NON-CONNECTOR, unofficial scrapers only)

Key: `none for official TEPCO; unofficial scrapers use a third-party API`
Endpoint (official): `https://teideninfo.tepco.co.jp/` (HTML, no API)
Endpoint (unofficial): `https://teiden.info/api/v1/latest/{prefecture}.json` (community-scraped)
Auth: `none`
Format: **HTML** (official) or **JSON** (unofficial scrapers)

Documentation:
- Official TEPCO: https://teideninfo.tepco.co.jp/
- Official TEPCO (English): https://www.tepco.co.jp/en/power/supply/outage.html
- Unofficial scraper (jp-power-outage): https://ryo-a.github.io/jp-power-outage/
- Per-prefecture JSON (unofficial): `https://teiden.info/api/v1/latest/{prefecture}.json`
- Mobile app: TEPCO速報 (push notifications for power outages)
- Coverage: TEPCO service territory (Tokyo, Kanagawa, Saitama,
  Chiba, Ibaraki, Tochigi, Gunma, Yamanashi, Shizuoka)

## ⚠️ No official API

**TEPCO** (Tokyo Electric Power Company) — one of the largest
electric utilities in the world, serving ~30 million customers
in the Kanto region — has **no public API** for outage data. The
official outage page is `https://teideninfo.tepco.co.jp/`, an
HTML page that's manually refreshed every few minutes.

This is a **documented non-connector** for OpenTIR-Data, like
the [[nypl_repo_api]] and [[transitwiki]] entries. We document
TEPCO so future contributors know the source exists, what the
shape would be, and which unofficial scrapers might be worth
using.

## What the official TEPCO page shows

The HTML at `https://teideninfo.tepco.co.jp/` shows:

- **Service area-wide** outage summary (count of homes without
  power)
- **Per-prefecture** outage list (9 prefectures: Tokyo,
  Kanagawa, Saitama, Chiba, Ibaraki, Tochigi, Gunma, Yamanashi,
  Shizuoka)
- **Per-municipality** detail (with address-level granularity
  for some events)
- **Per-event** detail with cause, restoration time, and
  "affected area" map

Each outage shows:
- 発生日時 (start time)
- 復旧日時 (restoration time, when known)
- 停電地域 (affected area)
- 停電軒数 (number of homes affected, bucketed into
  <1,000 / 1,000-10,000 / >10,000)
- 停電理由 (reason)
- 復旧見込み (restoration estimate)

The data is in Japanese. Translations required.

## The unofficial scrapers

### 1. jp-power-outage (ryo-a)

- GitHub: https://github.com/ryo-a/jp-power-outage
- Live data: https://ryo-a.github.io/jp-power-outage/
- API pattern:
  - Latest (per prefecture, refreshed every 10 min):
    `https://teiden.info/api/v1/latest/{prefecture}.json`
  - Historical: `https://teiden.info/api/v1/old/YYYY/MM/DD/{prefecture}/{prefecture}-HHmm.json`
- Covers: TEPCO only (9 prefectures in Kanto + Shizuoka)
- Maintainer: one person (ryo-a on GitHub)
- License: not declared in the repo README
- **Risk**: single-maintainer project, no SLA, can disappear
  without notice

### 2. Hydro-Quebec-style mobile API

The Qiita article notes that a third party discovered the
**mobile-app API** that the official TEPCO iOS/Android app uses
internally. This is undocumented, unofficial, and could break
whenever TEPCO updates their app.

## How to wire it up for OpenTIR-Data

1. **For shared warehouse (low confidence)**: if we need
   Japanese outage data, subscribe to the unofficial
   `teiden.info` API. Set a 10-min cron. Treat the source as
   "best effort, single point of failure" and have a fallback
   ready.
2. **For per-tenant**: a Japanese newsroom might want to scrape
   `teideninfo.tepco.co.jp` themselves. Build a small Playwright
   fetcher. Japanese locale + address-level parsing required.
3. **For historical**: there is no public historical archive.
   The per-event `停電履歴` (outage history) on the official site
   shows only the last 60 days.
4. **For the other 9 Japanese utilities** (Kansai, Chubu,
   Kyushu, Tohoku, Hokkaido, Chugoku, Shikoku, Hokuriku,
   Okinawa): each has its own outage page, with no public API.
   Same scrape pattern as TEPCO.

## Important caveats

| Caveat | Detail |
|---|---|
| **No official API** | The official page is HTML-only. Reverse-engineering is fragile. |
| **Unofficial scraper is single-maintainer** | `ryo-a` is a one-person project. The data could disappear. |
| **No public historical archive** | Only the current snapshot + 60-day per-event history. |
| **Japanese-only metadata** | All field names, region names, cause descriptions are in Japanese. Plan for `ja-JP` localization. |
| **Other 9 Japanese utilities not covered** | Kansai, Chubu, Kyushu, etc. each have their own pages. |
| **TEPCO's service area is large but not all of Japan** | ~30M of Japan's ~50M households. |

## What we use it for

- **Japan Map view**: TEPCO service territory (Kanto + Shizuoka)
  with per-municipality outage markers.
- **Real-time alerting**: 10-min cron → alert when TEPCO's
  prefecture total exceeds a threshold (typhoon, heat wave,
  earthquake).
- **Cross-source correlation**: Japan seismic activity (USGS,
  JMA) + TEPCO outages for post-earthquake restoration tracking.

## See also

- [[odin]] — the US federal standard
- [[entso_e_outages]] — Europe (some ENTSO-E data includes
  Japanese cross-border flows via the Japan-Korea HVDC)
- [[aemo_outages]] — Australia
- [[usoutage_com]] — the US WordPress scraper, documented as a
  non-connector (same pattern)

## License of this connector note

`connectors/tepco_outage.md` is dedicated to the public domain
under [CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/).
Attribution is appreciated but not required.

