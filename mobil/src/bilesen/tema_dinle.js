// Sistem temasi degisince haber verir (tuval renkleri yeniden okunsun diye). Tarayici destegi yoksa
// sessizce hicbir sey yapmaz. Donen islev dinlemeyi birakir.
const SORGU = "(prefers-color-scheme: dark)";

// Ayarlar'dan tema secilince de (belgeye gonderilen "tema-degisti" olayi) haber verir.
export function temaDinle(fn, sorgula = typeof matchMedia === "function" ? matchMedia : null, belge = typeof document === "object" ? document : null) {
  const birakanlar = [];
  if (belge && typeof belge.addEventListener === "function") {
    const olay = () => { fn(); };
    belge.addEventListener("tema-degisti", olay);
    birakanlar.push(() => belge.removeEventListener("tema-degisti", olay));
  }
  const hepsiniBirak = () => { for (const b of birakanlar) b(); };
  if (typeof sorgula !== "function") return hepsiniBirak;
  let liste = null;
  try { liste = sorgula(SORGU); } catch { liste = null; }
  if (!liste || typeof liste.addEventListener !== "function") return hepsiniBirak;
  const isleyici = () => { fn(); };
  liste.addEventListener("change", isleyici);
  birakanlar.push(() => { liste.removeEventListener("change", isleyici); });
  return hepsiniBirak;
}
