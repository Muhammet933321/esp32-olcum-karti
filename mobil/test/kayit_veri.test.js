// 5D-3 — kayit verisi: cozme, liste, kayit gorunumunun serileri, aralik okumasi (A24–A26, A41).
// Akis GERCEK bicimde (ortak paketleyiciler); degerler ikili kesir: beklenenler elle hesaplanir.
import { describe, it, expect } from "vitest";
import { seriHazirla } from "@ortak/grafik.js";
import { KayitVeriHatasi, TURLER, aralikOkuma, islemciKur, listeKur, oturumGorunumu, veriKur } from "../src/cekirdek/kayit_veri.js";
import { DEPO_YOLU, KayitIstemciHatasi, depoAdresi, kayitIstemciKur } from "../src/cekirdek/kayit_istemci.js";
import { Akis, ikiOturum } from "./yardim/akis_ornek.mjs";

const AKIS_KIMLIK = 7;

describe("veriKur", () => {
  it("akis cozulur: kayit / oturum sayilari, son siralar; bos ve olmayan dosya bos veri", () => {
    const { bayt, a, b } = ikiOturum();
    const v = veriKur(bayt, AKIS_KIMLIK);
    expect([...v.oturumlar.keys()]).toEqual([a, b]);
    expect(v).toMatchObject({ kimlik: AKIS_KIMLIK, bayt: bayt.length, gecerliBayt: bayt.length, uyari: 0 });
    expect(v.sonSira.get(a)).toBeGreaterThan(a);
    expect(v.sonSira.get(b)).toBe(v.kayitlar.at(-1).sira);
    expect(veriKur(new Uint8Array(0))).toMatchObject({ bayt: 0, gecerliBayt: 0, kimlik: null });
    expect(veriKur(new Uint8Array(0)).oturumlar.size).toBe(0);
    expect(veriKur(bayt.buffer.slice(bayt.byteOffset, bayt.byteOffset + bayt.length)).kayitlar.length).toBe(v.kayitlar.length);   // ArrayBuffer da olur
  });

  it("sondaki YARIM kayit (esitleme o an yaziyor) disarida kalir, gerisi cozulur; ortadaki bozukluk sonrasini keser", () => {
    const { bayt } = ikiOturum();
    const tam = veriKur(bayt);
    const yarim = veriKur(bayt.subarray(0, bayt.length - 7));
    expect(yarim.kayitlar.length).toBe(tam.kayitlar.length - 1);
    expect(yarim.gecerliBayt).toBeLessThan(bayt.length - 7);
    expect(yarim.bayt).toBe(bayt.length - 7);
    const bozuk = Uint8Array.from(bayt);
    bozuk[200] ^= 0xff;
    expect(veriKur(bozuk).kayitlar.length).toBeLessThan(tam.kayitlar.length);
    expect(veriKur(bozuk).gecerliBayt).toBeLessThanOrEqual(200);
  });
});

describe("listeKur (A25, A41)", () => {
  const { bayt, a, b } = ikiOturum();
  const veri = veriKur(bayt, AKIS_KIMLIK);
  const kart = (ek = {}) => ({ kimlik: AKIS_KIMLIK, aktif: 0, oturumlar: [
    { id: a, tur: 1, hiz_ms: 1000, unix_s: 1790000000, nokta: 60, durum: 2, son: veri.sonSira.get(a) },
    { id: b, tur: 1, hiz_ms: 1000, unix_s: 1790003600, nokta: 5, durum: 1, son: veri.sonSira.get(b) },
    { id: 999, tur: 2, hiz_ms: 1000, unix_s: 1790007200, nokta: 12, durum: 2, son: 1100 },
  ], ...ek });

  it("kart yokken (disarida): yalniz telefondaki kopya, YENIDEN ESKIYE; ad, etiket, tarih, sure, nokta", () => {
    const l = listeKur(veri);
    expect(l.map((s) => s.oturum)).toEqual([b, a]);
    expect(l[1]).toMatchObject({ oturum: a, tur: "olcum", ad: "Akü şarj", etiketler: ["akü", "deneme"], nokta: 60, nerede: "telefon", durum: "bitti", eksik: false, yerelde: true });
    expect(l[1].sure).toBe("00:01:00");                    // BASLA 5000 ms, son nokta 6000 + 59 x 1000
    expect(l[1].tarih).toMatch(/^2026-09-2\d \d\d:\d\d:\d\d$/);
    expect(l[0]).toMatchObject({ oturum: b, ad: null, nokta: 5, nerede: "telefon", durum: "acik" });
  });

  it("kart varken: nerede = ikisi / kart; kartta daha yeni kayit varsa 'eksik'; kayitta olan 'kayitta'", () => {
    const l = listeKur(veri, { kart: kart({ aktif: b }) });
    expect(l.map((s) => [s.oturum, s.nerede])).toEqual([[999, "kart"], [b, "ikisi"], [a, "ikisi"]]);
    expect(l[0]).toMatchObject({ tur: "pil", yerelde: false, ad: null, sure: null, nokta: 12 });
    expect(l[1].durum).toBe("kayitta");
    expect(l.every((s) => s.eksik === false)).toBe(true);
    const ileri = kart();
    ileri.oturumlar[1].son += 3;                           // kart b'ye 3 kayit daha yazmis
    expect(listeKur(veri, { kart: ileri }).find((s) => s.oturum === b).eksik).toBe(true);
    // Telefon bos, kart var: hepsi 'kart'.
    expect(listeKur(null, { kart: kart() }).map((s) => s.nerede)).toEqual(["kart", "kart", "kart"]);
    expect(listeKur(veriKur(new Uint8Array(0)), { kart: kart() }).length).toBe(3);
  });

  it("bozuk / eksik kart govdesi yok sayilir (liste telefondan); ATMAZ", () => {
    for (const k of [null, undefined, {}, { oturumlar: "x" }, "metin", 5, []]) {
      expect(listeKur(veri, { kart: k }).map((s) => s.nerede), JSON.stringify(k)).toEqual(["telefon", "telefon"]);
    }
    expect(listeKur(null)).toEqual([]);
  });

  it("arama (Turkce karakter duyarsiz, ad + etiket + not; #numara) ve tur suzgeci", () => {
    expect(TURLER).toEqual(["hepsi", "olcum", "pil", "skop"]);
    expect(listeKur(veri, { arama: "AKU" }).map((s) => s.oturum)).toEqual([a]);
    expect(listeKur(veri, { arama: "deneme sarj" }).map((s) => s.oturum)).toEqual([a]);
    expect(listeKur(veri, { arama: "yuk baglandi" }).map((s) => s.oturum)).toEqual([a]);
    expect(listeKur(veri, { arama: `#${b}` }).map((s) => s.oturum)).toEqual([b]);
    expect(listeKur(veri, { arama: "yok-boyle-bir-sey" })).toEqual([]);
    expect(listeKur(veri, { kart: kart(), tur: "pil" }).map((s) => s.oturum)).toEqual([999]);
    expect(listeKur(veri, { kart: kart(), tur: "olcum" }).map((s) => s.oturum)).toEqual([b, a]);
    expect(listeKur(veri, { tur: "sacma" }).length).toBe(2);           // bilinmeyen suzgec: hepsi
    expect(listeKur(veri, { arama: 5 }).length).toBe(2);
  });
});

describe("oturumGorunumu ve aralikOkuma (A26, A41)", () => {
  const { bayt, a, b } = ikiOturum();
  const veri = veriKur(bayt, AKIS_KIMLIK);

  it("seriler: V / I / W ort + min / maks zarflari, ORTAK t; degerler kalibrasyonla (volt = kod / 8)", () => {
    const g = oturumGorunumu(veri, a);
    expect(g).toMatchObject({ oturum: a, tur: "nokta", adet: 60, tahmini: false });
    expect(g.seriler.map((s) => s.ad)).toEqual(["V", "V min", "V maks", "I", "I min", "I maks", "W", "W min", "W maks"]);
    const V = g.seriler[0], I = g.seriler[3], W = g.seriler[6];
    expect(V.t.length).toBe(60);
    expect(g.seriler.every((s) => s.t === V.t)).toBe(true);
    expect([g.t0, g.t1]).toEqual([1000, 60000]);           // oturum basindan gecen ms
    expect(V.y[0]).toBeCloseTo(10, 9);
    expect(V.y[59]).toBeCloseTo(17.375, 9);
    expect(g.seriler[1].y[0]).toBeCloseTo(9, 9);           // min kodu = kod - 8 -> 1 V asagi
    expect(I.y[30]).toBeCloseTo(0.5, 9);
    expect(W.y[10]).toBeCloseTo(11.25 * 0.5, 9);
    expect([V.eksen, I.eksen, W.eksen, V.birim, I.birim, W.birim]).toEqual(["sol", "sag", "sag", "V", "A", "W"]);
    expect(g.seriler[1]).toMatchObject({ zarf: true });
    expect(g.baslik).toMatchObject({ oturum: a, ad: "Akü şarj", tur: "olcum", sure: "00:01:00" });
    expect(g.notlar).toEqual([{ metin: "yük bağlandı", genel: false, gecen: "00:00:11" }]);
  });

  it("piramit Worker tarafinda kurulur ve Grafik onu YENIDEN KURMAZ (ayni t / y nesnesi)", () => {
    const g = oturumGorunumu(veri, a);
    for (const s of g.seriler) {
      expect(s.oz.t).toBe(s.t);
      expect(s.oz.y).toBe(s.y);
      expect(seriHazirla(s).oz).toBe(s.oz);
    }
    // Yapisal kopyadan (Worker -> ana is parcacigi) sonra da ayni kimlik korunur.
    const kopya = structuredClone(g);
    for (const s of kopya.seriler) expect(seriHazirla(s).oz).toBe(s.oz);
    expect(kopya.seriler[0].y[59]).toBeCloseTo(17.375, 9);
  });

  it("'zaman tahmini' isareti seri bilgisinden tasinir (curutucu 5D Y6)", () => {
    const v = veriKur(ikiOturum().bayt, AKIS_KIMLIK);
    expect(oturumGorunumu(v, a).tahmini).toBe(false);
    const h = v.onbellek.get(a);
    v.onbellek.set(a, { ...h, tahmini: [false, true] });     // kart yeniden baslamis, ikinci parcanin yeri tahmini
    expect(oturumGorunumu(v, a).tahmini).toBe(true);
    v.onbellek.set(a, { ...h, tahmini: [] });
    expect(oturumGorunumu(v, a).tahmini).toBe(false);
  });

  it("olmayan oturum / bos veri: null", () => {
    expect(oturumGorunumu(veri, 12345)).toBe(null);
    expect(oturumGorunumu(null, a)).toBe(null);
    expect(aralikOkuma(veri, 12345, 0, 1)).toBe(null);
    expect(aralikOkuma(null, a, 0, 1)).toBe(null);
  });

  it("aralik okumasi HAM veriden: ort / min / maks / adet ve enerji; sinirlar ters verilse de ayni", () => {
    const tum = aralikOkuma(veri, a, 1000, 60000);
    expect(tum.v.adet).toBe(60);
    expect(tum.v.ort).toBeCloseTo((10 + 17.375) / 2, 6);
    expect(tum.v.min).toBeCloseTo(9, 9);                   // min ZARFTAN (min kodlari), ortalamadan degil
    expect(tum.v.maks).toBeCloseTo(18.375, 9);
    expect(tum.i.ort).toBeCloseTo(0.5, 9);
    expect(tum.sure).toBe("00:00:59");
    expect(tum.dt).toBe(59000);
    // 0.5 A x 59 s = 29.5 As = 8.194 mAh; Wh = ort W x sure.
    expect(tum.enerji.mah).toBeCloseTo(0.5 * 59 / 3.6, 3);
    expect(tum.enerji.wh).toBeCloseTo(((10 + 17.375) / 2) * 0.5 * 59 / 3600, 4);
    // Dar aralik: yalniz ilk 10 nokta (1000 .. 10000 ms).
    const dar = aralikOkuma(veri, a, 1000, 10000);
    expect(dar.v.adet).toBe(10);
    expect(dar.v.ort).toBeCloseTo(10.5625, 6);
    expect(aralikOkuma(veri, a, 10000, 1000)).toEqual(dar);
    for (const [x, y] of [[NaN, 1], [1, Infinity], [undefined, 5]]) expect(aralikOkuma(veri, a, x, y)).toBe(null);
  });

  it("acik oturum (BITIR yok) da gorunur; nokta kaydi olmayan oturum 'yok' turunde bos seriyle", () => {
    expect(oturumGorunumu(veri, b)).toMatchObject({ tur: "nokta", adet: 5 });
    const akis = new Akis(10);
    const bos = akis.basla();
    akis.ad(bos, "boş oturum");
    const v2 = veriKur(akis.bayt());
    expect(oturumGorunumu(v2, bos)).toMatchObject({ tur: "yok", adet: 0, seriler: [], t0: 0, t1: 0 });
    expect(aralikOkuma(v2, bos, 0, 100)).toBe(null);
  });
});

describe("islemci (Worker ve yedek AYNI kod)", () => {
  const { bayt, a } = ikiOturum();

  it("yukle -> liste -> oturum -> okuma; yukle dosyayi verilen adresten ISTER", async () => {
    const istenen = [];
    const i = islemciKur({ getir: async (url) => { istenen.push(url); return bayt; } });
    expect(await i.isle("liste", {})).toEqual([]);          // yuklenmeden: bos
    expect(await i.isle("yukle", { url: "/_depo/0123456789abcdef/kayitlar.kyt", akisKimlik: 7 })).toEqual({ kayit: veriKur(bayt).kayitlar.length, oturum: 2, bayt: bayt.length, gecerliBayt: bayt.length, uyari: 0 });
    expect(istenen).toEqual(["/_depo/0123456789abcdef/kayitlar.kyt"]);
    expect((await i.isle("liste", {})).length).toBe(2);
    expect((await i.isle("oturum", { oturum: a })).adet).toBe(60);
    expect((await i.isle("okuma", { oturum: a, tA: 1000, tB: 10000 })).v.adet).toBe(10);
    await i.isle("bosalt");
    expect(await i.isle("liste", {})).toEqual([]);
  });

  it("yeniden yuklemede oturum onbellegi BAYAT kalmaz: buyuyen oturumun yeni noktalari gorunur (curutucu 5D Y7)", async () => {
    const kur = (adet) => { const ak = new Akis(100); const id = ak.basla(); ak.noktalar(id, { adet, v0: 10, dv: 0.125 }); return { bayt: ak.bayt(), id }; };
    const kisa = kur(40), uzun = kur(80);
    expect(kisa.id).toBe(uzun.id);
    let dosya = kisa.bayt;
    const i = islemciKur({ getir: async () => dosya });
    await i.isle("yukle", { url: "/x" });
    expect((await i.isle("oturum", { oturum: kisa.id })).adet).toBe(40);
    expect((await i.isle("okuma", { oturum: kisa.id, tA: 0, tB: 1e9 })).v.adet).toBe(40);
    dosya = uzun.bayt;                                         // esitleme ayni oturuma 40 nokta daha ekledi
    await i.isle("yukle", { url: "/x" });
    expect((await i.isle("oturum", { oturum: kisa.id })).adet).toBe(80);
    expect((await i.isle("okuma", { oturum: kisa.id, tA: 0, tB: 1e9 })).v.adet).toBe(80);
    // Iki AYRI veri nesnesi onbellegi paylasmaz.
    expect(veriKur(kisa.bayt).onbellek).not.toBe(veriKur(uzun.bayt).onbellek);
  });

  it("dosya okunamazsa 'okunamadi' ve ESKI veri yerinde kalir; getir null donerse bos kopya; bilinmeyen is 'bicim'", async () => {
    let atsin = false;
    const i = islemciKur({ getir: async () => { if (atsin) throw new Error("gizli yol"); return bayt; } });
    await i.isle("yukle", { url: "/x" });
    atsin = true;
    await expect(i.isle("yukle", { url: "/x" })).rejects.toMatchObject({ tur: "okunamadi" });
    expect((await i.isle("liste", {})).length).toBe(2);
    await expect(i.isle("yukle", {})).rejects.toBeInstanceOf(KayitVeriHatasi);
    await expect(i.isle("sil-hepsini", {})).rejects.toMatchObject({ tur: "bicim" });
    const bos = islemciKur({ getir: async () => null });
    expect(await bos.isle("yukle", { url: "/x" })).toMatchObject({ kayit: 0, oturum: 0 });
    expect(() => islemciKur({})).toThrow(TypeError);
  });
});

describe("kayit istemcisi (ana is parcacigi)", () => {
  const { bayt, a } = ikiOturum();
  const yedekKur = () => islemciKur({ getir: async () => bayt });

  // Sahte Worker: mesaji GERCEK islemciyle yanitlar (yapisal kopya ile, Worker siniri gibi).
  function sahteIsci() {
    const islemci = yedekKur();
    const w = {
      gonderilen: [], onmessage: null, onerror: null, bitti: false,
      postMessage(m) {
        w.gonderilen.push(m);
        const { no, is, ...arg } = structuredClone(m);
        islemci.isle(is, arg).then(
          (sonuc) => w.onmessage({ data: structuredClone({ no, tamam: true, sonuc }) }),
          (h) => w.onmessage({ data: { no, tamam: false, tur: h.tur } }),
        );
      },
      terminate() { w.bitti = true; },
    };
    return w;
  }

  it("depoAdresi: DepoYolu.kt ile ayni bicim; gecersiz kimlik null", () => {
    expect(DEPO_YOLU).toBe("/_depo/");
    expect(depoAdresi("0123456789abcdef")).toBe("/_depo/0123456789abcdef/kayitlar.kyt");
    for (const k of [null, "", "abc", "0123456789ABCDEF", "../kasa", "0123456789abcdef/"]) expect(depoAdresi(k)).toBe(null);
  });

  it("Worker varsa is ONA gider; yanitlar numarayla eslesir (sira karissa da)", async () => {
    let w = null;
    const k = kayitIstemciKur({ isciKur: () => { w = sahteIsci(); return w; }, yedekKur: () => { throw new Error("yedek kullanilmamali"); } });
    await k.cagir("yukle", { url: "/x", akisKimlik: 7 });
    const [liste, oturum, okuma] = await Promise.all([k.cagir("liste", {}), k.cagir("oturum", { oturum: a }), k.cagir("okuma", { oturum: a, tA: 1000, tB: 10000 })]);
    expect(liste.length).toBe(2);
    expect(oturum.seriler[0].y.length).toBe(60);
    expect(okuma.v.adet).toBe(10);
    expect(w.gonderilen.map((m) => [m.no, m.is])).toEqual([[1, "yukle"], [2, "liste"], [3, "oturum"], [4, "okuma"]]);
    expect(k.isciVar()).toBe(true);
    await expect(k.cagir("sacma")).rejects.toMatchObject({ tur: "bicim" });
    k.kapat();
    expect(w.bitti).toBe(true);
  });

  it("Worker yoksa / kurulamiyorsa AYNI islemci ana is parcaciginda (yedek); sonuc ayni", async () => {
    for (const isciKur of [null, () => { throw new Error("Worker yok"); }]) {
      const k = kayitIstemciKur({ isciKur, yedekKur });
      await k.cagir("yukle", { url: "/x" });
      expect((await k.cagir("liste", {})).length).toBe(2);
      expect(k.isciVar()).toBe(false);
      await expect(k.cagir("sacma")).rejects.toBeInstanceOf(KayitIstemciHatasi);
    }
    expect(() => kayitIstemciKur({})).toThrow(TypeError);
  });

  it("Worker COKERSE bekleyen cagrilar 'ic-hata' ile biter (asili kalmaz) ve sonraki cagri yedege gecer", async () => {
    let w = null;
    const k = kayitIstemciKur({ isciKur: () => { w = { postMessage() {}, terminate() {}, onmessage: null, onerror: null }; return w; }, yedekKur });
    const asili = k.cagir("liste", {});
    w.onerror(new Error("yuklenemedi"));
    await expect(asili).rejects.toMatchObject({ tur: "ic-hata" });
    await k.cagir("yukle", { url: "/x" });
    expect((await k.cagir("liste", {})).length).toBe(2);
    expect(k.isciVar()).toBe(false);
  });

  it("taninmayan / gec gelen yanit yok sayilir; postMessage atarsa cagri reddedilir", async () => {
    let w = null;
    const k = kayitIstemciKur({ isciKur: () => { w = { postMessage() { throw new Error("kopyalanamadi"); }, terminate() {}, onmessage: null, onerror: null }; return w; }, yedekKur });
    await expect(k.cagir("liste", {})).rejects.toMatchObject({ tur: "ic-hata" });
    expect(() => w.onmessage({ data: { no: 99, tamam: true, sonuc: 1 } })).not.toThrow();
    expect(() => w.onmessage({})).not.toThrow();
  });
});
