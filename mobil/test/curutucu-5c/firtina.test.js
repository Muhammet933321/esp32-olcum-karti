// CURUTUCU 5C — yeniden baglanma firtinasi: GERCEK canliKur (+ GERCEK kabukDurumu), sahte kart / ag / eklenti,
// sahte saat. Olculen: imzali akis adresi sayisi (her biri tek kullanimlik sayac + kasaya YAZIM) ve imzali
// `G?` istekleri. A6: "yeniden baglanma 1, 2, 4, 8, 16, 30 s".
import { describe, it, expect, vi, afterEach } from "vitest";
import { canliKur } from "../../src/cekirdek/canli.js";
import { kabukDurumu } from "../../src/ekran/kabuk_durum.js";

afterEach(() => { vi.useRealTimers(); });

const D = "D 12.4820 1.936000 24.17000 10.0000 0.0027778 123456 500 0 0";

function duzenek(davranis) {
  const dinleyen = {};
  const sayim = { url: 0, istek: 0, akisAc: 0, kapat: 0, anlar: [] };
  let no = 0;
  const yay = (ad, veri) => { if (dinleyen[ad]) dinleyen[ad](veri); };
  const eklenti = { addListener: (ad, fn) => { dinleyen[ad] = fn; } };
  const kart = {
    durum: () => ({ durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef" }),   // kart.js ag hatasinda "bagli" kalir
    istek: async () => { sayim.istek += 1; return {}; },
    akisUrl: async () => { sayim.url += 1; sayim.anlar.push(Date.now()); return `http://192.168.1.7:80/akis?_c=1&_s=${sayim.url}&_i=00`; },
  };
  const ag = {
    akisAc: async () => { sayim.akisAc += 1; const kimlik = "a" + (++no); davranis(kimlik, yay); return { kimlik }; },
    akisKapat: async () => { sayim.kapat += 1; },
  };
  return { sayim, kart, ag, eklenti };
}

describe("curutucu 5C: yeniden baglanma firtinasi", () => {
  it("kart baglantiyi kabul edip BIR satir yollayip kapatiyor: dakikada en cok ~10 imzali baglanti olmali", async () => {
    vi.useFakeTimers();
    const s = duzenek((kimlik, yay) => {
      setTimeout(() => { yay("akisDurum", { kimlik, hal: "acik" }); yay("akis", { kimlik, satirlar: [D] }); }, 50);
      setTimeout(() => { yay("akisDurum", { kimlik, hal: "kapandi" }); }, 100);
    });
    const canli = canliKur({ kart: s.kart, ag: s.ag, eklenti: s.eklenti });
    canli.baslat();
    await vi.advanceTimersByTimeAsync(60000);
    canli.durdur();
    console.log(`[firtina-1] 60 s: imzali akis adresi=${s.sayim.url}, imzali G? istegi=${s.sayim.istek}, toplam imza=${s.sayim.url + s.sayim.istek}`);
    // KIRMIZI: tek satir geri cekilmeyi sifirlar -> sonsuza dek 1 s dongusu, her turda 2 imza + kasa yazimi.
    expect(s.sayim.url).toBeLessThanOrEqual(10);
  });

  it("kart KAPALI, uygulama onde 1 saat: 30 s tavani tutmali (saatte ~125 imzali adres)", async () => {
    vi.useFakeTimers();
    const s = duzenek((kimlik, yay) => {
      setTimeout(() => { yay("akisDurum", { kimlik, hal: "hata", tur: "baglanti" }); }, 100);
    });
    const canli = canliKur({ kart: s.kart, ag: s.ag, eklenti: s.eklenti });
    const kartNesnesi = { ...s.kart, baglan: async () => ({ durum: "bagli", adres: "192.168.1.7:80", kimlik: "0123456789abcdef", bilgi: {} }) };
    const k = kabukDurumu({ kartAl: async () => kartNesnesi, canliAl: async () => canli, belge: null });
    await k.ac();
    await vi.advanceTimersByTimeAsync(3600000);
    k.birak();
    const aralar = s.sayim.anlar.slice(1).map((t, i) => Math.round((t - s.sayim.anlar[i]) / 1000));
    console.log(`[firtina-2] 1 saat: imzali akis adresi=${s.sayim.url}; ilk 14 aralik (s)=${aralar.slice(0, 14).join(",")}; en uzun aralik=${Math.max(...aralar)} s`);
    // KIRMIZI: kabuk 30 s'de bir akisi kapatip yeniden baslatiyor -> canli.baslat() `deneme = 0` yapar;
    // geri cekilme 1,2,4,8,16'dan oteye HIC gecmez (30 s basamagina ulasilmaz).
    expect(Math.max(...aralar)).toBeGreaterThanOrEqual(30);
    expect(s.sayim.url).toBeLessThanOrEqual(150);
  });
});
