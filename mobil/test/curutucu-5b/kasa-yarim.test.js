// CURUTUCU 5B — S1..S4: cihazSakla YARIDA kalinca (anahtar yazildi, ilk isaret yazilamadi) tutarsiz durum.
// kart.test.js yalniz `anahtarYaz`in bozuldugu hali siniyor; `sayacYaz` bozulursa:
//   * anahtar diskte KALIR ("Eslestirme geri alindi" metni yanlis),
//   * kasa.js'in bellekteki kaydi SIFIRLANMIS K'li cihaz nesnesini tutar -> baglan() "bagli" der ve
//     uygulama 32 sifir baytlik anahtarla imzalar,
//   * kart o sirada ulasilmazsa uygulama yeniden baslayinca telefon SESSIZCE eslesmis olur.
// S4: iki kasaKur nesnesi ayni diskte (S1 ihlali) -> AYNI sayac iki kez kullanilir; 'geri' bunu yakalamaz.
import { describe, it, expect, afterEach } from "vitest";
import { sahteKartAc } from "../sahte-kart/sunucu.mjs";
import { imzaDogru } from "../sahte-kart/imza_dogrula.mjs";
import { K1, PAROLA, akibet, dunyaKur, eslesmis, hata, telefon } from "./yardim.mjs";

describe("curutucu 5B: kasa yarim / iki yazar", () => {
  let kapat = [];
  afterEach(async () => { for (const k of kapat) await k(); kapat = []; });

  async function yarimEsles({ kartKapali = false } = {}) {
    const k = await sahteKartAc({ port: 0, parola: PAROLA, kimlik: K1 });
    kapat.push(() => k.kapat());
    const dunya = dunyaKur(k);
    let kapandi = false;
    const t = telefon(dunya, {
      // kartKapali: kanit yaniti alindiktan SONRA kart ulasilmaz olur (telefon Wi-Fi'den dustu):
      // geri alma istegi (/cihaz/sil) karta varamaz.
      kanca: async (c, gonder) => {
        if (kapandi) { const e = new Error("baglanti"); e.code = "baglanti"; throw e; }
        const y = await gonder(c);
        if (kartKapali && c.url.includes("/eslestir/kanit")) kapandi = true;
        return y;
      },
    });
    await t.kart.baglan();
    t.kasaEk.bozYazim = "ic-hata";                         // ilk isaret yazimi (sayacYaz) bir kez bozulur
    const e = await hata(t.kart.esles("sinama telefonu", PAROLA));
    return { k, dunya, t, e, kartAc: () => { kapandi = false; } };
  }

  it("S1: 'kasa' hatasindan sonra diskte anahtar KALMAMALI (kullaniciya 'geri alindi' deniyor)", async () => {
    const { dunya, e, k } = await yarimEsles();
    expect(e.tur).toBe("kasa");
    expect(k.durum.cihazlar.size).toBe(0);                 // kart tarafi geri alindi
    expect(dunya.disk.anahtarlar.size).toBe(0);            // telefon tarafi alinmadi
  });

  it("S2: 'kasa' hatasindan sonra baglan() 'bagli' DEMEMELI; SIFIR anahtarla imza uretilmemeli", async () => {
    const { t, e } = await yarimEsles();
    expect(e.tur).toBe("kasa");
    const b = await t.kart.baglan();
    await akibet(t.kart.istek("GET", "/kayit/liste"));
    const imzali = t.imzalilar().filter((c) => c.url.endsWith("/kayit/liste"));
    expect({ durum: b.durum, imzaliIstek: imzali.length }).toEqual({ durum: "eslesmemis", imzaliIstek: 0 });
  });

  it("S2b: o imza gercekten 32 SIFIR baytlik anahtarla atilmis (herkes uretebilir)", async () => {
    const { t, k } = await yarimEsles();
    await t.kart.baglan();
    await akibet(t.kart.istek("GET", "/kayit/liste"));
    const c = t.imzalilar().filter((x) => x.url.endsWith("/kayit/liste")).at(-1);
    // DUZELTMEYLE GUNCELLENDI (bulgu 4): artik o istek HIC atilmiyor (eski beklenti "atilmis olmali" idi).
    expect(c).toBe(undefined);
    // Atilan hicbir imzali istek (geri alma /cihaz/sil dahil) SIFIR anahtarla imzali degil.
    expect(t.imzalilar().length).toBeGreaterThan(0);
    for (const x of t.imzalilar()) {
      const u = new URL(x.url);
      const sifirla = imzaDogru(new Uint8Array(32), x.yontem, u.pathname, [...u.searchParams], k.durum.acilis, BigInt(x.basliklar["X-Sayac"]), Buffer.alloc(0), x.basliklar["X-Imza"]);
      expect(sifirla).toBe(false);
    }
  });

  it("S3: geri alma karta ULASAMAZSA yeniden baslatinca telefon sessizce ESLESMIS olmamali", async () => {
    const { k, dunya, e, kartAc } = await yarimEsles({ kartKapali: true });
    expect(e.tur).toBe("kasa");                            // kullaniciya: "kaydedilemedi, geri alindi"
    expect(k.durum.cihazlar.size).toBe(1);                 // kartta yetim kayit (bu, kaynakta kabul edilmis)
    kartAc();
    const t2 = telefon(dunya);                             // uygulama yeniden basladi
    const b = await t2.kart.baglan();
    const s = await akibet(t2.kart.istek("POST", "/komut", [], "G?"));
    expect({ durum: b.durum, komutGecti: Boolean(s.tamam) }).toEqual({ durum: "eslesmemis", komutGecti: false });
  });

  it("S4: ayni diskte iki kasaKur (iki ekran / servis): iki istek AYNI sayaci tasimamali", async () => {
    const { k, dunya } = await eslesmis();
    kapat.push(() => k.kapat());
    const saat = () => 1_700_000_000_000;                  // saat isaretin gerisinde (geri alinmis / 4 s icinde yeniden acilis)
    const a = telefon(dunya, { saat }), b = telefon(dunya, { saat });
    await a.kart.baglan();
    await b.kart.baglan();
    const ra = await akibet(a.kart.istek("GET", "/kayit/liste"));
    const rb = await akibet(b.kart.istek("GET", "/kayit/liste"));
    const sa = a.imzalilar().map((c) => c.basliklar["X-Sayac"]), sb = b.imzalilar().map((c) => c.basliklar["X-Sayac"]);
    expect(sa.length).toBe(1);
    expect(sb.length).toBe(1);
    // Ikinci yazarin yazimi diskteki degere ESIT: eklenti (ve Kotlin SayacDosyasi) 'geri' demez.
    expect({ ayniSayac: sa[0] === sb[0], a: ra.tamam ? 200 : ra.tur, b: rb.tamam ? 200 : rb.tur })
      .toEqual({ ayniSayac: false, a: 200, b: 200 });
  });
});
