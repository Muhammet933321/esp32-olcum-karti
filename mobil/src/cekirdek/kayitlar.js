// Kayitlar ve kayit gorunumu ekranlarinin veri kaynagi (A24, A25, A41): telefondaki kopya (her zaman)
// + kart erisilebilirse kartin oturum dizini ("nerede: kart / telefon / ikisi").
//
//   const k = kayitlarKur({ istemci, kartAl, depoAl, sonKimlik });
//   await k.liste({ arama, tur })   -> { satirlar, kimlik, kartVar, bayt }
//   await k.oturum(no)              -> kayit gorunumunun verisi | null
//   await k.okuma(no, tA, tB)       -> aralik istatistigi | null
//
// Kurallar:
//   * Kart BAGLI degilken de calisir (disarida): hangi kartin kopyasi oldugu son baglanilan karttan
//     (`sonKimlik`: kesif onbellegi) bilinir. Hic kart bilinmiyorsa bos liste.
//   * Dosya yalniz DEGISTIYSE yeniden cozulur (boy + akis kimligi + kart kimligi izlenir).
//   * Kartin dizini okunamazsa (ag hatasi, eslesmemis) liste telefondan kurulur — hata DEGIL.
//   * Hatalar KayitlarHatasi(tur): ekran tur adini gosterir; dosya yolu / kart mesaji cikmaz.
import { depoAdresi } from "./kayit_istemci.js";

export class KayitlarHatasi extends Error {
  constructor(tur) {
    super(tur);
    this.name = "KayitlarHatasi";
    this.tur = tur;
  }
}

export function kayitlarKur({ istemci, kartAl, depoAl, sonKimlik = () => null }) {
  if (!istemci || typeof kartAl !== "function" || typeof depoAl !== "function") throw new TypeError("istemci, kartAl, depoAl gerekli");
  let yuklenen = null;                  // { kimlik, akisKimlik, boy }
  let suren = null;

  const hata = (e) => new KayitlarHatasi(e && typeof e.tur === "string" ? e.tur : "ic-hata");

  async function kartDurumu() {
    try {
      const kart = await kartAl();
      const d = kart.durum();
      return { kart, bagli: Boolean(d) && d.durum === "bagli", kimlik: d && typeof d.kimlik === "string" ? d.kimlik : null };
    } catch {
      return { kart: null, bagli: false, kimlik: null };
    }
  }

  // Kopya gerekirse (yeniden) cozulur. Donus: { kimlik, bayt } | null (hic kart bilinmiyor).
  async function hazirla(kimlikBilinen) {
    let kimlik = kimlikBilinen;
    if (kimlik === null) { try { kimlik = sonKimlik(); } catch { kimlik = null; } }
    const url = depoAdresi(kimlik);
    if (url === null) { yuklenen = null; return null; }
    let boy = 0, akisKimlik = null;
    try {
      const depo = await depoAl(kimlik);
      boy = await depo.veriBoyu();
      const d = await depo.durumOku();
      akisKimlik = d && Number.isInteger(d.kimlik) ? d.kimlik : null;
    } catch (e) {
      // Durum dosyasi bozuksa kopya yine de gosterilir (salt okuma); boy okunamadiysa hata.
      if (!(e && e.tur === "bozuk")) throw hata(e);
    }
    if (!yuklenen || yuklenen.kimlik !== kimlik || yuklenen.boy !== boy || yuklenen.akisKimlik !== akisKimlik) {
      try {
        await istemci.cagir("yukle", { url, akisKimlik });
      } catch (e) {
        yuklenen = null;
        throw hata(e);
      }
      yuklenen = { kimlik, akisKimlik, boy };
    }
    return { kimlik, bayt: boy };
  }

  async function listeKos({ arama = "", tur = "hepsi" } = {}) {
    const k = await kartDurumu();
    const h = await hazirla(k.kimlik);
    let dizin = null;
    if (k.bagli) {
      try { dizin = await (await k.kart.istek("GET", "/kayit/liste")).json(); } catch { dizin = null; }
    }
    if (h === null && dizin === null) return { satirlar: [], kimlik: null, kartVar: false, bayt: 0 };
    let satirlar;
    try { satirlar = await istemci.cagir("liste", { kart: dizin, arama, tur }); } catch (e) { throw hata(e); }
    return { satirlar, kimlik: h ? h.kimlik : k.kimlik, kartVar: dizin !== null, bayt: h ? h.bayt : 0 };
  }

  // Art arda cagrilar (arama kutusuna yazarken) SIRAYLA kosar: dosya iki kez ayni anda cozulmez.
  function sirayla(is) {
    const onceki = suren || Promise.resolve();
    const yeni = onceki.catch(() => {}).then(is);
    suren = yeni;
    yeni.finally(() => { if (suren === yeni) suren = null; }).catch(() => {});
    return yeni;
  }

  async function oturumKos(no) {
    const k = await kartDurumu();
    if ((await hazirla(k.kimlik)) === null) return null;
    try { return await istemci.cagir("oturum", { oturum: no }); } catch (e) { throw hata(e); }
  }

  return {
    liste: (secenek) => sirayla(() => listeKos(secenek)),
    oturum: (no) => sirayla(() => oturumKos(no)),
    async okuma(no, tA, tB) {
      try { return await istemci.cagir("okuma", { oturum: no, tA, tB }); } catch (e) { throw hata(e); }
    },
    bosalt() { yuklenen = null; },
  };
}
