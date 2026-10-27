// Harvest a Facebook friends grid (or any profile list) into structured per-friend records.
// Run via chrome-devtools-mcp evaluate_script with sourcePath + filePath.
// Session context: logged-out fresh-profile Brave (CDP). Captures only what the
// page renders for an anonymous visitor.
() => {
  const seen = new Set();
  const skip = /\/(friends|followers|following|about|photos|reels|posts|videos|map|events|reviews|reviews_given|groups|marketplace|pages|people$|gaming|live|watch|search|login|help|privacy|terms|settings|messenger|notifications|fundraisers|crisis|careers|ads|admanager|business|wallet|recover|photo)(\/|$)/;
  const friends = [];
  document.querySelectorAll('a[href*="facebook.com/"]').forEach(a => {
    const href = a.href.split('?')[0].replace(/\/$/, '');
    if (seen.has(href) || skip.test(href)) return;
    seen.add(href);
    // friend cards are list items / articles; fall back to the anchor's own subtree
    const card = a.closest('div[role="listitem"], div[role="article"]') || a.parentElement;
    const img = (card && card.querySelector('img')) || a.querySelector('img');
    const text = card ? card.innerText.replace(/\s+/g, ' ').trim() : '';
    const followers = (text.match(/([\d,.]+\s*[KM]?)\s*followers/i) || [])[1] || null;
    const place = (text.match(/(?:Lives in|From)\s+([^•]+)/i) || [])[1] || null;
    friends.push({
      name: (a.getAttribute('aria-label') || a.innerText || (img && img.alt) || '').trim() || href.split('/').pop(),
      url: href,
      pfbid: (href.match(/pfbid[0-9A-Za-z]+/) || [null])[0],
      avatar: img ? img.src : null,
      followers: followers,
      place: place,
    });
  });
  return {
    capturedAt: new Date().toISOString(),
    session: 'logged-out-fresh-profile',
    source: location.href,
    count: friends.length,
    friends,
  };
}
