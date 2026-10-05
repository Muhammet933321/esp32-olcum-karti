// Durum ekraninin (A39) durum -> gorunum eslemesi. Saf; DOM'suz sinanir (test/ekran.test.js).
// Girdi: kabuk durumu (ekran/kabuk_durum.js): baglanti { durum, adres, kimlik } | null,
// akis { hazir, hal, son (D satiri), kayit (G satiri) }.
// Cikti: sozluk ANAHTARLARI ve sayi yazilari — metin burada kurulmaz.

// kayit_yonet.h KDR_* (kartin G satirinin `durum` alani).
export const KDR = Object.freeze({ TARIYOR: 0, BOS: 1, KAYIT: 2, DOLU: 3, BEKLIYOR: 4, HATA: 5 });

export const YOK = "—";
// Kayit hizi nokta artisindan en az bu kadar gozlemden sonra OLCULUR (oncesi "bilinmiyor").
export const OLCUM_EN_AZ_MS = 10000;

// G satiri alani: ayristiricinin verdigi ad ya da firmware'deki uzun adi (ikisi de kabul).
export function gAlan(g, ...adlar) {
  if (!g || typeof g !== "object") return null;
  for (const ad of adlar) {
    const v = g[ad];
    if (typeof v === "number" && Number.isFinite(v)) return v;
  }
  return null;
}

// ── sayi yazilari ────────────────────────────────────────────────────────
export function sayiYaz(x, hane) {
  return typeof x === "number" && Number.isFinite(x) ? x.toFixed(hane) : YOK;
}
export const voltYaz = (v) => sayiYaz(v, Math.abs(v) >= 100 ? 2 : 3);      // 12.482
export const amperYaz = (a) => sayiYaz(a, 3);                               // 1.936
export const wattYaz = (w) => sayiYaz(w, Math.abs(w) >= 1000 ? 1 : 2);     // 24.17

// D satiri -> uc yazi. adcHata bit0: gerilim okunamadi, bit1: akim okunamadi (o kanal ve guc YOK).
export function olcumYazilari(son) {
  if (!son || typeof son !== "object") return { v: YOK, a: YOK, w: YOK };
  const hata = Number.isInteger(son.adcHata) ? son.adcHata : 0;
  const vYok = (hata & 1) !== 0;
  const aYok = (hata & 2) !== 0;
  return {
    v: vYok ? YOK : voltYaz(son.v),
    a: aYok ? YOK : amperYaz(son.a),
    w: vYok || aYok ? YOK : wattYaz(son.w),
  };
}

// Ekranda gosterilecek olcum: akis AKMIYORSA (hata / baglaniyor / dolu / kapali) eski olcum GOSTERILMEZ.
export function gorunenOlcum(hal, son) {
  return hal === "acik" && son && typeof son === "object" ? son : null;
}

// ── etkin oturumun turu (A40: pil testi surerken salt okuma) ─────────────
// G / D satiri oturum turunu soylemez; imzali GET /kayit/liste'nin `oturumlar` dizisinden okunur.
export const OTURUM_TURU = Object.freeze({ OLCUM: 1, PIL: 2, SKOP: 3 });

// /kayit/liste govdesi + oturum no -> tur | null (bilinmiyor: liste bozuk, oturum yok, tur sayi degil).
export function oturumTuruBul(liste, oturum) {
  if (!liste || typeof liste !== "object" || !Array.isArray(liste.oturumlar) || !Number.isInteger(oturum)) return null;
  const kayit = liste.oturumlar.find((o) => o && typeof o === "object" && o.id === oturum);
  return kayit && Number.isInteger(kayit.tur) ? kayit.tur : null;
}

// tur -> { saltOkuma, rozet, aciklama }. Yalniz PIL TESTI kayit komutlarini kapatir (kart o sirada
// Gb / Gd'yi reddeder; test karttan ya da panelden yonetilir). Tur BILINMIYORSA (null: okunamadi)
// dugmeler ACIK kalir — kart zaten reddeder. ACIL DURDUR bu kilitten ETKILENMEZ.
export function oturumKilidi(tur) {
  if (tur === OTURUM_TURU.PIL) return { saltOkuma: true, rozet: "m.dr.pil_testi", aciklama: "m.dr.pil_salt_okuma" };
  if (tur === OTURUM_TURU.SKOP) return { saltOkuma: false, rozet: "m.dr.skop_gunlugu", aciklama: null };
  return { saltOkuma: false, rozet: null, aciklama: null };
}

// ── kayit esitlemesi (A20–A23) ───────────────────────────────────────────
// Hata turu -> metin anahtari. Listede olmayan tur genel metne duser (tur degeriyle).
const ESIT_HATA = Object.freeze({
  "bagli-degil": "m.es.kopya_hata_bagli_degil",
  ag: "m.es.kopya_hata_ag",
  mesgul: "m.es.hata_mesgul",
  "kopya-uyusmuyor": "m.es.hata_kopya",
  "depo-bozuk": "m.es.hata_kopya",
  depo: "m.es.hata_depo",
  "yanit-bozuk": "m.es.hata_yanit",
  "cihaz-silinmis": "m.es.hata_silinmis",
});

// kabuk.esitleme + baglanti -> { anahtar, degerler, sinif, suruyor, dugme, sifirlaOner, ek }
//   dugme: "Simdi esitle" basilabilir mi (kart BAGLI ve esitleme surmuyor)
//   ek: ikinci satir (uyari) anahtari | null
export function esitlemeGorunumu(e, baglanti, simdiMs = 0) {
  const bagli = Boolean(baglanti) && baglanti.durum === "bagli";
  const sonuc = (anahtar, sinif = "", ek = null) => ({
    anahtar, degerler: null, sinif, suruyor: false, dugme: bagli, sifirlaOner: false, ek: null, ...ek,
  });
  if (!e || e.hazir === false) return sonuc("m.es.yok", "", { dugme: false });
  if (e.hal === "esitleniyor") return sonuc("m.es.kopya_suruyor", "", { suruyor: true, dugme: false });
  if (e.hal === "hata") {
    const bilinen = Object.hasOwn(ESIT_HATA, e.hata) ? ESIT_HATA[e.hata] : null;
    return sonuc(bilinen || "m.es.hata_genel", "uyari", {
      degerler: bilinen ? null : { tur: typeof e.hata === "string" ? e.hata : "?" },
      sifirlaOner: e.sifirlaOner === true,
      ek: e.sifirlaOner === true ? "m.es.sifirla_oner" : null,
    });
  }
  if (e.hal === "tamam") {
    const dk = e.sonMs === null ? 0 : Math.max(0, Math.floor((simdiMs - e.sonMs) / 60000));
    // Kartta telefonun ALAMADIGI daha yeni kayit varsa kopya "guncel" DEGILDIR (ust satir yalan soylemesin).
    if (e.bekleyen > 0) return sonuc("m.es.kopya_geride", "uyari", { ek: "m.es.bekleyen" });
    const ek = e.bosluk > 0 ? "m.es.bosluk" : null;
    return sonuc(dk === 0 ? "m.es.tamam_simdi" : "m.es.kopya_tamam", "iyi", { degerler: dk === 0 ? null : { dk }, ek });
  }
  return sonuc(bagli ? "m.es.bekliyor" : "m.es.kart_yok");
}

const iki = (n) => String(n).padStart(2, "0");

// ms -> "01:24:10" (saat 24'u gecebilir)
export function sureYaz(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return YOK;
  const s = Math.floor(ms / 1000);
  return `${iki(Math.floor(s / 3600))}:${iki(Math.floor((s % 3600) / 60))}:${iki(s % 60)}`;
}

// Kayit araligi (ms) -> { yazi } ("5/s") | { anahtar, degerler } (yavas hizlar) | null
export function hizYaz(ms, yaklasik = false) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms <= 0) return null;
  if (ms <= 1000) {
    const adet = 1000 / ms;
    const yazi = Number.isInteger(adet) ? String(adet) : adet.toFixed(adet < 10 ? 1 : 0);
    return { yazi: `${yazi}/s`, yaklasik };
  }
  const s = ms / 1000;
  if (s < 60) return { anahtar: "cn.hiz_s", degerler: { s: Number.isInteger(s) ? s : s.toFixed(1) }, yaklasik };
  const dk = s / 60;
  return { anahtar: "cn.hiz_dk", degerler: { dk: Number.isInteger(dk) ? dk : dk.toFixed(1) }, yaklasik };
}

// Gecen sure -> { anahtar, degerler } ("2 sn once")
export function gecenYaz(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return null;
  const s = Math.floor(ms / 1000);
  if (s < 60) return { anahtar: "m.dr.once_sn", degerler: { n: s } };
  if (s < 3600) return { anahtar: "m.dr.once_dk", degerler: { n: Math.floor(s / 60) } };
  return { anahtar: "m.dr.once_sa", degerler: { n: Math.floor(s / 3600) } };
}

const yuzde = (binde) => (binde === null ? null : Math.max(0, Math.min(100, Math.round(binde / 10))));

// ── kayit izleme (saf indirgeyici) ───────────────────────────────────────
// G satiri hizi ve baslangic anini TASIMAZ. Hiz: bu telefonun gonderdigi `Gb<ms>` (bilinenHizMs) ya da
// nokta artisindan OLCULEN. Baslangic: kaydin basladigini GORDUYSEK o an; ilk G'de kayit zaten
// suruyorduysa bilinmez (sure tahmin edilmez).
export function kayitIzle(onceki, g, simdiMs, bilinenHizMs = null) {
  const durum = gAlan(g, "durum");
  if (durum === null) return onceki || null;
  if (durum !== KDR.KAYIT) return { durum, oturum: null, basMs: null, hizMs: null, olculen: false, ilk: null, son: null };
  const oturum = gAlan(g, "oturum");
  const gozlem = { t: simdiMs, n: gAlan(g, "nokta", "nokta_sira") ?? 0 };
  if (!onceki || onceki.durum !== KDR.KAYIT || onceki.oturum !== oturum) {
    const bilinen = typeof bilinenHizMs === "number" && bilinenHizMs > 0 ? bilinenHizMs : null;
    return { durum, oturum, basMs: onceki ? simdiMs : null, hizMs: bilinen, olculen: false, ilk: gozlem, son: gozlem };
  }
  let { hizMs, olculen } = onceki;
  if (hizMs === null || olculen) {
    const dt = simdiMs - onceki.ilk.t;
    const dn = gozlem.n - onceki.ilk.n;
    if (dt >= OLCUM_EN_AZ_MS && dn > 0) { hizMs = dt / dn; olculen = true; }
  }
  return { ...onceki, hizMs, olculen, son: gozlem };
}

// Kayit suresi (ms) | null: bilinen aralikta nokta x aralik; degilse gorulen baslangictan.
export function kayitSuresi(izleme, simdiMs) {
  if (!izleme || izleme.durum !== KDR.KAYIT) return null;
  if (izleme.hizMs !== null && !izleme.olculen) return izleme.son.n * izleme.hizMs + Math.max(0, simdiMs - izleme.son.t);
  if (izleme.basMs !== null) return Math.max(0, simdiMs - izleme.basMs);
  if (izleme.hizMs !== null) return izleme.son.n * izleme.hizMs;
  return null;
}

// Aktif kayit karti. kayit = G satiri | null.
//   { var: false, rozet: "m.dr.kayit_bilinmiyor" }                 G satiri yok
//   { var: true, suruyor: false, rozet: "kayit.durum.<n>" ... }     kayit yok / dolu / hata ...
//   { var: true, suruyor: true, rozet: "cn.kayit_suruyor", sure, hiz, doluluk, onaysiz, oturum }
// Veri GELMIYORKEN (taze: false — akis acik degil / veri eski) kart SON BILINEN durumu gosterir ve bunu soyler
// (kullanici, 2026-10-05): sure sayaci son verinin aninda DONAR, rozet "Kayit suruyordu" olur ve `sonVeri`
// ("son veri X sn once") dolar — ilerleyen bir sayac kaydin surdugunu sandirir.
export function kayitGorunumu(kayit, izleme, simdiMs, { taze = true, sonGorulmeMs = null } = {}) {
  const sonVeri = taze ? null : gecenYaz(Number.isFinite(sonGorulmeMs) ? Math.max(0, simdiMs - sonGorulmeMs) : NaN);
  // Donmus saat: son verinin ani (bilinmiyorsa sure HIC gosterilmez).
  const saat = taze ? simdiMs : (Number.isFinite(sonGorulmeMs) ? Math.min(simdiMs, sonGorulmeMs) : null);
  const durum = gAlan(kayit, "durum");
  if (durum === null) {
    return { var: false, suruyor: false, rozet: "m.dr.kayit_bilinmiyor", sinif: "sakin", sure: YOK, hiz: null, doluluk: null, onaysiz: null, oturum: null, sonVeri: null };
  }
  const ortak = {
    var: true, sonVeri,
    doluluk: yuzde(gAlan(kayit, "doluluk", "doluluk_binde")),
    onaysiz: yuzde(gAlan(kayit, "onaysiz", "onaysiz_binde")),
  };
  if (durum !== KDR.KAYIT) {
    const bilinen = Object.values(KDR).includes(durum);
    return {
      ...ortak, suruyor: false,
      rozet: durum === KDR.BOS ? "m.dr.kayit_yok" : bilinen ? `kayit.durum.${durum}` : "kayit.durum.bilinmeyen",
      rozetDeger: bilinen ? null : { kod: durum },
      sinif: durum === KDR.BOS || durum === KDR.TARIYOR ? "sakin" : "uyari",
      sure: YOK, hiz: null, oturum: null,
    };
  }
  const uyan = izleme && izleme.durum === KDR.KAYIT && izleme.oturum === gAlan(kayit, "oturum") ? izleme : null;
  return {
    ...ortak, suruyor: true, rozet: taze ? "cn.kayit_suruyor" : "m.dr.kayit_suruyordu", rozetDeger: null, sinif: taze ? "" : "uyari",
    sure: saat === null ? YOK : sureYaz(kayitSuresi(uyan, saat)),
    hiz: uyan && uyan.hizMs !== null ? hizYaz(uyan.hizMs, uyan.olculen) : null,
    oturum: gAlan(kayit, "oturum"),
  };
}

// Baglanti satiri (Durum) ve ust cubuktaki cip.
//   { anahtar, sinif: "iyi" | "uyari" | "", gecen, esles, yeniden }
export function baglantiGorunumu({ baglanti, araniyor = false, akis = null, sonGorulmeMs = null, simdiMs = 0 }) {
  // "Son gorulme" yalniz veri GELMIYORKEN yazilir (kullanici, 2026-10-05): veri akarken satir saniyede bir
  // "0 sn once" gosterip kayboluyordu (veri tikler arasinda gelince yas eksi cikiyor, satir siliniyordu).
  // Saat tikten geride kalmissa yas 0 sayilir — satir bir gorunup bir kaybolmaz.
  const yas = Number.isFinite(sonGorulmeMs) ? gecenYaz(Math.max(0, simdiMs - sonGorulmeMs)) : null;
  const sonuc = (anahtar, sinif, ek = null) => ({ anahtar, sinif, gecen: yas, esles: false, yeniden: false, ...ek });
  if (!baglanti) return sonuc(araniyor ? "m.dr.araniyor" : "m.dr.ulasilamiyor", "", { yeniden: !araniyor });
  switch (baglanti.durum) {
    case "eslesmemis": return sonuc("m.dr.eslesmemis", "uyari", { esles: true });
    case "kimlik-uymuyor": return sonuc("m.bg.durum_kimlik", "uyari", { esles: true });
    case "kasa-bozuk": return sonuc("m.dr.kasa_bozuk", "uyari", { esles: true });
    case "bagli": break;
    default: return sonuc(araniyor ? "m.dr.araniyor" : "m.dr.ulasilamiyor", "", { yeniden: !araniyor });
  }
  const hal = akis ? akis.hal : "kapali";
  if (akis && akis.hazir === false) return sonuc("m.dr.bu_agda", "iyi", { gecen: null });       // akis modulu yok: baglanti yine de var
  if (hal === "acik") return sonuc("m.dr.bu_agda", "iyi", { gecen: null });
  if (hal === "dolu") return sonuc("m.cn.dolu", "uyari");
  if (hal === "hata") return sonuc("m.dr.ulasilamiyor", "uyari", { yeniden: true });
  // Akis acik ama veri gelmiyor (kart kapanmis / agdan dusmus olabilir): "bagli" DENMEZ.
  if (hal === "eski") return sonuc("m.dr.veri_yok", "uyari", { yeniden: true });
  return sonuc("m.cn.baglaniyor", "");
}
