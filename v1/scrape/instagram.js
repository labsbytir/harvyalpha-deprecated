// Harvest Instagram profile metadata. Consented handles only (consent.json).
//
// Instagram shows only profile-level metadata to logged-out browsers — the
// post grid, captions and timestamps are behind the login wall. This extractor
// captures what exists: handle, display name, follower/following/post counts
// and the latest bio line. Store it per person in socials-<handle>.json
// alongside any Threads/X harvest for the same person.
//
// Usage (chrome-devtools MCP, CDP Brave on localhost:9222):
//   1. navigate_page { pageId, url: "https://www.instagram.com/<handle>/" }
//   2. evaluate_script { pageId, function: INSTAGRAME_EXTRACTOR }
//   3. save the returned JSON string with v1/scrape/merge_graph.py.

const INSTAGRAM_EXTRACTOR = `() => {
  const grab = (sel) => { const m = document.querySelector(sel); return m ? m.content : null; };
  const title = grab('meta[property="og:title"]') || '';
  const desc = grab('meta[property="og:description"]') || '';
  const bio = grab('meta[name="description"]') || '';
  const hm = title.match(/\\(@([\\w.]+)\\)/);
  const counts = {};
  const cm = desc.match(/([\\d.,KM]+)\\s*Followers?,\\s*([\\d.,KM]+)\\s*Following?,\\s*([\\d.,KM]+)\\s*Posts?/i);
  if (cm) {
    counts.followers = cm[1];
    counts.following = cm[2];
    counts.posts = cm[3];
  }
  const bm = bio.match(/-\\s*(.+)$/);
  return JSON.stringify({
    platform: 'instagram',
    person: hm ? hm[1] : null,
    name: hm ? title.replace(/\\s*\\(@[\\w.]+\\).*$/, '') : title,
    counts: counts,
    bio: bm ? bm[1].trim() : null,
    loginWalled: !!document.body.innerText.match(/log in to continue|sign up/i) || !cm,
  });
}`;
