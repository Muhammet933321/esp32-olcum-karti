// Kayitlar listesi ve kayit gorunumu icin saf gorunum yardimcilari (A41). DOM'suz sinanir.

export const TUR_SECENEKLERI = Object.freeze([
  Object.freeze({ deger: "hepsi", anahtar: "m.ky.tur_hepsi" }),
  Object.freeze({ deger: "olcum", anahtar: "m.ky.tur_olcum" }),
  Object.freeze({ deger: "pil", anahtar: "m.ky.suz_pil" }),        // suzgec dugmesi dar: kisa ad
  Object.freeze({ deger: "skop", anahtar: "m.ky.suz_skop" }),
]);

const TUR = Object.freeze({
  olcum: "m.ky.tur_olcum", ayrinti: "m.ky.tur_ayrinti", pil: "m.ky.tur_pil", skop: "m.ky.tur_skop", bilinmeyen: "m.ky.tur_bilinmeyen",
});
const NEREDE = Object.freeze({ kart: "m.ky.nerede_kart", telefon: "m.ky.nerede_telefon", ikisi: "m.ky.nerede_ikisi" });

// Liste satiri -> ekrandaki hali.
//   acilabilir: kayit gorunumu acilir mi (telefonda kopyasi VAR). Yalniz kartta olan oturum acilmaz:
//   once esitlenmeli ("nerede: kart" + aciklama).
export function satirGorunumu(s) {
  const tur = Object.hasOwn(TUR, s.tur) ? TUR[s.tur] : TUR.bilinmeyen;
  const nerede = Object.hasOwn(NEREDE, s.nerede) ? NEREDE[s.nerede] : NEREDE.telefon;
  return {
    // Liste anahtari AKIS + oturum: kartin akisi degistiyse ayni numarali iki oturum ayri satirdir.
    anahtar: typeof s.anahtar === "string" && s.anahtar !== "" ? s.anahtar : String(s.oturum),
    eskiKart: s.eskiKart === true,
    oturum: s.oturum,
    ad: typeof s.ad === "string" && s.ad !== "" ? s.ad : null,      // null: "Oturum #N" (m.ky.adsiz)
    tur, nerede,
    neredeSinif: s.nerede === "kart" ? "uyari" : (s.nerede === "ikisi" ? "iyi" : ""),
    tarih: s.tarih || null,
    sure: s.sure || null,
    kayitta: s.durum === "kayitta",
    eksik: s.eksik === true,
    acilabilir: s.yerelde === true,
  };
}

// Listenin ustundeki not: kartin dizini listeye KATILMADIYSA nedenini soyler. Dizin katildiysa null.
//   kart bagli ama dizin okunamadi -> "okunamadi" · agda ama eslesmemis -> "eslesmemis" · yoksa "bu agda degil"
export function kartNotu(baglanti, kartVar) {
  if (kartVar === true) return null;
  const durum = baglanti && typeof baglanti.durum === "string" ? baglanti.durum : null;
  if (durum === "bagli") return "m.ky.kart_okunamadi";
  if (durum === "eslesmemis" || durum === "kimlik-uymuyor" || durum === "kasa-bozuk") return "m.ky.kart_eslesmemis";
  return "m.ky.kart_yok";
}

// Sag eksende gosterilecek buyukluk: "akim" | "guc". Iki birim tek eksende olmaz (eksen yazisi yalan soylerdi).
export const SAG_EKSENLER = Object.freeze([
  Object.freeze({ deger: "akim", anahtar: "m.cn.akim" }),
  Object.freeze({ deger: "guc", anahtar: "m.cn.guc" }),
]);

// Sayi -> yazi (sabit hane); sonlu degilse "—".
export function sayiYaz(x, hane) {
  return Number.isFinite(x) ? x.toFixed(hane) : "—";
}

// aralikOkuma sonucu -> tablo satirlari [{ anahtar, birim, ort, min, maks }] + enerji.
export function okumaTablosu(ok) {
  if (!ok) return null;
  const satir = (anahtar, k, hane) => (k ? { anahtar, birim: k.birim, ort: sayiYaz(k.ort, hane), min: sayiYaz(k.min, hane), maks: sayiYaz(k.maks, hane) } : null);
  return {
    sure: ok.sure || "—",
    adet: ok.v ? ok.v.adet : (ok.i ? ok.i.adet : 0),
    satirlar: [satir("m.cn.gerilim", ok.v, 3), satir("m.cn.akim", ok.i, 3), satir("m.cn.guc", ok.w, 2)].filter(Boolean),
    mah: ok.enerji ? sayiYaz(ok.enerji.mah, 2) : "—",
    wh: ok.enerji ? sayiYaz(ok.enerji.wh, 3) : "—",
  };
}
