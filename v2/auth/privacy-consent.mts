export async function signPrivacyConsent(id: string, acceptedAt: number, secret: string) {
  const value = `${id}.${acceptedAt}`;
  const key = await crypto.subtle.importKey("raw", new TextEncoder().encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign"]);
  const signature = new Uint8Array(await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(value)));
  const encoded = btoa(String.fromCharCode(...signature)).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  return `${value}.${encoded}`;
}

export function hasPrivacyAcceptance(body: unknown) {
  if (!body || typeof body !== "object" || Array.isArray(body)) return false;
  const payload = body as Record<string, unknown>;
  const additional = payload.additionalData;
  return payload.privacyAccepted === true
    || Boolean(additional && typeof additional === "object" && !Array.isArray(additional)
      && (additional as Record<string, unknown>).privacyAccepted === true);
}

export async function verifyPrivacyConsent(token: string, secret: string, now = Date.now()) {
  const [id, timestamp, signature] = token.split(".");
  const acceptedAt = Number(timestamp);
  if (!id || !Number.isFinite(acceptedAt) || !signature || now - acceptedAt > 10 * 60 * 1000 || acceptedAt > now + 30_000) return null;
  const expected = await signPrivacyConsent(id, acceptedAt, secret);
  if (!constantTimeEqual(expected, token)) return null;
  return { id, acceptedAt };
}

function constantTimeEqual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return result === 0;
}
