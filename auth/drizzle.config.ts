import { defineConfig } from "drizzle-kit";

export default defineConfig({
  schema: "./auth/auth-schema.ts",
  out: "./auth/migrations",
  dialect: "sqlite",
});
