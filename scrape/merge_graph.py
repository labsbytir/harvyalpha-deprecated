#!/usr/bin/env python3
"""Merge harvested social-account JSON into graph.json (consent-gated).

Usage: python3 scrape/merge_graph.py accounts.json --consent consent.json [--graph graph.json]
accounts.json is the output of harvest-threads/harvest-instagram/fetch-x:
[{"platform": "x|instagram|threads", "handle": "@natgeo", "url": "...",
  "posts": [{"text": ..., "timestamp": ...}, ...]}]
"""
import argparse, json, os, sys

def fail(msg, code=2):
    print(f"error: {msg}"); sys.exit(code)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("accounts")
    ap.add_argument("--consent", required=True)
    ap.add_argument("--graph", default="graph.json")
    args = ap.parse_args()

    consent = json.load(open(args.consent))
    handles = {h.lstrip("@").lower() for h in consent if isinstance(h, str)}
    if isinstance(consent, dict):
        handles = {h.lstrip("@").lower() for h in consent.get("handles", [])}
    accounts = json.load(open(args.accounts))

    gpath = args.graph if os.path.exists(args.graph) else None
    g = json.load(open(gpath)) if gpath else {"name": "You", "nodes": [], "links": []}
    nodes, links = g.setdefault("nodes", []), g.setdefault("links", [])
    you = next((n["id"] for n in nodes if n.get("type") == "center"), "you")
    if not any(n["id"] == you for n in nodes):
        nodes.insert(0, {"id": you, "name": g.get("name", "You"), "type": "center"})

    added = 0
    for acc in accounts:
        h = (acc.get("handle") or "").lstrip("@").lower()
        if not h: continue
        if h not in handles and not acc.get("own"):
            fail(f"@{h} not in the consent registry ({args.consent})")
        nid = f"{acc.get('platform','x')}:{h}"
        if not any(n["id"] == nid for n in nodes):
            nodes.append({"id": nid, "name": f"{acc.get('platform','x')} @{h}",
                          "type": "account", "platform": acc.get("platform"),
                          "handle": acc.get("handle"), "url": acc.get("url")})
            links.append({"source": you, "target": nid, "dashed": True})
            added += 1
        for p in (acc.get("posts") or []):
            if p.get("text"):
                nodes.append({"type": "social-post", "person": f"@{h}", "text": str(p["text"])[:200],
                              "date": p.get("timestamp") or p.get("date")})
    json.dump(g, open(args.graph, "w"), indent=2, ensure_ascii=False)
    print(f"merged {added} account node(s) into {args.graph}")

if __name__ == "__main__":
    main()
