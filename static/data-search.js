'use strict';
window.HarvyDataSearch = (() => {
  let index = null;
  let documents = [];
  let mounted = false;

  const sourceNames = {
    courtlistener: 'Case Intelligence',
    case_law: 'Case Intelligence',
    judyrecords: 'Public Records',
    arrests_org: 'Public Records',
    docket_alarm: 'Docket Intelligence',
    court_record: 'Court Directory',
    google_scholar: 'Academic References',
    mapillary: 'Location Intelligence',
  };

  function render(query) {
    const list = document.getElementById('data-search-results');
    const status = document.getElementById('data-search-status');
    if (!list || !index) return;
    list.replaceChildren();
    const term = query.trim();
    if (!term) {
      status.textContent = `${documents.length} saved records indexed. Enter terms to search.`;
      return;
    }
    const ids = index.search(term, 25, {suggest: true});
    for (const id of ids) {
      const doc = documents[id];
      if (!doc) continue;
      const item = document.createElement('li');
      item.className = 'data-search-result';
      const title = document.createElement('strong');
      title.textContent = doc.title || doc.file || 'Saved artifact';
      const meta = document.createElement('span');
      meta.textContent = sourceNames[doc.source] || 'Harvy Evidence';
      const snippet = document.createElement('p');
      snippet.textContent = (doc.text || '').slice(0, 320);
      item.append(title, meta, snippet);
      if (typeof doc.url === 'string' && doc.url.startsWith('https://')) {
        const link = document.createElement('a');
        link.href = doc.url;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = 'VIEW EVIDENCE ↗';
        item.append(link);
      }
      list.append(item);
    }
    status.textContent = `${ids.length} result${ids.length === 1 ? '' : 's'} (up to 25 shown).`;
  }

  function load(items, truncated) {
    const box = document.querySelector('.artifact-search');
    const input = document.getElementById('data-search-input');
    const status = document.getElementById('data-search-status');
    if (!box || !input || !window.FlexSearch) return;
    documents = Array.isArray(items) ? items : [];
    index = new window.FlexSearch.Index({tokenize: 'forward', cache: 100});
    for (let i = 0; i < documents.length; i++) {
      const doc = documents[i];
      index.add(i, [doc.title, doc.source, doc.file, doc.text].filter(Boolean).join(' '));
    }
    box.hidden = false;
    if (!mounted) {
      input.addEventListener('input', () => render(input.value));
      mounted = true;
    }
    status.textContent = `${documents.length} saved records indexed${truncated ? ' (index capped)' : ''}. Enter terms to search.`;
    render(input.value);
  }

  return {load};
})();
