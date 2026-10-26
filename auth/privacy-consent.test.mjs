import assert from "node:assert/strict";
import test from "node:test";
import { hasPrivacyAcceptance, signPrivacyConsent, verifyPrivacyConsent } from "./privacy-consent.mts";

test("signup requires an explicit privacy acknowledgement", () => {
  assert.equal(hasPrivacyAcceptance({}), false);
  assert.equal(hasPrivacyAcceptance({ privacyAccepted: false }), false);
  assert.equal(hasPrivacyAcceptance({ privacyAccepted: true }), true);
  assert.equal(hasPrivacyAcceptance({ additionalData: { privacyAccepted: true } }), true);
});

test("privacy consent token is accepted for the same secret within ten minutes", async () => {
  const now = 1_800_000_000_000;
  const token = await signPrivacyConsent("consent-id", now, "test-secret");
  assert.deepEqual(await verifyPrivacyConsent(token, "test-secret", now + 1_000), { id: "consent-id", acceptedAt: now });
});

test("privacy consent rejects tampering, wrong secrets, and expiry", async () => {
  const now = 1_800_000_000_000;
  const token = await signPrivacyConsent("consent-id", now, "test-secret");
  assert.equal(await verifyPrivacyConsent(`${token}x`, "test-secret", now), null);
  assert.equal(await verifyPrivacyConsent(token, "different-secret", now), null);
  assert.equal(await verifyPrivacyConsent(token, "test-secret", now + 10 * 60 * 1000 + 1), null);
});
