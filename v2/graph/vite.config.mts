import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// IIFE bundle in the style of v2/auth/vite.config.mts; the page shell is
// pages/query.html -> static/query/index.html via v2/scripts/build_templates.py.
export default defineConfig({
  root: fileURLToPath(new URL(".", import.meta.url)),
  plugins: [react()],
  define: { "process.env.NODE_ENV": '"production"' },
  build: {
    outDir: fileURLToPath(new URL("../../static", import.meta.url)),
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL("./src/main.tsx", import.meta.url)),
      name: "HarvyQuery",
      formats: ["iife"],
      fileName: () => "query-app.js",
      cssFileName: "query-app",
    },
  },
});
