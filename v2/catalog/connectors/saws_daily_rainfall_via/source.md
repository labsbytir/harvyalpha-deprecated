---
tags: [source, climate, tier-3, osint-data, scraper, africa, south-africa, fallback]
status: rejected
display_name: "SAWS Daily Rainfall via afriwx.co.za text dump (scraper fallback)"
source_name: saws_via_afriwx
---

# SAWS Daily Rainfall via afriwx.co.za text dump (scraper fallback)

afriwx.co.za republishes South African Weather Service (SAWS) daily rainfall data as plain HTML + a plain-text dump at `https://afriwx.co.za/rainfall-reenval/daily-recorded-rainfall-data-figures-south-africa/daily-recorded-rainfall-data-figures-south-africa-inc.txt`. Not an API — it's a scraper target.

**Status: rejected.** Don't use this if you can avoid it. Documented here as a fallback for when AfriGIS is not available and we need daily ZA rainfall.

## Metadata

| Field | Value |
|---|---|
| Source system | `saws_via_afriwx` |
| Underlying data | SAWS (via afriwx.co.za) |
| URL | `https://afriwx.co.za/rainfall-reenval/daily-recorded-rainfall-data-figures-south-africa/daily-recorded-rainfall-data-figures-south-africa-inc.txt` |
| Auth | **none** (public page) |
| Tier | 3 (scraper, not API) |
| Axis | climate |
| License | The afriwx page claims copyright ("PLEASE NOTE ALL CODE CONTAINED WITHIN THIS WEB SITE IS COPYRIGHTED") but the data itself is SAWS / public sector. **Treat as gray.** |
| per_tenant_only | false |
| Coverage type | national (South Africa) |

## Format

Plain text, one row per station, with format like:
```
GAUTENG
            BRONKHORSTSPRUIT AWS       05
            IRENE WO                   05
            JHB BOT TUINE              11
```

Each line has station name + rainfall in mm. The page also embeds 5 image scans of the SAWS daily bulletin.

## Why I'm rejecting this

1. **Not an API.** The afriwx terms of use say "all code contained within this web site is copyrighted" and "this site is monitored extensively for copyright infringements." Even if the *data* is public (SAWS), scraping the *page* is in tension with their stated policy.
2. **Fragile.** afriwx is a hobbyist site; if it goes down, the data goes with it. TAHMO and WMO are institutional.
3. **Better alternatives exist.** TAHMO has African station data; WMO WWIS has South African city forecasts; CHIRPS/DEAfrica has historical rainfall. None of them require scraping.
4. **The user said all 55 sources are free.** This is gray, not free.

## When this would be acceptable

- The data is genuinely needed and no other source provides it.
- afriwx is contacted and gives explicit permission (they list contact info).
- An alternative that's clearly public-domain (e.g., a hypothetical future SAWS open-data portal) doesn't exist.

## Related

- [[Africa Weather Sources - Survey 2026-09-05]]
- [[AfriGIS Weather / AfricaWeather.com API]] — the paid commercial alternative
- [[TAHMO — Trans-African Hydro-Meteorological Observatory]] — the free alternative
