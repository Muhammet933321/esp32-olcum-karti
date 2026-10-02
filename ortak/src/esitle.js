// B73 / 2C — KAYIT ESITLEME ISTEMCISI: kopru/kayit_esitle.py Esitleyici'sinin (B72; kartla
// dogrulanmis) JS karsiligi. Tasarim: tasarim/2026-10-02-alt-proje-2-ortak.md (O7: ag ve saklama
// ENJEKSIYONLA — tarayici, Node ve Capacitor ayni dosyayi yukler; bu dosyada Node API'si yok).
//
// Kart asil kaydi tutar. Bu istemci eksik kayitlari /kayit/veri'den parca parca (`sira`, `bayt`)
// ceker, CRC'lerini dogrular (kayit.js akisCoz), kartin baytlarini depoya AYNEN ekler ve ANCAK
// ONDAN SONRA "N'e kadar aldim" onayi yollar (kartin akilli temizligi yalniz onaylara bakar).
//
// Davranis Python'la BIREBIR (ortak/test/esitle.test.js: ayni sahte kart senaryolarinda iki
// istemcinin sakladigi akis baytlari, durum, kalibrasyon dosyalari ve onay dizisi ayni):
//   * X-Kayit-Kimlik degisirse DUR (EsitlemeHatasi): kart akisi yeniden baslatti; eski akisa
//     eklemek esitlenmemis veriyi sessizce kaybettirirdi. Yeni akis -> yeni depo.
//   * X-Sonraki-Sira bizim son siramizin GERISINDEYSE DUR.
//   * Bos yanit ama kartta daha yeni sira: hata degil, 'bitti' de degil: {bekleyen, uyari}.
//   * Bozuk yanit (CRC) -> KayitHatasi; istenenden eski / tekrar eden sira -> EsitlemeHatasi.
//     Ikisinde de depoya yazilmaz, onaylanmaz.
//   * onay(sira) YALNIZ depo.veriEkle + depo.durumYaz bittikten SONRA. `onaylanan` yalniz kart
//     X-Onay ile DOGRULAYINCA yazilir; dogrulanmazsa yeniden yollanir (en fazla 4 kez; Python'daki
//     gibi 4. yollamanin sonucu bu kosuda denetlenmez, sonraki kosu yeniden dener).
//   * Cokme: depodaki akis durumdan UZUNSA kesintisiz GECERLI kayitlar ileri sarilir, gerisi
//     (yarim kuyruk, sirasi atlayan kayit) KIRPILIR; KISAYSA hata (elle incele).
//   * /kal/liste veri esitlemesinden SONRA; hicbir hatasi veriyi bozmaz: 404/503 sessiz, baska
//     HTTP kodu "HTTP <kod>", ag/bicim hatasi "<Ad>: <mesaj>" (kalibrasyon_hata), eski dosya
//     yerinde. Kartin okuyamadigi kayit ({no, bozuk:true}) PC'deki saglam kopyayla birlestirilir
//     ("kartta_bozuk": true); kartin gecmisi PC'dekinden bir kaydi SILIYOR / DEGISTIRIYORSA (not,
//     tur, kartta_bozuk haric) ya da eski dosya okunamiyorsa eskisi depo.kalArsivle ile yedeklenir.
//     Python'un == / dict / dogruluk kurallari (True == 1, bos liste yanlis, hash'lenemez anahtar
//     TypeError ...) py* yardimcilariyla aynen uygulanir.
//
// API (Python -> JS):
//   Esitleyici(taban_url, dizin, onay, bayt, zaman_asimi, onay_bekle, cihaz)
//     -> new Esitleyici({ tabanUrl, fetch, depo, onay, bayt = 8192, istek, onayBekleMs = 300,
//                         zamanAsimiMs = 10000 })
//        fetch : WHATWG fetch (tarayici/Node/Capacitor). `istek` verilirse kullanilmaz.
//        istek : async (taban, yol, argumanlar) -> Response. Imzali yol (1D): imzaliIstek(cihaz,
//                ortam) — imza.js `ac`'yi takar; ac 2xx disinda HttpHatasi atar, o da islenir.
//        onay  : async (sira) -> void | null. Cagiran baglar: seri `Go<sira>`, httpOnay (jeton +
//                Basic Auth) ya da imzaliOnay (imzali /komut).
//   esitle(azami_tur) -> await e.esitle({ azamiTur = 100000 })
//        donus anahtarlari Python'daki ADLARLA: { yeni_kayit, son_sira, bosluk: [[a, b], ...],
//        onay_dogrulandi, kalibrasyon, [kalibrasyon_hata], [kalibrasyon_bozuk], [kalibrasyon_arsiv],
//        [bekleyen, uyari] }
//   son_sira() -> await e.sonSira();  _kal_cakisir -> kalCakisir;  _kal_bozuk_birlestir ->
//   kalBozukBirlestir;  json.dump(indent=1, ensure_ascii=False) -> jsonGirintili;
//   http_onay -> httpOnay;  imzali_onay -> imzaliOnay;  Kilit -> depo.kilitAl (istege bagli).
//   Hata siniflari: ValueError -> EsitlemeHatasi (DegerHatasi'ndan) / KayitHatasi (akisCoz) /
//   DegerHatasi (baslik sayi degil); RuntimeError -> CalismaHatasi; HTTPError -> HttpHatasi.
//
// DEPO arayuzu (hepsi async; disk / IndexedDB uygulamasi cagiranin isi — PC'de Python'la ayni
// dosyalar: DOSYA, DURUM, KAL_DOSYA). Sozlesme Python'un fsync/rename kurallari:
//   kilitAl()          -> birak() | yoksa yok. Ayni depoya iki esitleme: CalismaHatasi.
//   durumOku()         -> {son_sira, bayt, onaylanan, kimlik} | null   (ek alanlar korunur)
//   durumYaz(d)        ATOMIK (yarim durum asla gorulmez)
//   veriBoyu()         -> bayt
//   veriOku(bas)       -> Uint8Array: bas'tan sona
//   veriEkle(b)        DAYANIKLI (fsync): donunce baytlar kalici — onay ANCAK bundan sonra gider
//   veriKirp(n)        akisi n bayta kirp, dayanikli
//   kalOku()           -> kalibrasyon.json'in HAM baytlari | null (dosya yok)
//   kalYaz(b)          ATOMIK
//   kalArsivle(b)      -> ad: eski kalibrasyon dosyasinin zaman damgali DAYANIKLI kopyasi
// bellekDepo(): bellekte uygulama (testler; tarayicida gecici esitleme). anlik() ile icerik.
//
// Python'dan bilinen (davranis disi) farklar — hepsi kartin gercek ciktisinda olusmaz:
//   * kalibrasyon.json yazimi Python json.dump(indent=1, ensure_ascii=False) ile bayt bayt ayni,
//     YALNIZ tamsayi degerli float'lar haric: JS 2.0 ile 2'yi ayirt edemez, "2" yazar (Python
//     "2.0"). Kart degerleri %.9g ile basar ("2", ".0" yok) — kartin ciktisinda fark yok.
//     Anlam (Python ==) her durumda ayni. Satir sonu "\n": Python dosyayi METIN kipinde yazdigi
//     icin Windows'ta "\r\n" yazar (POSIX'te "\n") — JSON icin bosluk, okuma ikisinde de ayni.
//   * JSON.parse NaN/Infinity kabul etmez (Python eder); kart sonlu olmayani null basar.
//   * Ayni baslik iki kez gelirse fetch "a, b" birlestirir (Python ilkini alir) -> sayi hatasi.
//   * Tamsayi benzeri JSON anahtarlarinin sirasi JS nesnesinde korunmaz (kartin anahtarlari metin).
//   * Python yalniz OSError/HTTPException/ValueError'u kalibrasyon_hata yapar; fetch ag hatasini
//     TypeError ile bildirdiginden /kal/liste'nin getir-coz blogunda HER hata kalibrasyon_hata.

import { akisCoz, akisOnek, toplamBayt } from "./kayit.js";
import { DegerHatasi, bayt, utf8Coz, utf8Kodla } from "./kripto.js";
import { CalismaHatasi, HttpHatasi, ac, tamsayi } from "./imza.js";

export const DOSYA = "kayitlar.kyt";
export const DURUM = "durum.json";
export const KAL_DOSYA = "kalibrasyon.json";
export const EN_AZ_BAYT = 1100;      // en buyuk kayit 16 + 1012 = 1028 B; kucuk parca hic veri getiremez
export const ONAY_DENEME = 4;
export const UYARI_BEKLEYEN = "kartta daha yeni sira var ama veri gelmedi "
  + "(bicimlenmis ya da yarim yazilmis olabilir); yeni kayit gelince bosluk olarak gecilir";

/** Python ValueError (esitleme kurali): akis kimligi degisti, kart geride, sira tekrar, depo kisa. */
export class EsitlemeHatasi extends DegerHatasi {
  constructor(mesaj) {
    super(mesaj);
    this.name = "EsitlemeHatasi";
  }
}

/** Python KeyError karsiligi (yalniz Python'un da cokecegi bicimsiz kalibrasyon girdisinde). */
export class AnahtarHatasi extends Error {
  constructor(mesaj) {
    super(mesaj);
    this.name = "AnahtarHatasi";
  }
}

/** Python AttributeError karsiligi (dict olmayan degerde .get / .items). */
export class NitelikHatasi extends Error {
  constructor(mesaj) {
    super(mesaj);
    this.name = "NitelikHatasi";
  }
}

const VARSAYILAN_DURUM = () => ({ son_sira: 0, bayt: 0, onaylanan: 0, kimlik: null });

// Python bytes.decode("utf-8", errors="replace"): BOM SOYULMAZ (json.loads onu reddeder)
const UTF8_YUMUSAK = new TextDecoder("utf-8", { fatal: false, ignoreBOM: true });

function basarili(y) {
  return y.status >= 200 && y.status < 300;
}

function govdeyiBirak(y) {
  try {
    if (y.body && typeof y.body.cancel === "function") y.body.cancel().catch(() => {});
  } catch {
    // govde zaten okunmus / kilitli: birakacak bir sey yok
  }
}

/** Python int(basliklar.get(ad)) ya da None (baslik yok / bos). */
function sayi(basliklar, ad) {
  const v = basliklar.get(ad);
  return v === null || v === undefined || v === "" ? null : tamsayi(v);
}

function uyu(ms) {
  return new Promise((coz) => setTimeout(coz, ms));
}

function pyListe(a) {
  return `[${a.join(", ")}]`;
}

// ── Python veri modeli yardimcilari (JSON degerleri uzerinde) ──────────────
function duzNesne(x) {
  return x !== null && typeof x === "object" && !Array.isArray(x);
}

/** bool(x) */
function pyDogru(x) {
  if (x === null || x === undefined) return false;
  if (typeof x === "boolean") return x;
  if (typeof x === "number") return x !== 0;          // NaN Python'da dogru
  if (typeof x === "string" || Array.isArray(x)) return x.length > 0;
  return Object.keys(x).length > 0;
}

/** x.get(a, varsayilan): dict degilse AttributeError. */
function pyGet(x, a, varsayilan) {
  if (!duzNesne(x)) throw new NitelikHatasi(`'${x === null ? "NoneType" : typeof x}' nesnesinde .get yok`);
  return Object.hasOwn(x, a) ? x[a] : varsayilan;
}

/** x[a]: dict'te yoksa KeyError, dict degilse TypeError. */
function pyIndeks(x, a) {
  if (!duzNesne(x)) throw new TypeError(`${a} alt simgesi dict olmayan degerde`);
  if (!Object.hasOwn(x, a)) throw new AnahtarHatasi(a);
  return x[a];
}

/** iter(x): liste ogeleri, metin karakterleri, dict anahtarlari; gerisi TypeError. */
function pyIter(x) {
  if (Array.isArray(x)) return x;
  if (typeof x === "string") return Array.from(x);
  if (duzNesne(x)) return Object.keys(x);
  throw new TypeError("yinelenemez deger");
}

/** dict anahtari olarak: 1 == 1.0 == True ayni anahtar; liste/dict hash'lenemez (TypeError). */
function pyAnahtar(v) {
  if (v === null || v === undefined) return "None";
  if (typeof v === "boolean") return v ? "n:1" : "n:0";
  if (typeof v === "number") return `n:${Object.is(v, -0) ? 0 : v}`;
  if (typeof v === "string") return `s:${v}`;
  throw new TypeError("hash'lenemez tur: " + (Array.isArray(v) ? "list" : "dict"));
}

/** Python == (JSON degerleri): True == 1, dict sirasiz, liste sirali. */
function pyEsit(a, b) {
  const sayisal = (x) => typeof x === "number" || typeof x === "boolean";
  if (sayisal(a) && sayisal(b)) return Number(a) === Number(b);
  if (typeof a === "string" || typeof b === "string") return a === b;
  if (a === null || b === null) return a === b;
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length
      && a.every((x, i) => pyEsit(x, b[i]));
  }
  if (duzNesne(a) && duzNesne(b)) {
    const ka = Object.keys(a);
    return ka.length === Object.keys(b).length && ka.every((k) => Object.hasOwn(b, k) && pyEsit(a[k], b[k]));
  }
  return false;
}

function pyYakalanir(h) {
  return h instanceof TypeError || h instanceof AnahtarHatasi || h instanceof NitelikHatasi;
}

/** Y6 (1B inceleme M2): kartin OKUYAMADIGI kayit {"no", "bozuk": true} gelir. PC'de saglam kopyasi
 *  varsa o KALIR ("kartta_bozuk": true); yoksa bozuk isaretiyle yazilir. `veri` YERINDE degisir.
 *  Donus: kartta bozuk numaralar. (Python Esitleyici._kal_bozuk_birlestir) */
export function kalBozukBirlestir(veri, eski) {
  let saglam = new Map();
  try {
    for (const k of pyIter(pyGet(eski, "kayitlar", []))) {
      if (!pyDogru(pyGet(k, "bozuk", null))) saglam.set(pyAnahtar(pyIndeks(k, "no")), k);
    }
  } catch (h) {
    if (!pyYakalanir(h)) throw h;
    saglam = new Map();
  }
  const bozuk = [];
  const liste = veri.kayitlar;
  for (let i = 0; i < liste.length; i++) {
    const k = liste[i];
    if (duzNesne(k) && pyDogru(pyGet(k, "bozuk", null))) {
      const no = pyGet(k, "no", null);
      bozuk.push(no);
      if (saglam.has(pyAnahtar(no))) {
        const iyi = {};
        for (const [a, v] of Object.entries(saglam.get(pyAnahtar(pyIndeks(k, "no"))))) {
          if (a !== "kartta_bozuk") iyi[a] = v;
        }
        liste[i] = { ...iyi, kartta_bozuk: true };
      }
    }
  }
  return bozuk;
}

const KIMLIK_DISI = new Set(["not", "tur", "kartta_bozuk"]);

/** Kartin gecmisi PC'dekinden bir kaydi SILIYOR ya da DEGISTIRIYOR mu (NVS silindi, `adet`
 *  kayboldu, baska kart)? Not ve tur duzeltmesi olagan. Bicimsiz eski -> true. (_kal_cakisir) */
export function kalCakisir(eski, yeni) {
  const kimlik = (k) => {
    if (!duzNesne(k)) throw new NitelikHatasi("dict olmayan kayit");
    const o = {};
    for (const [a, v] of Object.entries(k)) if (!KIMLIK_DISI.has(a)) o[a] = v;
    return o;
  };
  const sozluk = (kayitlar) => {
    const m = new Map();
    for (const k of pyIter(kayitlar)) {
      const no = pyIndeks(k, "no");                      // Python: anahtar degerden ONCE
      m.set(pyAnahtar(no), kimlik(k));
    }
    return m;
  };
  let e;
  let y;
  try {
    e = sozluk(pyGet(eski, "kayitlar", []));
    y = sozluk(pyIndeks(yeni, "kayitlar"));
  } catch (h) {
    if (pyYakalanir(h)) return true;
    throw h;
  }
  for (const [no, v] of e) if (!y.has(no) || !pyEsit(y.get(no), v)) return true;
  return false;
}

// ── Python json.dump(deger, indent=1, ensure_ascii=False) ────────────────
function sayiYaz(x) {
  if (Number.isNaN(x)) return "NaN";                   // Python allow_nan=True varsayilani
  if (!Number.isFinite(x)) return x > 0 ? "Infinity" : "-Infinity";
  if (Number.isInteger(x)) return Object.is(x, -0) ? "0" : String(x);   // JSON.stringify ile ayni basamaklar
  // tamsayi olmayan double < 2^53: Python repr sabit nokta, |x| < 1e-4 bilimsel ("1e-05").
  // toExponential(): en kisa gidis-donus basamaklari (Python repr ile ayni basamaklar).
  if (Math.abs(x) >= 1e-4) return String(x);
  const m = /^(-?)(\d)(?:\.(\d+))?e([+-]\d+)$/.exec(x.toExponential());
  const us = Number(m[4]);
  return `${m[1]}${m[2]}${m[3] ? "." + m[3] : ""}e${us < 0 ? "-" : "+"}${String(Math.abs(us)).padStart(2, "0")}`;
}

function metinYaz(s) {
  utf8Kodla(s);                                        // eslesmemis vekil: Python da yazamaz (ValueError)
  return JSON.stringify(s);                            // kacislar Python ensure_ascii=False ile ayni
}

function jsonYaz(x, g) {
  if (x === null) return "null";
  if (x === true) return "true";
  if (x === false) return "false";
  if (typeof x === "number") return sayiYaz(x);
  if (typeof x === "string") return metinYaz(x);
  const ic = "\n" + " ".repeat(g + 1);
  const dis = "\n" + " ".repeat(g);
  if (Array.isArray(x)) {
    if (!x.length) return "[]";
    return "[" + ic + x.map((v) => jsonYaz(v, g + 1)).join("," + ic) + dis + "]";
  }
  if (duzNesne(x)) {
    const a = Object.keys(x);
    if (!a.length) return "{}";
    return "{" + ic + a.map((k) => metinYaz(k) + ": " + jsonYaz(x[k], g + 1)).join("," + ic) + dis + "}";
  }
  throw new TypeError("JSON'a yazilamaz: " + typeof x);
}

/** json.dumps(deger, ensure_ascii=False, indent=1) metni. */
export function jsonGirintili(deger) {
  return jsonYaz(deger, 0);
}

// ── istemci ───────────────────────────────────────────────────────────────
export class Esitleyici {
  constructor({ tabanUrl, fetch = null, depo, onay = null, bayt: parca = 8192, istek = null,
    onayBekleMs = 300, zamanAsimiMs = 10000 } = {}) {
    if (typeof tabanUrl !== "string") throw new TypeError("tabanUrl metin olmali");
    if (!depo || typeof depo !== "object") throw new TypeError("depo gerekli");
    if (istek !== null && typeof istek !== "function") throw new TypeError("istek islev olmali");
    if (istek === null && typeof fetch !== "function") throw new TypeError("fetch islevi (ya da istek) gerekli");
    if (onay !== null && typeof onay !== "function") throw new TypeError("onay islev ya da null olmali");
    if (!Number.isInteger(parca)) throw new TypeError("bayt tamsayi olmali");
    this.taban = tabanUrl.replace(/\/+$/, "");
    this._fetch = fetch;
    this.depo = depo;
    this.onay = onay;
    this.bayt = Math.max(parca, EN_AZ_BAYT);
    this.istek = istek;
    this.onayBekleMs = onayBekleMs;
    this.zamanAsimiMs = zamanAsimiMs;
  }

  // ── durum ──
  async _durum() {
    const d = VARSAYILAN_DURUM();
    const o = await this.depo.durumOku();
    if (o !== null && o !== undefined) Object.assign(d, o);
    return d;
  }

  async sonSira() {
    return (await this._durum()).son_sira;
  }

  /** Durumdan UZUN akis: durum yazilmadan kesilmis ekleme. GECERLI ve kesintisiz artan kayitlari
   *  ileri sar (dayanikli veri kaybolmasin), gerisini kirp. */
  async _hazirla(d) {
    const boy = await this.depo.veriBoyu();
    if (boy < d.bayt) {
      throw new EsitlemeHatasi(`${DOSYA} durumdan kisa (${boy} < ${d.bayt} B) — elle incele`);
    }
    if (boy === d.bayt) return;
    const [kayitlar] = akisOnek(await this.depo.veriOku(d.bayt));
    let son = d.son_sira;
    let gecerli = 0;
    for (const k of kayitlar) {
      // YALNIZ kesintisiz dizi: arada atlanan sira varsa ileri sarma durur, kalan yeniden CEKILIR
      if (k.sira !== son + 1) break;
      son = k.sira;
      gecerli += toplamBayt(k.yuk.length);
    }
    await this.depo.veriKirp(d.bayt + gecerli);
    if (gecerli) {
      d.son_sira = son;
      d.bayt += gecerli;
      await this.depo.durumYaz(d);
    }
  }

  // ── ag ──
  async _ac(yol, argumanlar = []) {
    if (this.istek) return this.istek(this.taban, yol, argumanlar);
    const q = argumanlar.map(([a, d]) => `${a}=${d}`).join("&");
    const secenek = { method: "GET" };
    if (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function") {
      secenek.signal = AbortSignal.timeout(this.zamanAsimiMs);
    }
    const f = this._fetch;                              // tarayicida fetch `this`siz cagrilmali
    return f(this.taban + yol + (q ? `?${q}` : ""), secenek);
  }

  async _getir(sira) {
    const y = await this._ac("/kayit/veri", [["sira", String(sira)], ["bayt", String(this.bayt)]]);
    if (!basarili(y)) {
      govdeyiBirak(y);
      throw new HttpHatasi(y.status, y, "/kayit/veri");
    }
    return [new Uint8Array(await y.arrayBuffer()), y.headers];
  }

  async _kimlikDenetle(d, basliklar) {
    const k = sayi(basliklar, "X-Kayit-Kimlik");
    if (k === null) return;                              // eski firmware: baslik yok
    if (d.kimlik === null || d.kimlik === undefined) {
      d.kimlik = k;
      await this.depo.durumYaz(d);
    } else if (d.kimlik !== k) {
      throw new EsitlemeHatasi(`kartin kayit AKISI degismis (kimlik ${d.kimlik} -> ${k}): `
        + "kart sifirlanmis ya da baska kart. Bu dizine EKLENMEZ — yeni bir dizine esitle");
    }
  }

  /** Kart onayi ALDI MI (X-Onay)? Almadiysa yeniden yolla, birkac kez. */
  async _onayDogrula(d, onayX) {
    if (d.onaylanan >= d.son_sira) return true;
    if (!this.onay) return false;
    for (let i = 0; i < ONAY_DENEME; i++) {
      if (onayX !== null && onayX >= d.son_sira) {
        d.onaylanan = d.son_sira;
        await this.depo.durumYaz(d);
        return true;
      }
      await this.onay(d.son_sira);
      await uyu(this.onayBekleMs);                       // kart onayi bir sonraki turda uygular
      const [, bas] = await this._getir(d.son_sira + 1);
      onayX = sayi(bas, "X-Onay");
    }
    return false;
  }

  async esitle({ azamiTur = 100000 } = {}) {
    if (!Number.isInteger(azamiTur)) throw new TypeError("azamiTur tamsayi olmali");
    const birak = typeof this.depo.kilitAl === "function" ? await this.depo.kilitAl() : null;
    try {
      return await this._esitle(azamiTur);
    } finally {
      if (birak) await birak();
    }
  }

  async _esitle(azamiTur) {
    const d = await this._durum();
    await this._hazirla(d);
    let yeni = 0;
    const bosluk = [];
    let sonuc = {};
    let onayX = null;
    for (let tur = 0; tur < azamiTur; tur++) {
      const son = d.son_sira;
      const [govde, bas] = await this._getir(son + 1);
      await this._kimlikDenetle(d, bas);
      onayX = sayi(bas, "X-Onay");
      const sonraki = sayi(bas, "X-Sonraki-Sira");
      if (sonraki !== null && sonraki - 1 < son) {
        throw new EsitlemeHatasi(`kartin sirasi GERI gitti (kartta son ${sonraki - 1}, `
          + `bizde ${son}): kart sifirlanmis. Bu dizine EKLENMEZ`);
      }
      if (govde.length === 0) {
        if (sonraki !== null && sonraki - 1 > son) {
          sonuc = { bekleyen: sonraki - 1 - son, uyari: UYARI_BEKLEYEN };
        }
        break;
      }
      const kayitlar = akisCoz(govde);                   // CRC: bozuk yanit depoya YAZILMAZ, onaylanmaz
      const siralar = kayitlar.map((k) => k.sira);
      let artan = true;
      for (let i = 1; i < siralar.length; i++) if (siralar[i] <= siralar[i - 1]) artan = false;
      if (siralar[0] <= son || !artan) {
        throw new EsitlemeHatasi(`kart sirasi geri gitti ya da tekrar etti: ${pyListe(siralar.slice(0, 3))} `
          + `(son ${son})`);
      }
      if (siralar[0] > son + 1) bosluk.push([son + 1, siralar[0]]);
      await this.depo.veriEkle(govde);                   // once KALICI yaz
      d.son_sira = siralar[siralar.length - 1];
      d.bayt += govde.length;
      await this.depo.durumYaz(d);
      yeni += kayitlar.length;
      if (this.onay) await this.onay(d.son_sira);        // ancak depoya yazildiktan SONRA
    }
    const dogru = await this._onayDogrula(d, onayX);
    return { yeni_kayit: yeni, son_sira: d.son_sira, bosluk, onay_dogrulandi: dogru,
      ...(await this._kalEsitle()), ...sonuc };
  }

  /** 1B: kalibrasyon gecmisini KAL_DOSYA'ya ATOMIK yaz. Veri esitlemesinden SONRA, onu HICBIR
   *  hatayla bozmaz. Donus: {kalibrasyon: adet | null, [kalibrasyon_hata], [kalibrasyon_bozuk],
   *  [kalibrasyon_arsiv]}. */
  async _kalEsitle() {
    const httpSonuc = (kod) => (kod === 404 || kod === 503 ? { kalibrasyon: null }
      : { kalibrasyon: null, kalibrasyon_hata: `HTTP ${kod}` });
    let veri;
    try {
      let y;
      try {
        y = await this._ac("/kal/liste");
      } catch (h) {
        if (h instanceof HttpHatasi) return httpSonuc(h.durum);      // imzali yol (imza.js ac)
        throw h;
      }
      if (!basarili(y)) {
        govdeyiBirak(y);
        return httpSonuc(y.status);
      }
      // eski firmware notta gecersiz UTF-8 birakabiliyordu (cp1254 's'): degistirilerek okunur
      veri = JSON.parse(UTF8_YUMUSAK.decode(new Uint8Array(await y.arrayBuffer())));
      if (!duzNesne(veri) || !Array.isArray(pyGet(veri, "kayitlar", null))) {
        throw new DegerHatasi("beklenmeyen bicim");
      }
    } catch (h) {
      return { kalibrasyon: null, kalibrasyon_hata: `${h && h.name ? h.name : "Hata"}: ${h && h.message}` };
    }
    const sonuc = { kalibrasyon: pyGet(veri, "adet", null) };
    const eskiBayt = await this.depo.kalOku();
    let eski = null;
    let okunamadi = false;
    if (eskiBayt !== null && eskiBayt !== undefined) {
      try {
        eski = JSON.parse(utf8Coz(eskiBayt));            // kati UTF-8 + BOM'lu dosya okunamaz (Python gibi)
      } catch {
        okunamadi = true;                                // okunamayan dosya da korunur
      }
    }
    const bozuk = kalBozukBirlestir(veri, eski);
    if (bozuk.length) sonuc.kalibrasyon_bozuk = bozuk;
    if (eskiBayt !== null && eskiBayt !== undefined && (okunamadi || kalCakisir(eski, veri))) {
      sonuc.kalibrasyon_arsiv = await this.depo.kalArsivle(eskiBayt);
    }
    await this.depo.kalYaz(utf8Kodla(jsonGirintili(veri)));
    return sonuc;
  }
}

// ── onay ve imzali istek baglayicilari ────────────────────────────────────
/** 1D: imza.js `ac` ile imzali GET (Esitleyici `istek`i). ortam: { fetch, simdiMs?, kaydet? }. */
export function imzaliIstek(cihaz, ortam) {
  return (taban, yol, argumanlar) => ac(cihaz, taban, "GET", yol, argumanlar, new Uint8Array(0), ortam);
}

/** 1D: /komut uzerinden imzali `Go<sira>` — jeton ve parola GEREKMEZ. (imzali_onay) */
export function imzaliOnay(cihaz, taban, ortam) {
  const t = taban.replace(/\/+$/, "");
  return async (sira) => {
    const y = await ac(cihaz, t, "POST", "/komut", [], utf8Kodla(`Go${sira}`), ortam);
    await y.arrayBuffer();
  };
}

const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

function base64(b) {
  let s = "";
  for (let i = 0; i < b.length; i += 3) {
    const n = (b[i] << 16) | ((b[i + 1] ?? 0) << 8) | (b[i + 2] ?? 0);
    s += B64[(n >> 18) & 63] + B64[(n >> 12) & 63]
      + (i + 1 < b.length ? B64[(n >> 6) & 63] : "=") + (i + 2 < b.length ? B64[n & 63] : "=");
  }
  return s;
}

/** `/komut` uzerinden `Go<sira>`: jeton /akis'in `kimlik` olayindan (bir kez alinir; kart yeniden
 *  baslayip 403 derse yenilenir). Parola verilirse Basic Auth (olcum:<parola>). (http_onay) */
export function httpOnay(taban, { fetch, parola = null, zamanAsimiMs = 5000 } = {}) {
  if (typeof fetch !== "function") throw new TypeError("fetch islevi gerekli");
  const t = taban.replace(/\/+$/, "");
  const bellek = { jeton: null };
  const sinyal = () => (typeof AbortSignal !== "undefined" && typeof AbortSignal.timeout === "function"
    ? { signal: AbortSignal.timeout(zamanAsimiMs) } : {});

  async function jetonAl() {
    const y = await fetch(`${t}/akis`, { method: "GET", ...sinyal() });
    if (!basarili(y)) {
      govdeyiBirak(y);
      throw new HttpHatasi(y.status, y, `${t}/akis`);
    }
    const okuyucu = y.body.getReader();
    const coz = new TextDecoder("utf-8");
    let tampon = "";
    let bitti = false;
    try {
      for (let satir = 0; satir < 50; satir++) {
        let i = tampon.indexOf("\n");
        while (i < 0 && !bitti) {
          const { value, done } = await okuyucu.read();
          if (done) bitti = true;
          else tampon += coz.decode(value, { stream: true });
          i = tampon.indexOf("\n");
        }
        if (i < 0) i = tampon.length;                    // akis bitti: kalan son satir
        const s = tampon.slice(0, i).trim();
        tampon = tampon.slice(i + 1);
        if (s.startsWith("data:") && s.includes("jeton")) return JSON.parse(s.slice(5).trim()).jeton;
      }
    } finally {
      okuyucu.cancel().catch(() => {});
    }
    throw new CalismaHatasi("oturum jetonu alinamadi");
  }

  async function gonder(sira) {
    const b = { "X-Olcum": "1", "X-Jeton": bellek.jeton, "Content-Type": "text/plain" };
    if (parola) b.Authorization = "Basic " + base64(utf8Kodla(`olcum:${parola}`));
    const y = await fetch(`${t}/komut`, { method: "POST", headers: b, body: utf8Kodla(`Go${sira}`), ...sinyal() });
    if (!basarili(y)) {
      govdeyiBirak(y);
      throw new HttpHatasi(y.status, y, `${t}/komut`);
    }
    await y.arrayBuffer();
  }

  return async (sira) => {
    if (!bellek.jeton) bellek.jeton = await jetonAl();
    try {
      await gonder(sira);
    } catch (h) {
      if (!(h instanceof HttpHatasi) || h.durum !== 403) throw h;
      bellek.jeton = await jetonAl();
      await gonder(sira);
    }
  };
}

// ── bellek deposu ───────────────────────────────────────────────────────
/** Bellekte depo: testler ve tarayicida gecici esitleme. simdi: arsiv adinin yerel saati. */
export function bellekDepo({ simdi = () => new Date() } = {}) {
  let tampon = new Uint8Array(4096);
  let boy = 0;
  let durum = null;
  let kal = null;
  let kilitli = false;
  const arsiv = new Map();
  const kopya = (o) => (o === null ? null : JSON.parse(JSON.stringify(o)));
  const iki = (n) => String(n).padStart(2, "0");

  function ekle(b) {
    if (boy + b.length > tampon.length) {
      let n = tampon.length;
      while (n < boy + b.length) n *= 2;
      const y = new Uint8Array(n);
      y.set(tampon.subarray(0, boy));
      tampon = y;
    }
    tampon.set(b, boy);
    boy += b.length;
  }

  return {
    async kilitAl() {
      if (kilitli) throw new CalismaHatasi("bellek deposu: baska bir esitleme suruyor");
      kilitli = true;
      return async () => {
        kilitli = false;
      };
    },
    async durumOku() {
      return kopya(durum);
    },
    async durumYaz(d) {
      durum = kopya(d);
    },
    async veriBoyu() {
      return boy;
    },
    async veriOku(bas = 0) {
      return tampon.slice(Math.min(bas, boy), boy);
    },
    async veriEkle(b) {
      ekle(bayt(b));
    },
    async veriKirp(n) {
      if (!Number.isInteger(n) || n < 0) throw new RangeError("kirpma boyu gecersiz");
      if (n < boy) boy = n;
      else if (n > boy) ekle(new Uint8Array(n - boy));   // Python truncate: uzatirsa sifir
    },
    async kalOku() {
      return kal === null ? null : kal.slice();
    },
    async kalYaz(b) {
      kal = Uint8Array.from(bayt(b));
    },
    async kalArsivle(b) {
      const t = simdi();
      const kok = `kalibrasyon-${t.getFullYear()}${iki(t.getMonth() + 1)}${iki(t.getDate())}`
        + `-${iki(t.getHours())}${iki(t.getMinutes())}${iki(t.getSeconds())}`;
      let ad = `${kok}.json`;
      for (let n = 1; arsiv.has(ad); n++) ad = `${kok}-${n}.json`;
      arsiv.set(ad, Uint8Array.from(bayt(b)));
      return ad;
    },
    /** Icerigin kopyasi: { veri, durum, kal, arsivler: [{ ad, bayt }] } (arsivler olusma sirasiyla). */
    anlik() {
      return {
        veri: tampon.slice(0, boy),
        durum: kopya(durum),
        kal: kal === null ? null : kal.slice(),
        arsivler: [...arsiv].map(([ad, b]) => ({ ad, bayt: b.slice() })),
      };
    },
  };
}
