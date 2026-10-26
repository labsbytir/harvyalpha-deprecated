import { createAuthClient } from "better-auth/client";
import { anonymousClient, adminClient, lastLoginMethodClient, multiSessionClient, organizationClient, twoFactorClient } from "better-auth/client/plugins";
import { apiKeyClient } from "@better-auth/api-key/client";
import { passkeyClient } from "@better-auth/passkey/client";
import { betterAuthReferralClient } from "@marinedotsh/better-auth-referral";
import { dashClient, sentinelClient } from "@better-auth/infra/client";
import { stripeClient } from "@better-auth/stripe/client";
import { renderAuthPanel } from "./ui";

declare global {
  interface Window {
    harvyAuthClient?: ReturnType<typeof createAuthClient>;
    harvyAuthFeatures?: Record<string, any>;
    harvyAuthReady?: Promise<void>;
    harvyAuthUI?: (container: HTMLElement, user: any, refresh: () => Promise<void>) => void;
  }
}

window.harvyAuthReady = (async () => {
  try {
    const response = await fetch("/api/better-auth/config", { cache: "no-store" });
    const features = await response.json();
    window.harvyAuthFeatures = features;
    if (!response.ok || !features.enabled) return;

    const plugins: any[] = [
      anonymousClient(),
      passkeyClient(),
      twoFactorClient(),
      adminClient(),
      apiKeyClient(),
      organizationClient(),
      lastLoginMethodClient(),
      multiSessionClient(),
      betterAuthReferralClient(),
    ];
    if (features.infrastructure) plugins.push(dashClient(), sentinelClient());
    if (features.stripe) plugins.push(stripeClient({ subscription: false }));

    window.harvyAuthClient = createAuthClient({
      baseURL: window.location.origin,
      basePath: "/api/better-auth",
      plugins,
    });
    window.harvyAuthUI = (container, user, refresh) => renderAuthPanel(window.harvyAuthClient, features, container, user, refresh);
  } catch {
    window.harvyAuthFeatures = { enabled: false };
  }
})();
