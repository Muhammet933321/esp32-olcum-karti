// Kartin canli akis (SSE) satirlari -> nesne (5C-1, A6/A7). SAF: ag, zaman, durum yok; Node'da sinanir.
// Bicimler kartin kaynagindan okundu (kod/olcum-karti-a3/olcum-karti-a3.ino), tahmin degil:
//
//   D <volt> <amper> <watt> <joule> <wh> <millis> <ornek> <menzil> <adc_hata>
//        "D %.4f %.6f %.5f %.4f %.7f %lu %lu %u %u" — rapor araliginda bir (varsayilan 5/s)
//        menzil 0 = NORMAL, 1 = YUKSEK; adc_hata bit0 = gerilim ADC'si, bit1 = akim ADC'si okunamadi
//   G <durum> <oturum> <nokta> <sonraki> <onay> <doluluk> <onaysiz> <dusen> <yaz_azami_us>
//     <sil_azami_us> <sil_adet> <tarama_ms> <son_hata> [<son_not> <mesaj_dusen>]
//        13 alan (A3-4B ve oncesi) ya da 15 alan (A3-W2). Kayitta saniyede bir, degisince hemen, `G?` ile.
//        durum: KDR (0 tariyor, 1 bos, 2 kayit, 3 dolu, 4 bekliyor, 5 hata); doluluk / onaysiz binde.
//   GA <hazir_sektor> <ayrintili_ornek> <dusen_ornek> <kayit_ici_silme>          (`G?` ile)
//   GT <etkin> <aralik_ms> <yakalama> <yazilamayan>                              (`G?` ile)
//   GP <durum> <bas_unix> <sure_s> <hiz_ms> <oturum>                             (`G?`, `Gp?` ile; durum: PLAN)
//   K <kayip_ms> <loop_azami_us> <loop_uzun_adet>                                (yalniz degisince)
//   A menzil=NORMAL|YUKSEK oto=<0|1> … rapor=<ms>                                (`?` ile)
//
// Ayristirici KATI: alan sayisi ya da bicimi tutmayan satir o tur SAYILMAZ; ama hicbir girdi ATMAZ —
// taninmayan her sey { tur: "diger", ham } olur (ham en cok SATIR_AZAMI karakter).

export const SATIR_AZAMI = 512;                 // kartin satir tamponu 224 bayt (WEB_SATIR_AZAMI)
export const G_ESKI_ALAN = 13;

export const KDR = Object.freeze({ TARIYOR: 0, BOS: 1, KAYIT: 2, DOLU: 3, BEKLIYOR: 4, HATA: 5 });
export const PLAN = Object.freeze({
  YOK: 0, BEKLIYOR: 1, SURUYOR: 2, BITTI: 3, ATLANDI: 4, KACIRILDI: 5, SAAT_YOK: 6, BASLATILAMADI: 7,
});

export const ALANLAR = Object.freeze({
  G: Object.freeze(["durum", "oturum", "nokta", "sonraki", "onay", "doluluk", "onaysiz", "dusen",
    "yaz_azami_us", "sil_azami_us", "sil_adet", "tarama_ms", "son_hata", "son_not", "mesaj_dusen"]),
  GA: Object.freeze(["hazir_sektor", "ayrintili_ornek", "dusen_ornek", "kayit_ici_silme"]),
  GT: Object.freeze(["etkin", "aralik_ms", "yakalama", "yazilamayan"]),
  GP: Object.freeze(["durum", "bas_unix", "sure_s", "hiz_ms", "oturum"]),
  K: Object.freeze(["kayip_ms", "loop_azami_us", "loop_uzun_adet"]),
});

const ISARETLI = Object.freeze(["son_hata", "son_not"]);          // kartta %ld
const DURUM_AZAMI = Object.freeze({ G: KDR.HATA, GP: PLAN.BASLATILAMADI });
const TAMSAYI = /^[0-9]{1,10}$/;
const ISARETLI_TAMSAYI = /^-?[0-9]{1,10}$/;
const ONDALIK = /^-?[0-9]{1,12}(\.[0-9]{1,9})?$/;
const SAYI_DEGIL = /^-?(nan|inf)$/;

const diger = (ham) => ({ tur: "diger", ham });

function ondalik(s) {
  if (ONDALIK.test(s)) return Number(s);
  return SAYI_DEGIL.test(s) ? NaN : null;
}

function dAyir(p) {
  if (p.length !== 10) return null;
  const o = { tur: "D" };
  const adlar = ["v", "a", "w", "joule", "wh"];
  for (let i = 0; i < adlar.length; i++) {
    const x = ondalik(p[i + 1]);
    if (x === null) return null;
    o[adlar[i]] = x;
  }
  for (let i = 6; i < 10; i++) if (!TAMSAYI.test(p[i])) return null;
  o.ms = Number(p[6]);
  o.ornek = Number(p[7]);
  o.menzil = Number(p[8]);
  o.adcHata = Number(p[9]);
  if (o.menzil > 1 || o.adcHata > 3) return null;
  return o;
}

function tamsayiSatiri(tur, p) {
  const alanlar = ALANLAR[tur];
  const n = p.length - 1;
  if (n !== alanlar.length && !(tur === "G" && n === G_ESKI_ALAN)) return null;
  const o = { tur };
  for (let i = 0; i < alanlar.length; i++) {
    if (i >= n) {                               // eski firmware: sondaki yeni alanlar yok
      o[alanlar[i]] = null;
      continue;
    }
    const desen = ISARETLI.includes(alanlar[i]) ? ISARETLI_TAMSAYI : TAMSAYI;
    if (!desen.test(p[i + 1])) return null;
    o[alanlar[i]] = Number(p[i + 1]);
  }
  if (Object.hasOwn(DURUM_AZAMI, tur) && o.durum > DURUM_AZAMI[tur]) return null;
  return o;
}

function aAyir(p) {
  const al = new Map();
  for (const parca of p.slice(1)) {
    const e = parca.indexOf("=");
    if (e > 0) al.set(parca.slice(0, e), parca.slice(e + 1));
  }
  const menzil = al.get("menzil") === "NORMAL" ? 0 : al.get("menzil") === "YUKSEK" ? 1 : null;
  const oto = al.get("oto"), rapor = al.get("rapor");
  if (menzil === null || (oto !== "0" && oto !== "1") || !TAMSAYI.test(rapor || "")) return null;
  return { tur: "A", menzil, oto: Number(oto), rapor_ms: Number(rapor) };
}

export function satirAyir(satir) {
  if (typeof satir !== "string") return diger("");
  if (satir.length > SATIR_AZAMI) return diger(satir.slice(0, SATIR_AZAMI));
  const p = satir.trim().split(/\s+/);
  let o = null;
  if (p[0] === "D") o = dAyir(p);
  else if (p[0] === "A") o = aAyir(p);
  else if (Object.hasOwn(ALANLAR, p[0])) o = tamsayiSatiri(p[0], p);
  return o || diger(satir);
}
