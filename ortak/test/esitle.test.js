// B73 / 2C — ortak/src/esitle.js == kopru/kayit_esitle.py (davranis BIREBIR).
//
// CAPRAZ TEST: B72'nin sahte karti (uretim/test_kayit_esp.py _SahteKart + _sunucu, AYNEN) iki
// surecte kosar — uretim/ortak_sahte_kart.py:
//   * `py` kipi: asagidaki SENARYOLARI Python basvurusuyla (kopru/kayit_esitle.py Esitleyici) kosar,
//     her esitleme adiminin anligini dondurur;
//   * `sunucu` kipi: ayni sahte kart, JS istemcisinin karsisinda; kart/disk adimlari onun
//     komutlariyla (adim yorumlayicisinin kart/disk kismi Python'da TEK yerde).
// Her esitleme adiminda karsilastirilan: sonuc nesnesi (anahtar sirasi dahil), hata turu + kodu,
// saklanan akis BAYTLARI, durum, kalibrasyon.json ve arsiv BAYTLARI, onay dizisi (sira + onay
// anindaki depo boyu), kartin onayi, imzali istek / 401 sayilari.
// Ayrica senaryo basina BAGIMSIZ denetimler (B72.E iddialari JS sonucunda) ve kalCakisir /
// kalBozukBirlestir / jsonGirintili icin Python'la uc durum karsilastirmasi.
// Ag: yalniz 127.0.0.1. Python: PYTHON ortam degiskeni ya da python / python3.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import * as E from "../src/esitle.js";
import { KayitHatasi, T_NOKTA, T_SAAT, akisCoz, kayitPaketle } from "../src/kayit.js";
import { DegerHatasi, hex, hexten, utf8Kodla } from "../src/kripto.js";
import { CalismaHatasi, HttpHatasi } from "../src/imza.js";

const YARDIMCI = fileURLToPath(new URL("../../uretim/ortak_sahte_kart.py", import.meta.url));
const PY = process.env.PYTHON || (process.platform === "win32" ? "python" : "python3");

// ── veri ─────────────────────────────────────────────────────────────────
// test_kayit_esp.py bolum_esitle'nin kalibrasyon gecmisi (JSON'dan gecince 2.0 -> 2: iki taraf ayni)
const KAL = {
  surum: 1, adet: 2, taslak: 0, azami: 40, kayitlar: [
    { no: 1, unix: 0, acilis: 0, tur: 0, kaynak: 2, not: "1B oncesi kalibrasyon (Ayar3)",
      kal: { normal: { n: 16.5, pga: 2.0, kazanc: 1.0, sifir_ham: -12, tau: 0.0029 },
        yuksek: { n: 312.5, pga: 2.0, kazanc: 0.99, sifir_ham: 5, tau: 0.0031 },
        i_ofset: -3, i_pga: 0.25, sont_ohm: 0.005, i_duzeltme: 1.0,
        sebeke_hz: 50.0, faz0: 12.5, faz1: -3.25 } },
    { no: 2, unix: 1790000000, acilis: 5, tur: 1, kaynak: 0, not: "şönt değişti ğü", kal: {} }],
};
const kopya = (x) => JSON.parse(JSON.stringify(x));
const KAL_DUZELTME = kopya(KAL);                    // kn/kt: olagan, yedek YOK
KAL_DUZELTME.kayitlar[1].not = "not duzeltildi";
KAL_DUZELTME.kayitlar[1].tur = 2;
const KAL_TARIH = kopya(KAL_DUZELTME);              // ayni numara BASKA tarih: yedek
KAL_TARIH.kayitlar[0].unix = 1791000000;
const KAL_EKSIK = { ...kopya(KAL_TARIH), adet: 1 }; // bir kayit KAYBOLDU: yedek
KAL_EKSIK.kayitlar = KAL_EKSIK.kayitlar.slice(0, 1);
const KAL_BOZUK2 = kopya(KAL);
KAL_BOZUK2.kayitlar[1] = { no: 2, bozuk: true };
// kartin %.9g bicimine benzer: kucuk float'lar Python'da bilimsel ("1.5e-05") yazilir
const KAL_KART = {
  surum: 1, adet: 1, taslak: 0, etkin: 1, azami: 40, kayitlar: [
    { no: 1, unix: 1790000000, acilis: 3, tur: 0, kaynak: 1, not: "kart: %.9g ölçek",
      kal: { normal: { n: 16.4999905, pga: 2, kazanc: 0.999999881, sifir_ham: -12, tau: 1.5e-05 },
        yuksek: { n: 312.5, pga: 2, kazanc: 1, sifir_ham: 5, tau: 0.00031 },
        i_ofset: -3, i_pga: 0.0001, sont_ohm: 0.00499999989, i_duzeltme: 1, sebeke_hz: 50,
        faz0: 12.5, faz1: -2.5e-07 } }],
};
const KAL_KART2 = kopya(KAL_KART);
KAL_KART2.kayitlar[0].kal.normal.tau = 1.25e-05;
const ESKI_KAL = '{"eski": 1}';
const CIHAZ = { n: 1, K: "5a".repeat(32) };

const esitle = (ek = {}) => ({ tur: "esitle", ...ek });
const kart = (alanlar) => ({ tur: "kart", alanlar });

/** B72.E senaryolari (+ parca siniri, imzali yol, kalibrasyon bicimi). `denetle` JS-yalniz. */
const SENARYOLAR = [
  { ad: "E1-E5 ilk esitleme kesilir/surer, onay yazildiktan sonra, artimli, bos tekrar",
    kayitlar: [[50, 1]],
    adimlar: [esitle({ bayt: 1100, azami_tur: 2 }), esitle({ bayt: 1100 }), esitle({ bayt: 1100 }),
      kart({ kayitlar: [[50, 1], [7, 51]] }), esitle({ bayt: 1100 })],
    denetle(a) {
      assert.ok(a[0].sonuc.son_sira > 0 && a[0].sonuc.son_sira < 50, "iki parcada 50 kayit gelmemeli");
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1]])), "E1 bayt bayt");
      assert.equal(a[1].sonuc.son_sira, 50);
      assert.equal(a[1].sonuc.onay_dogrulandi, true);
      onayOnek(a[1], [[50, 1]]);
      assert.equal(a[2].sonuc.yeni_kayit, 0, "E5");
      assert.equal(a[2].onaylar.length, a[1].onaylar.length, "E5 yeni onay yok");
      assert.equal(a.length, 4, "anlik yalniz esitleme adimlarinda");
      assert.equal(a[3].veri, hex(kartAkisi([[50, 1], [7, 51]])));
      assert.equal(a[3].sonuc.yeni_kayit, 7);
      assert.equal(a[3].kart_onay, 57);
    } },
  { ad: "parca siniri: en buyuk kayit (1012 B yuk), bayt = tam iki kayit",
    kayitlar: [[7, 1, 1012]],
    adimlar: [esitle({ bayt: 2056, azami_tur: 1 }), esitle({ bayt: 2056 })],
    denetle(a) {
      assert.equal(a[0].sonuc.yeni_kayit, 2);
      assert.equal(a[1].sonuc.son_sira, 7);
      assert.equal(akisCoz(hexten(a[1].veri)).length, 7);
    } },
  { ad: "bayt alt siniri EN_AZ_BAYT (1100): kucuk parca da en buyuk kaydi getirir",
    kayitlar: [[5, 1, 1012]],
    adimlar: [esitle({ bayt: 100, azami_tur: 3 }), esitle()],
    denetle(a) {
      assert.equal(a[0].sonuc.yeni_kayit, 3);
      assert.equal(a[1].sonuc.son_sira, 5);
    } },
  { ad: "E3 bozuk yanit (CRC): yazilmaz, onaylanmaz",
    kayitlar: [[50, 1]],
    adimlar: [kart({ bozuk: true }), esitle()],
    denetle(a) {
      assert.deepEqual([a[0].hata.tur, a[0].hata.kod], ["deger", "crc"]);
      assert.equal(a[0].veri, "");
      assert.deepEqual(a[0].onaylar, []);
    } },
  { ad: "E6 temizlikte silinmis aralik BOSLUK", kayitlar: [[40, 11]],
    adimlar: [esitle({ onay: "yok" })],
    denetle(a) {
      assert.deepEqual(a[0].sonuc.bosluk, [[1, 11]]);
      assert.equal(a[0].sonuc.son_sira, 50);
      assert.equal(a[0].sonuc.onay_dogrulandi, false);
    } },
  { ad: "E7 yanitta istenenden eski/tekrar sira: DUR", kayitlar: [[50, 1]],
    adimlar: [esitle({ onay: "yok" }), kart({ kayitlar: [[50, 1], [3, 51]], sirayi_yok_say: true }),
      esitle({ onay: "yok", azami_tur: 100 })],
    denetle(a) {
      assert.equal(a[1].hata.kod, "tekrar");
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1]])));
      assert.equal(a[1].durum.son_sira, 50);
    } },
  { ad: "E9 durum yazilmadan kesilen YARIM ekleme kirpilir", kayitlar: [[50, 1]],
    adimlar: [esitle({ bayt: 1100, azami_tur: 1, onay: "yok" }), { tur: "disk", ekle: "yarim" },
      esitle({ onay: "yok" })],
    denetle(a) {
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1]])));
    } },
  { ad: "E10 onay yollanamadiysa sonraki kosu yeniden yollar (veri tekrar cekilmez)",
    kayitlar: [[50, 1]],
    adimlar: [esitle({ onay: "patlayan" }), esitle()],
    denetle(a) {
      assert.equal(a[0].hata.tur, "os");
      assert.equal(a[1].sonuc.yeni_kayit, 0);
      assert.deepEqual(a[1].onaylar.map((x) => x[0]), [50, 50]);
      assert.equal(a[1].kart_onay, 50);
    } },
  { ad: "E11 akis KIMLIGI degisirse DUR: yazmaz, onaylamaz", kayitlar: [[50, 1]],
    adimlar: [esitle(), kart({ kimlik: 99, kayitlar: [[50, 1], [5, 51]] }), esitle()],
    denetle(a) {
      assert.equal(a[1].hata.kod, "kimlik");
      assert.equal(a[1].veri, a[0].veri);
      assert.equal(a[1].kart_onay, a[0].kart_onay);
    } },
  { ad: "E12 kartin sirasi istemcinin gerisine duserse DUR", kayitlar: [[50, 1]],
    adimlar: [esitle(), kart({ kayitlar: [[3, 1]] }), esitle()],
    denetle(a) {
      assert.equal(a[1].hata.kod, "geride");
      assert.equal(a[1].durum.son_sira, 50);
    } },
  { ad: "E13 bos yanit ama kartta yeni sira: uyari + bekleyen, 'bitti' YOK", kayitlar: [[50, 1]],
    adimlar: [kart({ bos_don: true }), esitle({ onay: "yok" })],
    denetle(a) {
      assert.equal(a[0].sonuc.bekleyen, 50);
      assert.equal(a[0].sonuc.uyari, E.UYARI_BEKLEYEN);
      assert.equal(a[0].sonuc.son_sira, 0);
      assert.equal(a[0].veri, "");
    } },
  { ad: "E14/E14b onay kaybolursa X-Onay'dan anlasilir, yeniden yollanir; hic alinmazsa YAZILMAZ",
    kayitlar: [[50, 1]],
    adimlar: [kart({ onay_dusur: 1 }), esitle(), kart({ onay_dusur: 99, onay: 0 }),
      { tur: "durum", alanlar: { onaylanan: 0 } }, esitle()],
    denetle(a) {
      assert.equal(a[0].sonuc.onay_dogrulandi, true);
      assert.equal(a[0].durum.onaylanan, 50);
      assert.equal(a[0].kart_onay, 50);
      assert.equal(a[1].sonuc.onay_dogrulandi, false);
      assert.equal(a[1].durum.onaylanan, 0);
      assert.equal(a[1].onaylar.length - a[0].onaylar.length, E.ONAY_DENEME);
    } },
  { ad: "E15 durum geride (rename kayboldu): gecerli kuyruk ileri sarilir", kayitlar: [[50, 1]],
    adimlar: [esitle({ bayt: 1100, azami_tur: 1 }), { tur: "disk", ekle: "sonraki", azami: 2000 }, esitle()],
    denetle(a) {
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1]])));
      assert.equal(a[1].sonuc.son_sira, 50);
    } },
  { ad: "E17 ileri sarma yalniz kesintisiz dizi: atlayan kuyruk kirpilir", kayitlar: [[50, 1]],
    adimlar: [esitle({ bayt: 1100, azami_tur: 1, onay: "yok" }), { tur: "disk", ekle: "son_kayit" },
      esitle({ onay: "yok" })],
    denetle(a) {
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1]])));
    } },
  { ad: "depo durumdan KISA: elle incele (hata)", kayitlar: [[5, 1]],
    adimlar: [{ tur: "durum", alanlar: { bayt: 100, son_sira: 3 } }, esitle()],
    denetle(a) {
      assert.equal(a[0].hata.kod, "kisa");
    } },
  { ad: "azami_tur 0: hicbir sey cekilmez", kayitlar: [[5, 1]],
    adimlar: [esitle({ azami_tur: 0 })],
    denetle(a) {
      assert.equal(a[0].sonuc.yeni_kayit, 0);
      assert.equal(a[0].sonuc.onay_dogrulandi, true);
    } },
  { ad: "E18 kalibrasyon gecmisi yazilir (Turkce not bozulmadan)", kayitlar: [[5, 1]],
    adimlar: [kart({ kal_liste: KAL }), esitle()],
    denetle(a) {
      assert.deepEqual(JSON.parse(new TextDecoder().decode(hexten(a[0].kal))), KAL);
      assert.equal(a[0].sonuc.kalibrasyon, 2);
    } },
  { ad: "E19 eski firmware (/kal/liste 404) veriyi DURDURMAZ", kayitlar: [[50, 1]],
    adimlar: [esitle()],
    denetle(a) {
      assert.equal(a[0].sonuc.son_sira, 50);
      assert.equal(a[0].sonuc.kalibrasyon, null);
      assert.ok(!("kalibrasyon_hata" in a[0].sonuc));
      assert.equal(a[0].kal, null);
    } },
  { ad: "E20 not/tur duzeltmesi yedeksiz; gecmis degisirse eski dosya YEDEKLENIR", kayitlar: [[5, 1]],
    adimlar: [kart({ kal_liste: KAL }), esitle(), kart({ kal_liste: KAL_DUZELTME }), esitle(),
      kart({ kal_liste: KAL_TARIH }), esitle(), kart({ kal_liste: KAL_EKSIK }), esitle()],
    denetle(a) {
      assert.equal(a[1].arsivler.length, 0);
      assert.ok(!("kalibrasyon_arsiv" in a[1].sonuc));
      assert.deepEqual(a[2].arsivler, [a[1].kal]);
      assert.equal(a[2].sonuc.kalibrasyon_arsiv, 0);
      assert.deepEqual(a[3].arsivler, [a[1].kal, a[2].kal]);
      assert.deepEqual(JSON.parse(new TextDecoder().decode(hexten(a[3].kal))), KAL_EKSIK);
    } },
  ...[["bozuk JSON", ["ham", hex(utf8Kodla("{bozuk"))]], ["500", ["kod", 500]], ["503", ["kod", 503]],
    ["yarida kopan", ["kes", hex(utf8Kodla('{"surum":1,"adet":'))]],
    ["gecersiz UTF-8 (cp1254)", ["ham", hex(Uint8Array.from([...utf8Kodla('{"surum":1,"adet":1,"kayitlar":[{"no":1,"not":"'),
      0xfe, 0xf0, ...utf8Kodla('nt"}]}')]))]]].map(([ad, yanit]) => ({
    ad: `E21 /kal/liste ${ad}: veri tamamlanir, eski dosya yerinde`, kayitlar: [[50, 1]],
    adimlar: [{ tur: "disk", kal_metin: ESKI_KAL }, kart({ kal_yanit: yanit }), esitle()],
    denetle(a) {
      assert.equal(a[0].sonuc.son_sira, 50);
      const metin = new TextDecoder().decode(hexten(a[0].kal));
      if (ad.startsWith("gecersiz")) {
        assert.equal(a[0].sonuc.kalibrasyon, 1);
        assert.ok(metin.includes("�"));
      } else {
        assert.equal(a[0].sonuc.kalibrasyon, null);
        assert.equal(metin, ESKI_KAL);
        assert.equal(Boolean(a[0].sonuc.kalibrasyon_hata), ad !== "503");
      }
    },
  })),
  { ad: "Y6b kartta BOZUK kayit: PC'deki saglam kopya kalir (yedeksiz)", kayitlar: [[5, 1]],
    adimlar: [kart({ kal_liste: KAL }), esitle(), kart({ kal_liste: KAL_BOZUK2 }), esitle()],
    denetle(a) {
      const y = JSON.parse(new TextDecoder().decode(hexten(a[1].kal)));
      assert.deepEqual(y.kayitlar[1], { ...KAL.kayitlar[1], kartta_bozuk: true });
      assert.deepEqual(a[1].sonuc.kalibrasyon_bozuk, [2]);
      assert.equal(a[1].arsivler.length, 0);
    } },
  { ad: "Y6b kartta BOZUK kayit, PC'de kopya yok: bozuk isaretiyle yazilir", kayitlar: [[5, 1]],
    adimlar: [kart({ kal_liste: KAL_BOZUK2 }), esitle()],
    denetle(a) {
      const y = JSON.parse(new TextDecoder().decode(hexten(a[0].kal)));
      assert.deepEqual(y.kayitlar[1], { no: 2, bozuk: true });
    } },
  { ad: "okunamayan eski kalibrasyon dosyasi yedeklenir", kayitlar: [[5, 1]],
    adimlar: [{ tur: "disk", kal_metin: "{bozuk" }, kart({ kal_liste: KAL }), esitle()],
    denetle(a) {
      assert.deepEqual(a[0].arsivler, [hex(utf8Kodla("{bozuk"))]);
    } },
  { ad: "kart bicimi (%.9g, 1.5e-05): kalibrasyon.json + yedek Python'la BAYT BAYT", kayitlar: [[5, 1]],
    adimlar: [kart({ kal_liste: KAL_KART }), esitle(), kart({ kal_liste: KAL_KART2 }), esitle()],
    denetle(a) {
      assert.ok(new TextDecoder().decode(hexten(a[0].kal)).includes('"tau": 1.5e-05'));
      assert.equal(a[1].arsivler.length, 1);
    } },
  { ad: "imzali esitleme (1D): imza.js ac takilir, zorunlu kartta 401 yok", kayitlar: [[50, 1]],
    cihaz: CIHAZ,
    adimlar: [kart({ imza_zorunlu: true }), esitle({ imzali: true, bayt: 1100 }),
      kart({ kayitlar: [[50, 1], [4, 51]] }), esitle({ imzali: true })],
    denetle(a) {
      assert.equal(a[1].veri, hex(kartAkisi([[50, 1], [4, 51]])));
      assert.ok(a[1].imzali > 0);
      assert.equal(a[1].ret_401, 0);
      assert.equal(a[1].kart_onay, 54);
    } },
];

// ── bagimsiz yardimcilar ─────────────────────────────────────────────────
/** test_kayit_esp._kayitlar'in BAGIMSIZ JS yazimi (kayit.js ile) — Python'a sormadan denetim. */
function kartAkisi(araliklar) {
  const parcalar = [];
  for (const [n, bas] of araliklar) {
    for (let i = bas; i < bas + n; i++) {
      const yuk = Uint8Array.from({ length: 4 + (i % 5) * 36 }, (_, j) => (i + j) & 0xFF);
      parcalar.push(kayitPaketle(i % 3 ? T_NOKTA : T_SAAT, i, 7, yuk));
    }
  }
  const b = new Uint8Array(parcalar.reduce((s, p) => s + p.length, 0));
  let o = 0;
  for (const p of parcalar) {
    b.set(p, o);
    o += p.length;
  }
  return b;
}

/** B72.E4: her onay [sira, depo boyu]: boy == o siraya kadar olan kayitlarin toplam boyu. */
function onayOnek(anlik, araliklar) {
  const kay = akisCoz(kartAkisi(araliklar));
  for (const [s, b] of anlik.onaylar) {
    const beklenen = kay.filter((k) => k.sira <= s).reduce((t, k) => t + 16 + k.yuk.length + ((4 - (k.yuk.length % 4)) % 4), 0);
    assert.equal(b, beklenen, `onay ${s} aninda depo ${b} B, beklenen ${beklenen}`);
  }
}

class AgHatasi extends Error {
  constructor(m) {
    super(m);
    this.name = "AgHatasi";
  }
}

const HATA_KODLARI = [["AKISI degismis", "kimlik"], ["sirasi GERI gitti", "geride"],
  ["geri gitti ya da tekrar etti", "tekrar"], ["baytta gecersiz kayit", "crc"], ["durumdan kisa", "kisa"],
  ["ag koptu", "ag"]];

function hataKodu(m) {
  const k = HATA_KODLARI.find(([s]) => m.includes(s));
  return k ? k[1] : `? ${m}`;
}

function hataTuru(h) {
  if (h instanceof DegerHatasi || h instanceof KayitHatasi) return "deger";
  if (h instanceof CalismaHatasi) return "calisma";
  if (h instanceof HttpHatasi || h instanceof AgHatasi) return "os";
  return h && h.name;
}

/** Python kalibrasyon.json'u METIN kipinde yazar: Windows'ta "\r\n" (POSIX'te "\n"). JSON'da ham CR
 *  yalniz satir sonundan gelebilir (metin icinde \r kacisli) -> karsilastirmada CRLF = LF. */
function lf(h) {
  if (h === null) return null;
  const b = hexten(h);
  return hex(b.filter((x, i) => !(x === 0x0d && b[i + 1] === 0x0a)));
}

/** Karsilastirma bicimi: hata metni -> kod, kalibrasyon_hata (ag/bicim) -> "*", anahtar sirasi. */
function normal(a) {
  const o = { ...a, kal: lf(a.kal), arsivler: a.arsivler.map(lf) };
  if (a.hata) o.hata = { tur: a.hata.tur, kod: hataKodu(a.hata.mesaj) };
  if (a.sonuc) {
    o.sonuc = { ...a.sonuc, $anahtarlar: Object.keys(a.sonuc) };
    if ("kalibrasyon_hata" in a.sonuc) {
      o.sonuc.kalibrasyon_hata = /^HTTP \d+$/.test(a.sonuc.kalibrasyon_hata) ? a.sonuc.kalibrasyon_hata : "*";
    }
  }
  return o;
}

// ── Python surecleri ─────────────────────────────────────────────────────
function pyKos(senaryolar) {
  return new Promise((coz, red) => {
    const p = spawn(PY, [YARDIMCI, "py"], { stdio: ["pipe", "pipe", "pipe"] });
    let cikti = "";
    let hata = "";
    p.stdout.setEncoding("utf8");
    p.stderr.setEncoding("utf8");
    p.stdout.on("data", (x) => { cikti += x; });
    p.stderr.on("data", (x) => { hata += x; });
    p.on("error", red);
    p.on("close", (kod) => (kod === 0 ? coz(JSON.parse(cikti))
      : red(new Error(`${PY} ortak_sahte_kart.py py -> ${kod}: ${hata.slice(-3000)}`))));
    p.stdin.end(JSON.stringify(senaryolar));
  });
}

class SahteKart {
  static baslat() {
    return new Promise((coz, red) => {
      const k = new SahteKart();
      k.p = spawn(PY, [YARDIMCI, "sunucu"], { stdio: ["pipe", "pipe", "pipe"] });
      k.bekleyen = [];
      k.hata = "";
      k.p.stderr.setEncoding("utf8");
      k.p.stderr.on("data", (x) => { k.hata += x; });
      k.p.on("error", red);
      k.p.on("close", (kod) => {
        for (const b of k.bekleyen.splice(0)) b(JSON.stringify({ hata: `sunucu kapandi (${kod}): ${k.hata.slice(-2000)}` }));
        red(new Error(`sunucu kapandi (${kod}): ${k.hata.slice(-2000)}`));
      });
      createInterface({ input: k.p.stdout }).on("line", (s) => {
        const b = k.bekleyen.shift();
        if (b) b(s);
      });
      k.bekleyen.push((s) => {
        k.taban = `http://127.0.0.1:${JSON.parse(s).port}`;
        coz(k);
      });
    });
  }

  komut(k) {
    return new Promise((coz, red) => {
      this.bekleyen.push((s) => {
        const r = JSON.parse(s);
        if (r.hata && !k.k.startsWith("kal_")) red(new Error(`sahte kart ${k.k}: ${r.hata}`));
        else coz(r);
      });
      this.p.stdin.write(JSON.stringify(k) + "\n");
    });
  }

  async kapat() {
    await this.komut({ k: "son" }).catch(() => {});
    this.p.stdin.end();
  }
}

// ── JS tarafinin adim yorumlayicisi (Python senaryo_py'nin karsiligi) ─────────
async function senaryoJs(sk, s) {
  await sk.komut({ k: "sifirla", kayitlar: s.kayitlar, cihaz: s.cihaz ?? null });
  const depo = E.bellekDepo();
  const ortam = { fetch };
  const jetonlu = E.httpOnay(sk.taban, { fetch });
  const onaylar = [];
  const anliklar = [];
  let cihaz = null;
  for (const adim of s.adimlar) {
    if (adim.tur === "kart") {
      await sk.komut({ k: "kart", alanlar: adim.alanlar });
    } else if (adim.tur === "disk") {
      if ("kal_metin" in adim) {
        await depo.kalYaz(utf8Kodla(adim.kal_metin));
      } else {
        const son = ((await depo.durumOku()) ?? { son_sira: 0 }).son_sira;
        await depo.veriEkle(hexten((await sk.komut({ k: "disk", adim, son_sira: son })).hex));
      }
    } else if (adim.tur === "durum") {
      await depo.durumYaz({ son_sira: 0, bayt: 0, onaylanan: 0, kimlik: null, ...(await depo.durumOku()),
        ...adim.alanlar });
    } else if (adim.tur === "esitle") {
      const onayAd = adim.onay ?? "kart";
      if (adim.imzali && !cihaz) {
        cihaz = { kimlik: "0011223344556677", n: s.cihaz.n, K: hexten(s.cihaz.K), ad: "PC", sayac: 0, acilis: "" };
      }
      const ic = adim.imzali ? E.imzaliOnay(cihaz, sk.taban, ortam) : jetonlu;
      const onay = async (sira) => {
        onaylar.push([sira, await depo.veriBoyu()]);
        if (onayAd === "patlayan") throw new AgHatasi("ag koptu");
        await ic(sira);
      };
      const e = new E.Esitleyici({
        tabanUrl: sk.taban, fetch, depo, onay: onayAd === "yok" ? null : onay, onayBekleMs: 10,
        ...("bayt" in adim ? { bayt: adim.bayt } : {}),
        ...(adim.imzali ? { istek: E.imzaliIstek(cihaz, ortam) } : {}),
      });
      let sonuc = null;
      let hata = null;
      try {
        sonuc = await e.esitle("azami_tur" in adim ? { azamiTur: adim.azami_tur } : {});
      } catch (h) {
        hata = { tur: hataTuru(h), mesaj: String(h && h.message) };
      }
      const a = depo.anlik();
      if (sonuc && sonuc.kalibrasyon_arsiv !== undefined) {
        sonuc.kalibrasyon_arsiv = a.arsivler.findIndex((x) => x.ad === sonuc.kalibrasyon_arsiv);
      }
      const kd = await sk.komut({ k: "durum" });
      anliklar.push({
        sonuc, hata, veri: hex(a.veri), durum: a.durum, kal: a.kal === null ? null : hex(a.kal),
        arsivler: a.arsivler.map((x) => hex(x.bayt)), onaylar: onaylar.map((x) => [...x]),
        kart_onay: kd.onay, imzali: kd.imzali, ret_401: kd.ret_401,
      });
    } else {
      throw new Error(`bilinmeyen adim: ${adim.tur}`);
    }
  }
  return { ad: s.ad, anliklar };
}

// ── testler ─────────────────────────────────────────────────────────────
let SK;
let PY_SONUC;

before(async () => {
  PY_SONUC = pyKos(SENARYOLAR);
  PY_SONUC.catch(() => {});                       // hata her testte ayrica raporlanir
  SK = await SahteKart.baslat();
});

after(async () => {
  if (SK) await SK.kapat();
});

SENARYOLAR.forEach((s, i) => {
  test(`capraz: ${s.ad}`, async () => {
    const js = await senaryoJs(SK, s);
    s.denetle(js.anliklar.map(normal));            // B72.E iddiasi JS sonucunda (Python'a sormadan)
    const py = (await PY_SONUC)[i];
    assert.equal(py.ad, s.ad);
    assert.equal(js.anliklar.length, py.anliklar.length);
    js.anliklar.forEach((a, j) => {
      assert.deepStrictEqual(normal(a), normal(py.anliklar[j]), `${s.ad}: ${j}. esitleme adimi Python'dan farkli`);
    });
  });
});

test("Python senaryo kosusu bos degil (capraz karsilastirma bir sey olcuyor)", async () => {
  const py = await PY_SONUC;
  assert.equal(py.length, SENARYOLAR.length);
  const yeni = py.flatMap((s) => s.anliklar).filter((a) => a.sonuc && a.sonuc.yeni_kayit > 0).length;
  const hatali = py.flatMap((s) => s.anliklar).filter((a) => a.hata).length;
  assert.ok(yeni >= 15 && hatali >= 6, `yeni kayitli adim ${yeni}, hatali adim ${hatali}`);
});

// ── kalibrasyon birlestirme uc durumlari: Python'un == / dict / dogruluk kurallari ──────────
const KY = (no, ek = {}) => ({ no, unix: 5, acilis: 1, tur: 0, kaynak: 0, not: "n", kal: { a: 1 }, ...ek });
const CAKISMA = [
  [null, { kayitlar: [] }], [1, { kayitlar: [] }], [[], { kayitlar: [] }], ["x", { kayitlar: [] }],
  [{}, { kayitlar: [KY(1)] }], [{ kayitlar: null }, { kayitlar: [] }], [{ kayitlar: "" }, { kayitlar: [] }],
  [{ kayitlar: {} }, { kayitlar: [] }], [{ kayitlar: { a: 1 } }, { kayitlar: [] }],
  [{ kayitlar: "ab" }, { kayitlar: [] }], [{ kayitlar: [1] }, { kayitlar: [] }],
  [{ kayitlar: [[1]] }, { kayitlar: [] }], [{ kayitlar: [{}] }, { kayitlar: [] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1)] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1, { not: "x", tur: 3 })] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1, { kartta_bozuk: true })] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1, { unix: 6 })] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1), KY(2)] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [KY(1, { ek: 1 })] }],
  [{ kayitlar: [KY(1, { kal: { a: true } })] }, { kayitlar: [KY(1)] }],
  [{ kayitlar: [KY(1, { kal: { a: 1, b: 2 } })] }, { kayitlar: [KY(1, { kal: { b: 2, a: 1 } })] }],
  [{ kayitlar: [KY(1, { kal: [1, 2] })] }, { kayitlar: [KY(1, { kal: [2, 1] })] }],
  [{ kayitlar: [KY(true)] }, { kayitlar: [KY(1)] }],
  [{ kayitlar: [KY("1")] }, { kayitlar: [KY(1)] }],
  [{ kayitlar: [KY(null)] }, { kayitlar: [KY(null)] }],
  [{ kayitlar: [KY([1])] }, { kayitlar: [] }],
  [{ kayitlar: [KY({ a: 1 })] }, { kayitlar: [] }],
  [{ kayitlar: [KY(1), KY(1, { unix: 9 })] }, { kayitlar: [KY(1, { unix: 9 })] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: [{}] }],
  [{ kayitlar: [KY(1)] }, { kayitlar: ["x"] }],
  [{ kayitlar: [KY(1, { kal: null })] }, { kayitlar: [KY(1, { kal: 0 })] }],
  [{ kayitlar: [KY(1, { kal: 0 })] }, { kayitlar: [KY(1, { kal: false })] }],
  [{ kayitlar: [KY(1, { kal: "" })] }, { kayitlar: [KY(1, { kal: [] })] }],
  [{ kayitlar: [KY(1, { kal: {} })] }, { kayitlar: [KY(1, { kal: [] })] }],
  [{ kayitlar: [KY(1, { kal: 1.5 })] }, { kayitlar: [KY(1, { kal: 1.5 })] }],
];
const BOZUK = [
  [{ kayitlar: [KY(1), { no: 2, bozuk: true }] }, { kayitlar: [KY(1), KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, null],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, { kayitlar: [KY(2, { bozuk: true })] }],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, { kayitlar: [KY(2, { kartta_bozuk: true })] }],
  [{ kayitlar: [{ no: 2, bozuk: 0 }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: [] }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: {} }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: "e" }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: [0] }] }, { kayitlar: [KY(2, { bozuk: "" })] }],
  [{ kayitlar: [{ bozuk: true }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ bozuk: true }] }, { kayitlar: [KY(null)] }],
  [{ kayitlar: [{ no: [2], bozuk: true }] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: true }, 5, "x", null] }, { kayitlar: [KY(2)] }],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, { kayitlar: [KY(2), 7] }],
  [{ kayitlar: [{ no: true, bozuk: true }] }, { kayitlar: [KY(1)] }],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, "metin"],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, { kayitlar: [KY(2, { bozuk: false })] }],
  [{ kayitlar: [{ no: 2, bozuk: true }] }, { kayitlar: { 2: KY(2) } }],
];
const PY_HATA = { TypeError: "TypeError", AnahtarHatasi: "KeyError", NitelikHatasi: "AttributeError" };

test("kalCakisir: uc durumlar Python _kal_cakisir ile ayni", async () => {
  for (const [eski, yeni] of CAKISMA) {
    const py = await SK.komut({ k: "kal_cakisir", eski, yeni });
    let js;
    try {
      js = { sonuc: E.kalCakisir(kopya(eski), kopya(yeni)) };
    } catch (h) {
      js = { hata: PY_HATA[h.name] ?? h.name };
    }
    assert.deepStrictEqual(js, py, `eski=${JSON.stringify(eski)} yeni=${JSON.stringify(yeni)}`);
  }
});

test("kalBozukBirlestir: uc durumlar Python _kal_bozuk_birlestir ile ayni", async () => {
  for (const [veri, eski] of BOZUK) {
    const py = await SK.komut({ k: "kal_bozuk", veri, eski });
    let js;
    const v = kopya(veri);
    try {
      js = { bozuk: E.kalBozukBirlestir(v, kopya(eski)), veri: v };
    } catch (h) {
      js = { hata: PY_HATA[h.name] ?? h.name };
    }
    assert.deepStrictEqual(js, py, `veri=${JSON.stringify(veri)} eski=${JSON.stringify(eski)}`);
  }
});

test("jsonGirintili == Python json.dumps(indent=1, ensure_ascii=False)", async () => {
  const DEGERLER = [KAL, KAL_KART, KAL_BOZUK2, { a: [], b: {}, c: [[]], d: [{}], e: "" },
    "ş\"\\\n\t\r\b\f\u0001\u001f\u007f   😀",
    [1e-5, 1.5e-7, 0.0001, 0.00012, 0.000099, -2.5e-07, 123.456, -0.5, 1e21, 2 ** 53, 2 ** 60, 1e16,
      0.1 + 0.2, 5e-324, 1.7976931348623157e308, -0, 1e-7, 123456789.123, 9007199254740.5],
    { "": null, " ": true, x: false }, [], {}, 0, -1, "metin", null, true];
  for (const d of DEGERLER) {
    const py = await SK.komut({ k: "json", deger: d });
    assert.equal(E.jsonGirintili(d), py.metin, JSON.stringify(d));
  }
  assert.throws(() => E.jsonGirintili("\ud800"), DegerHatasi);   // Python da UTF-8'e yazamaz
});

// ── JS'e ozgu birimler ───────────────────────────────────────────────────
test("B72.E8 httpOnay jetonu /akis'ten alip X-Olcum + X-Jeton ile Go<sira> yollar", async () => {
  await SK.komut({ k: "sifirla", kayitlar: [[3, 1]], cihaz: null });
  await E.httpOnay(SK.taban, { fetch })(42);
  assert.deepEqual((await SK.komut({ k: "durum" })).komutlar, ["Go42"]);
});

test("B72.E16 ayni depoya ikinci esitleme kilit yuzunden BASLAMAZ, hicbir sey yazmaz", async () => {
  await SK.komut({ k: "sifirla", kayitlar: [[20, 1]], cihaz: null });
  const depo = E.bellekDepo();
  const birak = await depo.kilitAl();
  await assert.rejects(new E.Esitleyici({ tabanUrl: SK.taban, fetch, depo }).esitle(), CalismaHatasi);
  assert.equal(await depo.veriBoyu(), 0);
  assert.equal(await depo.durumOku(), null);
  await birak();
  // es zamanli iki esitleme: biri reddedilir, digeri tamamlar; akis tekrarsiz
  const e = new E.Esitleyici({ tabanUrl: SK.taban, fetch, depo });
  const r = await Promise.allSettled([e.esitle(), e.esitle()]);
  assert.deepEqual(r.map((x) => x.status).sort(), ["fulfilled", "rejected"]);
  assert.ok(r.find((x) => x.status === "rejected").reason instanceof CalismaHatasi);
  assert.equal(hex(depo.anlik().veri), hex(kartAkisi([[20, 1]])));
  await e.esitle();                                // kilit birakildi
});

test("istek enjeksiyonu: /kayit/veri sira+bayt (alt sinir), sonra /kal/liste; fetch kullanilmaz", async () => {
  await SK.komut({ k: "sifirla", kayitlar: [[12, 1]], cihaz: null });
  const istekler = [];
  const istek = (taban, yol, args) => {
    istekler.push([yol, args]);
    const q = args.map(([a, d]) => `${a}=${d}`).join("&");
    return fetch(taban + yol + (q ? `?${q}` : ""));
  };
  const yasak = () => { throw new Error("fetch cagrilmamali"); };
  const r = await new E.Esitleyici({ tabanUrl: SK.taban + "//", fetch: yasak, depo: E.bellekDepo(), istek, bayt: 10 })
    .esitle();
  assert.equal(r.son_sira, 12);
  assert.deepEqual(istekler[0], ["/kayit/veri", [["sira", "1"], ["bayt", String(E.EN_AZ_BAYT)]]]);
  assert.equal(istekler.at(-1)[0], "/kal/liste");
  assert.ok(istekler.slice(0, -1).every(([y]) => y === "/kayit/veri"));
});

test("/kayit/veri HTTP hatasi esitlemeyi durdurur (HttpHatasi), depo bos", async () => {
  await SK.komut({ k: "sifirla", kayitlar: [[3, 1]], cihaz: null });
  const depo = E.bellekDepo();
  const istek = async (taban, yol) => fetch(taban + "/yok" + yol);
  await assert.rejects(new E.Esitleyici({ tabanUrl: SK.taban, depo, istek }).esitle(),
    (h) => h instanceof HttpHatasi && h.durum === 404);
  assert.equal(await depo.veriBoyu(), 0);
});

test("kurucu girdileri denetler", () => {
  const depo = E.bellekDepo();
  assert.throws(() => new E.Esitleyici({ tabanUrl: 5, fetch, depo }), TypeError);
  assert.throws(() => new E.Esitleyici({ tabanUrl: "http://x", depo }), TypeError);
  assert.throws(() => new E.Esitleyici({ tabanUrl: "http://x", fetch }), TypeError);
  assert.throws(() => new E.Esitleyici({ tabanUrl: "http://x", fetch, depo, onay: 1 }), TypeError);
  assert.throws(() => new E.Esitleyici({ tabanUrl: "http://x", fetch, depo, bayt: 1.5 }), TypeError);
  assert.equal(new E.Esitleyici({ tabanUrl: "http://x//", fetch, depo }).taban, "http://x");
  assert.equal(new E.Esitleyici({ tabanUrl: "http://x", fetch, depo, bayt: 5 }).bayt, E.EN_AZ_BAYT);
});

test("bellekDepo: ekle/kirp/oku, kirp uzatirsa sifir (Python truncate), arsiv adi cakismaz", async () => {
  const sabit = new Date(2026, 9, 2, 3, 4, 5);
  const d = E.bellekDepo({ simdi: () => sabit });
  for (let i = 0; i < 3000; i++) await d.veriEkle(Uint8Array.of(i & 0xFF, 1, 2));
  assert.equal(await d.veriBoyu(), 9000);
  assert.deepEqual([...(await d.veriOku(8997))], [2999 & 0xFF, 1, 2]);
  await d.veriKirp(4);
  await d.veriKirp(6);
  assert.deepEqual([...(await d.veriOku(0))], [0, 1, 2, 1, 0, 0]);
  const a1 = await d.kalArsivle(Uint8Array.of(1));
  const a2 = await d.kalArsivle(Uint8Array.of(2));
  const a3 = await d.kalArsivle(Uint8Array.of(3));
  assert.deepEqual([a1, a2, a3], ["kalibrasyon-20261002-030405.json", "kalibrasyon-20261002-030405-1.json",
    "kalibrasyon-20261002-030405-2.json"]);
  const ds = { son_sira: 1, bayt: 2, onaylanan: 0, kimlik: null };
  await d.durumYaz(ds);
  ds.son_sira = 99;                                // depo kopyasini tutar
  assert.equal((await d.durumOku()).son_sira, 1);
});
