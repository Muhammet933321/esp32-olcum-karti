// Kullanici tercihleri (A42, A43): dil ve tema. Telefonda saklanir (yerel depo); sir degildir.
//   dil  : "tr" | "en"                      (varsayilan "tr")
//   tema : "sistem" | "koyu" | "acik"       (varsayilan "sistem": prefers-color-scheme)
// Saf islevler: depo ve belge koku disaridan verilir (Node'da sinanir).

export const DILLER = Object.freeze(["tr", "en"]);
export const TEMALAR = Object.freeze(["sistem", "koyu", "acik"]);
export const VARSAYILAN = Object.freeze({ dil: "tr", tema: "sistem" });
export const DEPO_ANAHTARI = "tercih";
export const TEMA_OLAYI = "tema-degisti";

export function tercihOku(depo) {
  let ham = null;
  try { ham = JSON.parse(depo.getItem(DEPO_ANAHTARI)); } catch { ham = null; }
  const t = ham !== null && typeof ham === "object" ? ham : {};
  return {
    dil: DILLER.includes(t.dil) ? t.dil : VARSAYILAN.dil,
    tema: TEMALAR.includes(t.tema) ? t.tema : VARSAYILAN.tema,
  };
}

// Gecersiz deger YAZILMAZ (onceki deger kalir). Donus: saklanan tercih.
export function tercihYaz(depo, parca) {
  const simdiki = tercihOku(depo);
  const yeni = {
    dil: parca && DILLER.includes(parca.dil) ? parca.dil : simdiki.dil,
    tema: parca && TEMALAR.includes(parca.tema) ? parca.tema : simdiki.tema,
  };
  try { depo.setItem(DEPO_ANAHTARI, JSON.stringify(yeni)); } catch { /* depo dolu / kapali: tercih bu oturumda gecerli */ }
  return yeni;
}

// tema.css: `data-tema` yoksa sistem temasi; "koyu" / "acik" sistemi ezer. `lang` de ayarlanir.
// Tuval (grafik) renkleri yeniden okunsun diye belgeye TEMA_OLAYI gonderilir.
export function tercihUygula(belge, tercih) {
  const kok = belge.documentElement;
  if (tercih.tema === "sistem") kok.removeAttribute("data-tema");
  else kok.setAttribute("data-tema", tercih.tema);
  kok.setAttribute("lang", tercih.dil);
  if (typeof belge.dispatchEvent === "function" && typeof Event === "function") belge.dispatchEvent(new Event(TEMA_OLAYI));
}
