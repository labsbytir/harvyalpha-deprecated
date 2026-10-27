// Legacy-v1 fallback host; Vite copies this source to /static/auth-modal.js.
(function () {
  let currentUser = null;

  // Buffer conversion helpers for WebAuthn
  function bufferToBase64url(buffer) {
    const bytes = new Uint8Array(buffer);
    let str = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      str += String.fromCharCode(bytes[i]);
    }
    return btoa(str).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function base64urlToBuffer(base64url) {
    const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/");
    const pad = base64.length % 4 === 0 ? "" : "====".slice(base64.length % 4);
    const binary = atob(base64 + pad);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i);
    }
    return bytes.buffer;
  }

  async function checkSession() {
    if (window.harvyAuthReady) await window.harvyAuthReady;
    if (window.harvyAuthFeatures?.enabled && window.harvyAuthClient) {
      try {
        const result = await window.harvyAuthClient.getSession();
        const user = result.data?.user;
        currentUser = user ? { ...user, username: user.name || user.email || user.id } : null;
        updateNavButton();
      } catch (_) {
        currentUser = null;
        updateNavButton();
      }
      return;
    }
    try {
      const res = await fetch("/api/auth/session");
      if (res.ok) {
        const data = await res.json();
        currentUser = data.user;
        updateNavButton();
      }
    } catch (_) {}
  }

  function updateNavButton() {
    let btn = document.getElementById("auth-nav-trigger");
    if (!btn) {
      const topBar = document.querySelector(".google-top-bar") || document.querySelector(".header-meta") || document.body;
      btn = document.createElement("button");
      btn.id = "auth-nav-trigger";
      btn.className = "auth-nav-btn";
      topBar.appendChild(btn);
      btn.addEventListener("click", openAuthModal);
    }

    if (currentUser) {
      btn.className = "auth-nav-btn logged-in";
      btn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
        <span>@${currentUser.username}</span>
      `;
    } else {
      btn.className = "auth-nav-btn";
      btn.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
        <span>ACCOUNT</span>
      `;
    }
  }

  function openAuthModal() {
    let overlay = document.getElementById("auth-modal-overlay");
    if (overlay) overlay.remove();

    overlay = document.createElement("div");
    overlay.id = "auth-modal-overlay";
    overlay.className = "auth-modal-overlay";

    overlay.innerHTML = `
      <div class="auth-modal-card">
        <div class="auth-modal-header">
          <div class="auth-modal-title">${currentUser ? "Identity &amp; Developer Console" : "Autonomous Access &amp; Passkeys"}</div>
          <button id="auth-modal-close" class="auth-modal-close" aria-label="Close modal">&times;</button>
        </div>
        <div id="auth-modal-body"></div>
      </div>
    `;

    document.body.appendChild(overlay);

    document.getElementById("auth-modal-close").addEventListener("click", () => overlay.remove());
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.remove();
    });

    renderModalContent();
  }

  async function renderModalContent() {
    const container = document.getElementById("auth-modal-body");
    if (!container) return;

    if (window.harvyAuthFeatures?.enabled && window.harvyAuthClient && window.harvyAuthUI) {
      window.harvyAuthUI(container, currentUser, async () => {
        await checkSession();
        await renderModalContent();
      });
      return;
    }

    if (!currentUser) {
      // Logged out: Anonymous Passkey Registration or Passkey Login
      container.innerHTML = `
        <div class="auth-section">
          <div class="auth-section-title">OPTION 1: ANONYMOUS GHOST IDENTITY</div>
          <p style="color:#c9d1d9; font-size:.88rem; line-height:1.5; margin-bottom:1rem;">
            Generate an anonymous cryptographic handle. No email or personal data required. Protected with a hardware Passkey (Touch ID, Face ID, Windows Hello, or Security Key) so you never get locked out.
          </p>
          <label class="auth-consent-row">
            <input id="privacy-accepted" type="checkbox">
            <span>I have read and acknowledge the <a href="/privacy/" target="_blank" rel="noopener">Privacy Policy</a>. Required to create an account.</span>
          </label>
          <button id="btn-create-ghost" class="auth-btn-primary">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2a5 5 0 0 0-5 5v3a5 5 0 0 0 10 0V7a5 5 0 0 0-5-5z"></path><path d="M17 14v1a5 5 0 0 1-10 0v-1"></path><line x1="12" y1="19" x2="12" y2="23"></line><line x1="8" y1="23" x2="16" y2="23"></line></svg>
            GENERATE GHOST IDENTITY (PASSKEY)
          </button>
          <div id="turnstile-container" style="margin-top:1rem;"></div>
          <div id="auth-status-msg" class="auth-status-msg"></div>
        </div>

        <div class="auth-section">
          <div class="auth-section-title">OPTION 2: SIGN IN WITH PASSKEY</div>
          <button id="btn-login-passkey" class="auth-btn-secondary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect><path d="M7 11V7a5 5 0 0 1 10 0v4"></path></svg>
            SIGN IN WITH EXISTING PASSKEY
          </button>
        </div>

        <div class="auth-section">
          <div class="auth-section-title">OPTIONAL: HARVY EMAIL UPDATES</div>
          <p style="color:#c9d1d9; font-size:.84rem; line-height:1.45; margin-bottom:.75rem;">
            Newsletter signup is optional and separate from creating an account. We only send email updates if you explicitly opt in and confirm by email.
          </p>
          <label for="newsletter-email" class="auth-field-label">EMAIL ADDRESS</label>
          <input id="newsletter-email" class="auth-input" type="email" autocomplete="email" maxlength="254" placeholder="you@example.com">
          <label class="auth-consent-row">
            <input id="newsletter-opt-in" type="checkbox">
            <span>I explicitly want Harvy email updates. I can unsubscribe at any time.</span>
          </label>
          <button id="btn-newsletter-subscribe" class="auth-btn-secondary">SUBSCRIBE</button>
          <div id="newsletter-status" class="auth-status-msg" role="status" aria-live="polite"></div>
        </div>
      `;

      attachLoggedOutHandlers();
    } else {
      // Logged in: Dashboard with Profile, 2FA (TOTP), and Better Auth API Keys
      container.innerHTML = `
        <div class="auth-section">
          <div class="auth-section-title">OPERATOR IDENTITY</div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-size:1.1rem; font-weight:700; color:#58a6ff;">@${currentUser.username}</div>
              <div style="font-size:.78rem; color:#8b949e; font-family:var(--font-mono, monospace);">ID: ${currentUser.id.slice(0, 12)}...</div>
            </div>
            <span class="auth-badge ${currentUser.twoFactorEnabled ? 'active' : 'inactive'}">
              ${currentUser.twoFactorEnabled ? '2FA PROTECTED' : '2FA INACTIVE'}
            </span>
          </div>
        </div>

        <div class="auth-section">
          <div class="auth-section-title">AUTHENTICATOR 2FA (TOTP APPS ONLY - NO SMS)</div>
          <p style="color:#c9d1d9; font-size:.84rem; line-height:1.45; margin-bottom:.75rem;">
            Secure your session with Google Authenticator, 1Password, Bitwarden, or Apple Passwords. Zero texting / SIM swap risk.
          </p>
          ${currentUser.twoFactorEnabled 
            ? `<div style="color:#3fb950; font-size:.88rem; font-weight:600; display:flex; align-items:center; gap:.4rem;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
                Authenticator app active
               </div>`
            : `<button id="btn-setup-2fa" class="auth-btn-secondary">CONFIGURE AUTHENTICATOR APP &rarr;</button>
               <div id="totp-setup-area" style="display:none; margin-top:1rem;"></div>`
          }
        </div>

        <div class="auth-section">
          <div class="auth-section-title">API KEY MANAGEMENT (BETTER AUTH)</div>
          <p style="color:#c9d1d9; font-size:.84rem; margin-bottom:.75rem;">
            Scoped API keys for terminal scraping and headless reconnaissance. Authenticate with header <code>x-api-key: harvy_live_...</code>.
          </p>
          <div style="display:flex; gap:.5rem;">
            <input id="new-key-name" class="auth-input" type="text" placeholder="Key name (e.g. Scraper CLI)" maxlength="40">
            <button id="btn-create-key" class="auth-btn-primary" style="width:auto; padding:0 1.25rem; white-space:nowrap;">Generate Key</button>
          </div>
          <div id="new-key-reveal" style="display:none; margin-top:.75rem;"></div>
          <div id="api-keys-list" style="margin-top:1rem;">Loading keys...</div>
        </div>

        <div class="auth-section" style="display:flex; justify-content:space-between; align-items:center;">
          <button id="btn-sign-out" class="btn-revoke" style="padding:.5rem 1rem;">SIGN OUT</button>
        </div>
      `;

      attachLoggedInHandlers();
      loadApiKeys();
    }
  }

  function attachLoggedOutHandlers() {
    const statusMsg = document.getElementById("auth-status-msg");

    const btnGhost = document.getElementById("btn-create-ghost");
    if (btnGhost) {
      btnGhost.addEventListener("click", async () => {
        if (!document.getElementById("privacy-accepted")?.checked) {
          statusMsg.className = "auth-status-msg error";
          statusMsg.style.display = "block";
          statusMsg.textContent = "Acknowledge the Privacy Policy before creating an account.";
          return;
        }
        statusMsg.className = "auth-status-msg";
        statusMsg.style.display = "block";
        statusMsg.textContent = "Generating anonymous identity & requesting passkey...";
        btnGhost.disabled = true;

        try {
          const initRes = await fetch("/api/auth/register-anonymous", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ privacyAccepted: true })
          });
          const initData = await initRes.json();
          if (!initRes.ok) throw new Error(initData.error || "Failed to initialize identity");

          // WebAuthn Passkey Registration
          const publicKeyCredentialCreationOptions = {
            challenge: base64urlToBuffer(initData.challenge),
            rp: { name: "Harvy Autonomous Intelligence", id: window.location.hostname },
            user: {
              id: new TextEncoder().encode(initData.userId),
              name: initData.username,
              displayName: initData.displayName
            },
            pubKeyCredParams: [
              { alg: -7, type: "public-key" }, // ES256
              { alg: -257, type: "public-key" } // RS256
            ],
            authenticatorSelection: {
              residentKey: "preferred",
              userVerification: "preferred"
            },
            timeout: 60000
          };

          const credential = await navigator.credentials.create({
            publicKey: publicKeyCredentialCreationOptions
          });

          // Verify passkey with server
          const verifyRes = await fetch("/api/auth/passkey/register-verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              userId: initData.userId,
              credentialId: bufferToBase64url(credential.rawId),
              publicKey: bufferToBase64url(credential.response.attestationObject || credential.rawId),
              name: "Hardware Passkey"
            })
          });
          const verifyData = await verifyRes.json();
          if (!verifyRes.ok) throw new Error(verifyData.error || "Passkey verification failed");

          currentUser = verifyData.user;
          updateNavButton();
          renderModalContent();
        } catch (err) {
          statusMsg.className = "auth-status-msg error";
          statusMsg.textContent = err.name === "NotAllowedError" 
            ? "Passkey registration was cancelled or timed out." 
            : (err.message || "Failed to register passkey.");
          btnGhost.disabled = false;
        }
      });
    }

    const newsletterButton = document.getElementById("btn-newsletter-subscribe");
    if (newsletterButton) {
      newsletterButton.addEventListener("click", async () => {
        const newsletterStatus = document.getElementById("newsletter-status");
        const email = document.getElementById("newsletter-email").value.trim();
        if (!document.getElementById("privacy-accepted")?.checked) {
          newsletterStatus.className = "auth-status-msg error";
          newsletterStatus.textContent = "Acknowledge the Privacy Policy before subscribing.";
          return;
        }
        if (!document.getElementById("newsletter-opt-in")?.checked) {
          newsletterStatus.className = "auth-status-msg error";
          newsletterStatus.textContent = "Tick the separate email-updates opt-in to subscribe.";
          return;
        }
        if (!email) {
          newsletterStatus.className = "auth-status-msg error";
          newsletterStatus.textContent = "Enter an email address.";
          return;
        }
        newsletterButton.disabled = true;
        newsletterStatus.className = "auth-status-msg";
        newsletterStatus.style.display = "block";
        newsletterStatus.textContent = "Submitting subscription…";
        try {
          const response = await fetch("/api/newsletter/subscribe", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, privacyAccepted: true, newsletterOptIn: true })
          });
          const data = await response.json();
          if (!response.ok) throw new Error(data.error || "Subscription could not be submitted.");
          newsletterStatus.className = "auth-status-msg success";
          newsletterStatus.textContent = data.message || "Check your email to confirm subscription.";
        } catch (error) {
          newsletterStatus.className = "auth-status-msg error";
          newsletterStatus.textContent = error.message || "Subscription could not be submitted.";
          newsletterButton.disabled = false;
        }
      });
    }

    const btnLogin = document.getElementById("btn-login-passkey");
    if (btnLogin) {
      btnLogin.addEventListener("click", async () => {
        statusMsg.className = "auth-status-msg";
        statusMsg.style.display = "block";
        statusMsg.textContent = "Requesting passkey from your device...";
        btnLogin.disabled = true;

        try {
          const challRes = await fetch("/api/auth/passkey/login-challenge", { method: "POST" });
          const challData = await challRes.json();
          if (!challRes.ok) throw new Error(challData.error || "Failed to get challenge");

          const assertion = await navigator.credentials.get({
            publicKey: {
              challenge: base64urlToBuffer(challData.challenge),
              userVerification: "preferred",
              timeout: 60000
            }
          });

          const verifyRes = await fetch("/api/auth/passkey/login-verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              credentialId: bufferToBase64url(assertion.rawId),
              challengeId: challData.challengeId
            })
          });
          const verifyData = await verifyRes.json();
          if (!verifyRes.ok) throw new Error(verifyData.error || "Passkey sign-in failed");

          currentUser = verifyData.user;
          updateNavButton();
          renderModalContent();
        } catch (err) {
          statusMsg.className = "auth-status-msg error";
          statusMsg.textContent = err.name === "NotAllowedError" 
            ? "Passkey authentication was cancelled." 
            : (err.message || "Failed to sign in with passkey.");
          btnLogin.disabled = false;
        }
      });
    }
  }

  function attachLoggedInHandlers() {
    const btn2fa = document.getElementById("btn-setup-2fa");
    if (btn2fa) {
      btn2fa.addEventListener("click", async () => {
        btn2fa.disabled = true;
        btn2fa.textContent = "Generating TOTP Key...";
        const area = document.getElementById("totp-setup-area");
        area.style.display = "block";

        try {
          const res = await fetch("/api/auth/2fa/generate", { method: "POST" });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Failed to generate 2FA");

          area.innerHTML = `
            <div style="background:#090d13; border:1px solid #30363d; padding:1rem; border-radius:8px;">
              <div style="font-size:.8rem; color:#8b949e; margin-bottom:.5rem;">ENTER THIS SECRET INTO YOUR AUTHENTICATOR APP:</div>
              <div style="font-family:var(--font-mono, monospace); font-size:1.05rem; font-weight:700; color:#58a6ff; letter-spacing:0.1em; word-break:break-all;">
                ${data.secret}
              </div>
              <div style="margin-top:.75rem;">
                <label style="font-size:.78rem; color:#8b949e; display:block; margin-bottom:.35rem;">VERIFICATION CODE (6 DIGITS):</label>
                <div style="display:flex; gap:.5rem;">
                  <input id="totp-code-input" class="auth-input" type="text" placeholder="123456" maxlength="6" style="width:140px; font-family:var(--font-mono, monospace); font-size:1.1rem; text-align:center;">
                  <button id="btn-verify-totp" class="auth-btn-primary" style="width:auto; padding:0 1.25rem;">VERIFY &amp; ACTIVATE</button>
                </div>
              </div>
              <div style="font-size:.75rem; color:#8b949e; margin-top:.75rem;">EMERGENCY BACKUP CODES:</div>
              <div class="backup-codes-grid">
                ${data.backupCodes.map(c => `<div>${c}</div>`).join("")}
              </div>
              <div id="totp-error" style="color:#f85149; font-size:.8rem; margin-top:.5rem; display:none;"></div>
            </div>
          `;

          document.getElementById("btn-verify-totp").addEventListener("click", async () => {
            const code = document.getElementById("totp-code-input").value.trim();
            const errBox = document.getElementById("totp-error");
            errBox.style.display = "none";

            try {
              const vRes = await fetch("/api/auth/2fa/verify", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ code })
              });
              const vData = await vRes.json();
              if (!vRes.ok) throw new Error(vData.error || "Code verification failed");
              currentUser.twoFactorEnabled = true;
              renderModalContent();
            } catch (vErr) {
              errBox.style.display = "block";
              errBox.textContent = vErr.message;
            }
          });
        } catch (err) {
          btn2fa.disabled = false;
          btn2fa.textContent = "Error generating 2FA. Try again.";
        }
      });
    }

    const btnCreateKey = document.getElementById("btn-create-key");
    if (btnCreateKey) {
      btnCreateKey.addEventListener("click", async () => {
        const nameInput = document.getElementById("new-key-name");
        const name = nameInput.value.trim() || "CLI Key";
        btnCreateKey.disabled = true;

        try {
          const res = await fetch("/api/auth/api-keys", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name })
          });
          const data = await res.json();
          if (!res.ok) throw new Error(data.error || "Failed to create API key");

          nameInput.value = "";
          const reveal = document.getElementById("new-key-reveal");
          reveal.style.display = "block";
          reveal.innerHTML = `
            <div style="background:rgba(63,185,80,0.12); border:1px solid rgba(63,185,80,0.4); padding:.85rem; border-radius:8px;">
              <div style="color:#3fb950; font-size:.78rem; font-weight:700;">KEY CREATED: COPY NOW (WILL NOT BE SHOWN AGAIN)</div>
              <div style="display:flex; gap:.5rem; margin-top:.4rem; align-items:center;">
                <input id="raw-key-val" class="auth-input" type="text" readonly value="${data.key}" style="font-family:var(--font-mono, monospace); font-size:.85rem; color:#3fb950;">
                <button id="btn-copy-key" class="auth-btn-secondary" style="width:auto; margin:0; padding:0 .85rem; white-space:nowrap;">Copy</button>
              </div>
            </div>
          `;

          document.getElementById("btn-copy-key").addEventListener("click", () => {
            const input = document.getElementById("raw-key-val");
            input.select();
            navigator.clipboard.writeText(input.value);
            document.getElementById("btn-copy-key").textContent = "Copied!";
          });

          loadApiKeys();
        } catch (err) {
          alert(err.message);
        } finally {
          btnCreateKey.disabled = false;
        }
      });
    }

    const btnSignOut = document.getElementById("btn-sign-out");
    if (btnSignOut) {
      btnSignOut.addEventListener("click", async () => {
        await fetch("/api/auth/sign-out", { method: "POST" });
        currentUser = null;
        updateNavButton();
        renderModalContent();
      });
    }
  }

  async function loadApiKeys() {
    const listEl = document.getElementById("api-keys-list");
    if (!listEl) return;

    try {
      const res = await fetch("/api/auth/api-keys");
      const data = await res.json();
      if (!res.ok || !data.keys || data.keys.length === 0) {
        listEl.innerHTML = `<div style="color:#8b949e; font-size:.82rem; font-style:italic;">No active API keys yet.</div>`;
        return;
      }

      listEl.innerHTML = `
        <table class="api-keys-table">
          <thead>
            <tr>
              <th>LABEL</th>
              <th>PREFIX</th>
              <th>CREATED</th>
              <th>ACTION</th>
            </tr>
          </thead>
          <tbody>
            ${data.keys.map(k => `
              <tr>
                <td style="font-weight:600;">${escapeHtml(k.name)}</td>
                <td><code class="api-key-code">${escapeHtml(k.key_prefix)}</code></td>
                <td>${new Date(k.created_at * 1000).toLocaleDateString()}</td>
                <td><button class="btn-revoke" data-key-id="${escapeHtml(k.id)}">Revoke</button></td>
              </tr>
            `).join("")}
          </tbody>
        </table>
      `;

      listEl.querySelectorAll(".btn-revoke").forEach(btn => {
        btn.addEventListener("click", async () => {
          const id = btn.getAttribute("data-key-id");
          if (!confirm("Revoke this API key? Any script using it will stop working immediately.")) return;
          await fetch(`/api/auth/api-keys/${id}`, { method: "DELETE" });
          loadApiKeys();
        });
      });
    } catch (_) {
      listEl.innerHTML = `<div style="color:#f85149; font-size:.82rem;">Failed to load API keys.</div>`;
    }
  }

  function escapeHtml(str) {
    return String(str || "").replace(/[&<>"']/g, m => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    }[m]));
  }

  // Initialize
  document.addEventListener("DOMContentLoaded", () => {
    checkSession();
  });
})();
