// Curutucu 5D — Kayitlar listesinin / kayit gorunumunun YANLIS bilgi verdigi haller.
// Istemci GERCEK (kayit_istemci.js), islemci GERCEK (kayit_veri.js); Worker yerine ayni islemciyi saran
// sahte bir isci (mesaj protokolu src/isci/kayit_isci.js ile ayni); depo: depo.js + eklenti sahtesi.
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { depoKur } from "../../src/cekirdek/depo.js";
import { kayitIstemciKur } from "../../src/cekirdek/kayit_istemci.js";
import { islemciKur, listeKur, veriKur } from "../../src/cekirdek/kayit_veri.js";
import { kayitlarKur } from "../../src/cekirdek/kayitlar.js";
import { satirGorunumu } from "../../src/ekran/kayitlar_gorunum.js";
import { Akis, ikiOturum } from "../yardim/akis_ornek.mjs";
import { depoSahtesi } from "../yardim/depo_sahtesi.mjs";

const K = "0123456789abcdef";
const K2 = "fedcba9876543210";
let dizin;
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "curutucu5d-ky-")); });
afterEach(() => { rmSync(dizin, { recursive: true, force: true }); });

// url -> kart kimligi -> o kartin dosyasi (uretimdeki yerelOku + MainActivity'nin yaptigi).
const getirKur = (ek) => async (url) => ek.dosya(/^\/_depo\/([0-9a-f]{16})\//.exec(url)[1]) || new Uint8Array(0);

// Worker taklidi: kayit_isci.js'in kabugu. cokert(): tarayicinin `onerror`u (bellek bitti, betik hatasi).
function sahteIsci(ek) {
  const islemci = islemciKur({ getir: getirKur(ek) });
  const w = {
    onmessage: null, onerror: null, bitti: false,
    postMessage(m) {
      const { no, is, ...arguman } = m;
      islemci.isle(is, arguman).then(
        (sonuc) => { if (!w.bitti && w.onmessage) w.onmessage({ data: { no, tamam: true, sonuc } }); },
        (h) => { if (!w.bitti && w.onmessage) w.onmessage({ data: { no, tamam: false, tur: h && h.tur } }); },
      );
    },
    terminate() { w.bitti = true; },
    cokert() { if (w.onerror) w.onerror({ message: "x" }); },
  };
  return w;
}

async function doldur(ek, kimlik, bayt, akisKimlik = 7) {
  const depo = depoKur(ek, kimlik);
  await depo.veriEkle(bayt);
  await depo.durumYaz({ son_sira: 1, bayt: bayt.length, onaylanan: 0, kimlik: akisKimlik });
}

describe("curutucu 5D — Kayitlar", () => {
  it("isci (Worker) coktukten sonra liste BOS gosterilmez: kopya yedek islemciye yeniden yuklenir", async () => {
    const ek = depoSahtesi(dizin);
    const { bayt, a, b } = ikiOturum();
    await doldur(ek, K, bayt);
    let isci = null;
    const istemci = kayitIstemciKur({
      isciKur: () => { isci = sahteIsci(ek); return isci; },
      yedekKur: () => islemciKur({ getir: getirKur(ek) }),
    });
    const kart = { durum: () => ({ durum: "bagli-degil", adres: null, kimlik: null }), istek: async () => { throw new Error("yok"); } };
    const k = kayitlarKur({ istemci, kartAl: async () => kart, depoAl: (kimlik) => depoKur(ek, kimlik), sonKimlik: () => K });

    const once = await k.liste();
    expect(once.satirlar.map((s) => s.oturum).sort()).toEqual([a, b].sort());
    expect(istemci.isciVar()).toBe(true);

    isci.cokert();                                   // WebView isciyi oldurdu
    expect(istemci.isciVar()).toBe(false);

    // Dosya DEGISMEDI: telefonda hala iki oturum var. Ekran yenilenince (sekme degisimi, esitleme bitti) ayni liste beklenir.
    const sonra = await k.liste();
    expect(sonra.satirlar.map((s) => s.oturum).sort()).toEqual([a, b].sort());
  });

  it("isci coktukten sonra kayit gorunumu 'bu kayit telefonda yok' DEMEZ (oturum hala dosyada)", async () => {
    const ek = depoSahtesi(dizin);
    const { bayt, a } = ikiOturum();
    await doldur(ek, K, bayt);
    let isci = null;
    const istemci = kayitIstemciKur({ isciKur: () => { isci = sahteIsci(ek); return isci; }, yedekKur: () => islemciKur({ getir: getirKur(ek) }) });
    const kart = { durum: () => ({ durum: "bagli-degil", adres: null, kimlik: null }), istek: async () => { throw new Error("yok"); } };
    const k = kayitlarKur({ istemci, kartAl: async () => kart, depoAl: (kimlik) => depoKur(ek, kimlik), sonKimlik: () => K });
    expect((await k.oturum(a)).adet).toBe(60);
    isci.cokert();
    const g = await k.oturum(a);
    expect(g).not.toBe(null);
    expect(g.adet).toBe(60);
  });

  it("kartin akisi degistiyse (GF! / baska akis) ayni numarali iki oturum AYIRT edilir: tekil liste anahtari + 'eski kart' isareti", () => {
    // Telefondaki kopya akis 7'den; kart artik akis 9'da ve ONDA da 101 numarali (BASKA) bir oturum var.
    const { bayt, a } = ikiOturum();
    const kartDizini = { kimlik: 9, aktif: 0, oturumlar: [{ id: a, tur: 1, hiz_ms: 1000, unix_s: 1790009999, nokta: 5, durum: 2, son: 300 }] };
    const satirlar = listeKur(veriKur(bayt, 7), { kart: kartDizini });
    expect(satirlar.filter((s) => s.oturum === a).length).toBe(2);          // on kosul: iki AYRI kayit, ayni numara
    const gorunen = satirlar.map(satirGorunumu);
    // Kayitlar.vue'nun v-for anahtari (kaynaktan okunur) gorunen satirlarda TEKIL olmali (Vue: yinelenen anahtar = bozuk guncelleme).
    const vue = readFileSync(fileURLToPath(new URL("../../src/ekran/Kayitlar.vue", import.meta.url)), "utf8");
    const alan = /<li v-for="s in gorunen" :key="s\.(\w+)">/.exec(vue)[1];
    const anahtarlar = gorunen.map((s) => s[alan]);
    expect(new Set(anahtarlar).size, `:key="s.${alan}" -> ${JSON.stringify(anahtarlar)}`).toBe(anahtarlar.length);
    // Eski karttan kalan satir ekranda isaretli olmali (panel: 'kl.eski_kart' rozeti); telefonda bilgi gorunume hic gecmiyor.
    const eski = gorunen.filter((s, i) => satirlar[i].eskiKart === true);
    expect(eski.length).toBe(2);
    for (const s of eski) expect(s.eskiKart, "satirGorunumu eskiKart'i tasimiyor").toBe(true);
  });

  it("aralik istatistigi (okuma) EKRANDAKI kartin kopyasindan hesaplanir: araya baska kartin listesi girse de", async () => {
    // Kart A ve kart B'nin kopyalari telefonda; ikisinde de AYNI numarali oturum var (her akis sirayi kendi sayar).
    const ek = depoSahtesi(dizin);
    const akisA = new Akis(100); const oA = akisA.basla(); akisA.noktalar(oA, { adet: 40, v0: 10, dv: 0, amper: 0.5 }); akisA.bitir(oA, 40);
    const akisB = new Akis(100); const oB = akisB.basla(); akisB.noktalar(oB, { adet: 40, v0: 20, dv: 0, amper: 0.5 }); akisB.bitir(oB, 40);
    expect(oA).toBe(oB);
    await doldur(ek, K, akisA.bayt(), 7);
    await doldur(ek, K2, akisB.bayt(), 9);
    let bagliKimlik = K;
    const kart = { durum: () => ({ durum: "eslesmemis", adres: "192.168.1.7:80", kimlik: bagliKimlik }), istek: async () => { throw new Error("yok"); } };
    const istemci = kayitIstemciKur({ isciKur: null, yedekKur: () => islemciKur({ getir: getirKur(ek) }) });
    const k = kayitlarKur({ istemci, kartAl: async () => kart, depoAl: (kimlik) => depoKur(ek, kimlik), sonKimlik: () => null });

    const g = await k.oturum(oA);                     // kayit gorunumu A kartinin oturumunu acti: 10 V
    expect(g.seriler.find((s) => s.ad === "V").y[0]).toBe(10);
    // Kayitlar ekraninin yolda kalmis yenilemesi (Kayitlar.vue: `sira` yalniz EKRANI korur, istegi iptal etmez)
    // bu arada kart degistikten sonra kosar:
    bagliKimlik = K2;
    await k.liste();
    // Kullanici grafigi kaydirir: gorunen araligin istatistigi istenir. Grafik 10 V gosteriyor.
    const ok = await k.okuma(oA, g.t0, g.t1);
    expect(ok.v.ort).toBeCloseTo(10, 6);
  });
});
