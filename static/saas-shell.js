/**
 * Harvy SaaS Shell & Command-K Palette
 */
(function() {
  'use strict';

  const NAV_ITEMS = [
    {
      group: 'Analytics',
      items: [
        {
          title: 'Query Dashboard',
          url: '/query/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/></svg>',
          shortcut: 'G Q',
          keywords: 'query cube metrics analytics charts sql dashboard data'
        },
        {
          title: 'Graph Nodes',
          url: '/nodes/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>',
          shortcut: 'G N',
          keywords: 'nodes cytoscape topology entities links graph relationships'
        },
        {
          title: 'Geospatial Map',
          url: '/map/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="3 6 9 3 15 6 21 3 21 18 15 21 9 18 3 21"/><line x1="9" y1="3" x2="9" y2="18"/><line x1="15" y1="6" x2="15" y2="21"/></svg>',
          shortcut: 'G M',
          keywords: 'map geo spatial coordinates arrests location places leaflet'
        }
      ]
    },
    {
      group: 'Intelligence',
      items: [
        {
          title: 'Unified Search',
          url: '/search/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>',
          shortcut: 'G S',
          keywords: 'search universal find dossiers documents targets usernames'
        },
        {
          title: 'Legal & Research',
          url: '/research/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>',
          shortcut: 'G R',
          keywords: 'research legal court judyrecords arrests case law public records'
        }
      ]
    },
    {
      group: 'Operations',
      items: [
        {
          title: 'Ingress Scraper',
          url: '/platform/',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="4 17 10 11 4 5"/><line x1="12" y1="19" x2="20" y2="19"/></svg>',
          shortcut: 'G I',
          keywords: 'ingress scraper spider runner jobs terminal execution ingest social'
        },
        {
          title: 'System Health',
          url: '/health',
          icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>',
          shortcut: 'G H',
          keywords: 'health status api worker cloudflare runtime ping telemetry'
        }
      ]
    }
  ];

  const EXTRA_COMMANDS = [
    {
      title: 'Sign In / Account Settings',
      url: '/auth/',
      group: 'Account',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>',
      keywords: 'auth login register profile password api session user'
    },
    {
      title: 'Switch to Private Tenant Overlay',
      action: () => {
        const current = localStorage.getItem('harvy_environment') || 'shared';
        const next = current === 'shared' ? 'env_private' : 'shared';
        localStorage.setItem('harvy_environment', next);
        window.location.reload();
      },
      group: 'Environment',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="18" height="18" x="3" y="3" rx="2"/><path d="m9 12 2 2 4-4"/></svg>',
      keywords: 'switch environment tenant private shared toggle'
    },
    {
      title: 'Acceptable Use & Terms',
      url: '/terms/',
      group: 'System',
      icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>',
      keywords: 'terms policy legal privacy privacy-policy'
    }
  ];

  function initSaasShell() {
    if (document.getElementById('harvy-sidebar')) return;

    document.body.classList.add('has-saas-shell');
    const path = window.location.pathname;

    // Build Sidebar DOM
    const sidebar = document.createElement('aside');
    sidebar.id = 'harvy-sidebar';
    sidebar.className = 'harvy-sidebar';

    const envName = localStorage.getItem('harvy_environment') || 'shared';

    let navHtml = '';
    NAV_ITEMS.forEach(grp => {
      navHtml += `<div class="harvy-nav-group">
        <div class="harvy-nav-label">${grp.group}</div>`;
      grp.items.forEach(item => {
        const isActive = path === item.url || (item.url !== '/' && path.startsWith(item.url));
        navHtml += `
          <a href="${item.url}" class="harvy-nav-item ${isActive ? 'active' : ''}">
            ${item.icon}
            <span>${item.title}</span>
          </a>`;
      });
      navHtml += `</div>`;
    });

    sidebar.innerHTML = `
      <div class="harvy-sidebar-header">
        <a href="/" class="harvy-sidebar-brand" aria-label="Harvy Home">
          <img src="/static/harvy-logo.png" alt="Harvy" class="harvy-sidebar-logo">
        </a>
      </div>

      <button type="button" class="harvy-cmd-trigger" id="harvy-cmd-open-btn">
        <span style="display:flex;align-items:center;gap:8px;">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <span>Search or jump...</span>
        </span>
        <span class="harvy-cmd-badge">⌘K</span>
      </button>

      <div class="harvy-sidebar-scroll">
        ${navHtml}
      </div>

      <div class="harvy-sidebar-footer">
        <a href="/auth/" class="harvy-user-card" id="harvy-user-profile-link">
          <div class="harvy-user-info">
            <div class="harvy-user-avatar" id="harvy-avatar">H</div>
            <div class="harvy-user-meta">
              <span class="harvy-user-name" id="harvy-username">Analyst Session</span>
              <span class="harvy-user-role" id="harvy-userrole">${envName.toUpperCase()}</span>
            </div>
          </div>
          <button type="button" class="harvy-user-action-btn" title="Account Settings" aria-label="Account Settings">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>
          </button>
        </a>
      </div>
    `;

    // Mobile bar
    const mobileBar = document.createElement('div');
    mobileBar.className = 'harvy-mobile-bar';
    mobileBar.innerHTML = `
      <div style="display:flex;align-items:center;gap:10px;">
        <button type="button" class="harvy-mobile-btn" id="harvy-mobile-toggle" aria-label="Toggle navigation">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="12" x2="20" y2="12"/><line x1="4" y1="6" x2="20" y2="6"/><line x1="4" y1="18" x2="20" y2="18"/></svg>
        </button>
        <a href="/" style="display:flex;align-items:center;text-decoration:none;" aria-label="Harvy Home">
          <img src="/static/harvy-logo.png" alt="Harvy" style="height:26px;width:auto;display:block;">
        </a>
      </div>
      <button type="button" class="harvy-mobile-btn" id="harvy-mobile-cmd" aria-label="Search">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
      </button>
    `;

    const backdropOverlay = document.createElement('div');
    backdropOverlay.className = 'harvy-backdrop-overlay';
    backdropOverlay.id = 'harvy-mobile-backdrop';

    // Wrap page body if not wrapped
    let mainWrapper = document.querySelector('.harvy-main-wrapper');
    if (!mainWrapper) {
      mainWrapper = document.createElement('div');
      mainWrapper.className = 'harvy-main-wrapper';
      while (document.body.firstChild) {
        mainWrapper.appendChild(document.body.firstChild);
      }
    }

    document.body.appendChild(sidebar);
    document.body.appendChild(backdropOverlay);
    mainWrapper.insertBefore(mobileBar, mainWrapper.firstChild);
    document.body.appendChild(mainWrapper);

    // Mobile events
    const toggleBtn = document.getElementById('harvy-mobile-toggle');
    const mobileCmd = document.getElementById('harvy-mobile-cmd');
    toggleBtn?.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      backdropOverlay.classList.toggle('open');
    });
    backdropOverlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      backdropOverlay.classList.remove('open');
    });
    mobileCmd?.addEventListener('click', () => openCommandPalette());

    // Fetch user profile async
    fetchSessionUser();

    // Setup Command-K Palette
    setupCommandPalette();
  }

  function fetchSessionUser() {
    fetch('/api/auth/me', { credentials: 'include' })
      .then(res => res.ok ? res.json() : null)
      .then(data => {
        if (data && (data.user || data.username)) {
          const user = data.user || data;
          const name = user.displayName || user.username || 'Analyst';
          const nameEl = document.getElementById('harvy-username');
          const avatarEl = document.getElementById('harvy-avatar');
          const roleEl = document.getElementById('harvy-userrole');
          if (nameEl) nameEl.textContent = name;
          if (avatarEl) avatarEl.textContent = name.charAt(0).toUpperCase();
          if (roleEl && user.role) roleEl.textContent = user.role.toUpperCase();
        }
      })
      .catch(() => {});
  }

  // --- Command-K Palette ---
  let cmdBackdrop = null;
  let cmdInput = null;
  let cmdResults = null;
  let selectedIndex = 0;
  let activeMatches = [];

  function getAllCommands() {
    const list = [];
    NAV_ITEMS.forEach(grp => {
      grp.items.forEach(it => {
        list.push({
          ...it,
          group: grp.group
        });
      });
    });
    return [...list, ...EXTRA_COMMANDS];
  }

  function setupCommandPalette() {
    cmdBackdrop = document.createElement('div');
    cmdBackdrop.className = 'harvy-cmd-backdrop';
    cmdBackdrop.id = 'harvy-cmd-modal';
    cmdBackdrop.innerHTML = `
      <div class="harvy-cmd-palette">
        <div class="harvy-cmd-input-wrap">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#71717a" stroke-width="2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
          <input type="text" class="harvy-cmd-input" id="harvy-cmd-input" placeholder="Type a command or jump to page..." autocomplete="off">
          <span class="harvy-cmd-kbd" style="font-size:10px;">ESC</span>
        </div>
        <div class="harvy-cmd-results" id="harvy-cmd-results"></div>
        <div class="harvy-cmd-footer">
          <span><span class="harvy-cmd-kbd">↑</span> <span class="harvy-cmd-kbd">↓</span> navigate</span>
          <span><span class="harvy-cmd-kbd">↵</span> select</span>
          <span><span class="harvy-cmd-kbd">ESC</span> close</span>
        </div>
      </div>
    `;

    document.body.appendChild(cmdBackdrop);

    cmdInput = document.getElementById('harvy-cmd-input');
    cmdResults = document.getElementById('harvy-cmd-results');

    // Button trigger in sidebar
    document.getElementById('harvy-cmd-open-btn')?.addEventListener('click', openCommandPalette);

    // Global keyboard listener
    window.addEventListener('keydown', (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        toggleCommandPalette();
      } else if (e.key === 'Escape' && cmdBackdrop.classList.contains('active')) {
        closeCommandPalette();
      }
    });

    cmdBackdrop.addEventListener('click', (e) => {
      if (e.target === cmdBackdrop) closeCommandPalette();
    });

    cmdInput.addEventListener('input', () => {
      renderResults(cmdInput.value.trim().toLowerCase());
    });

    cmdInput.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (activeMatches.length > 0) {
          selectedIndex = (selectedIndex + 1) % activeMatches.length;
          updateSelected();
        }
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (activeMatches.length > 0) {
          selectedIndex = (selectedIndex - 1 + activeMatches.length) % activeMatches.length;
          updateSelected();
        }
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (activeMatches[selectedIndex]) {
          executeCommand(activeMatches[selectedIndex]);
        }
      }
    });
  }

  function openCommandPalette() {
    if (!cmdBackdrop) return;
    cmdBackdrop.classList.add('active');
    cmdInput.value = '';
    renderResults('');
    setTimeout(() => cmdInput.focus(), 50);
  }

  function closeCommandPalette() {
    if (!cmdBackdrop) return;
    cmdBackdrop.classList.remove('active');
  }

  function toggleCommandPalette() {
    if (cmdBackdrop && cmdBackdrop.classList.contains('active')) {
      closeCommandPalette();
    } else {
      openCommandPalette();
    }
  }

  function renderResults(filter) {
    const all = getAllCommands();
    activeMatches = all.filter(c => {
      if (!filter) return true;
      const haystack = `${c.title} ${c.group} ${c.keywords || ''}`.toLowerCase();
      return haystack.includes(filter);
    });

    selectedIndex = 0;
    if (activeMatches.length === 0) {
      cmdResults.innerHTML = `
        <div style="padding: 24px; text-align: center; color: #71717a; font-size: 13px;">
          No matching commands found.
        </div>
      `;
      return;
    }

    let html = '';
    let lastGroup = null;

    activeMatches.forEach((cmd, idx) => {
      if (cmd.group !== lastGroup) {
        html += `<div class="harvy-cmd-group-title">${cmd.group}</div>`;
        lastGroup = cmd.group;
      }
      const isSel = idx === selectedIndex;
      html += `
        <div class="harvy-cmd-option ${isSel ? 'selected' : ''}" data-idx="${idx}">
          <div class="harvy-cmd-option-left">
            ${cmd.icon}
            <span>${cmd.title}</span>
          </div>
          ${cmd.shortcut ? `<span class="harvy-cmd-shortcut">${cmd.shortcut}</span>` : ''}
        </div>
      `;
    });

    cmdResults.innerHTML = html;

    // Click handler on options
    cmdResults.querySelectorAll('.harvy-cmd-option').forEach(el => {
      el.addEventListener('click', () => {
        const idx = parseInt(el.getAttribute('data-idx') || '0', 10);
        if (activeMatches[idx]) {
          executeCommand(activeMatches[idx]);
        }
      });
      el.addEventListener('mouseenter', () => {
        selectedIndex = parseInt(el.getAttribute('data-idx') || '0', 10);
        updateSelected();
      });
    });
  }

  function updateSelected() {
    const items = cmdResults.querySelectorAll('.harvy-cmd-option');
    items.forEach((el, idx) => {
      if (idx === selectedIndex) {
        el.classList.add('selected');
        el.scrollIntoView({ block: 'nearest' });
      } else {
        el.classList.remove('selected');
      }
    });
  }

  function executeCommand(cmd) {
    closeCommandPalette();
    if (cmd.action) {
      cmd.action();
    } else if (cmd.url) {
      window.location.href = cmd.url;
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initSaasShell);
  } else {
    initSaasShell();
  }
})();
