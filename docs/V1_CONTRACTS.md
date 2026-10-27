# Harvy Scraping V1 Contracts Inventory

This document freezes the contracts, input parameters, output schemas, completeness signals, and retry behavior of all Harvy v1 scraping and research collectors. It serves as the regression baseline for V2 migration.

## 1. Social Profile Collectors

### 1.1 Facebook Collector (`v1.scrape.facebook`)
- **Entrypoint:** `python3 -m v1.scrape.facebook <url> --out <dir> [--max-posts N] [--max-linked-profiles N]`
- **Inputs:**
  - `url`: Public HTTPS URL (`https://facebook.com/<handle>` or `https://www.facebook.com/<handle>`). No credentials, no nested query parameters.
  - `--out`: Destination directory path.
  - `--max-posts`: Positive integer (default 100).
  - `--max-linked-profiles`: Non-negative integer (default 20, 0 disables recursive following).
- **Environment:** `SPIDER_API_KEY` (required), `WEBSHARE_PROXY_URL` (optional, proxied via Webshare).
- **Disk Artifacts:**
  - `raw/`: Full Spider responses per attempted section and discovered post permalink.
  - `posts/<post_id>.json`: Normalized post object (`id`, `url`, `platform`, `text`, `timestamp`, `ownership_verified`).
  - `profile-details.json`: Normalized profile object (`platform`, `url`, `name`, `bio`, `links`, `about`).
  - `manifest.json`: Execution manifest with `target`, `sections`, `complete: false`, and `captured_at`.
  - `linked-profiles/`: Recursively captured bio-linked profile folders.
  - `linked-profiles/network.json`: Directed graph with `nodes` and `edges` (`bio_links_to`).
- **Completeness Signals:**
  - `complete` is always `false` on anonymous public captures.
  - Absence of posts or fields denotes unexposed/login-gated content, not an empty account.
- **Retry & Failure Handling:**
  - Spider HTTP timeout: 120s.
  - Handles `HTTPError`, `URLError`, `TimeoutError`, returning structured failures in manifest without silent corruption.

### 1.2 Social Profile Recipe Registry (`v1.scrape.profiles`)
- **Entrypoint:** `python3 -m v1.scrape.profiles [--url <url> | --dir <dir>] --out <dir> [--max-profiles N]`
- **Supported Recipes (21 endpoints):**
  - Identity platforms: `x` (`x.com`, `twitter.com`), `bluesky` (`bsky.app/profile/*`), `instagram` (`instagram.com/*`), `threads` (`threads.net/*`, `threads.com/*`), `linkedin` (`linkedin.com/in/*`), `quora` (`quora.com/profile/*`), `mastodon` (`mastodon.social/*`, etc.), `tiktok` (`tiktok.com/*`), `substack` (`*.substack.com`), `medium` (`medium.com/*`), `twitch` (`twitch.tv/*`), `youtube` (`youtube.com/@*`, `youtube.com/channel/*`), `truthsocial` (`truthsocial.com/@*`), `steam` (`steamcommunity.com/id/*`, `steamcommunity.com/profiles/*`).
  - Communities & Utilities: `discord` (`discord.gg/*`, community invite), `europefreechat` (`europefreechat.com`), `sssinstagram` (`sssinstagram.com`, utility).
  - Publications: `blogspot` (`*.blogspot.com`), `github-blog` (`github.blog/author/*`).
  - Service sites: `bsky.social`.
- **Validation:** SSRF protection rejects private IP resolutions (`validate_public_destination`).
- **Outputs:** `profile-details.json`, `posts/*.json`, `raw/*.json`, `network.json`.
- **Completeness Signals:** Best-effort anonymous extraction; author verification required for posts.

### 1.3 Username Footprint Scanner (`v1.scrape.username`)
- **Entrypoint:** `python3 -m v1.scrape.username --username=<name> --out=<dir> [--category=<cat> ...]`
- **Inputs:**
  - `username`: 1–64 characters matching `[\w.-]{1,64}`.
  - `categories`: One or more of 19 WhatsMyName categories (`archived`, `art`, `blog`, `business`, `dating`, `finance`, `gaming`, `health`, `hobby`, `images`, `misc`, `music`, `news`, `political`, `search`, `shopping`, `social`, `tech`, `video`, `xx NSFW xx`).
- **Outputs:**
  - `results.json`: `{"username": str, "checked_count": int, "duration_seconds": float, "matches": [{"name": str, "category": str, "url": str, "status": "found"}]}`.
- **Completeness Signals:** Per-target status (`found`, `not_found`, `error`); aggregate `checked_count` vs catalog.

---

## 2. Legal and Geospatial Research Collectors

### 2.1 Research Runner (`v1.scrape.research`)
- **Entrypoint:** `python3 -m v1.scrape.research --input <request.json> --out <dir>`
- **Modes:** `"legal"` and `"map"`.

#### Legal Mode Inputs & Sources:
- `query`: String between 2 and 200 characters.
- `first_name`: String <= 80 characters.
- `last_name`: String <= 80 characters.
- `state`: Two-letter US state code (validated against `ARREST_STATE_SLUGS`).
- `sources`: Subset of:
  - `courtlistener`: REST search (`type=o`, page size 10). Auth via `COURTLISTENER_API_TOKEN` (optional). Status `ok` (200) or `inconclusive`.
  - `case_law`: Caselaw Access Project search. Auth via `CASELAW_API_TOKEN`. Status `ok` if JSON returned, else `api_unavailable`.
  - `judyrecords`: Search via Spider Unlimited with `X-Api-Key` header (`JUDYRECORDS_API_KEY`), or direct session-cookie proxy mining via `WEBSHARE_PROXY_URL` with automatic candidate query extraction. Status `ok`, `not_configured`, or `inconclusive`.
  - `docket_alarm`: REST login + search. Auth via `DOCKETALARM_USERNAME` + `DOCKETALARM_PASSWORD`. Status `ok`, `not_configured`, or `inconclusive`. Retrieval is indexed search only; no live PACER fetch.
  - `arrests_org`: Spider Unlimited scrape of state arrest subdomain. Requires `first_name`, `last_name`, `state`. Saves HTML; status `page_captured` (200) or `inconclusive`.
  - `court_record`: Link-out only (`link_only`). Terms restrict scraping/commercial reuse.
  - `google_scholar`: Link-out only (`link_only`). No verified public API.

#### Map Mode Inputs & Sources:
- `latitude`: Float between -90 and 90.
- `longitude`: Float between -180 and 180.
- `sources`:
  - `mapillary`: Graph API image search (radius 50m, limit 10). Auth via `MAPILLARY_ACCESS_TOKEN`. Status `ok` or `not_configured`.
  - `zoom_earth`: Link-out only (`link_only`).
  - `opensfm`: Tool reference (`tool_reference`).

- **Outputs:**
  - `raw/<source>.json`: Captured payload from each source.
  - `results.json`: List of source result summaries (`source`, `status`, `result_count`, `url`, metadata notes).
- **Completeness Signals:**
  - `ok`: Successful HTTP 200 with structured JSON response.
  - `inconclusive`: Non-200 or unexpected payload format.
  - `page_captured`: Raw HTML preserved for verification.
  - `link_only` / `tool_reference`: Source lacks public API or has contractual scraping prohibitions.
  - `not_configured`: Credential absent in environment.
  - `api_unavailable`: Source endpoint offline or responding with invalid format.
- **Constraints & Quotas:**
  - Direct request size cap: 4 MB (`MAX_SOURCE_BYTES = 4_000_000`).
  - Timeout: 45s for direct requests, 120s for Spider requests.
  - Proxied via Webshare proxy when required.

---

## 3. Geospatial Places Collector

### 3.1 Google Maps (`v1.scrape.google_maps`)
- **Entrypoint:** `python3 -m v1.scrape.google_maps <url> --out <dir>`
- **Inputs:** `https://www.google.com/maps/place/...`
- **Spider Endpoint:** `/unlimited/scrape`. Never metered `/fetch`.
- **Outputs:** `raw/raw.json`, `place-details.json` (JSON-LD business facts), `reviews/*.json`.
- **Completeness Signals:** Explicitly marked partial; reviews capped to initial page.

---

## 4. Frozen Sanitized Fixtures Matrix

The following regression test fixtures are frozen under `tests/fixtures/v1/`:
- `facebook/`: `manifest.json`, `profile-details.json`, `posts/post-1.json`.
- `social/`: `instagram_post.json`, `threads_post.json`, `x_tweet.json`, `network.json`.
- `username/`: `results.json`.
- `legal/`: `courtlistener_results.json`, `case_law_results.json`, `judyrecords_results.json`, `docket_alarm_results.json`, `arrests_org_page.json`, `research_results.json`.
- `map/`: `mapillary_results.json`, `map_results.json`.