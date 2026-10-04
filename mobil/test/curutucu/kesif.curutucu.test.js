// CURUTUCU (5A-7): kesif.js'e karsi kanit testleri. Her "it" bir ACIGI gosterir ve su an KIRMIZIDIR;
// acik kapaninca yesile doner. Ag YOK: kartFetch ve eklenti sahte (bellek ici).
import { describe, it, expect } from "vitest";
import { kesifKur } from "../../src/cekirdek/kesif.js";

const K1 = "00112233aabbccdd";
const K2 = "ffeeddcc99887766";
const ASILI = Symbol("asili");

// adres -> kimlik (kart) | ASILI (hic donmeyen istek) | yok (baglanti hatasi). cozum: ad -> "ip:port".
function sahteAg(harita, cozum = {}) {
  const cagrilar = [];
  async function kartFetch(url) {
    const ad = /^http:\/\/([^/]+)\//.exec(url)[1];
    cagrilar.push(ad);
    const d = harita[ad];
    if (d === ASILI) return new Promise(() => {});
    if (typeof d !== "string") { const e = new Error("baglanti"); e.tur = "baglanti"; throw e; }
    return { status: 200, adres: cozum[ad] ?? null, json: async () => ({ kimlik: d, acilis: "1" }) };
  }
  return { kartFetch, cagrilar };
}

// Soz `ms` icinde sonuclanmazsa "ASILI KALDI" doner (testin kendisi asilmasin).
const sinirla = (soz, ms) => Promise.race([
  soz.then((s) => ({ tamam: s }), (e) => ({ hata: e })),
  new Promise((c) => setTimeout(() => c("ASILI KALDI"), ms)),
]);

describe("curutucu / kesif: asili kalma (Review Focus 4: 'kesif takilmaz')", () => {
  it("K1: NSD taramasi hic donmezse ve baska aday yoksa bul() SONSUZA DEK asili kalir", async () => {
    const ag = sahteAg({});
    const eklenti = { nsdTara: () => new Promise(() => {}) };
    const k = kesifKur({ kartFetch: ag.kartFetch, eklenti, zamanAsimiMs: 100, yenidenDene: 0, nsdSureMs: 100, sabitAdaylar: [{ adres: "192.168.4.1", kaynak: "ap" }] });
    const s = await sinirla(k.bul({ beklenenKimlik: K1 }), 1500);
    expect(s, "bul() 1.5 s icinde sonuclanmali (bulunamadi)").not.toBe("ASILI KALDI");
  });

  it("K2: tek bir adayin istegi donmezse (baslik damlatan sahte kart, H1) bul() asili kalir — JS'te kendi suresi yok", async () => {
    const ag = sahteAg({ "192.168.4.1": ASILI });
    const k = kesifKur({ kartFetch: ag.kartFetch, zamanAsimiMs: 100, yenidenDene: 0, sabitAdaylar: [{ adres: "192.168.4.1", kaynak: "ap" }, { adres: "192.168.1.9", kaynak: "ad" }] });
    const s = await sinirla(k.bul(), 1500);
    expect(s, "zamanAsimiMs = 100 iken bul() 1.5 s icinde sonuclanmali").not.toBe("ASILI KALDI");
  });

  it("K3: elle girilen adres asili + agda SAGLAM bir kart var -> saglam kart 'yedek'te bekler, bul() hic donmez", async () => {
    const ag = sahteAg({ "192.168.1.50": ASILI, "192.168.4.1": K1 });
    const k = kesifKur({ kartFetch: ag.kartFetch, zamanAsimiMs: 100, yenidenDene: 0, sabitAdaylar: [{ adres: "192.168.4.1", kaynak: "ap" }] });
    const s = await sinirla(k.bul({ elle: "192.168.1.50" }), 1500);
    expect(s, "saglam kart yanit verdi; elle adres suresini doldurunca o kullanilmali").not.toBe("ASILI KALDI");
  });
});

describe("curutucu / kesif: NSD ile gercek karti gizleme (dogrulanmamis TXT / siralama)", () => {
  it("K4: saldirgan gercek kartin IP'sini YANLIS TXT kimligiyle duyurur -> kart yoklanmadan elenir", async () => {
    // Kart 192.168.1.7'de ve kimligi K1. Tek ulasim yolu NSD (ad cozulmuyor, onbellek yok).
    const ag = sahteAg({ "192.168.1.7": K1 });
    const eklenti = { nsdTara: async () => ({ servisler: [{ ad: "olcum", ip: "192.168.1.7", port: 80, kimlik: K2 }] }) };
    const k = kesifKur({ kartFetch: ag.kartFetch, eklenti, zamanAsimiMs: 100, yenidenDene: 0, sabitAdaylar: [] });
    const s = await sinirla(k.bul({ beklenenKimlik: K1 }), 1500);
    // "TXT yalnizca eleme icindir; dogrulama /eslestir/bilgi" — ama eleme DOGRULANMAMIS veriye dayaniyor.
    expect(s.tamam?.kimlik, `kart ulasilabilir; sonuc: ${s.hata?.tur}`).toBe(K1);
    expect(ag.cagrilar).toContain("192.168.1.7");
  });

  it("K5: 8 sahte 'olcum*' duyurusu gercek kartin onune gecer -> 9. siradaki gercek kart hic aday olmaz", async () => {
    const ag = sahteAg({ "192.168.1.7": K1 });
    const sahte = Array.from({ length: 8 }, (_, i) => ({ ad: `olcum-${i}`, ip: `192.168.1.${100 + i}`, port: 80 }));
    const eklenti = { nsdTara: async () => ({ servisler: [...sahte, { ad: "olcum", ip: "192.168.1.7", port: 80, kimlik: K1 }] }) };
    const k = kesifKur({ kartFetch: ag.kartFetch, eklenti, zamanAsimiMs: 100, yenidenDene: 0, sabitAdaylar: [] });
    const s = await sinirla(k.bul({ beklenenKimlik: K1 }), 1500);
    expect(s.tamam?.kimlik, `sonuc: ${s.hata?.tur}`).toBe(K1);
  });
});

describe("curutucu / kesif: 'ayni adres bir kez yoklanir' iddiasi", () => {
  it("K6: olcum.local + onbellekteki IP AYNI kart -> karta iki eszamanli istek (tekillestirme cozumden ONCE)", async () => {
    const ag = sahteAg({ "olcum.local": K1, "192.168.1.7": K1 }, { "olcum.local": "192.168.1.7:80", "192.168.1.7": "192.168.1.7:80" });
    const onbellek = { oku: () => ({ adres: "192.168.1.7", kimlik: K2 }), yaz: () => {} };
    // beklenenKimlik uymuyor ki yaris erken bitmesin ve butun adaylar gorulsun.
    const h = await kesifKur({ kartFetch: ag.kartFetch, onbellek, zamanAsimiMs: 100, yenidenDene: 0, sabitAdaylar: [{ adres: "olcum.local", kaynak: "ad" }] })
      .bul({ beklenenKimlik: K2 }).catch((e) => e);
    const ayniKart = h.denenenler.filter((d) => d.adres === "192.168.1.7");
    expect(ayniKart.length, "ayni IP denenenler listesinde iki kez").toBe(1);
  });
});
