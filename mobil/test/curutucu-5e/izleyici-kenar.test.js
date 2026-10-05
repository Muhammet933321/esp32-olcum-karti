// 5E BAGIMSIZ CURUTUCU — WebView yarisi (cekirdek/bildirim.js). Her test DOGRU davranisi bekler:
// bulgu VARKEN KIRMIZI. Ayrinti: BULGULAR.md (B12–B15).
import { describe, it, expect } from "vitest";
import { bildirimIzleyici, izlemeSorusuKur } from "../../src/cekirdek/bildirim.js";

const KIMLIK = "0123456789abcdef";
const BASKA = "fedcba9876543210";
const G = (durum, oturum = 53) => ({ tur: "G", durum, oturum });
const on = { gorunur: true, bagli: true, kimlik: KIMLIK, adres: "192.168.1.7:80" };

describe("B12: zarf yenilemesi gecici hatada bu baglanti boyunca bir daha DENENMEZ", () => {
  it("ilk yenileme 'ag' ile dustuyse sonraki tiklerde yeniden denenmeli (kayit suruyor, izleme baslayamiyor)", async () => {
    const olay = [];
    let zarfVar = false;
    let deneme = 0;
    const bildirim = {
      adresYaz: async () => {},
      yenile: async () => { olay.push("yenile"); if (++deneme === 1) throw Object.assign(new Error("x"), { tur: "ag" }); zarfVar = true; return "yazildi"; },
      izlemeBaslat: async () => { olay.push(zarfVar ? "baslat:tamam" : "baslat:zarf-yok"); return { basladi: zarfVar, neden: zarfVar ? "" : "zarf-yok" }; },
      yerel: async () => false,
    };
    const i = bildirimIzleyici({ bildirim });
    for (let t = 0; t < 60; t++) { i.tik({ ...on, kayit: G(2) }); await i.bosalt(); }      // 60 s bagli, kayit suruyor
    expect(i.son()).toBe("yazildi");                         // gercek: "ag" (Ayarlar da bunu gosterir)
    expect(olay).toContain("baslat:tamam");                  // gercek: tek "baslat:zarf-yok", izleme HIC baslamaz
  });
});

describe("B13: servis henuz ayaga kalkmadan iletilen yerel durum KAYBOLUR", () => {
  it("yerel() 'iletilmedi' donduyse sonraki tikte yeniden iletilmeli", async () => {
    const olay = [];
    let servisHazir = false;
    const bildirim = {
      yenile: async () => "yazildi",
      // Eklenti: startForegroundService doner donmez cozulur; servis (calisanKimlik) biraz SONRA hazir olur.
      izlemeBaslat: async () => { setTimeout(() => { servisHazir = true; }, 5); return { basladi: true, neden: "" }; },
      yerel: async (k, d, o) => { olay.push([d, o, servisHazir]); return servisHazir; },
    };
    const i = bildirimIzleyici({ bildirim });
    i.tik({ ...on, kayit: G(2) });
    await i.bosalt();
    expect(olay).toEqual([[2, 53, false]]);                  // ilk iletim: servis hazir degil -> eklenti dusurdu
    await new Promise((c) => setTimeout(c, 20));
    for (let t = 0; t < 5; t++) { i.tik({ ...on, kayit: G(2) }); await i.bosalt(); }
    expect(olay.some((o) => o[2] === true)).toBe(true);      // gercek: bir daha HIC iletilmez (sonG ayni)
  });
});

describe("B14: baglanti kopmadan kart degisirse yeni kartin zarfi / adresi / durumu islenmez", () => {
  it("kimlik degisince zarf yeni kart icin yenilenmeli, ayni G satiri yeni karta da iletilmeli", async () => {
    const olay = [];
    const bildirim = {
      adresYaz: async (k, a) => { olay.push(["adres", k, a]); },
      yenile: async () => { olay.push(["yenile"]); return "yazildi"; },
      izlemeBaslat: async (k) => { olay.push(["baslat", k]); return { basladi: true, neden: "" }; },
      yerel: async (k, d, o) => { olay.push(["yerel", k, d, o]); return true; },
    };
    const i = bildirimIzleyici({ bildirim });
    i.tik({ ...on, kayit: G(2) });
    await i.bosalt();
    i.tik({ ...on, kimlik: BASKA, adres: "192.168.1.9:80", kayit: G(2) });      // sonraki tik: baska kart, ayni G
    await i.bosalt();
    expect(olay.filter((o) => o[0] === "yenile").length).toBe(2);
    expect(olay).toContainEqual(["adres", BASKA, "192.168.1.9:80"]);
    expect(olay).toContainEqual(["yerel", BASKA, 2, 53]);
  });
});

describe("B15: 'ac' islemi surerken kayit biterse izleme YINE baslatilir", () => {
  it("izin penceresi acikken kayit bittiyse izlemeBaslat cagrilmamali", async () => {
    const olay = [];
    let izinCoz;
    const bildirim = {
      durum: async () => ({ zarf: true, izin: false, izinGerekli: true, calisiyor: false, anlik: false }),
      izinIste: () => new Promise((c) => { izinCoz = c; }),                      // Android'in izin penceresi acik
      izlemeBaslat: async (k, s) => { olay.push(["baslat", k, s]); return { basladi: true, neden: "" }; },
    };
    const s = izlemeSorusuKur({ bildirim, kimlikAl: async () => KIMLIK });
    await s.kayitBasladi();
    expect(s.hal()).toBe("soruluyor");
    const evet = s.evet();
    await new Promise((c) => setTimeout(c, 5));
    expect(typeof izinCoz).toBe("function");
    s.kayitBitti();                                          // kullanici pencereye bakarken kayit bitti
    izinCoz(true);
    await evet;
    expect(s.hal()).toBe("yok");
    expect(olay).toEqual([]);                                // gercek: [["baslat", KIMLIK, { buKayit: true }]]
  });
});
