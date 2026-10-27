# SocialMention

Key: `none required` — was a free social-search API. **Site and API are currently unreachable** from this network (HTTP 000). Status pending.

Status: **Site down.** All probes returned 000 (no route / no response). The project appears to have been deprecated or moved.

Endpoint (legacy, if it returns): `http://api.socialmention.com/search?q=<keyword>&type=articles|blogs|microblogs|comments|images|videos|news&q=<keyword>&lang=en`
Auth: none
Format: `JSON`, `XML`, `CSV` (legacy)

Documentation:
- Main site: http://www.socialmention.com/ (currently unreachable)
- API docs (legacy): http://www.socialmention.com/api (also unreachable)
- Last known stable: 2015-2018

## Recommended replacement

| Old SocialMention feature | Modern replacement |
|---|---|
| Real-time mention tracking | [[connectors/reddit]] + X (Twitter) API + [[connectors/google-trends]] |
| Sentiment analysis | Hugging Face Inference API: https://huggingface.co/docs/api-inference (free tier), or run a model locally with `transformers` |
| Top users / sources for a topic | Reddit r/all, Google News RSS, Mastodon public APIs |
| Daily volume for a keyword | Google Trends via `pytrends` |

## How to handle this in OpenTIR-Data

Don't write a fetcher for it. Instead, build the equivalent pipeline from the working sources above:

```python
# Ingest equivalent of SocialMention from working sources
import asyncio
from ingest.fetchers.reddit import RedditFetcher
from ingest.fetchers.google_trends import GoogleTrendsFetcher
# (X/Twitter is paid, see TwitterAPI.io or Apify)


async def track_mentions(keyword: str):
    reddit = RedditFetcher(...)
    trends = GoogleTrendsFetcher(...)
    reddit_bundles = [b async for b in reddit.fetch() if keyword in b.metadata.get("submission", {}).get("title", "")]
    trend_bundles = [b async for b in trends.fetch() if keyword in b.metadata.get("keyword", "")]
    return reddit_bundles, trend_bundles
```

## Notes

- **If you have an old SocialMention account** and it still works, the legacy API is at `api.socialmention.com/search?...` and returns JSON with `count`, `sentiment`, `top_keywords`, `top_users`, `top_sources`, `top_hashtags` per keyword.
- The project hasn't been actively maintained since ~2018. Modern OSINT tooling has moved to:
  - **Brand24 / Mention** (paid SaaS, $40-500/mo)
  - **Talkwalker** (paid, $500+/mo for enterprise)
  - **Reddit + X + Trends** (free, what we built above)
  - **Mastodon federated timeline search** (free, the Fediverse)
- For "what's being said about X on social media" — the closest free source is the **X (Twitter) advanced search** web page (no API), the **Reddit search API** (we have a connector), and **Mastodon public instance search** (FOSS).

