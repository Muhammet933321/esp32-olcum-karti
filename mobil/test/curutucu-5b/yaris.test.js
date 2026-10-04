// CURUTUCU 5B — Y1..Y3: "401 + ayni acilis = cihaz silinmis" (A17) varsayimi ESZAMANLI isteklerde yanlis.
// Kart yeniden baslayinca ya da bir istek kartin 64'luk tekrar penceresinin gerisine dusunce, cihaz kartta
// DURDUGU halde uygulama "cihaz-silinmis" diyor; eslesmeyiKaldir da ayni yanilgiyla "kartta kaldirildi" diyor.
import { describe, it, expect, afterEach } from "vitest";
import { akibet, bekle, eslesmis, telefon } from "./yardim.mjs";

describe("curutucu 5B: yaris", () => {
  let kapat = [];
  afterEach(async () => { for (const k of kapat) await k(); kapat = []; });

  it("Y1: kart yeniden baslar + 5 ESZAMANLI istek -> hepsi gecmeli (cihaz kartta duruyor)", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    const t = telefon(dunya);
    await t.kart.baglan();
    expect((await t.kart.istek("GET", "/kayit/liste")).status).toBe(200);
    k.ayarla({ yenidenBasla: true });                     // kart yeniden basladi: cihaz listesi AYNI
    expect(k.durum.cihazlar.size).toBe(1);
    const sonuc = await Promise.all(Array.from({ length: 5 }, () => akibet(t.kart.istek("GET", "/kayit/liste"))));
    const turler = sonuc.map((s) => (s.tamam ? "200" : s.tur));
    // Tek istekte yeniden deneme calisiyor (kart.test.js); eszamanlida ilki acilisi gunceller, otekiler
    // "ayni acilis + 401" gorup pes eder.
    expect(turler).toEqual(Array(5).fill("200"));
  });

  it("Y2: 70 eszamanli istek, ILKI agda 400 ms gecikir -> pencerenin gerisine duser; 'cihaz-silinmis' DENMEMELI", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    let ilk = true;
    const t = telefon(dunya, {
      kanca: async (c, gonder) => {
        if (c.basliklar["X-Imza"] !== undefined && ilk) { ilk = false; await bekle(400); }
        return gonder(c);
      },
    });
    await t.kart.baglan();
    const sonuc = await Promise.all(Array.from({ length: 70 }, () => akibet(t.kart.istek("GET", "/kayit/liste"))));
    const turler = [...new Set(sonuc.map((s) => (s.tamam ? "200" : s.tur)))];
    expect(k.durum.cihazlar.size).toBe(1);                // cihaz kartta DURUYOR
    expect(turler).not.toContain("cihaz-silinmis");
  });

  it("Y3: eslesmeyiKaldir 'kartta: true' diyorsa cihaz kartta GERCEKTEN silinmis olmali", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    const t = telefon(dunya);
    await t.kart.baglan();
    k.ayarla({ yenidenBasla: true });
    // Arka planda suren iki istek + kullanici "Eslesmeyi kaldir"a basiyor.
    const [, , kaldir] = await Promise.all([
      akibet(t.kart.istek("GET", "/kayit/liste")), akibet(t.kart.istek("GET", "/kayit/liste")), t.kart.eslesmeyiKaldir(),
    ]);
    expect(dunya.disk.anahtarlar.size).toBe(0);           // telefon K'yi sildi
    // kartta: true ise kartin listesi bos olmali; degilse yetim kayit + kullaniciya yanlis bilgi.
    expect({ kartta: kaldir.kartta, karttaKalan: k.durum.cihazlar.size }).toEqual({ kartta: true, karttaKalan: 0 });
  });
});
