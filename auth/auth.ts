import { betterAuth } from "better-auth";
import { drizzleAdapter } from "@better-auth/drizzle-adapter";
import {
  admin,
  anonymous,
  captcha,
  lastLoginMethod,
  multiSession,
  organization,
  twoFactor,
} from "better-auth/plugins";
import { apiKey } from "@better-auth/api-key";
import { createEmailSender, dash, sentinel } from "@better-auth/infra";
import { passkey } from "@better-auth/passkey";
import { stripe } from "@better-auth/stripe";
import { betterAuthReferral } from "@marinedotsh/better-auth-referral";
import Stripe from "stripe";
import { withCloudflare } from "better-auth-cloudflare";

export interface HarvyAuthEnv {
  HARVY_D1: D1Database;
  BETTER_AUTH_SECRET?: string;
  BETTER_AUTH_URL?: string;
  BETTER_AUTH_BASE_PATH?: string;
  BETTER_AUTH_API_KEY?: string;
  BETTER_AUTH_INFRA_ENABLED?: string;
  BETTER_AUTH_EMAIL_ENABLED?: string;
  HARVY_ADMIN_USER_IDS?: string;
  DISCORD_CLIENT_ID?: string;
  DISCORD_CLIENT_SECRET?: string;
  GITHUB_CLIENT_ID?: string;
  GITHUB_CLIENT_SECRET?: string;
  GOOGLE_CLIENT_ID?: string;
  GOOGLE_CLIENT_SECRET?: string;
  TWITTER_CLIENT_ID?: string;
  TWITTER_CLIENT_SECRET?: string;
  TURNSTILE_SITE_KEY?: string;
  TURNSTILE_SECRET_KEY?: string;
  STRIPE_SECRET_KEY?: string;
  STRIPE_WEBHOOK_SECRET?: string;
  STRIPE_ENABLED?: string;
}

export function authFeatures(env: HarvyAuthEnv) {
  const infrastructure = Boolean(env.BETTER_AUTH_API_KEY && env.BETTER_AUTH_INFRA_ENABLED === "true");
  return {
    enabled: Boolean(env.BETTER_AUTH_SECRET),
    emailPassword: infrastructure && env.BETTER_AUTH_EMAIL_ENABLED === "true",
    passkey: true,
    anonymous: true,
    apiKeys: true,
    organizations: true,
    twoFactor: true,
    multiSession: true,
    admin: true,
    lastLoginMethod: true,
    discord: Boolean(env.DISCORD_CLIENT_ID && env.DISCORD_CLIENT_SECRET),
    github: Boolean(env.GITHUB_CLIENT_ID && env.GITHUB_CLIENT_SECRET),
    google: Boolean(env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET),
    twitter: Boolean(env.TWITTER_CLIENT_ID && env.TWITTER_CLIENT_SECRET),
    captcha: Boolean(env.TURNSTILE_SITE_KEY && env.TURNSTILE_SECRET_KEY),
    turnstileSiteKey: env.TURNSTILE_SITE_KEY || "",
    infrastructure,
    stripe: env.STRIPE_ENABLED === "true" && Boolean(env.STRIPE_SECRET_KEY && env.STRIPE_WEBHOOK_SECRET),
    referrals: true,
  };
}

export function createAuth(env: HarvyAuthEnv, ctx?: ExecutionContext, cf?: object): any {
  const baseURL = env.BETTER_AUTH_URL || "https://harvybot.com";
  const basePath = env.BETTER_AUTH_BASE_PATH || "/api/better-auth";
  const infraKey = env.BETTER_AUTH_API_KEY;
  const infraEnabled = Boolean(infraKey && env.BETTER_AUTH_INFRA_ENABLED === "true");
  const emailEnabled = Boolean(infraEnabled && env.BETTER_AUTH_EMAIL_ENABLED === "true");
  const emailSender = emailEnabled && infraKey ? createEmailSender({ apiKey: infraKey }) : undefined;
  const origin = new URL(baseURL).origin;
  const rpID = new URL(baseURL).hostname;
  const adminUserIds = (env.HARVY_ADMIN_USER_IDS || "").split(",").map((id) => id.trim()).filter(Boolean);
  const socialProviders: Record<string, { clientId: string; clientSecret: string }> = {};

  if (env.DISCORD_CLIENT_ID && env.DISCORD_CLIENT_SECRET) {
    socialProviders.discord = { clientId: env.DISCORD_CLIENT_ID, clientSecret: env.DISCORD_CLIENT_SECRET };
  }
  if (env.GITHUB_CLIENT_ID && env.GITHUB_CLIENT_SECRET) {
    socialProviders.github = { clientId: env.GITHUB_CLIENT_ID, clientSecret: env.GITHUB_CLIENT_SECRET };
  }
  if (env.GOOGLE_CLIENT_ID && env.GOOGLE_CLIENT_SECRET) {
    socialProviders.google = { clientId: env.GOOGLE_CLIENT_ID, clientSecret: env.GOOGLE_CLIENT_SECRET };
  }
  if (env.TWITTER_CLIENT_ID && env.TWITTER_CLIENT_SECRET) {
    socialProviders.twitter = { clientId: env.TWITTER_CLIENT_ID, clientSecret: env.TWITTER_CLIENT_SECRET };
  }

  const plugins: any[] = [
    anonymous({ generateName: () => `ghost-${crypto.randomUUID().slice(0, 8)}` }),
    passkey({ rpID, rpName: "Harvy", origin }),
    twoFactor({ issuer: "Harvy" }),
    admin({ defaultRole: "user", adminRoles: ["admin"], adminUserIds }),
    apiKey({
      defaultPrefix: "harvy_live_",
      defaultKeyLength: 64,
      requireName: true,
      references: "user",
      enableSessionForAPIKeys: true,
      rateLimit: { enabled: true, timeWindow: 60_000, maxRequests: 60 },
    }),
    organization({
      allowUserToCreateOrganization: async (user) => user.emailVerified,
      organizationLimit: 5,
      membershipLimit: 100,
      requireEmailVerificationOnInvitation: true,
    }),
    lastLoginMethod({ storeInDatabase: true, beforeStoreCookie: () => false }),
    multiSession({ maximumSessions: 5 }),
    betterAuthReferral({ maskReferredUserEmail: true }),
  ];

  if (env.TURNSTILE_SITE_KEY && env.TURNSTILE_SECRET_KEY) {
    plugins.push(captcha({ provider: "cloudflare-turnstile", secretKey: env.TURNSTILE_SECRET_KEY }));
  }
  if (infraEnabled && infraKey) {
    plugins.push(dash({ apiKey: infraKey }));
    plugins.push(sentinel({
      apiKey: infraKey,
      security: {
        credentialStuffing: { enabled: true, action: "challenge" },
        botBlocking: { action: "challenge" },
        suspiciousIpBlocking: { action: "challenge" },
        compromisedPassword: { enabled: true, action: "challenge" },
      },
    }));
  }

  if (env.STRIPE_ENABLED === "true" && env.STRIPE_SECRET_KEY && env.STRIPE_WEBHOOK_SECRET) {
    plugins.push(stripe({
      stripeClient: new Stripe(env.STRIPE_SECRET_KEY),
      stripeWebhookSecret: env.STRIPE_WEBHOOK_SECRET,
      createCustomerOnSignUp: false,
    }));
  }

  const emailOptions = emailSender ? {
    emailAndPassword: {
      enabled: true,
      requireEmailVerification: true,
      minPasswordLength: 12,
      maxPasswordLength: 256,
      revokeSessionsOnPasswordReset: true,
      sendResetPassword: async ({ user, url }: { user: { email: string; name: string }; url: string }) => {
        const result = await emailSender.send({
          template: "reset-password",
          to: user.email,
          variables: { resetLink: url, userEmail: user.email, userName: user.name, appName: "Harvy" },
        });
        if (!result.success) throw new Error("Password reset email delivery failed");
      },
    },
    emailVerification: {
      sendOnSignUp: true,
      sendVerificationEmail: async ({ user, url }: { user: { email: string; name: string }; url: string }) => {
        const result = await emailSender.send({
          template: "verify-email",
          to: user.email,
          variables: { verificationUrl: url, userEmail: user.email, userName: user.name, appName: "Harvy" },
        });
        if (!result.success) throw new Error("Email verification delivery failed");
      },
    },
  } : { emailAndPassword: { enabled: false } };

  const options: any = {
      appName: "Harvy",
      baseURL,
      basePath,
      secret: env.BETTER_AUTH_SECRET,
      trustedOrigins: [origin, "https://harvybot.com", "https://www.harvybot.com", "http://localhost:8903", "http://127.0.0.1:8903"],
      socialProviders: socialProviders as any,
      plugins,
      rateLimit: {
        enabled: true,
        window: 60,
        max: 100,
        storage: "database",
        customRules: {
          "/sign-in/email": { window: 60, max: 5 },
          "/sign-up/email": { window: 60, max: 3 },
        },
      },
      verification: { storeInDatabase: true },
      session: { expiresIn: 60 * 60 * 24 * 7, updateAge: 60 * 60 * 24 },
      advanced: {
        useSecureCookies: true,
        backgroundTasks: { handler: (promise: Promise<unknown>) => ctx ? ctx.waitUntil(promise) : void promise.catch(() => {}) },
      },
      ...emailOptions,
    };
  if (env.HARVY_D1) {
    return betterAuth(withCloudflare(
      { d1Native: env.HARVY_D1, autoDetectIpAddress: true, geolocationTracking: false, cf: cf || {} },
      options,
    ) as any);
  }
  return betterAuth({
    ...options,
    database: drizzleAdapter({} as any, { provider: "sqlite" }),
  } as any);
}
