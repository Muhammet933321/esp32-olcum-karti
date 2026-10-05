// 5D-2 — esitleme dongusu (A20–A23). GERCEK kart.js + ag.js + kasa (kopru SAHTE), sahte kart 127.0.0.1'de,
// depo: depo.js + eklenti sahtesi (gercek dosyalar, gecici dizinde).
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { T_NOKTA, KayitHatasi, kayitPaketle } from "../../ortak/src/kayit.js";
import { EsitlemeHatasi } from "../../ortak/src/esitle.js";
import { CalismaHatasi, HttpHatasi } from "../../ortak/src/imza.js";
import { DepoHatasi, depoKur } from "../src/cekirdek/depo.js";
import { ARALIK_MS, ISTEK_ARA_MS, PARCA_BAYT, bosluklar, esitlemeKur, hataTuru } from "../src/cekirdek/esitleme.js";
import { KartHatasi } from "../src/cekirdek/kart.js";
import { depoSahtesi } from "./yardim/depo_sahtesi.mjs";
import { K1, eslesmis } from "./curutucu-5b/yardim.mjs";

const kayit = (sira) => kayitPaketle(T_NOKTA, sira, 3, Uint8Array.from({ length: 36 }, (_, j) => (sira * 7 + j) & 255));
const akisKur = (ilk, son) => Buffer.concat(Array.from({ length: son - ilk + 1 }, (_, i) => kayit(ilk + i)));

let dizin;
let kapat = [];
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "esitleme-")); });
afterEach(async () => {
  for (const k of kapat) await k();
  kapat = [];
  rmSync(dizin, { recursive: true, force: true });
});

async function duzenek({ kayitSayisi = 60, onay = false, secenek = {}, kartSecenek = {} } = {}) {
  const { k, t } = await eslesmis(kartSecenek);
  kapat.push(() => k.kapat());
  if (kayitSayisi) k.ayarla({ kayitlar: akisKur(1, kayitSayisi) });
  const ek = depoSahtesi(dizin);
  const durumlar = [];
  const e = esitlemeKur({
    kartAl: async () => t.kart, depoAl: (kimlik) => depoKur(ek, kimlik), onayAcik: () => onay, istekAraMs: 0, ...secenek,
  });
  e.dinle((d) => durumlar.push(d.hal));
  const goKomutlari = () => k.durum.komutlar.filter((x) => /^Go/.test(x));
  return { k, t, ek, e, durumlar, goKomutlari };
}

describe("esitleme — tek tur", () => {
  it("sabitler: 60 s aralik, istek baslari arasi 100 ms, parca 8192 B", () => {
    expect([ARALIK_MS, ISTEK_ARA_MS, PARCA_BAYT]).toEqual([60000, 100, 8192]);
  });

  it("kartin akisi dosyaya bayt bayt iner; durum 'tamam'; varsayilan ONAYSIZ: karta Go GITMEZ", async () => {
    const { k, ek, e, durumlar, goKomutlari } = await duzenek({ kayitSayisi: 400 });      // 20 800 B: uc parca
    expect(e.durum()).toMatchObject({ hal: "bos", sonMs: null, onayli: false });
    const d = await e.simdi();
    expect(d).toMatchObject({ hal: "tamam", yeni: 400, sonSira: 400, bosluk: 0, bekleyen: 0, hata: null, sifirlaOner: false, onayli: false });
    expect(typeof d.sonMs).toBe("number");
    expect(durumlar).toEqual(["esitleniyor", "tamam"]);
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 400))).toBe(true);
    expect(goKomutlari()).toEqual([]);
    expect(k.durum.komutlar.length).toBe(0);                                              // HICBIR komut gitmedi
    // Ikinci tur: yeni kayit yok.
    expect(await e.simdi()).toMatchObject({ hal: "tamam", yeni: 0, sonSira: 400 });
    // Karta yeni kayit geldi: yalniz yeniler iner.
    k.ayarla({ kayitlar: akisKur(1, 410) });
    expect(await e.simdi()).toMatchObject({ hal: "tamam", yeni: 10, sonSira: 410 });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 410))).toBe(true);
  });

  it("butun istekler IMZALI gider (zorunlu kartta 401 yok) ve yalniz /kayit/veri + /kal/liste", async () => {
    const { t, e } = await duzenek({ kayitSayisi: 30, kartSecenek: { zorunlu: 1 } });
    const once = t.kopru.cagrilar.length;
    expect((await e.simdi()).hal).toBe("tamam");
    const yeni = t.kopru.cagrilar.slice(once);
    expect(yeni.length).toBeGreaterThan(1);
    for (const c of yeni) {
      expect(c.basliklar["X-Imza"]).toBeDefined();
      expect(c.yontem ?? "GET").toBe("GET");
      expect(new URL(c.url).pathname).toMatch(/^\/(kayit\/veri|kal\/liste)$/);
    }
  });

  it("onay ACIKSA: Go<sira> yalniz veri DISKE indikten sonra gider ve imzalidir", async () => {
    const { k, ek, e, goKomutlari } = await duzenek({ kayitSayisi: 40, onay: true });
    const sirasi = [];
    const asil = ek.veriEkle;
    ek.veriEkle = async (v) => { const y = await asil(v); sirasi.push(`yaz:${y.boy}`); return y; };
    const say = () => { const g = goKomutlari(); if (g.length > sirasi.filter((x) => x.startsWith("Go")).length) sirasi.push(g.at(-1)); };
    const zamanlayici = setInterval(say, 1);
    const d = await e.simdi();
    clearInterval(zamanlayici);
    say();
    expect(d).toMatchObject({ hal: "tamam", onayli: true, sonSira: 40 });
    expect(goKomutlari().at(-1)).toBe("Go40");
    expect(sirasi[0]).toBe("yaz:2080");                    // ONCE yazim
    expect(sirasi.indexOf("Go40")).toBeGreaterThan(0);
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 40))).toBe(true);
    expect(k.durum.ret401).toBe(0);
  });

  it("onay ayari HER turda yeniden okunur (anahtar kapatilinca sonraki turda Go gitmez)", async () => {
    let acik = true;
    const { k, e, goKomutlari } = await duzenek({ kayitSayisi: 10, secenek: { onayAcik: () => acik } });
    await e.simdi();
    expect(goKomutlari()).toEqual(["Go10"]);
    acik = false;
    k.ayarla({ kayitlar: akisKur(1, 20) });
    expect(await e.simdi()).toMatchObject({ hal: "tamam", onayli: false, sonSira: 20 });
    expect(goKomutlari()).toEqual(["Go10"]);
    // Yalniz kesin `true` acar.
    for (const v of [1, "true", null, undefined, {}]) {
      rmSync(join(dizin, K1), { recursive: true, force: true });        // onceki turun kopyasi kalmasin
      const d2 = await duzenek({ kayitSayisi: 5, secenek: { onayAcik: () => v } });
      expect(await d2.e.simdi(), String(v)).toMatchObject({ hal: "tamam", yeni: 5, onayli: false });
      expect(d2.goKomutlari(), String(v)).toEqual([]);
    }
  });

  it("es zamanli cagrilar TEK tura baglanir; iki ayri dongu ayni depoya yazamaz (kilit)", async () => {
    const { k, t, ek, e } = await duzenek({ kayitSayisi: 200 });
    k.ayarla({ gecikmeMs: 5 });
    const once = t.kopru.cagrilar.length;
    const [a, b, c] = await Promise.all([e.simdi(), e.simdi(), e.simdi()]);
    expect(a).toBe(b);
    expect(b).toBe(c);
    const veriIstekleri = t.kopru.cagrilar.slice(once).filter((x) => x.url.includes("/kayit/veri")).length;
    expect(veriIstekleri).toBeLessThanOrEqual(4);          // 10 400 B / 8192 -> 2 parca + bos son tur (+1 pay)
    // Ikinci, BAGIMSIZ dongu ayni anda: 'mesgul' der, dosya bozulmaz.
    k.ayarla({ kayitlar: akisKur(1, 400) });
    const e2 = esitlemeKur({ kartAl: async () => t.kart, depoAl: (kimlik) => depoKur(ek, kimlik), istekAraMs: 0 });
    const [d1, d2] = await Promise.all([e.simdi(), new Promise((r) => setTimeout(r, 8)).then(() => e2.simdi())]);
    expect(d1.hal).toBe("tamam");
    expect(d2).toMatchObject({ hal: "hata", hata: "mesgul", sifirlaOner: false });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 400))).toBe(true);
  });

  it("istek BASLARI arasi >= istekAraMs (saat ve bekleme enjekte)", async () => {
    const saat = { ms: 1000 };
    const beklemeler = [];
    const { t, e } = await duzenek({
      kayitSayisi: 400,
      secenek: { istekAraMs: 100, simdiMs: () => saat.ms, bekle: async (ms) => { beklemeler.push(ms); saat.ms += ms; } },
    });
    const baslar = [];
    const asil = t.kart.istek;
    t.kart.istek = (...a) => { baslar.push(saat.ms); saat.ms += 30; return asil(...a); };      // her istek 30 ms "surer"
    expect((await e.simdi()).hal).toBe("tamam");
    expect(baslar.length).toBeGreaterThan(3);
    for (let i = 1; i < baslar.length; i++) expect(baslar[i] - baslar[i - 1]).toBeGreaterThanOrEqual(100);
    expect(beklemeler.every((ms) => ms === 70)).toBe(true);                                    // 100 - 30
    expect(beklemeler.length).toBe(baslar.length - 1);
  });
});

describe("esitleme — bosluk sayimi", () => {
  it("ILK esitlemede kartin eski kayitlari silmis olmasi (akis 1'den baslamiyor) BOSLUK SAYILMAZ; aradaki gercek bosluk sayilir", async () => {
    // Gercek kartta goruldu (2026-10-05): kopya bosken kartin ilk kaydi 59043'tu ve ekran "kopyada bosluk kaldi" dedi.
    const { k, ek, e } = await duzenek({ kayitSayisi: 0 });
    k.ayarla({ kayitlar: akisKur(500, 530) });
    expect(await e.simdi()).toMatchObject({ hal: "tamam", yeni: 31, sonSira: 530, bosluk: 0 });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(500, 530))).toBe(true);
    // Kart 531..539'u sildi (baskasi onayladi): bu GERCEK bosluktur.
    k.ayarla({ kayitlar: akisKur(540, 545) });
    expect(await e.simdi()).toMatchObject({ hal: "tamam", yeni: 6, sonSira: 545, bosluk: 1 });
    expect(bosluklar([[1, 59043]])).toBe(0);
    expect(bosluklar([[1, 5], [9, 12]])).toBe(1);
    expect(bosluklar([[531, 540]])).toBe(1);
    expect(bosluklar(null)).toBe(0);
  });
});

describe("esitleme — hata halleri (ASLA atmaz)", () => {
  it("hataTuru (saf)", () => {
    expect(hataTuru(new EsitlemeHatasi("x"))).toEqual({ tur: "kopya-uyusmuyor", sifirlaOner: true });
    expect(hataTuru(new KayitHatasi("x"))).toEqual({ tur: "yanit-bozuk", sifirlaOner: false });
    expect(hataTuru(new CalismaHatasi("x"))).toEqual({ tur: "mesgul", sifirlaOner: false });
    expect(hataTuru(new DepoHatasi("bozuk"))).toEqual({ tur: "depo-bozuk", sifirlaOner: true });
    expect(hataTuru(new DepoHatasi("yazilamadi"))).toEqual({ tur: "depo", sifirlaOner: false });
    expect(hataTuru(new KartHatasi("cihaz-silinmis"))).toEqual({ tur: "cihaz-silinmis", sifirlaOner: false });
    expect(hataTuru(new HttpHatasi(500, null, "/x"))).toEqual({ tur: "http", sifirlaOner: false });
    for (const e of [null, undefined, new Error("gizli /yol"), "metin", { name: "KartHatasi" }]) expect(hataTuru(e)).toEqual({ tur: "ic-hata", sifirlaOner: false });
  });

  it("kart bagli degil / kartAl atiyor / depoAl atiyor: hal 'hata', soz COZULUR", async () => {
    const bagsiz = esitlemeKur({ kartAl: async () => ({ durum: () => ({ durum: "bagli-degil" }) }), depoAl: () => { throw new Error("cagrilmamali"); } });
    expect(await bagsiz.simdi()).toMatchObject({ hal: "hata", hata: "bagli-degil" });
    const eslesmemis = esitlemeKur({ kartAl: async () => ({ durum: () => ({ durum: "eslesmemis", kimlik: K1 }) }), depoAl: () => { throw new Error("cagrilmamali"); } });
    expect(await eslesmemis.simdi()).toMatchObject({ hal: "hata", hata: "bagli-degil" });
    const atan = esitlemeKur({ kartAl: async () => { throw new Error("gizli"); }, depoAl: () => null });
    expect(await atan.simdi()).toMatchObject({ hal: "hata", hata: "ic-hata" });
    const depoAtan = esitlemeKur({ kartAl: async () => ({ durum: () => ({ durum: "bagli", kimlik: K1 }) }), depoAl: () => { throw new DepoHatasi("yazilamadi"); } });
    expect(await depoAtan.simdi()).toMatchObject({ hal: "hata", hata: "depo" });
    expect(() => esitlemeKur({})).toThrow(TypeError);
  });

  it("kart kapandi (ag hatasi): 'ag'; kopya AYNEN kalir; kart donunce kaldigi yerden surer", async () => {
    const { k, ek, e } = await duzenek({ kayitSayisi: 50 });
    await e.simdi();
    await k.kapat();
    kapat = [];
    const d = await e.simdi();
    expect(d).toMatchObject({ hal: "hata", hata: "ag", sifirlaOner: false });
    expect(d.sonSira).toBe(50);                              // son BASARILI turun bilgisi silinmez
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 50))).toBe(true);
  });

  it("A23: akis kimligi degisti / dosya kisa / durum bozuk -> sifirlaOner; sifirla sonrasi bastan iner", async () => {
    const { k, ek, e } = await duzenek({ kayitSayisi: 30 });
    await e.simdi();
    k.ayarla({ kayitKimlik: 9, kayitlar: akisKur(1, 35) });                 // kart bicimlendi
    expect(await e.simdi()).toMatchObject({ hal: "hata", hata: "kopya-uyusmuyor", sifirlaOner: true });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 30))).toBe(true);    // eldeki kopyaya DOKUNULMADI
    await e.sifirla();
    expect(e.durum()).toMatchObject({ hal: "bos", sonSira: null, sifirlaOner: false });
    expect(ek.dosya(K1)).toBe(null);
    expect(await e.simdi()).toMatchObject({ hal: "tamam", yeni: 35 });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 35))).toBe(true);
    // Durum dosyasi bozuk: "bos depo" sayilip USTUNE YAZILMAZ.
    ek.bozDurum(K1, Buffer.from("{\"son_si"));
    expect(await e.simdi()).toMatchObject({ hal: "hata", hata: "depo-bozuk", sifirlaOner: true });
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 35))).toBe(true);
  });

  it("kartin yaniti bozuk (CRC): depoya YAZILMAZ, 'yanit-bozuk'", async () => {
    const { t, ek } = await duzenek({ kayitSayisi: 10 });
    // Yanit yolda bozulur: govdenin bir bayti degisir.
    const kart = {
      durum: () => t.kart.durum(),
      istek: async (yontem, yol, arg, govde) => {
        const y = await t.kart.istek(yontem, yol, arg, govde);
        if (yol !== "/kayit/veri") return y;
        const b = new Uint8Array(await y.arrayBuffer());
        if (b.length > 30) b[30] ^= 0xff;
        return new Response(b, { status: 200, headers: y.headers });
      },
    };
    const e2 = esitlemeKur({ kartAl: async () => kart, depoAl: (kimlik) => depoKur(ek, kimlik), istekAraMs: 0 });
    expect(await e2.simdi()).toMatchObject({ hal: "hata", hata: "yanit-bozuk", sifirlaOner: false });
    expect(ek.dosya(K1)).toBe(null);
  });

  it("dinleyici atarsa esitleme etkilenmez; dinle() birakilabilir", async () => {
    const { e } = await duzenek({ kayitSayisi: 5 });
    const gorulen = [];
    e.dinle(() => { throw new Error("arayuz"); });
    const birak = e.dinle((d) => gorulen.push(d.hal));
    expect((await e.simdi()).hal).toBe("tamam");
    birak();
    await e.simdi();
    expect(gorulen).toEqual(["esitleniyor", "tamam"]);
  });
});

describe("esitleme — ne zaman kosar (A22)", () => {
  function sayac() {
    const saat = { ms: 5_000_000 };
    let kosu = 0;
    let coz = null;
    const kart = { durum: () => { kosu += 1; return { durum: "bagli-degil" }; } };
    const kartAl = () => new Promise((c) => { coz = () => c(kart); });
    const e = esitlemeKur({ kartAl, depoAl: () => null, simdiMs: () => saat.ms });
    const bitir = async () => { const c = coz; coz = null; if (c) c(); await new Promise((r) => setTimeout(r, 0)); };
    return { saat, e, bitir, kosu: () => kosu, bekliyor: () => coz !== null };
  }

  it("tik: gorunur + bagli ise ilk tikte, sonra 60 s'de bir; arka planda / bagli degilken HIC", async () => {
    const s = sayac();
    expect(s.e.tik({ gorunur: false, bagli: true })).toBe(false);
    expect(s.e.tik({ gorunur: true, bagli: false })).toBe(false);
    expect(s.bekliyor()).toBe(false);
    expect(s.e.tik({ gorunur: true, bagli: true })).toBe(true);
    expect(s.e.tik({ gorunur: true, bagli: true })).toBe(false);      // suruyor
    await s.bitir();
    expect(s.kosu()).toBe(1);
    s.saat.ms += ARALIK_MS - 1;
    expect(s.e.tik({ gorunur: true, bagli: true })).toBe(false);      // BASARISIZ denemeden sonra da 60 s beklenir
    s.saat.ms += 1;
    expect(s.e.tik({ gorunur: false, bagli: true })).toBe(false);     // arka planda esitleme YOK
    expect(s.e.tik({ gorunur: true, bagli: true })).toBe(true);
    await s.bitir();
    expect(s.kosu()).toBe(2);
  });

  it("baglandi / kayitBitti: hemen bir tur; tur surerken gelirse o bitince BIR tur daha (kaydin sonu kacmasin)", async () => {
    const s = sayac();
    s.e.baglandi();
    expect(s.bekliyor()).toBe(true);
    s.e.kayitBitti();
    s.e.kayitBitti();                                                  // iki olay da TEK ek tur
    await s.bitir();
    expect(s.kosu()).toBe(1);
    expect(s.bekliyor()).toBe(true);                                   // ek tur basladi
    await s.bitir();
    expect(s.kosu()).toBe(2);
    expect(s.bekliyor()).toBe(false);                                  // ucuncu tur YOK
    // Olay 60 s sayacini da yeniler: hemen ardindan tik kosmaz.
    expect(s.e.tik({ gorunur: true, bagli: true })).toBe(false);
  });

  it("elle simdi() tur surerken AYNI sozu doner ve ek tur ISTEMEZ", async () => {
    const s = sayac();
    const a = s.e.simdi(), b = s.e.simdi();
    expect(a).toBe(b);
    await s.bitir();
    expect(s.bekliyor()).toBe(false);
    expect(s.kosu()).toBe(1);
  });
});
