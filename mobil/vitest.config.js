import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";

const ortak = fileURLToPath(new URL("../ortak/src", import.meta.url));

export default defineConfig({
  resolve: { alias: { "@ortak": ortak } },
  test: {
    environment: "node",
    include: ["test/**/*.test.js"],
    testTimeout: 20000,
    // Makine baska bir oturumla paylasiliyor: az isci.
    maxWorkers: 2,
  },
});
