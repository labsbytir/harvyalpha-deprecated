(function () {
  const form = document.getElementById("universal-search-form");
  const queryInput = document.getElementById("universal-search-query");
  const statusEl = document.getElementById("universal-search-status");
  const resultsEl = document.getElementById("universal-search-results");
  const advToggle = document.getElementById("adv-toggle");
  const advDrawer = document.getElementById("adv-drawer");
  const tabChips = document.querySelectorAll(".tab-chip");

  let activeCategory = "all";
  let forceGeneralSearch = false;

  // Recognized social platforms & patterns
  const SOCIAL_DOMAINS = [
    "facebook.com", "fb.com", "instagram.com", "threads.net", "twitter.com", "x.com",
    "tiktok.com", "youtube.com", "youtu.be", "reddit.com", "bsky.app", "bluesky.app",
    "t.me", "telegram.me", "truthsocial.com", "linkedin.com", "github.com", "steamcommunity.com",
    "pinterest.com", "twitch.tv", "medium.com", "substack.com"
  ];

  function detectTargetType(text) {
    const raw = text.trim();
    if (!raw) return { type: "empty" };

    // Only parse explicit URLs or domain-shaped input; a plain word is not a hostname.
    if (/^https?:\/\//i.test(raw) || /^[a-z0-9.-]+\.[a-z]{2,}(?:[/:?#].*)?$/i.test(raw)) {
      try {
        const url = new URL(/^https?:\/\//i.test(raw) ? raw : "https://" + raw);
        const host = url.hostname.toLowerCase().replace(/^www\./, "");
        const isSocial = SOCIAL_DOMAINS.some(d => host === d || host.endsWith("." + d));
        if (isSocial) {
          return {
            type: "social_url",
            url: url.toString(),
            domain: host,
            label: `Detected ${host} Profile Target`
          };
        }
        return {
          type: "web_url",
          url: url.toString(),
          domain: host,
          label: `Detected Web Target (${host})`
        };
      } catch (_) {}
    }

    // Check if it starts with @ (username handle)
    if (raw.startsWith("@") || /^[a-zA-Z0-9_.-]{3,30}$/.test(raw)) {
      return {
        type: "username",
        handle: raw.replace(/^@/, ""),
        label: `Detected Username Handle (@${raw.replace(/^@/, "")})`
      };
    }

    return { type: "general_search", query: raw };
  }

  // Toggle Advanced Filters Drawer
  if (advToggle && advDrawer) {
    advToggle.addEventListener("click", () => {
      const isOpen = advDrawer.classList.toggle("open");
      advToggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
      advToggle.innerHTML = isOpen 
        ? `<span>Filters</span> <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="18 15 12 9 6 15"></polyline></svg>`
        : `<span>Filters</span> <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 12 15 18 9"></polyline></svg>`;
    });
  }

  // Handle Tab Chips
  tabChips.forEach(chip => {
    chip.addEventListener("click", () => {
      tabChips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      activeCategory = chip.dataset.category;
      const typeSelect = document.getElementById("adv-type");
      if (typeSelect) typeSelect.value = activeCategory;
      if (queryInput.value.trim()) form.dispatchEvent(new Event("submit"));
    });
  });

  // Handle Suggestions clicks
  document.querySelectorAll(".suggestion-tag").forEach(tag => {
      tag.addEventListener("click", () => {
        queryInput.value = tag.textContent.trim();
        forceGeneralSearch = true;
        form.dispatchEvent(new Event("submit"));
      });
  });

  if (queryInput) {
    queryInput.addEventListener("input", () => {
      if (!queryInput.value.trim()) {
        const pageEl = document.querySelector(".universal-search-page");
        if (pageEl) pageEl.classList.remove("has-results");
        if (resultsEl) resultsEl.innerHTML = "";
        if (statusEl) statusEl.textContent = "";
      }
    });
  }

  function renderActionCard(target) {
    if (target.type === "social_url") {
      return `
        <div class="universal-result action-banner" style="border: 1px solid rgba(138, 180, 248, 0.4); background: rgba(138, 180, 248, 0.08);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.75rem;">
            <div>
              <div class="universal-result-meta" style="color: #8ab4f8; margin:0 0 .25rem;">
                <span class="result-badge" style="border-color:#8ab4f8; background:rgba(138,180,248,0.2); color:#ffffff;">AUTONOMOUS RECON TARGET</span>
                <span>${escapeHtml(target.domain)}</span>
              </div>
              <div style="color:#ffffff; font-size:1.05rem; font-weight:600;">Dispatch Ingress Scrape for ${escapeHtml(target.url)}</div>
              <div style="color:#888888; font-size:.82rem; margin-top:.2rem;">Resolves outlink graph, post archives, and network topology.</div>
            </div>
            <button id="btn-fire-scrape" class="glass-submit-btn" style="background:#8ab4f8; color:#000000; padding:.5rem 1.25rem;">
              DISPATCH RECON &rarr;
            </button>
          </div>
          <div id="scrape-dispatch-status" style="margin-top:.75rem; font-family:var(--font-mono); font-size:.78rem; display:none;"></div>
        </div>
      `;
    }

    if (target.type === "username") {
      return `
        <div class="universal-result action-banner" style="border: 1px solid rgba(129, 201, 149, 0.4); background: rgba(129, 201, 149, 0.08);">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:.75rem;">
            <div>
              <div class="universal-result-meta" style="color: #81c995; margin:0 0 .25rem;">
                <span class="result-badge" style="border-color:#81c995; background:rgba(129,201,149,0.2); color:#ffffff;">USERNAME FOOTPRINT SCAN</span>
                <span>@${escapeHtml(target.handle)}</span>
              </div>
              <div style="color:#ffffff; font-size:1.05rem; font-weight:600;">Scan 490+ Public Platforms for @${escapeHtml(target.handle)}</div>
              <div style="color:#888888; font-size:.82rem; margin-top:.2rem;">Cross-platform presence verification via residential mesh.</div>
            </div>
            <button id="btn-fire-username" class="glass-submit-btn" style="background:#81c995; color:#000000; padding:.5rem 1.25rem;">
              LAUNCH SCAN &rarr;
            </button>
          </div>
          <div id="username-dispatch-status" style="margin-top:.75rem; font-family:var(--font-mono); font-size:.78rem; display:none;"></div>
        </div>
      `;
    }

    return "";
  }

  function attachActionHandlers(target) {
    const btnScrape = document.getElementById("btn-fire-scrape");
    if (btnScrape) {
      btnScrape.addEventListener("click", async () => {
        const statusBox = document.getElementById("scrape-dispatch-status");
        statusBox.style.display = "block";
        statusBox.style.color = "#8ab4f8";
        statusBox.textContent = "Connecting to TIR Cloud Mesh Network...";
        btnScrape.disabled = true;

        try {
          const res = await fetch("/api/jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              url: target.url,
              max_posts: 100,
              max_linked_profiles: 20,
              consent: true
            })
          });
          const data = await res.json();
          if (res.ok) {
            statusBox.style.color = "#81c995";
            statusBox.innerHTML = `Recon Job Dispatched. Job ID: <code>${escapeHtml(data.id || data.job_id || 'active')}</code>. <a href="/platform/" style="color:#8ab4f8; text-decoration:underline;">View Live Telemetry in Platform &rarr;</a>`;
          } else {
            statusBox.style.color = "#f28b82";
            statusBox.textContent = `Dispatch error: ${data.error || 'Server error'}. Redirecting to Platform...`;
            setTimeout(() => { window.location.href = `/platform/?target=${encodeURIComponent(target.url)}`; }, 1200);
          }
        } catch (err) {
          // Fallback redirect to platform with prepopulated target
          statusBox.style.color = "#8ab4f8";
          statusBox.textContent = "Redirecting to Ingress Console...";
          window.location.href = `/platform/?target=${encodeURIComponent(target.url)}`;
        }
      });
    }

    const btnUser = document.getElementById("btn-fire-username");
    if (btnUser) {
      btnUser.addEventListener("click", async () => {
        const statusBox = document.getElementById("username-dispatch-status");
        statusBox.style.display = "block";
        statusBox.style.color = "#81c995";
        statusBox.textContent = "Dispatching cross-platform footprint scan...";
        btnUser.disabled = true;

        try {
          const res = await fetch("/api/username-jobs", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              username: target.handle,
              consent: true
            })
          });
          const data = await res.json();
          if (res.ok) {
            statusBox.style.color = "#81c995";
            statusBox.innerHTML = `Footprint Scan Dispatched. <a href="/platform/" style="color:#8ab4f8; text-decoration:underline;">Monitor in Platform &rarr;</a>`;
          } else {
            statusBox.textContent = "Opening Platform Scanner...";
            window.location.href = `/platform/?user=${encodeURIComponent(target.handle)}`;
          }
        } catch (err) {
          window.location.href = `/platform/?user=${encodeURIComponent(target.handle)}`;
        }
      });
    }
  }

  const MASKED_EMAIL_RE = /\b[A-Za-z0-9._%+-]*\*\*\*[A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b/g;

  function formatMaskedEmails(htmlText, recordId) {
    if (!htmlText || !recordId) return htmlText;
    return htmlText.replace(MASKED_EMAIL_RE, (match) => {
      return `<span class="email-reveal-wrap" data-record-id="${escapeHtml(recordId)}"><span class="masked-email">${match}</span> <button type="button" class="btn-reveal-email" data-record-id="${escapeHtml(recordId)}" onclick="event.stopPropagation();">View Email</button></span>`;
    });
  }

  function attachRevealHandlers() {
    document.querySelectorAll(".btn-reveal-email").forEach(btn => {
      if (btn.dataset.bound) return;
      btn.dataset.bound = "true";
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        e.stopPropagation();
        const recordId = btn.dataset.recordId;
        const wrap = btn.closest(".email-reveal-wrap");
        if (!recordId || !wrap) return;

        btn.disabled = true;
        btn.textContent = "Verifying...";
        let turnstileToken = "";
        if (window.turnstile && typeof window.turnstile.getResponse === "function") {
          turnstileToken = window.turnstile.getResponse();
        }

        try {
          const res = await fetch(`/api/records/${encodeURIComponent(recordId)}/reveal`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ turnstileToken })
          });
          const data = await res.json();
          if (!res.ok) {
            btn.textContent = res.status === 429 ? (data.quota_exceeded ? "Quota Reached" : "Sign In to Reveal") : "Error";
            btn.title = data.error || "Could not reveal email";
            if (res.status === 429 && !data.quota_exceeded) {
              btn.disabled = false;
              btn.onclick = (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                if (typeof openAuthModal === "function") openAuthModal();
                else if (document.getElementById("auth-nav-trigger")) document.getElementById("auth-nav-trigger").click();
              };
            } else {
              setTimeout(() => { btn.disabled = false; btn.textContent = "View Email"; }, 2500);
            }
            return;
          }
          const email = data.email || (data.emails && data.emails[0]);
          if (email) {
            wrap.innerHTML = `<a href="mailto:${escapeHtml(email)}" class="revealed-email" onclick="event.stopPropagation();">${escapeHtml(email)}</a>`;
          } else {
            wrap.innerHTML = `<span class="masked-email">None on record</span>`;
          }
        } catch (err) {
          btn.disabled = false;
          btn.textContent = "Error";
          setTimeout(() => { btn.textContent = "View Email"; }, 2000);
        }
      });
    });
  }

  function renderResults(query, results, target) {
    const pageEl = document.querySelector(".universal-search-page");
    if (pageEl) pageEl.classList.add("has-results");
    const actionBannerHtml = renderActionCard(target);

    if (!results || results.length === 0) {
      if (actionBannerHtml) {
        statusEl.textContent = `Zero existing archive hits for "${query}". Ready to launch live job:`;
        resultsEl.innerHTML = actionBannerHtml;
        attachActionHandlers(target);
      } else {
        statusEl.textContent = `No indexed records match "${query}" yet.`;
        resultsEl.innerHTML = "";
      }
      return;
    }

    statusEl.textContent = `Found ${results.length} archive result${results.length === 1 ? "" : "s"} across dataset`;
    const resultsHtml = results.map(item => {
      const title = formatMaskedEmails(escapeHtml(item.title || "Archive Artifact"), item.id);
      const snippet = formatMaskedEmails(escapeHtml(item.snippet || "No preview snippet available."), item.id);
      const source = escapeHtml(item.source || "harvy_dataset");
      const reportLink = item.id ? `/report/artifact/${encodeURIComponent(item.id)}` : (item.url || "#");
      const extLink = item.url ? escapeHtml(item.url) : "";
      const isSocial = item.source === "posts" || item.source === "social";
      const actionText = isSocial ? "View Person Dossier &rarr;" : "View Dossier Report &rarr;";

      return `
        <div class="universal-result-card-wrap">
          <a class="universal-result" href="${reportLink}">
            <div class="universal-result-header">
              <span class="universal-result-title">${title}</span>
              <span class="universal-result-action-pill">${actionText}</span>
            </div>
            <div class="universal-result-meta">
              <span class="result-badge">${source}</span>
              <span class="result-tap-hint">Tap anywhere to open dossier &rarr;</span>
            </div>
            <p class="universal-result-snippet">${snippet}</p>
          </a>
          ${extLink ? `<a href="${extLink}" target="_blank" rel="noopener" class="ext-source-link" onclick="event.stopPropagation();" title="View original external source">Original Source &nearr;</a>` : ''}
        </div>
      `;
    }).join("");

    resultsEl.innerHTML = actionBannerHtml + resultsHtml;
    attachActionHandlers(target);
    attachRevealHandlers();
  }

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();
    const q = queryInput.value.trim();
    if (!q) return;

    const target = forceGeneralSearch ? { type: "general_search", query: q } : detectTargetType(q);
    forceGeneralSearch = false;
    const sourceFilter = document.getElementById("adv-type") ? document.getElementById("adv-type").value : activeCategory;
    const sortFilter = document.getElementById("adv-sort") ? document.getElementById("adv-sort").value : "relevance";

    statusEl.textContent = "Scanning indexed archive...";
    resultsEl.innerHTML = "";

    try {
      const url = new URL("/api/universal-search", window.location.origin);
      url.searchParams.set("q", q);
      if (sourceFilter && sourceFilter !== "all") url.searchParams.set("type", sourceFilter);
      if (sortFilter) url.searchParams.set("sort", sortFilter);

      const res = await fetch(url.toString());
      if (!res.ok) throw new Error("Search service unavailable");
      const data = await res.json();
      renderResults(q, data.results || [], target);
    } catch (err) {
      statusEl.textContent = "Error searching archive. Please try again.";
      if (target.type !== "general_search") {
        resultsEl.innerHTML = renderActionCard(target);
        attachActionHandlers(target);
      }
    }
  });

  // Auto-search if ?q= in URL
  const initialParams = new URLSearchParams(window.location.search);
  const initialQ = initialParams.get("q");
  if (initialQ) {
    queryInput.value = initialQ;
    form.dispatchEvent(new Event("submit"));
  }
})();
