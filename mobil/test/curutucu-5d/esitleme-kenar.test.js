// Curutucu 5D — esitleme dongusunun kenar halleri. GERCEK kart.js + ag.js + kasa (kopru sahte), sahte kart
// 127.0.0.1'de, depo: depo.js + eklenti sahtesi (gecici dizinde gercek dosyalar). Duzenek mobil/test/esitleme.test.js
// ile ayni; kaynak dosyalara dokunulmaz.
import { describe, it, expect, afterEach, beforeEach } from "vitest";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import { T_NOKTA, kayitPaketle } from "../../../ortak/src/kayit.js";
import { depoKur } from "../../src/cekirdek/depo.js";
import { esitlemeKur } from "../../src/cekirdek/esitleme.js";
import { kabukDurumu } from "../../src/ekran/kabuk_durum.js";
import { depoSahtesi } from "../yardim/depo_sahtesi.mjs";
import { K1, bekle, eslesmis } from "../curutucu-5b/yardim.mjs";

const kayit = (sira) => kayitPaketle(T_NOKTA, sira, 3, Uint8Array.from({ length: 36 }, (_, j) => (sira * 7 + j) & 255));
const akisKur = (ilk, son) => Buffer.concat(Array.from({ length: son - ilk + 1 }, (_, i) => kayit(ilk + i)));

let dizin;
let kapat = [];
beforeEach(() => { dizin = mkdtempSync(join(tmpdir(), "curutucu5d-")); });
afterEach(async () => {
  for (const k of kapat) await k();
  kapat = [];
  rmSync(dizin, { recursive: true, force: true });
});

async function duzenek({ kayitSayisi = 60, onayAcik = () => false, secenek = {} } = {}) {
  const { k, t } = await eslesmis();
  kapat.push(() => k.kapat());
  k.ayarla({ kayitlar: akisKur(1, kayitSayisi) });
  const ek = depoSahtesi(dizin);
  const haller = [];
  const e = esitlemeKur({ kartAl: async () => t.kart, depoAl: (kimlik) => depoKur(ek, kimlik), onayAcik, istekAraMs: 0, ...secenek });
  e.dinle((d) => haller.push(d.hal));
  const go = () => k.durum.komutlar.filter((x) => /^Go/.test(x));
  return { k, t, ek, e, haller, go };
}

describe("curutucu 5D — A21: onay ayari", () => {
  it("kullanici onayi tur SURERKEN kapatirsa, o andan sonra karta Go GITMEZ", async () => {
    // 2000 kayit = 104 000 B = 13 parca (8192 B). Onay ACIK baslar; 2. parcadan sonra kullanici KAPATIR.
    let acik = true;
    const d = await duzenek({ kayitSayisi: 2000, onayAcik: () => acik });
    let kapatildigindaGo = null;
    const asil = d.ek.veriEkle;
    let parca = 0;
    d.ek.veriEkle = async (v) => {
      const y = await asil(v);
      parca += 1;
      if (parca === 2) { acik = false; kapatildigindaGo = d.go().length; }
      return y;
    };
    const s = await d.e.simdi();
    expect(s.hal).toBe("tamam");
    expect(parca).toBeGreaterThan(5);
    // Ayar kapatildiktan sonra gonderilen Go sayisi: en cok 1 (o an yolda olan). Bugun: tur sonuna kadar HEPSI.
    expect(d.go().length - kapatildigindaGo).toBeLessThanOrEqual(1);
  });

  it("onayAcik() atarsa simdi() REDDETMEZ ('asla atmaz'), hal 'hata' olur, Go gitmez", async () => {
    const d = await duzenek({ onayAcik: () => { throw new Error("localStorage kapali"); } });
    const s = await d.e.simdi().then((x) => ({ deger: x }), (h) => ({ reddetti: String(h && h.message) }));
    expect(d.go()).toEqual([]);
    expect(s.reddetti).toBeUndefined();
    expect(["tamam", "hata"]).toContain(d.e.durum().hal);
  });
});

describe("curutucu 5D — A23: kopyayi sifirla", () => {
  it("tur surerken 'kayit bitti' olayi geldiyse sifirla() BASARIR (bekler), 'mesgul' diye reddetmez", async () => {
    const d = await duzenek({ kayitSayisi: 400 });
    d.k.ayarla({ gecikmeMs: 15 });
    const ilk = d.e.simdi();
    await bekle(20);
    d.e.kayitBitti();                    // suren tur bitince BIR tur daha (esitleme.js `tekrar`)
    const sonuc = await d.e.sifirla().then(() => "tamam", (h) => `${h && h.name}`);
    await ilk;
    for (let i = 0; i < 200 && d.e.durum().hal === "esitleniyor"; i++) await bekle(10);
    expect(sonuc).toBe("tamam");
  });
});

describe("curutucu 5D — A22: arka planda esitleme yok", () => {
  it("uygulama arka plana gectikten SONRA yeni bir esitleme turu BASLAMAZ (bekleyen 'tekrar' dahil)", async () => {
    const d = await duzenek({ kayitSayisi: 400 });
    d.k.ayarla({ gecikmeMs: 15 });
    const canli = { baslat() {}, durdur() {}, durum: () => ({ bagli: false, hal: "kapali", son: null, kayit: null }), dinle: () => () => {}, seri: () => null, komut: async () => true };
    const aralik = { fn: null };
    const kabuk = kabukDurumu({
      kartAl: async () => d.t.kart, canliAl: async () => canli, esitlemeAl: async () => d.e, belge: null,
      araliKur: (fn) => { aralik.fn = fn; return 1; }, araliSil: () => { aralik.fn = null; },
    });
    await kabuk.ac();
    expect(kabuk.baglanti.value.durum).toBe("bagli");
    aralik.fn(); await bekle(5);         // esitleme kurulur
    aralik.fn(); await bekle(5);         // "baglandi": ilk tur basladi
    expect(d.e.durum().hal).toBe("esitleniyor");
    d.e.kayitBitti();                    // kabuk bunu canli akistan gelen KAYIT -> BOS gecisinde cagirir
    kabuk.kapat();                       // ARKA PLAN
    const kapanistaTur = d.haller.filter((h) => h === "esitleniyor").length;
    for (let i = 0; i < 300; i++) {
      await bekle(10);
      if (d.e.durum().hal !== "esitleniyor" && i > 30) break;
    }
    await bekle(100);
    expect(d.haller.filter((h) => h === "esitleniyor").length - kapanistaTur).toBe(0);
  });
});
