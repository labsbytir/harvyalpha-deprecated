"""Explicit, measurable scrolling steps for Spider's cloud browser."""
import json

INIT = """(() => {
window.__harvyScroll = {samples: [], postLinks: []};
document.documentElement.setAttribute('data-harvy-scroll-started', 'true');
})();"""

SAMPLE = """(() => {
const data = window.__harvyScroll || (window.__harvyScroll = {samples: [], postLinks: []});
for (const a of document.querySelectorAll('a[href]')) {
  if (/\\/posts\\/|story_fbid|\\/reel\\//.test(a.href) && !data.postLinks.includes(a.href)) data.postLinks.push(a.href);
}
data.samples.push({y: window.scrollY, height: document.scrollingElement ? document.scrollingElement.scrollHeight : null,
                  articles: document.querySelectorAll('[role="article"]').length, links: data.postLinks.length});
})();"""

FINISH = """(() => {
const data = window.__harvyScroll || {samples: [], postLinks: []};
data.url = location.href;
let script = document.getElementById('harvy-scroll-diagnostic');
if (!script) { script = document.createElement('script'); script.type = 'application/json'; script.id = 'harvy-scroll-diagnostic'; document.body.appendChild(script); }
script.textContent = JSON.stringify({harvy_scroll: data});
})();"""


def options(url):
    steps = [{"Evaluate": INIT}, {"Wait": 2000}]
    for _ in range(18):
        steps.extend([{"ScrollY": 900}, {"Wait": 1200}, {"Evaluate": SAMPLE}, {"Evaluate": FINISH}])
    # Exact full URL is Spider's documented script match; '/' covers root-path matches.
    return {"automation_scripts": {url: steps, "/": steps}}


def diagnostic(page):
    from v1.scrape.facebook import walk
    from html.parser import HTMLParser

    class DiagnosticScript(HTMLParser):
        def __init__(self):
            super().__init__()
            self.active = False
            self.text = ""

        def handle_starttag(self, tag, attrs):
            if tag == "script" and dict(attrs).get("id") == "harvy-scroll-diagnostic":
                self.active = True

        def handle_endtag(self, tag):
            if tag == "script":
                self.active = False

        def handle_data(self, text):
            if self.active:
                self.text += text

    data = next((n["harvy_scroll"] for n in walk(page.get("json_data")) if isinstance(n.get("harvy_scroll"), dict)), None)
    if data is None:
        parser = DiagnosticScript()
        parser.feed(page.get("content") or "")
        try:
            data = json.loads(parser.text).get("harvy_scroll")
        except (ValueError, AttributeError):
            data = None
    if not isinstance(data, dict):
        return {"verified": False, "reason": "Spider returned no execution/scroll evidence", "postLinks": []}
    samples = data.get("samples") or []
    positions = {s.get("y") for s in samples if isinstance(s, dict) and isinstance(s.get("y"), (int, float))}
    return {**data, "verified": len(positions) > 1,
            "reason": "Scroll positions changed" if len(positions) > 1 else "No observed scroll-position change"}
