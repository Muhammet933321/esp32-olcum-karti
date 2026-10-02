// 2B — imza.js: 1D vektorleri (uretim/vektor_guvenlik.json: C, Python ve JS ayni dosya) +
// Python capraz vektorleri (ortak/test/vektor/kripto.json: kopru/imza.py'nin GERCEK ac / akis_url /
// esles akislari sahte agla yakalandi) + bozuk girdi. Kosu: node --test ortak/test/imza.test.js
import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DegerHatasi, hex, hexten } from "../src/kripto.js";
import * as I from "../src/imza.js";

const V = JSON.parse(readFileSync(new URL("./vektor/kripto.json", import.meta.url), "utf8"));
const G = JSON.parse(readFileSync(new URL("../../uretim/vektor_guvenlik.json", import.meta.url), "utf8"));
const yazi = new TextEncoder();

// Python vektorunde sayac metin (uint64 sinirina kadar); guvenliyse Number, degilse BigInt
const sayacAl = (s) => (BigInt(s) <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(s) : BigInt(s));

// Python hata adi -> JS sinifi
const HATA = { ValueError: DegerHatasi, RuntimeError: I.CalismaHatasi, TypeError: TypeError, HTTPError: I.HttpHatasi };

// Sahte fetch: Python'a verilen AYNI yanitlari sirayla verir, istekleri Python bicimine cevirip kaydeder.
function sahteAg(yanitlar) {
  const kalan = [...yanitlar];
  const istekler = [];
  const fetch = async (url, secenek = {}) => {
    const b = {};
    for (const [a, d] of Object.entries(secenek.headers || {})) b[a.toLowerCase()] = d;
    istekler.push({
      url, yontem: secenek.method || "GET", basliklar: b,
      govde: secenek.body === undefined ? null : hex(secenek.body),
    });
    if (!kalan.length) throw new Error(`beklenmeyen istek: ${url}`);
    const y = kalan.shift();
    return new Response(y.durum === 204 ? null : hexten(y.govde), { status: y.durum, headers: y.basliklar });
  };
  return { fetch, istekler, kalan };
}

function cihazAl(c) {
  return { kimlik: c.kimlik, n: c.n, K: hexten(c.K), ad: c.ad, sayac: c.sayac, acilis: c.acilis };
}

// ── 1D ortak vektorleri (C == Python == JS) ──────────────────────────────
describe("uretim/vektor_guvenlik.json (C, Python ve JS ayni dosya)", () => {
  const p = G.protokol;
  it("pbkdf2 kisa/uc tur (AVR icin dusuk tur)", () => {
    for (const k of [p.pbkdf2_kisa, p.pbkdf2_uc]) assert.equal(hex(I.pbkdf2(k.parola, hexten(k.tuz), k.tur)), k.P);
  });
  it("kanit_istemci, kanit_kart, K (ad 'PC ğ', n 3)", () => {
    const P = hexten(p.P), nk = hexten(p.nk), nc = hexten(p.nc);
    assert.equal(hex(I.kanitIstemci(P, p.kimlik, nk, nc, p.ad)), p.kanit_istemci);
    assert.equal(hex(I.kanitKart(P, p.kimlik, nk, nc, p.n)), p.kanit_kart);
    assert.equal(hex(I.cihazAnahtari(P, p.kimlik, nk, nc, p.n)), p.K);
  });
  it(`kanonik metin + imza (${G.imza.length} ornek) ve akis sorgusu`, () => {
    for (const v of G.imza) {
      const args = v.argumanlar.map(([a, d]) => [a, d]);
      assert.equal(hex(I.kanonik(v.yontem, v.yol, args, v.acilis, v.sayac, hexten(v.govde))), v.kanonik, v.ad);
      assert.equal(I.imzala(hexten(v.K), v.yontem, v.yol, args, v.acilis, v.sayac, hexten(v.govde)), v.imza, v.ad);
      if (v.tam_sorgu) {
        const c = { n: p.n, K: hexten(v.K), acilis: v.acilis };
        assert.equal(I.akisUrlKur(c, "http://x", v.sayac), `http://x/akis?${v.tam_sorgu}`);
      }
    }
  });
});

// ── saf cekirdek: Python capraz ──────────────────────────────────────────
describe("saf cekirdek: Python capraz (kopru/imza.py)", () => {
  it(`yuzdeKodla (${V.imza.yuzde.length} metin: Turkce, emoji, ayrilmis karakterler, NUL/DEL)`, () => {
    for (const v of V.imza.yuzde) assert.equal(I.yuzdeKodla(v.metin), v.kodlu, JSON.stringify(v.metin));
  });
  it(`adGecerli (${V.imza.ad_gecerli.length} ad: 24/25 bayt siniri UTF-8 ile, kontrol karakteri)`, () => {
    for (const v of V.imza.ad_gecerli) assert.equal(I.adGecerli(v.ad), v.gecerli, JSON.stringify(v.ad));
  });
  it("tabanUrl", () => {
    for (const v of V.imza.taban_url) assert.equal(I.tabanUrl(v.host), v.taban, v.host);
  });
  it(`kanonik + imza (${V.imza.kanonik.length} durum; uint64 sayac, ikili govde, bos acilis, Turkce yol)`, () => {
    const K = hexten(V.imza.K);
    for (const v of V.imza.kanonik) {
      const s = sayacAl(v.sayac), g = hexten(v.govde);
      assert.equal(hex(I.kanonik(v.yontem, v.yol, v.argumanlar, v.acilis, s, g)), v.kanonik, `${v.yol} ${v.sayac}`);
      assert.equal(I.imzala(K, v.yontem, v.yol, v.argumanlar, v.acilis, s, g), v.imza);
      assert.equal(I.imzala(K, v.yontem, v.yol, v.argumanlar, v.acilis, BigInt(v.sayac), g), v.imza, "BigInt sayac");
    }
  });
  it("esles hesaplari: P (20 000 tur), kanit_istemci (4 ad), kanit_kart ve K (n 1/3/8/10)", () => {
    const e = V.esles_hesap;
    const P = I.pbkdf2(e.parola, hexten(e.tuz), e.tur);
    assert.equal(hex(P), e.P);
    const nk = hexten(e.nk), nc = hexten(e.nc);
    for (const k of e.kanit_istemci) assert.equal(hex(I.kanitIstemci(P, e.kimlik, nk, nc, k.ad)), k.kanit, k.ad);
    for (const k of e.kart) {
      assert.equal(hex(I.kanitKart(P, e.kimlik, nk, nc, k.n)), k.kanit_kart, `n=${k.n}`);
      assert.equal(hex(I.cihazAnahtari(P, e.kimlik, nk, nc, k.n)), k.K, `n=${k.n}`);
    }
  });
  it(`bilgiDenetle (${V.bilgi_denetle.length} durum: tur sinirlari, tur yalniz JSON tamsayisi (S7), bicimsiz ya da metin olmayan kimlik/tuz/acilis)`, () => {
    for (const v of V.bilgi_denetle) {
      if (v.sonuc.hata) {
        assert.throws(() => I.bilgiDenetle(v.bilgi), HATA[v.sonuc.hata], v.ad);
      } else {
        const r = I.bilgiDenetle(v.bilgi);
        assert.deepEqual({ ...r, tuz: hex(r.tuz) }, v.sonuc, v.ad);
      }
    }
  });
});

// ── istek akislari: Python'un gercek ac / akis_url'u ─────────────────────
describe("istekler: kopru/imza.py ac/akis_url ile ayni istekler (sahte ag)", () => {
  for (const v of V.istekler) {
    it(`${v.ad}`, async () => {
      const ag = sahteAg(v.yanitlar);
      const cihaz = cihazAl(v.cihaz);
      const ortam = { fetch: ag.fetch, simdiMs: () => v.simdi_ms };
      let sonuc;
      try {
        if (v.islev === "ac") {
          const y = await I.ac(cihaz, v.taban, v.yontem, v.yol, v.argumanlar, hexten(v.govde), ortam);
          sonuc = { durum: y.status };
        } else {
          sonuc = { url: await I.akisUrl(cihaz, v.taban, ortam) };
        }
      } catch (h) {
        assert.ok(h instanceof I.HttpHatasi, `beklenmeyen hata: ${h}`);
        sonuc = { hata: "HTTPError", durum: h.durum };
      }
      assert.deepEqual(ag.istekler, v.istekler);
      assert.deepEqual(sonuc, v.sonuc);
      assert.equal(ag.kalan.length, 0);
      assert.equal(cihaz.sayac, v.cihaz_son.sayac);
      assert.equal(cihaz.acilis, v.cihaz_son.acilis);
    });
  }
  it("istekKur saf: POST'ta govde + Content-Type, GET'te govde yok ama imza govdeyi kapsar", () => {
    const c = cihazAl(V.istekler[0].cihaz);
    const p = I.istekKur(c, "http://k/", "POST", "/komut", [], "Go1", 5);
    assert.equal(p.url, "http://k/komut");
    assert.equal(p.secenekler.headers["Content-Type"], "text/plain");
    assert.deepEqual(p.secenekler.body, yazi.encode("Go1"));
    const g = I.istekKur(c, "http://k", "GET", "/kayit/liste", [], yazi.encode("x"), 5);
    assert.equal(g.secenekler.body, undefined);
    assert.equal(g.secenekler.headers["Content-Type"], undefined);
    assert.notEqual(g.secenekler.headers["X-Imza"], I.istekKur(c, "http://k", "GET", "/kayit/liste", [], "", 5)
      .secenekler.headers["X-Imza"]);
  });
  it("ac: her denemede kaydet cagrilir (sayac diske), fetch yoksa TypeError", async () => {
    const v = V.istekler.find((x) => x.ad === "yeniden_dene");
    const ag = sahteAg(v.yanitlar);
    const kayitlar = [];
    await I.ac(cihazAl(v.cihaz), v.taban, v.yontem, v.yol, v.argumanlar, hexten(v.govde),
      { fetch: ag.fetch, simdiMs: () => v.simdi_ms, kaydet: (c) => kayitlar.push([c.sayac, c.acilis]) });
    assert.deepEqual(kayitlar.map((k) => k[0]), [v.simdi_ms, v.simdi_ms, v.simdi_ms + 1]);
    assert.equal(kayitlar[1][1], v.cihaz_son.acilis);
    await assert.rejects(I.ac(cihazAl(v.cihaz), "http://k", "GET", "/x", [], "", {}), TypeError);
  });
});

// ── eslestirme akisi: Python'un gercek esles'i ───────────────────────────
describe("esles: kopru/imza.py esles ile ayni istekler ve ayni K (sahte kart)", () => {
  for (const v of V.esles_akis) {
    it(`${v.ad}${v.sonuc.hata ? ` -> ${v.sonuc.hata}` : ""}`, async () => {
      const ag = sahteAg(v.yanitlar);
      const ortam = { fetch: ag.fetch, rastgele: (n) => hexten(v.nc).subarray(0, n) };
      if (v.sonuc.hata) {
        await assert.rejects(I.esles(v.taban, v.cihaz_adi, v.parola, ortam), HATA[v.sonuc.hata]);
      } else {
        const kayit = [];
        const c = await I.esles(v.taban, v.cihaz_adi, v.parola, { ...ortam, kaydet: (x) => kayit.push(x) });
        assert.deepEqual({ ...c, K: hex(c.K) }, v.sonuc.cihaz);
        assert.equal(kayit.length, 1);
      }
      assert.deepEqual(ag.istekler, v.istekler, "istek dizisi Python'la ayni (red YOLLAMADAN once mi)");
      assert.equal(ag.kalan.length, 0);
    });
  }
  it("kart kaniti yanlisken HICBIR anahtar kaydedilmez", async () => {
    const v = V.esles_akis.find((x) => x.ad === "kart_kaniti_yanlis");
    const ag = sahteAg(v.yanitlar);
    let kaydedildi = false;
    await assert.rejects(I.esles(v.taban, v.cihaz_adi, v.parola, {
      fetch: ag.fetch, rastgele: (n) => hexten(v.nc).subarray(0, n), kaydet: () => { kaydedildi = true; },
    }), I.CalismaHatasi);
    assert.equal(kaydedildi, false);
  });
});

// ── bozuk girdi ve imzanin her alana bagliligi ───────────────────────────
describe("imza her alana bagli; bozuk girdi reddedilir", () => {
  const K = hexten(V.imza.K);
  const temel = ["POST", "/komut", [["a", "1"]], "0f1e2d3c4b5a69788796a5b4c3d2e1f0", 7, yazi.encode("Go1")];
  const imza = (...a) => I.imzala(K, ...a);
  const asil = imza(...temel);
  const degis = (i, d) => {
    const a = [...temel];
    a[i] = d;
    return imza(...a);
  };
  it("yontem / yol / sorgu adi / sorgu degeri / sorgu sirasi / acilis / sayac / govde degisince imza degisir", () => {
    const farklar = [
      degis(0, "GET"), degis(1, "/komut2"), degis(2, [["b", "1"]]), degis(2, [["a", "2"]]),
      degis(2, [["a", "1"], ["b", "2"]]), degis(2, []), degis(3, "0f1e2d3c4b5a69788796a5b4c3d2e1f1"),
      degis(4, 8), degis(5, yazi.encode("Go2")), degis(5, new Uint8Array(0)),
      I.imzala(K.map((x, i) => (i ? x : x ^ 1)), ...temel),
    ];
    for (const f of farklar) assert.notEqual(f, asil);
    assert.notEqual(imza("GET", "/x", [["a", "1"], ["b", "2"]], "", 1, ""), imza("GET", "/x", [["b", "2"], ["a", "1"]], "", 1, ""));
    assert.notEqual(imza("GET", "/x", [["a", "1&b=2"]], "", 1, ""), imza("GET", "/x", [["a", "1"], ["b", "2"]], "", 1, ""));
  });
  it("sayac kesirli / guvensiz Number TypeError (BigInt kullanilmali)", () => {
    assert.throws(() => imza("GET", "/x", [], "", 1.5, ""), TypeError);
    assert.throws(() => imza("GET", "/x", [], "", 2 ** 60, ""), TypeError);
  });
  it("eslesmemis vekil karakter (sorgu, yol, ad, parola) DegerHatasi — Python encode hatasi", () => {
    assert.throws(() => I.yuzdeKodla("\ud800"), DegerHatasi);
    assert.throws(() => imza("GET", "/\udc00", [], "", 1, ""), DegerHatasi);
    assert.throws(() => I.adGecerli("a\ud800"), DegerHatasi);
    assert.throws(() => I.pbkdf2("\ud800".repeat(12), new Uint8Array(16), 1), DegerHatasi);
  });
  it("sorgu degeri metin degilse TypeError (Python da reddeder)", () => {
    assert.throws(() => I.yuzdeKodla(12), TypeError);
  });
  it("sayacSec: max(son + 1, simdi) — saat geri gitse de tekduze", () => {
    assert.equal(I.sayacSec(0, 1759000000500), 1759000000500);
    assert.equal(I.sayacSec(1759000000900, 1759000000500), 1759000000901);
    assert.equal(I.sayacSec(5, 5.9), 6);
    const c = { sayac: 10 };
    assert.equal(I.sonrakiSayac(c, 3), 11);
    assert.equal(c.sayac, 11);
  });
  it("tamsayi: Python int() gibi (bool, ondalik, alt cizgi, bosluk); bozuk metin/null red", () => {
    assert.equal(I.tamsayi(true), 1);
    assert.equal(I.tamsayi(-2.7), -2);
    assert.equal(I.tamsayi(" 20_000 "), 20000);
    assert.throws(() => I.tamsayi("1e4"), DegerHatasi);
    assert.throws(() => I.tamsayi("__1"), DegerHatasi);
    assert.throws(() => I.tamsayi(null), TypeError);
    assert.throws(() => I.tamsayi(NaN), DegerHatasi);
  });
  it("bilgiDenetle: nesne olmayan girdi TypeError", () => {
    assert.throws(() => I.bilgiDenetle(null), TypeError);
    assert.throws(() => I.bilgiDenetle([1]), TypeError);
  });
});
