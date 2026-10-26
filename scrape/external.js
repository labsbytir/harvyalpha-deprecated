// Harvest external profile links (social media handles) from a Facebook
// "about" / profile page. Run via chrome-devtools-mcp evaluate_script.
// Output: [{ platform, handle, url }] — one per external profile link found.
() => {
  const FB_HOSTS = /^(www\.|m\.|web\.|business\.|l\.|lm\.)?facebook\.com$|fbcdn\.net$|fb\.com$/i;
  const PLATFORMS = [
    [/instagram\.com/i, 'instagram'],
    [/(twitter\.com|x\.com)/i, 'x/twitter'],
    [/tiktok\.com/i, 'tiktok'],
    [/linkedin\.com/i, 'linkedin'],
    [/youtube\.com|youtu\.be/i, 'youtube'],
    [/github\.com/i, 'github'],
    [/twitch\.tv/i, 'twitch'],
    [/spotify\.com|open\.spotify/i, 'spotify'],
    [/reddit\.com/i, 'reddit'],
    [/pinterest\./i, 'pinterest'],
    [/threads\.net/i, 'threads'],
    [/snapchat\.com/i, 'snapchat'],
    [/telegram|t\.me/i, 'telegram'],
    [/discord/i, 'discord'],
    [/steamcommunity\.com|steampowered\.com/i, 'steam'],
  ];
  const seen = new Map();
  document.querySelectorAll('a[href]').forEach(a => {
    let u;
    try { u = new URL(a.href); } catch { return; }
    if (u.protocol !== 'https:' || FB_HOSTS.test(u.hostname)) return;
    const platform = (PLATFORMS.find(([re]) => re.test(u.hostname)) || [null, 'other'])[1];
    const handle = u.pathname.split('/').filter(Boolean)[0] || u.hostname;
    const key = platform + '|' + handle.toLowerCase();
    if (seen.has(key)) return;
    seen.set(key, { platform, handle, url: u.origin + u.pathname.replace(/\/$/, '') });
  });
  return {
    capturedAt: new Date().toISOString(),
    source: location.href,
    count: seen.size,
    accounts: [...seen.values()],
  };
}
