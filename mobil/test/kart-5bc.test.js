// kart.js — curutucu 5B'nin YASAYAN buldugu mutasyonlarin (C2, C4–C8) ve duzeltmelerin iddialari.
// Duzenek: test/curutucu-5b/yardim.mjs (kopru kancali telefon + kotu kart).
import { describe, it, expect, afterEach } from "vitest";
import { agKur } from "../src/cekirdek/ag.js";
import { kartKur } from "../src/cekirdek/kart.js";
import { KasaHatasi, kasaKur } from "../src/cekirdek/kasa.js";
import { sahteKartAc } from "./sahte-kart/sunucu.mjs";
import { kasaSahtesi } from "./yardim/kasa_sahtesi.mjs";
import { kopruSahtesi } from "./yardim/kopru_sahtesi.mjs";
import { K1, K2, PAROLA, adres, akibet, bilgiYaniti, dunyaKur, eslesmis, hata, kotuKartAc, telefon } from "./curutucu-5b/yardim.mjs";

describe("kart: curutucu 5B duzeltmeleri", () => {
  let kapat = [];
  afterEach(async () => { for (const k of kapat) await k(); kapat = []; });
  const ac = async (secenek = {}) => {
    const k = await sahteKartAc({ port: 0, parola: PAROLA, kimlik: K1, ...secenek });
    kapat.push(() => k.kapat());
    return k;
  };

  it("C2: anahtar saklanamazsa bellekteki K SIFIRLANIR — ama geri alma istegi (kartta sil) imzalandiktan SONRA", async () => {
    const k = await ac();
    const t = telefon(dunyaKur(k));
    await t.kart.baglan();
    let yakalanan = null;
    t.kasa.cihazSakla = async (c) => { yakalanan = c; throw new KasaHatasi("ic-hata"); };
    expect((await hata(t.kart.esles("sinama telefonu", PAROLA))).tur).toBe("kasa");
    expect(yakalanan.K.length).toBe(32);
    expect([...yakalanan.K].every((b) => b === 0)).toBe(true);
    expect(k.durum.cihazlar.size).toBe(0);                 // geri alma GERCEK K ile imzalandi, kart kabul etti
  });

  it("C4: kesfin soyledigi acilis 32 kucuk onaltilik degilse imzaya GIRMEZ (kart ilk imzayi reddetmek zorunda kalmaz)", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    for (const kotu of ["KOTU", "AB".repeat(16), "ab".repeat(15) + "a", 7]) {
      const ham = kopruSahtesi();
      const ag = agKur(ham, { yerelDongu: true, zamanAsimiMs: 3000 });
      const kesif = { bul: async () => ({ adres: adres(k), kimlik: K1, bilgi: { ...bilgiYaniti(), acilis: kotu } }) };
      const kart = kartKur({ ag, kesif, kasa: kasaKur(kasaSahtesi(dunya.disk)) });
      expect((await kart.baglan()).durum).toBe("bagli");
      const once = k.durum.ret401;
      expect((await kart.istek("GET", "/kayit/liste")).status).toBe(200);
      expect(k.durum.ret401, String(kotu)).toBe(once);
      expect(ham.cagrilar.filter((c) => c.basliklar["X-Imza"] !== undefined).length).toBe(1);
    }
  });

  it("C5: esles SURERKEN baska bir karta baglanilirsa, eslesilen kartin anahtariyla O adrese imzali istek GITMEZ", async () => {
    const k1 = await ac(), k2 = await ac({ kimlik: K2 });
    let kapi;
    const bekleyen = new Promise((coz) => { kapi = coz; });
    const t = telefon(dunyaKur(k1), {
      kanca: async (c, gonder) => { if (c.url.includes("/eslestir/kanit")) await bekleyen; return gonder(c); },
    });
    await t.kart.baglan();
    const eslesme = t.kart.esles("sinama telefonu", PAROLA);
    const b2 = await t.kart.baglan({ elle: adres(k2) });   // eslesme bitmeden: kasa bos -> 'eslesmemis', K2
    expect({ durum: b2.durum, kimlik: b2.kimlik }).toEqual({ durum: "eslesmemis", kimlik: K2 });
    kapi();
    expect((await eslesme).kimlik).toBe(K1);               // K1'in anahtari saklandi; baglanti ise K2
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("eslesmemis");
    expect(t.imzalilar()).toEqual([]);
    expect(k2.durum.ret401).toBe(0);
  });

  it("C6: saat verilirken AG hatasi olursa sonraki cagri YENIDEN verir (bir kez kurali gitmeyen istegi saymaz)", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    let dusur = true;
    const t = telefon(dunya, {
      saat: () => 1_790_000_000_500,
      kanca: async (c, gonder) => {
        if (dusur && c.url.includes("/saat")) { dusur = false; const e = new Error("baglanti"); e.code = "baglanti"; throw e; }
        return gonder(c);
      },
    });
    await t.kart.baglan();
    expect((await hata(t.kart.saatVer())).tur).toBe("ag");
    expect(k.durum.saat).not.toBe(1_790_000_000);
    expect(await t.kart.saatVer()).toBe(true);
    expect(k.durum.saat).toBe(1_790_000_000);
    expect(await t.kart.saatVer()).toBe(false);
  });

  it("C7: Retry-After ust siniri 3600 s — kart daha uzun bekletemez (saniye TASINMAZ, genel 'bekle' metni)", async () => {
    const sonuc = {};
    for (const bekle of ["3600", "3601", "99999", "0", "7"]) {
      const kotu = await kotuKartAc((yol) => {
        if (yol === "/eslestir/bilgi") return { govde: bilgiYaniti() };
        if (yol === "/eslestir/baslat") return { kod: 429, basliklar: { "Retry-After": bekle }, govde: "" };
        return null;
      });
      kapat.push(() => kotu.kapat());
      const t = telefon(dunyaKur(kotu));
      await t.kart.baglan();
      const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
      expect(e.tur).toBe("bekle");
      sonuc[bekle] = e.saniye;
    }
    expect(sonuc).toEqual({ 3600: 3600, 3601: undefined, 99999: undefined, 0: undefined, 7: 7 });
  });

  it("C8: eslesmeyiKaldir — kart 401 derse 'kartta: null' (BILINMIYOR); true YALNIZ kart 2xx dediginde", async () => {
    // Cihaz kartta zaten yok (USB'den silinmis): kart 401 der. Telefon "kartta kaldirildi" DIYEMEZ.
    const bir = await eslesmis();
    kapat.push(() => bir.k.kapat());
    const t = telefon(bir.dunya);
    await t.kart.baglan();
    bir.k.durum.cihazlar.clear();
    expect(await t.kart.eslesmeyiKaldir()).toEqual({ kartta: null });
    expect(bir.dunya.disk.anahtarlar.size).toBe(0);        // yerelde yine de silinir
    // Kart baska bir hatayla (500) yanitlarsa: kartta: false.
    const iki = await eslesmis();
    await iki.k.kapat();
    const kotu = await kotuKartAc((yol) => (yol === "/eslestir/bilgi" ? { govde: bilgiYaniti() } : { kod: 500, govde: "" }));
    kapat.push(() => kotu.kapat());
    iki.dunya.adaylar = [adres(kotu)];
    iki.dunya.onbellek.yaz(null);
    const t2 = telefon(iki.dunya);
    expect((await t2.kart.baglan()).durum).toBe("bagli");
    expect(await t2.kart.eslesmeyiKaldir()).toEqual({ kartta: false });
    expect(iki.dunya.disk.anahtarlar.size).toBe(0);
    // Kart silerse: true ve kartin listesi BOS.
    const uc = await eslesmis();
    kapat.push(() => uc.k.kapat());
    const t3 = telefon(uc.dunya);
    await t3.kart.baglan();
    expect(await t3.kart.eslesmeyiKaldir()).toEqual({ kartta: true });
    expect(uc.k.durum.cihazlar.size).toBe(0);
  });

  it("es zamanli iki istek + adresteki kart o arada DEGISIRSE: ikinci istek IMZALADIGI acilistan farkli acilis gorunce kimligi yeniden dogrular", async () => {
    const { k, dunya } = await eslesmis();
    await k.kapat();
    const Y = "cd".repeat(16);
    let degisti = false;
    const kotu = await kotuKartAc((yol) => (yol === "/eslestir/bilgi"
      ? { govde: bilgiYaniti(degisti ? { kimlik: K2 } : {}) }
      : { kod: 401, basliklar: { "X-Acilis": Y }, govde: "" }));
    kapat.push(() => kotu.kapat());
    dunya.adaylar = [adres(kotu)];
    dunya.onbellek.yaz(null);
    let kapi, imzali = 0;
    const bekleyen = new Promise((coz) => { kapi = coz; });
    const t = telefon(dunya, {
      kanca: async (c, gonder) => {
        const y = await gonder(c);
        if (c.basliklar["X-Imza"] !== undefined && ++imzali === 2) await bekleyen;     // B'nin ILK yaniti bekletilir
        return y;
      },
    });
    await t.kart.baglan();
    const a = t.kart.istek("GET", "/kayit/liste"), b = t.kart.istek("GET", "/kayit/liste");
    // A: 401 + yeni acilis -> kimlik (hala K1) dogrulanir, cihaz.acilis = Y olur, yeniden imzalar, yine 401.
    expect((await akibet(a)).tur).toBe("cihaz-silinmis");
    degisti = true;                                        // adresteki kart artik BASKA kimlik soyluyor
    kapi();
    // B eski acilisla imzalanmisti: Y, cihaz.acilis'e ESIT olsa da B'nin imzaladigindan FARKLI -> kimlik sorulur.
    expect((await akibet(b)).tur).toBe("kimlik-uymuyor");
    expect(kotu.imzalilar().length).toBe(3);               // A: 2, B: 1 (yeniden imza YOK)
    expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("bagli-degil");
  });

  it("ayni acilista 401: istek YENI sayacla BIR kez yeniden imzalanir; X-Acilis'siz 401'de yeniden imza YOK", async () => {
    const { k, dunya } = await eslesmis();
    await k.kapat();
    let n = 0;
    const kotu = await kotuKartAc((yol) => {
      if (yol === "/eslestir/bilgi") return { govde: bilgiYaniti() };
      if (yol === "/basliksiz") return { kod: 401, govde: "" };
      return n++ === 0 ? { kod: 401, basliklar: { "X-Acilis": bilgiYaniti().acilis }, govde: "" } : { govde: { oturumlar: [] } };
    });
    kapat.push(() => kotu.kapat());
    dunya.adaylar = [adres(kotu)];
    dunya.onbellek.yaz(null);
    const t = telefon(dunya);
    await t.kart.baglan();
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    const sayaclar = kotu.imzalilar().map((i) => BigInt(i.basliklar["x-sayac"]));
    expect(sayaclar.length).toBe(2);
    expect(sayaclar[1] > sayaclar[0]).toBe(true);
    expect((await hata(t.kart.istek("GET", "/basliksiz"))).tur).toBe("cihaz-silinmis");
    expect(kotu.imzalilar().length).toBe(3);
  });
});
