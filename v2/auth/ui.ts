type HarvyUser = { id: string; name?: string; email?: string; role?: string; twoFactorEnabled?: boolean };
type AuthFeatures = Record<string, any> & { providers?: string[]; turnstileSiteKey?: string };

declare global {
  interface Window {
    turnstile?: any;
    __harvyTurnstileLoader?: Promise<void>;
  }
}

export async function renderAuthPanel(client: any, features: AuthFeatures, container: HTMLElement, user: HarvyUser | null, refresh: () => Promise<void>) {
  if (!user) {
    renderSignIn(client, features, container, refresh);
    return;
  }
  renderAccount(client, features, container, user, refresh);
}

function renderSignIn(client: any, features: AuthFeatures, container: HTMLElement, refresh: () => Promise<void>) {
  const providers = ["google", "github", "discord", "twitter"].filter((provider) => features[provider]);
  container.innerHTML = `
    <section class="auth-section">
      <div class="auth-section-title">PASSKEY IDENTITY</div>
      <p class="auth-help">Create an anonymous account with a passkey, or sign in with an existing passkey. No email is required for anonymous accounts.</p>
      <label class="auth-consent-row"><input id="ba-privacy" type="checkbox"><span>I accept Harvy's <a href="/privacy/" target="_blank" rel="noopener">Privacy Policy</a>.</span></label>
      <button id="ba-anonymous" class="auth-btn-primary">CREATE PASSKEY IDENTITY</button>
      <button id="ba-passkey-login" class="auth-btn-secondary">SIGN IN WITH PASSKEY</button>
      <div id="ba-message" class="auth-message" role="status"></div>
    </section>
    ${features.emailPassword ? `
    <section class="auth-section">
      <div class="auth-section-title">EMAIL &amp; PASSWORD</div>
      <label class="auth-field-label" for="ba-name">DISPLAY NAME</label><input id="ba-name" class="auth-input" autocomplete="name" maxlength="80">
      <label class="auth-field-label" for="ba-email">EMAIL</label><input id="ba-email" class="auth-input" type="email" autocomplete="email" maxlength="254">
      <label class="auth-field-label" for="ba-password">PASSWORD</label><input id="ba-password" class="auth-input" type="password" autocomplete="new-password" minlength="12" maxlength="256">
      ${features.captcha ? `<div id="ba-turnstile" class="auth-turnstile"></div>` : ""}
      <div class="auth-actions"><button id="ba-email-signup" class="auth-btn-primary">CREATE ACCOUNT</button><button id="ba-email-login" class="auth-btn-secondary">SIGN IN</button></div>
    </section>` : `<section class="auth-section"><div class="auth-section-title">EMAIL SIGN-IN</div><p class="auth-help">Email/password sign-in will be enabled after transactional email is configured.</p></section>`}
    ${providers.length ? `<section class="auth-section"><div class="auth-section-title">SOCIAL SIGN-IN</div><div class="ba-social-grid">${providers.map((provider) => `<button class="auth-btn-secondary" data-provider="${provider}">CONTINUE WITH ${provider.toUpperCase()}</button>`).join("")}</div></section>` : ""}
  `;

  const message = (text: string, error = false) => {
    const node = container.querySelector<HTMLElement>("#ba-message");
    if (node) {
      node.textContent = text;
      node.dataset.error = error ? "true" : "false";
    }
  };
  const ensurePrivacy = () => {
    const accepted = container.querySelector<HTMLInputElement>("#ba-privacy")?.checked === true;
    if (!accepted) message("Accept the Privacy Policy before creating or linking an account.", true);
    return accepted;
  };
  const captchaOptions = async () => {
    if (!features.captcha) return undefined;
    const token = await getTurnstileToken(features.turnstileSiteKey);
    return { fetchOptions: { headers: { "x-captcha-response": token } } };
  };

  container.querySelector("#ba-anonymous")?.addEventListener("click", async () => {
    if (!ensurePrivacy()) return;
    message("Creating the anonymous identity and registering your passkey…");
    try {
      const result = await client.signIn.anonymous({ privacyAccepted: true });
      if (result.error) throw new Error(result.error.message || "Could not create an anonymous identity.");
      const passkeyResult = await client.passkey.addPasskey({ name: "Harvy passkey" });
      if (passkeyResult.error) {
        await client.deleteAnonymousUser();
        await client.signOut();
        throw new Error("Passkey registration did not complete. The temporary account was removed; try again.");
      }
      await refresh();
    } catch (error) {
      message(error instanceof Error ? error.message : "Authentication failed.", true);
    }
  });

  container.querySelector("#ba-passkey-login")?.addEventListener("click", async () => {
    message("Waiting for your passkey…");
    const result = await client.signIn.passkey({ autoFill: false });
    if (result.error) return message(result.error.message || "Passkey sign-in failed.", true);
    await refresh();
  });

  container.querySelector("#ba-email-signup")?.addEventListener("click", async () => {
    if (!ensurePrivacy()) return;
    const name = container.querySelector<HTMLInputElement>("#ba-name")?.value.trim() || "";
    const email = container.querySelector<HTMLInputElement>("#ba-email")?.value.trim() || "";
    const password = container.querySelector<HTMLInputElement>("#ba-password")?.value || "";
      if (!name || !email || password.length < 12) return message("Enter a display name, valid email, and password of at least 12 characters.", true);
    const captcha = await captchaOptions();
    const result = await client.signUp.email({ name, email, password, privacyAccepted: true, callbackURL: location.origin }, captcha);
    if (result.error) return message(result.error.message || "Account creation failed.", true);
    message("Account created. Check your inbox to verify your email address.");
  });

  container.querySelector("#ba-email-login")?.addEventListener("click", async () => {
    const email = container.querySelector<HTMLInputElement>("#ba-email")?.value.trim() || "";
    const password = container.querySelector<HTMLInputElement>("#ba-password")?.value || "";
    const captcha = await captchaOptions();
    const result = await client.signIn.email({ email, password }, captcha);
    if (result.error) return message(result.error.message || "Email sign-in failed.", true);
    if ((result.data as any)?.twoFactorRedirect) {
      const code = prompt("Enter the code from your authenticator app.") || "";
      const verified = await client.twoFactor.verifyTotp({ code, trustDevice: true });
      if (verified.error) return message(verified.error.message || "Authenticator code was not accepted.", true);
    }
    await refresh();
  });

  container.querySelectorAll<HTMLButtonElement>("[data-provider]").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!ensurePrivacy()) return;
      const provider = button.dataset.provider;
      if (!provider) return;
      await client.signIn.social({ provider, callbackURL: location.href, requestSignUp: true, additionalData: { privacyAccepted: true } });
    });
  });
}

async function getTurnstileToken(siteKey?: string) {
  if (!siteKey) throw new Error("Turnstile is enabled but its public site key is not configured.");
  if (!window.turnstile) {
    window.__harvyTurnstileLoader ||= new Promise<void>((resolve, reject) => {
      const script = document.createElement("script");
      script.src = "https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit";
      script.async = true;
      script.onload = () => resolve();
      script.onerror = () => reject(new Error("Could not load Turnstile."));
      document.head.appendChild(script);
    });
    await window.__harvyTurnstileLoader;
  }
  const host = document.getElementById("ba-turnstile");
  if (!host) throw new Error("Turnstile container is missing.");
  return await new Promise<string>((resolve, reject) => {
    host.replaceChildren();
    window.turnstile.render(host, {
      sitekey: siteKey,
      callback: (token: string) => resolve(token),
      "error-callback": () => reject(new Error("Turnstile verification failed.")),
      "expired-callback": () => reject(new Error("Turnstile expired; try again.")),
    });
  });
}

function renderAccount(client: any, features: AuthFeatures, container: HTMLElement, user: HarvyUser, refresh: () => Promise<void>) {
  container.innerHTML = `
    <section class="auth-section">
      <div class="auth-section-title">IDENTITY</div>
      <div class="auth-help">${escapeHtml(user.name || user.id)}${user.email ? ` · ${escapeHtml(user.email)}` : ""}</div>
      <div class="auth-actions"><button id="ba-add-passkey" class="auth-btn-secondary">ADD PASSKEY</button><button id="ba-sign-out" class="auth-btn-secondary">SIGN OUT</button></div>
      <div id="ba-message" class="auth-message" role="status"></div>
    </section>
    <section class="auth-section"><div class="auth-section-title">API KEYS</div>
      <label class="auth-field-label" for="ba-key-name">KEY NAME</label><input id="ba-key-name" class="auth-input" maxlength="80">
      <button id="ba-create-key" class="auth-btn-primary">CREATE KEY</button><div id="ba-key-result"></div><div id="ba-key-list" class="auth-list"></div>
    </section>
    <section class="auth-section"><div class="auth-section-title">AUTHENTICATOR APP</div>
      <p class="auth-help">TOTP authenticator codes; no SMS. Email/password accounts can enable this with their password.</p>
      <button id="ba-enable-2fa" class="auth-btn-secondary">SET UP AUTHENTICATOR</button><div id="ba-2fa-result"></div>
    </section>
    <section class="auth-section"><div class="auth-section-title">DATA ENVIRONMENTS</div>
      <p class="auth-help">Organizations scope private customer data; shared Harvy ontology objects remain shared.</p>
      <label class="auth-field-label" for="ba-org-name">NEW ENVIRONMENT</label><input id="ba-org-name" class="auth-input" maxlength="80">
      <button id="ba-create-org" class="auth-btn-secondary">CREATE ENVIRONMENT</button><div id="ba-org-list" class="auth-list"></div>
    </section>
    <section class="auth-section"><div class="auth-section-title">SESSIONS</div><div id="ba-session-list" class="auth-list"></div></section>
    <section class="auth-section"><div class="auth-section-title">REFERRALS</div><div id="ba-referral" class="auth-list"></div></section>
    ${features.infrastructure ? `<section class="auth-section"><div class="auth-section-title">AUDIT ACTIVITY</div><div id="ba-audit-list" class="auth-list"></div></section>` : ""}
    ${user.role === "admin" ? `<section class="auth-section"><div class="auth-section-title">ADMIN</div><div id="ba-admin-list" class="auth-list"></div></section>` : ""}
  `;

  const message = (text: string, error = false) => {
    const node = container.querySelector<HTMLElement>("#ba-message");
    if (node) { node.textContent = text; node.dataset.error = error ? "true" : "false"; }
  };
  container.querySelector("#ba-sign-out")?.addEventListener("click", async () => {
    await client.signOut();
    await refresh();
  });
  container.querySelector("#ba-add-passkey")?.addEventListener("click", async () => {
    const result = await client.passkey.addPasskey({ name: "Harvy passkey" });
    message(result.error?.message || "Passkey added.", Boolean(result.error));
  });
  container.querySelector("#ba-create-key")?.addEventListener("click", async () => {
    const name = container.querySelector<HTMLInputElement>("#ba-key-name")?.value.trim() || "";
    if (!name) return message("Name the API key first.", true);
    const result = await client.apiKey.create({ name, expiresIn: 90 * 24 * 60 * 60 });
    if (result.error) return message(result.error.message || "Key creation failed.", true);
    const key = (result.data as any)?.key;
    const display = container.querySelector<HTMLElement>("#ba-key-result");
    if (display && key) display.innerHTML = `<div class="auth-key-once"><strong>Copy this key now; it will not be shown again.</strong><br><code>${escapeHtml(key)}</code></div>`;
    await loadApiKeys(client, container);
  });
  container.querySelector("#ba-enable-2fa")?.addEventListener("click", async () => {
    const password = prompt("Confirm your account password to set up app-based two-factor authentication.") || "";
    if (!password) return;
    const result = await client.twoFactor.enable({ password });
    const output = container.querySelector<HTMLElement>("#ba-2fa-result");
    if (result.error) { if (output) output.textContent = result.error.message || "Could not start 2FA setup."; return; }
    const setup = result.data as any;
    if (!output || !setup?.totpURI) return;
    output.innerHTML = `<p>Import this URI in your authenticator app, then verify a current code:</p><code>${escapeHtml(setup.totpURI)}</code><label class="auth-field-label" for="ba-totp-code">AUTHENTICATOR CODE</label><input id="ba-totp-code" class="auth-input" inputmode="numeric" autocomplete="one-time-code" maxlength="8"><button id="ba-verify-totp" class="auth-btn-secondary">VERIFY &amp; ENABLE</button>`;
    output.querySelector("#ba-verify-totp")?.addEventListener("click", async () => {
      const code = output.querySelector<HTMLInputElement>("#ba-totp-code")?.value.trim() || "";
      const verified = await client.twoFactor.verifyTotp({ code, trustDevice: true });
      if (verified.error) { message(verified.error.message || "Authenticator code was not accepted.", true); return; }
      output.innerHTML = `<p>Two-factor authentication is enabled. Store these one-time backup codes securely:</p><code>${(setup.backupCodes || []).map(escapeHtml).join("<br>")}</code>`;
    });
  });
  container.querySelector("#ba-create-org")?.addEventListener("click", async () => {
    const name = container.querySelector<HTMLInputElement>("#ba-org-name")?.value.trim() || "";
    if (!name) return message("Enter an environment name.", true);
    const slug = name.toLowerCase().normalize("NFKD").replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48);
    const result = await client.organization.create({ name, slug });
    if (result.error) return message(result.error.message || "Environment creation failed.", true);
    await loadOrganizations(client, container);
  });

  void loadApiKeys(client, container);
  void loadOrganizations(client, container);
  void loadSessions(client, container);
  void loadReferrals(client, container);
  if (features.infrastructure) void loadAudit(client, container);
  if (user.role === "admin") void loadAdmin(client, container);
}

async function loadApiKeys(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-key-list");
  if (!node) return;
  const result = await client.apiKey.list({ query: { limit: 20 } });
  const keys = (result.data as any)?.apiKeys || [];
  node.innerHTML = keys.length ? keys.map((key: any) => `<div class="auth-list-row"><span>${escapeHtml(key.name || "API key")} · ${escapeHtml(key.start || "harvy_live_")}</span><button class="auth-btn-secondary" data-revoke-key="${escapeHtml(key.id)}">REVOKE</button></div>`).join("") : "<p>No active API keys.</p>";
  node.querySelectorAll<HTMLButtonElement>("[data-revoke-key]").forEach((button) => button.addEventListener("click", async () => {
    await client.apiKey.delete({ keyId: button.dataset.revokeKey });
    await loadApiKeys(client, container);
  }));
}

async function loadOrganizations(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-org-list");
  if (!node) return;
  const result = await client.organization.list();
  const organizations = result.data || [];
  node.innerHTML = organizations.length ? organizations.map((org: any) => `<div class="auth-list-row">${escapeHtml(org.name)}</div>`).join("") : "<p>No customer environments yet.</p>";
}

async function loadSessions(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-session-list");
  if (!node) return;
  const result = await client.multiSession.listDeviceSessions();
  const sessions = (result.data as any)?.sessions || [];
  node.innerHTML = sessions.length ? `${sessions.length} active session(s). Manage or revoke sessions in account settings.` : "<p>Session list unavailable.</p>";
}

async function loadReferrals(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-referral");
  if (!node) return;
  const result = await client.getMyReferralDashboard();
  node.textContent = result.data?.code ? `Referral code: ${result.data.code}` : "Referral code not available yet.";
}

async function loadAudit(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-audit-list");
  if (!node) return;
  const session = await client.getSession();
  const result = await client.dash.getAuditLogs({ session: session.data, limit: 10, offset: 0 });
  const events = result.data?.events || [];
  node.innerHTML = events.length ? events.map((event: any) => `<div class="auth-list-row">${escapeHtml(event.eventType || event.type || "Activity")}</div>`).join("") : "<p>No audit events.</p>";
}

async function loadAdmin(client: any, container: HTMLElement) {
  const node = container.querySelector<HTMLElement>("#ba-admin-list");
  if (!node) return;
  const result = await client.admin.listUsers({ query: { limit: 20, offset: 0 } });
  const users = result.data?.users || [];
  node.innerHTML = users.length ? users.map((user: any) => `<div class="auth-list-row">${escapeHtml(user.name)} · ${escapeHtml(user.email || "anonymous")}</div>`).join("") : "<p>No users.</p>";
}

function escapeHtml(value: unknown) {
  return String(value || "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[char] as string));
}
