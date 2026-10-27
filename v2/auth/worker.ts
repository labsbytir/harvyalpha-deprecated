import { createAuth, authFeatures, type HarvyAuthEnv } from "./auth";
import { hasPrivacyAcceptance, signPrivacyConsent, verifyPrivacyConsent } from "./privacy-consent.mts";

export default {
  async fetch(request: Request, env: HarvyAuthEnv, ctx: ExecutionContext): Promise<Response> {
    const url = new URL(request.url);
    if (url.pathname === "/api/better-auth/config" && request.method === "GET") {
      return Response.json(authFeatures(env), { headers: { "Cache-Control": "no-store" } });
    }
    if (!env.BETTER_AUTH_SECRET) {
      return Response.json({ error: "Better Auth is not configured." }, { status: 503 });
    }
    const auth = createAuth(env, ctx, request.cf);
    if (url.pathname === "/__internal/actor" && request.method === "GET") {
      return resolveActor(request, env, auth);
    }
    return handleAuthRequest(request, env, auth);
  },
};

async function resolveActor(request: Request, env: HarvyAuthEnv, auth: ReturnType<typeof createAuth>) {
  const session = await auth.api.getSession({ headers: request.headers });
  if (session?.user) {
    const user = session.user as typeof session.user & { role?: string; twoFactorEnabled?: boolean };
    return Response.json({
      id: user.id,
      username: user.name,
      displayName: user.name,
      role: user.role || "user",
      twoFactorEnabled: Boolean(user.twoFactorEnabled),
      authMethod: "better_auth_session",
    });
  }

  const authorization = request.headers.get("Authorization") || "";
  const apiKey = request.headers.get("x-api-key")
    || (authorization.startsWith("Bearer harvy_live_") ? authorization.slice(7).trim() : "");
  if (!apiKey) return Response.json({ error: "Unauthorized" }, { status: 401 });

  const verified = await auth.api.verifyApiKey({ body: { key: apiKey } });
  if (!verified.valid || !verified.key?.referenceId) {
    return Response.json({ error: "Unauthorized" }, { status: 401 });
  }
  const user = await env.HARVY_D1.prepare(
    "SELECT id, name, role, two_factor_enabled AS twoFactorEnabled FROM user WHERE id = ?",
  ).bind(verified.key.referenceId).first<{
    id: string;
    name: string;
    role?: string;
    twoFactorEnabled?: number;
  }>();
  if (!user) return Response.json({ error: "Unauthorized" }, { status: 401 });
  return Response.json({
    id: user.id,
    username: user.name,
    displayName: user.name,
    role: user.role || "user",
    twoFactorEnabled: Boolean(user.twoFactorEnabled),
    authMethod: "better_auth_api_key",
  });
}

const POLICY_VERSION = "2026-10-v1";
const CONSENT_COOKIE = "harvy_privacy_consent";

async function handleAuthRequest(request: Request, env: HarvyAuthEnv, auth: ReturnType<typeof createAuth>) {
  const url = new URL(request.url);
  const basePath = env.BETTER_AUTH_BASE_PATH || "/api/better-auth";
  const route = url.pathname.slice(basePath.length) || "/";
  const isSocialCallback = route.startsWith("/callback/");
  const isEmailSignup = route === "/sign-up/email";
  const isAnonymousSignup = route === "/sign-in/anonymous";
  const isSocialSignin = route === "/sign-in/social";
  let consentId: string | null = null;
  let acceptedAt: number | null = null;
  let forwarded = request;

  if (request.method === "POST" && (isEmailSignup || isAnonymousSignup || isSocialSignin)) {
    let body: Record<string, unknown>;
    try {
      body = await request.clone().json() as Record<string, unknown>;
    } catch {
      return Response.json({ error: "Privacy Policy acceptance is required." }, { status: 400 });
    }
    if (!hasPrivacyAcceptance(body)) return Response.json({ error: "Privacy Policy acceptance is required." }, { status: 400 });

    acceptedAt = Date.now();
    consentId = crypto.randomUUID();
    const source = isEmailSignup ? "email_signup" : isAnonymousSignup ? "anonymous_signup" : "social_signin";
    try {
      await env.HARVY_D1.prepare(
        "INSERT INTO harvy_auth_privacy_consents (id, accepted_at, policy_version, source) VALUES (?, ?, ?, ?)",
      ).bind(consentId, acceptedAt, POLICY_VERSION, source).run();
    } catch {
      return Response.json({ error: "Privacy consent storage is unavailable." }, { status: 503 });
    }

    delete body.privacyAccepted;
    if (body.additionalData && typeof body.additionalData === "object") {
      delete (body.additionalData as Record<string, unknown>).privacyAccepted;
    }
    const headers = new Headers(request.headers);
    headers.delete("content-length");
    headers.set("X-Harvy-Privacy-Accepted", "true");
    forwarded = new Request(request.url, {
      method: request.method,
      headers,
      body: JSON.stringify(body),
      redirect: request.redirect,
    });
  }

  if (request.method === "GET" && isSocialCallback) {
    const token = request.headers.get("Cookie")?.match(new RegExp(`${CONSENT_COOKIE}=([^;]+)`))?.[1];
    const verified = token ? await verifyPrivacyConsent(token, env.BETTER_AUTH_SECRET || "") : null;
    if (!verified) return Response.json({ error: "Accept the Privacy Policy before signing in." }, { status: 400 });
    consentId = verified.id;
    acceptedAt = verified.acceptedAt;
    const headers = new Headers(request.headers);
    headers.set("X-Harvy-Privacy-Accepted", "true");
    forwarded = new Request(request, { headers });
  }

  const response = await auth.handler(forwarded);
  if (consentId) {
    const result = await response.clone().json().catch(() => null) as { user?: { id?: string } } | null;
    if (result?.user?.id) {
      await env.HARVY_D1.prepare("UPDATE harvy_auth_privacy_consents SET user_id = ? WHERE id = ?")
        .bind(result.user.id, consentId).run();
    }
  }

  const headers = new Headers(response.headers);
  if (isSocialSignin && consentId && acceptedAt) {
    const token = await signPrivacyConsent(consentId, acceptedAt, env.BETTER_AUTH_SECRET || "");
    headers.append("Set-Cookie", `${CONSENT_COOKIE}=${token}; Max-Age=600; Path=${basePath}; HttpOnly; Secure; SameSite=Lax`);
  }
  if (isSocialCallback) {
    headers.append("Set-Cookie", `${CONSENT_COOKIE}=; Max-Age=0; Path=${basePath}; HttpOnly; Secure; SameSite=Lax`);
  }
  return new Response(response.body, { status: response.status, statusText: response.statusText, headers });
}
