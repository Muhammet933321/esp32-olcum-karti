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
export function kayitGorunumu(kayit, izleme, simdiMs) {
  const durum = gAlan(kayit, "durum");
  if (durum === null) {
    return { var: false, suruyor: false, rozet: "m.dr.kayit_bilinmiyor", sinif: "sakin", sure: YOK, hiz: null, doluluk: null, onaysiz: null, oturum: null };
  }
  const ortak = {
    var: true,
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
    ...ortak, suruyor: true, rozet: "cn.kayit_suruyor", rozetDeger: null, sinif: "",
    sure: sureYaz(kayitSuresi(uyan, simdiMs)),
    hiz: uyan && uyan.hizMs !== null ? hizYaz(uyan.hizMs, uyan.olculen) : null,
    oturum: gAlan(kayit, "oturum"),
  };
}

// Baglanti satiri (Durum) ve ust cubuktaki cip.
//   { anahtar, sinif: "iyi" | "uyari" | "", gecen, esles, yeniden }
export function baglantiGorunumu({ baglanti, araniyor = false, akis = null, sonGorulmeMs = null, simdiMs = 0 }) {
  const gecen = sonGorulmeMs === null ? null : gecenYaz(simdiMs - sonGorulmeMs);
  const sonuc = (anahtar, sinif, ek = null) => ({ anahtar, sinif, gecen, esles: false, yeniden: false, ...ek });
  if (!baglanti) return sonuc(araniyor ? "m.dr.araniyor" : "m.dr.ulasilamiyor", "", { yeniden: !araniyor });
  switch (baglanti.durum) {
    case "eslesmemis": return sonuc("m.dr.eslesmemis", "uyari", { esles: true });
    case "kimlik-uymuyor": return sonuc("m.bg.durum_kimlik", "uyari", { esles: true });
    case "kasa-bozuk": return sonuc("m.dr.kasa_bozuk", "uyari", { esles: true });
    case "bagli": break;
    default: return sonuc(araniyor ? "m.dr.araniyor" : "m.dr.ulasilamiyor", "", { yeniden: !araniyor });
  }
  const hal = akis ? akis.hal : "kapali";
  if (akis && akis.hazir === false) return sonuc("m.dr.bu_agda", "iyi");       // akis modulu yok: baglanti yine de var
  if (hal === "acik") return sonuc("m.dr.bu_agda", "iyi");
  if (hal === "dolu") return sonuc("m.cn.dolu", "uyari");
  if (hal === "hata") return sonuc("m.dr.ulasilamiyor", "uyari", { yeniden: true });
  return sonuc("m.cn.baglaniyor", "");
}
