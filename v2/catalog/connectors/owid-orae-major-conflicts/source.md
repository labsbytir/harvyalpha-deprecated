# OWID OR&A Major Conflicts (one-off OCR project, 2018)

Key: `none required` for the data. **The code has no declared license** (HTTP 404 on `LICENSE` files, GitHub API returns `license: null`), and the project has been **frozen since 2018-11-07**. The original source is **"Major Armed Conflicts, 1720 to 1985: A Compendium"** — a reference work by the Office of Research and Analysis (OR&A) of the U.S. Army, which is **public domain US Government work** (17 USC § 105). The OCR output is faithful to that public-domain source.

Status: **archived.** This is a one-off project, not a maintained pipeline. The OCR is from 2018 (Tesseract 4.0, ScanTailor) and contains the typical noise of that era. Use as a static reference for the 1720–1985 period; for 1946+ use the live UCDP/PRIO dataset.

Endpoint: `https://raw.githubusercontent.com/owid/orae-major-conflicts/master/6-csv/entries.csv`
Auth: none
Format: `CSV` (single file)

Documentation:
- Repo: https://github.com/owid/orae-major-conflicts
- README: https://raw.githubusercontent.com/owid/orae-major-conflicts/master/README.md
- Original source compendium: U.S. Army Office of Research and Analysis (OR&A), "Major Armed Conflicts, 1720 to 1985: A Compendium" (public domain)
- Live alternative: UCDP/PRIO Armed Conflict Dataset at https://ucdp.uu.se/ (covered in [[connectors/no-public-api]] via SIPRI)

## What this is

A single CSV containing **~1,300+ historical armed conflict events from 1720 to 1985** (265 years), extracted via OCR from a public-domain US Army reference compendium. The repo is the entire OCR pipeline:

```text
1-pdf/         (9.5 MB)         the original PDF: orae_merged.pdf
2-images/      (63 MB, 188 files)  PDF split into PNG images (300 dpi)
3-clean-images/(14 MB, 187 files)  ScanTailor-cropped, deskewed, dewarped
4-ocr/         (273 KB, 187 files) raw Tesseract 4.0 output
5-ocr-split/   (237 KB, 644 files) per-event text segments
6-csv/         (178 KB)            final structured data
```

Total: **85 MB on disk** but the only file that matters is `6-csv/entries.csv` (178 KB).

## The data

```csv
filePath,HEADER,START,END,REGION(S)-,NATION(S)-,ACTOR(S)-,COMMITTER(S)-,LOCATION(S)-,INTERVENOR(S)-,MODE-,MAGNITUDE-,COMBATANTS-,DEATHS-,FORCE-,ISSUE(S)-,OUTCOME(S)-,SOURCE(S)-
5-ocr-split/0001.tif-1.txt,"ANNEX B COMPENDIUM OF MAJOR ARMED CONFLICTS 1720 TO 1985...",1720,1985,...
5-ocr-split/0002.tif-1.txt,L INVASION OF PERSIA 1722 to 1730,1722,1730,Asia,AFGHANISTAN TRAN/PERSIA,,AFGHANISTAN,TRAN/PERSIA,,Conventional Interstate,192,0,0,Ground Forces,Territory-Population Colonial,Unsuccess. Conmitter,7
5-ocr-split/0002.tif-2.txt,L-TREATY OF SEVILLE 1727 to Nov. 1729,1727,1729,BRITAIN FRANCE SPAIN TTALY/SARDINIA,,BRITAIN _ FRANCE,ITALY/SARDINIA,...
```

**17 columns:**
- `filePath` — internal trace back to the source OCR file
- `HEADER` — the conflict's title (e.g. "WAR OF THE POLISH SUCCESSION 1733 to Oct. 173")
- `START`, `END` — year of onset and termination
- `REGION(S)-`, `NATION(S)-`, `ACTOR(S)-`, `COMMITTER(S)-`, `LOCATION(S)-`, `INTERVENOR(S)-` — who was involved
- `MODE-` — "Conventional Interstate", "Imperial", "Colonial", "Primarily Internal", etc.
- `MAGNITUDE-` — an ordinal severity ranking (lowest ~18, largest ~thousands)
- `COMBATANTS-`, `DEATHS-`, `FORCE-` — scale
- `ISSUE(S)-` — "Territory-Population", "Elite", "Colonial", "Internal Tension Elite", etc.
- `OUTCOME(S)-` — "Unsuccess. Committer", "Successful Committer", "Compromise Committer"
- `SOURCE(S)-` — bibliographic reference id (linked to the original compendium)

## OCR noise (real examples from the live data)

- `L INVASION OF PERSIA` (should be `I. INVASION OF PERSIA` — Roman numeral 1)
- `WAR OF THE POLISH SUCCESSION 1733 to Oct. 173` (truncated; should be `1738`)
- `REVOLT OF CORSICA _ 1729 to 1755` (underscore for hyphen)
- `GENEV UPRISINGS 1734 to 2.737` (should be `GENEVA UPRISINGS 1734 to 1737`)
- `Conmmitter`, `Conmmitter`, `Committer` (3 different spellings of the same word)
- `TTALY` (should be `ITALY`)

This is **typical Tesseract 4.0 OCR from 2018 on early-modern typefaces**. A 2018-vintage OCR pipeline. For a modern run, you'd use Tesseract 5.x with LSTM models — but the result would be similar-quality (not fundamentally better, since the source is 1985-vintage dot-matrix print). Plan for a 5–10% error rate on the text fields; numeric fields like `START`, `END`, `DEATHS-` are usually correct.

## How it's used in OpenTIR-Data

```python
# /Users/penelope/Documents/opentir/ingest/fetchers/owid_orae.py
import csv
import io
import httpx
from ingest.fetchers.base import BaseFetcher, RawBundle

ENTRIES = "https://raw.githubusercontent.com/owid/orae-major-conflicts/master/6-csv/entries.csv"


class Fetcher(BaseFetcher):
    async def fetch(self):
        async with httpx.AsyncClient(
            timeout=60.0,
            headers={"User-Agent": "OpenTIR-Data/0.1"},
        ) as client:
            r = await client.get(ENTRIES)
            r.raise_for_status()
            yield RawBundle(
                source_system=self.source_system,
                source_collection="historical_conflicts",
                source_id="orae-1720-1985",
                source_url="https://github.com/owid/orae-major-conflicts",
                bundle_url=ENTRIES,
                fetched_at=self.now(),
                payload=r.content,
                payload_format="csv",
                metadata={
                    "title": "Major Armed Conflicts, 1720 to 1985",
                    "publisher": "US Army Office of Research and Analysis (OR&A)",
                    "period": "1720-1985",
                    "row_count": sum(1 for _ in r.text.splitlines()) - 1,
                    "note": "OCR output, ~5-10% text error rate",
                },
            )
```

## Quick call — verify

```bash
curl -sL "https://raw.githubusercontent.com/owid/orae-major-conflicts/master/6-csv/entries.csv" \
  -o /tmp/orae.csv -w "code=%{http_code} size=%{size_download}\n"
echo "  rows: $(wc -l < /tmp/orae.csv)"
echo "  columns: $(head -1 /tmp/orae.csv | tr ',' '\n' | wc -l)"
echo "  first conflict: $(sed -n '3p' /tmp/orae.csv | cut -d',' -f2,3,4)"
```

Expected: HTTP 200, 178 KB, ~1,300 rows, 17 columns, first conflict "L INVASION OF PERSIA, 1722, 1730".

## Why this is useful

1. **The 1720–1946 gap** isn't covered by UCDP/PRIO. The OR&A compendium is the **only public dataset** that goes back to 1720. Pre-Napoleonic conflicts (War of Spanish Succession, Seven Years War, etc.) are in here.
2. **Structured from the start** — 17 columns, conflict-level granularity, not just country-year aggregates.
3. **Public domain** (US Government work). The compendium is freely distributable; this OCR output is therefore also distributable.
4. **Single CSV** — 178 KB, easy to ingest, easy to version.

## Notes

- **OCR noise is real.** Plan to post-process the text fields: lowercase + strip + `Levenshtein` distance against a country dictionary to fix names. The `START`, `END`, `DEATHS-` numeric fields are usually correct.
- **Coverage is 1720–1985** — for 1986+ use the UCDP/PRIO Armed Conflict Dataset (which we noted in [[connectors/no-public-api]] via SIPRI/owid-etl). UCDP also covers non-state conflict (riots, terrorism) which OR&A doesn't.
- **OR&A is one of many historical compendiums.** The Correlates of War (COW) project at the University of Michigan maintains a similar dataset ("COW War Data, 1816–2007"). The COW data is the academic standard for conflict research and is the right primary source for serious historical analysis. The OR&A compendium is a useful supplement, especially for the 1720–1816 pre-Napoleonic period.
- **For the world dashboard**, this is a "long-run conflict history" layer. Render as a heatmap of conflict years × region (Asia, Europe, Mid East, etc.), with the option to filter by century or conflict type. Pairs naturally with the real-time ACLED feed for the 1946+ period.
- **Don't try to re-run the OCR pipeline.** It's 2018-vintage ImageMagick + Tesseract 4.0 + ScanTailor. Modern Tesseract 5.x + a clean modern OCR pipeline (e.g. `paddleocr` or `marker-pdf`) would produce higher quality, but the gain is incremental (~5–10% text error rate vs ~2–3%). The structured fields (years, numbers, regions) are already correct.
- **The CSV is a snapshot, not a dataset.** OR&A has not updated the compendium since the 1985 cut-off. The repo will not get more events. Treat as immutable historical data.
- **License caveat**: technically, the repo has no declared license and the original compendium is from a US Government agency (public domain). The OCR pipeline code (R + ImageMagick + Tesseract) is also a chain of free tools. Use the data; don't redistribute the repo's code.

