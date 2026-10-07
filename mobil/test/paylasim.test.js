// 5F — paylasim (A41): CSV / ham .kyt / rapor dosyalarinin uretilmesi (Worker islemcisi), rapor metni,
// parca parca eklentiye verilmesi, ekran baglantisi ve FileProvider'in yalniz paylasim dizinini acmasi.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { BICIM_EN, BICIM_EXCEL_TR, csvBayt, hamDisari, oturumCsv } from "@ortak/disari.js";
import { akisCoz, oturumlariKur } from "@ortak/kayit.js";
import { oturumRaporu } from "@ortak/rapor.js";
import { disariUret } from "@panel/kayit_gorunum.js";
import { DISARI_AZAMI, KayitVeriHatasi, RAPOR_TURU, islemciKur, kalGecmisi, paylasimTurleri, paylasimUret, veriKur } from "../src/cekirdek/kayit_veri.js";
import { kayitlarKur } from "../src/cekirdek/kayitlar.js";
import { AD_DESENI, PARCA, PaylasHatasi, paylasKur } from "../src/cekirdek/paylas.js";
import { raporMetni, sayiMetni } from "../src/cekirdek/rapor_metin.js";
import { SOZLUK_MOBIL } from "../src/cekirdek/sozluk_mobil.js";
import { paylasimDugmeleri, paylasimHatasi } from "../src/ekran/kayitlar_gorunum.js";
import { ikiOturum } from "./yardim/akis_ornek.mjs";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../${yol}`, import.meta.url)), "utf8");
const metin = (b) => new TextDecoder("utf-8").decode(b);
const turu = async (soz) => { try { await soz; return null; } catch (e) { return e && e.tur ? e.tur : `baska:${e && e.message}`; } };

describe("paylasimUret: dosya panelin urettigiyle AYNI (hesap tek kopya)", () => {
  const { bayt, a, b } = ikiOturum();
  const v = veriKur(bayt, 7);
  const o = v.oturumlar.get(a);

  it("turler: olcum oturumunda CSV (tr, en) + ham + rapor; olmayan oturumda null", () => {
    expect(paylasimTurleri(v, a)).toEqual(["csv_tr", "csv_en", "ham", "rapor"]);
    expect(paylasimTurleri(v, 99999)).toBe(null);
    expect(paylasimTurleri(null, a)).toBe(null);
    expect(RAPOR_TURU).toBe("rapor");
  });

  it("CSV (Excel-TR): BOM + ';' + ondalik virgul + CRLF; ortak oturumCsv ile BAYT BAYT ayni", () => {
    const d = paylasimUret(v, a, "csv_tr");
    expect(d.ad).toBe(`kayit-${a}-aku-sarj.csv`);
    expect(d.mime).toBe("text/csv;charset=utf-8");
    expect(d.bayt).toEqual(csvBayt(oturumCsv(o, { ...BICIM_EXCEL_TR, kayitlar: v.kayitlar })));
    expect([...d.bayt.subarray(0, 3)]).toEqual([0xef, 0xbb, 0xbf]);
    const m = metin(d.bayt);
    const satirlar = m.split("\r\n");
    expect(satirlar.length).toBe(62);                      // baslik + 60 nokta + sondaki bos
    expect(satirlar[0]).toMatch(/;v_ort_V;/);
    expect(satirlar[1]).toMatch(/;10,000000;/);
    expect(d.bayt).toEqual(disariUret("csv_tr", o, v.kayitlar).bayt);
  });

  it("CSV (EN): ',' ayrac + ondalik nokta; ad -en", () => {
    const d = paylasimUret(v, a, "csv_en");
    expect(d.ad).toBe(`kayit-${a}-aku-sarj-en.csv`);
    expect(d.bayt).toEqual(csvBayt(oturumCsv(o, { ...BICIM_EN, kayitlar: v.kayitlar })));
    expect(metin(d.bayt).split("\r\n")[1]).toMatch(/,10\.000000,/);
  });

  it("ham .kyt: yalniz o oturumun kayitlari; yeniden cozulunce AYNI oturum", () => {
    const d = paylasimUret(v, a, "ham");
    expect(d.ad).toBe(`kayit-${a}-aku-sarj.kyt`);
    expect(d.mime).toBe("application/octet-stream");
    expect(d.bayt).toEqual(hamDisari(v.kayitlar, a));
    const geri = oturumlariKur(akisCoz(d.bayt));
    expect([...geri.keys()]).toEqual([a]);
    expect(geri.get(a).noktalar.length).toBe(60);
    expect(geri.get(a).ad).toBe("Akü şarj");
    expect(d.bayt.length).toBeLessThan(bayt.length);       // oteki oturum disarida
    expect(paylasimUret(v, b, "ham").ad).toBe(`kayit-${b}.kyt`);
  });

  it("rapor: ortak oturumRaporu'nun metni, secilen dilde; ad -rapor.txt", () => {
    const tr = paylasimUret(v, a, "rapor", "tr");
    expect(tr.ad).toBe(`kayit-${a}-aku-sarj-rapor.txt`);
    expect(tr.mime).toBe("text/plain;charset=utf-8");
    expect(metin(tr.bayt)).toBe(raporMetni(oturumRaporu(o, { kayitlar: v.kayitlar, dil: "tr" }), "tr"));
    const en = metin(paylasimUret(v, a, "rapor", "en").bayt);
    expect(en).toBe(raporMetni(oturumRaporu(o, { kayitlar: v.kayitlar, dil: "en" }), "en"));
    expect(en).not.toBe(metin(tr.bayt));
    expect(metin(paylasimUret(v, a, "rapor", "de").bayt)).toBe(metin(tr.bayt));      // bilinmeyen dil -> tr
  });

  it("bilinmeyen / oturuma uymayan tur ve olmayan oturum: null; dosya adlari eklentinin kabul ettigi desende", () => {
    for (const tur of ["pil_tr", "ayrinti_tr", "skop", "yok-boyle", "", null]) expect(paylasimUret(v, a, tur)).toBe(null);
    expect(paylasimUret(v, 99999, "ham")).toBe(null);
    expect(paylasimUret(null, a, "ham")).toBe(null);
    for (const tur of paylasimTurleri(v, a)) expect(paylasimUret(v, a, tur).ad).toMatch(AD_DESENI);
    expect(DISARI_AZAMI).toBe(48 * 1024 * 1024);
    // Sinirin ustundeki dosya uretilse de VERILMEZ (kopruden gecirilmez).
    const boy = paylasimUret(v, a, "csv_tr").bayt.length;
    expect(paylasimUret(v, a, "csv_tr", "tr", boy).bayt.length).toBe(boy);
    let hata = null;
    try { paylasimUret(v, a, "csv_tr", "tr", boy - 1); } catch (e) { hata = e; }
    expect(hata).toBeInstanceOf(KayitVeriHatasi);
    expect(hata.tur).toBe("cok-buyuk");
  });

  it("islemci (Worker ve yedek ayni kod): disariTurleri / disari mesajlari", async () => {
    const i = islemciKur({ getir: async () => bayt });
    await i.isle("yukle", { url: "/_depo/0123456789abcdef/kayitlar.kyt", akisKimlik: 7 });
    expect(await i.isle("disariTurleri", { oturum: a })).toEqual(["csv_tr", "csv_en", "ham", "rapor"]);
    const d = await i.isle("disari", { oturum: a, tur: "csv_tr", dil: "tr" });
    expect(d.bayt).toEqual(paylasimUret(v, a, "csv_tr").bayt);
    expect(await i.isle("disari", { oturum: a, tur: "yok" })).toBe(null);
    const bos = islemciKur({ getir: async () => new Uint8Array(0) });
    expect(await bos.isle("disariTurleri", { oturum: a })).toBe(null);
  });

  it("kayitlar: paylasim EKRANDAKI kartin kopyasindan ve sirayla; oturum acilmadan null", async () => {
    const cagrilar = [];
    const istemci = { cagir: async (is, arg) => { cagrilar.push([is, arg]); return is === "disari" ? { ad: "kayit-1.kyt", mime: "application/octet-stream", bayt: new Uint8Array([1]) } : is === "disariTurleri" ? ["ham"] : {}; }, kusak: () => 0 };
    const k = kayitlarKur({
      istemci, kartAl: async () => ({ durum: () => ({ durum: "bagli-degil", kimlik: null }) }),
      depoAl: () => ({ veriBoyu: async () => 10, durumOku: async () => ({ kimlik: 7 }) }), sonKimlik: () => "0123456789abcdef",
    });
    expect(await k.disari(101, "ham", "tr")).toBe(null);                    // henuz oturum acilmadi
    await k.oturum(101);
    expect(await k.disariTurleri(101)).toEqual(["ham"]);
    expect((await k.disari(101, "ham", "en")).ad).toBe("kayit-1.kyt");
    expect(cagrilar.map((c) => c[0])).toEqual(["yukle", "oturum", "disariTurleri", "disari"]);
    expect(cagrilar.at(-1)[1]).toEqual({ oturum: 101, tur: "ham", dil: "en", kal: null });
    const atan = kayitlarKur({
      istemci: { cagir: async (is) => { if (is === "disari") throw new KayitVeriHatasi("cok-buyuk"); return {}; }, kusak: () => 0 },
      kartAl: async () => ({ durum: () => null }), depoAl: () => ({ veriBoyu: async () => 1, durumOku: async () => null }), sonKimlik: () => "0123456789abcdef",
    });
    await atan.oturum(1);
    expect(await turu(atan.disari(1, "csv_tr", "tr"))).toBe("cok-buyuk");
  });
});

describe("rapor metni", () => {
  const { bayt, a } = ikiOturum();
  const v = veriKur(bayt, 7);
  const rapor = (dil) => raporMetni(oturumRaporu(v.oturumlar.get(a), { kayitlar: v.kayitlar, dil }), dil);

  it("tr: baslik, sozluk etiketleri (birimleriyle), kodlu alan 'metin (kod)', ondalik virgul, girinti", () => {
    const m = rapor("tr");
    const s = m.split("\n");
    expect(s[0]).toBe("Ölçüm kartı — kayıt raporu");
    expect(m).toContain("Kimlik:\n  Oturum no: 101\n  Tür: Ölçüm kaydı (1)\n  Ad: Akü şarj\n  Etiketler: akü, deneme\n");
    expect(m).toContain("  Gerilim (V):\n    Adet: 60\n    En düşük: 9\n    En yüksek: 18,375\n    Ortalama: 13,6875\n");
    expect(m).toContain("Enerji (boşluklar hariç):\n  Enerji (Wh): ");
    expect(m).toContain("  Bitiş sebebi: kullanıcı durdurdu (1)\n");
    expect(m).toContain("  Ayrıntılı kip (her örnek): hayır\n");
    expect(m).toContain("\nPil testi: —\n\n");
    expect(m).toContain("  Kayıt biçimi sürümü: 2\n");
    expect(m).toContain("  Süre (s): 59\n");
    // Her alanin etiketi sozlukten: satir basinda ham (deveHorgucu) alan adi kalmaz.
    expect(m.split("\n").filter((x) => /^ *[a-z]+[A-Z][A-Za-z]*:/.test(x))).toEqual([]);
    expect(m).toMatch(/Notlar:\n {2}1\.\n {4}/);
    expect(m).toContain("yük bağlandı");
    expect(m.endsWith("\n")).toBe(true);
    expect(m).not.toMatch(/\n\n\n/);
    expect(m).not.toMatch(/undefined|\[object|NaN/);
    expect(m).not.toMatch(/^(surum|dil):/m);
  });

  it("en: ayni yapi, Ingilizce etiketler ve ondalik nokta", () => {
    const m = rapor("en");
    expect(m.split("\n")[0]).toBe("Measurement board — recording report");
    expect(m).toContain("Identity:\n  Session no: 101\n");
    expect(m).toContain("    Maximum: 18.375\n    Mean: 13.6875\n");
    expect(m).toContain("  Detailed mode (every sample): no\n");
    expect(m.split("\n").length).toBe(rapor("tr").split("\n").length);
  });

  it("sayiMetni: tamsayi aynen, kesirli 6 basamaga yuvarlanir ve sondaki sifirlar atilir, sonlu olmayan '—'", () => {
    expect(sayiMetni(60, "tr")).toBe("60");
    expect(sayiMetni(-3, "en")).toBe("-3");
    expect(sayiMetni(13.6875, "tr")).toBe("13,6875");
    expect(sayiMetni(0.11216145833333334, "en")).toBe("0.112161");
    expect(sayiMetni(2.5, "en")).toBe("2.5");
    expect(sayiMetni(0.0000001, "tr")).toBe("0");
    expect(sayiMetni(NaN, "tr")).toBe("—");
    expect(sayiMetni(Infinity, "en")).toBe("—");
  });

  it("bos dizi, null, ic ice dizi ve bilinmeyen alan: cokme yok, alan adi oldugu gibi", () => {
    const m = raporMetni({ surum: 1, dil: "tr", kimlik: { oturumNo: 5, ad: null, etiketler: [] }, bilinmeyenAlan: [[1, 2], { x: true }], uyarilar: [] }, "tr");
    expect(m).toBe("Ölçüm kartı — kayıt raporu\n\nKimlik:\n  Oturum no: 5\n  Ad: —\n  Etiketler: —\n\nbilinmeyenAlan:\n  1: 1, 2\n  2.\n    x: evet\n\nUyarılar: —\n");
  });
});

describe("paylas: dosya eklentiye parca parca", () => {
  function eklenti({ red = {} } = {}) {
    const cagrilar = [];
    const e = {};
    for (const ad of ["baslat", "yaz", "gonder"]) e[ad] = async (veri) => { cagrilar.push([ad, veri]); if (red[ad]) throw Object.assign(new Error("gizli"), { code: red[ad] }); return {}; };
    return { e, cagrilar };
  }
  const dosya = (boy, ad = "kayit-101.csv", mime = "text/csv;charset=utf-8") => ({ ad, mime, bayt: Uint8Array.from({ length: boy }, (_, i) => (i * 31) & 0xff) });

  it("baslat -> yaz (512 KiB'lik parcalar) -> gonder; parcalar birlesince AYNI baytlar; mime karakter kumesiz", async () => {
    const { e, cagrilar } = eklenti();
    const d = dosya(PARCA * 2 + 100);
    await paylasKur({ eklenti: e }).gonder(d);
    expect(cagrilar.map((c) => c[0])).toEqual(["baslat", "yaz", "yaz", "yaz", "gonder"]);
    expect(cagrilar[0][1]).toEqual({ ad: "kayit-101.csv" });
    const parcalar = cagrilar.filter((c) => c[0] === "yaz").map((c) => Buffer.from(c[1].parca, "base64"));
    expect(parcalar.map((p) => p.length)).toEqual([PARCA, PARCA, 100]);
    expect(Buffer.concat(parcalar)).toEqual(Buffer.from(d.bayt));
    expect(cagrilar.at(-1)[1]).toEqual({ ad: "kayit-101.csv", mime: "text/csv", boy: d.bayt.length });
    expect(PARCA).toBe(512 * 1024);
  });

  it("gecersiz ad / mime / bos veri eklentiye GITMEZ", async () => {
    const { e, cagrilar } = eklenti();
    const p = paylasKur({ eklenti: e });
    for (const ad of ["../kasa/x.csv", "a/b.csv", "kayit.exe", "kayit..csv", ".gizli.csv", "kayit 1.csv", "kayıt.csv", `${"a".repeat(90)}.csv`, "", null]) {
      expect(await turu(p.gonder(dosya(10, ad))), String(ad)).toBe("bicim");
    }
    expect(await turu(p.gonder(dosya(10, "k.csv", "text/html")))).toBe("bicim");
    expect(await turu(p.gonder({ ad: "k.csv", mime: "text/csv", bayt: new Uint8Array(0) }))).toBe("bos");
    expect(await turu(p.gonder({ ad: "k.csv", mime: "text/csv", bayt: [1, 2] }))).toBe("bos");
    expect(cagrilar).toEqual([]);
    for (const ad of ["kayit-101-aku-sarj.csv", "kayit-5.kyt", "kayit-5-rapor.txt"]) expect(ad).toMatch(AD_DESENI);
  });

  it("eklenti reddederse TUR adi; mesaj disari cikmaz; sonraki paylasim calisir; es zamanli ikinci 'mesgul'", async () => {
    const { e, cagrilar } = eklenti({ red: { yaz: "cok-buyuk" } });
    const p = paylasKur({ eklenti: e });
    let hata = null;
    try { await p.gonder(dosya(10)); } catch (h) { hata = h; }
    expect(hata).toBeInstanceOf(PaylasHatasi);
    expect([hata.tur, hata.message]).toEqual(["cok-buyuk", "cok-buyuk"]);
    expect(cagrilar.map((c) => c[0])).toEqual(["baslat", "yaz"]);
    const iyi = eklenti();
    const q = paylasKur({ eklenti: iyi.e });
    const ilk = q.gonder(dosya(10));
    expect(await turu(q.gonder(dosya(10)))).toBe("mesgul");
    await ilk;
    await q.gonder(dosya(10));
    expect(iyi.cagrilar.filter((c) => c[0] === "gonder").length).toBe(2);
    expect(await turu(paylasKur({ eklenti: { baslat: async () => { throw Object.assign(new Error("x"), { code: "Gizli Mesaj" }); } } }).gonder(dosya(10)))).toBe("ic-hata");
  });
});

describe("paylasim: ekran ve Android baglantisi", () => {
  it("dugmeler: bilinen turler sirayla, bilinmeyen gosterilmez; hata metinleri", () => {
    expect(paylasimDugmeleri(["csv_tr", "csv_en", "yok", "ham", "rapor"]).map((d) => d.tur)).toEqual(["csv_tr", "csv_en", "ham", "rapor"]);
    expect(paylasimDugmeleri(null)).toEqual([]);
    expect(paylasimHatasi("cok-buyuk").anahtar).toBe("m.ps.hata_buyuk");
    expect(paylasimHatasi("bos").anahtar).toBe("m.ps.hata_bos");
    expect(paylasimHatasi("ic-hata")).toEqual({ anahtar: "m.ps.hata_genel", degerler: { tur: "ic-hata" } });
    const hepsi = ["csv_tr", "csv_en", "ayrinti_tr", "ayrinti_en", "pil_tr", "pil_en", "ham", "rapor"];
    for (const d of paylasimDugmeleri(hepsi)) {
      expect(SOZLUK_MOBIL[d.anahtar].tr.length).toBeGreaterThan(1);
      expect(SOZLUK_MOBIL[d.anahtar].en.length).toBeGreaterThan(1);
    }
    expect(paylasimDugmeleri(hepsi).length).toBe(8);
    expect(SOZLUK_MOBIL["m.ps.hata_buyuk"].tr).toMatch(/\.kyt/);
  });

  it("Kayit.vue: dosya islemciden (uygulamanin dilinde) alinir, paylas eklentisine verilir; uretim surerken dugmeler kapali", () => {
    const v = kaynak("src/ekran/Kayit.vue");
    expect(v).toMatch(/const d = await kaynak\.disari\(oturumNo, tur, dil\.value\);/);
    expect(v).toMatch(/await paylasAl\(\)\.gonder\(d\);/);
    expect(v).toMatch(/:disabled="paylasilan !== null" @click="paylas\(d\.tur\)"/);
    expect(v).toMatch(/if \(paylasilan\.value !== null \|\| !kaynak\) return;/);
  });

  it("FileProvider YALNIZ cache/paylas/ dizinini acar; eklenti dosyayi okuma izniyle ve secici pencereyle verir", () => {
    const x = kaynak("android/app/src/main/res/xml/file_paths.xml").replace(/<!--[^]*?-->/g, "");
    expect([...x.matchAll(/<([a-z-]+-path)\s+name="[^"]*"\s+path="([^"]*)"/g)].map((m) => `${m[1]} ${m[2]}`)).toEqual(["cache-path paylas/"]);
    expect(x).not.toMatch(/external|root-path|files-path/);
    const kt = kaynak("android/app/src/main/java/tr/olcumkarti/mobil/paylas/PaylasPlugin.kt");
    expect(kt).toContain("Intent.createChooser(");
    expect(kt).toContain("FLAG_GRANT_READ_URI_PERMISSION");
    expect(kt).not.toMatch(/FLAG_GRANT_WRITE_URI_PERMISSION|ACTION_VIEW|http/);
    expect(kt).toContain('const val DIZIN = "paylas"');
    expect(kaynak("android/app/src/main/AndroidManifest.xml")).toMatch(/android:name="androidx\.core\.content\.FileProvider"[^>]*android:exported="false"/);
    // JS ve Kotlin ayni ad desenini kullanir (5P K11/K12: + html, pdf).
    expect(kaynak("android/app/src/main/java/tr/olcumkarti/mobil/paylas/PaylasDeposu.kt")).toContain('Regex("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\\\\.(csv|kyt|txt|html|pdf)$")');
    expect(AD_DESENI.source).toBe("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}\\.(csv|kyt|txt|html|pdf)$");
    // MIME kumesi de Kotlin MIMELER ile ayni.
    expect(kaynak("android/app/src/main/java/tr/olcumkarti/mobil/paylas/PaylasDeposu.kt")).toContain('setOf("text/csv", "text/plain", "application/octet-stream", "text/html", "application/pdf")');
  });
});

describe("rapor: kalibrasyon gecmisi telefondaki kopyadan (esitlemenin yazdigi kalibrasyon.json)", () => {
  const { bayt, a } = ikiOturum();
  const v = veriKur(bayt, 7);
  // Ornek akisin oturumu kal_no 2 ve KAL (yardim/akis_ornek.mjs) kopyasini tasir.
  const KAL = {
    normal: { n: 1, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 }, yuksek: { n: 2, pga: 4096, kazanc: 1, sifir_ham: 0, tau: 0 },
    i_ofset: 0, i_pga: 32, sont_ohm: 1, i_duzeltme: 1, sebeke_hz: 50, faz_kal_us: [0, 0],
  };
  const gecmis = (ek = {}) => ({ kayitlar: [{ no: 1, tur: 1, kaynak: 1, not: "eski", kal: KAL }, { no: 2, tur: 1, kaynak: 1, not: "tezgah kalibrasyonu", kal: KAL, ...ek }] });
  const metinAl = (kal, dil = "tr") => metin(paylasimUret(v, a, "rapor", dil, DISARI_AZAMI, kal).bayt);

  it("gecmis verilince oturumun kalibrasyon kaydi BULUNUR (notuyla); verilmeyince 'gecmis verilmedi'", () => {
    const yok = metinAl(null);
    expect(yok).toContain("Geçmişteki durumu: kalibrasyon geçmişi verilmedi (gecmis_yok)");
    const var_ = metinAl(gecmis());
    expect(var_).toContain("  Kalibrasyon no: 2\n");
    expect(var_).toMatch(/Geçmişteki durumu: [^\n]*\(bulundu\)/);
    expect(var_).toContain("tezgah kalibrasyonu");
    expect(var_).not.toContain("eski");                                     // baska numaranin kaydi rapora girmez
    expect(var_).toBe(raporMetni(oturumRaporu(v.oturumlar.get(a), { kalibrasyonGecmisi: gecmis(), kayitlar: v.kayitlar, dil: "tr" }), "tr"));
    expect(metinAl(gecmis(), "en")).toMatch(/\(bulundu\)/);
  });

  it("gecmiste o numara yoksa 'yok'; bicimsiz gecmis yok sayilir (paylasim durmaz)", () => {
    expect(metinAl({ kayitlar: [{ no: 9, tur: 1, kaynak: 1, kal: KAL }] })).toMatch(/Geçmişteki durumu: [^\n]*\(yok\)/);
    for (const bozuk of [{}, [], "x", 5, { kayitlar: "x" }, { kayitlar: null }]) {
      expect(kalGecmisi(bozuk)).toBe(null);
      expect(metinAl(bozuk)).toContain("(gecmis_yok)");
    }
    expect(kalGecmisi(gecmis())).not.toBe(null);
    // Gecmis yalniz RAPORU etkiler: CSV ve ham kayit ayni baytlar.
    expect(paylasimUret(v, a, "csv_tr", "tr", DISARI_AZAMI, gecmis()).bayt).toEqual(paylasimUret(v, a, "csv_tr").bayt);
  });

  it("islemci `kal` argumanini rapora tasir", async () => {
    const i = islemciKur({ getir: async () => bayt });
    await i.isle("yukle", { url: "/_depo/0123456789abcdef/kayitlar.kyt", akisKimlik: 7 });
    expect(metin((await i.isle("disari", { oturum: a, tur: "rapor", dil: "tr", kal: gecmis() })).bayt)).toMatch(/\(bulundu\)/);
    expect(metin((await i.isle("disari", { oturum: a, tur: "rapor", dil: "tr" })).bayt)).toContain("(gecmis_yok)");
  });

  it("kayitlar: gecmis ekrandaki kartin deposundan okunur; yok / bozuk / okunamayan -> null (paylasim surer)", async () => {
    const kod = (o) => new TextEncoder().encode(JSON.stringify(o));
    async function kos(kalOku) {
      const cagrilar = [];
      const kimlikler = [];
      const k = kayitlarKur({
        istemci: { cagir: async (is, arg) => { cagrilar.push([is, arg]); return is === "disari" ? { ad: "kayit-1-rapor.txt", mime: "text/plain", bayt: new Uint8Array([1]) } : {}; }, kusak: () => 0 },
        kartAl: async () => ({ durum: () => null }),
        depoAl: (kimlik) => { kimlikler.push(kimlik); return { veriBoyu: async () => 10, durumOku: async () => ({ kimlik: 7 }), kalOku }; },
        sonKimlik: () => "0123456789abcdef",
      });
      await k.oturum(101);
      await k.disari(101, "rapor", "tr");
      return { kal: cagrilar.at(-1)[1].kal, kimlikler };
    }
    const iyi = await kos(async () => kod(gecmis()));
    expect(iyi.kal).toEqual(gecmis());
    expect(new Set(iyi.kimlikler)).toEqual(new Set(["0123456789abcdef"]));
    expect((await kos(async () => null)).kal).toBe(null);
    expect((await kos(async () => new Uint8Array(0))).kal).toBe(null);
    expect((await kos(async () => new TextEncoder().encode("{bozuk"))).kal).toBe(null);
    expect((await kos(async () => kod({ kayitlar: "x" }))).kal).toBe(null);
    expect((await kos(async () => kod([1, 2]))).kal).toBe(null);
    expect((await kos(async () => new Uint8Array([0xff, 0xfe, 0x7b]))).kal).toBe(null);     // gecersiz UTF-8
    expect((await kos(async () => { throw Object.assign(new Error("x"), { tur: "bozuk" }); })).kal).toBe(null);
  });
});
