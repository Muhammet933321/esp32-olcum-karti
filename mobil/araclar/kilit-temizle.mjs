// package-lock.json'daki "deprecated" aciklamalarini kisaltir. npm bu alana paket yazarinin serbest
// metnini (bazen bir e-posta adresi) koyar; depo herkese acik ve gizlilik denetimi dosyadaki her
// e-posta bicimini kirmizi sayar. Alan yalniz bilgi amaclidir: `npm ci` surumleri ve ozetleri
// (integrity) kullanir, onlara DOKUNULMAZ. Her `npm install`dan sonra: `npm run kilit`.
import { readFileSync, writeFileSync } from "node:fs";

const yol = new URL("../package-lock.json", import.meta.url);
const kilit = JSON.parse(readFileSync(yol, "utf8"));
let n = 0;
for (const p of Object.values(kilit.packages || {})) {
  if (typeof p.deprecated === "string" && p.deprecated !== "deprecated") { p.deprecated = "deprecated"; n++; }
}
writeFileSync(yol, JSON.stringify(kilit, null, 2) + "\n");
console.log(`${n} aciklama kisaltildi`);
