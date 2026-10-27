(() => {
  let currentUser = null;

  async function refresh() {
    await window.harvyAuthReady;
    if (window.harvyAuthFeatures?.enabled && window.harvyAuthClient) {
      try {
        currentUser = (await window.harvyAuthClient.getSession()).data?.user || null;
      } catch {
        currentUser = null;
      }
    } else {
      currentUser = null;
    }
    updateNavButton();
    renderModalBody();
  }

  function updateNavButton() {
    const parent = document.querySelector(".google-top-bar") || document.querySelector(".header-meta") || document.body;
    let button = document.getElementById("auth-nav-trigger");
    if (!button) {
      button = document.createElement("button");
      button.id = "auth-nav-trigger";
      button.type = "button";
      button.className = "auth-nav-btn";
      button.addEventListener("click", openAuthModal);
      parent.appendChild(button);
    }
    button.textContent = currentUser ? `@${currentUser.name || currentUser.email || currentUser.id}` : "ACCOUNT";
    button.classList.toggle("logged-in", Boolean(currentUser));
  }

  function renderModalBody() {
    const container = document.getElementById("auth-modal-body");
    if (!container) return;
    if (!window.harvyAuthFeatures?.enabled || !window.harvyAuthUI) {
      container.textContent = "Authentication is not enabled for this deployment.";
      return;
    }
    window.harvyAuthUI(container, currentUser, refresh);
  }

  function openAuthModal() {
    document.getElementById("auth-modal-overlay")?.remove();
    const overlay = document.createElement("div");
    overlay.id = "auth-modal-overlay";
    overlay.className = "auth-modal-overlay";
    overlay.innerHTML = `
      <section class="auth-modal-card" role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
        <header class="auth-modal-header">
          <div id="auth-modal-title" class="auth-modal-title">Account</div>
          <button id="auth-modal-close" class="auth-modal-close" type="button" aria-label="Close">&times;</button>
        </header>
        <div id="auth-modal-body"></div>
      </section>`;
    document.body.appendChild(overlay);
    overlay.querySelector("#auth-modal-close").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (event) => {
      if (event.target === overlay) overlay.remove();
    });
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "Escape") overlay.remove();
    });
    void refresh();
  }

  window.openHarvyAuthModal = openAuthModal;

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => void refresh(), { once: true });
  } else {
    void refresh();
  }
})();
