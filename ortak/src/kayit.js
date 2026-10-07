// B73 / 2A — KAYIT BICIMI cozucusu: kopru/kayit_bicim.py'nin (kartla dogrulanmis
// basvuru) JS karsiligi. Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md.
//
// Ad eslemesi: Python islevi snake_case -> JS camelCase (akis_coz -> akisCoz,
// oturumlari_kur -> oturumlariKur). Veri alanlari kayit_bicim.h / Python'daki
// adlariyla kalir (kart_ms, v_ort_kod, ...).
// Tur eslemesi: tuple -> dizi, dataclass/dict -> nesne, dict[int, ...] -> Map,
// bytes -> Uint8Array, None -> null. Python'un struct.error / ValueError ile
// reddettigi girdi burada KayitHatasi firlatir; paketleyicilerde RangeError.
//
// Yalniz DataView / Uint8Array / TextDecoder: tarayici, Node ve Capacitor ayni
// dosyayi yukler. Bagimlilik yok.

export const SURUM = 2;              // 1B: BASLA'da kal_no; surum 1 (98 B) okunur
export const IMZA = 0xA5;
export const BASLIK_BAYT = 16;
export const NOKTA_BAYT = 36;
export const BASLA_BAYT = 102;
export const BASLA_V1_BAYT = 98;
export const KAL_BAYT = 62;

export const T_BASLA = 1, T_NOKTA = 2, T_DEVAM = 3, T_BITIR = 4, T_SAAT = 5, T_TEKRAR = 6;
export const T_OLAY = 7, T_NOT = 8;
export const T_AYRINTI = 9;
export const T_SKOP = 10;
export const KA_KAYIP_ONCE = 0x01, KA_SILME = 0x02;
export const KAO_YUKSEK = 0x1, KAO_V_HATA = 0x2, KAO_I_HATA = 0x4, KAO_V_DOYDU = 0x8;
export const KN_YUKSEK = 0x01, KN_V_HATA = 0x02, KN_I_HATA = 0x04;
export const KN_V_DOYDU = 0x08, KN_DURAKLAMA = 0x10, KN_KAYIP_ONCE = 0x20;
export const KN_DCIR = 0x40;
export const KN_OCV = 0x80;          // PT2: nokta pil testinin OCV on evresinde (yuk KAPALI, ilk 5 s)
// PT4: PIL oturumunda hiz_ms 0 = her ornek: AYRINTI kayitlari ARTI bu aralikla NOKTA kayitlari (ikisi ayni
// sira uzayinda; o.ayrinti VE o.noktalar dolu). PIL_AYAR'da kayit_hz 0 = her ornek, dcir_aralik_ms 0 = DCIR KAPALI.
export const PIL_AYR_NOKTA_MS = 1000;
export const SEBEP = new Map([
  [1, "kullanici"], [2, "bellek doldu"], [3, "hata"], [4, "pil testi bitti"],
  [5, "kart yeniden basladi"], [6, "baska oturum basladi"], [7, "planli sure doldu"],
]);
export const OTURUM_OLCUM = 1;
export const OTURUM_PIL = 2;
export const OTURUM_SKOP = 3;
export const KO_PIL_AYAR = 1, KO_DCIR = 2, KO_PIL_SONUC = 3;
export const KO_SKOP_KAL = 4;
export const KO_PLAN = 5;
export const KNT_AD = 1, KNT_ETIKET = 2, KNT_NOT = 3;
export const NOT_METIN = 120;
export const KAL_BICIM = 1;
export const ADS_SAYIM = 32768.0;

/** Python'un struct.error / ValueError'una karsilik: bicime uymayan girdi. */
export class KayitHatasi extends Error {
  constructor(mesaj) {
    super(mesaj);
    this.name = "KayitHatasi";
  }
}

// ── kucuk struct motoru: bicim dizgeleri Python'dakiyle AYNI ("<" + B b H h I i f x Ns)
const BOYUT = { B: 1, b: 1, H: 2, h: 2, I: 4, i: 4, f: 4 };

function yapi(bicim) {
  if (bicim[0] !== "<") throw new Error("yalniz '<' bicimi: " + bicim);
  const alanlar = [];
  let ofset = 0;
  let i = 1;
  while (i < bicim.length) {
    let sayi = "";
    while (bicim[i] >= "0" && bicim[i] <= "9") sayi += bicim[i++];
    const h = bicim[i++];
    const n = sayi === "" ? 1 : Number(sayi);
    if (h === "x") {
      ofset += n;
    } else if (h === "s") {
      alanlar.push({ h, ofset, n });
      ofset += n;
    } else if (h in BOYUT) {
      for (let k = 0; k < n; k++) {
        alanlar.push({ h, ofset });
        ofset += BOYUT[h];
      }
    } else {
      throw new Error("bilinmeyen bicim harfi: " + h);
    }
  }
  return { bicim, alanlar, boyut: ofset };
}

function gorunum(y) {
  return new DataView(y.buffer, y.byteOffset, y.byteLength);
}

function alanOku(v, y, a, f) {
  switch (f.h) {
    case "B": return v.getUint8(a);
    case "b": return v.getInt8(a);
    case "H": return v.getUint16(a, true);
    case "h": return v.getInt16(a, true);
    case "I": return v.getUint32(a, true);
    case "i": return v.getInt32(a, true);
    case "f": return v.getFloat32(a, true);
    case "s": return new Uint8Array(y.subarray(a, a + f.n));
  }
  throw new Error("bicim harfi: " + f.h);
}

/** struct.unpack_from: a negatifse sondan sayilir (Python ile ayni). */
function oku(y, a, yp) {
  let b = a;
  if (b < 0) b += y.length;
  if (b < 0 || y.length - b < yp.boyut) {
    throw new KayitHatasi(`${yp.bicim}: ${y.length} baytlik tamponda ${a}'dan ${yp.boyut} bayt yok`);
  }
  const v = gorunum(y);
  return yp.alanlar.map((f) => alanOku(v, y, b + f.ofset, f));
}

/** struct.unpack: uzunluk TAM tutmali. */
function cozTam(y, yp) {
  if (y.length !== yp.boyut) {
    throw new KayitHatasi(`${yp.bicim}: ${yp.boyut} bayt bekleniyordu, ${y.length} geldi`);
  }
  return oku(y, 0, yp);
}

const ARALIK = {
  B: [0, 0xFF], b: [-0x80, 0x7F], H: [0, 0xFFFF], h: [-0x8000, 0x7FFF],
  I: [0, 0xFFFFFFFF], i: [-0x80000000, 0x7FFFFFFF],
};

function tamsayiYaz(v, a, h, x) {
  const [alt, ust] = ARALIK[h];
  if (!Number.isInteger(x) || x < alt || x > ust) {
    throw new RangeError(`'${h}' alanina sigmaz: ${x}`);
  }
  switch (h) {
    case "B": v.setUint8(a, x); return;
    case "b": v.setInt8(a, x); return;
    case "H": v.setUint16(a, x, true); return;
    case "h": v.setInt16(a, x, true); return;
    case "I": v.setUint32(a, x, true); return;
    case "i": v.setInt32(a, x, true); return;
  }
}

function float32Yaz(v, a, x) {
  if (typeof x !== "number") throw new RangeError(`'f' alani sayi degil: ${x}`);
  if (Number.isFinite(x) && !Number.isFinite(Math.fround(x))) {
    throw new RangeError("float too large to pack with f format");   // Python OverflowError
  }
  v.setFloat32(a, x, true);
}

/** struct.pack */
function paketle(yp, degerler) {
  if (degerler.length !== yp.alanlar.length) {
    throw new RangeError(`${yp.bicim}: ${yp.alanlar.length} deger bekleniyordu, ${degerler.length} geldi`);
  }
  const b = new Uint8Array(yp.boyut);
  const v = gorunum(b);
  yp.alanlar.forEach((f, k) => {
    const x = degerler[k];
    if (f.h === "f") {
      float32Yaz(v, f.ofset, x);
    } else if (f.h === "s") {
      if (!(x instanceof Uint8Array)) throw new RangeError("'s' alani bayt dizisi olmali");
      b.set(x.subarray(0, f.n), f.ofset);                 // kisa: NUL dolgu, uzun: kirpilir
    } else {
      tamsayiYaz(v, f.ofset, f.h, x);
    }
  });
  return b;
}

function bayt(x) {
  if (x instanceof Uint8Array) return x;
  if (x instanceof ArrayBuffer) return new Uint8Array(x);
  if (ArrayBuffer.isView(x)) return new Uint8Array(x.buffer, x.byteOffset, x.byteLength);
  throw new TypeError("bayt dizisi bekleniyordu (Uint8Array / ArrayBuffer)");
}

function birlestir(parcalar) {
  let n = 0;
  for (const p of parcalar) n += p.length;
  const b = new Uint8Array(n);
  let a = 0;
  for (const p of parcalar) {
    b.set(p, a);
    a += p.length;
  }
  return b;
}

const S_BASLIK = yapi("<BBHII");            // imza, tur, yuk_bayt, sira, oturum
const S_KAYIT_BAS = yapi("<BBHIII");        // + crc
const S_U32 = yapi("<I");
const S_NOKTA = yapi("<IHBxfhhfhhfff");
const S_KANAL = yapi("<fffhf");
const S_AKIM = yapi("<hffffff");
const S_BASLA_BAS = yapi("<BBHIIII16s");
const S_DEVAM = yapi("<IIII");
const S_BITIR = yapi("<IB3x");
const S_SAAT = yapi("<III");
const S_OLAY_BAS = yapi("<B3xI");           // olay_tur, kart_ms
const OLAY = new Map([                      // tur -> [yapi, alan adlari]
  [KO_PIL_AYAR, [yapi("<ffIIIf"),
    ["kesme_v", "ocv", "azami_s", "dcir_aralik_ms", "dcir_ms", "kayit_hz"]]],
  [KO_DCIR, [yapi("<Iffffffff"),
    ["no", "v_once", "i_once", "v_ani", "v_oturmus", "r_ani", "r_oturmus", "mah", "wh"]]],
  [KO_PIL_SONUC, [yapi("<BBxxffffII"),
    ["durum", "hata", "mah", "wh", "ocv", "v_son", "sure_ms", "dcir_sayisi"]]],
  [KO_SKOP_KAL, [yapi("<17h"), ["mv"]]],    // tek alan: 17 elemanli liste
  [KO_PLAN, [yapi("<IIII"), ["bas_unix", "sure_s", "hiz_ms", "plan_no"]]],
]);
const S_NOT_BAS = yapi("<IB3xII");          // hedef, alan, nokta_ms, degistirir
const S_AYRINTI_BAS = yapi("<IIIHBx");      // ilk, t0_ms, t0_us, adet, bayrak
const S_AYRINTI_ORNEK = yapi("<hhH");       // v, i, (dt4 << 4 | bayrak)
const S_SKOP_BAS = yapi("<IHHHBx");         // no, ilk, adet, toplam, parca
const S_SKOP_META = yapi("<IIIIffHHH5Bx");
const SKOP_META_AD = ["t_ms", "sure_ms", "hz", "tdiv_us", "adim", "ofset", "tetik", "esik",
  "histerezis", "kip", "tetiklendi", "kenar", "on_yuzde", "onay"];

// Python'daki assert'lerin karsiligi: bicim kayarsa modul hic yuklenmez
function dogrula(kosul, ne) {
  if (!kosul) throw new Error("kayit.js boyut denetimi: " + ne);
}
dogrula(S_NOKTA.boyut === NOKTA_BAYT, "NOKTA");
dogrula([...OLAY.values()].map(([y]) => S_OLAY_BAS.boyut + y.boyut).join() === "32,44,36,42,24", "OLAY");
dogrula(S_SKOP_BAS.boyut === 12 && S_SKOP_META.boyut === 36, "SKOP");
dogrula(S_NOT_BAS.boyut === 16, "NOT");
dogrula(S_AYRINTI_BAS.boyut === 16 && S_AYRINTI_ORNEK.boyut === 6, "AYRINTI");
dogrula(2 * S_KANAL.boyut + S_AKIM.boyut === KAL_BAYT, "KAL");
dogrula(S_BASLA_BAS.boyut + KAL_BAYT === BASLA_V1_BAYT && BASLA_V1_BAYT + 4 === BASLA_BAYT, "BASLA");
dogrula(S_KAYIT_BAS.boyut === BASLIK_BAYT, "BASLIK");

/** Kaydin flasta kapladigi bayt: baslik + yuk, 4'un katina. */
export function toplamBayt(yukBayt) {
  return Math.floor((BASLIK_BAYT + yukBayt + 3) / 4) * 4;
}

const CRC_TABLO = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

/** zlib.crc32(veri, onceki) & 0xFFFFFFFF */
export function crc(veri, onceki = 0) {
  const b = bayt(veri);
  let c = (onceki ^ 0xFFFFFFFF) >>> 0;
  for (let i = 0; i < b.length; i++) c = CRC_TABLO[(c ^ b[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

// ── kayit ─────────────────────────────────────────────────────────────
// Kayit: { tur, sira, oturum, yuk: Uint8Array, adres }

export function kayitPaketle(tur, sira, oturum, yuk) {
  const y = bayt(yuk);
  const bas = paketle(S_BASLIK, [IMZA, tur, y.length, sira, oturum]);
  const c = crc(y, crc(bas));
  const ham = new Uint8Array(toplamBayt(y.length));
  ham.set(bas, 0);
  gorunum(ham).setUint32(12, c, true);
  ham.set(y, BASLIK_BAYT);
  return ham;
}

/** [durum, kayit]: 1 gecerli, 0 bos (0xFF), -1 cop ya da yarim. */
function kayitOku(veri, a, son) {
  if (a + BASLIK_BAYT > son) return [0, null];
  const b = veri.subarray(a, a + BASLIK_BAYT);
  if (b.length === BASLIK_BAYT && b.every((x) => x === 0xFF)) return [0, null];
  // son <= veri.length (flasCoz kirpar, S6): b burada hep 16 bayt
  const [imza, tur, n, sira, oturum, c] = cozTam(b, S_KAYIT_BAS);
  // bilinmeyen tur GECERLI (C ile ayni): ileride eklenen turler esitlemeyi kirmasin
  if (imza !== IMZA || tur === 0 || tur === 0xFF || sira === 0 || sira === 0xFFFFFFFF) {
    return [-1, null];
  }
  if (a + toplamBayt(n) > son) return [-1, null];
  const yuk = new Uint8Array(veri.subarray(a + BASLIK_BAYT, a + BASLIK_BAYT + n));
  if (crc(yuk, crc(b.subarray(0, 12))) !== c) return [-1, null];
  return [1, { tur, sira, oturum, yuk, adres: a }];
}

/** Akisin GECERLI on eki: ilk gecersiz/yarim kayitta durur. Donus [kayitlar, gecerli bayt]. */
export function akisOnek(veri) {
  const v = bayt(veri);
  const kayitlar = [];
  let a = 0;
  while (a < v.length) {
    const [d, k] = kayitOku(v, a, v.length);
    if (d !== 1) break;
    kayitlar.push(k);
    a += toplamBayt(k.yuk.length);
  }
  return [kayitlar, a];
}

/** Esitleme yaniti: art arda kayitlar. Tek bozuk kayit -> KayitHatasi. */
export function akisCoz(veri) {
  const v = bayt(veri);
  const kayitlar = [];
  let a = 0;
  while (a < v.length) {
    const [d, k] = kayitOku(v, a, v.length);
    if (d !== 1) throw new KayitHatasi(`${a}. baytta gecersiz kayit`);
    kayitlar.push(k);
    a += toplamBayt(k.yuk.length);
  }
  return kayitlar;
}

/** Flas goruntusu: her sektor bastan, ilk gecersiz kayitta o sektor biter.
 *  Donus [sira ile sirali kayitlar, cop/yarim gorulen sektor sayisi].
 *  S6: goruntu tam sektor olmak zorunda DEGIL. Son sektor goruntunun sonunda biter:
 *  < 16 B kuyruk (yarim baslik) sektor sonundaki < 16 B gibi BOS sayilir (bozuk degil);
 *  basligi tam ama yuku goruntuden tasan kayit yarim kayittir (bozuk +1). Firlatmaz. */
export function flasCoz(veri, sektor) {
  const v = bayt(veri);
  if (!Number.isInteger(sektor)) throw new TypeError("sektor tamsayi olmali");
  if (sektor === 0) throw new RangeError("sektor 0 olamaz");     // Python range(): ValueError
  const kayitlar = [];
  let bozuk = 0;
  for (let s = 0; sektor > 0 && s < v.length; s += sektor) {
    let a = s;
    let sonSira = 0;
    const son = Math.min(s + sektor, v.length);
    for (;;) {
      let [d, k] = kayitOku(v, a, son);
      if (d === 1 && k.sira <= sonSira) d = -1;
      if (d !== 1) {
        bozuk += d < 0 ? 1 : 0;
        break;
      }
      kayitlar.push(k);
      sonSira = k.sira;
      a += toplamBayt(k.yuk.length);
    }
  }
  kayitlar.sort((x, y) => x.sira - y.sira);   // kararli siralama (Python sort gibi)
  return [kayitlar, bozuk];
}

// ── nokta ─────────────────────────────────────────────────────────────
const NOKTA_AD = ["kart_ms", "n", "bayrak", "v_ort_kod", "v_min_kod", "v_maks_kod",
  "i_ort_kod", "i_min_kod", "i_maks_kod", "w_ort", "w_min", "w_maks"];

function nesne(adlar, degerler) {
  const d = {};
  adlar.forEach((ad, k) => { d[ad] = degerler[k]; });
  return d;
}

export function noktaPaketle(p) {
  return paketle(S_NOKTA, NOKTA_AD.map((a) => p[a]));
}

export function noktaCoz(b) {
  return nesne(NOKTA_AD, cozTam(bayt(b), S_NOKTA));
}

// ── BASLA ve kalibrasyon ──────────────────────────────────────────────
const KANAL_AD = ["n", "pga", "kazanc", "sifir_ham", "tau"];

export function kalPaketle(k) {
  return birlestir([
    paketle(S_KANAL, KANAL_AD.map((a) => k.normal[a])),
    paketle(S_KANAL, KANAL_AD.map((a) => k.yuksek[a])),
    paketle(S_AKIM, [k.i_ofset, k.i_pga, k.sont_ohm, k.i_duzeltme, k.sebeke_hz,
      k.faz_kal_us[0], k.faz_kal_us[1]]),
  ]);
}

export function kalCoz(y, a = 0) {
  const b = bayt(y);
  const normal = nesne(KANAL_AD, oku(b, a, S_KANAL));
  const yuksek = nesne(KANAL_AD, oku(b, a + S_KANAL.boyut, S_KANAL));
  const [io, ip, so, idz, sh, f0, f1] = oku(b, a + 2 * S_KANAL.boyut, S_AKIM);
  return { normal, yuksek, i_ofset: io, i_pga: ip, sont_ohm: so, i_duzeltme: idz,
    sebeke_hz: sh, faz_kal_us: [f0, f1] };
}

function asciiKodla(s) {
  const b = [];
  for (let i = 0; i < s.length; i++) {
    const c = s.charCodeAt(i);
    if (c > 0x7F) throw new RangeError("ascii disi karakter (Python UnicodeEncodeError)");
    b.push(c);
  }
  return Uint8Array.from(b);
}

export function baslaPaketle(b) {
  const surum = asciiKodla(b.surum).subarray(0, 16);
  return birlestir([
    paketle(S_BASLA_BAS, [b.oturum_turu, b.kal_bicim, SURUM, b.hiz_ms, b.unix_s, b.kart_ms,
      b.acilis, surum]),
    kalPaketle(b.kal),
    paketle(S_U32, [b.kal_no ?? 0]),
  ]);
}

/** bytes.rstrip(b"\0").decode("ascii", "replace") */
function surumCoz(s) {
  let n = s.indexOf(0);                     // C dizgisi: ILK NUL'da biter (sonrasi cop olabilir)
  if (n < 0) n = s.length;
  let m = "";
  for (let i = 0; i < n; i++) m += s[i] < 0x80 ? String.fromCharCode(s[i]) : "\ufffd";
  return m;
}

/** Surum 2 (102 B) ya da surum 1 (98 B; kal_no yok -> 0). */
export function baslaCoz(y) {
  const b = bayt(y);
  const [tur, kb, bs, hiz, unix, kms, acilis, surum] = oku(b, 0, S_BASLA_BAS);
  const kalNo = b.length >= BASLA_BAYT ? oku(b, BASLA_V1_BAYT, S_U32)[0] : 0;
  return { oturum_turu: tur, kal_bicim: kb, hiz_ms: hiz, unix_s: unix, kart_ms: kms,
    acilis, surum: surumCoz(surum), kal: kalCoz(b, S_BASLA_BAS.boyut),
    bicim_surum: bs, kal_no: kalNo };
}

// S5: DEVAM/BITIR/SAAT yuku bilinen boydan UZUNSA on ek cozulur (yeni firmware alan
// ekleyebilir — ileri uyumluluk); KISAYSA KayitHatasi (oturumlariKur onu atlar + uyarir).
export function devamCoz(y) {
  const [a, u, k, n] = oku(bayt(y), 0, S_DEVAM);
  return { acilis: a, unix_s: u, kart_ms: k, nokta_sira: n };
}

export function bitirCoz(y) {
  const [n, s] = oku(bayt(y), 0, S_BITIR);
  return { nokta_adedi: n, sebep: s };
}

export function saatCoz(y) {
  const [u, k, a] = oku(bayt(y), 0, S_SAAT);
  return { unix_s: u, kart_ms: k, acilis: a };
}

/** OLAY yuku (kayit_bicim.h kayit_olay_*_paketle ile ayni). */
export function olayPaketle(d) {
  const o = OLAY.get(d.tur);
  if (!o) throw new RangeError(`bilinmeyen olay turu: ${d.tur}`);    // Python KeyError
  const [yp, adlar] = o;
  const bas = paketle(S_OLAY_BAS, [d.tur, d.kart_ms]);
  if (adlar.length === 1 && adlar[0] === "mv") return birlestir([bas, paketle(yp, d.mv)]);
  return birlestir([bas, paketle(yp, adlar.map((a) => d[a]))]);
}

/** OLAY yuku -> {tur, kart_ms, ...alanlar}. Bilinmeyen (ya da kisa) olay: {tur, kart_ms, ham}. */
export function olayCoz(y) {
  const b = bayt(y);
  const [t, ms] = oku(b, 0, S_OLAY_BAS);
  const d = { tur: t, kart_ms: ms };
  const o = OLAY.get(t);
  if (o && b.length >= S_OLAY_BAS.boyut + o[0].boyut) {
    const [yp, adlar] = o;
    const deg = oku(b, S_OLAY_BAS.boyut, yp);
    if (adlar.length === 1 && adlar[0] === "mv") d.mv = deg;
    else adlar.forEach((a, k) => { d[a] = deg[k]; });
  } else {
    d.ham = new Uint8Array(b.subarray(S_OLAY_BAS.boyut));
  }
  return d;
}

/** NOT yuku. `metin` kartin TEMIZLEDIGI bayt dizisi (burada temizlenmez). */
export function notPaketle(hedef, alan, noktaMs, degistirir, metin) {
  return birlestir([paketle(S_NOT_BAS, [hedef, alan, noktaMs, degistirir]), bayt(metin)]);
}

// Python bytes.decode("utf-8", errors="replace") ile ayni: BOM SILINMEZ (ignoreBOM)
const UTF8 = new TextDecoder("utf-8", { fatal: false, ignoreBOM: true });

export function notCoz(y) {
  const b = bayt(y);
  const [h, a, ms, dg] = oku(b, 0, S_NOT_BAS);
  return { hedef: h, alan: a, nokta_ms: ms, degistirir: dg,
    metin: UTF8.decode(b.subarray(S_NOT_BAS.boyut)) };
}

/** AYRINTI yuku. ornekler: [[v, i, dt4, bayrak], ...] */
export function ayrintiPaketle(d) {
  const parcalar = [paketle(S_AYRINTI_BAS, [d.ilk, d.t0_ms, d.t0_us, d.ornekler.length, d.bayrak])];
  for (const [v, i, dt4, b] of d.ornekler) {
    if (!Number.isInteger(dt4) || !Number.isInteger(b)) throw new RangeError("dt4/bayrak tamsayi olmali");
    parcalar.push(paketle(S_AYRINTI_ORNEK, [v, i, dt4 * 16 + (b & 0xF)]));   // (dt4 << 4) | (b & 0xF)
  }
  return birlestir(parcalar);
}

export function ayrintiCoz(y) {
  const b = bayt(y);
  const [ilk, ms, us, adet0, bayrak] = oku(b, 0, S_AYRINTI_BAS);
  const adet = Math.min(adet0, Math.floor((b.length - S_AYRINTI_BAS.boyut) / S_AYRINTI_ORNEK.boyut));
  const v = gorunum(b);
  const orn = [];
  for (let k = 0; k < adet; k++) {
    const a = S_AYRINTI_BAS.boyut + k * S_AYRINTI_ORNEK.boyut;
    const w = v.getUint16(a + 4, true);
    orn.push([v.getInt16(a, true), v.getInt16(a + 2, true), w >> 4, w & 0xF]);
  }
  return { ilk, t0_ms: ms, t0_us: us, bayrak, ornekler: orn };
}

/** SKOP parcasi (kayit_bicim.h kayit_skop_*_paketle ile ayni). 0. parca META'li. */
export function skopPaketle(d) {
  const parcalar = [paketle(S_SKOP_BAS, [d.no, d.ilk, d.kodlar.length, d.toplam, d.parca])];
  if (d.parca === 0) parcalar.push(paketle(S_SKOP_META, SKOP_META_AD.map((a) => d.meta[a])));
  parcalar.push(paketle(yapi(`<${d.kodlar.length}H`), d.kodlar));
  return birlestir(parcalar);
}

export function skopCoz(y) {
  const b = bayt(y);
  const [no, ilk, adet0, toplam, parca] = oku(b, 0, S_SKOP_BAS);
  let a = S_SKOP_BAS.boyut;
  let meta = null;
  if (parca === 0 && b.length >= a + S_SKOP_META.boyut) {
    meta = nesne(SKOP_META_AD, oku(b, a, S_SKOP_META));
    a += S_SKOP_META.boyut;
  }
  const adet = Math.min(adet0, Math.floor((b.length - a) / 2));
  const v = gorunum(b);
  const kodlar = new Array(adet);
  for (let k = 0; k < adet; k++) kodlar[k] = v.getUint16(a + 2 * k, true);
  return { no, ilk, adet, toplam, parca, meta, kodlar };
}

/** Yakalamalarin parcalarini birlestir. Eksik parca DOLDURULMAZ: tam=false, kodlar null. */
function skopBirlestir(o) {
  for (const y of o.skoplar.values()) {
    delete y._sonraki;
    const p = y._parca;
    delete y._parca;
    const kodlar = [];
    let beklenen = 0;
    for (const ilk of [...p.keys()].sort((x, z) => x - z)) {
      if (ilk !== beklenen) break;
      for (const kd of p.get(ilk)) kodlar.push(kd);
      beklenen = ilk + p.get(ilk).length;
    }
    y.tam = y.meta !== null && beklenen === y.toplam && kodlar.length === y.toplam;
    y.kodlar = y.tam ? kodlar : null;
  }
}

/** Tam yakalamayi `/skop.bin` bicimine cevir (32 B S3B baslik + u16; kopru/arsiv.py
 *  skop_ikili ile ayni). Eksik yakalama: null. ⚠ META'da SINYALLI NaN varsa JS motoru onu
 *  sessizlestirir (Python 3.14 bitleri korur); sessiz NaN ve sayilar bayt bayt ayni. */
export function skopIkili(y) {
  if (!y.tam) return null;
  const m = y.meta;
  const ornek = y.kodlar;
  const n = ornek.length;
  const b = new Uint8Array(32 + 2 * n);
  const v = gorunum(b);
  b.set([0x53, 0x33, 0x42], 0);               // "S3B"
  b[3] = 1;                                   // SKOP_SURUM
  tamsayiYaz(v, 4, "H", n);
  tamsayiYaz(v, 8, "I", Math.trunc(m.hz));
  float32Yaz(v, 12, m.adim);
  float32Yaz(v, 16, m.ofset);
  tamsayiYaz(v, 20, "I", Math.trunc(m.tdiv_us));
  tamsayiYaz(v, 24, "H", Math.min(Math.trunc(m.tetik), 0xFFFF));
  b[26] = m.kip & 0xFF;
  b[27] = m.tetiklendi ? 1 : 0;
  v.setUint32(28, Math.trunc(y.no ?? 0) >>> 0, true);
  for (let k = 0; k < n; k++) tamsayiYaz(v, 32 + 2 * k, "H", ornek[k]);
  return b;
}

/** Python round(): en yakin tamsayi, YARIDA CIFTE (Math.round yukari yuvarlar). */
function pyRound(x) {
  const f = Math.floor(x);
  const r = x - f;
  if (r > 0.5) return f + 1;
  if (r < 0.5) return f + 0;
  return f % 2 === 0 ? f + 0 : f + 1;
}

const IKI32 = 4294967296;

/** Oturumun ayrintili ornekleri: [[sira, us, v_kod, i_kod, bayrak, acilis], ...].
 *  us = t0_us + 4 x (dt4 toplami), o acilistaki micros(); 32 bit sarmasi t0_ms'den
 *  cozulur. acilis: 0 = BASLA'nin acilisi, n = n. DEVAM'dan sonrasi. Ayni sira iki
 *  kayitta olabilir (Y5): her sira BIR kez, ilk kopyasiyla. us < 2^53: Number yeter.
 *  siraIle (yalniz JS, W1 inceleme): true -> sira ile sirali (Python'un
 *  sorted(ayrinti_ornekler(o), key=sira)'si); bu liste ayrintiGuc / skopYerleri'ne `orn`
 *  diye verilirse yeniden kurulmaz. */
export function ayrintiOrnekler(o, siraIle = false) {
  if (siraIle) return ayrintiSirali(o);
  const devam = o.devamlar.map((d) => d.nokta_sira).sort((x, y) => x - y);
  const cikti = [];
  const gorulen = new Set();
  const sirali = [...o.ayrinti].sort((x, y) => x.sira - y.sira);
  for (const r of sirali) {
    const k = pyRound((r.t0_ms * 1000 - r.t0_us) / IKI32);
    let t = r.t0_us + k * IKI32;
    let ac = 0;
    for (const d of devam) if (d <= r.ilk) ac++;
    r.ornekler.forEach(([v, i, dt4, b], j) => {
      t += 4 * dt4;
      if (gorulen.has(r.ilk + j)) return;
      gorulen.add(r.ilk + j);
      cikti.push([r.ilk + j, t, v, i, b, ac]);
    });
  }
  return cikti;
}

// ── birimler ─────────────────────────────────────────────────────────
function kirp(d) {
  return Math.max(-32768, Math.min(32767, d));
}

function tamsayiDenetle(ad, kod, tamsayi) {
  if (typeof tamsayi !== "boolean") {
    throw new TypeError(`${ad}: 3. bagimsiz degisken 'tamsayi' zorunlu — true: int16 kod alani `
      + "(v_min_kod, ornek, ...; firmware kirpmasi uygulanir), false: float ortalama (v_ort_kod)");
  }
  if (tamsayi && !Number.isInteger(kod)) throw new TypeError(`${ad}: tamsayi=true ama kod ${kod}`);
}

/** olc_gerilim3 ile ayni formul, float64. `tamsayi`: Python'da kod int mi (JS 1.0 ile 1'i
 *  ayiramaz; doymus ortalama 32767.0'da kirpma farki gercek). */
export function volt(kod, k, tamsayi) {
  tamsayiDenetle("volt", kod, tamsayi);
  let d = kod - k.sifir_ham;
  if (tamsayi) d = kirp(d);
  return d * (k.pga / ADS_SAYIM) * k.n * k.kazanc;
}

/** olc_akim3 ile ayni formul, float64. S6: sont_ohm 0 (ya da -0; bozuk/eksik kalibrasyon)
 *  -> NaN: akim BILINMIYOR (Python da NaN; eskiden ZeroDivisionError / RangeError). */
export function amper(kod, kal, tamsayi) {
  tamsayiDenetle("amper", kod, tamsayi);
  if (kal.sont_ohm === 0) return NaN;
  let d = kod - kal.i_ofset;
  if (tamsayi) d = kirp(d);
  return d * (kal.i_pga / ADS_SAYIM) / kal.sont_ohm * kal.i_duzeltme;
}

/** 0 = kartin saati bilinmiyordu: null (1970 tarihi URETILMEZ). */
export function unixZaman(s) {
  return s ? new Date(s * 1000) : null;
}

// ── W1: PC hesaplari — yakalamanin yeri (Y7) ve hizali guc ────────────
// kopru/kayit_bicim.py ile AYNI aritmetik SIRASI (capraz vektor, bit bit). Gerekce Python'da.
export const US_SARMA = IKI32 * 1000;       // millis() 32 bit sarmasinin mikrosaniyesi
export const AYRINTI_BOSLUK_US = 4095 * 4;  // dt4 12 bit x 4 us: kart yeni AYRINTI kaydi acar
export const VI_KAYMA_US = 152.0;           // B29: kartta olculen V-I baslatma kaymasi (kayitta YOK)
export const TAU_AKIM = Math.fround(0.002904);   // olcum3.h TAU_AKIM (float32)

/** x mod m, [-m/2, m/2) araligina: isaretli sarma farki (m cift, x/m tamsayi). */
function isaretli(x, m) {
  let r = ((x % m) + m) % m;
  if (r >= m / 2) r -= m;
  return r;
}

/** ayrintiOrnekler, sira ile sirali (Python sorted(..., key=sira); sira tekil — ayrintiOrnekler
 *  ayni siraya ikinci ornek vermez — yani kararli siralamayla ayni). Cogu zaman zaten sirali:
 *  o zaman kopya kurulmaz. W1 inceleme: ~1.9 M ornekli oturumda bu liste BIR kez kurulur ve
 *  gucDizi / skopYerleri'ne gecirilir (her biri yeniden kurunca 1 GB yigin asiliyordu). */
function ayrintiSirali(o) {
  const orn = ayrintiOrnekler(o);
  for (let k = 1; k < orn.length; k++) {
    if (orn[k][0] < orn[k - 1][0]) return orn.sort((x, y) => x[0] - y[0]);
  }
  return orn;
}

/** Olcum verisini sira ile gez: f(sira, zaman_us, acilis) (Python _olcum_zamanlari). Ayrintili
 *  oturumda `orn` (ayrintiSirali) verilirse yeniden kurulmaz; ara uclu dizi kurulmaz. */
function olcumZamanlariGez(o, orn, f) {
  if (o.ayrinti.length && !o.noktalar.length) {
    for (const r of orn || ayrintiSirali(o)) f(r[0], r[1], r[5]);
    return;
  }
  const dv = o.devamlar.map((d) => d.nokta_sira).sort((x, y) => x - y);
  for (const [s, p] of [...o.noktalar].sort((x, y) => x[0] - y[0])) {
    let ac = 0;
    for (const d of dv) if (d <= s) ac++;
    f(s, p.kart_ms * 1000, ac);
  }
}

/** Python bisect.bisect_left */
function bisectSol(a, x) {
  let lo = 0;
  let hi = a.length;
  while (lo < hi) {
    const orta = Math.floor((lo + hi) / 2);
    if (a[orta] < x) lo = orta + 1;
    else hi = orta;
  }
  return lo;
}

/** Y7: META'li her yakalamanin olcumdeki YERI, ZAMAN sirasiyla: [{sira, no, acilis, t_ms,
 *  sure_ms, once, sonra}]. sonra = istekten (t_ms) SONRAKI ilk olcum verisinin sirasi (ayrintili:
 *  zamani >= (t_ms+1) x 1000 us; nokta: kart_ms > t_ms), once = ayni acilista ondan onceki;
 *  yoksa null. Siralama (acilis, t_ms'nin acilisin ilk yakalamasina isaretli 32 bit farki, sira).
 *  META'siz yakalama listede YOK. Ayrinti: kopru/kayit_bicim.py skop_yerleri. orn (yalniz JS):
 *  ayrintili oturumda onceden kurulmus ayrintiOrnekler(o, true) (verilmezse burada kurulur). */
export function skopYerleri(o, orn = null) {
  if (!o.skoplar.size) return [];
  const gruplar = new Map();
  olcumZamanlariGez(o, orn, (s, us, ac) => {
    let g = gruplar.get(ac);
    if (!g) {
      g = { us0: us, sira: [], rel: [] };
      gruplar.set(ac, g);
    }
    g.sira.push(s);
    g.rel.push(isaretli(us - g.us0, US_SARMA));
  });
  const ilkT = new Map();
  const yerler = [];
  for (const sira of [...o.skoplar.keys()].sort((x, y) => x - y)) {
    const y = o.skoplar.get(sira);
    const m = y.meta;
    if (m === null) continue;
    const ac = y.acilis;
    if (!ilkT.has(ac)) ilkT.set(ac, m.t_ms);
    const t0 = ilkT.get(ac);
    let once = null;
    let sonra = null;
    const g = gruplar.get(ac);
    if (g) {
      const j = bisectSol(g.rel, isaretli((m.t_ms + 1) * 1000 - g.us0, US_SARMA));
      sonra = j < g.sira.length ? g.sira[j] : null;
      once = j > 0 ? g.sira[j - 1] : null;
    }
    yerler.push([[ac, isaretli(m.t_ms - t0, IKI32), sira],
      { sira, no: y.no, acilis: ac, t_ms: m.t_ms, sure_ms: m.sure_ms, once, sonra }]);
  }
  yerler.sort((x, z) => x[0][0] - z[0][0] || x[0][1] - z[0][1] || x[0][2] - z[0][2]);
  return yerler.map(([, d]) => d);
}

/** olcum3.h suzgec_ters_kazanc, float64 (Python _suzgec_ters_kazanc ile ayni sira). */
function suzgecTersKazanc(f, tau) {
  if (f <= 0 || tau <= 0) return 1.0;
  const w = 2 * Math.PI * f * tau;
  return Math.sqrt(1 + w * w);
}

/** dx dugumlerinden (us) gecen polinomun x'teki degeri (Python _lagrange ile ayni sira). */
function lagrange(dx, y, x) {
  let t = 0.0;
  for (let j = 0; j < dx.length; j++) {
    let pay = 1.0;
    let payda = 1.0;
    for (let m = 0; m < dx.length; m++) {
      if (m !== j) {
        pay *= x - dx[m];
        payda *= dx[j] - dx[m];
      }
    }
    t += pay / payda * y[j];
  }
  return t;
}

/** Ayrintili ornek basina HIZALI guc: [[sira, w], ...] ornek sirasiyla (capraz vektor bicimi).
 *  Yalniz JS secenekleri (W1 inceleme, ~1.9 M ornekte cift dizisi kurmamak icin): orn =
 *  onceden kurulmus ayrintiOrnekler(o, true); dizi: true -> Float64Array (k. eleman = orn'un k.
 *  ornegi), [sira, w] ciftleri kurulmaz. */
export function ayrintiGuc(o, { orn = null, dizi = false } = {}) {
  if (orn === null) orn = ayrintiSirali(o);
  const w = gucDizi(o, orn);
  return dizi ? w : orn.map((r, k) => [r[0], w[k]]);
}

/** Hizali guc, Float64Array (k. eleman = orn'un k. ornegi). Kartin o.watt'iyla ayni tanim
 *  (V akim anina Lagrange ile tasinir, x I, sebeke_hz > 0 ise RC ters kazanci), GERCEK ornek
 *  zamanlariyla. Dugum/yedek kurallari: kopru/kayit_bicim.py ayrinti_guc. */
function gucDizi(o, orn) {
  const kal = o.basla ? o.basla.kal : null;
  const n = orn.length;
  const out = new Float64Array(n).fill(NaN);
  if (!kal) return out;
  const v = new Float64Array(n);
  for (let k = 0; k < n; k++) {
    const b = orn[k][4];
    v[k] = b & KAO_V_HATA ? NaN : volt(orn[k][2], b & KAO_YUKSEK ? kal.yuksek : kal.normal, true);
  }
  const f = kal.sebeke_hz;
  const olcek = [kal.normal, kal.yuksek].map((k) => (f > 0 ? suzgecTersKazanc(f, k.tau) * suzgecTersKazanc(f, TAU_AKIM) : 1.0));
  const bagli = (a) => {
    const d = isaretli(orn[a + 1][1] - orn[a][1], US_SARMA);
    return orn[a][5] === orn[a + 1][5] && d > 0 && d <= AYRINTI_BOSLUK_US;
  };
  const gecerli = (a) => v[a] === v[a];
  for (let k = 0; k < n; k++) {
    const [, us, , ik, b] = orn[k];
    if ((b & KAO_I_HATA) || !gecerli(k)) continue;     // out[k] NaN kalir
    const yk = b & KAO_YUKSEK ? 1 : 0;
    const kayma = VI_KAYMA_US + kal.faz_kal_us[yk];
    let dugum;
    if (k >= 1 && k + 2 < n && bagli(k - 1) && bagli(k) && bagli(k + 1)
        && gecerli(k - 1) && gecerli(k + 1) && gecerli(k + 2)) {
      dugum = [k - 1, k, k + 1, k + 2];
    } else if (kayma >= 0 && k + 1 < n && bagli(k) && gecerli(k + 1)) {
      dugum = [k, k + 1];
    } else if (kayma < 0 && k >= 1 && bagli(k - 1) && gecerli(k - 1)) {
      dugum = [k - 1, k];
    } else {
      dugum = [k];
    }
    const dx = dugum.map((j) => isaretli(orn[j][1] - us, US_SARMA));
    let x = kayma;
    if (x < dx[0]) x = dx[0];
    if (x > dx[dx.length - 1]) x = dx[dx.length - 1];
    out[k] = lagrange(dx, dugum.map((j) => v[j]), x) * amper(ik, kal, true) * olcek[yk];
  }
  return out;
}

// ── oturumlar ────────────────────────────────────────────────────────
function yeniOturum(id) {
  return {
    id,
    basla: null,
    basi_eksik: true,        // BASLA temizlikte gitti, TEKRAR'dan bilgi
    tekrar_adet: 0,
    noktalar: [],            // [[sira, nokta], ...]
    devamlar: [],
    saatler: [],
    bitir: null,
    olaylar: [],             // olayCoz + sira
    ad: null,                // en son NOT(ad)
    etiketler: [],           // en son NOT(etiket), virgulden
    notlar: new Map(),       // NOT kaydinin sirasi -> {nokta_ms, metin}
    ayrinti: [],             // ayrintiCoz + sira
    skoplar: new Map(),      // 0. parcanin (ya da yetim parcanin) SIRASI -> {no, meta, toplam, t_sira, acilis, tam, kodlar}
  };
}

// Python str.isspace() kumesi (str.strip() bunlari atar; JS trim() farkli: U+FEFF'i atar, U+0085'i atmaz)
const PY_BOSLUK = new Set([0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x85, 0xA0,
  0x1680, 0x2000, 0x2001, 0x2002, 0x2003, 0x2004, 0x2005, 0x2006, 0x2007, 0x2008, 0x2009, 0x200A,
  0x2028, 0x2029, 0x202F, 0x205F, 0x3000]);

function pyStrip(s) {
  let a = 0;
  let b = s.length;
  while (a < b && PY_BOSLUK.has(s.charCodeAt(a))) a++;
  while (b > a && PY_BOSLUK.has(s.charCodeAt(b - 1))) b--;
  return s.slice(a, b);
}

/** NOT kaydini oturumun son haline isle (kayit_bicim.h NOT aciklamasi). */
function notUygula(o, k) {
  const n = notCoz(k.yuk);
  if (n.alan === KNT_AD) {
    o.ad = n.metin;
  } else if (n.alan === KNT_ETIKET) {
    o.etiketler = n.metin.split(",").map(pyStrip).filter((e) => e);
  } else if (n.alan === KNT_NOT) {
    const dg = n.degistirir;
    if (dg) {
      // ASIL notun sirasi; bilinmeyen/silinmis ya da duzeltme kaydinin sirasi YOK SAYILIR
      if (o.notlar.has(dg)) {
        if (n.metin) {
          o.notlar.set(dg, { nokta_ms: n.nokta_ms || o.notlar.get(dg).nokta_ms,   // 0: yer KORUNUR
            metin: n.metin });
        } else {
          o.notlar.delete(dg);
        }
      }
    } else if (n.metin) {
      o.notlar.set(k.sira, { nokta_ms: n.nokta_ms, metin: n.metin });
    }
  }
}

// S5: bilinen kayit turunun EN KISA gecerli yuku (bayt) — Python _EN_AZ ile ayni. Daha uzun
// yuk: bilinen on ek cozulur (BASLA 98..101 = surum 1, >= 102 = surum 2 + fazlasi; NOKTA'da
// yarim nokta, AYRINTI/SKOP'ta adet'i asan kuyruk, OLAY'da govdeyi asan bayt yok sayilir).
// Daha kisa: kayit ATLANIR, oturum ACMAZ, ot.uyarilar'a girer. Tabloda olmayan (bilinmeyen)
// tur sessizce yok sayilir ve o da oturum ACMAZ (S6).
const EN_AZ = new Map([
  [T_BASLA, BASLA_V1_BAYT], [T_TEKRAR, BASLA_V1_BAYT], [T_NOKTA, 4],
  [T_DEVAM, S_DEVAM.boyut], [T_BITIR, S_BITIR.boyut], [T_SAAT, S_SAAT.boyut],
  [T_OLAY, S_OLAY_BAS.boyut], [T_NOT, S_NOT_BAS.boyut],
  [T_AYRINTI, S_AYRINTI_BAS.boyut], [T_SKOP, S_SKOP_BAS.boyut],
]);
dogrula([...EN_AZ.values()].join() === "98,98,4,16,8,12,8,16,16,12", "EN_AZ");

/** Kayitlardan oturumlar: Map(oturum id -> oturum), oturumun ilk VERI kaydinin sirasiyla.
 *  CRC'si gecerli her kayitta FIRLATMAZ (S5). Donen Map'in SAYILAMAZ `uyarilar` ozelligi
 *  (Python Oturumlar.uyarilar): yuku turunun en kisa boyundan KISA oldugu icin ATLANAN
 *  kayitlar, kayit sirasiyla: {sira, tur, oturum (baslik), bayt (yuk boyu), en_az}. Bos
 *  dizi = hepsi cozuldu. Sayilamaz: Map'in kendisi ve deepStrictEqual karsilastirmasi degismez. */
export function oturumlariKur(kayitlar) {
  const ot = new Map();
  const uyarilar = [];
  Object.defineProperty(ot, "uyarilar", { value: uyarilar, enumerable: false });
  const al = (id) => {
    let o = ot.get(id);
    if (!o) {
      o = yeniOturum(id);
      ot.set(id, o);
    }
    return o;
  };
  // Yakalama KAYIT SIRASIYLA kurulur. 0. parca yeni yakalama acar; sonraki parca yalniz
  // HEMEN onceki acik yakalamaya (ayni no/toplam, ilk kesintisiz) eklenir — arada yalniz TEKRAR.
  const acik = new Map();
  const noktaGorulen = new Map();
  const sirali = [...kayitlar].sort((x, y) => x.sira - y.sira);
  for (const k of sirali) {
    if (k.oturum && k.tur !== T_SKOP && k.tur !== T_TEKRAR) acik.delete(k.oturum);
    const enAz = EN_AZ.get(k.tur);
    if (enAz === undefined) continue;          // bilinmeyen tur: yok sayilir, oturum ACMAZ (S6)
    if (k.yuk.length < enAz) {                 // S5: kisa kayit cozulemez — atla, oturum ACMA, uyar
      uyarilar.push({ sira: k.sira, tur: k.tur, oturum: k.oturum, bayt: k.yuk.length, en_az: enAz });
      continue;
    }
    if (k.tur === T_NOT && k.yuk.length >= S_NOT_BAS.boyut) {
      const h = oku(k.yuk, 0, S_U32)[0];        // baslikta oturum 0; hedef yukte
      if (h) notUygula(al(h), k);
      continue;
    }
    if (!k.oturum) continue;
    const o = al(k.oturum);
    if (k.tur === T_OLAY && k.yuk.length >= S_OLAY_BAS.boyut) {
      o.olaylar.push({ ...olayCoz(k.yuk), sira: k.sira });
      continue;
    }
    if (k.tur === T_AYRINTI && k.yuk.length >= S_AYRINTI_BAS.boyut) {
      o.ayrinti.push({ ...ayrintiCoz(k.yuk), sira: k.sira });
      continue;
    }
    if (k.tur === T_SKOP && k.yuk.length >= S_SKOP_BAS.boyut) {
      const p = skopCoz(k.yuk);
      let y = acik.get(k.oturum);
      if (p.parca === 0 || y === undefined || y.no !== p.no
          || y.toplam !== p.toplam || p.ilk !== y._sonraki) {
        // W1/Y7: acilis = oturumda bu kayittan ONCE gelen DEVAM sayisi (yakalama yazildigi acilisa ait)
        y = { no: p.no, meta: null, toplam: p.toplam, t_sira: k.sira, acilis: o.devamlar.length,
          _parca: new Map(), _sonraki: 0 };
        o.skoplar.set(k.sira, y);
        acik.set(k.oturum, y);
      }
      if (p.parca === 0) y.meta = p.meta;
      if (!y._parca.has(p.ilk)) y._parca.set(p.ilk, p.kodlar);
      y._sonraki = p.ilk + p.kodlar.length;
      continue;
    }
    if (k.tur === T_BASLA) {
      o.basla = baslaCoz(k.yuk);
      o.basi_eksik = false;
    } else if (k.tur === T_TEKRAR) {
      o.tekrar_adet += 1;
      if (o.basla === null) o.basla = baslaCoz(k.yuk);
    } else if (k.tur === T_NOKTA) {
      const ilk = oku(k.yuk, 0, S_U32)[0];
      let gorulen = noktaGorulen.get(k.oturum);
      if (!gorulen) {
        gorulen = new Set();
        noktaGorulen.set(k.oturum, gorulen);
      }
      const adet = Math.floor((k.yuk.length - 4) / NOKTA_BAYT);
      for (let j = 0; j < adet; j++) {
        if (gorulen.has(ilk + j)) continue;     // Y5: yeniden deneme kopyasi — ilki kalir
        gorulen.add(ilk + j);
        const a = 4 + j * NOKTA_BAYT;
        o.noktalar.push([ilk + j, noktaCoz(k.yuk.subarray(a, a + NOKTA_BAYT))]);
      }
    } else if (k.tur === T_DEVAM) {
      o.devamlar.push(devamCoz(k.yuk));
    } else if (k.tur === T_BITIR) {
      o.bitir = bitirCoz(k.yuk);
    } else if (k.tur === T_SAAT) {
      o.saatler.push(saatCoz(k.yuk));
    }
  }
  for (const o of ot.values()) skopBirlestir(o);
  return ot;
}
