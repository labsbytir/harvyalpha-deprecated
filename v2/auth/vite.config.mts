import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const authRoot = fileURLToPath(new URL(".", import.meta.url));

export default defineConfig({
  root: authRoot,
  publicDir: fileURLToPath(new URL("./public", import.meta.url)),
  build: {
    outDir: fileURLToPath(new URL("../../static", import.meta.url)),
    emptyOutDir: false,
    lib: {
      entry: fileURLToPath(new URL("./client.ts", import.meta.url)),
      name: "HarvyAuthClient",
      formats: ["iife"],
      fileName: () => "auth-client.js",
    },
  },
});
