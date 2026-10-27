# situation.watch / Karnak (live OSINT video wall)

Key: `none required` — public, no auth, no API. The reference implementation is on GitHub.
Endpoint: `https://www.situation.watch/` (web app) + `https://github.com/mathdroid/karnak` (source)
Auth: none
Format: HTML SPA + YouTube live stream iframes

Documentation:
- Live app: https://www.situation.watch/
- Source (mathdroid/karnak): https://github.com/mathdroid/karnak
- Config source: https://raw.githubusercontent.com/mathdroid/karnak/main/app/main.py
- Pattern reference: "Karnak" is the codename for the situation.watch design (after the fortress of Ozymandias in *Watchmen*).

## What it is

**situation.watch** is a single-screen web dashboard that monitors a
fast-moving event through public sources. It combines multiple views on one
page:

- A **grid of live news video streams** (YouTube)
- An **AI-generated situation brief** (LLM over collected headlines)
- A **merged news timeline** (Google News + publisher RSS)
- An **activity map** (per-city report density)
- **Market indicators** (currency, stock index, macro)
- A **platform reachability panel** (block-detection probes)

It is **mathdroid's "Karnak" project**, deployed as a public web app. The
default configuration follows protests in Indonesia, but the same
"wall of monitors" pattern generalizes to any country or event.

The single most useful pattern for our use case is the **YouTube live
video wall** — the way situation.watch discovers, verifies, and embeds
multiple YouTube live streams on a single page.

## How the YouTube video wall works (the bit we want)

For each channel, situation.watch:

1. Has a curated list of YouTube channel IDs (in `app/main.py`, the
   `YT_CHANNELS` variable) — name, channel_id, handle.
2. Verifies each channel is **currently live** (via the YouTube Data API
   or a poll of the live page).
3. Embeds the live stream as an iframe using the canonical URL:
   ```
   https://www.youtube.com/embed/live_stream?channel={channel_id}
   ```
4. Renders all streams in a grid, with one-click audio focus switching.

The default channel list (8 Indonesian news channels) is in `app/main.py`.
For a global live TV hub, we want a curated list of ~25-30 international
news channels — see `/Users/penelope/Documents/opentir/data/live_tv_channels.json`
in our project.

## What's interesting for OpenTIR-Data

| Situation.watch feature | We can adopt for our dashboard |
|---|---|
| **YouTube live video wall** | Yes — multi-channel grid, audio focus, channel metadata |
| **AI situation brief** | Yes — feeds the "AI assistant" already in the design doc |
| **News timeline merge** | Yes — Google News + RSS, with dedup |
| **Activity map** | Yes — we already have a map view |
| **Market indicators** | Yes — Yahoo Finance + exchange APIs |
| **Platform reachability** | Yes — useful for "is X blocked in country Y" type questions |

## Quick verification (no key)

```bash
# The live web app
curl -sL -m 10 "https://www.situation.watch/" | head -c 500
# Expected: HTML SPA loading the JS bundle at /assets/index-*.js

# The source code
curl -sL "https://raw.githubusercontent.com/mathdroid/karnak/main/README.md" | head -30
```

## Notes

- **No public API** — the channel list and config are hardcoded in
  `app/main.py`. To use this pattern, fork or adapt the code.
- **License**: karnak repo is on GitHub but I didn't see a LICENSE file in
  the root listing. The README says "Pantau" is the project name and
  "Karnak" is the codename. **Check the LICENSE before forking.**
- **Our approach**: rather than forking situation.watch, we adopt the
  **YouTube live video wall pattern** in our own dashboard, with our
  own curated channel list (see `data/live_tv_channels.json` in our
  project) and our own geocoding (each channel is mapped to its HQ city
  on the world map).
- **Streaming source**: the live stream URL pattern
  `https://www.youtube.com/embed/live_stream?channel={channel_id}` is
  the official YouTube embed for live channels. It works for any
  YouTube channel that has "live" enabled. No YouTube Data API key
  needed for the embed itself; only needed if we want to detect when a
  channel is live vs offline.
- **Multi-region**: the same YouTube embed works for channels in any
  country. We can curate channels by region, language, and political
  alignment (objective fact, recorded in our channel data).
- **Live detection**: to know which channels are actually live at a
  given moment, you can either:
  - Use the YouTube Data API v3 with the `liveBroadcasts` endpoint
    (paid, free tier of 10k units/day)
  - Or use the YouTube RSS feed `https://www.youtube.com/feeds/videos.xml?channel_id=...`
    which shows the latest uploads (live streams appear there when started)
  - For v1, just show all channels and let YouTube handle the "live" /
    "offline" state in the iframe.

## License: check before forking

The karnak repo is on GitHub at `mathdroid/karnak`. As of 2026-09-05, the
LICENSE file is in the root but I haven't fetched its contents. Before
forking any code, read `LICENSE` and confirm terms.

For **using the pattern** (a video wall of YouTube embeds + a curated
channel list) — there's no IP involved. It's a standard web app
architecture. The channel IDs are public facts; the embed URL is a
public endpoint.

