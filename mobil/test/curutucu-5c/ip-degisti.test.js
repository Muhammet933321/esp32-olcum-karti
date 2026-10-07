// CURUTUCU 5C — kartin IP'si degisince (DHCP, yonlendirici yeniden basladi, kart AP'den ev agina dondu):
// GERCEK kartKur + GERCEK arka plan (src/ortam/arka_plan.js; 5P P6'dan once kabukDurumu). Iddia (arka_plan.js
// YENIDEN_ARA_MS yorumu): "akis bu kadar suredir hatadaysa kart yeniden ARANIR (adresi degismis olabilir)".
// Var olan test (ekran.test.js "akis uzun sure hatadaysa karti yeniden arar") sahte kartin durumunu ELLE
// "bagli-degil" yapiyor (`s.kart.d = …`); gercek kart.js ag hatasinda baglantiyi HIC dusurmez.
import { describe, it, expect, vi } from "vitest";

vi.mock("../../src/cekirdek/eklenti.js", () => ({
  KartAg: { wifiDurumu: async () => ({ hataAyiklama: false }), istek: async () => { throw new Error("kullanilmaz"); }, p0: () => new Promise(() => {}) },
  Kesif: {}, Kasa: {},
}));

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { KartAgHatasi } from "../../src/cekirdek/ag.js";
import { kartKur } from "../../src/cekirdek/kart.js";
import { durdurAdresleri } from "../../src/cekirdek/uygulama.js";
import { YENIDEN_ARA_MS, arkaPlanKur } from "../../src/ortam/arka_plan.js";

const KIMLIK = "0123456789abcdef";
const ESKI = "192.168.1.7:80";
const YENI = "192.168.1.23:80";

function duzenek() {
  const aramalar = [];
  const yer = { ip: ESKI };
  const kesif = {
    bul: async () => {
      aramalar.push(yer.ip);
      return { adres: yer.ip, kimlik: KIMLIK, bilgi: { saat: 1 } };
    },
  };
  const kasa = {
    kaydet: async () => {},
    liste: async () => [{ kimlik: KIMLIK }],
    cihazYukle: async () => ({ kimlik: KIMLIK, n: 1, K: new Uint8Array(32), ad: "sinama", sayac: 0, acilis: "ab".repeat(16) }),
  };
  // Eski adreste artik kimse yok: her istek ag hatasi.
  const ag = { kartFetch: async () => { throw new KartAgHatasi("baglanti"); } };
  const kart = kartKur({ ag, kesif, kasa });

  let hal = "kapali", dinleyen = null;
  const canli = {
    baslat() { hal = "baglaniyor"; },
    durdur() { hal = "kapali"; },
    durum: () => ({ bagli: hal === "acik", hal, son: null, kayit: null, yas_ms: null }),
    dinle(fn) { dinleyen = fn; return () => { dinleyen = null; }; },
    seri: () => null,
    komut: async () => true,
  };
  const saat = { ms: 1000000 };
  const aralik = { fn: null };
  const k = arkaPlanKur({
    kartAl: async () => kart, canliAl: async () => canli, belge: null, simdiMs: () => saat.ms,
    araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
  });
  // Ondeyken + panel akis isterken (telefon ortami): ac() karti arar, akisIste(true) akisi acar.
  const ac = async () => { await k.ac(); k.akisIste(true); await bekle(); await bekle(); };
  const yay = (yeniHal) => { hal = yeniHal; if (dinleyen) dinleyen(); };
  return { k, ac, kart, yer, aramalar, saat, aralik, yay };
}

const bekle = () => new Promise((c) => setTimeout(c, 0));

describe("curutucu 5C: kartin adresi degisti", () => {
  it("akis 5 dakikadir hatada: kart YENIDEN aranmali ve yeni adres bulunmali", async () => {
    const s = duzenek();
    await s.ac();
    expect(s.k.durum().baglanti).toMatchObject({ durum: "bagli", adres: ESKI });
    s.yay("acik");

    s.yer.ip = YENI;                          // kart artik baska adreste
    for (let i = 0; i < 10; i++) {            // 10 x 30 s = 5 dakika; her turda akis yine dusuyor
      s.yay("hata");
      s.saat.ms += YENIDEN_ARA_MS;
      s.aralik.fn();
      await bekle();
      await bekle();
    }
    // KIRMIZI: kesif yalniz acilista bir kez calisti; kabuk kart.durum()'un "bagli" demesine guvendi.
    expect(s.aramalar.length, "kesif.bul cagri sayisi").toBeGreaterThanOrEqual(2);
    expect(s.k.durum().baglanti.adres).toBe(YENI);
  });

  it("ayni durumda ACIL DURDUR'un adres listesi kartin YENI adresini icermeli", async () => {
    const s = duzenek();
    await s.ac();
    s.yay("acik");
    s.yer.ip = YENI;
    for (let i = 0; i < 10; i++) {
      s.yay("hata");
      s.saat.ms += YENIDEN_ARA_MS;
      s.aralik.fn();
      await bekle();
      await bekle();
    }
    // uygulama.js adresler(): bagli adres (kart.durum().adres) + onbellek (son basarili kesif = ESKI).
    const liste = durdurAdresleri(s.kart.durum().adres, { adres: ESKI, kimlik: KIMLIK });
    // KIRMIZI: liste [ESKI] — p0 eski IP'ye ve 192.168.4.1'e gider, kart (YENI) hic denenmez -> ULASILAMADI.
    expect(liste).toContain(YENI);
  });

  it("uygulama.js canli'yi 'yenidenBul' ile kurmali (canli.js'teki yeniden bulma yolu ACIK olmali)", () => {
    const u = readFileSync(fileURLToPath(new URL("../../src/cekirdek/uygulama.js", import.meta.url)), "utf8");
    const cagri = /modul\.canliKur\(\{[^}]*\}\)/.exec(u)[0];
    // KIRMIZI: canli.js'in `yenidenBul` secenegi (varsayilan false) hicbir yerde acilmiyor: olu kod.
    expect(cagri).toMatch(/yenidenBul:\s*true/);
  });
});
