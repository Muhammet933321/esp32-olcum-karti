import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";

// ortak/ TEK KOPYA: ice aktarilir, kopyalanmaz, duzenlenmez (tasarim §3).
const ortak = fileURLToPath(new URL("../ortak/src", import.meta.url));

export default defineConfig({
  base: "./",
  plugins: [vue()],
  resolve: { alias: { "@ortak": ortak } },
  server: { fs: { allow: [".."] } },
  build: { target: "chrome100", outDir: "dist", emptyOutDir: true },
});
