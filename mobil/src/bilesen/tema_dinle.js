// Sistem temasi degisince haber verir (tuval renkleri yeniden okunsun diye). Tarayici destegi yoksa
// sessizce hicbir sey yapmaz. Donen islev dinlemeyi birakir.
const SORGU = "(prefers-color-scheme: dark)";

export function temaDinle(fn, sorgula = typeof matchMedia === "function" ? matchMedia : null) {
  if (typeof sorgula !== "function") return () => {};
  let liste = null;
  try { liste = sorgula(SORGU); } catch { liste = null; }
  if (!liste || typeof liste.addEventListener !== "function") return () => {};
  const isleyici = () => { fn(); };
  liste.addEventListener("change", isleyici);
  return () => { liste.removeEventListener("change", isleyici); };
}
