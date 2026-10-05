import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

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
  resolve: { alias: TAKMA_ADLAR },
  test: {
    environment: "node",
    include: ["test/**/*.test.js"],
    testTimeout: 20000,
    // Makine baska bir oturumla paylasiliyor: az isci.
    maxWorkers: 2,
  },
});
