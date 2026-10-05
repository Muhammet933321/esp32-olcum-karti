// Kayit verisinin ana is parcacigindaki istemcisi (A24): isi arka plan iscisine (src/isci/kayit_isci.js)
// yollar, yaniti soze cevirir. Isci kurulamiyorsa (eski WebView, test) AYNI islemci ana is
// parcaciginda kosar — ekranlar farki bilmez.
//
//   const k = kayitIstemciKur({ isciKur, yedekKur });
//   await k.cagir("yukle", { url: depoAdresi(kartKimligi), akisKimlik });
//   await k.cagir("liste", { kart, arama, tur });
//   k.kapat();
//
// Hata: KayitIstemciHatasi(tur) — tur islemcinin TUR adi (bicim, okunamadi, ic-hata). Isci cokerse
// (onerror) bekleyen butun cagrilar "ic-hata" ile reddedilir ve SONRAKI cagri yedege gecer.

export const DEPO_YOLU = "/_depo/";
const KIMLIK = /^[0-9a-f]{16}$/;

export class KayitIstemciHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KayitIstemciHatasi";
    this.tur = tur;
  }
}

// Kart kimligi -> ham dosyanin YEREL adresi (DepoYolu.kt ile ayni bicim). Gecersiz kimlik: null.
export function depoAdresi(kimlik) {
  return typeof kimlik === "string" && KIMLIK.test(kimlik) ? `${DEPO_YOLU}${kimlik}/kayitlar.kyt` : null;
}

export function kayitIstemciKur({ isciKur = null, yedekKur }) {
  if (typeof yedekKur !== "function") throw new TypeError("yedekKur gerekli");
  let isci = null;
  let isciDenendi = false;
  let yedek = null;
  let no = 0;
  let kusak = 0;                        // islemci (isci / yedek) her degistiginde artar: YUKLU VERI GITTI demektir
  const bekleyen = new Map();

  function isciBirak() {
    if (isci) { try { isci.terminate(); } catch { /* zaten bitmis */ } kusak += 1; }
    isci = null;
    for (const [, b] of bekleyen) b.reddet(new KayitIstemciHatasi("ic-hata"));
    bekleyen.clear();
  }

  function isciAl() {
    if (isci || isciDenendi) return isci;
    isciDenendi = true;
    if (typeof isciKur !== "function") return null;
    try {
      const w = isciKur();
      w.onmessage = (e) => {
        const m = e.data || {};
        const b = bekleyen.get(m.no);
        if (!b) return;
        bekleyen.delete(m.no);
        if (m.tamam === true) b.coz(m.sonuc);
        else b.reddet(new KayitIstemciHatasi(typeof m.tur === "string" ? m.tur : "ic-hata"));
      };
      w.onerror = () => { isciBirak(); };        // isci yuklenemedi / coktu: yedege gecilir
      isci = w;
    } catch {
      isci = null;
    }
    return isci;
  }

  async function yedekCagir(is, arguman) {
    if (!yedek) yedek = Promise.resolve().then(yedekKur);
    let islemci;
    try { islemci = await yedek; } catch { yedek = null; throw new KayitIstemciHatasi("ic-hata"); }
    try {
      return await islemci.isle(is, arguman);
    } catch (h) {
      throw new KayitIstemciHatasi(h && typeof h.tur === "string" ? h.tur : "ic-hata");
    }
  }

  function cagir(is, arguman = {}) {
    const w = isciAl();
    if (!w) return yedekCagir(is, arguman);
    return new Promise((coz, reddet) => {
      const n = ++no;
      bekleyen.set(n, { coz, reddet });
      try {
        w.postMessage({ no: n, is, ...arguman });
      } catch {
        bekleyen.delete(n);
        reddet(new KayitIstemciHatasi("ic-hata"));
      }
    });
  }

  // kusak(): cagiran, yukledigi verinin hala ISLEMCIDE durup durmadigini bununla anlar (isci cokunce
  // yedek islemci BOS baslar).
  return { cagir, kapat: isciBirak, isciVar: () => isci !== null, kusak: () => kusak };
}
