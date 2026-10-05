// Curutucu 5E — duzeltmelerin ve YASAYAN mutasyonlarin (J02, J05, J06, J09, J11, J12, J13, J15) testleri.
// Bulgularin kendi kanitlari: izleyici-kenar.test.js (B12–B15), rapor-kenar.test.js (B16).
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  KAYITTA, YENILE_ARALIK_TIK, YEREL_DENEME, bildirimIzleyici, bildirimKur, izlemeSorusuKur, kayitBittiMi,
} from "../../src/cekirdek/bildirim.js";
import { raporMetni, sayiMetni } from "../../src/cekirdek/rapor_metin.js";

const kaynak = (yol) => readFileSync(fileURLToPath(new URL(`../../${yol}`, import.meta.url)), "utf8");
const KIMLIK = "0123456789abcdef";
const G = (durum, oturum = 53) => ({ tur: "G", durum, oturum });
const on = { gorunur: true, bagli: true, kimlik: KIMLIK, adres: "192.168.1.7:80" };
const D = { zarf: true, izin: true, izinGerekli: true, pilMuaf: false, calisiyor: false, izleme: "durduruldu", anlik: false, kapali: [], dil: "tr" };

describe("B12: zarf yenilemesinin yeniden denenmesi", () => {
  function izleyici(sonuclar) {
    const olay = [];
    let n = 0;
    const bildirim = {
      yenile: async () => { olay.push("yenile"); const s = sonuclar[Math.min(n++, sonuclar.length - 1)]; if (s.startsWith("!")) throw Object.assign(new Error("x"), { tur: s.slice(1) }); return s; },
      izlemeBaslat: async () => { olay.push("baslat"); return { basladi: false, neden: "zarf-yok" }; },
      yerel: async () => false,
    };
    return { i: bildirimIzleyici({ bildirim }), olay };
  }
  const tikle = async (i, n, kayit = null) => { for (let t = 0; t < n; t++) { i.tik({ ...on, kayit }); await i.bosalt(); } };

  it("basarisiz yenileme TAM 30 tik sonra yeniden denenir (daha erken degil); basarinca durur", async () => {
    const { i, olay } = izleyici(["!ag", "!ag", "yazildi"]);
    await tikle(i, 1 + YENILE_ARALIK_TIK - 1);
    expect(olay.filter((o) => o === "yenile").length).toBe(1);
    await tikle(i, 1);
    expect(olay.filter((o) => o === "yenile").length).toBe(2);
    await tikle(i, YENILE_ARALIK_TIK);
    expect(olay.filter((o) => o === "yenile").length).toBe(3);
    await tikle(i, 3 * YENILE_ARALIK_TIK);
    expect(olay.filter((o) => o === "yenile").length).toBe(3);
    expect(i.son()).toBe("yazildi");
    expect(YENILE_ARALIK_TIK).toBe(30);
  });

  it("'kartta ayarsiz' (404) hata DEGILDIR: yeniden denenmez; ilk basarida izleme iki kez baslatilmaz", async () => {
    const ayarsiz = izleyici(["kartta-ayarsiz"]);
    await tikle(ayarsiz.i, 100);
    expect(ayarsiz.olay.filter((o) => o === "yenile").length).toBe(1);
    const ilk = izleyici(["yazildi"]);
    await tikle(ilk.i, 100, G(2));
    expect(ilk.olay.filter((o) => o === "baslat").length).toBe(1);
  });

  it("yeniden deneme basarinca suren kayit icin izleme YENIDEN baslatilir; baglanti kopunca bekleyen deneme silinir", async () => {
    const { i, olay } = izleyici(["!ag", "yazildi"]);
    await tikle(i, 1, G(2));
    expect(olay.filter((o) => o === "baslat").length).toBe(1);
    await tikle(i, YENILE_ARALIK_TIK + 1, G(2));
    expect(olay.filter((o) => o === "baslat").length).toBe(2);
    const kopan = izleyici(["!ag", "!ag", "yazildi"]);
    await tikle(kopan.i, 10);
    kopan.i.tik({ ...on, bagli: false, kayit: null });
    await tikle(kopan.i, 5);                                  // yeni baglanti: hemen bir kez
    expect(kopan.olay.filter((o) => o === "yenile").length).toBe(2);
  });
});

describe("B13: iletilmeyen yerel durum", () => {
  it("servis BASLATILDIYSA en cok 5 tik yeniden iletilir; baslatilmadiysa (ayar kapali) yeniden iletilmez", async () => {
    const say = async (basladi) => {
      let n = 0;
      const i = bildirimIzleyici({ bildirim: { yenile: async () => "yazildi", izlemeBaslat: async () => ({ basladi, neden: "" }), yerel: async () => { n += 1; return false; } } });
      for (let t = 0; t < 20; t++) { i.tik({ ...on, kayit: G(2) }); await i.bosalt(); }
      return n;
    };
    expect(await say(true)).toBe(1 + YEREL_DENEME);
    expect(await say(false)).toBe(1);
    expect(YEREL_DENEME).toBe(5);
  });

  it("iletilince yeniden deneme durur; durum degisince sayac sifirlanir", async () => {
    let hazir = false;
    const olay = [];
    const i = bildirimIzleyici({ bildirim: {
      yenile: async () => "yazildi", izlemeBaslat: async () => ({ basladi: true, neden: "" }),
      yerel: async (k, d, o) => { olay.push(`${d}:${o}`); return hazir; },
    } });
    i.tik({ ...on, kayit: G(2) }); await i.bosalt();
    hazir = true;
    for (let t = 0; t < 10; t++) { i.tik({ ...on, kayit: G(2) }); await i.bosalt(); }
    expect(olay).toEqual(["2:53", "2:53"]);
    i.tik({ ...on, kayit: G(1) }); await i.bosalt();
    expect(olay).toEqual(["2:53", "2:53", "1:53"]);
  });
});

describe("izleme sorusu: yasayan mutasyonlar", () => {
  it("J02: kayit bittikten SONRA donen durum sorgusu soruyu acmaz", async () => {
    let coz;
    const s = izlemeSorusuKur({ bildirim: { durum: () => new Promise((c) => { coz = c; }) }, kimlikAl: async () => KIMLIK });
    const p = s.kayitBasladi();
    await new Promise((c) => setTimeout(c, 0));
    s.kayitBitti();
    coz(D);
    await p;
    expect(s.hal()).toBe("yok");
  });

  it("J09: 'hayir' yalniz SORU acikken kapatir; acilmis izlemenin sonucunu silmez", async () => {
    const s = izlemeSorusuKur({ bildirim: { durum: async () => D, izinIste: async () => true, izlemeBaslat: async () => ({ basladi: true, neden: "" }) }, kimlikAl: async () => KIMLIK });
    await s.kayitBasladi();
    await s.evet();
    expect(s.hal()).toBe("acildi");
    s.hayir();
    expect(s.hal()).toBe("acildi");
  });

  it("izlemeBaslat 'basladi' true DEGILSE (ornegin metin) 'acilamadi'", async () => {
    const s = izlemeSorusuKur({ bildirim: { durum: async () => D, izinIste: async () => true, izlemeBaslat: async () => ({ basladi: "evet" }) }, kimlikAl: async () => KIMLIK });
    await s.kayitBasladi();
    await s.evet();
    expect(s.hal()).toBe("acilamadi");
  });
});

describe("bildirimKur: eklenti donusleri TUR denetimiyle (J05, J06, J11, J12)", () => {
  const kur = (yanit) => bildirimKur({ kartAl: async () => ({}), eklenti: { durum: async () => yanit, izlemeBaslat: async () => yanit, yerel: async () => yanit } });

  it("durum: zarf / calisiyor yalniz TAM true ise true", async () => {
    const d = await kur({ zarf: "evet", calisiyor: 1, anlik: "true", izin: {}, pilMuaf: "1", izinGerekli: 1 }).durum(KIMLIK);
    expect([d.zarf, d.calisiyor, d.anlik, d.izin, d.pilMuaf, d.izinGerekli]).toEqual([false, false, false, false, false, false]);
  });

  it("izlemeBaslat: neden yalniz tur bicimindeyse gecer; yerel: iletildi yalniz TAM true", async () => {
    expect(await kur({ basladi: true, neden: "<b>Gizli Mesaj</b>" }).izlemeBaslat(KIMLIK)).toEqual({ basladi: true, neden: "" });
    expect(await kur({ basladi: false, neden: "baska-kart" }).izlemeBaslat(KIMLIK)).toEqual({ basladi: false, neden: "baska-kart" });
    expect(await kur({ basladi: 1, neden: 5 }).izlemeBaslat(KIMLIK)).toEqual({ basladi: false, neden: "" });
    expect(await kur({ iletildi: "evet" }).yerel(KIMLIK, 2, 5)).toBe(false);
    expect(await kur({ iletildi: true }).yerel(KIMLIK, 2, 5)).toBe(true);
  });
});

describe("kayit bitti mi (K-11)", () => {
  it("KAYIT / BEKLIYOR -> baska durum: bitti; KAYIT <-> BEKLIYOR ve bilinmeyen (akis koptu): bitmedi", () => {
    expect(KAYITTA).toEqual([2, 4]);
    expect(kayitBittiMi(2, 1)).toBe(true);
    expect(kayitBittiMi(2, 3)).toBe(true);
    expect(kayitBittiMi(4, 1)).toBe(true);
    expect(kayitBittiMi(2, 4)).toBe(false);
    expect(kayitBittiMi(4, 2)).toBe(false);
    expect(kayitBittiMi(2, null)).toBe(false);
    expect(kayitBittiMi(2, undefined)).toBe(false);
    expect(kayitBittiMi(1, 3)).toBe(false);
    expect(kayitBittiMi(null, 1)).toBe(false);
    const v = kaynak("src/ekran/KayitDugmesi.vue");
    expect(v).toMatch(/const g = kabuk\.akis\.value\.kayit; return g && Number\.isInteger\(g\.durum\) \? g\.durum : null;/);
  });
});

describe("rapor metni: yasayan mutasyonlar ve kucukler (J13, J15, K-12)", () => {
  it("kodsuz kodlu deger yalniz metniyle; kod 0 yazilir; bos metin '—'", () => {
    const m = raporMetni({ a: { kod: null, metin: "bilinmiyor" }, b: { kod: 0, metin: "sifir" }, c: { kod: undefined, metin: "x" }, d: "", e: "dolu" }, "tr");
    expect(m).toContain("a: bilinmiyor\n");
    expect(m).toContain("b: sifir (0)\n");
    expect(m).toContain("c: x\n");
    expect(m).toContain("d: —\n");
    expect(m).toContain("e: dolu\n");
  });

  it("satir sonu / denetim karakteri iceren metin TEK satir; eksi sifir '0'; ic duzeyde 'dil' alani atlanmaz", () => {
    const m = raporMetni({ aciklama: "bir\r\niki\nuc dort\tbes\u0000alti", ic: { dil: "en", surum: 3 } }, "tr");
    expect(m).toContain("aciklama: bir / iki / uc / dort bes alti\n");
    expect(m).toContain("  dil: en\n");
    expect(m).toContain("  surum: 3\n");
    expect(m.split("\n").filter((x) => x.startsWith("dil:") || x.startsWith("surum:"))).toEqual([]);
    expect(sayiMetni(-1e-7, "tr")).toBe("0");
    expect(sayiMetni(-1e-7, "en")).toBe("0");
    expect(sayiMetni(-0.5, "tr")).toBe("-0,5");
  });
});
