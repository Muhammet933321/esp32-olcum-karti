// 5P (P3) — telefon kopyasi panelin gozunden (K10): ORTAM.akislar / depo / esitle. Depo: gercek depo.js +
// KartDepo eklenti sahtesi (gercek dosyalar, gecici dizinde). Eşitleme: gercek cekirdek/esitleme.js + sahte kart.
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { T_NOKTA, kayitPaketle } from "../../ortak/src/kayit.js";
import { depoKur } from "../src/cekirdek/depo.js";
import { esitlemeKur } from "../src/cekirdek/esitleme.js";
import { HATA_DURUMU, ZAMAN_ANAHTARI, kopyaKur } from "../src/ortam/kopya.js";
import { metin } from "../src/ortam/metin.js";
import { depoSahtesi } from "./yardim/depo_sahtesi.mjs";
import { K1, K2, eslesmis } from "./curutucu-5b/yardim.mjs";

const kayit = (sira) => kayitPaketle(T_NOKTA, sira, 3, Uint8Array.from({ length: 36 }, (_, j) => (sira * 7 + j) & 255));
const akisKur = (ilk, son) => Buffer.concat(Array.from({ length: son - ilk + 1 }, (_, i) => kayit(ilk + i)));

let dizin;
let kapat = [];
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "ortam-kopya-")); });
afterEach(async () => {
  for (const k of kapat.splice(0)) await k();
  rmSync(dizin, { recursive: true, force: true });
});

function yerelDepo() {
  const m = new Map();
  return { getItem: (a) => (m.has(a) ? m.get(a) : null), setItem: (a, v) => { m.set(a, String(v)); }, removeItem: (a) => { m.delete(a); }, m };
}

function kartStub(kimlik, durum = "bagli") {
  return { durum: () => ({ durum, kimlik, adres: "127.0.0.1:1" }) };
}

describe("akislar / depo", () => {
  async function hazirla() {
    const ek = depoSahtesi(dizin);
    const depoAl = (k) => depoKur(ek, k);
    const d1 = depoAl(K1);
    await d1.durumYaz({ son_sira: 30, bayt: 1560, onaylanan: 0, kimlik: 3995957410 });
    await d1.veriEkle(akisKur(1, 30));
    await d1.kalYaz(new TextEncoder().encode('{"kayitlar":[]}'));
    return { ek, depoAl };
  }

  it("bagli kartin kopyasi panelin bicimiyle; kopyasi olmayan son kart listelenmez; zamanlar kalici", async () => {
    const { depoAl } = await hazirla();
    let t = 1000;
    const yerel = yerelDepo();
    const k = kopyaKur({ kartAl: async () => kartStub(K1), depoAl, esitlemeAl: async () => ({ dinle: () => () => {} }), sonKimlik: () => K2, yerel, simdiMs: () => t });
    const l = await k.akislar();
    expect(l).toEqual([{
      kimlik: 3995957410, kart: K1, bayt: akisKur(1, 30).length, durum: { son_sira: 30, bayt: 1560, onaylanan: 0, kimlik: 3995957410 },
      olusma: 1000, guncelleme: 1000, kalVar: true, telefon: true,
    }]);
    t = 5000;
    expect((await k.akislar())[0].olusma).toBe(1000);                         // ilk gorulme ani korunur
    expect(JSON.parse(yerel.getItem(ZAMAN_ANAHTARI))[K1].olusma).toBe(1000);
  });

  it("kart bagli degilken son baglanilan kartin kopyasi; hic kart bilinmiyorsa bos; durum.json bozuk kopya atlanir", async () => {
    const { ek, depoAl } = await hazirla();
    const k = kopyaKur({ kartAl: async () => kartStub(null, "bagli-degil"), depoAl, esitlemeAl: async () => ({ dinle: () => () => {} }), sonKimlik: () => K1 });
    expect((await k.akislar()).map((a) => [a.kimlik, a.kart])).toEqual([[3995957410, K1]]);
    const bos = kopyaKur({ kartAl: async () => { throw new Error("yok"); }, depoAl, esitlemeAl: async () => ({}), sonKimlik: () => null });
    expect(await bos.akislar()).toEqual([]);
    ek.bozDurum(K1, Buffer.from("{bozuk"));
    expect(await k.akislar()).toEqual([]);
  });

  it("depo(akis kimligi): okuma yarisi kopyadan, `kart` alani; yazma yollari REDDEDER; bilinmeyen kimlik anlasilir hata", async () => {
    const { depoAl } = await hazirla();
    const k = kopyaKur({ kartAl: async () => kartStub(K1), depoAl, esitlemeAl: async () => ({ dinle: () => () => {} }) });
    const d = await k.depo(3995957410);                    // akislar() cagrilmadan da bulur
    expect(d.kart).toBe(K1);
    expect(d.telefon).toBe(true);
    expect(await d.veriBoyu()).toBe(akisKur(1, 30).length);
    expect(Buffer.from(await d.veriOku(0)).equals(akisKur(1, 30))).toBe(true);
    expect((await d.durumOku()).son_sira).toBe(30);
    expect(new TextDecoder().decode(await d.kalOku())).toBe('{"kayitlar":[]}');
    expect((await k.depo("3995957410")).kart).toBe(K1);
    for (const yaz of ["durumYaz", "veriEkle", "veriKirp", "kalYaz", "kalArsivle", "sifirla"]) {
      await expect(d[yaz](new Uint8Array(1)), yaz).rejects.toThrow(metin("or.kopya_salt_okuma", "tr"));
    }
    expect(Object.isFrozen(d)).toBe(true);
    await expect(k.depo(12345)).rejects.toThrow(metin("or.kopya_yok", "tr"));
  });
});

describe("esitle: Android eşitleyicisi panelin sonuc bicimiyle", () => {
  it("gercek eşitleyici + sahte kart: { durum: 'tamam', sonuc: { yeni_kayit, son_sira, ... }, bayt }; ilerleme bayt", async () => {
    const { k, t } = await eslesmis();
    kapat.push(() => k.kapat());
    k.ayarla({ kayitlar: akisKur(1, 400) });
    const ek = depoSahtesi(dizin);
    const depoAl = (kimlik) => depoKur(ek, kimlik);
    const e = esitlemeKur({ kartAl: async () => t.kart, depoAl, istekAraMs: 0 });
    const baglanSayisi = [];
    const ko = kopyaKur({ kartAl: async () => t.kart, depoAl, esitlemeAl: async () => e, arka: { baglan: async () => { baglanSayisi.push(1); return t.kart.durum(); } }, yoklaMs: 1 });
    const ilerleme = [];
    const r = await ko.esitle({ kimlik: 7, ilerleme: (b) => ilerleme.push(b) });
    expect(r).toEqual({
      durum: "tamam", sonuc: { yeni_kayit: 400, son_sira: 400, bekleyen: 0, bosluk_adet: 0, onayli: false }, bayt: akisKur(1, 400).length,
    });
    expect(ilerleme.at(-1)).toBe(akisKur(1, 400).length);
    for (let i = 1; i < ilerleme.length; i++) expect(ilerleme[i]).toBeGreaterThan(ilerleme[i - 1]);
    expect(baglanSayisi.length).toBe(1);
    expect(Buffer.from(ek.dosya(K1)).equals(akisKur(1, 400))).toBe(true);
    // Panel artik bu kopyayi akis kimligiyle gorur.
    const l = await ko.akislar();
    expect(l).toHaveLength(1);
    expect(l[0]).toMatchObject({ kart: K1, bayt: akisKur(1, 400).length, telefon: true });
    expect(Number.isSafeInteger(l[0].kimlik)).toBe(true);
    const r2 = await ko.esitle({});
    expect(r2).toMatchObject({ durum: "tamam", sonuc: { yeni_kayit: 0 }, bayt: 0 });
  });

  it("hata turleri panelin `durum`una; akis degistiyse 'akis' + sifirlama metni; kart bagli degilse 'ag'; eşitleyici yoksa 'depo'", async () => {
    const ek = depoSahtesi(dizin);
    const depoAl = (k) => depoKur(ek, k);
    const kos = (hal, kart = kartStub(K1)) => kopyaKur({ kartAl: async () => kart, depoAl, esitlemeAl: async () => ({ simdi: async () => hal, dinle: () => () => {} }) }).esitle({});
    expect(await kos({ hal: "hata", hata: "kopya-uyusmuyor", sifirlaOner: true })).toEqual({ durum: "akis", mesaj: metin("or.akis_degisti", "tr"), bayt: 0, sifirlaOner: true });
    expect(await kos({ hal: "hata", hata: "mesgul" })).toMatchObject({ durum: "kilit" });
    expect(await kos({ hal: "hata", hata: "cihaz-silinmis" })).toMatchObject({ durum: "imza", mesaj: `${metin("or.esitleme_hata", "tr")} (cihaz-silinmis)` });
    expect(await kos({ hal: "hata", hata: "garip" })).toMatchObject({ durum: "hata" });
    expect(await kos({ hal: "bos" })).toMatchObject({ durum: "kilit", mesaj: metin("or.esitleme_mesgul", "tr") });
    expect(await kos({ hal: "tamam" }, kartStub(null, "bagli-degil"))).toEqual({ durum: "ag", mesaj: metin("or.bagli_degil", "tr"), bayt: 0 });
    const yok = kopyaKur({ kartAl: async () => kartStub(K1), depoAl, esitlemeAl: async () => { throw new Error("modul"); } });
    expect(await yok.esitle({})).toEqual({ durum: "depo", mesaj: metin("or.esitleme_yok", "tr"), bayt: 0 });
    expect(HATA_DURUMU["depo-bozuk"]).toBe("depo");
  });
});
