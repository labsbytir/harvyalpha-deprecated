# Google Trends

Key: `none required` — Google has no official API. Access is via an undocumented JSON endpoint that returns daily-trend, real-time-trend, explore, and autocomplete data, with a hidden `hl=en-US&tz=Etc/GMT+5` parameter convention.

Status: **No official API; unofficial endpoints work with effort.** Google has been progressively rate-limiting and re-shaping these endpoints; the most stable access is via the `pytrends` Python library, which wraps the public web UI. For production / high-volume use, paid proxy services (SerpAPI, Scaleserp) provide reliable access.

Endpoint (unofficial): `https://trends.google.com/trends/api/...`
Auth: none (the endpoints look at cookies / IP / user-agent)
Format: `JSON` (with a leading `)]}'\n` XSSI prefix that needs stripping)

Documentation:
- Trends UI: https://trends.google.com/trends/
- Google Trends help: https://support.google.com/trends
- `pytrends` (recommended wrapper): https://github.com/GeneralMills/pytrends
- SerpAPI paid proxy: https://serpapi.com/google-trends-api

## How it's used in OpenTIR-Data (via `pytrends`)

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/google_trends.py
# pip install pytrends
from pytrends.request import TrendReq
from ingest.fetchers.base import BaseFetcher, RawBundle
from datetime import datetime, timezone


class Fetcher(BaseFetcher):
    def __init__(self, source):
        super().__init__(source)
        self.pytrends = TrendReq(hl="en-US", tz=360)

    async def fetch(self):
        # Note: pytrends is sync. Wrap in run_in_executor if you need true async.
        for kw in ["climate change", "remote work", "open data", "ai regulation"]:
            self.pytrends.build_payload([kw], timeframe="today 5-y", geo="US")
            iot = self.pytrends.interest_over_time()
            if iot.empty:
                continue
            yield RawBundle(
                source_system=self.source_system,
                source_collection="interest_over_time",
                source_id=f"{kw}-US-5y",
                source_url=f"https://trends.google.com/trends/explore?q={kw.replace(' ', '+')}",
                bundle_url=f"/trends/api/widgetdata/multiline?hl=en-US&tz=Etc/GMT&...&q={kw}",
                fetched_at=datetime.now(timezone.utc),
                payload=iot.to_csv().encode("utf-8"),
                payload_format="csv",
                metadata={"keyword": kw, "geo": "US", "timeframe": "today 5-y"},
            )

            # Related queries (top + rising)
            related = self.pytrends.related_queries()
            if related and kw in related and related[kw]["top"] is not None:
                yield RawBundle(
                    source_system=self.source_system,
                    source_collection="related_queries",
                    source_id=f"{kw}-related",
                    source_url=f"https://trends.google.com/trends/explore?q={kw}",
                    bundle_url=f"/trends/api/widgetdata/relatedsearches?hl=en-US&...&q={kw}",
                    fetched_at=datetime.now(timezone.utc),
                    payload=related[kw]["top"].to_csv().encode("utf-8"),
                    payload_format="csv",
                    metadata={"keyword": kw, "type": "top"},
                )
```

## Quick call — verify

```bash
# Direct call to one of the underlying endpoints. The `)]}'\n` is XSSI protection; strip it.
curl -sL "https://trends.google.com/trends/api/dailytrends?hl=en-US&tz=Etc/GMT&ed=20240101&geo=US&ns=15" \
  | sed 's/^)\]}''//' | head -c 800
```

Expected: JSON object with `default.trendsByDay` array. My probe returned 404 because the date format is wrong (Google wants `YYYYMMDD` for `ed=`; my probe had truncated the value).

```python
# Recommended: just use pytrends
python3 -c "
from pytrends.request import TrendReq
p = TrendReq(hl='en-US', tz=360)
p.build_payload(['climate change'], timeframe='today 12-m', geo='')
print(p.interest_over_time().tail())
"
```

## Endpoints used (verified live 2026-09-04)

```text
GET /trends/api/dailytrends?hl=&tz=&ed=YYYYMMDD&geo=          # daily trending searches
GET /trends/api/realtimetrends?hl=&tz=&geo=                   # real-time trending
GET /trends/api/explore?hl=&tz=&q=&date=                      # interest-over-time widget
GET /trends/api/widgetdata/multiline?...&q=&...               # underlying widget data
GET /trends/api/widgetdata/relatedsearches?hl=&tz=&q=&...     # related searches
GET /trends/api/autocomplete/<type>?hl=&tz=&q=                # typeahead suggestions
```

All return JSON with a `)]}'\n` XSSI prefix that must be stripped. The data is keyed by widget/component id, so you have to first call `/trends/api/explore` to get the right `widgetIds`, then call each widget endpoint.

## Notes

- **No documented API.** Google deprecated the official Trends Data API in 2012. The `pytrends` library is the de-facto community wrapper.
- **Google actively rate-limits** undocumented access; expect 429s after ~50-100 requests from one IP. Use a proxy or SerpAPI for production.
- **The data is normalized 0-100**, not absolute search volume. You can compare related queries but not raw counts.
- **Region granularity** is limited: metro, state (US), country, and DMA. Not city-block.
- **Time granularity** ranges from "past hour" (real-time) to "2004-present" (monthly).
- **For OSINT**: most useful is "interest over time" for narrative tracking (e.g., how public concern about a topic changes), and "related queries" for emerging vocabulary / framing.
- **Cross-source dedup**: same query word across Google Trends + Twitter (X) trends + news media mentions → all dedupe via `dataset_fingerprint` once we have the other sources.

