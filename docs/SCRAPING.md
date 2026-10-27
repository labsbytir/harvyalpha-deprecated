# Public profile snapshots

This project's scraper runs through Spider Unlimited with an optional Webshare
proxy. It does not start a local browser or accept logged-in account cookies.

Set `SPIDER_API_KEY` and `WEBSHARE_PROXY_URL` in the shell environment. The proxy
value is an endpoint URL (`http://user:password@host:port`), not a Webshare API key.
Never commit credentials. Collected data is excluded by `.gitignore`.

```bash
python3 -m v1.scrape.facebook https://www.facebook.com/debra.holbrook1/ \
  --out data/debra.holbrook1
python3 -m unittest discover -v
```

Choose a new output directory for each new run. Existing post files are not
silently overwritten or mixed with another snapshot.

## Output

- `raw/`: complete API responses for attempted sections and discovered post URLs.
- `posts/`: one JSON file per exposed post explicitly associated with the target.
- `profile-details.json`: identity, exposed About fields and external links.
- `manifest.json`: per-section outcomes and explicit completeness limitations.
- `linked-profiles/`: automatically scraped bio-linked social profiles, each with
  raw evidence, normalized details and separate JSON files for exposed posts.
- `linked-profiles/network.json`: evidence-backed `bio_links_to` edges; these do
  not assert that matching handles belong to the same person.

No image/video files are downloaded. Raw responses may contain media URLs and
profile-photo metadata; normalized post files omit images.

## Coverage

Attempts the profile, About subsections, friends/followers/following, liked Pages,
events, map, posts and reels. These are requested surfaces, not a guarantee that
the platform exposes list members anonymously. Requests explicit cloud scroll/wait
steps and stores observable scroll positions; HTTP 200 alone does not verify scrolling.
Up to 100 discovered post
permalinks are fetched by default; use `--max-posts N` to change that bound.

This is a best-effort anonymous snapshot, not a guaranteed full profile archive.
Pagination cursors are retained in raw evidence but not replayed. A successful
HTTP response may still be a login page or omit posts. The manifest remains
`complete: false`; absent posts must not be interpreted as an empty account.

## Automatically follow social bio links

New Facebook runs follow recognized bio-linked profiles automatically, then their
bio links, deduplicating canonical URLs. The default limit is 20 destinations;
use `--max-linked-profiles N` (zero disables it). Only bio/profile fields and
`rel="me"` links qualify, not every link in posts or comments.

## X / Twitter via Spider

`v1/scrape/x.py` is already the X adapter used by the shared profile pipeline. Its consent-gated CLI uses the Spider Unlimited `/unlimited/scrape` endpoint and `WEBSHARE_PROXY_URL`; it does not call a metered `/fetch` endpoint or the former Xquik client.

```bash
python3 -m v1.scrape.x NASA --consent data/x-consent.json \
  --out data/x/nasa.json --max-posts 25
```

The adapter uses plain HTTP mode, retains the raw Spider response, and normalizes only exposed target-authored posts and engagement fields. Completeness remains `false`; unavailable timeline pages are not treated as no posts.

For an existing snapshot without repeating the Facebook scan:

```bash
python3 -m v1.scrape.profiles data/jason.n.moore.9 --max-profiles 20
```

## Truth Social via Spider

`v1/scrape/truthsocial.py` adapts Truth Social public profile and timeline collection via Spider Unlimited (`/unlimited/scrape`) and `WEBSHARE_PROXY_URL`. It uses public Mastodon-compatible endpoints (`/api/v1/accounts/lookup` and `/api/v1/accounts/:id/statuses`), parses author-verified statuses and engagement metrics (favourites, reblogs, replies), and integrates with the shared `v1/scrape/profiles.py` and `v1/scrape/protocol.py` pipeline.

```bash
python3 -m v1.scrape.truthsocial realDonaldTrump --max-posts 25 --out data/truthsocial/trump.json
```


The registry includes all 21 supplied Spider recipe pages: X, Bluesky, Instagram,
SSSInstagram, both Threads domain recipes, LinkedIn, Quora, Mastodon, Discord,
TikTok, Substack, Medium, Twitch, YouTube, Truth Social, Blogspot, Steam Community,
GitHub Blog, bsky.social and EuropeFreeChat. Both Threads domains use the same adapter.
Network adapters live under `v1/scrape/`; app jobs use the versioned envelope in
`v1/scrape/protocol.py`, and Spider requests go through `v1/scrape/client.py`. Facebook,
Instagram, Threads, and X have named adapters; remaining supported profiles share
the common public-profile adapter. No local browser is required by these scripts.

SSSInstagram is treated as a utility, not an Instagram identity. Discord invites
are community links, not proof of a personal account; private channels are not
crawled. Public Mastodon-style `rel="me"` links may target other instances;
non-public DNS destinations are rejected before requesting them.

Extraction supports exposed X/Bluesky/Instagram/Threads/TikTok/Mastodon structured
records and standard JSON-LD articles/posts/videos. Other structured records are
retained in raw evidence rather than guessed. This is not a claim that every
platform's entire history is available anonymously, and login-page detection is
best-effort. No posts returned means unavailable or unexposed, not an empty account.

YouTube channel/handle links and Steam vanity/numeric profile links are recognized;
ordinary video URLs and workshop files are not profile links. Blogspot blogs and
GitHub Blog's homepage are publications; GitHub Blog author pages are profile links.
The GitHub Blog recipe is not a claim of GitHub account/repository extraction.
`bsky.social` is Bluesky's service site, while `bsky.app/profile/...` identifies an
account. EuropeFreeChat and Steam group links are public communities, not personal
identities; the scraper does not join rooms or access private conversations.
