// Kayit esitleme dongusu (tasarim A20–A23): kartin kayitlarini telefondaki kopyaya ceker.
// Isin kendisi ortak/src/esitle.js `Esitleyici`dedir (tek kopya kural, Python'la bayt bayt); burada
// yalniz NE ZAMAN kosacagi, kartla nasil konusacagi ve sonucun ekrana nasil ozetlenecegi var.
//
//   const e = esitlemeKur({ kartAl, depoAl, onayAcik: () => false });
//   await e.simdi();            // elle "Simdi esitle" — ASLA atmaz; suren esitleme varsa ONA baglanir
//   e.tik({ gorunur, bagli });  // saniyede bir (kabuk): 60 s'de bir kendiliginden (A22)
//   e.baglandi(); e.kayitBitti();   // olay tetikleyicileri (A22) — hemen bir tur
//   e.durum()  -> { hal, sonMs, yeni, sonSira, bosluk, bekleyen, hata, sifirlaOner, onayli }
//                 hal: "bos" | "esitleniyor" | "tamam" | "hata"
//   e.dinle(fn) -> birak()
//   await e.sifirla();          // "kopyayi sifirla" (A23): bu kartin telefondaki kopyasi silinir
//
// Kurallar:
//   * Varsayilan ONAYSIZ (A21): `onayAcik()` true DEGILSE karta `Go` HIC gitmez. Aciksa onay yalniz
//     depo.veriEkle + durumYaz bittikten SONRA (Esitleyici'nin sirasi) ve imzali /komut ile gider.
//   * Butun istekler imzali ve `kart.istek` uzerinden (tek sayac, A15); istek BASLARI arasi >= 100 ms.
//   * Ayni anda TEK esitleme: suren soze baglanilir; depo kilidi ikinci savunma hattidir.
//   * Arka planda esitleme YOK (A22): tik yalniz `gorunur` iken tetikler.
//   * Hata ekrana TUR olarak cikar; kartin / dosyanin mesaji cikmaz. Kopyanin kartla bagdasmadigi
//     hallerde (akis kimligi degisti, dosya kisa, durum bozuk) `sifirlaOner` true olur.
import { Esitleyici, EsitlemeHatasi } from "@ortak/esitle.js";
import { CalismaHatasi, HttpHatasi } from "@ortak/imza.js";
import { KayitHatasi } from "@ortak/kayit.js";

export const ARALIK_MS = 60000;
export const ISTEK_ARA_MS = 100;
export const PARCA_BAYT = 8192;

const BOS = Object.freeze({
  hal: "bos", sonMs: null, yeni: 0, sonSira: null, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false,
});

// Esitleyici'nin bosluk listesi ([[a, b], ...]: a..b-1 siralari kartta YOK) -> kullaniciya soylenecek
// bosluk sayisi. 1'den baslayan bosluk SAYILMAZ: kopya bosken kartin akisinin 1'den baslamamasi
// (eski kayitlar onaylanip silinmis) olagan haldir, "kopyada bosluk kaldi" uyarisi yaniltirdi. Saf.
export function bosluklar(liste) {
  if (!Array.isArray(liste)) return 0;
  return liste.filter((b) => Array.isArray(b) && b[0] > 1).length;
}

// Hata -> { tur, sifirlaOner }. Saf.
export function hataTuru(e) {
  if (e instanceof EsitlemeHatasi) return { tur: "kopya-uyusmuyor", sifirlaOner: true };
  if (e instanceof KayitHatasi) return { tur: "yanit-bozuk", sifirlaOner: false };
  if (e instanceof CalismaHatasi) return { tur: "mesgul", sifirlaOner: false };
  if (e && e.name === "DepoHatasi") return { tur: e.tur === "bozuk" ? "depo-bozuk" : "depo", sifirlaOner: e.tur === "bozuk" };
  if (e && e.name === "KartHatasi" && typeof e.tur === "string") return { tur: e.tur, sifirlaOner: false };
  if (e instanceof HttpHatasi) return { tur: "http", sifirlaOner: false };
  return { tur: "ic-hata", sifirlaOner: false };
}

export function esitlemeKur({
  kartAl, depoAl, onayAcik = () => false, simdiMs = Date.now,
  bekle = (ms) => new Promise((c) => setTimeout(c, ms)), aralikMs = ARALIK_MS, istekAraMs = ISTEK_ARA_MS,
}) {
  if (typeof kartAl !== "function" || typeof depoAl !== "function") throw new TypeError("kartAl ve depoAl gerekli");
  let hal = { ...BOS };
  let suren = null;
  let sonDeneme = null;                 // son esitleme DENEMESININ baslangici (basarisiz olsa da)
  let sonIstek = null;
  let tekrar = false;                   // suren tur sirasinda olay geldi: bitince BIR tur daha
  const dinleyenler = new Set();

  function yay(parca) {
    hal = { ...hal, ...parca };
    for (const fn of [...dinleyenler]) { try { fn(hal); } catch { /* arayuz hatasi esitlemeyi etkilemez */ } }
  }

  // Istek BASLARI arasi >= istekAraMs (canli akisi ve olcum dongusunu bogmamak icin; 4C olcumu).
  async function aralikli(is) {
    if (sonIstek !== null) {
      const kalan = istekAraMs - (simdiMs() - sonIstek);
      if (kalan > 0) await bekle(kalan);
    }
    sonIstek = simdiMs();
    return is();
  }

  // kart.istek HTTP hatasini KartHatasi("http", { durum }) yapar; Esitleyici'nin kurallari (ornegin
  // /kal/liste 404 / 503 sessiz) HttpHatasi bekler: geri cevrilir.
  async function kartIstek(kart, yontem, yol, argumanlar, govde) {
    try {
      return await aralikli(() => kart.istek(yontem, yol, argumanlar, govde));
    } catch (e) {
      if (e && e.name === "KartHatasi" && e.tur === "http" && Number.isInteger(e.durum)) throw new HttpHatasi(e.durum, null, yol);
      throw e;
    }
  }

  async function kos() {
    sonDeneme = simdiMs();
    const onayli = onayAcik() === true;
    yay({ hal: "esitleniyor", hata: null, sifirlaOner: false, onayli });
    try {
      const kart = await kartAl();
      const d = kart.durum();
      if (!d || d.durum !== "bagli" || typeof d.kimlik !== "string") throw Object.assign(new Error("bagli-degil"), { name: "KartHatasi", tur: "bagli-degil" });
      const depo = await depoAl(d.kimlik);
      const e = new Esitleyici({
        tabanUrl: "http://kart", depo, bayt: PARCA_BAYT,
        istek: (_taban, yol, argumanlar) => kartIstek(kart, "GET", yol, argumanlar, new Uint8Array(0)),
        onay: onayli
          ? async (sira) => { const y = await kartIstek(kart, "POST", "/komut", [], new TextEncoder().encode(`Go${sira}`)); await y.arrayBuffer(); }
          : null,
      });
      const s = await e.esitle();
      yay({
        hal: "tamam", sonMs: simdiMs(), yeni: s.yeni_kayit, sonSira: s.son_sira,
        bosluk: bosluklar(s.bosluk), bekleyen: Number.isInteger(s.bekleyen) ? s.bekleyen : 0,
      });
    } catch (h) {
      yay({ hal: "hata", ...(({ tur, sifirlaOner }) => ({ hata: tur, sifirlaOner }))(hataTuru(h)) });
    }
    return hal;
  }

  function simdi() {
    if (!suren) {
      suren = kos().finally(() => {
        suren = null;
        if (tekrar) { tekrar = false; simdi(); }
      });
    }
    return suren;
  }

  // Olay (baglandi / kayit bitti): suren tur olaydan ONCE baslamis olabilir ve kaydin sonunu
  // gormemis olabilir — o bitince bir tur daha kosar.
  function olay() {
    if (suren) tekrar = true;
    else simdi();
  }

  // Saniyede bir: gorunur + bagli ise ve son denemeden aralikMs gectiyse (ya da hic denenmediyse) bir tur.
  function tik({ gorunur, bagli }) {
    if (!gorunur || !bagli || suren) return false;
    if (sonDeneme !== null && simdiMs() - sonDeneme < aralikMs) return false;
    simdi();
    return true;
  }

  async function sifirla() {
    if (suren) { try { await suren; } catch { /* kos atmaz */ } }
    const kart = await kartAl();
    const d = kart.durum();
    const kimlik = d && typeof d.kimlik === "string" ? d.kimlik : null;
    if (kimlik === null) throw Object.assign(new Error("bagli-degil"), { name: "KartHatasi", tur: "bagli-degil" });
    await (await depoAl(kimlik)).sifirla();
    sonDeneme = null;
    yay({ ...BOS });
  }

  return {
    simdi, tik, sifirla,
    baglandi: olay,
    kayitBitti: olay,
    durum: () => hal,
    dinle(fn) { dinleyenler.add(fn); return () => { dinleyenler.delete(fn); }; },
  };
}
