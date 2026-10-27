import { createAuth, type HarvyAuthEnv } from "./auth";

const variables = ((globalThis as any).process?.env || {}) as Record<string, string | undefined>;
if (!variables.BETTER_AUTH_SECRET) {
  throw new Error("Set a temporary BETTER_AUTH_SECRET when generating the auth schema.");
}

// The Better Auth CLI only inspects options/plugins; it must never connect to D1.
export const auth = createAuth({
  HARVY_D1: undefined as unknown as HarvyAuthEnv["HARVY_D1"],
  BETTER_AUTH_SECRET: variables.BETTER_AUTH_SECRET,
  BETTER_AUTH_URL: "https://harvybot.com",
  BETTER_AUTH_API_KEY: variables.BETTER_AUTH_API_KEY,
  BETTER_AUTH_INFRA_ENABLED: variables.BETTER_AUTH_INFRA_ENABLED,
  BETTER_AUTH_EMAIL_ENABLED: variables.BETTER_AUTH_EMAIL_ENABLED,
  TURNSTILE_SECRET_KEY: variables.TURNSTILE_SECRET_KEY,
  TURNSTILE_SITE_KEY: variables.TURNSTILE_SITE_KEY,
  STRIPE_SECRET_KEY: variables.STRIPE_SECRET_KEY,
  STRIPE_WEBHOOK_SECRET: variables.STRIPE_WEBHOOK_SECRET,
  STRIPE_ENABLED: variables.STRIPE_ENABLED,
}, undefined, {});
