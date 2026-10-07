// 5P (P3) — `__olcumOrtam` sozlesmesi (plan "Sozlesme", surum 1): anahtarlar, p0 (K8), serit (K9),
// dosyaVer / yazdir (K11, K12), ayarBolumu (K13), komutGitti (anlik izleme sorusu).
import { describe, it, expect } from "vitest";
import { izlemeSorusuKur } from "../src/cekirdek/bildirim.js";
import { paylasKur } from "../src/cekirdek/paylas.js";
import { DosyaHatasi, isAdi } from "../src/ortam/dosya.js";
import { SOZLESME_ANAHTARLARI, SURUM, ortamOlustur } from "../src/ortam/ortam.js";
import { SONUC_MS, soruKur } from "../src/ortam/soru.js";

const bosalt = async () => { for (let i = 0; i < 5; i++) await new Promise((r) => setImmediate(r)); };

function paylasEklentisi() {
  const cagrilar = [];
  const e = {};
  for (const ad of ["baslat", "yaz", "gonder"]) e[ad] = async (v) => { cagrilar.push([ad, v]); return {}; };
  return { e, cagrilar };
}

function olustur(ek = {}) {
  const pe = paylasEklentisi();
  const yazdirilan = [];
  const belge = { title: "Ölçüm Kartı — Kayıt 41 raporu", documentElement: { lang: "tr" }, visibilityState: "visible", addEventListener() {}, removeEventListener() {} };
  const kart = { durum: () => ({ durum: "bagli-degil" }), baglan: async () => ({ durum: "bulunamadi" }) };
  const { ortam, arka } = ortamOlustur({
    kartAl: async () => kart, canliAl: async () => { throw new Error("yok"); }, esitlemeAl: async () => ({ dinle: () => () => {} }),
    depoAl: () => { throw new Error("yok"); }, acilDurdur: async () => ({ tamam: true, basarili: ["192.168.1.7"] }),
    paylas: paylasKur({ eklenti: pe.e }), yazdirEklenti: { yazdir: async (v) => { yazdirilan.push(v); return {}; } },
    belge, araliKur: () => 1, araliSil: () => {}, ...ek,
  });
  return { ortam, arka, pe, yazdirilan, belge };
}

describe("sozlesme yuzu", () => {
  it("anahtarlar TAM sozlesmedeki kume; ad/surum; nesne donuk; tasiyici sozlesmesi", () => {
    const { ortam } = olustur();
    expect(Object.keys(ortam).sort()).toEqual([...SOZLESME_ANAHTARLARI].sort());
    expect(ortam.ad).toBe("telefon");
    expect(ortam.surum).toBe(1);
    expect(SURUM).toBe(1);
    expect(Object.isFrozen(ortam)).toBe(true);
    for (const a of ["istek", "p0", "serit", "akislar", "depo", "esitle", "dosyaVer", "yazdir", "ayarBolumu", "komutGitti"]) expect(typeof ortam[a], a).toBe("function");
    for (const a of ["ac", "kapat", "gonder", "destekli"]) expect(typeof ortam.tasiyici[a], a).toBe("function");
    expect(ortam.tasiyici.ad).toBe("telefon");
  });
});

describe("p0 (K8): ASLA reddetmez", () => {
  it("kart 204 -> true; ulasilamadi -> false; eklenti atti / reddetti -> false", async () => {
    expect(await olustur().ortam.p0()).toBe(true);
    expect(await olustur({ acilDurdur: async () => ({ tamam: false, basarili: [] }) }).ortam.p0()).toBe(false);
    expect(await olustur({ acilDurdur: () => { throw new Error("kopru"); } }).ortam.p0()).toBe(false);
    expect(await olustur({ acilDurdur: async () => { throw new Error("kopru"); } }).ortam.p0()).toBe(false);
    expect(await olustur({ acilDurdur: async () => null }).ortam.p0()).toBe(false);
  });
});

describe("serit (K9): yalniz pil testinin SURMEDIGI KESINSE false", () => {
  it("dogruluk tablosu: panel (true | false | null) x ortam (kesin degil | kesin surmuyor)", () => {
    const { ortam, arka } = olustur();
    const tablo = [];
    for (const ortamKesin of [false, true]) {
      arka.seritGorunur = () => !ortamKesin;          // ortamin hukmu (gercegi: pil_durum.js durdurGorunur)
      for (const panel of [true, false, null, undefined]) tablo.push([ortamKesin, panel, ortam.serit(panel)]);
    }
    expect(tablo).toEqual([
      [false, true, true], [false, false, true], [false, null, true], [false, undefined, true],
      [true, true, true], [true, false, false], [true, null, false], [true, undefined, false],
    ]);
    arka.seritGorunur = () => { throw new Error("hesap"); };
    expect(ortam.serit(false)).toBe(true);
  });

  it("gercek arka plan: hicbir sey bilinmezken GORUNUR", () => {
    const { ortam } = olustur();
    expect(ortam.serit(false)).toBe(true);
    expect(ortam.serit(null)).toBe(true);
  });
});

describe("dosyaVer (K11) / yazdir (K12)", () => {
  it("html, pdf, csv, kyt -> Paylas eklentisine (yalin MIME); string govde UTF-8", async () => {
    const { ortam, pe } = olustur();
    expect(await ortam.dosyaVer({ ad: "kayit-41-rapor.html", mime: "text/html;charset=utf-8", bayt: "<p>ç</p>" })).toBe(true);
    expect(pe.cagrilar.at(-1)).toEqual(["gonder", { ad: "kayit-41-rapor.html", mime: "text/html", boy: 9 }]);
    expect(Buffer.from(pe.cagrilar.find((c) => c[0] === "yaz")[1].parca, "base64").toString("utf8")).toBe("<p>ç</p>");
    await ortam.dosyaVer({ ad: "rapor.pdf", mime: "application/pdf", bayt: new Uint8Array([37, 80, 68, 70]) });
    expect(pe.cagrilar.at(-1)[1]).toEqual({ ad: "rapor.pdf", mime: "application/pdf", boy: 4 });
    await ortam.dosyaVer({ ad: "olcum-2026-10-07-12-00-00.csv", mime: "text/csv;charset=utf-8", bayt: new Uint8Array([1]).buffer });
    await ortam.dosyaVer({ ad: "kayit-41.kyt", mime: "application/octet-stream", bayt: new Uint8Array([1, 2]) });
    expect(pe.cagrilar.filter((c) => c[0] === "gonder").length).toBe(4);
  });

  it("gecersiz ad / MIME / bos govde: DosyaHatasi(tur), eklentiye GITMEZ", async () => {
    const { ortam, pe } = olustur();
    const tur = (s) => s.then(() => "tamam", (e) => (e instanceof DosyaHatasi ? e.tur : "?"));
    expect(await tur(ortam.dosyaVer({ ad: "../x.html", mime: "text/html", bayt: "a" }))).toBe("bicim");
    expect(await tur(ortam.dosyaVer({ ad: "x.csv", mime: "application/pdf", bayt: "a" }))).toBe("bicim");
    expect(await tur(ortam.dosyaVer({ ad: "x.exe", mime: "application/octet-stream", bayt: "a" }))).toBe("bicim");
    expect(await tur(ortam.dosyaVer({ ad: "x.html", mime: "text/html", bayt: new Uint8Array(0) }))).toBe("bos");
    expect(await tur(ortam.dosyaVer({ ad: "x.html", mime: "text/html", bayt: 5 }))).toBe("bos");
    expect(await tur(ortam.dosyaVer())).toBe("bicim");
    const e = await ortam.dosyaVer({ ad: "x.csv", mime: "text/html", bayt: "a" }).catch((x) => x);
    expect(e.message).toContain("Dosya paylaşılamadı");
    expect(pe.cagrilar).toEqual([]);
  });

  it("yazdir: Kotlin Yazdir.yazdir({ ad }) — ad belge basligindan, ASCII; eklenti reddederse tur", async () => {
    const { ortam, yazdirilan } = olustur();
    expect(await ortam.yazdir()).toBe(true);
    expect(yazdirilan).toEqual([{ ad: "Olcum-Karti-Kayit-41-raporu" }]);
    expect(isAdi("")).toBe("olcum-karti");
    expect(isAdi("..//..")).toBe("olcum-karti");
    expect(isAdi("a".repeat(100)).length).toBe(60);
    const red = olustur({ yazdirEklenti: { yazdir: async () => { throw Object.assign(new Error("x"), { code: "iptal" }); } } }).ortam;
    await expect(red.yazdir()).rejects.toMatchObject({ name: "DosyaHatasi", tur: "iptal" });
    const yok = olustur({ yazdirEklenti: null }).ortam;
    await expect(yok.yazdir()).rejects.toMatchObject({ tur: "ic-hata" });
  });
});

describe("ayarBolumu (K13)", () => {
  it("telefon/index.js bolum()'unu tembel yukleyip doner; yoksa anlasilir hata", async () => {
    const BILESEN = { ad: "BuTelefon" };
    let yuklendi = 0;
    const { ortam } = olustur({ ayarBolumuYukle: async () => { yuklendi += 1; return { bolum: async () => BILESEN }; } });
    expect(yuklendi).toBe(0);
    expect(await ortam.ayarBolumu()).toBe(BILESEN);
    expect(yuklendi).toBe(1);
    await expect(olustur().ortam.ayarBolumu()).rejects.toThrow("Bu telefon bölümü yüklenemedi");
    await expect(olustur({ ayarBolumuYukle: async () => ({}) }).ortam.ayarBolumu()).rejects.toThrow("Bu telefon bölümü yüklenemedi");
  });
});

describe("komutGitti: yalniz Gb… anlik izleme sorusunu baslatir (gercek izlemeSorusuKur)", () => {
  function kur({ durum = { anlik: false, calisiyor: false, zarf: true, izin: true, izinGerekli: false }, basladi = true } = {}) {
    const g = { cizimler: [], baslat: [] };
    const izlemeSorusu = izlemeSorusuKur({
      bildirim: { durum: async () => durum, izinIste: async () => {}, izlemeBaslat: async (k, s) => { g.baslat.push([k, s]); return { basladi }; } },
      kimlikAl: async () => "0123456789abcdef",
    });
    const zaman = [];
    const s = soruKur({ izlemeSorusu, ciz: (x) => g.cizimler.push(x), zamanla: (fn, ms) => { zaman.push({ fn, ms }); return zaman.length; }, zamaniBirak: () => {} });
    return { g, s, izlemeSorusu, zaman };
  }

  it("Gb1000 -> soru cizilir; evet -> izleme bu kayit icin baslar, 'acildi' cizilir ve SONUC_MS sonra kalkar", async () => {
    const { g, s, zaman } = kur();
    s.komutGitti("Gb1000");
    await bosalt();
    const soru = g.cizimler.at(-1);
    expect(soru).toMatchObject({ hal: "soruluyor", soru: true, mesgul: false });
    soru.evet();
    await bosalt();
    expect(g.baslat).toEqual([["0123456789abcdef", { buKayit: true }]]);
    expect(g.cizimler.at(-1)).toEqual({ hal: "acildi", soru: false });
    expect(zaman.at(-1).ms).toBe(SONUC_MS);
    zaman.at(-1).fn();
    expect(g.cizimler.at(-1)).toBeNull();
  });

  it("hayir -> kutu kalkar; Gb disi komut (Gd, G?, p0, xGb, bos, null) HICBIR sey yapmaz", async () => {
    const { g, s } = kur();
    for (const m of ["Gd", "G?", "p0", "xGb1000", "", null, undefined, 5]) s.komutGitti(m);
    await bosalt();
    expect(g.cizimler.filter((x) => x !== null)).toEqual([]);
    s.komutGitti("Gb0");
    await bosalt();
    g.cizimler.at(-1).hayir();
    expect(g.cizimler.at(-1)).toBeNull();
  });

  it("anlik izleme zaten acik / zarf yok: soru SORULMAZ (cekirdek kurali)", async () => {
    const { g, s } = kur({ durum: { anlik: true, calisiyor: false, zarf: true } });
    s.komutGitti("Gb1000");
    await bosalt();
    expect(g.cizimler.filter((x) => x !== null)).toEqual([]);
  });

  it("ortam.komutGitti soruya baglidir; cizim hatasi disari cikmaz", async () => {
    const cagri = [];
    const izlemeSorusu = { dinle: () => () => {}, kayitBasladi: async () => { cagri.push(1); } };
    const { ortam } = olustur({ izlemeSorusu, ciz: () => { throw new Error("cizim"); } });
    expect(ortam.komutGitti("Gb200")).toBeUndefined();
    ortam.komutGitti("Gd");
    expect(cagri).toEqual([1]);
  });
});
