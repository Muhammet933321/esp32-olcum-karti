// B73 / 2F — DISA AKTARMA: CSV (Excel-TR) + ham kayit. Tasarim:
// tasarim/2026-10-02-alt-proje-2-ortak.md (2F), ust tasarim §5 (oturumlar), §9 (rapor, dil).
//
// Girdi kayit.js'in cozdugu oturumdur (oturumlariKur). Fiziksel birimler kayit.js
// volt()/amper() ile, oturumun KENDI kalibrasyon kopyasindan (BASLA/TEKRAR) — kopru/
// kayit_bicim.py ile bit bit ayni sayilar. Bagimlilik yok, Node API'si yok.
//
// ── CSV BICIMI ───────────────────────────────────────────────────────────────────
// Varsayilan Excel-TR (kopru/arsiv.py csv_uret ile ayni sozlesme): UTF-8 + BOM, ';' ayrac,
// CRLF (son satir dahil), ondalik VIRGUL, tek baslik satiri, sutun adlari kucuk ASCII
// snake_case + SI birimi soneki (v_ort_V). Secenekler: ayrac, ondalik (',' | '.'), bom,
// satirSonu, dil ('tr' | 'en': yalniz basliklar ve metin hucreleri; sayilar ayni).
// BICIM_EN = ',' ayrac + '.' ondalik. ayrac === ondalik REDDEDILIR (RangeError).
//
// SAYI YAZIMI (sayiYaz): ustel gosterim YOK, binlik ayraci YOK. Yuvarlama Python
// format(x, ".Nf") ile AYNI: double'in TAM ikili degeri uzerinden en yakin, tam ortada
// YARIDA CIFTE (toFixed yarida yukari gider: 0.0078125 -> "0.007813", Python "0.007812").
// Bilerek fark: sifira yuvarlanan eksi deger isaretsiz yazilir ("0,000000"; Python
// "-0.000000"). NaN / sonsuz / null / undefined -> BOS hucre.
//   Basamak (BASAMAK): V 6 · A 6 · W 6 · ohm 6 · mAh 6 · Wh 6 · unix_s 3 · ayrintili
//   gecen_ms 3 (mikrosaniye) · skop t_s 9. Tamsayilar (sira, kart_ms, nokta gecen_ms, n,
//   bayrak, kod) aynen. Zamanlar tamsayi ms/us'ten olcekli yazilir: kayan nokta yok.
//
// METIN HUCRESI: RFC 4180 — ayrac, cift tirnak, CR ya da LF iceren alan tirnaga alinir, ic
// tirnak ikilenir. Formul enjeksiyonu: '=', '+', '-', '@', TAB ya da CR ile baslayan METIN
// hucresine "'" onek (Excel onu formul diye calistirmasin; OWASP). Sayi hucreleri etkilenmez.
//
// ── ZAMAN (zamanEkseni) ───────────────────────────────────────────────────────────
// acilis: 0 = BASLA'nin acilisi, n = n. DEVAM'dan sonrasi (kayit.js ayrintiOrnekler ile ayni:
// nokta sirasi >= DEVAM.nokta_sira). Kart yeniden baslayinca millis() sifirlanir; her acilisin
// capasi (kart_ms, unix) BASLA ya da DEVAM; unix 0 ise ayni acilisin SAAT kaydi (NTP sonradan
// geldi). Acilis icinde zaman ARDISIK isaretli 32 bit farklarla acilir (millis sarmasi 49.7 g).
//   gecen_ms = oturum baslangicindan (BASLA ani) beri. Acilis 0'da her zaman bilinir; sonraki
//     acilislarda yalniz iki capanin unix'i de biliniyorsa (unix tam saniye: aradaki
//     yeniden baslama boslugu +-1 s). Bilinmiyorsa BOS hucre.
//   unix_s / zaman_utc = unix capa + acilis ici fark (unix tam saniyeden: mutlak +-1 s).
//     zaman_utc ISO 8601, UTC, milisaniyeli ("2026-10-01T12:00:00.250Z").
//   OLAY / NOT / SKOP zamanlari kart_ms tasir, ACILIS NUMARASI TASIMAZ: DEVAM'siz oturumda
//     acilis 0. DEVAM'li oturumda OLAY/SKOP kayit sirasiyla acilisa baglanir (secenek
//     `kayitlar`: ham kayitlar, DEVAM kayitlarinin sirasi oradan); NOT'un kayit sirasi
//     anlamsiz (sonradan yazilabilir, "grafikteki kart_ms") -> kart_ms'nin hangi acilisin
//     [capa, son veri] araligina dustugune bakilir: tek aday -> o; hic yoksa ve son acilisin
//     capasindan sonraysa -> son acilis; birden fazla -> belirsiz (zaman bos, rapor uyarir).
//     (`kayitlar` verilmeyen DEVAM'li oturumda OLAY/SKOP da bu sezgiyle.)
//     Acilis icinde olay/not farki isaretli 32 bit (+-24.8 gun).
//
// ── TABLOLAR ─────────────────────────────────────────────────────────────────────
// oturumCsv  nokta basina satir: sira, acilis, devam (DEVAM'dan sonraki ILK satir 1; bos
//            satir YOK), kart_ms (noktanin BITTIGI an), gecen_ms, unix_s, zaman_utc, n,
//            V/A/W ort-min-maks, bayrak + adlari, not. V/A: KN_YUKSEK'te yuksek kanal.
//            v_min_V = volt(v_min_kod) (kayittaki min KOD; kalibrasyon carpani eksiyse
//            buyuklugu min olmayabilir — kayit ne diyorsa o). W kartin sakladigi watt
//            (ornek basina V*I ortalamasi). n = 0 (hic gecerli ornek yok): V/A/W BOS.
// ayrintiCsv ornek basina satir (hiz 0): sira, acilis, devam, kart_us, gecen_ms (3 hane),
//            unix_s, zaman_utc, V, A, W, ornek_bayrak (KAO), kayit_bayrak (KA;
//            kaydin ILK orneginde: KA_SILME/KA_KAYIP_ONCE), bayraklar, not. KAO_V_HATA'li
//            ornekte V (ve W) BOS, KAO_I_HATA'lida A (ve W) BOS. W1: W = HIZALI guc
//            (kayit.js ayrintiGuc: V akim ornegi anina Lagrange'la tasinir, kartin o.watt'iyla
//            ayni tanim) — ayni satirin V x A'si DEGIL. V/A ham ornegin kendisi.
// SKOP BOSLUGU (W1/Y7): oturumdaki her META'li yakalama kayit.js skopYerleri ile ZAMANINA
//            yerlestirilir (kayit sirasi zaman sirasi degil); yakalamadan SONRAKI ilk olcum
//            satirinin `bayraklar` hucresine "SKOP" eklenir (sayisal bayrak sutunlari kartin
//            yazdigi gibi kalir: PC turetimi ham bayraga karismaz). Nokta oturumunda o satir
//            yakalamanin icine dustugu noktadir.
// pilCsv     KARAR: TEK TABLO, DCIR olaylari ZAMAN SIRASINDA AYRI SATIR (ilk sutun `kayit`:
//            nokta | dcir). Nokta satirlari oturumCsv sutunlari + birikimli mAh/Wh (PC,
//            yamuk, bosluk haric — rapor enerjisiyle son satirda AYNI sayi); DCIR satirinda
//            nokta sutunlari bos, dcir_* sutunlari (kartin olcumu; dcir_mAh/Wh kartin o ana
//            kadarki sayaci). DCIR, zamani <= olan noktalardan SONRA gelir. PIL_AYAR /
//            PIL_SONUC CSV'de YOK (tek seferlik): rapor.js'te. PT2: OCV on evresinin noktalari (yuk KAPALI)
//            `bayrak`ta KN_OCV (0x80), `bayraklar`da "OCV" — yeni SUTUN YOK (Python arsiv.py ile ayni sutunlar).
//            PT4 her ornek pil oturumunun AYRINTI ornekleri ayrintiCsv ile (ayri dosya).
//            HT3: oturumda KO_PIL_HAT olayi VARSA (yalniz o zaman) SONA uc sutun: v_pil_V (V_ort + I_ort x R, R o
//            satirin aninda gecerli hat direnci; DCIR satirinda bos), w_pil_W (pilin verdigi guc W_ort + I_ort^2 x R —
//            nokta yaklasimi: ornek basina I^2'nin ortalamasi kayitta yok) ve hat_mohm; o zaman `enerji_Wh` w_pil'den
//            (kartin pil Wh kurali). v/w ort-min-maks sutunlari HAM kalir. ayrintiCsv'de ayni (ornek basina, kesin).
//            Olay yoksa tablo BAYT BAYT eskisi. Basliklar sabit (HT_KOLON): acilis sozlugu dolu (EU32).
// skopCsv    tam yakalama: ornek, t_s (tetige gore: (i - tetik)/hz), kod, v_V = kod*adim -
//            ofset (META; arayuz kodVolt'un kalibrasyonsuz yolu). Eksik yakalama: null.
// hamDisari  oturumun kayitlari (oturum no'lu + hedefi bu oturum olan NOT'lar), kayit
//            sirasiyla, ayni sira bir kez, kayitPaketle ile YENIDEN CERCEVELI. Kart dolguyu
//            SIFIRLA yazar (kayit_gunluk.h) -> kartin akisindaki baytlarla AYNI; akisCoz /
//            kopru akis_coz geri okur.
//
// NOT HUCRESI: genel not (nokta_ms 0) ilk satirda; digeri zamanina dusen ilk satirda (o
// acilista zamani >= not); belirsizse kart_ms >= nokta_ms olan ilk satir, yoksa son satir.
// Ayni satirdaki notlar LF ile (tirnakli hucre icinde) birlesir, asil not sirasiyla.

import {
  volt, amper, ayrintiOrnekler, ayrintiGuc, skopYerleri, kayitPaketle, T_NOT,
  KN_YUKSEK, KN_V_HATA, KN_I_HATA, KN_V_DOYDU, KN_DURAKLAMA, KN_KAYIP_ONCE, KN_DCIR, KN_OCV,
  KAO_YUKSEK, KAO_V_HATA, KAO_I_HATA, KAO_V_DOYDU, KA_KAYIP_ONCE, KA_SILME, KO_DCIR,
  T_DEVAM, OTURUM_PIL, PIL_AYR_NOKTA_MS, KO_PIL_HAT, pilVDuzelt, pilWDuzelt,
} from "./kayit.js";
import { ceviri } from "./sozluk.js";
import { MS_SAAT, AMS_MAH } from "./istatistik.js";

export const BICIM_EXCEL_TR = Object.freeze({ ayrac: ";", ondalik: ",", bom: true, satirSonu: "\r\n", dil: "tr" });
export const BICIM_EN = Object.freeze({ ayrac: ",", ondalik: ".", bom: true, satirSonu: "\r\n", dil: "en" });
export const BASAMAK = Object.freeze({
  V: 6, A: 6, W: 6, ohm: 6, mAh: 6, Wh: 6, unix_s: 3, ayrinti_ms: 3, skop_t_s: 9,
});
/** Nokta oturumunda bosluk: ardisik iki nokta arasi > hiz_ms x 2.5 (D1). */
export const NOKTA_BOSLUK_KAT = 2.5;
/** Ayrintili kipte bosluk: kartin YENI AYRINTI kaydi actigi sinir (dt4 12 bit x 4 us). */
export const AYRINTI_BOSLUK_MS = 4095 * 4 / 1000;

/** PC'nin turettigi (kayitta biti olmayan) ad: yakalamadan sonraki ilk olcum satiri (W1/Y7). */
export const SKOP_BAYRAK_AD = "bayrak.skop";

/** Bayrak bit -> sozluk anahtari (adlar '|' ile). Bilinmeyen bit 0x.. diye yazilir. */
export const BAYRAKLAR = Object.freeze({
  nokta: Object.freeze([[KN_YUKSEK, "bayrak.yuksek"], [KN_V_HATA, "bayrak.v_hata"],
    [KN_I_HATA, "bayrak.i_hata"], [KN_V_DOYDU, "bayrak.v_doydu"], [KN_DURAKLAMA, "bayrak.duraklama"],
    [KN_KAYIP_ONCE, "bayrak.kayip_once"], [KN_DCIR, "bayrak.dcir"], [KN_OCV, "bayrak.ocv"]]),
  ornek: Object.freeze([[KAO_YUKSEK, "bayrak.yuksek"], [KAO_V_HATA, "bayrak.v_hata"],
    [KAO_I_HATA, "bayrak.i_hata"], [KAO_V_DOYDU, "bayrak.v_doydu"]]),
  kayit: Object.freeze([[KA_KAYIP_ONCE, "bayrak.kayip_once"], [KA_SILME, "bayrak.silme"]]),
});

/** Sutun anahtarlari (sozluk "csv.*"); basliklar ceviri(anahtar, dil). */
export const KOLONLAR = Object.freeze({
  nokta: Object.freeze(["csv.sira", "csv.acilis", "csv.devam", "csv.kart_ms", "csv.gecen_ms",
    "csv.unix_s", "csv.zaman_utc", "csv.n", "csv.v_ort", "csv.v_min", "csv.v_maks", "csv.i_ort",
    "csv.i_min", "csv.i_maks", "csv.w_ort", "csv.w_min", "csv.w_maks", "csv.bayrak",
    "csv.bayraklar", "csv.not"]),
  ayrinti: Object.freeze(["csv.sira", "csv.acilis", "csv.devam", "csv.kart_us", "csv.gecen_ms",
    "csv.unix_s", "csv.zaman_utc", "csv.v", "csv.i", "csv.w", "csv.ornek_bayrak",
    "csv.kayit_bayrak", "csv.bayraklar", "csv.not"]),
  pil: Object.freeze(["csv.kayit", "csv.sira", "csv.acilis", "csv.devam", "csv.kart_ms",
    "csv.gecen_ms", "csv.unix_s", "csv.zaman_utc", "csv.n", "csv.v_ort", "csv.v_min",
    "csv.v_maks", "csv.i_ort", "csv.i_min", "csv.i_maks", "csv.w_ort", "csv.w_min", "csv.w_maks",
    "csv.mah", "csv.wh", "csv.dcir_no", "csv.dcir_v_once", "csv.dcir_i_once", "csv.dcir_v_ani",
    "csv.dcir_v_oturmus", "csv.dcir_r_ani", "csv.dcir_r_oturmus", "csv.dcir_mah", "csv.dcir_wh",
    "csv.bayrak", "csv.bayraklar", "csv.not"]),
  skop: Object.freeze(["csv.skop_ornek", "csv.skop_t", "csv.skop_kod", "csv.skop_v"]),
});

// ── sayi yazimi ─────────────────────────────────────────────────────────────────
const IKI32 = 4294967296;
const SAYI_GORUNUM = new DataView(new ArrayBuffer(8));

/** |x| = m * 2^e (m BigInt, tam). x sonlu. */
function ikiliParcala(x) {
  SAYI_GORUNUM.setFloat64(0, x);
  const ust = SAYI_GORUNUM.getUint32(0);
  const alt = SAYI_GORUNUM.getUint32(4);
  const us = (ust >>> 20) & 0x7FF;
  let m = (BigInt(ust & 0xFFFFF) << 32n) | BigInt(alt);
  if (us === 0) return [m, -1074];
  m |= 1n << 52n;
  return [m, us - 1075];
}

/** n (BigInt >= 0) birimi 10^-basamak olan sayiyi yaz. */
function birimliYaz(n, basamak, ondalik, eksi) {
  let s = n.toString();
  if (basamak > 0) {
    s = s.padStart(basamak + 1, "0");
    s = s.slice(0, s.length - basamak) + ondalik + s.slice(s.length - basamak);
  }
  return (eksi && n !== 0n ? "-" : "") + s;
}

/** Tam ikili deger uzerinden yarida-cifte yuvarlama (BigInt; toFixed'in yetmedigi yol). */
function kesinYaz(x, basamak, ondalik) {
  const [m, e] = ikiliParcala(Math.abs(x));
  const p = 10n ** BigInt(basamak);
  let n;
  if (e >= 0) {
    n = (m << BigInt(e)) * p;
  } else {
    const pay = m * p;
    const payda = 1n << BigInt(-e);
    n = pay / payda;
    const iki = 2n * (pay - n * payda);
    if (iki > payda || (iki === payda && (n & 1n) === 1n)) n += 1n;
  }
  return birimliYaz(n, basamak, ondalik, x < 0);
}

/**
 * Sayiyi `basamak` ondalikla yaz: Python format(x, ".<basamak>f") ile ayni yuvarlama
 * (yarida cifte), ustel gosterim ve binlik ayraci YOK; sifira yuvarlanan eksi isaretsiz.
 * Sonlu olmayan / sayi olmayan -> "" (bos hucre).
 */
export function sayiYaz(x, basamak, ondalik = ".") {
  if (typeof x !== "number" || !Number.isFinite(x)) return "";
  if (!Number.isInteger(basamak) || basamak < 0 || basamak > 20) {
    throw new RangeError(`sayiYaz: basamak 0..20 tamsayi olmali (${basamak})`);
  }
  // Ortada kalma (tie) ancak x * 2^(b+1) tek tamsayiysa olur (x ikili kesir; 5^b pay'i boler).
  // Oyle degilse toFixed (tam degerden en yakin) dogru; 1e21 ustu toFixed ustel yazar.
  const y = x * 2 ** (basamak + 1);
  const ortada = Number.isInteger(y) && Math.abs(y) < 2 ** 53 && y % 2 !== 0;
  if (ortada || Math.abs(x) >= 1e21) return kesinYaz(x, basamak, ondalik);
  let s = x.toFixed(basamak);
  if (s[0] === "-" && /^-0(\.0*)?$/.test(s)) s = s.slice(1);
  return ondalik === "." ? s : s.replace(".", ondalik);
}

/** Tamsayi n'yi (birimi 10^-basamak) yaz: kayan nokta YOK. Guvenli tamsayi degilse "". */
export function olcekliYaz(n, basamak, ondalik = ".") {
  if (typeof n !== "number" || !Number.isSafeInteger(n)) return "";
  return birimliYaz(BigInt(Math.abs(n)), basamak, ondalik, n < 0);
}

/** Tamsayi n'yi bolen'e yarida-cifte bol (ikisi de guvenli tamsayi, bolen > 0). */
function ciftBol(n, bolen) {
  const q = Math.floor(n / bolen);
  const r = n - q * bolen;
  if (2 * r > bolen || (2 * r === bolen && q % 2 !== 0)) return q + 1;
  return q;
}

/** ms (tamsayi) -> ISO 8601 UTC, milisaniyeli. */
function isoYaz(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms)) return "";
  const d = new Date(ms);
  return Number.isNaN(d.getTime()) ? "" : d.toISOString();
}

// ── hucre / satir ───────────────────────────────────────────────────────────────
const FORMUL = /^[=+\-@\t\r]/;

/** RFC 4180 metin hucresi (+ formul onegi). */
export function metinHucre(s, ayrac = ";") {
  if (s === null || s === undefined) return "";
  let m = String(s);
  if (FORMUL.test(m)) m = "'" + m;
  if (m.includes(ayrac) || m.includes('"') || m.includes("\r") || m.includes("\n")) {
    m = '"' + m.split('"').join('""') + '"';
  }
  return m;
}

function bicimAl(secenek) {
  const b = { ...BICIM_EXCEL_TR, ...(secenek || {}) };
  if (typeof b.ayrac !== "string" || b.ayrac.length !== 1 || b.ayrac === '"' || b.ayrac === "\r" || b.ayrac === "\n") {
    throw new RangeError(`ayrac tek karakter olmali, tirnak/CR/LF olamaz (${JSON.stringify(b.ayrac)})`);
  }
  if (b.ondalik !== "," && b.ondalik !== ".") throw new RangeError(`ondalik ',' ya da '.' olmali (${b.ondalik})`);
  if (b.ondalik === b.ayrac) throw new RangeError("ayrac ile ondalik ayni olamaz");
  if (typeof b.satirSonu !== "string" || !/^(\r\n|\n|\r)$/.test(b.satirSonu)) {
    throw new RangeError("satirSonu CRLF, LF ya da CR olmali");
  }
  if (b.dil !== "tr" && b.dil !== "en") throw new RangeError(`dil 'tr' ya da 'en' olmali (${b.dil})`);
  return b;
}

function yazici(secenek) {
  const b = bicimAl(secenek);
  return {
    b,
    sayi: (x, basamak) => sayiYaz(x, basamak, b.ondalik),
    tam: (n) => (typeof n === "number" && Number.isSafeInteger(n) ? String(n) : ""),
    olcekli: (n, basamak) => olcekliYaz(n, basamak, b.ondalik),
    metin: (s) => metinHucre(s, b.ayrac),
    satir: (hucreler) => hucreler.join(b.ayrac) + b.satirSonu,
    baslik: (kolonlar) => kolonlar.map((k) => metinHucre(ceviri(k, b.dil), b.ayrac)).join(b.ayrac) + b.satirSonu,
    bas: () => (b.bom ? "﻿" : ""),
  };
}

/** Bayrak bitlerinin adlari ('|' ile). 0 -> "". */
export function bayrakAdlari(bayrak, tablo, dil = "tr") {
  const adlar = [];
  let kalan = bayrak >>> 0;
  for (const [bit, anahtar] of tablo) {
    if (kalan & bit) {
      adlar.push(ceviri(anahtar, dil));
      kalan &= ~bit;
    }
  }
  for (let bit = 1; kalan; bit <<= 1) {
    if (kalan & bit) {
      adlar.push("0x" + bit.toString(16));
      kalan &= ~bit;
    }
  }
  return adlar.join("|");
}

/** CSV metnini UTF-8 baytlarina cevir (BOM metnin icindeyse EF BB BF olur). */
export function csvBayt(metin) {
  return new TextEncoder().encode(metin);
}

// ── zaman ekseni ────────────────────────────────────────────────────────────────
/** a - b, isaretli 32 bit (u32 sayac farki). */
function fark32(a, b) {
  return (a - b) | 0;
}

/**
 * Oturumun acilis capalari. Donus:
 *   { devamVar, segmentler: [{no, acilis, kartMs, unixMs, ofsetMs, ilkSira, kayitSira,
 *     saattenUnix}], devamSiralari (nokta_sira, artan), kayitlarVar (DEVAM kayit siralari
 *     `kayitlar`dan alinabildi: OLAY/SKOP acilisi kesin) }
 * kartMs: acilisin capasi (BASLA/DEVAM kart_ms; BASLA yoksa ilk noktanin/ornegin kart_ms'i).
 * unixMs: capadaki unix (ms) ya da null. ofsetMs: oturum baslangicindan capaya ms ya da null.
 */
export function zamanEkseni(oturum, kayitlar = null) {
  const b = oturum.basla;
  const devamlar = oturum.devamlar.map((d, k) => ({ d, k }));
  const sirali = [...devamlar].sort((x, y) => x.d.nokta_sira - y.d.nokta_sira || x.k - y.k);
  // DEVAM kayitlarinin sirasi (kayit sirasiyla k. DEVAM = devamlar[k]; oturumlariKur ayni sirayla iter)
  let devamKayit = null;
  if (kayitlar) {
    devamKayit = kayitlar.filter((k) => k.tur === T_DEVAM && k.oturum === oturum.id)
      .map((k) => k.sira).sort((x, y) => x - y);
    if (devamKayit.length !== devamlar.length) devamKayit = null;   // tutarsiz: kullanma
  }
  let kart0 = b ? b.kart_ms : null;
  if (kart0 === null) {
    const ilkNokta = [...oturum.noktalar].sort((x, y) => x[0] - y[0])[0];
    if (ilkNokta) kart0 = ilkNokta[1].kart_ms;
    else if (oturum.ayrinti.length) kart0 = [...oturum.ayrinti].sort((x, y) => x.sira - y.sira)[0].t0_ms;
  }
  const segmentler = [{
    no: 0, acilis: b ? b.acilis : null, kartMs: kart0,
    unixMs: b && b.unix_s ? b.unix_s * 1000 : null, ofsetMs: 0, ilkSira: 0, kayitSira: null,
    saattenUnix: false,
  }];
  sirali.forEach(({ d, k }, j) => {
    segmentler.push({
      no: j + 1, acilis: d.acilis, kartMs: d.kart_ms, unixMs: d.unix_s ? d.unix_s * 1000 : null,
      ofsetMs: null, ilkSira: d.nokta_sira, kayitSira: devamKayit ? devamKayit[k] : null,
      saattenUnix: false,
    });
  });
  for (const s of segmentler) {
    if (s.unixMs !== null || s.acilis === null || s.kartMs === null) continue;
    const z = oturum.saatler.find((x) => x.acilis === s.acilis && x.unix_s);
    if (z) {
      s.unixMs = z.unix_s * 1000 - fark32(z.kart_ms, s.kartMs);
      s.saattenUnix = true;
    }
  }
  const u0 = segmentler[0].unixMs;
  for (const s of segmentler.slice(1)) s.ofsetMs = s.unixMs !== null && u0 !== null ? s.unixMs - u0 : null;
  return {
    devamVar: devamlar.length > 0,
    segmentler,
    devamSiralari: sirali.map(({ d }) => d.nokta_sira),
    kayitlarVar: devamKayit !== null,
  };
}

/** Nokta/ornek sirasinin acilisi: nokta_sira <= s olan DEVAM sayisi. */
function segmentNo(eksen, s) {
  let n = 0;
  for (const d of eksen.devamSiralari) if (d <= s) n++;
  return n;
}

/**
 * kart_ms'li bir anin (OLAY, NOT, SKOP) zamani. kayitSira: anin kayit sirasi (NOT icin
 * null). acilis: biliniyorsa (yakalama: kayit.js `acilis`) dogrudan o; yoksa kayitSira/sezgi.
 * araliklar: noktaSerileri/ayrintiSerileri'nin acilis basina [enKucukRel, enBuyukRel].
 * Donus {acilis, relMs, gecenMs, unixMs} — bilinmeyen alan null; acilis null = belirsiz.
 */
export function anZamani(eksen, araliklar, kartMs, kayitSira = null, acilis = null) {
  const seg = eksen.segmentler;
  let no = null;
  if (acilis !== null && Number.isInteger(acilis) && acilis >= 0 && acilis < seg.length) {
    no = acilis;                       // W1: kayit.js'in bildigi acilis (yakalama: DEVAM sayisi)
  } else if (!eksen.devamVar) {
    no = 0;
  } else if (kayitSira !== null && eksen.kayitlarVar) {
    no = 0;
    for (const s of seg) if (s.kayitSira !== null && s.kayitSira < kayitSira) no = Math.max(no, s.no);
  } else {
    // Sezgi: kart_ms hangi acilisin [capa, son veri] araligina dusuyor. Tek aday -> o; hic
    // aday yoksa ve SON acilisin son verisinden sonraysa -> son acilis; birden fazla -> belirsiz.
    const aday = [];
    for (const s of seg) {
      const a = araliklar ? araliklar[s.no] : null;
      if (s.kartMs === null || !a) continue;
      const rel = fark32(kartMs, s.kartMs);
      if (rel >= 0 && rel <= a[1]) aday.push(s.no);
    }
    const son = seg[seg.length - 1];
    if (aday.length === 1) no = aday[0];
    else if (aday.length === 0 && son.kartMs !== null && fark32(kartMs, son.kartMs) >= 0) no = son.no;
  }
  if (no === null || seg[no].kartMs === null) return { acilis: null, relMs: null, gecenMs: null, unixMs: null };
  const s = seg[no];
  const rel = fark32(kartMs, s.kartMs);
  return {
    acilis: no, relMs: rel,
    gecenMs: s.ofsetMs === null ? null : s.ofsetMs + rel,
    unixMs: s.unixMs === null ? null : s.unixMs + rel,
  };
}

// ── seriler (rapor.js de kullanir) ──────────────────────────────────────────────
function kanalSec(kal, yuksek) {
  return yuksek ? kal.yuksek : kal.normal;
}

/**
 * Nokta oturumunun fiziksel serileri (nokta sirasiyla). Diziler:
 *   sira, acilis, devam (0/1), kartMs, n, bayrak: Array;  relMs (acilis capasindan, ms),
 *   gecenMs, unixMs: Float64Array (bilinmeyen NaN);  vOrt vMin vMaks iOrt iMin iMaks wOrt
 *   wMin wMaks: Float64Array (V, A, W; eksik NaN); skop: Array (W1: yakalamanin icine dustugu
 *   noktada o yakalamanin skoplar anahtari, digerlerinde 0 — skopSonralari); yerler: kayit.js
 *   skopYerleri (rapor/gorunum yeniden hesaplamasin).
 * araliklar[acilis] = [ilk rel, son rel] (o acilisin noktalari). eksen: zamanEkseni.
 */
export function noktaSerileri(oturum, secenek = {}) {
  const eksen = secenek.eksen || zamanEkseni(oturum, secenek.kayitlar || null);
  const nk = [...oturum.noktalar].sort((x, y) => x[0] - y[0]);
  const n = nk.length;
  const kal = oturum.basla ? oturum.basla.kal : null;
  const f = () => new Float64Array(n).fill(NaN);
  const r = {
    adet: n, eksen, araliklar: [], sira: [], acilis: [], devam: [], kartMs: [], n: [], bayrak: [],
    relMs: new Float64Array(n), gecenMs: f(), unixMs: f(),
    vOrt: f(), vMin: f(), vMaks: f(), iOrt: f(), iMin: f(), iMaks: f(), wOrt: f(), wMin: f(), wMaks: f(),
    skop: [], yerler: skopYerleri(oturum),
  };
  const sonralar = skopSonralari(oturum, r.yerler);
  let onceSeg = 0;
  let onceKart = 0;
  let onceRel = 0;
  nk.forEach(([s, p], k) => {
    const sg = segmentNo(eksen, s);
    const seg = eksen.segmentler[sg];
    const rel = k > 0 && sg === onceSeg ? onceRel + fark32(p.kart_ms, onceKart) : fark32(p.kart_ms, seg.kartMs);
    r.sira.push(s);
    r.acilis.push(sg);
    r.devam.push(sg > 0 && (k === 0 || sg !== onceSeg) ? 1 : 0);
    r.kartMs.push(p.kart_ms);
    r.n.push(p.n);
    r.bayrak.push(p.bayrak);
    r.skop.push(sonralar.get(s) || 0);
    r.relMs[k] = rel;
    if (seg.ofsetMs !== null) r.gecenMs[k] = seg.ofsetMs + rel;
    if (seg.unixMs !== null) r.unixMs[k] = seg.unixMs + rel;
    const a = r.araliklar[sg];
    if (!a) r.araliklar[sg] = [rel, rel];
    else { a[0] = Math.min(a[0], rel); a[1] = Math.max(a[1], rel); }
    if (p.n > 0) {
      if (kal) {
        const kn = kanalSec(kal, p.bayrak & KN_YUKSEK);
        r.vOrt[k] = volt(p.v_ort_kod, kn, false);
        r.vMin[k] = volt(p.v_min_kod, kn, true);
        r.vMaks[k] = volt(p.v_maks_kod, kn, true);
        if (kal.sont_ohm !== 0) {
          r.iOrt[k] = amper(p.i_ort_kod, kal, false);
          r.iMin[k] = amper(p.i_min_kod, kal, true);
          r.iMaks[k] = amper(p.i_maks_kod, kal, true);
        }
      }
      r.wOrt[k] = p.w_ort;
      r.wMin[k] = p.w_min;
      r.wMaks[k] = p.w_maks;
    }
    onceSeg = sg;
    onceKart = p.kart_ms;
    onceRel = rel;
  });
  return r;
}

/**
 * PT7: bayragin (or. KN_OCV) KESINTISIZ nokta dizileri -> x araliklari [[t0, t1], ...] (grafigin bandi).
 * Nokta kendi araliginin SONUNDA damgali (kart_ms = noktanin bittigi an): dizinin ilk noktasi k ise
 * t0 = t[k - 1] (onceki noktanin bittigi an); oturumun ilk noktasiysa t0 = t[0] - ilkPayMs (hiz_ms;
 * pil oturumunda ~0 = BASLA). t1 = dizinin son noktasi. t azalmayan olmali (grafik x'i); NaN t'li
 * nokta diziyi KESER. Bayragi tasimayan oturumda bos dizi.
 */
export function bayrakAraliklari(t, bayrak, bit, ilkPayMs = 0) {
  const l = [];
  const n = Math.min(t ? t.length : 0, bayrak ? bayrak.length : 0);
  let bas = -1;
  const kapat = (son) => {
    if (bas < 0) return;
    const t0 = bas > 0 ? t[bas - 1] : t[0] - (Number.isFinite(ilkPayMs) && ilkPayMs > 0 ? ilkPayMs : 0);
    if (Number.isFinite(t0) && t[son] > t0) l.push([t0, t[son]]);
    bas = -1;
  };
  for (let k = 0; k < n; k++) {
    const var_ = (bayrak[k] & bit) !== 0 && Number.isFinite(t[k]);
    if (var_ && bas < 0) bas = k;
    if (!var_) kapat(k - 1);
  }
  kapat(n - 1);
  return l;
}

/** W1/Y7: olcum sirasi -> o siradan HEMEN ONCE biten yakalamanin skoplar anahtari
 *  (kayit.js skopYerleri `sonra`; ayni satira iki yakalama duserse ZAMANCA ilki). yerler:
 *  onceden hesaplanmis skopYerleri(oturum) (verilmezse burada hesaplanir). */
export function skopSonralari(oturum, yerler = null) {
  const m = new Map();
  for (const y of yerler || skopYerleri(oturum)) if (y.sonra !== null && !m.has(y.sonra)) m.set(y.sonra, y.sira);
  return m;
}

/** Ornek sirasi -> kaydin KA bayragi (yalniz o ornegi SAGLAYAN kaydin ILK ornegiyse). */
function ayrintiKayitBayraklari(oturum) {
  const m = new Map();
  const gorulen = new Set();
  for (const r of [...oturum.ayrinti].sort((x, y) => x.sira - y.sira)) {
    r.ornekler.forEach((_, j) => {
      const s = r.ilk + j;
      if (gorulen.has(s)) return;
      gorulen.add(s);
      if (j === 0 && r.bayrak) m.set(s, r.bayrak);
    });
  }
  return m;
}

const US_SARMA = IKI32 * 1000;

/**
 * Ayrintili oturumun ornek serileri (ornek sirasiyla). Diziler: sira, acilis, devam, kartUs,
 * ornekBayrak, kayitBayrak, skop: Array; relUs, gecenUs, unixUs (bilinmeyen NaN), relMs:
 * Float64Array; v, i, w: Float64Array (KAO_V_HATA -> v NaN, KAO_I_HATA -> i NaN; w = HIZALI guc,
 * kayit.js ayrintiGuc — V x I DEGIL). skop: yakalamadan sonraki ilk ornekte o yakalamanin
 * skoplar anahtari, digerlerinde 0. yerler: kayit.js skopYerleri (rapor/gorunum yeniden
 * hesaplamasin). araliklar ms. W1 inceleme: sirali ornek listesi (ayrintiOrnekler(o, true)) BIR kez kurulur,
 * hizali guce ve yakalama yerine gecirilir — ~1.9 M ornekte her biri yeniden kurunca yigin 1 GB'i
 * asiyordu (disari.test W1-bellek).
 */
export function ayrintiSerileri(oturum, secenek = {}) {
  const eksen = secenek.eksen || zamanEkseni(oturum, secenek.kayitlar || null);
  const orn = ayrintiOrnekler(oturum, true);
  const n = orn.length;
  const kal = oturum.basla ? oturum.basla.kal : null;
  const kb = ayrintiKayitBayraklari(oturum);
  const f = () => new Float64Array(n).fill(NaN);
  const r = {
    adet: n, eksen, araliklar: [], sira: [], acilis: [], devam: [], kartUs: [], ornekBayrak: [],
    kayitBayrak: [], skop: [], relUs: new Float64Array(n), relMs: new Float64Array(n), gecenUs: f(),
    unixUs: f(), v: f(), i: f(), w: ayrintiGuc(oturum, { orn, dizi: true }),   // k. eleman = orn'un k. ornegi
    yerler: skopYerleri(oturum, orn),
  };
  const sonralar = skopSonralari(oturum, r.yerler);
  let onceSeg = 0;
  orn.forEach(([s, us, vk, ik, b, ac], k) => {
    const seg = eksen.segmentler[ac] || eksen.segmentler[eksen.segmentler.length - 1];
    let rel = seg.kartMs === null ? 0 : us - seg.kartMs * 1000;
    rel = ((rel % US_SARMA) + US_SARMA) % US_SARMA;
    if (rel >= US_SARMA / 2) rel -= US_SARMA;
    r.sira.push(s);
    r.acilis.push(ac);
    r.devam.push(ac > 0 && (k === 0 || ac !== onceSeg) ? 1 : 0);
    r.kartUs.push(us);
    r.ornekBayrak.push(b);
    r.kayitBayrak.push(kb.get(s) || 0);
    r.skop.push(sonralar.get(s) || 0);
    r.relUs[k] = rel;
    r.relMs[k] = rel / 1000;
    if (seg.ofsetMs !== null) r.gecenUs[k] = seg.ofsetMs * 1000 + rel;
    if (seg.unixMs !== null) r.unixUs[k] = seg.unixMs * 1000 + rel;
    const a = r.araliklar[ac];
    if (!a) r.araliklar[ac] = [rel / 1000, rel / 1000];
    else { a[0] = Math.min(a[0], rel / 1000); a[1] = Math.max(a[1], rel / 1000); }
    if (kal) {
      if (!(b & KAO_V_HATA)) r.v[k] = volt(vk, kanalSec(kal, b & KAO_YUKSEK), true);
      if (!(b & KAO_I_HATA) && kal.sont_ohm !== 0) r.i[k] = amper(ik, kal, true);
    }
    onceSeg = ac;
  });
  return r;
}

// ── notlar ──────────────────────────────────────────────────────────────────────
/**
 * Notlari satirlara yerlestir (dosya basindaki NOT HUCRESI kurali). satirlar: {acilis[],
 * relMs (dizi), kartMs (dizi, ms)}. Donus Map(satir indisi -> [metin, ...]).
 */
function notYerlestir(oturum, eksen, araliklar, satirlar) {
  const m = new Map();
  const adet = satirlar.acilis.length;
  if (!adet) return m;
  const ekle = (k, metin) => {
    if (!m.has(k)) m.set(k, []);
    m.get(k).push(metin);
  };
  const notlar = [...oturum.notlar.entries()].sort((x, y) => x[0] - y[0]);
  for (const [, nt] of notlar) {
    if (!nt.nokta_ms) {
      ekle(0, nt.metin);
      continue;
    }
    const z = anZamani(eksen, araliklar, nt.nokta_ms, null);
    let yer = -1;
    if (z.acilis !== null) {
      let sonSeg = -1;
      for (let k = 0; k < adet; k++) {
        if (satirlar.acilis[k] !== z.acilis) continue;
        sonSeg = k;
        if (satirlar.relMs[k] >= z.relMs) { yer = k; break; }
      }
      if (yer < 0) yer = sonSeg;
    }
    if (yer < 0) {
      for (let k = 0; k < adet; k++) if (satirlar.kartMs[k] >= nt.nokta_ms) { yer = k; break; }
    }
    if (yer < 0) yer = adet - 1;
    ekle(yer, nt.metin);
  }
  return m;
}

// ── CSV ─────────────────────────────────────────────────────────────────────────
function zamanHucreleri(y, gecenMs, unixMs) {
  const u = Number.isFinite(unixMs) ? unixMs : null;
  return [
    y.tam(Number.isFinite(gecenMs) ? gecenMs : null),
    u === null ? "" : y.olcekli(u, BASAMAK.unix_s),
    u === null ? "" : y.metin(isoYaz(u)),
  ];
}

function noktaHucreleri(y, s, k) {
  return [
    y.tam(s.n[k]),
    y.sayi(s.vOrt[k], BASAMAK.V), y.sayi(s.vMin[k], BASAMAK.V), y.sayi(s.vMaks[k], BASAMAK.V),
    y.sayi(s.iOrt[k], BASAMAK.A), y.sayi(s.iMin[k], BASAMAK.A), y.sayi(s.iMaks[k], BASAMAK.A),
    y.sayi(s.wOrt[k], BASAMAK.W), y.sayi(s.wMin[k], BASAMAK.W), y.sayi(s.wMaks[k], BASAMAK.W),
  ];
}

/** Bayrak adlari + (yakalamadan sonraki ilk satirsa) PC'nin "SKOP" adi, '|' ile. */
function adlarSkop(adlar, skop, dil) {
  if (!skop) return adlar;
  const s = ceviri(SKOP_BAYRAK_AD, dil);
  return adlar ? adlar + "|" + s : s;
}

function notHucre(y, notlar, k) {
  const n = notlar.get(k);
  return n ? y.metin(n.join("\n")) : "";
}

/**
 * Nokta oturumu -> CSV metni (BOM dahil). secenek: bicim (BICIM_EXCEL_TR varsayilan) +
 * kayitlar (DEVAM'li oturumda OLAY/SKOP icin; burada yalniz notlar icin anlamsiz).
 */
export function oturumCsv(oturum, secenek = {}) {
  const y = yazici(secenek);
  const s = noktaSerileri(oturum, secenek);
  const notlar = notYerlestir(oturum, s.eksen, s.araliklar, s);
  let c = y.bas() + y.baslik(KOLONLAR.nokta);
  for (let k = 0; k < s.adet; k++) {
    c += y.satir([
      y.tam(s.sira[k]), y.tam(s.acilis[k]), y.tam(s.devam[k]), y.tam(s.kartMs[k]),
      ...zamanHucreleri(y, s.gecenMs[k], s.unixMs[k]),
      ...noktaHucreleri(y, s, k),
      y.tam(s.bayrak[k]), y.metin(adlarSkop(bayrakAdlari(s.bayrak[k], BAYRAKLAR.nokta, y.b.dil), s.skop[k], y.b.dil)),
      notHucre(y, notlar, k),
    ]);
  }
  return c;
}

/** Ayrintili (her ornek) oturum -> CSV metni. */
export function ayrintiCsv(oturum, secenek = {}) {
  const y = yazici(secenek);
  const s = ayrintiSerileri(oturum, secenek);
  const kartMs = s.kartUs.map((u) => u / 1000);
  const notlar = notYerlestir(oturum, s.eksen, s.araliklar, { acilis: s.acilis, relMs: s.relMs, kartMs });
  const ht = hatSutun(y, hatDuzeltV(oturum, s.kartUs.map((u) => Math.floor(u / 1000)), s.v, s.i, s.w));   // HT3: olay yoksa sutun YOK
  let c = y.bas() + baslikEk(y.baslik(KOLONLAR.ayrinti), ht.baslik, y.b.satirSonu);
  for (let k = 0; k < s.adet; k++) {
    const g = s.gecenUs[k];
    const u = s.unixUs[k];
    const ms = Number.isFinite(u) ? ciftBol(u, 1000) : null;
    const adlar = adlarSkop([bayrakAdlari(s.ornekBayrak[k], BAYRAKLAR.ornek, y.b.dil),
      bayrakAdlari(s.kayitBayrak[k], BAYRAKLAR.kayit, y.b.dil)].filter((x) => x).join("|"), s.skop[k], y.b.dil);
    c += satirEk(y.satir([
      y.tam(s.sira[k]), y.tam(s.acilis[k]), y.tam(s.devam[k]), y.tam(s.kartUs[k]),
      Number.isFinite(g) ? y.olcekli(g, BASAMAK.ayrinti_ms) : "",
      ms === null ? "" : y.olcekli(ms, BASAMAK.unix_s),
      ms === null ? "" : y.metin(isoYaz(ms)),
      y.sayi(s.v[k], BASAMAK.V), y.sayi(s.i[k], BASAMAK.A), y.sayi(s.w[k], BASAMAK.W),
      y.tam(s.ornekBayrak[k]), y.tam(s.kayitBayrak[k]), y.metin(adlar),
      notHucre(y, notlar, k),
    ]), ht.hucre(k), y.b.satirSonu);
  }
  return c;
}

/** Neumaier telafili toplam — istatistik.js enerji() ile AYNI toplama sirasi ve sonuc. */
class Toplam {
  constructor() { this.s = 0; this.d = 0; }
  ekle(x) {
    const s = this.s + x;
    if (Math.abs(this.s) >= Math.abs(x)) this.d += (this.s - s) + x;
    else this.d += (x - s) + this.s;
    this.s = s;
  }
  get deger() { return this.s + this.d; }
}

/**
 * Birikimli yamuk integrali — istatistik.enerji ile AYNI kural ve aritmetik: acilis basina
 * ayri (acilislar arasinda integral YOK), gecerli (NaN'siz) ardisik iki nokta arasi
 * dt <= bosluk ise (a_once + a) * dt / 2, Neumaier toplam, acilis toplami SONDA bolen'e
 * bolunur ve acilis toplamlari sirayla eklenir (rapor.js'in enerji toplamiyla son satirda
 * bit bit ayni). Donus Float64Array: her satirda o satira kadarki toplam.
 */
function birikimli(relMs, acilis, a, bosluk, bolen) {
  const n = relMs.length;
  const cikti = new Float64Array(n);
  let toplam = new Toplam();
  let devir = 0;
  let var_ = false;
  let tOnce = 0;
  let aOnce = 0;
  let seg = null;
  for (let k = 0; k < n; k++) {
    if (acilis[k] !== seg) {
      if (seg !== null) devir += toplam.deger / bolen;
      toplam = new Toplam();
      var_ = false;
      seg = acilis[k];
    }
    const x = a[k];
    if (x === x) {
      if (var_) {
        const dt = relMs[k] - tOnce;
        if (dt <= bosluk) toplam.ekle((aOnce + x) * dt / 2);
      }
      var_ = true;
      tOnce = relMs[k];
      aOnce = x;
    }
    cikti[k] = devir + toplam.deger / bolen;
  }
  return cikti;
}

/** Nokta oturumunun bosluk esigi (ms): hiz_ms x 2.5; hiz bilinmiyorsa sonsuz. PT4: her ornek PIL oturumunda
 *  (hiz_ms 0) noktalar PIL_AYR_NOKTA_MS'de bir — esik onun 2.5 kati. */
export function noktaBoslukMs(oturum) {
  const h = noktaAralikMs(oturum);
  return h > 0 ? h * NOKTA_BOSLUK_KAT : Infinity;
}

/** Noktalarin araligi (ms): BASLA hiz_ms; her ornek PIL oturumunda (hiz_ms 0) PIL_AYR_NOKTA_MS; bilinmiyorsa 0. */
export function noktaAralikMs(oturum) {
  const b = oturum.basla;
  if (!b) return 0;
  return b.hiz_ms > 0 ? b.hiz_ms : b.oturum_turu === OTURUM_PIL ? PIL_AYR_NOKTA_MS : 0;
}

// ── HT3: hat direnci telafisi ─────────────────────────────────────────────────────
/** HT3 CSV sutunlari (yalniz KO_PIL_HAT olayli oturumda, tablonun SONUNDA). */
export const HT_KOLON = Object.freeze({ tr: Object.freeze(["v_pil_V", "w_pil_W", "hat_mohm"]),
  en: Object.freeze(["v_cell_V", "p_cell_W", "lead_mohm"]) });

/**
 * HT3: PIL oturumunda pil kutuplarindaki gerilim — satir basina (kartMs: satirin kart_ms'i; ayrintili ornekte us // 1000)
 * o ANDA gecerli hat direnciyle V + I x R. R kayit.js pilHatMohmAt ile AYNI kural (kayit sirasiyla zamani <= an olan SON
 * KO_PIL_HAT; yoksa 0) — burada olaylar BIR kez suzulur (her ornekte siralama yok); gerilim pilVDuzelt (R = 0 iken HAM
 * AYNEN). Olay YOKSA ya da PIL oturumu degilse null: cagiran HAM'i kullanir (grafik / CSV / rapor bugunku gibi).
 * w verilirse pilin VERDIGI guc pilWDuzelt (w + I^2 x R; kartin pil Wh kurali) da: donus w (yoksa null).
 * Donus {v, w: Float64Array | null, mohm: Float64Array, ozet: {ilk (ilk satirdaki R), son (son olayin R'si), degisim}}.
 */
export function hatDuzeltV(oturum, kartMs, v, i, w = null) {
  if (!oturum.basla || oturum.basla.oturum_turu !== OTURUM_PIL) return null;   // olcum / skop oturumu: HAM
  const l = oturum.olaylar.filter((o) => o.tur === KO_PIL_HAT && "hat_mohm" in o).sort((a, b) => a.sira - b.sira);
  if (!l.length) return null;
  const n = v.length;
  const vd = new Float64Array(n);
  const wd = w ? new Float64Array(n) : null;
  const mohm = new Float64Array(n);
  const an = (t) => {
    let r = 0;
    for (const o of l) if (fark32(t, o.kart_ms) >= 0) r = o.hat_mohm;
    return r;
  };
  for (let k = 0; k < n; k++) {
    mohm[k] = an(kartMs[k]);
    vd[k] = pilVDuzelt(v[k], i[k], mohm[k]);
    if (wd) wd[k] = pilWDuzelt(w[k], i[k], mohm[k]);
  }
  /* ozet: ilk satirdaki R; o andan SONRAKI olaylarda deger kac kez degisti (test basindaki olay degisim sayilmaz) */
  const ilk = n ? mohm[0] : 0;
  let r = ilk;
  let degisim = 0;
  for (const o of l) {
    if (n && fark32(kartMs[0], o.kart_ms) >= 0) continue;
    if (o.hat_mohm !== r) degisim++;
    r = o.hat_mohm;
  }
  return { v: vd, w: wd, mohm, ozet: { ilk, son: l[l.length - 1].hat_mohm, degisim } };
}

/** HT3: CSV'nin ek basligi ve satir hucreleri (olay yoksa bos: tablo degismez). */
function hatSutun(y, h) {
  if (!h) return { baslik: "", hucre: () => "", bos: "" };
  const a = y.b.ayrac;
  return {
    baslik: a + (HT_KOLON[y.b.dil] || HT_KOLON.tr).map((s) => y.metin(s)).join(a),
    hucre: (k) => a + y.sayi(h.v[k], BASAMAK.V) + a + y.sayi(h.w[k], BASAMAK.W) + a + y.tam(h.mohm[k]),
    bos: a + a + a,
  };
}

/** Basliga ek sutun (satir sonundan once). */
function baslikEk(baslik, ek, satirSonu) {
  return ek ? baslik.slice(0, baslik.length - satirSonu.length) + ek + satirSonu : baslik;
}

/** Satira ek hucreler (satir sonundan once). */
function satirEk(satir, ek, satirSonu) {
  return ek ? satir.slice(0, satir.length - satirSonu.length) + ek + satirSonu : satir;
}

/**
 * Pil oturumu -> CSV metni: nokta satirlari + DCIR satirlari zaman sirasinda (dosya basi).
 * mAh = ∫A dt, Wh = ∫W dt (kartin W'si), birikimli, bosluk ve acilis siniri haric.
 */
export function pilCsv(oturum, secenek = {}) {
  const y = yazici(secenek);
  const s = noktaSerileri(oturum, secenek);
  const hd = hatDuzeltV(oturum, s.kartMs, s.vOrt, s.iOrt, s.wOrt);   // HT3: olay yoksa null -> sutun YOK, Wh HAM
  const ht = hatSutun(y, hd);
  const notlar = notYerlestir(oturum, s.eksen, s.araliklar, s);
  const bosluk = noktaBoslukMs(oturum);
  // mAh: gecerli ornek = v ve i NaN degil (istatistik.enerji ile ayni kosul)
  const iMaskeli = s.iOrt.map((x, k) => (s.vOrt[k] === s.vOrt[k] ? x : NaN));
  const mah = birikimli(s.relMs, s.acilis, iMaskeli, bosluk, AMS_MAH);
  const wh = birikimli(s.relMs, s.acilis, hd ? hd.w : s.wOrt, bosluk, MS_SAAT);
  const dcir = oturum.olaylar.filter((o) => o.tur === KO_DCIR && "no" in o)
    .sort((a, b) => a.sira - b.sira)
    .map((o) => ({ o, z: anZamani(s.eksen, s.araliklar, o.kart_ms, o.sira) }));
  const nokta = (k) => satirEk(y.satir([
    y.metin(ceviri("csv.kayit.nokta", y.b.dil)),
    y.tam(s.sira[k]), y.tam(s.acilis[k]), y.tam(s.devam[k]), y.tam(s.kartMs[k]),
    ...zamanHucreleri(y, s.gecenMs[k], s.unixMs[k]),
    ...noktaHucreleri(y, s, k),
    y.sayi(mah[k], BASAMAK.mAh), y.sayi(wh[k], BASAMAK.Wh),
    "", "", "", "", "", "", "", "", "",
    y.tam(s.bayrak[k]), y.metin(adlarSkop(bayrakAdlari(s.bayrak[k], BAYRAKLAR.nokta, y.b.dil), s.skop[k], y.b.dil)),
    notHucre(y, notlar, k),
  ]), ht.hucre(k), y.b.satirSonu);
  const olay = ({ o, z }) => satirEk(y.satir([
    y.metin(ceviri("csv.kayit.dcir", y.b.dil)),
    "", y.tam(z.acilis), "", y.tam(o.kart_ms),
    ...zamanHucreleri(y, z.gecenMs, z.unixMs),
    "", "", "", "", "", "", "", "", "", "",
    "", "",
    y.tam(o.no), y.sayi(o.v_once, BASAMAK.V), y.sayi(o.i_once, BASAMAK.A),
    y.sayi(o.v_ani, BASAMAK.V), y.sayi(o.v_oturmus, BASAMAK.V),
    y.sayi(o.r_ani, BASAMAK.ohm), y.sayi(o.r_oturmus, BASAMAK.ohm),
    y.sayi(o.mah, BASAMAK.mAh), y.sayi(o.wh, BASAMAK.Wh),
    "", "", "",
  ]), ht.bos, y.b.satirSonu);
  let c = y.bas() + baslikEk(y.baslik(KOLONLAR.pil), ht.baslik, y.b.satirSonu);
  let j = 0;
  const once = (d, k) => d.z.acilis !== null
    && (d.z.acilis < s.acilis[k] || (d.z.acilis === s.acilis[k] && d.z.relMs < s.relMs[k]));
  for (let k = 0; k < s.adet; k++) {
    while (j < dcir.length && once(dcir[j], k)) c += olay(dcir[j++]);
    c += nokta(k);
  }
  while (j < dcir.length) c += olay(dcir[j++]);
  return c;
}

/**
 * Tek osiloskop yakalamasi (oturum.skoplar'in bir degeri) -> CSV metni; eksik yakalama
 * (tam degil) -> null. t_s = (i - tetik) / hz (hz 0 -> bos), v_V = kod * adim - ofset.
 */
export function skopCsv(yakalama, secenek = {}) {
  const y = yazici(secenek);
  if (!yakalama || !yakalama.tam || !yakalama.meta) return null;
  const m = yakalama.meta;
  let c = y.bas() + y.baslik(KOLONLAR.skop);
  yakalama.kodlar.forEach((kod, i) => {
    c += y.satir([
      y.tam(i), m.hz > 0 ? y.sayi((i - m.tetik) / m.hz, BASAMAK.skop_t_s) : "",
      y.tam(kod), y.sayi(kod * m.adim - m.ofset, BASAMAK.V),
    ]);
  });
  return c;
}

// ── ham ─────────────────────────────────────────────────────────────────────────
/**
 * Oturumun HAM kayitlari: kayit basliginda oturumNo olanlar + hedefi oturumNo olan NOT'lar
 * (baslikta oturum 0). Kayit sirasiyla, ayni sira bir kez (ilki). Uint8Array: kayitPaketle
 * ile yeniden cerceveli art arda kayitlar — kartin akisindaki baytlarla ayni (dolgu sifir).
 */
export function hamDisari(kayitlar, oturumNo) {
  if (!Number.isInteger(oturumNo) || oturumNo <= 0) throw new RangeError(`oturumNo > 0 tamsayi olmali (${oturumNo})`);
  const secilen = [];
  const gorulen = new Set();
  const sirali = kayitlar.map((k, i) => [k, i]).sort((a, b) => a[0].sira - b[0].sira || a[1] - b[1]);
  for (const [k] of sirali) {
    let bu = k.oturum === oturumNo;
    if (!bu && k.tur === T_NOT && k.oturum === 0 && k.yuk.length >= 4) {
      bu = new DataView(k.yuk.buffer, k.yuk.byteOffset, 4).getUint32(0, true) === oturumNo;
    }
    if (!bu || gorulen.has(k.sira)) continue;
    gorulen.add(k.sira);
    secilen.push(kayitPaketle(k.tur, k.sira, k.oturum, k.yuk));
  }
  let n = 0;
  for (const p of secilen) n += p.length;
  const b = new Uint8Array(n);
  let a = 0;
  for (const p of secilen) {
    b.set(p, a);
    a += p.length;
  }
  return b;
}
