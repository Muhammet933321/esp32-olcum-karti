import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import panelPaketle from "./araclar/panel_paketle.mjs";
import { fileURLToPath } from "node:url";

// ortak/ TEK KOPYA: ice aktarilir, kopyalanmaz, duzenlenmez (tasarim §3).
const ortak = fileURLToPath(new URL("../ortak/src", import.meta.url));
// Panelin SAF kayit yardimcilari (arayuz3/ekran/kayit_gorunum.js, kayitlar.js) kopyalanmadan ice aktarilir;
// o dosyalar ortak modulleri "/ortak/..." diye cagirir.
const panel = fileURLToPath(new URL("../arayuz3/ekran", import.meta.url));
const TAKMA_ADLAR = [
  { find: "@ortak", replacement: ortak },
  { find: "@panel", replacement: panel },
  { find: /^\/ortak\//, replacement: ortak + "/" },
];

export default defineConfig({
  base: "./",
  // panelPaketle: PC panelinin sablonlarini derlemede render'a cevirir (CSP: unsafe-eval yok; 5P K1).
  // vue(): eski .vue dosyalari (P6 silene dek) ve Vue derleme bayraklari.
  plugins: [panelPaketle(), vue()],
  resolve: { alias: TAKMA_ADLAR },
  server: { fs: { allow: [".."] } },
  build: { target: "chrome100", outDir: "dist", emptyOutDir: true },
});
