// CURUTUCU 5C — ekranin "yanlis ama emin" gosterdigi degerler. GERCEK kabukDurumu + gorunum islevleri;
// canli'nin sahtesi (ekran.test.js'teki ile ayni bicim). Vue bilesenleri calistirilmiyor: bilesenin
// yaptigi hesap (Durum.vue'daki `computed` satirlari) burada AYNEN tekrarlanir, kaynagi da denetlenir.
import { describe, it, expect } from "vitest";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { canliKur } from "../../src/cekirdek/canli.js";
import { satirAyir } from "../../src/cekirdek/akis_ayir.js";
import { KDR, YOK, baglantiGorunumu, kayitGorunumu, olcumYazilari } from "../../src/ekran/durum_gorunum.js";
import { kabukDurumu } from "../../src/ekran/kabuk_durum.js";

const G = (durum, ek = {}) => ({ tur: "G", durum, oturum: 0, nokta: 0, doluluk: 120, onaysiz: 30, ...ek });
const DSATIR = "D 12.4820 1.936000 24.17000 10.0000 0.0027778 123456 500 0 0";

function sahteler() {
  const komutlar = [];
  let hal = "kapali", son = null, kayit = null, dinleyen = null, komutHata = null;
  const kart = {
    d: { durum: "bagli-degil", adres: null, kimlik: null },
    durum() { return this.d; },
    async baglan() { this.d = { durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" }; return { ...this.d, bilgi: {} }; },
  };
  const canli = {
    baslat() { hal = "baglaniyor"; }, durdur() { hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son, kayit, yas_ms: 0 }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; },
    seri: () => null,
    async komut(metin) { komutlar.push(metin); if (komutHata) throw Object.assign(new Error("x"), { tur: komutHata }); return true; },
  };
  const saat = { ms: 1000000 };
  const k = kabukDurumu({
    kartAl: async () => kart, canliAl: async () => canli, belge: null, simdiMs: () => saat.ms,
    araliKur: () => 1, araliSil: () => {},
  });
  const yay = (yeni) => { ({ hal = hal, son = son, kayit = kayit } = yeni); if (dinleyen) dinleyen(); };
  return { k, saat, yay, komutlar, komutHatasi: (t) => { komutHata = t; } };
}

describe("curutucu 5C: basarisiz 'Kaydi baslat'in hizi BASKA bir kayda yapisiyor", () => {
  it("Gb20 karta ULASMADI; 10 dk sonra baskasinin (PC paneli / plan) 1/s kaydi 'bu telefonun hizi' ile gosterilmemeli", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    s.komutHatasi("ag");                                       // komut gitmedi (ag hatasi) — kayit BASLAMADI
    await expect(s.k.kayitBaslat(20)).rejects.toMatchObject({ tur: "ag" });
    s.komutHatasi(null);

    s.saat.ms += 600000;                                       // 10 dakika sonra
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 77, nokta: 0 }) });  // baska bir istemci 1/s kayit baslatti
    for (let i = 1; i <= 30; i++) {                            // 30 saniye, saniyede 1 nokta
      s.saat.ms += 1000;
      s.yay({ kayit: G(KDR.KAYIT, { oturum: 77, nokta: i }) });
    }
    const g = kayitGorunumu(s.k.akis.value.kayit, s.k.izleme.value, s.saat.ms);
    console.log(`[hiz] 30 s suren 1/s kayit -> ekranda hiz=${JSON.stringify(g.hiz)} sure=${g.sure}`);
    // KIRMIZI: hiz "50/s", yaklasik=false (basinda "~" yok) ve sure 00:00:00 — gercek: 1/s, 00:00:30.
    expect(g.hiz && g.hiz.yazi).not.toBe("50/s");
    expect(g.sure).toBe("00:00:30");
  });

  it("kart Gb'yi REDDETTI (ornegin pil testi suruyor: HTTP yaniti 2xx ama kayit baslamaz) -> hiz sonraki yabanci kayda yapismamali", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik", kayit: G(KDR.BOS) });
    await s.k.kayitBaslat(100);                                // komut gitti; G satiri hic KAYIT olmadi
    s.saat.ms += 3600000;
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 91, nokta: 0 }) });  // 1 saat sonra planli kayit (ornegin 60 s aralikli)
    s.saat.ms += 60000;
    s.yay({ kayit: G(KDR.KAYIT, { oturum: 91, nokta: 1 }) });
    const g = kayitGorunumu(s.k.akis.value.kayit, s.k.izleme.value, s.saat.ms);
    console.log(`[hiz-2] 60 s aralikli kayit -> ekranda hiz=${JSON.stringify(g.hiz)} sure=${g.sure}`);
    expect(g.hiz && g.hiz.yazi).not.toBe("10/s");              // KIRMIZI
  });
});

describe("curutucu 5C: Durum ekrani kart yokken ESKI olcumu gosteriyor", () => {
  it("akis hatada / kapali iken Durum'un V/A/W yazilari cizgi olmali (Canli ekrani boyle yapiyor)", async () => {
    const s = sahteler();
    await s.k.ac();
    s.yay({ hal: "acik", son: satirAyir(DSATIR) });
    s.yay({ hal: "hata" });                                    // kartin fisi cekildi
    s.saat.ms += 3600000;                                      // 1 saat gecti
    // Durum.vue: const olcum = computed(() => olcumYazilari(kabuk.akis.value.son));
    const olcum = olcumYazilari(s.k.akis.value.son);
    const bag = baglantiGorunumu({ baglanti: s.k.baglanti.value, akis: s.k.akis.value, sonGorulmeMs: s.k.sonGorulme.value, simdiMs: s.saat.ms });
    console.log(`[eski] baglanti satiri=${bag.anahtar}; Durum'daki olcum=${JSON.stringify(olcum)}`);
    expect(bag.anahtar).toBe("m.dr.ulasilamiyor");
    expect(olcum).toEqual({ v: YOK, a: YOK, w: YOK });         // KIRMIZI: 12.482 / 1.936 / 24.17 duruyor
  });

  it("Durum.vue kaynagi: olcum akisin haline bagli olmali (Canli.vue'daki gibi)", () => {
    const oku = (ad) => readFileSync(fileURLToPath(new URL(`../../src/ekran/${ad}`, import.meta.url)), "utf8");
    expect(oku("Canli.vue")).toContain("olcumYazilari(hal.value.akiyor ? kabuk.akis.value.son : null)");   // yesil (karsilastirma)
    expect(oku("Durum.vue")).not.toContain("olcumYazilari(kabuk.akis.value.son)");                           // KIRMIZI
  });
});

describe("curutucu 5C: grafik tamponu okunamayan olcumu de ciziyor", () => {
  function canliDuzenegi() {
    const dinleyen = {};
    const kart = { durum: () => ({ durum: "bagli" }), istek: async () => ({}), akisUrl: async () => "http://192.168.1.7:80/akis?_c=1&_s=1&_i=00" };
    const ag = { akisAc: async () => ({ kimlik: "a1" }), akisKapat: async () => {} };
    const canli = canliKur({ kart, ag, eklenti: { addListener: (ad, fn) => { dinleyen[ad] = fn; } } });
    return { canli, yay: (ad, veri) => dinleyen[ad](veri) };
  }

  it("adc_hata = 3 (iki ADC de okunamadi) ve 'nan' satirlari seri()'ye GIRMEMELI", async () => {
    const s = canliDuzenegi();
    s.canli.baslat();
    await new Promise((c) => setTimeout(c, 0));
    await new Promise((c) => setTimeout(c, 0));
    s.yay("akisDurum", { kimlik: "a1", hal: "acik" });
    s.yay("akis", { kimlik: "a1", satirlar: [
      "D 0.0000 0.000000 0.00000 10.0000 0.0027778 123456 500 0 3",      // okunamadi: sayilar anlamsiz
      "D nan nan nan 10.0000 0.0027778 123457 501 0 0",
    ] });
    const seri = s.canli.seri();
    const yazi = olcumYazilari(s.canli.durum().son);
    s.canli.durdur();
    console.log(`[grafik] seri.n=${seri.n} v=[${Array.from(seri.v).join(",")}]; rakamlar=${JSON.stringify(yazi)}`);
    expect(yazi).toEqual({ v: YOK, a: YOK, w: YOK });          // yesil: rakamlar cizgi
    expect(seri.n).toBe(0);                                    // KIRMIZI: grafik 0 V ve NaN noktasi ciziyor
  });
});
