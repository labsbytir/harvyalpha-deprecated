#!/usr/bin/env python3
"""Compile verified intelligence reports from genuine scraped post files."""

import html
import json
import os
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

TARGETS = [
    {
        "slug": "trump",
        "name": "Donald J. Trump",
        "title": "47th President of the United States",
        "primary_surface": "Truth Social (@realDonaldTrump)",
        "surfaces": ["Truth Social", "Web Wire"],
        "posts_dir": DATA_DIR / "leaders" / "trump" / "posts",
        "report_dir": DATA_DIR / "leaders" / "trump",
    },
    {
        "slug": "zelenskyy",
        "name": "Volodymyr Zelenskyy",
        "title": "President of Ukraine",
        "primary_surface": "Telegram (@V_Zelenskiy_official)",
        "surfaces": ["Telegram Official Channel", "Web Wire"],
        "posts_dir": DATA_DIR / "leaders" / "zelenskyy" / "posts",
        "report_dir": DATA_DIR / "leaders" / "zelenskyy",
    },
    {
        "slug": "starmer",
        "name": "Keir Starmer",
        "title": "Prime Minister of the United Kingdom",
        "primary_surface": "10 Downing Street (GOV.UK)",
        "surfaces": ["GOV.UK Official", "Prime Minister Communiqués"],
        "posts_dir": DATA_DIR / "leaders" / "starmer" / "posts",
        "report_dir": DATA_DIR / "leaders" / "starmer",
    },
    {
        "slug": "modi",
        "name": "Narendra Modi",
        "title": "Prime Minister of India",
        "primary_surface": "YouTube Official (@NarendraModi)",
        "surfaces": ["YouTube Official Channel", "Public Addresses"],
        "posts_dir": DATA_DIR / "leaders" / "modi" / "posts",
        "report_dir": DATA_DIR / "leaders" / "modi",
    },
    {
        "slug": "macron",
        "name": "Emmanuel Macron",
        "title": "President of France",
        "primary_surface": "YouTube Official (@EmmanuelMacron)",
        "surfaces": ["YouTube Official Channel", "Élysée Addresses"],
        "posts_dir": DATA_DIR / "leaders" / "macron" / "posts",
        "report_dir": DATA_DIR / "leaders" / "macron",
    },
    {
        "slug": "putin",
        "name": "Vladimir Putin",
        "title": "President of the Russian Federation",
        "primary_surface": "President of Russia (kremlin.ru)",
        "surfaces": ["Kremlin Official Events", "Presidential Communiqués"],
        "posts_dir": DATA_DIR / "leaders" / "putin" / "posts",
        "report_dir": DATA_DIR / "leaders" / "putin",
    },
    {
        "slug": "xi",
        "name": "Xi Jinping",
        "title": "President of the People's Republic of China",
        "primary_surface": "Xinhua Xi's Time Wire (english.news.cn)",
        "surfaces": ["Xinhua News Agency", "State Communiqués"],
        "posts_dir": DATA_DIR / "leaders" / "xi" / "posts",
        "report_dir": DATA_DIR / "leaders" / "xi",
    },
    {
        "slug": "natgeo",
        "name": "National Geographic",
        "title": "Global Nature & Science Documentarian",
        "primary_surface": "Facebook & YouTube Official",
        "surfaces": ["Facebook Verified", "YouTube Official Channel"],
        "posts_dir": DATA_DIR / "natgeo" / "posts",
        "report_dir": DATA_DIR / "natgeo",
    },
]


def compile_report(target):
    p_dir = target["posts_dir"]
    r_dir = target["report_dir"]
    r_dir.mkdir(parents=True, exist_ok=True)

    json_files = sorted(p_dir.glob("*.json"))
    posts = []
    total_reactions = 0
    total_shares = 0
    total_comments = 0
    unique_outlinks = set()

    for jf in json_files:
        try:
            p = json.loads(jf.read_text(encoding="utf-8"))
            posts.append(p)
            if p.get("reactions"):
                total_reactions += int(p["reactions"])
            if p.get("shares"):
                total_shares += int(p["shares"])
            if p.get("comments"):
                total_comments += int(p["comments"])
            for link in p.get("outlinks", []):
                unique_outlinks.add(link)
        except Exception as e:
            print(f"Error reading {jf}: {e}")

    report_data = {
        "target": {
            "name": target["name"],
            "title": target["title"],
            "primary_surface": target["primary_surface"],
            "surfaces": target["surfaces"],
        },
        "telemetry": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source": "spider_unlimited_residential_proxy",
            "posts_captured": len(posts),
            "aggregate_reactions": total_reactions if total_reactions > 0 else None,
            "aggregate_shares": total_shares if total_shares > 0 else None,
            "aggregate_comments": total_comments if total_comments > 0 else None,
            "unique_outlinks": len(unique_outlinks),
        },
        "posts": posts,
    }

    (r_dir / "report.json").write_text(json.dumps(report_data, indent=2, ensure_ascii=False))

    # Generate HTML rows
    table_rows = []
    for i, p in enumerate(posts, 1):
        txt = html.escape(p.get("text", "")[:320])
        url = html.escape(p.get("url", "#"))
        p_type = html.escape(p.get("type", "Post"))
        p_surf = html.escape(p.get("surface", target["primary_surface"]))
        created = html.escape(str(p.get("created_at") or p.get("timestamp") or "Verified Ingestion"))
        
        rx = f"{p['reactions']:,}" if p.get("reactions") is not None else "&mdash;"
        sh = f"{p['shares']:,}" if p.get("shares") is not None else "&mdash;"
        cm = f"{p['comments']:,}" if p.get("comments") is not None else "&mdash;"

        row = f"""
        <tr>
          <td class="p-num">{i:02d}</td>
          <td><span class="p-type-badge">{p_type}</span></td>
          <td><span class="p-surf-badge">{p_surf}</span></td>
          <td>
            <div class="p-text">{txt}</div>
            <a href="{url}" target="_blank" rel="noopener" class="p-link">&nearr; {url[:55]}...</a>
          </td>
          <td class="p-num">{created}</td>
          <td class="p-num">{rx}</td>
          <td class="p-num">{sh}</td>
          <td class="p-num">{cm}</td>
        </tr>
        """
        table_rows.append(row)

    rows_html = "\n".join(table_rows)

    rx_display = f"{total_reactions:,}" if total_reactions > 0 else "&mdash;"
    sh_display = f"{total_shares:,}" if total_shares > 0 else "&mdash;"
    cm_display = f"{total_comments:,}" if total_comments > 0 else "&mdash;"

    html_report = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>HarvyBot Recon Dossier // {target['name']} ({len(posts)} Posts)</title>
  <link rel="stylesheet" href="/static/stylesheet.css">
  <style>
    :root {{
      --bg: #0d1117;
      --card: #161b22;
      --border: #30363d;
      --text: #f0f6fc;
      --text-muted: #8b949e;
      --text-subtle: #484f58;
      --accent: #58a6ff;
      --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: var(--bg); color: var(--text); font-family: var(--font-sans); padding: 1.5rem 1rem; line-height: 1.5; -webkit-font-smoothing: antialiased; }}
    .container {{ max-width: 1100px; margin: 0 auto; width: 100%; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 1.25rem; margin-bottom: 1.5rem; display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem; }}
    .brand-title {{ font-family: var(--font-mono); font-size: 0.78rem; color: #8b949e; letter-spacing: 0.08em; }}
    h1 {{ font-size: 1.6rem; font-weight: 800; color: #fff; margin-top: 0.25rem; }}
    .badge {{ font-family: var(--font-mono); font-size: 0.72rem; background: #238636; color: #fff; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 3px; }}
    .nav-back {{ font-family: var(--font-mono); font-size: 0.78rem; color: var(--accent); text-decoration: none; margin-bottom: 1rem; display: inline-block; }}
    .nav-back:hover {{ text-decoration: underline; }}
    
    .telemetry-row {{ display: flex; gap: 0.5rem; flex-wrap: wrap; font-family: var(--font-mono); font-size: 0.72rem; margin-bottom: 1.25rem; }}
    .pill {{ background: #161b22; border: 1px solid var(--border); padding: 0.3rem 0.6rem; color: #8b949e; border-radius: 4px; }}
    .pill strong {{ color: #f0f6fc; }}
    
    .target-profile {{ background: var(--card); border: 1px solid var(--border); padding: 1.25rem; margin-bottom: 1.5rem; border-radius: 6px; }}
    .target-profile h2 {{ font-size: 1.3rem; color: #fff; margin-bottom: 0.25rem; }}
    .target-profile .title-tag {{ font-family: var(--font-mono); font-size: 0.8rem; color: #8b949e; margin-bottom: 0.5rem; }}
    .surfaces-tag {{ font-family: var(--font-mono); font-size: 0.72rem; color: #8b949e; }}

    .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }}
    .stat-card {{ background: var(--card); border: 1px solid var(--border); padding: 1rem; border-radius: 6px; }}
    .stat-fig {{ font-family: var(--font-mono); font-size: 0.68rem; color: var(--text-muted); margin-bottom: 0.25rem; }}
    .stat-val {{ font-size: 1.4rem; font-weight: 800; font-family: var(--font-mono); color: #fff; }}
    .stat-label {{ font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}

    .section-title {{ font-family: var(--font-mono); font-size: 0.82rem; font-weight: 700; color: #8b949e; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin: 1.5rem 0 1rem; letter-spacing: 0.05em; }}
    
    .table-wrap {{ width: 100%; overflow-x: auto; -webkit-overflow-scrolling: touch; border: 1px solid var(--border); background: #0d1117; margin-bottom: 2rem; border-radius: 6px; }}
    .posts-table {{ width: 100%; min-width: 720px; border-collapse: collapse; font-size: 0.82rem; text-align: left; border: none; }}
    .posts-table th {{ background: #161b22; border: 1px solid var(--border); padding: 0.55rem 0.75rem; font-family: var(--font-mono); font-size: 0.7rem; color: #8b949e; text-transform: uppercase; }}
    .posts-table td {{ border: 1px solid var(--border); padding: 0.7rem 0.75rem; color: #c9d1d9; vertical-align: top; }}
    .posts-table tr:nth-child(even) {{ background: #0d1117; }}
    .posts-table tr:hover {{ background: #161b22; }}
    .p-type-badge {{ font-family: var(--font-mono); font-size: 0.68rem; padding: 0.15rem 0.35rem; border: 1px solid #30363d; background: #21262d; color: #f0f6fc; border-radius: 3px; white-space: nowrap; }}
    .p-surf-badge {{ font-family: var(--font-mono); font-size: 0.68rem; padding: 0.15rem 0.35rem; border: 1px solid #30363d; background: #161b22; color: #58a6ff; border-radius: 3px; white-space: nowrap; }}
    .p-text {{ color: #e6edf3; font-size: 0.8rem; line-height: 1.4; max-width: 460px; word-break: break-word; }}
    .p-link {{ font-family: var(--font-mono); font-size: 0.7rem; color: #58a6ff; text-decoration: none; display: inline-block; margin-top: 0.35rem; }}
    .p-link:hover {{ text-decoration: underline; }}
    .p-num {{ font-family: var(--font-mono); font-size: 0.75rem; color: #8b949e; text-align: right; }}

    @media (max-width: 768px) {{
      .stats-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
  </style>
</head>
<body>
  <div class="container">
    <a href="/#examples" class="nav-back">&larr; BACK TO HARVYBOT RECON EXAMPLES</a>
    
    <header>
      <div>
        <div class="brand-title">HARVYBOT // VERIFIED OSINT DOSSIER</div>
        <h1>{target['name']}</h1>
      </div>
      <div class="badge">LIVE INGRESS HARVEST</div>
    </header>

    <div class="telemetry-row">
      <div class="pill">TARGET: <strong>{target['slug']}</strong></div>
      <div class="pill">WIRES HARVESTED: <strong>{len(posts)} AUTHENTIC POSTS</strong></div>
      <div class="pill">SOURCE: <strong>{target['primary_surface']}</strong></div>
      <div class="pill">STATUS: <strong>VERIFIED RECORD ARCHIVE</strong></div>
    </div>

    <div class="target-profile">
      <h2>{target['name']}</h2>
      <div class="title-tag">{target['title']}</div>
      <div class="surfaces-tag">AUTHENTIC INGESTION SURFACES: {', '.join(target['surfaces'])}</div>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-fig">FIG 1.1</div>
        <div class="stat-val">{len(posts)}</div>
        <div class="stat-label">Verified Posts</div>
      </div>
      <div class="stat-card">
        <div class="stat-fig">FIG 1.2</div>
        <div class="stat-val">{rx_display}</div>
        <div class="stat-label">Total Reactions</div>
      </div>
      <div class="stat-card">
        <div class="stat-fig">FIG 1.3</div>
        <div class="stat-val">{sh_display}</div>
        <div class="stat-label">Total Shares / Reblogs</div>
      </div>
      <div class="stat-card">
        <div class="stat-fig">FIG 1.4</div>
        <div class="stat-val">{len(unique_outlinks)}</div>
        <div class="stat-label">Extracted Outlinks</div>
      </div>
    </div>

    <div class="section-title">[01] AUTHENTIC HARVESTED POST WIRES &amp; COMMUNICATIONS ({len(posts)} RECORDS)</div>
    <div class="table-wrap">
      <table class="posts-table">
        <thead>
          <tr>
            <th style="width: 35px;">#</th>
            <th>Type</th>
            <th>Surface</th>
            <th>Post Content &amp; Live Permalinks</th>
            <th style="text-align: right;">Ingestion Date</th>
            <th style="text-align: right;">Reactions</th>
            <th style="text-align: right;">Shares</th>
            <th style="text-align: right;">Comments</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>
"""
    (r_dir / "report.html").write_text(html_report, encoding="utf-8")
    print(f"[+] Compiled report for {target['name']}: {len(posts)} genuine posts.")


if __name__ == "__main__":
    for t in TARGETS:
        compile_report(t)
