// Kayit cozme Web Worker'inin kurucusu (A24). src/ agacinda Worker kurulan TEK yer; betik paketin
// icindeki kendi dosyamizdir (src/isci/kayit_isci.js) — baska adresten betik yuklenmez (CSP + WebKapi).
export function kayitIsciKur() {
  return new Worker(new URL("../isci/kayit_isci.js", import.meta.url), { type: "module" });
}
