// Harvest Threads posts from one profile. Consented handles only (consent.json).
//
// Usage (chrome-devtools MCP, CDP Brave on localhost:9222):
//   1. navigate_page { pageId, url: "https://www.threads.com/@<handle>" }
//   2. evaluate_script { pageId, function: THREADED_EXTRACTOR }
//   3. save the returned JSON string: python3 scrape/merge_graph.py threads-<handle>.json
// Threads renders its whole client-side app for anonymous visitors; the extractor
// gets everything in the initial feed. Scroll down in the tab first if the
// account posts heavily — each scroll batch adds more posts.

const THREADS_EXTRACTOR = `() => {
  const out = [];
  document.querySelectorAll('[data-pressable-container="true"]').forEach(c => {
    const t = c.querySelector('time[datetime]');
    if (!t) return;
    let text = c.innerText.replace(/\\s+/g, ' ').trim();
    // strip the leading handle + relative date and trailing reaction counts
    text = text.replace(/^[a-zA-Z0-9._]+\\s+(\\d+[dhm]|\\d{1,2}\\/\\d{1,2}\\/\\d{2,4})\\s+/, '');
    text = text.replace(/(\\s+\\d[a-zA-Z]?)+\\s*$/, '').trim().slice(0, 280);
    const href = [...c.querySelectorAll('a[href]')].map(a => a.getAttribute('href'))
      .find(h => /\\/post\\//.test(h) || /\\/thread\\//.test(h));
    out.push({
      time: t.getAttribute('datetime'),
      text: text,
      url: href ? 'https://www.threads.com' + href : null,
    });
  });
  const handle = document.title.match(/\\(@([\\w.]+)\\)/);
  return JSON.stringify({
    platform: 'threads',
    person: handle ? handle[1] : null,
    posts: out,
  });
}`;
