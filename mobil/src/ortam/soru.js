// "Bu kayit icin anlik izleme acilsin mi?" sorusu telefonda (eski KayitDugmesi.vue davranisi; kullanici
// karari 2026-10-05). Kayit BU TELEFONDAN baslatilinca (panel `Gb…` yolladi -> ORTAM.komutGitti) bir kez
// sorulur; soru kaydi BEKLETMEZ. Mantik cekirdek/bildirim.js izlemeSorusuKur'da (ne zaman sorulmaz, evet /
// hayir, kayit bitince kapanma); burada yalniz NE GOSTERILECEGI:
//
//   const s = soruKur({ izlemeSorusu, ciz });
//   s.komutGitti("Gb1000");     // Gb ile baslayan komut: soru akisi baslar. Baskasi: hicbir sey.
//   ciz(g) — g: null (kutu yok) | { hal, soru: true, mesgul, evet(), hayir() } | { hal, soru: false }
//
// Sonuc metni ("izleniyor" / "acilamadi") SONUC_MS sonra kendiliginden kalkar. Hicbir hata disari cikmaz.

export const SONUC_MS = 6000;
const GB = /^Gb/;

export function soruKur({ izlemeSorusu, ciz, zamanla = (fn, ms) => setTimeout(fn, ms), zamaniBirak = (z) => clearTimeout(z) }) {
  if (!izlemeSorusu || typeof izlemeSorusu.dinle !== "function" || typeof ciz !== "function") throw new TypeError("izlemeSorusu ve ciz gerekli");
  let silZ = null;

  const cizGuvenli = (g) => { try { ciz(g); } catch { /* cizim hatasi kaydi / akisi etkilemez */ } };
  const evet = () => { try { Promise.resolve(izlemeSorusu.evet()).catch(() => {}); } catch { /* yok say */ } };
  const hayir = () => { try { izlemeSorusu.hayir(); } catch { /* yok say */ } };

  function goster(hal) {
    if (silZ !== null) { zamaniBirak(silZ); silZ = null; }
    if (hal === "soruluyor" || hal === "aciliyor") {
      cizGuvenli({ hal, soru: true, mesgul: hal === "aciliyor", evet, hayir });
    } else if (hal === "acildi" || hal === "acilamadi") {
      cizGuvenli({ hal, soru: false });
      silZ = zamanla(() => { silZ = null; cizGuvenli(null); }, SONUC_MS);
    } else {
      cizGuvenli(null);
    }
  }

  const birak = izlemeSorusu.dinle(goster);

  function komutGitti(metin) {
    if (typeof metin !== "string" || !GB.test(metin)) return;
    try { Promise.resolve(izlemeSorusu.kayitBasladi()).catch(() => {}); } catch { /* soru sorulmaz */ }
  }

  return {
    komutGitti,
    birak() { try { birak(); } catch { /* yok say */ } if (silZ !== null) zamaniBirak(silZ); cizGuvenli(null); },
  };
}
