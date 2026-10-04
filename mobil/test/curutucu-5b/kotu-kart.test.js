// CURUTUCU 5B — kotu niyetli kart / imza oracle'i / sir sizmasi.
//   O1 (KIRMIZI): 401'de verilen X-Acilis BICIMI denetlenmeden imzaya giriyor (32 hex degil).
//   O2 (yesil, tuttu): surekli yeni X-Acilis veren kart istek basina en cok 2 imza alir.
//   O3 (KIRMIZI): kanit 200 + eksik/bicimsiz kart_kanit -> 'kart-gecersiz' (kanit sizdi ama 'kart-sahte' denmiyor).
//   O2b (duzeltmeyle eklendi): ayni acilis + yeni acilis karisik verilse de istek basina en cok 2 imza.
// 2026-10-04: aciklar duzeltildi; bu dosya artik REGRESYON testi (hepsi yesil olmali).
//   O4 (yesil, tuttu): parola / kanit / K hicbir hata nesnesine, durum nesnesine, kopru cagrisina (Kasa disinda) girmez.
import { describe, it, expect, afterEach } from "vitest";
import { ref } from "vue";
import { eslesDurumu } from "../../src/ekran/esles_durum.js";
import { K1, PAROLA, akibet, bilgiYaniti, dunyaKur, eslesmis, hata, kotuKartAc, telefon } from "./yardim.mjs";

void ref;
const yazi = (e) => JSON.stringify(e, Object.getOwnPropertyNames(e));

describe("curutucu 5B: kotu kart", () => {
  let kapat = [];
  afterEach(async () => { for (const k of kapat) await k(); kapat = []; });

  // Eslesmis bir telefonun diskini alip, ayni kimligi soyleyen KOTU karta baglar.
  async function kotuyeBagli(isleyici) {
    const { k, dunya } = await eslesmis();
    await k.kapat();
    const kotu = await kotuKartAc(isleyici);
    kapat.push(() => kotu.kapat());
    dunya.adaylar = [`127.0.0.1:${kotu.port}`];
    dunya.onbellek.yaz(null);
    const t = telefon(dunya);
    const b = await t.kart.baglan();
    expect(b.durum).toBe("bagli");                         // kimlik acik bilgi: taklit etmek yeter
    return { t, kotu };
  }

  it("O1: X-Acilis 32 onaltilik degilse onunla IMZA uretilmemeli", async () => {
    const { t, kotu } = await kotuyeBagli((yol) => (yol === "/eslestir/bilgi"
      ? { govde: bilgiYaniti() }
      : { kod: 401, basliklar: { "X-Acilis": "saldirganin-sectigi-metin" }, govde: "" }));
    await akibet(t.kart.istek("POST", "/komut", [], "p1"));
    expect(kotu.imzalilar().length).toBe(1);               // 2 geliyor: ikincisi saldirganin metniyle imzali
  });

  it("O2 (tuttu): her 401'de YENI acilis veren kart, istek basina en cok 2 imza alir", async () => {
    let n = 0;
    const { t, kotu } = await kotuyeBagli((yol) => (yol === "/eslestir/bilgi"
      ? { govde: bilgiYaniti() }
      : { kod: 401, basliklar: { "X-Acilis": (++n).toString(16).padStart(32, "0") }, govde: "" }));
    const e = await hata(t.kart.istek("GET", "/kayit/liste"));
    expect(e.tur).toBe("cihaz-silinmis");
    expect(kotu.imzalilar().length).toBe(2);
  });

  it("O2b: once AYNI acilisla 401 (yeni sayacla yeniden imza), sonra hep YENI acilis -> yine en cok 2 imza", async () => {
    let n = 0;
    const { t, kotu } = await kotuyeBagli((yol) => {
      if (yol === "/eslestir/bilgi") return { govde: bilgiYaniti() };
      const acilis = n++ === 0 ? bilgiYaniti().acilis : n.toString(16).padStart(32, "0");
      return { kod: 401, basliklar: { "X-Acilis": acilis }, govde: "" };
    });
    const e = await hata(t.kart.istek("POST", "/komut", [], "p1"));
    expect(e.tur).toBe("cihaz-silinmis");
    expect(kotu.imzalilar().length).toBe(2);
    const sayaclar = kotu.imzalilar().map((i) => i.basliklar["x-sayac"]);
    expect(new Set(sayaclar).size).toBe(2);               // ikinci imza YENI sayacla
  });

  it("O1b: X-Acilis BUYUK harfli onaltilik ya da 31 hane -> 'kart-gecersiz', tek imza", async () => {
    for (const kotuAcilis of ["AB".repeat(16), "ab".repeat(16).slice(1), "ab".repeat(17)]) {
      const { t, kotu } = await kotuyeBagli((yol) => (yol === "/eslestir/bilgi"
        ? { govde: bilgiYaniti() }
        : { kod: 401, basliklar: { "X-Acilis": kotuAcilis }, govde: "" }));
      expect((await hata(t.kart.istek("GET", "/kayit/liste"))).tur).toBe("kart-gecersiz");
      expect(kotu.imzalilar().length).toBe(1);
    }
  });

  it("O3: kanit yollandiktan sonra kart_kanit EKSIK gelirse de kullanici 'kart-sahte' ile uyarilmali", async () => {
    const kotu = await kotuKartAc((yol) => {
      if (yol === "/eslestir/bilgi") return { govde: bilgiYaniti() };
      if (yol === "/eslestir/baslat") return { govde: { eno: 1, nk: "11".repeat(16) } };
      if (yol === "/eslestir/kanit") return { govde: { n: 1 } };          // kaniti aldi, kendi kanitini vermedi
      return null;
    });
    kapat.push(() => kotu.kapat());
    const t = telefon(dunyaKur(kotu));
    await t.kart.baglan();
    const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
    expect(kotu.durum.istekler.some((i) => i.yol === "/eslestir/kanit")).toBe(true);   // cevrimdisi tahmin malzemesi gitti
    expect(e.tur).toBe("kart-sahte");
  });

  it("O4 (tuttu): parola, kanit ve K — hata nesnesi, durum nesnesi ve KartAg kopru cagrilarinda yok", async () => {
    const turler = [];
    for (const kanitYaniti of [{ kod: 403, govde: "x" }, { govde: { n: 1, kart_kanit: "00".repeat(32) } }, { govde: "{bozuk" }, { kod: 429, basliklar: { "Retry-After": "7" }, govde: "" }]) {
      const kotu = await kotuKartAc((yol) => {
        if (yol === "/eslestir/bilgi") return { govde: bilgiYaniti() };
        if (yol === "/eslestir/baslat") return { govde: { eno: 1, nk: "11".repeat(16) } };
        if (yol === "/eslestir/kanit") return kanitYaniti;
        return null;
      });
      kapat.push(() => kotu.kapat());
      const t = telefon(dunyaKur(kotu));
      await t.kart.baglan();
      const s = eslesDurumu(t.kart, { kareBekle: async () => {}, varsayilanAd: "sinama telefonu" });
      s.parola.value = PAROLA;
      await s.gonder();
      const kanit = new URLSearchParams(kotu.durum.istekler.find((i) => i.yol === "/eslestir/kanit").sorgu).get("kanit");
      expect(kanit).toMatch(/^[0-9a-f]{64}$/);
      const durumYazi = JSON.stringify({ ad: s.ad.value, parola: s.parola.value, hata: s.hata.value, tamam: s.tamam.value });
      const e = await hata(t.kart.esles("sinama telefonu", PAROLA + "x"));
      for (const metin of [durumYazi, yazi(e)]) {
        expect(metin).not.toContain(PAROLA);
        expect(metin).not.toContain(kanit);
      }
      expect(s.parola.value).toBe("");
      // KartAg koprusune giden hicbir cagride parola yok; kanit yalniz /eslestir/kanit URL'sinde.
      for (const c of t.kopru.cagrilar) {
        expect(JSON.stringify(c)).not.toContain(PAROLA);
        if (!c.url.includes("/eslestir/kanit")) expect(JSON.stringify(c)).not.toContain(kanit);
      }
      expect(t.kasaEk.cagrilar.filter((c) => c.ad === "anahtarYaz")).toEqual([]);
      turler.push(s.hata.value.anahtar);
    }
    // DUZELTMEYLE GUNCELLENDI (bulgu 6): kanit gittikten sonra gelen bicimsiz 2xx ("{bozuk") de 'kart-sahte'.
    expect(turler).toEqual(["m.es.hata_parola_yanlis", "m.es.hata_kart_sahte", "m.es.hata_kart_sahte", "m.es.hata_kart_gecersiz"]);
    expect(K1).toMatch(/^[0-9a-f]{16}$/);
  });
});
