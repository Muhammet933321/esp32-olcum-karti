// Panelin `telefon` TASIYICISI (5P K6): panelin taşıyıcı sözlesmesi (arayuz3/app.js "TASIYICI KATMANI"):
//   ad, yetenek, destekli(), ac(uyg), kapat(uyg), gonder(uyg, metin)
// Akis: Android'in imzali akisi (cekirdek/canli.js, Kotlin `Akis`) — her ham satir `uyg.satirIsle`'ye.
// Komut: imzali `POST /komut` (X-Olcum: 1, Content-Type: text/plain; imza basliklari kart.istek'te),
// yanit govdesinin satirlari da `uyg.satirIsle`'ye. `p0` imzasiz kendi yolundan (acilDurdur).
//
// Durumlar panelin kutularina (TasiyiciAkis ile ayni tavir, app.js):
//   eslesmemis / kimlik uymuyor / kasa bozuk -> ac() REDDEDER (mesaj: Bu telefon -> Kart); dongu YOK
//   kart bulunamadi -> ac() basarir, uyg.hata "aranıyor"; arka plan 15 s'de bir arar, akis acilinca silinir
//   akis "dolu" (baska izleyiciler / PC koprusu) -> uyg.uyari; akis acilinca silinir
//   akis koptu -> uyg.hata "Akış koptu — yeniden bağlanılıyor" (+ sebep); akis acilinca silinir
//   arka plana gecis -> HICBIR SEY yazilmaz (akis kapanir, donuste yeniden acilir; satirlar yeniden gelir)
// Ortamin yazdigi metin yalniz ORTAMIN yazdigi metinse silinir (panelin kendi hatasina dokunulmaz).

import { dilSec, metin } from "./metin.js";

export const YETENEK = Object.freeze({
  ad: "telefon", komut: "hepsi", skop: "ikili", skop_azami: 4000, gecmis_s: 86400, cok_istemci: false, surucu: false,
});

const REDDEDILEN = Object.freeze({
  eslesmemis: "or.eslesmemis",
  "kimlik-uymuyor": "or.kimlik_uymuyor",
  "kasa-bozuk": "or.kasa",
});

// Akis hata sebebi (canli.js TUR adi) -> metin anahtari. Listede olmayan sebep genel "koptu" metnidir.
const SEBEP_METNI = Object.freeze({
  "wifi-yok": "or.wifi_yok",
  "cihaz-silinmis": "or.cihaz_silinmis",
  eslesmemis: "or.eslesmemis",
  "kimlik-uymuyor": "or.kimlik_uymuyor",
});

export class TasiyiciHatasi extends Error {
  constructor(tur, mesaj) {
    super(mesaj);
    this.name = "TasiyiciHatasi";
    this.tur = tur;
  }
}

const kodla = (s) => new TextEncoder().encode(s);

export function tasiyiciKur({ arka, kartAl, p0 }) {
  if (!arka || typeof arka.baglan !== "function" || typeof kartAl !== "function" || typeof p0 !== "function") {
    throw new TypeError("arka, kartAl ve p0 gerekli");
  }
  let bagli = null;            // { uyg, birak: [], hata, uyari } — panelin bagli oldugu uygulama nesnesi
  let bekleyen = null;         // eslesmemis diye reddedilen uyg: eslesme gelince panelden yeniden baglanilir

  const dilAl = (uyg) => dilSec(uyg && uyg.dil);

  function hataYaz(b, s) {
    b.hata = s;
    b.uyg.hata = s;
  }

  function hataSil(b) {
    if (b.hata !== null && b.uyg.hata === b.hata) b.uyg.hata = "";
    b.hata = null;
  }

  function uyariYaz(b, s) {
    b.uyari = s;
    b.uyg.uyari = s;
  }

  function uyariSil(b) {
    if (b.uyari !== null && b.uyg.uyari === b.uyari) b.uyg.uyari = "";
    b.uyari = null;
  }

  // Arka planin durum degisimi -> panelin kutulari.
  function durumDegisti(d) {
    if (bekleyen && d.baglanti && d.baglanti.durum === "bagli") {
      const u = bekleyen;
      bekleyen = null;
      // Bu telefon -> Kart'ta eslesildi: panel kendiliginden yeniden baglanir (kullanici "Karta baglan"a basmaz).
      if (!u.bagli && typeof u.baglan === "function") { try { Promise.resolve(u.baglan()).catch(() => {}); } catch { /* yok say */ } }
    }
    const b = bagli;
    if (!b) return;
    const dil = dilAl(b.uyg);
    const hal = d.akis.hal;
    if (hal === "acik") {
      hataSil(b);
      uyariSil(b);
    } else if (hal === "dolu") {
      hataSil(b);
      uyariYaz(b, metin("or.dolu", dil));
    } else if (hal === "hata") {
      const anahtar = SEBEP_METNI[d.akis.sebep];
      const ek = anahtar ? ` — ${metin(anahtar, dil)}` : "";
      hataYaz(b, metin("or.koptu", dil) + ek);
    } else if (hal === "kapali" && d.baglanti && d.baglanti.durum === "bulunamadi" && d.gorunur) {
      hataYaz(b, metin("or.bulunamadi", dil));
    }
  }

  const durumBirak = arka.dinle(durumDegisti);

  async function ac(uyg) {
    if (bagli) await kapat(bagli.uyg);
    const b = await arka.baglan();
    const red = b ? REDDEDILEN[b.durum] : null;
    if (red) {
      bekleyen = uyg;
      throw new TasiyiciHatasi(b.durum, metin(red, dilAl(uyg)));
    }
    bekleyen = null;
    const yeni = { uyg, birak: [], hata: null, uyari: null };
    bagli = yeni;
    yeni.birak.push(arka.hamDinle((satir) => {
      if (bagli !== yeni) return;
      const s = String(satir).trim();
      if (s) uyg.satirIsle(s);
    }));
    if (!b || b.durum !== "bagli") hataYaz(yeni, metin("or.bulunamadi", dilAl(uyg)));
    arka.akisIste(true);
  }

  async function kapat(uyg) {
    const b = bagli;
    if (!b || (uyg && b.uyg !== uyg)) return;
    bagli = null;
    for (const fn of b.birak.splice(0)) { try { fn(); } catch { /* yok say */ } }
    hataSil(b);
    uyariSil(b);
    arka.akisIste(false);
  }

  // Panelin TasiyiciAkis.gonder'i gibi ASLA atmaz: sonuc satirlari ya da uyg.hata.
  async function gonder(uyg, metinGelen) {
    const komut = String(metinGelen ?? "");
    const dil = dilAl(uyg);
    if (komut === "p0") {
      let tamam = false;
      try { tamam = (await p0()) === true; } catch { tamam = false; }
      if (!tamam) uyg.hata = metin("or.p0_ulasmadi", dil);
      return;
    }
    let y;
    try {
      const kart = await kartAl();
      if (kart.durum().durum === "bagli-degil") await arka.baglan();
      y = await kart.istek("POST", "/komut", [], kodla(komut), { hamYanit: true });
    } catch (e) {
      komutHatasi(uyg, e, dil);
      return;
    }
    let govde = "";
    try { govde = await y.text(); } catch { govde = ""; }
    if (!y.ok) {
      const neden = govde.trim().slice(0, 200);
      uyg.hata = `${metin("or.komut_gitmedi", dil)} (${y.status})${neden ? ": " + neden : ""}`;
      return;
    }
    for (const sat of govde.split("\n")) {
      const s = sat.trim();
      if (s) uyg.satirIsle(s);
    }
  }

  function komutHatasi(uyg, e, dil) {
    const tur = e && typeof e.tur === "string" ? e.tur : "ic-hata";
    if (tur === "bagli-degil" || tur === "ag") {
      if (typeof uyg.olayEkle === "function") { try { uyg.olayEkle(`! komut: ${tur}${e.ag ? " " + e.ag : ""}`, "unlem"); } catch { /* yok say */ } }
      let s = "";
      try { s = typeof uyg.metin === "function" ? uyg.metin("kb.komut_kart_yok") : ""; } catch { s = ""; }
      uyg.hata = s && s !== "kb.komut_kart_yok" ? s : metin("or.kart_yok", dil);
      return;
    }
    const anahtar = { eslesmemis: "or.eslesmemis", "cihaz-silinmis": "or.cihaz_silinmis", "kimlik-uymuyor": "or.kimlik_uymuyor", kasa: "or.kasa" }[tur];
    uyg.hata = anahtar ? metin(anahtar, dil) : `${metin("or.komut_gitmedi", dil)} — ${tur}`;
  }

  return {
    ad: "telefon",
    yetenek: YETENEK,
    destekli: () => true,
    ac, kapat, gonder,
    birak() { try { durumBirak(); } catch { /* yok say */ } },
  };
}
