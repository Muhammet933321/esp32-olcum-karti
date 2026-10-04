// Canli ekraninin (A40) durum -> gorunum eslemesi ve grafik serileri. Saf; DOM'suz sinanir.
import { KDR, gAlan } from "./durum_gorunum.js";

// Kayit hizi secici: etiket (olcum/s) -> kartin kayit araligi (ms) -> komut. Kart yalniz
// 20/100/200/1000/10000/60000 ms kabul eder (kayit__hiz_gecerli); telefonda dort secenek.
export const HIZLAR = Object.freeze([
  Object.freeze({ ms: 1000, yazi: "1/s" }),
  Object.freeze({ ms: 200, yazi: "5/s" }),
  Object.freeze({ ms: 100, yazi: "10/s" }),
  Object.freeze({ ms: 20, yazi: "50/s" }),
]);
export const VARSAYILAN_HIZ_MS = 200;
export const DURDUR_KOMUTU = "Gd";

// Secilen hiz -> "Gb<ms>". Listede OLMAYAN deger komut olmaz (null): ekran uydurma hiz gonderemez.
export function hizKomutu(ms) {
  return HIZLAR.some((h) => h.ms === ms) ? `Gb${ms}` : null;
}

export const PENCERELER = Object.freeze([
  Object.freeze({ s: 60, anahtar: "m.cn.pencere_60s" }),
  Object.freeze({ s: 300, anahtar: "m.cn.pencere_5dk" }),
]);
export const SAG_EKSENLER = Object.freeze(["a", "w"]);
export const BIRIM = Object.freeze({ v: "V", a: "A", w: "W" });

// Canli ekranin ust durumu.
//   { anahtar, sinif, akiyor (rakamlar canli mi), komut (kayit komutlari acik mi), esles }
export function canliHali({ baglanti, araniyor = false, akis = null }) {
  const sonuc = (anahtar, sinif, ek = null) => ({ anahtar, sinif, akiyor: false, komut: false, esles: false, ...ek });
  if (!baglanti) return sonuc(araniyor ? "m.dr.araniyor" : "m.cn.kart_yok", araniyor ? "" : "uyari");
  if (baglanti.durum === "eslesmemis") return sonuc("m.dr.eslesmemis", "uyari", { esles: true });
  if (baglanti.durum === "kimlik-uymuyor") return sonuc("m.bg.durum_kimlik", "uyari", { esles: true });
  if (baglanti.durum === "kasa-bozuk") return sonuc("m.dr.kasa_bozuk", "uyari", { esles: true });
  if (baglanti.durum !== "bagli") return sonuc(araniyor ? "m.dr.araniyor" : "m.cn.kart_yok", araniyor ? "" : "uyari");
  if (!akis || akis.hazir === false) return sonuc("m.cn.akis_yok", "uyari");
  switch (akis.hal) {
    case "acik": return sonuc("m.dr.bu_agda", "iyi", { akiyor: true, komut: true });
    case "dolu": return sonuc("m.cn.dolu", "uyari", { komut: true });     // izleyemiyoruz ama komut yolu ayri
    case "hata": return sonuc("m.cn.kart_yok", "uyari");
    default: return sonuc("m.cn.baglaniyor", "");
  }
}

// Kayit dugmesi: G satirina gore.
//   "baslat" | "durdur" | "kapali" (+ neden: sozluk anahtari)
export function kayitDugmesi(kayit) {
  const durum = gAlan(kayit, "durum");
  if (durum === KDR.KAYIT) return { is: "durdur", neden: null };
  if (durum === KDR.BOS || durum === null) return { is: "baslat", neden: null };
  const bilinen = Object.values(KDR).includes(durum);
  return { is: "kapali", neden: bilinen ? `kayit.durum.${durum}` : "kayit.durum.bilinmeyen", nedenDeger: bilinen ? null : { kod: durum } };
}

const BOS = Object.freeze({ seriler: Object.freeze([]), sonT: 0, n: 0 });

// canli.seri() -> son `pencereMs`'lik grafik serileri (ortak/src/grafik.js bicimi).
// seri: { t: Float64Array (ms, artan), v, a, w, n } — ilk n oge gecerli. Uc kanal AYNI t dizisini paylasir.
// Sag eksen TEK birim (A ya da W): iki birim tek eksende eksen yazisini yalanci yapardi.
export function pencereSerileri(seri, pencereMs, sagEksen = "a") {
  const n = seri && Number.isInteger(seri.n) ? Math.min(seri.n, seri.t ? seri.t.length : 0) : 0;
  if (n <= 0) return BOS;
  const sonT = seri.t[n - 1];
  let bas = 0;
  let son = n;
  while (bas < son) {                               // ikili arama: t >= sonT - pencereMs olan ilk indis
    const orta = (bas + son) >> 1;
    if (seri.t[orta] < sonT - pencereMs) bas = orta + 1; else son = orta;
  }
  const t = seri.t.subarray(bas, n);
  const kanal = (ad, alan, renk, eksen, gizli) => ({ ad, t, y: seri[alan].subarray(bas, n), birim: ad, renk, eksen, boslukMs: 2500, gizli });
  return {
    sonT,
    n: n - bas,
    seriler: [
      kanal(BIRIM.v, "v", "volt", "sol", false),
      kanal(BIRIM.a, "a", "amper", "sag", sagEksen !== "a"),
      kanal(BIRIM.w, "w", "watt", "sag", sagEksen !== "w"),
    ],
  };
}
